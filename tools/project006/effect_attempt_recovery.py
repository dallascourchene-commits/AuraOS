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
    RecoveryContext,
    decide_recovery,
    effect_attempt_root,
)
from tools.project006.terminal_outbox import CommandIdentity, OutboxJournal, TerminalResponse

D0 = "D0_NONPROMOTING"
SCHEMA = "AURA-PROJECT006-EFFECT-ATTEMPT-JOURNAL-v1"


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
    """Non-authorizing proof that a provider action was durably journalled first."""

    action: Action
    command_id: str
    intent_root: str
    contract_root: str
    effect_attempt_root: str | None
    provider_request_count: int
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
        if type(self.provider_request_count) is not int or self.provider_request_count < 0:
            raise ValueError("provider_request_count must be nonnegative exact int")
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("permit cannot mint authority")


class EffectAttemptJournal:
    """Durable effect-attempt/recovery owner separate from the final-return outbox.

    The final Project006 outbox owns outbound terminal publication.  This journal
    owns only the effect lifecycle needed to prove whether a provider call may be
    made or may already have escaped.  A provider-call permit is returned only
    after the corresponding effect-attempt root and request count have committed
    under SQLite WAL + FULL synchronous durability.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        con = sqlite3.connect(self.path)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("""CREATE TABLE IF NOT EXISTS effect_tx(
              command_id TEXT PRIMARY KEY,
              idempotency_key TEXT NOT NULL,
              source_digest TEXT NOT NULL,
              intent_root TEXT NOT NULL,
              contract_root TEXT NOT NULL,
              effect_payload_root TEXT NOT NULL,
              phase TEXT NOT NULL,
              provider_request_count INTEGER NOT NULL DEFAULT 0,
              ack_receipt_root TEXT,
              ack_outbound_ref TEXT,
              effect_attempt_root TEXT,
              provider_operation_root TEXT,
              result_root TEXT,
              terminal_class TEXT,
              return_receipt_root TEXT
            )""")
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

    def bind_admitted(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract) -> None:
        self._bind(ident, intent, contract)
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            values = (ident.idempotency_key, ident.source_digest, intent.identity_root,
                      contract.contract_root, intent.effect_payload_root)
            if row is None:
                con.execute("""INSERT INTO effect_tx(
                    command_id,idempotency_key,source_digest,intent_root,contract_root,effect_payload_root,phase
                ) VALUES(?,?,?,?,?,?,?)""",
                            (ident.command_id, *values, Phase.DECIDED_ADMITTED.value))
                return
            observed = tuple(row[key] for key in (
                "idempotency_key", "source_digest", "intent_root", "contract_root", "effect_payload_root"
            ))
            if observed != values:
                raise ValueError("EFFECT_LINEAGE_EQUIVOCATION")

    @staticmethod
    def _state(row: sqlite3.Row) -> DurableEffectState:
        return DurableEffectState(
            Phase(row["phase"]),
            row["intent_root"],
            row["idempotency_key"],
            row["effect_payload_root"],
            row["contract_root"],
            row["provider_request_count"],
            row["ack_receipt_root"],
            row["effect_attempt_root"],
            row["provider_operation_root"],
            row["result_root"],
            row["return_receipt_root"],
            row["terminal_class"],
        )

    def status(self, command_id: str) -> dict[str, Any]:
        with self._con() as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            return dict(row)

    def publish_ack(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract,
                    writer: Callable[[Mapping[str, Any]], str]) -> str:
        """Publish ACK separately; provider execution stays impossible if the write fails."""
        self._bind(ident, intent, contract)
        with self._con() as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            if row["phase"] != Phase.DECIDED_ADMITTED.value:
                raise ValueError("ACK_PHASE_INVALID")
        response = TerminalResponse(
            ident,
            "ACK_ACCEPTED_PRE_EFFECT",
            provider_request_count=0,
            payload={"intent_root": intent.identity_root, "contract_root": contract.contract_root},
        )
        payload = response.canonical()
        ref = writer(payload)
        if not isinstance(ref, str) or not ref:
            raise ValueError("ACK_WRITER_DID_NOT_RETURN_REF")
        receipt = digest({"schema": SCHEMA, "kind": "ack_receipt", "payload": payload, "outbound_ref": ref})
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None or row["phase"] != Phase.DECIDED_ADMITTED.value:
                raise ValueError("ACK_PHASE_MOVED")
            con.execute("UPDATE effect_tx SET phase=?,ack_receipt_root=?,ack_outbound_ref=? WHERE command_id=?",
                        (Phase.ACK_WRITTEN_PRE_EFFECT.value, receipt, ref, ident.command_id))
        return receipt

    def decide_and_persist(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract,
                           context: RecoveryContext) -> ProviderActionPermit:
        """Run O10 recovery and durably record every call/retry before returning its permit."""
        self._bind(ident, intent, contract)
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            state = self._state(row)
            decision = decide_recovery(state, intent, contract, context)
            if decision.action in (Action.CALL_PROVIDER_FIRST_TIME, Action.RETRY_EXACT_SAME_EFFECT):
                count = state.provider_request_count + 1
                attempt_root = effect_attempt_root(intent, contract, count)
                con.execute("UPDATE effect_tx SET phase=?,provider_request_count=?,effect_attempt_root=? WHERE command_id=?",
                            (Phase.EFFECT_ATTEMPT_DURABLE.value, count, attempt_root, ident.command_id))
                return ProviderActionPermit(decision.action, ident.command_id, intent.identity_root,
                                            contract.contract_root, attempt_root, count)
            return ProviderActionPermit(decision.action, ident.command_id, intent.identity_root,
                                        contract.contract_root, state.effect_attempt_root,
                                        state.provider_request_count)

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
            con.execute("UPDATE effect_tx SET phase=?,result_root=?,provider_operation_root=? WHERE command_id=?",
                        (Phase.RESULT_OBSERVED.value, result_root, provider_operation_root, command_id))

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

    def stage_final_terminal(self, outbox: OutboxJournal, ident: CommandIdentity) -> str:
        """Cross-bind the effect journal into Project006's final-return owner."""
        with self._con() as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            if row["idempotency_key"] != ident.idempotency_key or row["source_digest"] != ident.source_digest:
                raise ValueError("FINAL_RETURN_IDENTITY_DIVERGED")
            phase = Phase(row["phase"])
            count = row["provider_request_count"]
            payload = {
                "intent_root": row["intent_root"],
                "contract_root": row["contract_root"],
                "effect_payload_root": row["effect_payload_root"],
                "effect_attempt_root": row["effect_attempt_root"],
                "provider_operation_root": row["provider_operation_root"],
                "result_root": row["result_root"],
            }
            if phase is Phase.RESULT_OBSERVED:
                kind = "RESULT"
            elif phase is Phase.ERROR_TERMINAL:
                kind = "EXECUTOR_ERROR"
            elif phase is Phase.COMPLETION_AMBIGUOUS:
                kind = "COMPLETION_AMBIGUOUS"
            else:
                raise ValueError("NO_FINAL_EFFECT_TERMINAL")
        return outbox.stage_terminal(TerminalResponse(
            ident, kind, provider_request_count=count, payload=payload
        ))

    def mark_return_written(self, command_id: str, outbound_ref: str) -> str:
        if not isinstance(outbound_ref, str) or not outbound_ref:
            raise ValueError("OUTBOUND_REF_REQUIRED")
        receipt = digest({"schema": SCHEMA, "kind": "return_receipt",
                          "command_id": command_id, "outbound_ref": outbound_ref})
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["phase"] not in (
                Phase.RESULT_OBSERVED.value, Phase.ERROR_TERMINAL.value, Phase.COMPLETION_AMBIGUOUS.value
            ):
                raise ValueError("RETURN_PHASE_INVALID")
            con.execute("UPDATE effect_tx SET phase=?,return_receipt_root=? WHERE command_id=?",
                        (Phase.RETURN_WRITTEN.value, receipt, command_id))
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
