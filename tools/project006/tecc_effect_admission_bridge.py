from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac
import json
import sqlite3
import importlib
from typing import Any, Mapping

D0 = "D0_NONPROMOTING"
TECC_SCHEMA = "AURA-TECC-v1"
CONSUMER_SCHEMA = "AURA-MEMCITY-TECC-CONSUMER-ADMISSION-v1"
BRIDGE_SCHEMA = "AURA-PROJECT006-TECC-EFFECT-ADMISSION-BRIDGE-v2"
OWNER_JOURNAL_SCHEMA = "AURA-PROJECT006-EFFECT-ATTEMPT-JOURNAL-v3"


def canon(v: object) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(v: object) -> str:
    return sha256(canon(v)).hexdigest()


def _root(v: str, name: str) -> str:
    if not isinstance(v, str) or len(v) != 64 or v.lower() != v or any(c not in "0123456789abcdef" for c in v):
        raise ValueError(f"{name} must be lowercase sha256 hex")
    return v


def _id(v: str, name: str) -> str:
    if not isinstance(v, str) or not v:
        raise ValueError(f"{name} required")
    return v


def _nn(v: int, name: str) -> int:
    if type(v) is not int or v < 0:
        raise ValueError(f"{name} must be nonnegative exact int")
    return v


def _explicit_false(v: bool, name: str) -> None:
    if type(v) is not bool or v:
        raise ValueError(f"{name} must be explicit false")


def operation_identity_root(ident: Any, intent: Any, contract: Any) -> str:
    return digest({
        "schema": BRIDGE_SCHEMA,
        "kind": "operation_identity",
        "command_id": getattr(ident, "command_id", None),
        "idempotency_key": getattr(ident, "idempotency_key", None),
        "source_file_id": getattr(ident, "source_file_id", None),
        "source_revision": getattr(ident, "source_revision", None),
        "source_digest": getattr(ident, "source_digest", None),
        "intent_root": getattr(intent, "identity_root", None),
        "effect_payload_root": getattr(intent, "effect_payload_root", None),
        "contract_root": getattr(contract, "contract_root", None),
    })


@dataclass(frozen=True)
class ProducerTeccEvidence:
    producer_schema: str
    producer_semantic_head: str
    tecc_input_root: str
    handoff_root: str
    effect_refinement_root: str
    effect_escalation_root: str
    intent_root: str
    effect_payload_root: str
    proof_generation_root: str
    proof_semantics_id: str
    producer_lineage: str
    required_verifier_schema: str
    receipt_root: str
    authority_minted: bool = False
    mutation_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for n in ("producer_schema", "producer_semantic_head", "proof_semantics_id", "producer_lineage", "required_verifier_schema"):
            _id(getattr(self, n), n)
        for n in ("tecc_input_root", "handoff_root", "effect_refinement_root", "effect_escalation_root", "intent_root", "effect_payload_root", "proof_generation_root", "receipt_root"):
            _root(getattr(self, n), n)
        for n in ("authority_minted", "mutation_authority", "effect_authority", "gate10"):
            _explicit_false(getattr(self, n), n)

    def payload(self) -> dict[str, object]:
        return {
            "producer_schema": self.producer_schema,
            "producer_semantic_head": self.producer_semantic_head,
            "tecc_input_root": self.tecc_input_root,
            "handoff_root": self.handoff_root,
            "effect_refinement_root": self.effect_refinement_root,
            "effect_escalation_root": self.effect_escalation_root,
            "intent_root": self.intent_root,
            "effect_payload_root": self.effect_payload_root,
            "proof_generation_root": self.proof_generation_root,
            "proof_semantics_id": self.proof_semantics_id,
            "producer_lineage": self.producer_lineage,
            "required_verifier_schema": self.required_verifier_schema,
            "authority_minted": False,
            "mutation_authority": False,
            "effect_authority": False,
            "gate10": False,
        }


