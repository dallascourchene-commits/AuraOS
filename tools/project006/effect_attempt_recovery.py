from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from tools.arena.effect_return_atomicity import (
    Action,
    DurableEffectState,
    EffectContract,
    EffectIntent,
    Phase,
    ProviderActionCurrentness,
    RecoveryContext,
    RecoveryMode,
    _currentness_failure,
    decide_recovery,
    effect_attempt_root,
)
from tools.project006.terminal_outbox import (
    CommandIdentity,
    OutboxJournal,
    TerminalResponse,
    TxState,
)

D0 = "D0_NONPROMOTING"
SCHEMA = "AURA-PROJECT006-EFFECT-ATTEMPT-JOURNAL-v3"
CurrentnessResolver = Callable[[EffectIntent, EffectContract], ProviderActionCurrentness | None]


def digest(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} required")
    return value


@dataclass(frozen=True)
class ProviderActionPermit:
    """D0 proof that a candidate provider action was journalled after currentness resolution."""

    action: Action
    command_id: str
    intent_root: str
    contract_root: str
    effect_attempt_root: str | None
    provider_request_count: int
    provider_action_currentness_root: str | None
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.action, Action):
            raise ValueError("action must be Action")
        _id(self.command_id, "command_id")
        _root(self.intent_root, "intent_root")
        _root(self.contract_root, "contract_root")
        if self.effect_attempt_root is not None:
            _root(self.effect_attempt_root, "effect_attempt_root")
        if self.provider_action_currentness_root is not None:
            _root(self.provider_action_currentness_root, "provider_action_currentness_root")
        if type(self.provider_request_count) is not int or self.provider_request_count < 0:
            raise ValueError("provider_request_count must be nonnegative exact int")
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("permit cannot mint authority")


