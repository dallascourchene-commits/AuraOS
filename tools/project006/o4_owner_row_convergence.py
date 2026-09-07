from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

D0 = "D0_NONPROMOTING"
SCHEMA = "AURA-PROJECT006-O4-OWNER-ROW-CONVERGENCE-v1"


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


@dataclass(frozen=True)
class SemanticEffectIdentity:
    command_id: str
    idempotency_key: str
    source_file_id: str
    source_revision: str
    source_digest: str
    intent_root: str
    contract_root: str
    effect_payload_root: str
    recovery_mode: str


@dataclass(frozen=True)
class ProofAdmission:
    proof_bound_admission_root: str
    tecc_input_root: str
    consumer_admission_root: str
    authorization_receipt_root: str
    producer_proof_generation_root: str
    producer_proof_semantics_id: str
    consumer_generation: int
    consumer_currentness_root: str
    verifier_instance: str
    authority_scope_root: str
    authority_epoch: int
    authorization_expires_at: int
    recovery_mode: str
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for name in ("proof_bound_admission_root", "tecc_input_root", "consumer_admission_root", "authorization_receipt_root", "producer_proof_generation_root", "consumer_currentness_root", "authority_scope_root"):
            _root(getattr(self, name), name)
        if any(type(getattr(self, n)) is not int or getattr(self, n) < 0 for n in ("consumer_generation", "authority_epoch", "authorization_expires_at")):
            raise ValueError("proof generation/epoch values invalid")
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("proof admission cannot mint authority")


def stable_provider_operation_root(s: SemanticEffectIdentity) -> str:
    return digest({"schema": SCHEMA, "kind": "stable_provider_operation", "command_id": s.command_id,
        "idempotency_key": s.idempotency_key, "source_file_id": s.source_file_id,
        "source_revision": s.source_revision, "source_digest": s.source_digest,
        "intent_root": s.intent_root, "contract_root": s.contract_root,
        "effect_payload_root": s.effect_payload_root})


def proof_crossbind_root(s: SemanticEffectIdentity, a: ProofAdmission) -> str:
    return digest({"schema": SCHEMA, "kind": "proof_admission_crossbind", "command_id": s.command_id,
        "idempotency_key": s.idempotency_key, "source_file_id": s.source_file_id,
        "source_revision": s.source_revision, "source_digest": s.source_digest,
        "intent_root": s.intent_root, "contract_root": s.contract_root,
        "effect_payload_root": s.effect_payload_root, "recovery_mode": s.recovery_mode,
        "tecc_input_root": a.tecc_input_root, "consumer_admission_root": a.consumer_admission_root,
        "authorization_receipt_root": a.authorization_receipt_root,
        "producer_proof_generation_root": a.producer_proof_generation_root,
        "producer_proof_semantics_id": a.producer_proof_semantics_id,
        "consumer_generation": a.consumer_generation, "consumer_currentness_root": a.consumer_currentness_root,
        "verifier_instance": a.verifier_instance, "authority_scope_root": a.authority_scope_root,
        "authority_epoch": a.authority_epoch, "authorization_expires_at": a.authorization_expires_at})


def proof_action_currentness_root(a: ProofAdmission) -> str:
    return digest({"schema": SCHEMA, "kind": "proof_action_currentness",
        "consumer_admission_root": a.consumer_admission_root, "consumer_generation": a.consumer_generation,
        "consumer_currentness_root": a.consumer_currentness_root, "verifier_instance": a.verifier_instance,
        "authority_scope_root": a.authority_scope_root, "authority_epoch": a.authority_epoch,
        "authorization_expires_at": a.authorization_expires_at,
        "producer_proof_generation_root": a.producer_proof_generation_root,
        "producer_proof_semantics_id": a.producer_proof_semantics_id})


def validate_admission(s: SemanticEffectIdentity, a: ProofAdmission, *, now: int) -> None:
    if a.recovery_mode != s.recovery_mode:
        raise ValueError("RECOVERY_MODE_NOT_BOUND_TO_AUTHENTICATED_CONTRACT")
    if type(now) is not int or now < 0 or now >= a.authorization_expires_at:
        raise ValueError("PROOF_AUTHORIZATION_EXPIRED")
    if a.proof_bound_admission_root != proof_crossbind_root(s, a):
        raise ValueError("PROOF_ADMISSION_CROSSBIND_DIVERGED")