@dataclass(frozen=True)
class ConsumerAdmissionEvidence:
    schema: str
    disposition: str
    producer_receipt_root: str
    tecc_input_root: str
    consumer_generation: int
    currentness_root: str
    verifier_instance: str
    observer_lineage: str
    observer_receipt_root: str
    admission_root: str
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for n in ("schema", "disposition", "verifier_instance", "observer_lineage"):
            _id(getattr(self, n), n)
        for n in ("producer_receipt_root", "tecc_input_root", "currentness_root", "observer_receipt_root", "admission_root"):
            _root(getattr(self, n), n)
        _nn(self.consumer_generation, "consumer_generation")
        for n in ("authority_minted", "effect_authority", "gate10"):
            _explicit_false(getattr(self, n), n)

    def payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "disposition": self.disposition,
            "producer_receipt_root": self.producer_receipt_root,
            "tecc_input_root": self.tecc_input_root,
            "consumer_generation": self.consumer_generation,
            "currentness_root": self.currentness_root,
            "verifier_instance": self.verifier_instance,
            "observer_lineage": self.observer_lineage,
            "observer_receipt_root": self.observer_receipt_root,
            "authority_minted": False,
            "effect_authority": False,
            "gate10": False,
        }


@dataclass(frozen=True)
class TeccAuthorizationReceipt:
    schema: str
    tecc_input_root: str
    consumer_admission_root: str
    operation_identity_root: str
    intent_root: str
    effect_payload_root: str
    contract_root: str
    authority_scope_root: str
    authority_epoch: int
    expires_at: int
    verifier_instance: str
    authorized: bool
    signature: str

    def __post_init__(self) -> None:
        for n in ("schema", "verifier_instance"):
            _id(getattr(self, n), n)
        for n in ("tecc_input_root", "consumer_admission_root", "operation_identity_root", "intent_root", "effect_payload_root", "contract_root", "authority_scope_root", "signature"):
            _root(getattr(self, n), n)
        _nn(self.authority_epoch, "authority_epoch")
        _nn(self.expires_at, "expires_at")
        if type(self.authorized) is not bool:
            raise ValueError("authorized must be bool")

    def payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "tecc_input_root": self.tecc_input_root,
            "consumer_admission_root": self.consumer_admission_root,
            "operation_identity_root": self.operation_identity_root,
            "intent_root": self.intent_root,
            "effect_payload_root": self.effect_payload_root,
            "contract_root": self.contract_root,
            "authority_scope_root": self.authority_scope_root,
            "authority_epoch": self.authority_epoch,
            "expires_at": self.expires_at,
            "verifier_instance": self.verifier_instance,
            "authorized": self.authorized,
        }

    @property
    def receipt_root(self) -> str:
        return digest({**self.payload(), "signature": self.signature})


@dataclass(frozen=True)
class TeccVerifierRegistry:
    authorization_key: bytes
    registry_root: str

    def __post_init__(self) -> None:
        if not isinstance(self.authorization_key, bytes) or len(self.authorization_key) < 16:
            raise ValueError("authorization_key must be >=16 bytes")
        _root(self.registry_root, "registry_root")


@dataclass(frozen=True)
class AdmissionAtUseContext:
    expected_producer_schema: str
    producer_semantic_head: str
    producer_receipt_root: str
    proof_generation_root: str
    proof_semantics_id: str
    producer_lineage: str
    tecc_input_root: str
    effect_escalation_root: str
    expected_consumer_schema: str
    consumer_generation: int
    currentness_root: str
    verifier_instance: str
    authority_scope_root: str
    authority_epoch: int
    now: int

    def __post_init__(self) -> None:
        for n in ("expected_producer_schema", "producer_semantic_head", "proof_semantics_id", "producer_lineage", "expected_consumer_schema", "verifier_instance"):
            _id(getattr(self, n), n)
        for n in ("producer_receipt_root", "proof_generation_root", "tecc_input_root", "effect_escalation_root", "currentness_root", "authority_scope_root"):
            _root(getattr(self, n), n)
        for n in ("consumer_generation", "authority_epoch", "now"):
            _nn(getattr(self, n), n)


class AdmissionDisposition(str, Enum):
    BIND_EFFECT_ATTEMPT_D0 = "BIND_EFFECT_ATTEMPT_D0"
    HOLD = "HOLD"
    REBIND = "REBIND"
    REPROVE = "REPROVE"


@dataclass(frozen=True)
class AdmissionDecision:
    disposition: AdmissionDisposition
    reason: str
    admission_root: str | None = None
    authority: str = D0
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if self.admission_root is not None:
            _root(self.admission_root, "admission_root")
        if self.authority != D0 or self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("bridge decision cannot mint authority")


