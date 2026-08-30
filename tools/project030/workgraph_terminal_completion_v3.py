"""Owner-backed terminal-completion seam for the canonical Arena WorkGraph.

This module is an additive integration candidate on top of the current WorkGraph V1
owner. It keeps WorkGraph mission-neutral while requiring three orthogonal,
owner-backed evidence axes before a terminal COMPLETE transition is returned:
MISSION, EXECUTION and QUALITY.

Important boundary: the legacy ``aura_arena_workgraph.apply_action(COMPLETE)`` API is
still callable on the parent branch. This module cannot make that legacy entry point
non-bypassable by existing consumers without owner integration into the canonical
WorkGraph module. The regression suite therefore preserves that fact as an explicit
OWNER_INTEGRATION_REQUIRED residual rather than claiming the bypass is already gone.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from aura_arena_workgraph import apply_action, project_workgraph, state_digest

POLICY_SCHEMA = "WorkGraphCompletionPolicyV3"
ATTESTATION_SCHEMA = "WorkGraphAxisAttestationV3"
ADMISSION_SCHEMA = "WorkGraphTerminalCompletionAdmissionV3"
RECEIPT_SCHEMA = "AuraArenaWorkGraphTerminalCompletionReceiptV3"
AXES = ("MISSION", "EXECUTION", "QUALITY")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class TerminalCompletionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class AxisDisposition(str, Enum):
    SATISFIED = "SATISFIED"
    NOT_REQUIRED = "NOT_REQUIRED"
    BLOCKED = "BLOCKED"


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TerminalCompletionError(code)
    return value.strip()


def _sha(value: object, code: str) -> str:
    value = _text(value, code).lower()
    if not _SHA256.fullmatch(value):
        raise TerminalCompletionError(code)
    return value


def _refs(values: Sequence[str], code: str) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise TerminalCompletionError(code)
    out = tuple(sorted({_text(v, code) for v in values}))
    if not out:
        raise TerminalCompletionError(code)
    return out


def _digests(values: Sequence[str], code: str) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise TerminalCompletionError(code)
    out = tuple(sorted({_sha(v, code) for v in values}))
    if not out:
        raise TerminalCompletionError(code)
    return out


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TerminalCompletionError("NONCANONICAL_COMPLETION_EVIDENCE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


@dataclass(frozen=True)
class AxisPolicyV3:
    axis: str
    responsibility_class: str
    evidence_domain: str
    owner_ref: str
    owner_generation: str
    owner_currentness_ref: str
    trusted_issuer_refs: tuple[str, ...]
    required: bool = True

    def __post_init__(self) -> None:
        axis = _text(self.axis, "AXIS_REQUIRED").upper()
        if axis not in AXES:
            raise TerminalCompletionError("AXIS_INVALID", axis)
        object.__setattr__(self, "axis", axis)
        for field in (
            "responsibility_class",
            "evidence_domain",
            "owner_ref",
            "owner_generation",
            "owner_currentness_ref",
        ):
            object.__setattr__(
                self, field, _text(getattr(self, field), f"AXIS_{field.upper()}_INVALID")
            )
        object.__setattr__(
            self,
            "trusted_issuer_refs",
            _refs(self.trusted_issuer_refs, "AXIS_TRUSTED_ISSUERS_REQUIRED"),
        )
        if type(self.required) is not bool:
            raise TerminalCompletionError("AXIS_REQUIRED_BOOL_REQUIRED")


@dataclass(frozen=True)
class WorkGraphCompletionPolicyV3:
    policy_ref: str
    policy_generation: str
    policy_currentness_ref: str
    project_id: str
    mission_ref: str
    cell_id: str
    workgraph_currentness_ref: str
    candidate_ref: str
    candidate_digest: str
    axes: tuple[AxisPolicyV3, ...]
    schema: str = POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != POLICY_SCHEMA:
            raise TerminalCompletionError("COMPLETION_POLICY_SCHEMA_MISMATCH")
        for field in (
            "policy_ref",
            "policy_generation",
            "policy_currentness_ref",
            "project_id",
            "mission_ref",
            "cell_id",
            "workgraph_currentness_ref",
            "candidate_ref",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), f"{field.upper()}_INVALID"))
        object.__setattr__(self, "candidate_digest", _sha(self.candidate_digest, "POLICY_CANDIDATE_DIGEST_INVALID"))
        if not isinstance(self.axes, tuple) or len(self.axes) != len(AXES):
            raise TerminalCompletionError("POLICY_EXACT_THREE_AXES_REQUIRED")
        if not all(isinstance(item, AxisPolicyV3) for item in self.axes):
            raise TerminalCompletionError("POLICY_AXIS_INVALID")
        names = [item.axis for item in self.axes]
        if sorted(names) != sorted(AXES):
            raise TerminalCompletionError("POLICY_AXIS_SET_INVALID")

    @property
    def policy_digest(self) -> str:
        return _digest("WORKGRAPH_COMPLETION_POLICY_V3", asdict(self))


@dataclass(frozen=True)
class WorkGraphAxisAttestationV3:
    axis: str
    responsibility_class: str
    evidence_domain: str
    owner_ref: str
    owner_generation: str
    owner_currentness_ref: str
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
    disposition: AxisDisposition
    schema: str = ATTESTATION_SCHEMA
    effect_authorized: bool = False
    promotion_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema != ATTESTATION_SCHEMA:
            raise TerminalCompletionError("AXIS_ATTESTATION_SCHEMA_MISMATCH")
        axis = _text(self.axis, "ATTESTATION_AXIS_REQUIRED").upper()
        if axis not in AXES:
            raise TerminalCompletionError("ATTESTATION_AXIS_INVALID", axis)
        object.__setattr__(self, "axis", axis)
        for field in (
            "responsibility_class",
            "evidence_domain",
            "owner_ref",
            "owner_generation",
            "owner_currentness_ref",
            "issuer_ref",
            "issuer_generation",
            "policy_ref",
            "policy_generation",
            "policy_currentness_ref",
            "project_id",
            "mission_ref",
            "cell_id",
            "claim_id",
            "worker_id",
            "graph_digest",
            "currentness_ref",
            "candidate_ref",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), f"ATTESTATION_{field.upper()}_INVALID"))
        object.__setattr__(self, "candidate_digest", _sha(self.candidate_digest, "ATTESTATION_CANDIDATE_DIGEST_INVALID"))
        object.__setattr__(self, "acceptance_refs", _refs(self.acceptance_refs, "ATTESTATION_ACCEPTANCE_REFS_REQUIRED"))
        object.__setattr__(self, "output_refs", _refs(self.output_refs, "ATTESTATION_OUTPUT_REFS_REQUIRED"))
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, "ATTESTATION_EVIDENCE_REFS_REQUIRED"))
        object.__setattr__(self, "evidence_digests", _digests(self.evidence_digests, "ATTESTATION_EVIDENCE_DIGESTS_INVALID"))
        if not isinstance(self.disposition, AxisDisposition):
            raise TerminalCompletionError("ATTESTATION_DISPOSITION_INVALID")
        if self.effect_authorized is not False or self.promotion_authorized is not False:
            raise TerminalCompletionError("ATTESTATION_AUTHORITY_WIDENING")

    @property
    def attestation_digest(self) -> str:
        value = asdict(self)
        value["disposition"] = self.disposition.value
        return _digest("WORKGRAPH_AXIS_ATTESTATION_V3", value)


def _exact_cell_claim(projection: Mapping[str, Any], *, cell_id: str, worker_id: str):
    cells = [row for row in projection.get("cells", ()) if row.get("cell_id") == cell_id]
    if len(cells) != 1 or cells[0].get("effective_state") != "CLAIMED":
        raise TerminalCompletionError("COMPLETION_CELL_NOT_EXACTLY_CLAIMED")
    claims = [
        row for row in cells[0].get("active_claims", ())
        if row.get("worker_id") == worker_id and row.get("active", True) is True
    ]
    if len(claims) != 1:
        raise TerminalCompletionError("COMPLETION_ACTIVE_CLAIM_NOT_EXACT")
    return cells[0], claims[0]


def admit_terminal_completion_v3(
    *,
    projection: Mapping[str, Any],
    policy: WorkGraphCompletionPolicyV3,
    attestations: Sequence[WorkGraphAxisAttestationV3],
    worker_id: str,
    cell_id: str,
    acceptance_refs: Sequence[str],
    output_refs: Sequence[str],
) -> Mapping[str, Any]:
    if not isinstance(projection, Mapping) or projection.get("schema") != "AuraArenaWorkGraphProjectionV1":
        raise TerminalCompletionError("WORKGRAPH_PROJECTION_REQUIRED")
    if not isinstance(policy, WorkGraphCompletionPolicyV3):
        raise TerminalCompletionError("WORKGRAPH_COMPLETION_POLICY_REQUIRED")
    worker_id = _text(worker_id, "COMPLETION_WORKER_REQUIRED")
    cell_id = _text(cell_id, "COMPLETION_CELL_REQUIRED")
    acceptance = _refs(acceptance_refs, "COMPLETE_ACCEPTANCE_REFS_REQUIRED")
    outputs = _refs(output_refs, "COMPLETE_OUTPUT_REFS_REQUIRED")
    _, claim = _exact_cell_claim(projection, cell_id=cell_id, worker_id=worker_id)

    if policy.project_id != projection.get("project_id"):
        raise TerminalCompletionError("COMPLETION_POLICY_PROJECT_MISMATCH")
    if policy.mission_ref != projection.get("mission_ref"):
        raise TerminalCompletionError("COMPLETION_POLICY_MISSION_MISMATCH")
    if policy.cell_id != cell_id:
        raise TerminalCompletionError("COMPLETION_POLICY_CELL_MISMATCH")
    if policy.workgraph_currentness_ref != projection.get("currentness_ref"):
        raise TerminalCompletionError("COMPLETION_POLICY_CURRENTNESS_STALE")

    if isinstance(attestations, (str, bytes)) or not isinstance(attestations, Sequence):
        raise TerminalCompletionError("AXIS_ATTESTATIONS_REQUIRED")
    rows = tuple(attestations)
    if len(rows) != len(AXES) or not all(isinstance(item, WorkGraphAxisAttestationV3) for item in rows):
        raise TerminalCompletionError("EXACT_THREE_AXIS_ATTESTATIONS_REQUIRED")
    by_axis = {item.axis: item for item in rows}
    if sorted(by_axis) != sorted(AXES) or len(by_axis) != len(AXES):
        raise TerminalCompletionError("ATTESTATION_AXIS_SET_INVALID")
    policy_by_axis = {item.axis: item for item in policy.axes}

    admitted: dict[str, Mapping[str, Any]] = {}
    for axis in AXES:
        axis_policy = policy_by_axis[axis]
        att = by_axis[axis]
        if att.responsibility_class != axis_policy.responsibility_class:
            raise TerminalCompletionError("AXIS_RESPONSIBILITY_MISMATCH", axis)
        if att.evidence_domain != axis_policy.evidence_domain:
            raise TerminalCompletionError("AXIS_EVIDENCE_DOMAIN_MISMATCH", axis)
        if (att.owner_ref, att.owner_generation, att.owner_currentness_ref) != (
            axis_policy.owner_ref,
            axis_policy.owner_generation,
            axis_policy.owner_currentness_ref,
        ):
            raise TerminalCompletionError("AXIS_OWNER_BINDING_MISMATCH", axis)
        if att.issuer_ref not in axis_policy.trusted_issuer_refs:
            raise TerminalCompletionError("AXIS_ISSUER_UNTRUSTED", axis)
        if (att.policy_ref, att.policy_generation, att.policy_currentness_ref) != (
            policy.policy_ref,
            policy.policy_generation,
            policy.policy_currentness_ref,
        ):
            raise TerminalCompletionError("AXIS_POLICY_BINDING_MISMATCH", axis)
        exact = (
            att.project_id == policy.project_id
            and att.mission_ref == policy.mission_ref
            and att.cell_id == cell_id
            and att.claim_id == claim.get("claim_id")
            and att.worker_id == worker_id
            and att.graph_digest == projection.get("graph_digest")
            and att.currentness_ref == policy.workgraph_currentness_ref
            and att.candidate_ref == policy.candidate_ref
            and att.candidate_digest == policy.candidate_digest
            and att.acceptance_refs == acceptance
            and att.output_refs == outputs
        )
        if not exact:
            raise TerminalCompletionError("AXIS_TARGET_BINDING_MISMATCH", axis)
        if att.disposition is AxisDisposition.BLOCKED:
            raise TerminalCompletionError("AXIS_BLOCKED", axis)
        if axis_policy.required and att.disposition is not AxisDisposition.SATISFIED:
            raise TerminalCompletionError("REQUIRED_AXIS_NOT_SATISFIED", axis)
        if not axis_policy.required and att.disposition not in {
            AxisDisposition.SATISFIED,
            AxisDisposition.NOT_REQUIRED,
        }:
            raise TerminalCompletionError("OPTIONAL_AXIS_DISPOSITION_INVALID", axis)
        admitted[axis] = {
            "attestation_digest": att.attestation_digest,
            "disposition": att.disposition.value,
            "responsibility_class": att.responsibility_class,
            "evidence_domain": att.evidence_domain,
            "owner_ref": att.owner_ref,
            "owner_generation": att.owner_generation,
            "owner_currentness_ref": att.owner_currentness_ref,
            "issuer_ref": att.issuer_ref,
            "evidence_refs": list(att.evidence_refs),
            "evidence_digests": list(att.evidence_digests),
        }

    logical = {
        "schema": ADMISSION_SCHEMA,
        "policy_digest": policy.policy_digest,
        "project_id": policy.project_id,
        "mission_ref": policy.mission_ref,
        "cell_id": cell_id,
        "claim_id": claim.get("claim_id"),
        "worker_id": worker_id,
        "graph_digest": projection.get("graph_digest"),
        "currentness_ref": policy.workgraph_currentness_ref,
        "candidate_ref": policy.candidate_ref,
        "candidate_digest": policy.candidate_digest,
        "acceptance_refs": list(acceptance),
        "output_refs": list(outputs),
        "axes": admitted,
        "coordination_completion_admitted": True,
        "execution_axis_satisfied": admitted["EXECUTION"]["disposition"] == AxisDisposition.SATISFIED.value,
        "quality_axis_satisfied": admitted["QUALITY"]["disposition"] == AxisDisposition.SATISFIED.value,
        "effect_authorized": False,
        "promotion_authorized": False,
    }
    return {**logical, "admission_digest": _digest("WORKGRAPH_TERMINAL_COMPLETION_ADMISSION_V3", logical)}


def apply_terminal_completion_v3(
    state: Mapping[str, Any],
    *,
    action: Mapping[str, Any],
    policy: WorkGraphCompletionPolicyV3,
    attestations: Sequence[WorkGraphAxisAttestationV3],
    now_ms: int,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Apply a terminal transition only after exact three-axis admission.

    The legacy WorkGraph transition is used only as a pure in-memory CAS/state
    transition after V3 admission. Its unconditional execution-state promotion and
    receipt mixing are then replaced before anything is returned to a persistence
    adapter. Existing callers of raw V1 COMPLETE remain an explicit owner-integration
    blocker and are not silently claimed repaired by this child module.
    """
    if not isinstance(action, Mapping) or str(action.get("action") or "").upper() != "COMPLETE":
        raise TerminalCompletionError("V3_COMPLETE_ACTION_REQUIRED")
    projection = project_workgraph(state, now_ms=now_ms)
    worker_id = _text(action.get("worker_id"), "COMPLETION_WORKER_REQUIRED")
    cell_id = _text(action.get("cell_id"), "COMPLETION_CELL_REQUIRED")
    acceptance = action.get("acceptance_refs") or ()
    outputs = action.get("output_refs") or ()
    cell, _ = _exact_cell_claim(projection, cell_id=cell_id, worker_id=worker_id)
    prior_execution_state = cell.get("execution_state")
    prior_execution_refs = tuple(cell.get("execution_receipt_refs") or ())

    admission = admit_terminal_completion_v3(
        projection=projection,
        policy=policy,
        attestations=attestations,
        worker_id=worker_id,
        cell_id=cell_id,
        acceptance_refs=acceptance,
        output_refs=outputs,
    )

    legacy_next, _legacy_receipt = apply_action(
        state,
        action=action,
        now_ms=now_ms,
    )
    next_state = deepcopy(legacy_next)
    execution_attestation = next(item for item in attestations if item.axis == "EXECUTION")
    for row in next_state["cells"]:
        if row["cell_id"] != cell_id:
            continue
        if admission["execution_axis_satisfied"]:
            row["execution_state"] = "VERIFIED_COMPLETE"
            row["execution_receipt_refs"] = sorted(
                set(prior_execution_refs) | set(execution_attestation.evidence_refs)
            )
        else:
            row["execution_state"] = prior_execution_state
            row["execution_receipt_refs"] = sorted(set(prior_execution_refs))
        break

    body = {
        "schema": RECEIPT_SCHEMA,
        "project_id": policy.project_id,
        "mission_ref": policy.mission_ref,
        "cell_id": cell_id,
        "worker_id": worker_id,
        "basis_graph_digest": projection.get("graph_digest"),
        "before_state_digest": state_digest(state),
        "after_state_digest": state_digest(next_state),
        "currentness_ref": policy.workgraph_currentness_ref,
        "candidate_ref": policy.candidate_ref,
        "candidate_digest": policy.candidate_digest,
        "policy_digest": policy.policy_digest,
        "admission_digest": admission["admission_digest"],
        "axis_attestation_digests": {
            item.axis: item.attestation_digest for item in attestations
        },
        "execution_axis_satisfied": admission["execution_axis_satisfied"],
        "quality_axis_satisfied": admission["quality_axis_satisfied"],
        "legacy_v1_complete_entrypoint_disabled_by_this_module": False,
        "owner_integration_required": True,
        "runtime_execution_proven_by_this_module": False,
        "effect_authorized": False,
        "promotion_authorized": False,
    }
    return next_state, {**body, "receipt_digest": _digest("AURA_ARENA_WORKGRAPH_TERMINAL_COMPLETION_RECEIPT_V3", body)}
