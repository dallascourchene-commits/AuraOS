"""Mission-owned completion evidence membrane for the Arena WorkGraph.

This is a D0/reference composition layer. It does not interpret mission-specific
acceptance semantics and it does not create a second scheduler or evidence owner.
A production resolver must supply the owner policy/attestation from the mission
evidence plane. The membrane only proves exact structural binding before delegating
a COMPLETE transition to the existing WorkGraph owner.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from aura_arena_workgraph import apply_action, project_workgraph

POLICY_SCHEMA = "MissionCompletionPolicyBindingV1"
ATTESTATION_SCHEMA = "MissionCompletionAttestationV1"
ADMISSION_SCHEMA = "MissionCompletionAdmissionV1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CompletionEvidenceError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class CompletionDisposition(str, Enum):
    SATISFIED = "SATISFIED"
    NOT_REQUIRED = "NOT_REQUIRED"
    BLOCKED = "BLOCKED"


class EvidenceDomain(str, Enum):
    MISSION_COMPLETION = "MISSION_COMPLETION"
    REVIEW_CONTEXT = "REVIEW_CONTEXT"
    REVIEW_ADJUDICATION = "REVIEW_ADJUDICATION"
    MODEL_PREFIX_KV = "MODEL_PREFIX_KV"
    EXECUTION_OBSERVATION = "EXECUTION_OBSERVATION"
    UNKNOWN = "UNKNOWN"


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompletionEvidenceError(code)
    return value.strip()


def _sha(value: object, code: str) -> str:
    value = _text(value, code).lower()
    if not _SHA256.fullmatch(value):
        raise CompletionEvidenceError(code)
    return value


def _strict_bool(value: object, code: str) -> bool:
    if type(value) is not bool:
        raise CompletionEvidenceError(code)
    return value


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CompletionEvidenceError("NONCANONICAL_COMPLETION_EVIDENCE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _refs(values: Sequence[str], code: str) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise CompletionEvidenceError(code)
    out = tuple(sorted({_text(v, code) for v in values}))
    if not out:
        raise CompletionEvidenceError(code)
    return out


def _digests(values: Sequence[str], code: str) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise CompletionEvidenceError(code)
    out = tuple(sorted({_sha(v, code) for v in values}))
    if not out:
        raise CompletionEvidenceError(code)
    return out


@dataclass(frozen=True)
class MissionCompletionPolicyBindingV1:
    policy_ref: str
    policy_generation: str
    policy_currentness_ref: str
    mission_ref: str
    trusted_attestation_issuer_refs: tuple[str, ...]
    allows_not_required: bool = False
    schema: str = POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != POLICY_SCHEMA:
            raise CompletionEvidenceError("COMPLETION_POLICY_SCHEMA_MISMATCH")
        for field in ("policy_ref", "policy_generation", "policy_currentness_ref", "mission_ref"):
            object.__setattr__(self, field, _text(getattr(self, field), f"{field.upper()}_INVALID"))
        object.__setattr__(
            self,
            "trusted_attestation_issuer_refs",
            _refs(self.trusted_attestation_issuer_refs, "TRUSTED_ATTESTATION_ISSUERS_REQUIRED"),
        )
        _strict_bool(self.allows_not_required, "ALLOWS_NOT_REQUIRED_BOOL_REQUIRED")

    @property
    def policy_digest(self) -> str:
        return _digest("MISSION_COMPLETION_POLICY_BINDING_V1", asdict(self))


@dataclass(frozen=True)
class MissionCompletionAttestationV1:
    issuer_ref: str
    issuer_generation: str
    policy_ref: str
    policy_generation: str
    policy_currentness_ref: str
    project_id: str
    mission_ref: str
    cell_id: str
    claim_id: str
    worker_id: str
    graph_digest: str
    currentness_ref: str
    candidate_ref: str
    candidate_digest: str
    acceptance_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    evidence_digests: tuple[str, ...]
    evidence_domain: EvidenceDomain
    disposition: CompletionDisposition
    schema: str = ATTESTATION_SCHEMA
    effect_authorized: bool = False
    execution_verified: bool = False
    review_pass_proven: bool = False

    def __post_init__(self) -> None:
        if self.schema != ATTESTATION_SCHEMA:
            raise CompletionEvidenceError("COMPLETION_ATTESTATION_SCHEMA_MISMATCH")
        for field in (
            "issuer_ref", "issuer_generation", "policy_ref", "policy_generation",
            "policy_currentness_ref", "project_id", "mission_ref", "cell_id", "claim_id",
            "worker_id", "graph_digest", "currentness_ref", "candidate_ref",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), f"{field.upper()}_INVALID"))
        object.__setattr__(self, "candidate_digest", _sha(self.candidate_digest, "CANDIDATE_DIGEST_INVALID"))
        object.__setattr__(self, "acceptance_refs", _refs(self.acceptance_refs, "ATTESTED_ACCEPTANCE_REFS_REQUIRED"))
        object.__setattr__(self, "output_refs", _refs(self.output_refs, "ATTESTED_OUTPUT_REFS_REQUIRED"))
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, "MISSION_EVIDENCE_REFS_REQUIRED"))
        object.__setattr__(self, "evidence_digests", _digests(self.evidence_digests, "MISSION_EVIDENCE_DIGESTS_INVALID"))
        if not isinstance(self.evidence_domain, EvidenceDomain):
            raise CompletionEvidenceError("MISSION_EVIDENCE_DOMAIN_INVALID")
        if not isinstance(self.disposition, CompletionDisposition):
            raise CompletionEvidenceError("COMPLETION_DISPOSITION_INVALID")
        for field in ("effect_authorized", "execution_verified", "review_pass_proven"):
            if getattr(self, field) is not False:
                raise CompletionEvidenceError("ATTESTATION_AUTHORITY_WIDENING", field)

    @property
    def attestation_digest(self) -> str:
        value = asdict(self)
        value["evidence_domain"] = self.evidence_domain.value
        value["disposition"] = self.disposition.value
        return _digest("MISSION_COMPLETION_ATTESTATION_V1", value)


def _exact_active_claim(projection: Mapping[str, Any], *, cell_id: str, worker_id: str) -> Mapping[str, Any]:
    cells = [c for c in projection.get("cells", ()) if c.get("cell_id") == cell_id]
    if len(cells) != 1:
        raise CompletionEvidenceError("COMPLETION_CELL_NOT_EXACT")
    cell = cells[0]
    if cell.get("effective_state") != "CLAIMED":
        raise CompletionEvidenceError("COMPLETION_CELL_NOT_CLAIMED")
    claims = [
        c for c in cell.get("active_claims", ())
        if c.get("worker_id") == worker_id and c.get("active", True) is True
    ]
    if len(claims) != 1:
        raise CompletionEvidenceError("COMPLETION_ACTIVE_CLAIM_NOT_EXACT")
    return claims[0]


def admit_mission_completion(
    *,
    projection: Mapping[str, Any],
    policy: MissionCompletionPolicyBindingV1,
    attestation: MissionCompletionAttestationV1,
    worker_id: str,
    cell_id: str,
    acceptance_refs: Sequence[str],
    output_refs: Sequence[str],
) -> Mapping[str, Any]:
    if not isinstance(projection, Mapping) or projection.get("schema") != "AuraArenaWorkGraphProjectionV1":
        raise CompletionEvidenceError("WORKGRAPH_PROJECTION_REQUIRED")
    if not isinstance(policy, MissionCompletionPolicyBindingV1):
        raise CompletionEvidenceError("MISSION_COMPLETION_POLICY_REQUIRED")
    if not isinstance(attestation, MissionCompletionAttestationV1):
        raise CompletionEvidenceError("MISSION_COMPLETION_ATTESTATION_REQUIRED")

    worker_id = _text(worker_id, "COMPLETION_WORKER_REQUIRED")
    cell_id = _text(cell_id, "COMPLETION_CELL_REQUIRED")
    submitted_acceptance = _refs(acceptance_refs, "COMPLETE_ACCEPTANCE_REFS_REQUIRED")
    submitted_outputs = _refs(output_refs, "COMPLETE_OUTPUT_REFS_REQUIRED")
    claim = _exact_active_claim(projection, cell_id=cell_id, worker_id=worker_id)

    if policy.mission_ref != projection.get("mission_ref"):
        raise CompletionEvidenceError("COMPLETION_POLICY_MISSION_MISMATCH")
    if attestation.issuer_ref not in policy.trusted_attestation_issuer_refs:
        raise CompletionEvidenceError("COMPLETION_ATTESTATION_ISSUER_UNTRUSTED")
    for field in ("policy_ref", "policy_generation", "policy_currentness_ref"):
        if getattr(attestation, field) != getattr(policy, field):
            raise CompletionEvidenceError("COMPLETION_POLICY_BINDING_MISMATCH", field)
    if attestation.project_id != projection.get("project_id"):
        raise CompletionEvidenceError("COMPLETION_PROJECT_MISMATCH")
    if attestation.mission_ref != projection.get("mission_ref"):
        raise CompletionEvidenceError("COMPLETION_MISSION_MISMATCH")
    if attestation.cell_id != cell_id or attestation.worker_id != worker_id:
        raise CompletionEvidenceError("COMPLETION_SUBJECT_MISMATCH")
    if attestation.claim_id != claim.get("claim_id"):
        raise CompletionEvidenceError("COMPLETION_CLAIM_MISMATCH")
    if attestation.graph_digest != projection.get("graph_digest"):
        raise CompletionEvidenceError("COMPLETION_GRAPH_STALE")
    if attestation.currentness_ref != projection.get("currentness_ref"):
        raise CompletionEvidenceError("COMPLETION_CURRENTNESS_STALE")
    if attestation.acceptance_refs != submitted_acceptance:
        raise CompletionEvidenceError("COMPLETION_ACCEPTANCE_REFS_MISMATCH")
    if attestation.output_refs != submitted_outputs:
        raise CompletionEvidenceError("COMPLETION_OUTPUT_REFS_MISMATCH")
    if attestation.evidence_domain is not EvidenceDomain.MISSION_COMPLETION:
        raise CompletionEvidenceError("COMPLETION_EVIDENCE_DOMAIN_MISMATCH")
    if attestation.disposition is CompletionDisposition.BLOCKED:
        raise CompletionEvidenceError("MISSION_COMPLETION_BLOCKED")
    if attestation.disposition is CompletionDisposition.NOT_REQUIRED and not policy.allows_not_required:
        raise CompletionEvidenceError("MISSION_COMPLETION_NOT_REQUIRED_NOT_ALLOWED")

    logical = {
        "schema": ADMISSION_SCHEMA,
        "policy_digest": policy.policy_digest,
        "attestation_digest": attestation.attestation_digest,
        "project_id": attestation.project_id,
        "mission_ref": attestation.mission_ref,
        "cell_id": cell_id,
        "claim_id": attestation.claim_id,
        "worker_id": worker_id,
        "graph_digest": attestation.graph_digest,
        "currentness_ref": attestation.currentness_ref,
        "candidate_ref": attestation.candidate_ref,
        "candidate_digest": attestation.candidate_digest,
        "acceptance_refs": submitted_acceptance,
        "output_refs": submitted_outputs,
        "evidence_domain": EvidenceDomain.MISSION_COMPLETION.value,
        "disposition": attestation.disposition.value,
        "coordination_complete_admitted": True,
        "execution_verified": False,
        "review_pass_proven": False,
        "effect_authorized": False,
        "promotion_authorized": False,
        "policy_resolution_proven_by_this_module": False,
    }
    return {
        **logical,
        "admission_digest": _digest("MISSION_COMPLETION_ADMISSION_V1", logical),
    }


def apply_complete_with_mission_evidence(
    state: Mapping[str, Any],
    *,
    policy: MissionCompletionPolicyBindingV1,
    attestation: MissionCompletionAttestationV1,
    worker_id: str,
    cell_id: str,
    acceptance_refs: Sequence[str],
    output_refs: Sequence[str],
    now_ms: int,
) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
    """Safe reference path for COMPLETE.

    The underlying WorkGraph still owns the coordination transition. This wrapper
    refuses to call it until mission-owned completion evidence is structurally
    admitted. Production integration must make this membrane non-bypassable.
    """
    projection = project_workgraph(state, now_ms=now_ms)
    admission = admit_mission_completion(
        projection=projection,
        policy=policy,
        attestation=attestation,
        worker_id=worker_id,
        cell_id=cell_id,
        acceptance_refs=acceptance_refs,
        output_refs=output_refs,
    )
    next_state, receipt = apply_action(
        state,
        action={
            "action": "COMPLETE",
            "basis_graph_digest": projection["graph_digest"],
            "cell_id": cell_id,
            "worker_id": worker_id,
            "acceptance_refs": list(acceptance_refs),
            "output_refs": list(output_refs),
        },
        now_ms=now_ms,
    )
    receipt = {
        **receipt,
        "mission_completion_admission_digest": admission["admission_digest"],
        "mission_completion_evidence_domain": EvidenceDomain.MISSION_COMPLETION.value,
        "mission_completion_policy_ref": policy.policy_ref,
        "mission_completion_attestation_digest": attestation.attestation_digest,
        "mission_semantics_interpreted_by_workgraph": False,
        "review_pass_proven": False,
        "effect_authorized": False,
        "promotion_authorized": False,
    }
    return next_state, receipt, admission