def sign_authorization(payload: Mapping[str, object], key: bytes) -> str:
    return hmac.new(key, canon(dict(payload)), sha256).hexdigest()


def issue_authorization_receipt(*, producer: ProducerTeccEvidence, consumer: ConsumerAdmissionEvidence,
                                ident: Any, intent: Any, contract: Any,
                                authority_scope_root: str, authority_epoch: int,
                                expires_at: int, verifier_instance: str,
                                key: bytes, authorized: bool = True) -> TeccAuthorizationReceipt:
    op = operation_identity_root(ident, intent, contract)
    fields = {
        "schema": TECC_SCHEMA,
        "tecc_input_root": producer.tecc_input_root,
        "consumer_admission_root": consumer.admission_root,
        "operation_identity_root": op,
        "intent_root": getattr(intent, "identity_root", None),
        "effect_payload_root": getattr(intent, "effect_payload_root", None),
        "contract_root": getattr(contract, "contract_root", None),
        "authority_scope_root": authority_scope_root,
        "authority_epoch": authority_epoch,
        "expires_at": expires_at,
        "verifier_instance": verifier_instance,
        "authorized": authorized,
    }
    return TeccAuthorizationReceipt(**fields, signature=sign_authorization(fields, key))


def validate_effect_admission(*, producer: ProducerTeccEvidence, consumer: ConsumerAdmissionEvidence,
                              authorization: TeccAuthorizationReceipt, ident: Any, intent: Any,
                              contract: Any, ctx: AdmissionAtUseContext,
                              registry: TeccVerifierRegistry) -> AdmissionDecision:
    if producer.producer_schema != ctx.expected_producer_schema:
        return AdmissionDecision(AdmissionDisposition.REPROVE, "PRODUCER_SCHEMA_MOVED")
    if producer.required_verifier_schema != TECC_SCHEMA:
        return AdmissionDecision(AdmissionDisposition.REPROVE, "PRODUCER_VERIFIER_SCHEMA_MOVED")
    if digest(producer.payload()) != producer.receipt_root:
        return AdmissionDecision(AdmissionDisposition.HOLD, "PRODUCER_RECEIPT_FORGED")
    if (producer.producer_semantic_head, producer.receipt_root, producer.proof_generation_root,
        producer.proof_semantics_id, producer.producer_lineage, producer.tecc_input_root,
        producer.effect_escalation_root) != (ctx.producer_semantic_head, ctx.producer_receipt_root,
        ctx.proof_generation_root, ctx.proof_semantics_id, ctx.producer_lineage,
        ctx.tecc_input_root, ctx.effect_escalation_root):
        return AdmissionDecision(AdmissionDisposition.REPROVE, "PRODUCER_SEMANTIC_OR_PROOF_IDENTITY_MOVED")
    if producer.authority_minted or producer.mutation_authority or producer.effect_authority or producer.gate10:
        return AdmissionDecision(AdmissionDisposition.HOLD, "PRODUCER_AUTHORITY_WIDENED")
    if consumer.schema != ctx.expected_consumer_schema:
        return AdmissionDecision(AdmissionDisposition.REPROVE, "CONSUMER_SCHEMA_MOVED")
    if consumer.disposition != "BIND_TECC_CONSUMER_D0":
        return AdmissionDecision(AdmissionDisposition.HOLD, "TECC_CONSUMER_NOT_ELIGIBLE")
    if digest(consumer.payload()) != consumer.admission_root:
        return AdmissionDecision(AdmissionDisposition.HOLD, "CONSUMER_ADMISSION_FORGED")
    if consumer.producer_receipt_root != producer.receipt_root or consumer.tecc_input_root != producer.tecc_input_root:
        return AdmissionDecision(AdmissionDisposition.REPROVE, "PRODUCER_CONSUMER_BINDING_MOVED")
    if consumer.observer_lineage == producer.producer_lineage:
        return AdmissionDecision(AdmissionDisposition.HOLD, "NONINDEPENDENT_CONSUMER_OBSERVER")
    if consumer.consumer_generation != ctx.consumer_generation:
        return AdmissionDecision(AdmissionDisposition.REPROVE, "CONSUMER_GENERATION_MOVED")
    if consumer.currentness_root != ctx.currentness_root or consumer.verifier_instance != ctx.verifier_instance:
        return AdmissionDecision(AdmissionDisposition.REBIND, "CONSUMER_CURRENTNESS_MOVED")
    if consumer.authority_minted or consumer.effect_authority or consumer.gate10:
        return AdmissionDecision(AdmissionDisposition.HOLD, "CONSUMER_AUTHORITY_WIDENED")
    if authorization.schema != TECC_SCHEMA:
        return AdmissionDecision(AdmissionDisposition.REPROVE, "TECC_AUTH_SCHEMA_MOVED")
    expected_sig = sign_authorization(authorization.payload(), registry.authorization_key)
    if not hmac.compare_digest(authorization.signature, expected_sig):
        return AdmissionDecision(AdmissionDisposition.HOLD, "TECC_AUTH_FORGED")
    if not authorization.authorized:
        return AdmissionDecision(AdmissionDisposition.HOLD, "TECC_NOT_AUTHORIZED")
    if authorization.verifier_instance != ctx.verifier_instance:
        return AdmissionDecision(AdmissionDisposition.REBIND, "TECC_VERIFIER_INSTANCE_MOVED")
    if authorization.authority_scope_root != ctx.authority_scope_root or authorization.authority_epoch != ctx.authority_epoch:
        return AdmissionDecision(AdmissionDisposition.REBIND, "TECC_AUTHORITY_CURRENTNESS_MOVED")
    if ctx.now >= authorization.expires_at:
        return AdmissionDecision(AdmissionDisposition.HOLD, "TECC_AUTHORIZATION_EXPIRED")
    op = operation_identity_root(ident, intent, contract)
    checks = (
        (authorization.tecc_input_root, producer.tecc_input_root, "TECC_INPUT_ROOT_MOVED"),
        (authorization.consumer_admission_root, consumer.admission_root, "TECC_CONSUMER_ROOT_MOVED"),
        (authorization.operation_identity_root, op, "OPERATION_IDENTITY_MOVED"),
        (authorization.intent_root, getattr(intent, "identity_root", None), "INTENT_ROOT_MOVED"),
        (authorization.effect_payload_root, getattr(intent, "effect_payload_root", None), "EFFECT_PAYLOAD_ROOT_MOVED"),
        (authorization.contract_root, getattr(contract, "contract_root", None), "EFFECT_CONTRACT_ROOT_MOVED"),
        (producer.intent_root, getattr(intent, "identity_root", None), "PRODUCER_INTENT_ROOT_MOVED"),
        (producer.effect_payload_root, getattr(intent, "effect_payload_root", None), "PRODUCER_EFFECT_PAYLOAD_MOVED"),
    )
    for observed, expected, reason in checks:
        if observed != expected:
            return AdmissionDecision(AdmissionDisposition.REPROVE, reason)
    root = digest({
        "schema": BRIDGE_SCHEMA,
        "kind": "proof_bound_effect_admission",
        "operation_identity_root": op,
        "producer_receipt_root": producer.receipt_root,
        "tecc_input_root": producer.tecc_input_root,
        "effect_escalation_root": producer.effect_escalation_root,
        "consumer_admission_root": consumer.admission_root,
        "authorization_receipt_root": authorization.receipt_root,
        "registry_root": registry.registry_root,
        "authority": D0,
        "authority_minted": False,
        "effect_authority": False,
        "gate10": False,
    })
    return AdmissionDecision(AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0,
                             "EXACT_TECC_AUTHORIZATION_BOUND_TO_EFFECT_ATTEMPT", root)