class EffectAttemptJournal:
    """Durable effect-attempt/recovery owner separate from final-return publication.

    Provider-call candidates require owner-resolved, at-use currentness. ACK
    publication is two-phase: an INFLIGHT marker commits before the external
    writer is invoked. A crash after the writer may have succeeded therefore
    reopens as ACK reconciliation, never blind ACK replay or provider execution.

    The journal stores the full Drive source identity. Final effect closure can
    be marked only from the canonical final-return outbox's already-published,
    exact response; a caller-provided outbound-ref string is never proof that a
    return was written.
    """

    def __init__(self, path: str | Path, *, currentness_resolver: CurrentnessResolver | None = None):
        self.path = str(path)
        self.currentness_resolver = currentness_resolver
        con = sqlite3.connect(self.path)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("""CREATE TABLE IF NOT EXISTS effect_tx(
              command_id TEXT PRIMARY KEY,
              idempotency_key TEXT NOT NULL,
              source_file_id TEXT NOT NULL,
              source_revision TEXT NOT NULL,
              source_digest TEXT NOT NULL,
              intent_root TEXT NOT NULL,
              contract_root TEXT NOT NULL,
              effect_payload_root TEXT NOT NULL,
              recovery_mode TEXT NOT NULL DEFAULT 'NON_RETRYABLE',
              phase TEXT NOT NULL,
              provider_request_count INTEGER NOT NULL DEFAULT 0,
              ack_payload_root TEXT,
              ack_receipt_root TEXT,
              ack_outbound_ref TEXT,
              effect_attempt_root TEXT,
              provider_action_currentness_root TEXT,
              provider_operation_root TEXT,
              result_root TEXT,
              terminal_class TEXT,
              return_receipt_root TEXT
            )""")
            columns = {row[1] for row in con.execute("PRAGMA table_info(effect_tx)")}
            additions = {
                "source_file_id": "TEXT",
                "source_revision": "TEXT",
                "recovery_mode": "TEXT NOT NULL DEFAULT 'NON_RETRYABLE'",
                "ack_payload_root": "TEXT",
                "provider_action_currentness_root": "TEXT",
            }
            for name, ddl in additions.items():
                if name not in columns:
                    con.execute(f"ALTER TABLE effect_tx ADD COLUMN {name} {ddl}")
            con.commit()
        finally:
            con.close()

    @contextmanager
    def _con(self, *, immediate: bool = False):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            if immediate:
                con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _bind(ident: CommandIdentity, intent: EffectIntent, contract: EffectContract) -> None:
        ident.validate()
        if ident.command_id != intent.command_id:
            raise ValueError("COMMAND_IDENTITY_DIVERGED")
        if ident.idempotency_key != intent.idempotency_key:
            raise ValueError("IDEMPOTENCY_IDENTITY_DIVERGED")
        if ident.source_digest != intent.source_root:
            raise ValueError("SOURCE_IDENTITY_DIVERGED")
        if intent.effect_type != contract.effect_type:
            raise ValueError("EFFECT_CONTRACT_TYPE_DIVERGED")

    @staticmethod
    def _assert_ident_row(row: sqlite3.Row, ident: CommandIdentity) -> None:
        if row["source_file_id"] is None or row["source_revision"] is None:
            raise ValueError("LEGACY_SOURCE_IDENTITY_REBIND_REQUIRED")
        observed = (
            row["idempotency_key"], row["source_file_id"],
            row["source_revision"], row["source_digest"],
        )
        expected = (
            ident.idempotency_key, ident.source_file_id,
            ident.source_revision, ident.source_digest,
        )
        if observed != expected:
            raise ValueError("FULL_SOURCE_IDENTITY_DIVERGED")

    @classmethod
    def _assert_active_lineage(
        cls,
        row: sqlite3.Row,
        ident: CommandIdentity,
        intent: EffectIntent,
        contract: EffectContract,
    ) -> None:
        cls._assert_ident_row(row, ident)
        observed = (
            row["intent_root"], row["contract_root"],
            row["effect_payload_root"], row["recovery_mode"],
        )
        expected = (
            intent.identity_root, contract.contract_root,
            intent.effect_payload_root, contract.recovery_mode.value,
        )
        if observed != expected:
            raise ValueError("EFFECT_LINEAGE_EQUIVOCATION")

    def _resolve_currentness(self, intent: EffectIntent, contract: EffectContract) -> ProviderActionCurrentness | None:
        if self.currentness_resolver is None:
            return None
        try:
            resolved = self.currentness_resolver(intent, contract)
        except Exception:
            return None
        if resolved is not None and not isinstance(resolved, ProviderActionCurrentness):
            return None
        return resolved

    def _require_currentness(self, intent: EffectIntent, contract: EffectContract) -> ProviderActionCurrentness:
        currentness = self._resolve_currentness(intent, contract)
        failure = _currentness_failure(intent, currentness)
        if failure is not None:
            raise ValueError(failure)
        assert currentness is not None
        return currentness

    def bind_admitted(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract) -> None:
        self._bind(ident, intent, contract)
        values = (
            ident.idempotency_key,
            ident.source_file_id,
            ident.source_revision,
            ident.source_digest,
            intent.identity_root,
            contract.contract_root,
            intent.effect_payload_root,
            contract.recovery_mode.value,
        )
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                con.execute("""INSERT INTO effect_tx(
                    command_id,idempotency_key,source_file_id,source_revision,source_digest,
                    intent_root,contract_root,effect_payload_root,recovery_mode,phase
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (ident.command_id, *values, Phase.DECIDED_ADMITTED.value))
                return
            self._assert_ident_row(row, ident)
            observed = (
                row["idempotency_key"], row["source_file_id"], row["source_revision"],
                row["source_digest"], row["intent_root"], row["contract_root"],
                row["effect_payload_root"], row["recovery_mode"],
            )
            if observed != values:
                raise ValueError("EFFECT_LINEAGE_EQUIVOCATION")

    @staticmethod
    def _state(row: sqlite3.Row) -> DurableEffectState:
        return DurableEffectState(
            Phase(row["phase"]), row["intent_root"], row["idempotency_key"],
            row["effect_payload_root"], row["contract_root"], row["provider_request_count"],
            row["ack_receipt_root"], row["effect_attempt_root"], row["provider_operation_root"],
            row["result_root"], row["return_receipt_root"], row["terminal_class"],
        )

    def status(self, command_id: str) -> dict[str, Any]:
        with self._con() as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            return dict(row)

    def prepare_ack(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract) -> tuple[dict[str, Any], str]:
        """Durably mark ACK publication INFLIGHT before any external write occurs."""
        self._bind(ident, intent, contract)
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            self._assert_active_lineage(row, ident, intent, contract)
            phase = Phase(row["phase"])
            if phase is Phase.ACK_WRITTEN_PRE_EFFECT:
                raise ValueError("ACK_ALREADY_WRITTEN")
            if phase in (Phase.ACK_WRITE_INFLIGHT, Phase.ACK_WRITE_AMBIGUOUS):
                raise ValueError("ACK_RECONCILIATION_REQUIRED")
            if phase is not Phase.DECIDED_ADMITTED:
                raise ValueError("ACK_PHASE_INVALID")
            self._require_currentness(intent, contract)
            response = TerminalResponse(
                ident, "ACK_ACCEPTED_PRE_EFFECT", provider_request_count=0,
                payload={"intent_root": intent.identity_root, "contract_root": contract.contract_root},
            )
            payload = response.canonical()
            payload_root = digest(payload)
            con.execute("UPDATE effect_tx SET phase=?,ack_payload_root=? WHERE command_id=?",
                        (Phase.ACK_WRITE_INFLIGHT.value, payload_root, ident.command_id))
        return payload, payload_root

    def mark_ack_ambiguous(self, command_id: str, payload_root: str) -> None:
        _root(payload_root, "ack_payload_root")
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["phase"] != Phase.ACK_WRITE_INFLIGHT.value or row["ack_payload_root"] != payload_root:
                raise ValueError("ACK_AMBIGUITY_STATE_MOVED")
            con.execute("UPDATE effect_tx SET phase=? WHERE command_id=?",
                        (Phase.ACK_WRITE_AMBIGUOUS.value, command_id))

    def confirm_ack_written(self, command_id: str, payload_root: str, outbound_ref: str) -> str:
        _root(payload_root, "ack_payload_root")
        if not isinstance(outbound_ref, str) or not outbound_ref:
            raise ValueError("ACK_WRITER_DID_NOT_RETURN_REF")
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["phase"] != Phase.ACK_WRITE_INFLIGHT.value or row["ack_payload_root"] != payload_root:
                raise ValueError("ACK_CONFIRMATION_STATE_MOVED")
            receipt = digest({"schema": SCHEMA, "kind": "ack_receipt", "ack_payload_root": payload_root,
                              "outbound_ref": outbound_ref})
            con.execute("UPDATE effect_tx SET phase=?,ack_receipt_root=?,ack_outbound_ref=? WHERE command_id=?",
                        (Phase.ACK_WRITTEN_PRE_EFFECT.value, receipt, outbound_ref, command_id))
        return receipt

    def resolve_ambiguous_ack_as_written(self, command_id: str, payload_root: str, outbound_ref: str) -> str:
        """Explicit reconciliation path; never automatically resends an ambiguous ACK."""
        _root(payload_root, "ack_payload_root")
        if not isinstance(outbound_ref, str) or not outbound_ref:
            raise ValueError("ACK_OUTBOUND_REF_REQUIRED")
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["phase"] not in (Phase.ACK_WRITE_INFLIGHT.value, Phase.ACK_WRITE_AMBIGUOUS.value):
                raise ValueError("ACK_RECONCILIATION_STATE_INVALID")
            if row["ack_payload_root"] != payload_root:
                raise ValueError("ACK_PAYLOAD_ROOT_DIVERGED")
            receipt = digest({"schema": SCHEMA, "kind": "ack_receipt", "ack_payload_root": payload_root,
                              "outbound_ref": outbound_ref})
            con.execute("UPDATE effect_tx SET phase=?,ack_receipt_root=?,ack_outbound_ref=? WHERE command_id=?",
                        (Phase.ACK_WRITTEN_PRE_EFFECT.value, receipt, outbound_ref, command_id))
        return receipt

    def publish_ack(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract,
                    writer: Callable[[Mapping[str, Any]], str]) -> str:
        row = self.status(ident.command_id)
        if row["phase"] == Phase.ACK_WRITTEN_PRE_EFFECT.value and row["ack_receipt_root"]:
            return str(row["ack_receipt_root"])
        payload, payload_root = self.prepare_ack(ident, intent, contract)
        try:
            ref = writer(payload)
        except Exception:
            self.mark_ack_ambiguous(ident.command_id, payload_root)
            raise
        return self.confirm_ack_written(ident.command_id, payload_root, ref)

    def decide_and_persist(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract,
                           context: RecoveryContext) -> ProviderActionPermit:
        """Resolve currentness for effect actions, while preserving already-owed terminal returns."""
        self._bind(ident, intent, contract)
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            self._assert_ident_row(row, ident)
            state = self._state(row)

            # A locally observed terminal outcome is already an owed return. Later
            # source/authorization/consumer currentness changes must not erase it.
            if state.phase in (Phase.RESULT_OBSERVED, Phase.ERROR_TERMINAL):
                return ProviderActionPermit(
                    Action.RETRY_RETURN_WRITER_ONLY, ident.command_id,
                    row["intent_root"], row["contract_root"], row["effect_attempt_root"],
                    row["provider_request_count"], None,
                )
            if state.phase is Phase.RETURN_WRITTEN:
                return ProviderActionPermit(
                    Action.NOOP_TERMINAL, ident.command_id,
                    row["intent_root"], row["contract_root"], row["effect_attempt_root"],
                    row["provider_request_count"], None,
                )

            self._assert_active_lineage(row, ident, intent, contract)
            currentness = self._resolve_currentness(intent, contract)
            decision = decide_recovery(state, intent, contract, context, currentness)
            currentness_root = decision.currentness_root
            if decision.action in (Action.CALL_PROVIDER_FIRST_TIME, Action.RETRY_EXACT_SAME_EFFECT):
                if currentness_root is None:
                    raise AssertionError("provider action requires owner-resolved currentness")
                count = state.provider_request_count + 1
                attempt_root = effect_attempt_root(intent, contract, count, currentness_root)
                con.execute("""UPDATE effect_tx SET phase=?,provider_request_count=?,effect_attempt_root=?,
                               provider_action_currentness_root=? WHERE command_id=?""",
                            (Phase.EFFECT_ATTEMPT_DURABLE.value, count, attempt_root, currentness_root, ident.command_id))
                return ProviderActionPermit(decision.action, ident.command_id, intent.identity_root,
                                            contract.contract_root, attempt_root, count, currentness_root)
            return ProviderActionPermit(decision.action, ident.command_id, intent.identity_root,
                                        contract.contract_root, state.effect_attempt_root,
                                        state.provider_request_count, currentness_root)

    def record_ambiguous(self, command_id: str, provider_operation_root: str | None = None) -> None:
        if provider_operation_root is not None:
            _root(provider_operation_root, "provider_operation_root")
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["phase"] != Phase.EFFECT_ATTEMPT_DURABLE.value:
                raise ValueError("AMBIGUOUS_WITHOUT_DURABLE_ATTEMPT")
            con.execute("UPDATE effect_tx SET phase=?,provider_operation_root=? WHERE command_id=?",
                        (Phase.COMPLETION_AMBIGUOUS.value, provider_operation_root, command_id))

    def record_result(self, command_id: str, result_root: str,
                      provider_operation_root: str | None = None) -> None:
        _root(result_root, "result_root")
        if provider_operation_root is not None:
            _root(provider_operation_root, "provider_operation_root")
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["phase"] not in (
                Phase.EFFECT_ATTEMPT_DURABLE.value, Phase.COMPLETION_AMBIGUOUS.value
            ):
                raise ValueError("RESULT_WITHOUT_DURABLE_ATTEMPT")
            existing = row["provider_operation_root"]
            if existing is not None and provider_operation_root is not None and existing != provider_operation_root:
                raise ValueError("PROVIDER_OPERATION_ROOT_CONFLICT")
            effective = provider_operation_root if provider_operation_root is not None else existing
            con.execute("UPDATE effect_tx SET phase=?,result_root=?,provider_operation_root=? WHERE command_id=?",
                        (Phase.RESULT_OBSERVED.value, result_root, effective, command_id))

    def record_error_terminal(self, command_id: str, result_root: str) -> None:
        _root(result_root, "error_root")
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["phase"] not in (
                Phase.EFFECT_ATTEMPT_DURABLE.value, Phase.COMPLETION_AMBIGUOUS.value
            ):
                raise ValueError("ERROR_WITHOUT_DURABLE_ATTEMPT")
            con.execute("UPDATE effect_tx SET phase=?,result_root=? WHERE command_id=?",
                        (Phase.ERROR_TERMINAL.value, result_root, command_id))

    @staticmethod
    def _terminal_response_for_row(row: sqlite3.Row, ident: CommandIdentity) -> TerminalResponse:
        phase = Phase(row["phase"])
        count = row["provider_request_count"]
        payload = {
            "intent_root": row["intent_root"],
            "contract_root": row["contract_root"],
            "effect_payload_root": row["effect_payload_root"],
            "effect_attempt_root": row["effect_attempt_root"],
            "provider_action_currentness_root": row["provider_action_currentness_root"],
            "provider_operation_root": row["provider_operation_root"],
            "result_root": row["result_root"],
        }
        if phase is Phase.RESULT_OBSERVED:
            kind = "RESULT"
        elif phase is Phase.ERROR_TERMINAL:
            kind = "EXECUTOR_ERROR"
        elif phase is Phase.COMPLETION_AMBIGUOUS:
            if RecoveryMode(row["recovery_mode"]) is not RecoveryMode.NON_RETRYABLE:
                raise ValueError("AMBIGUITY_REQUIRES_RECOVERY_DECISION")
            kind = "COMPLETION_AMBIGUOUS"
        else:
            raise ValueError("NO_FINAL_EFFECT_TERMINAL")
        return TerminalResponse(ident, kind, provider_request_count=count, payload=payload)

    def stage_final_terminal(self, outbox: OutboxJournal, ident: CommandIdentity) -> str:
        """Stage the exact effect outcome in Project006's canonical final-return owner."""
        with self._con() as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            self._assert_ident_row(row, ident)
            response = self._terminal_response_for_row(row, ident)
        return outbox.stage_terminal(response)

    def mark_return_written(self, outbox: OutboxJournal, ident: CommandIdentity) -> str:
        """Close the effect journal only from an owner-proved exact published return."""
        ident.validate()
        owner = outbox.status(ident.command_id)
        if owner["state"] != TxState.RETURN_WRITTEN.value:
            raise ValueError("OUTBOX_RETURN_NOT_WRITTEN")
        if not owner.get("response_digest") or not owner.get("response_json") or not owner.get("outbound_ref"):
            raise ValueError("OUTBOX_RETURN_EVIDENCE_INCOMPLETE")
        if hashlib.sha256(owner["response_json"].encode()).hexdigest() != owner["response_digest"]:
            raise ValueError("OUTBOX_RETURN_CORRUPT")

        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            self._assert_ident_row(row, ident)
            if row["phase"] == Phase.RETURN_WRITTEN.value and row["return_receipt_root"]:
                return str(row["return_receipt_root"])

            expected = self._terminal_response_for_row(row, ident)
            if owner["response_digest"] != expected.digest():
                raise ValueError("OUTBOX_RETURN_DIGEST_DIVERGED")
            parsed = json.loads(owner["response_json"])
            observed_identity = (
                parsed.get("command_id"), parsed.get("idempotency_key"),
                parsed.get("source_file_id"), parsed.get("source_revision"),
                parsed.get("source_digest"),
            )
            expected_identity = (
                ident.command_id, ident.idempotency_key,
                ident.source_file_id, ident.source_revision, ident.source_digest,
            )
            if observed_identity != expected_identity:
                raise ValueError("OUTBOX_RETURN_SOURCE_IDENTITY_DIVERGED")

            receipt = digest({
                "schema": SCHEMA,
                "kind": "owner_proved_return_receipt",
                "command_id": ident.command_id,
                "response_digest": owner["response_digest"],
                "outbound_ref": owner["outbound_ref"],
                "outbox_state": owner["state"],
            })
            con.execute("UPDATE effect_tx SET phase=?,return_receipt_root=? WHERE command_id=?",
                        (Phase.RETURN_WRITTEN.value, receipt, ident.command_id))
        return receipt


def hard_o11_state(axes) -> str:
    """Eight hard ternary axes; nuisance context may not repair a hard invalid state."""
    if len(axes) != 8 or any(type(x) is not int or x not in (0, 1, 2) for x in axes):
        return "HOLD_MALFORMED"
    if 0 in axes:
        return "HOLD_HARD_INVALID"
    if 1 in axes:
        return "HOLD_UNRESOLVED"
    return "READY_RECOVERY_ACTION_D0"