def owner_bound_attempt_root(*, parent_attempt_root: str, stable_root: str, admission_root: str,
        proof_currentness_root: str, provider_currentness_root: str, count: int) -> str:
    for v, n in ((parent_attempt_root,"parent_attempt_root"),(stable_root,"stable_root"),(admission_root,"admission_root"),
                 (proof_currentness_root,"proof_currentness_root"),(provider_currentness_root,"provider_currentness_root")):
        _root(v, n)
    return digest({"schema": SCHEMA, "kind": "owner_bound_effect_attempt", "parent_attempt_root": parent_attempt_root,
        "stable_provider_operation_root": stable_root, "proof_bound_admission_root": admission_root,
        "proof_action_currentness_root": proof_currentness_root,
        "provider_action_currentness_root": provider_currentness_root, "provider_request_count": count})


O4_COLUMNS = {
    "stable_provider_operation_root":"TEXT", "proof_bound_admission_root":"TEXT", "proof_action_currentness_root":"TEXT",
    "tecc_input_root":"TEXT", "consumer_admission_root":"TEXT", "authorization_receipt_root":"TEXT",
    "producer_proof_generation_root":"TEXT", "producer_proof_semantics_id":"TEXT", "consumer_generation":"INTEGER",
    "consumer_currentness_root":"TEXT", "proof_verifier_instance":"TEXT", "authority_scope_root":"TEXT",
    "authority_epoch":"INTEGER", "authorization_expires_at":"INTEGER"}


def ensure_o4_columns(con: sqlite3.Connection) -> None:
    have = {row[1] for row in con.execute("PRAGMA table_info(effect_tx)")}
    for name, ddl in O4_COLUMNS.items():
        if name not in have:
            con.execute(f"ALTER TABLE effect_tx ADD COLUMN {name} {ddl}")


def persist_owner_bound_provider_attempt(con: sqlite3.Connection, *, semantic: SemanticEffectIdentity,
        admission: ProofAdmission, now: int, parent_attempt_root: str,
        provider_action_currentness_root: str, provider_request_count: int) -> str:
    """Call inside PR899's existing BEGIN IMMEDIATE; no sidecar or second journal."""
    ensure_o4_columns(con)
    validate_admission(semantic, admission, now=now)
    _root(provider_action_currentness_root, "provider_action_currentness_root")
    row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (semantic.command_id,)).fetchone()
    if row is None:
        raise ValueError("EFFECT_COMMAND_NOT_BOUND")
    expected = (semantic.idempotency_key, semantic.source_file_id, semantic.source_revision, semantic.source_digest,
                semantic.intent_root, semantic.contract_root, semantic.effect_payload_root, semantic.recovery_mode)
    observed = tuple(row[k] for k in ("idempotency_key","source_file_id","source_revision","source_digest","intent_root","contract_root","effect_payload_root","recovery_mode"))
    if observed != expected:
        raise ValueError("OWNER_ROW_SEMANTIC_LINEAGE_DIVERGED")
    stable = stable_provider_operation_root(semantic)
    if row["stable_provider_operation_root"] not in (None, stable):
        raise ValueError("STABLE_PROVIDER_OPERATION_IDENTITY_DIVERGED")
    pc = proof_action_currentness_root(admission)
    attempt = owner_bound_attempt_root(parent_attempt_root=parent_attempt_root, stable_root=stable,
        admission_root=admission.proof_bound_admission_root, proof_currentness_root=pc,
        provider_currentness_root=provider_action_currentness_root, count=provider_request_count)
    con.execute("""UPDATE effect_tx SET phase='EFFECT_ATTEMPT_DURABLE',provider_request_count=?,effect_attempt_root=?,
        provider_action_currentness_root=?,stable_provider_operation_root=?,proof_bound_admission_root=?,
        proof_action_currentness_root=?,tecc_input_root=?,consumer_admission_root=?,authorization_receipt_root=?,
        producer_proof_generation_root=?,producer_proof_semantics_id=?,consumer_generation=?,consumer_currentness_root=?,
        proof_verifier_instance=?,authority_scope_root=?,authority_epoch=?,authorization_expires_at=? WHERE command_id=?""",
        (provider_request_count,attempt,provider_action_currentness_root,stable,admission.proof_bound_admission_root,pc,
         admission.tecc_input_root,admission.consumer_admission_root,admission.authorization_receipt_root,
         admission.producer_proof_generation_root,admission.producer_proof_semantics_id,admission.consumer_generation,
         admission.consumer_currentness_root,admission.verifier_instance,admission.authority_scope_root,
         admission.authority_epoch,admission.authorization_expires_at,semantic.command_id))
    return attempt


def provider_candidate_ready(row: sqlite3.Row, *, now: int) -> bool:
    required=("stable_provider_operation_root","proof_bound_admission_root","proof_action_currentness_root",
              "consumer_admission_root","authorization_receipt_root","provider_action_currentness_root","effect_attempt_root")
    try:
        return row["phase"] == "EFFECT_ATTEMPT_DURABLE" and all(row[k] for k in required) and now < row["authorization_expires_at"]
    except (KeyError, IndexError, TypeError):
        return False