@dataclass(frozen=True)
class ProofBoundProviderActionPermit:
    parent_permit: Any
    proof_bound_admission_root: str
    tecc_input_root: str
    consumer_admission_root: str
    authorization_receipt_root: str
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for n in ("proof_bound_admission_root", "tecc_input_root", "consumer_admission_root", "authorization_receipt_root"):
            _root(getattr(self, n), n)
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("proof-bound permit cannot mint authority")


def _journal_schema(journal: Any) -> str | None:
    explicit = getattr(journal, "schema", None)
    if isinstance(explicit, str):
        return explicit
    try:
        mod = importlib.import_module(journal.__class__.__module__)
    except Exception:
        return None
    value = getattr(mod, "SCHEMA", None)
    return value if isinstance(value, str) else None


class ProofBoundEffectAttemptJournal:
    """Non-owning safety membrane over PR899 EffectAttemptJournal.

    The legacy journal row and TECC admission sidecar are separate durable writes.
    A crash between them is fail-closed: provider progression through this membrane
    requires the sidecar. This reference deliberately does not claim cross-store
    atomicity or production key management.
    """

    def __init__(self, journal: Any):
        self.journal = journal
        self.path = str(getattr(journal, "path"))
        self.owner_journal_schema = _journal_schema(journal)
        con = sqlite3.connect(self.path)
        try:
            con.execute("""CREATE TABLE IF NOT EXISTS tecc_admission(
                command_id TEXT PRIMARY KEY,
                owner_journal_schema TEXT NOT NULL,
                operation_identity_root TEXT NOT NULL,
                producer_receipt_root TEXT NOT NULL,
                tecc_input_root TEXT NOT NULL,
                effect_escalation_root TEXT NOT NULL,
                consumer_admission_root TEXT NOT NULL,
                authorization_receipt_root TEXT NOT NULL,
                proof_bound_admission_root TEXT NOT NULL
            )""")
            con.commit()
        finally:
            con.close()

    def _sidecar(self, command_id: str) -> dict[str, str] | None:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            row = con.execute("SELECT * FROM tecc_admission WHERE command_id=?", (command_id,)).fetchone()
            return dict(row) if row is not None else None
        finally:
            con.close()

    def _parent_row_exact(self, ident: Any, intent: Any, contract: Any) -> tuple[bool, str, dict[str, Any]]:
        try:
            row = self.journal.status(getattr(ident, "command_id"))
        except Exception:
            return False, "PARENT_EFFECT_ROW_REQUIRED", {}
        if self.owner_journal_schema != OWNER_JOURNAL_SCHEMA:
            return False, "PARENT_JOURNAL_SCHEMA_MOVED", row
        expected = {
            "idempotency_key": getattr(ident, "idempotency_key", None),
            "source_file_id": getattr(ident, "source_file_id", None),
            "source_revision": getattr(ident, "source_revision", None),
            "source_digest": getattr(ident, "source_digest", None),
            "intent_root": getattr(intent, "identity_root", None),
            "contract_root": getattr(contract, "contract_root", None),
            "effect_payload_root": getattr(intent, "effect_payload_root", None),
        }
        for k, v in expected.items():
            if row.get(k) != v:
                return False, "PARENT_EFFECT_LINEAGE_MOVED", row
        return True, "PARENT_EFFECT_LINEAGE_CURRENT", row

    def bind_verified(self, ident: Any, intent: Any, contract: Any, *,
                      producer: ProducerTeccEvidence, consumer: ConsumerAdmissionEvidence,
                      authorization: TeccAuthorizationReceipt, ctx: AdmissionAtUseContext,
                      registry: TeccVerifierRegistry) -> AdmissionDecision:
        decision = validate_effect_admission(producer=producer, consumer=consumer,
            authorization=authorization, ident=ident, intent=intent, contract=contract,
            ctx=ctx, registry=registry)
        if decision.disposition is not AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0:
            return decision
        assert decision.admission_root is not None
        self.journal.bind_admitted(ident, intent, contract)
        parent_ok, parent_reason, parent_row = self._parent_row_exact(ident, intent, contract)
        if not parent_ok:
            return AdmissionDecision(AdmissionDisposition.REPROVE, parent_reason)
        existing_sidecar = self._sidecar(getattr(ident, "command_id"))
        if existing_sidecar is None and (
            parent_row.get("phase") != "DECIDED_ADMITTED"
            or int(parent_row.get("provider_request_count", 0) or 0) != 0
            or parent_row.get("effect_attempt_root") is not None
        ):
            return AdmissionDecision(AdmissionDisposition.HOLD, "RETROACTIVE_TECC_BIND_FORBIDDEN")
        row = (
            getattr(ident, "command_id"), OWNER_JOURNAL_SCHEMA, operation_identity_root(ident, intent, contract),
            producer.receipt_root, producer.tecc_input_root, producer.effect_escalation_root,
            consumer.admission_root, authorization.receipt_root, decision.admission_root,
        )
        con = sqlite3.connect(self.path)
        try:
            con.execute("BEGIN IMMEDIATE")
            old = con.execute("SELECT * FROM tecc_admission WHERE command_id=?", (row[0],)).fetchone()
            if old is None:
                con.execute("INSERT INTO tecc_admission VALUES(?,?,?,?,?,?,?,?,?)", row)
            elif tuple(old) != row:
                raise ValueError("TECC_ADMISSION_EQUIVOCATION")
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return decision

    def _require_sidecar_current(self, ident: Any, intent: Any, contract: Any, *,
                                 producer: ProducerTeccEvidence, consumer: ConsumerAdmissionEvidence,
                                 authorization: TeccAuthorizationReceipt, ctx: AdmissionAtUseContext,
                                 registry: TeccVerifierRegistry) -> tuple[AdmissionDecision, dict[str, str]]:
        row = self._sidecar(getattr(ident, "command_id"))
        if row is None:
            return AdmissionDecision(AdmissionDisposition.HOLD, "TECC_ADMISSION_REQUIRED"), {}
        parent_ok, parent_reason, _ = self._parent_row_exact(ident, intent, contract)
        if not parent_ok:
            return AdmissionDecision(AdmissionDisposition.REPROVE, parent_reason), row
        decision = validate_effect_admission(producer=producer, consumer=consumer,
            authorization=authorization, ident=ident, intent=intent, contract=contract,
            ctx=ctx, registry=registry)
        if decision.disposition is not AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0:
            return decision, row
        expected = {
            "owner_journal_schema": OWNER_JOURNAL_SCHEMA,
            "operation_identity_root": operation_identity_root(ident, intent, contract),
            "producer_receipt_root": producer.receipt_root,
            "tecc_input_root": producer.tecc_input_root,
            "effect_escalation_root": producer.effect_escalation_root,
            "consumer_admission_root": consumer.admission_root,
            "authorization_receipt_root": authorization.receipt_root,
            "proof_bound_admission_root": decision.admission_root,
        }
        for k, v in expected.items():
            if row.get(k) != v:
                return AdmissionDecision(AdmissionDisposition.REPROVE, "DURABLE_TECC_ADMISSION_MOVED"), row
        return decision, row

    def prepare_ack(self, ident: Any, intent: Any, contract: Any, *, producer: ProducerTeccEvidence,
                    consumer: ConsumerAdmissionEvidence, authorization: TeccAuthorizationReceipt,
                    ctx: AdmissionAtUseContext, registry: TeccVerifierRegistry):
        decision, _ = self._require_sidecar_current(ident, intent, contract, producer=producer,
            consumer=consumer, authorization=authorization, ctx=ctx, registry=registry)
        if decision.disposition is not AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0:
            raise ValueError(decision.reason)
        return self.journal.prepare_ack(ident, intent, contract)

    def decide_and_persist(self, ident: Any, intent: Any, contract: Any, recovery_context: Any, *,
                           producer: ProducerTeccEvidence, consumer: ConsumerAdmissionEvidence,
                           authorization: TeccAuthorizationReceipt, ctx: AdmissionAtUseContext,
                           registry: TeccVerifierRegistry) -> ProofBoundProviderActionPermit:
        decision, row = self._require_sidecar_current(ident, intent, contract, producer=producer,
            consumer=consumer, authorization=authorization, ctx=ctx, registry=registry)
        if decision.disposition is not AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0:
            raise ValueError(decision.reason)
        parent = self.journal.decide_and_persist(ident, intent, contract, recovery_context)
        return ProofBoundProviderActionPermit(parent, row["proof_bound_admission_root"],
            row["tecc_input_root"], row["consumer_admission_root"], row["authorization_receipt_root"])

    def record_result(self, *args, **kwargs):
        return self.journal.record_result(*args, **kwargs)

    def record_ambiguous(self, *args, **kwargs):
        return self.journal.record_ambiguous(*args, **kwargs)

    def stage_final_terminal(self, *args, **kwargs):
        return self.journal.stage_final_terminal(*args, **kwargs)

    def mark_return_written(self, *args, **kwargs):
        return self.journal.mark_return_written(*args, **kwargs)
