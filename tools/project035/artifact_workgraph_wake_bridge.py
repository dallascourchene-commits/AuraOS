"""Coordination-only AS-07 bridge from durable artifacts to canonical WorkGraph wake.

The bridge consumes an AS-06 ArtifactAvailableEventV1 *after* persistence/index CAS
and an explicit artifact->WorkGraph dependency binding. It may compile a canonical
WorkGraph REOPEN proposal, but it never mutates WorkGraph, never emits a WakeIntent,
and never grants execution/effect/provider/background authority.

A deterministic WorkGraph transition receipt is integrity evidence, not persistence
authority. Only after an injected trusted canonical-transition resolver confirms the
exact REOPEN was durably persisted/read back by the canonical WorkGraph owner may
this bridge say that the existing H-G wake scanner is allowed to rescan.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

ARTIFACT_AVAILABLE_SCHEMA = "ArtifactAvailableEventV1"
WORKGRAPH_PROJECTION_SCHEMA = "AuraArenaWorkGraphProjectionV1"
WORKGRAPH_TRANSITION_RECEIPT_SCHEMA = "AuraArenaWorkGraphTransitionReceiptV1"
WORKGRAPH_TRANSITION_EVIDENCE_SCHEMA = "CanonicalWorkGraphTransitionEvidenceV1"
BINDING_SCHEMA = "ArtifactWorkDependencyBindingV1"
PROPOSAL_SCHEMA = "ArtifactDependencyReadyProposalV1"
VERIFICATION_SCHEMA = "ArtifactDependencyTransitionVerificationV1"


class ArtifactWakeBridgeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactWakeBridgeError(code)
    return value.strip()


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ArtifactWakeBridgeError("NONCANONICAL_VALUE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactWakeBridgeError(code)
    return value


def _strict_bool(value: Any, code: str) -> bool:
    if type(value) is not bool:
        raise ArtifactWakeBridgeError(code)
    return value


def _require_zero_authority(event: Mapping[str, Any]) -> None:
    if event.get("delivery_intent_only") is not True:
        raise ArtifactWakeBridgeError("ARTIFACT_EVENT_NOT_DELIVERY_INTENT_ONLY")
    for field in (
        "execution_authorized",
        "effect_authorized",
        "provider_calls_authorized",
        "runtime_execution_proven",
        "background_execution_claimed",
    ):
        if event.get(field) is not False:
            raise ArtifactWakeBridgeError("ARTIFACT_EVENT_AUTHORITY_WIDENING", field)


@dataclass(frozen=True)
class ArtifactWorkDependencyBinding:
    project_id: str
    artifact_sid: str
    persistence_receipt_id: str
    live_index_revision: str
    currentness_ref: str
    target_cell_id: str
    target_reopen_condition: str
    basis_graph_digest: str
    binding_id: str = ""
    schema: str = BINDING_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != BINDING_SCHEMA:
            raise ArtifactWakeBridgeError("DEPENDENCY_BINDING_SCHEMA_INVALID")
        for field_name, code in (
            ("project_id", "PROJECT_ID_REQUIRED"),
            ("artifact_sid", "ARTIFACT_SID_REQUIRED"),
            ("persistence_receipt_id", "PERSISTENCE_RECEIPT_ID_REQUIRED"),
            ("live_index_revision", "LIVE_INDEX_REVISION_REQUIRED"),
            ("currentness_ref", "CURRENTNESS_REF_REQUIRED"),
            ("target_cell_id", "TARGET_CELL_ID_REQUIRED"),
            ("target_reopen_condition", "TARGET_REOPEN_CONDITION_REQUIRED"),
            ("basis_graph_digest", "BASIS_GRAPH_DIGEST_REQUIRED"),
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), code))
        expected = self.compute_binding_id()
        supplied = str(self.binding_id or "").strip()
        if supplied and supplied != expected:
            raise ArtifactWakeBridgeError("DEPENDENCY_BINDING_ID_MISMATCH")
        object.__setattr__(self, "binding_id", expected)

    def logical_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "project_id": self.project_id,
            "artifact_sid": self.artifact_sid,
            "persistence_receipt_id": self.persistence_receipt_id,
            "live_index_revision": self.live_index_revision,
            "currentness_ref": self.currentness_ref,
            "target_cell_id": self.target_cell_id,
            "target_reopen_condition": self.target_reopen_condition,
            "basis_graph_digest": self.basis_graph_digest,
        }

    def compute_binding_id(self) -> str:
        return "awdb-" + _digest("ARTIFACT_WORK_DEPENDENCY_BINDING_V1", self.logical_payload())[:32]


@dataclass(frozen=True)
class ArtifactDependencyReadyProposal:
    event_id: str
    binding_id: str
    project_id: str
    artifact_sid: str
    persistence_receipt_id: str
    live_index_revision: str
    currentness_ref: str
    target_cell_id: str
    target_reopen_condition: str
    basis_graph_digest: str
    proposal_id: str = ""
    schema: str = PROPOSAL_SCHEMA
    requested_workgraph_action: str = "REOPEN"
    requires_canonical_workgraph_transition: bool = True
    requires_admitted_worker: bool = True
    wake_scan_allowed: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    provider_calls_authorized: bool = False
    runtime_execution_proven: bool = False
    background_execution_claimed: bool = False

    def __post_init__(self) -> None:
        if self.schema != PROPOSAL_SCHEMA or self.requested_workgraph_action != "REOPEN":
            raise ArtifactWakeBridgeError("DEPENDENCY_READY_PROPOSAL_SCHEMA_INVALID")
        for field_name in (
            "event_id", "binding_id", "project_id", "artifact_sid", "persistence_receipt_id",
            "live_index_revision", "currentness_ref", "target_cell_id",
            "target_reopen_condition", "basis_graph_digest",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), f"{field_name.upper()}_REQUIRED"),
            )
        if self.requires_canonical_workgraph_transition is not True or self.requires_admitted_worker is not True:
            raise ArtifactWakeBridgeError("CANONICAL_WORKGRAPH_TRANSITION_REQUIRED")
        for field_name in (
            "wake_scan_allowed", "execution_authorized", "effect_authorized",
            "provider_calls_authorized", "runtime_execution_proven", "background_execution_claimed",
        ):
            if getattr(self, field_name) is not False:
                raise ArtifactWakeBridgeError("PROPOSAL_AUTHORITY_WIDENING", field_name)
        expected = self.compute_proposal_id()
        supplied = str(self.proposal_id or "").strip()
        if supplied and supplied != expected:
            raise ArtifactWakeBridgeError("DEPENDENCY_READY_PROPOSAL_ID_MISMATCH")
        object.__setattr__(self, "proposal_id", expected)

    def logical_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("proposal_id", None)
        return payload

    def compute_proposal_id(self) -> str:
        return "adrp-" + _digest("ARTIFACT_DEPENDENCY_READY_PROPOSAL_V1", self.logical_payload())[:32]


def _target_cell(projection: Mapping[str, Any], cell_id: str) -> Mapping[str, Any]:
    matches = [row for row in projection.get("cells", []) if isinstance(row, Mapping) and row.get("cell_id") == cell_id]
    if len(matches) != 1:
        raise ArtifactWakeBridgeError("TARGET_CELL_NOT_UNIQUE")
    return matches[0]


def compile_dependency_ready_proposal(
    *,
    artifact_event: Mapping[str, Any],
    binding: ArtifactWorkDependencyBinding,
    workgraph_projection: Mapping[str, Any],
) -> ArtifactDependencyReadyProposal:
    """Compile a REOPEN request, never the REOPEN transition itself."""
    event = _mapping(artifact_event, "ARTIFACT_EVENT_MAPPING_REQUIRED")
    projection = _mapping(workgraph_projection, "WORKGRAPH_PROJECTION_MAPPING_REQUIRED")
    if event.get("schema") != ARTIFACT_AVAILABLE_SCHEMA:
        raise ArtifactWakeBridgeError("ARTIFACT_AVAILABLE_SCHEMA_INVALID")
    _require_zero_authority(event)
    event_type = _text(event.get("event_type"), "ARTIFACT_EVENT_TYPE_REQUIRED").upper()
    if event_type == "ARTIFACT_TOMBSTONED":
        raise ArtifactWakeBridgeError("ARTIFACT_TOMBSTONED_REVIEW_REQUIRED")
    if event_type != "ARTIFACT_AVAILABLE":
        raise ArtifactWakeBridgeError("ARTIFACT_EVENT_TYPE_INVALID")
    if projection.get("schema") != WORKGRAPH_PROJECTION_SCHEMA:
        raise ArtifactWakeBridgeError("WORKGRAPH_PROJECTION_SCHEMA_INVALID")

    exact_pairs = (
        (event.get("project_id"), binding.project_id, "ARTIFACT_PROJECT_MISMATCH"),
        (event.get("artifact_sid"), binding.artifact_sid, "ARTIFACT_SID_MISMATCH"),
        (event.get("persistence_receipt_id"), binding.persistence_receipt_id, "PERSISTENCE_RECEIPT_MISMATCH"),
        (event.get("live_index_revision"), binding.live_index_revision, "LIVE_INDEX_REVISION_MISMATCH"),
        (event.get("currentness_ref"), binding.currentness_ref, "ARTIFACT_CURRENTNESS_MISMATCH"),
        (projection.get("project_id"), binding.project_id, "WORKGRAPH_PROJECT_MISMATCH"),
        (projection.get("currentness_ref"), binding.currentness_ref, "WORKGRAPH_CURRENTNESS_MISMATCH"),
        (projection.get("graph_digest"), binding.basis_graph_digest, "WORKGRAPH_BASIS_MISMATCH"),
    )
    for actual, expected, code in exact_pairs:
        if actual != expected:
            raise ArtifactWakeBridgeError(code)

    cell = _target_cell(projection, binding.target_cell_id)
    if cell.get("state") in {"COMPLETE", "SUPERSEDED"} or cell.get("effective_state") in {"COMPLETE", "SUPERSEDED"}:
        raise ArtifactWakeBridgeError("HISTORICAL_CELL_REQUIRES_SUCCESSOR")
    if cell.get("state") != "BLOCKED" or cell.get("effective_state") != "BLOCKED":
        raise ArtifactWakeBridgeError("TARGET_CELL_NOT_DECLARED_BLOCKED")
    if cell.get("execution_state") not in {"NOT_STARTED", "FAILED"}:
        raise ArtifactWakeBridgeError("RECONCILE_EFFECT_STATE_REQUIRED")
    reopen_conditions = cell.get("reopen_conditions") or []
    if binding.target_reopen_condition not in reopen_conditions:
        raise ArtifactWakeBridgeError("REOPEN_CONDITION_BINDING_MISMATCH")

    return ArtifactDependencyReadyProposal(
        event_id=_text(event.get("event_id"), "ARTIFACT_EVENT_ID_REQUIRED"),
        binding_id=binding.binding_id,
        project_id=binding.project_id,
        artifact_sid=binding.artifact_sid,
        persistence_receipt_id=binding.persistence_receipt_id,
        live_index_revision=binding.live_index_revision,
        currentness_ref=binding.currentness_ref,
        target_cell_id=binding.target_cell_id,
        target_reopen_condition=binding.target_reopen_condition,
        basis_graph_digest=binding.basis_graph_digest,
    )


def compute_workgraph_transition_receipt_digest(receipt: Mapping[str, Any]) -> str:
    """Recompute the canonical WorkGraph reference-receipt integrity digest.

    This proves deterministic receipt integrity only. It does not prove the returned
    state was persisted by the canonical WorkGraph owner.
    """
    row = _mapping(receipt, "WORKGRAPH_TRANSITION_RECEIPT_MAPPING_REQUIRED")
    if row.get("schema") != WORKGRAPH_TRANSITION_RECEIPT_SCHEMA:
        raise ArtifactWakeBridgeError("WORKGRAPH_TRANSITION_RECEIPT_SCHEMA_INVALID")
    now_ms = row.get("now_ms")
    if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
        raise ArtifactWakeBridgeError("TRANSITION_NOW_INVALID")
    body = {
        "action": _text(row.get("action"), "WORKGRAPH_TRANSITION_ACTION_REQUIRED").upper(),
        "project_id": _text(row.get("project_id"), "TRANSITION_PROJECT_REQUIRED"),
        "worker_id": _text(row.get("worker_id"), "TRANSITION_WORKER_REQUIRED"),
        "cell_id": _text(row.get("cell_id"), "TRANSITION_CELL_REQUIRED"),
        "basis_graph_digest": _text(row.get("basis_graph_digest"), "TRANSITION_BASIS_REQUIRED"),
        "before_state_digest": _text(row.get("before_state_digest"), "TRANSITION_BEFORE_STATE_REQUIRED"),
        "after_state_digest": _text(row.get("after_state_digest"), "TRANSITION_AFTER_STATE_REQUIRED"),
        "after_graph_digest": _text(row.get("after_graph_digest"), "TRANSITION_AFTER_GRAPH_REQUIRED"),
        "now_ms": now_ms,
    }
    return _digest("AURA_ARENA_WORKGRAPH_TRANSITION_RECEIPT_V1", body)


def _resolve_canonical_transition_evidence(
    *,
    resolver: Callable[[str], Mapping[str, Any]] | None,
    transition_receipt: Mapping[str, Any],
    proposal: ArtifactDependencyReadyProposal,
    after_projection: Mapping[str, Any],
) -> Mapping[str, Any]:
    if resolver is None or not callable(resolver):
        raise ArtifactWakeBridgeError("CANONICAL_TRANSITION_EVIDENCE_RESOLVER_REQUIRED")

    expected_digest = compute_workgraph_transition_receipt_digest(transition_receipt)
    supplied_digest = _text(
        transition_receipt.get("receipt_digest"), "TRANSITION_RECEIPT_DIGEST_REQUIRED"
    )
    if supplied_digest != expected_digest:
        raise ArtifactWakeBridgeError("TRANSITION_RECEIPT_DIGEST_MISMATCH")

    evidence = _mapping(
        resolver(expected_digest), "CANONICAL_TRANSITION_EVIDENCE_MAPPING_REQUIRED"
    )
    if evidence.get("schema") != WORKGRAPH_TRANSITION_EVIDENCE_SCHEMA:
        raise ArtifactWakeBridgeError("CANONICAL_TRANSITION_EVIDENCE_SCHEMA_INVALID")
    if evidence.get("status") != "VERIFIED_PERSISTED_TRANSITION":
        raise ArtifactWakeBridgeError("CANONICAL_TRANSITION_NOT_PERSISTED")
    if _strict_bool(
        evidence.get("persistence_verified"), "CANONICAL_PERSISTENCE_VERIFIED_BOOLEAN_REQUIRED"
    ) is not True:
        raise ArtifactWakeBridgeError("CANONICAL_TRANSITION_NOT_PERSISTED")
    if _strict_bool(
        evidence.get("readback_verified"), "CANONICAL_READBACK_VERIFIED_BOOLEAN_REQUIRED"
    ) is not True:
        raise ArtifactWakeBridgeError("CANONICAL_TRANSITION_READBACK_REQUIRED")

    for field_name, code in (
        ("canonical_workgraph_owner_ref", "CANONICAL_WORKGRAPH_OWNER_REF_REQUIRED"),
        ("canonical_store_ref", "CANONICAL_WORKGRAPH_STORE_REF_REQUIRED"),
        ("persistence_verification_ref", "TRANSITION_PERSISTENCE_VERIFICATION_REF_REQUIRED"),
        ("readback_ref", "TRANSITION_READBACK_REF_REQUIRED"),
    ):
        _text(evidence.get(field_name), code)

    exact_pairs = (
        (evidence.get("transition_receipt_digest"), expected_digest, "CANONICAL_EVIDENCE_RECEIPT_DIGEST_MISMATCH"),
        (evidence.get("project_id"), proposal.project_id, "CANONICAL_EVIDENCE_PROJECT_MISMATCH"),
        (evidence.get("cell_id"), proposal.target_cell_id, "CANONICAL_EVIDENCE_CELL_MISMATCH"),
        (evidence.get("currentness_ref"), proposal.currentness_ref, "CANONICAL_EVIDENCE_CURRENTNESS_MISMATCH"),
        (evidence.get("basis_graph_digest"), proposal.basis_graph_digest, "CANONICAL_EVIDENCE_BASIS_MISMATCH"),
        (evidence.get("before_state_digest"), transition_receipt.get("before_state_digest"), "CANONICAL_EVIDENCE_BEFORE_STATE_MISMATCH"),
        (evidence.get("after_state_digest"), transition_receipt.get("after_state_digest"), "CANONICAL_EVIDENCE_AFTER_STATE_MISMATCH"),
        (evidence.get("after_graph_digest"), transition_receipt.get("after_graph_digest"), "CANONICAL_EVIDENCE_AFTER_GRAPH_MISMATCH"),
        (evidence.get("after_graph_digest"), after_projection.get("graph_digest"), "CANONICAL_READBACK_GRAPH_MISMATCH"),
    )
    for actual, expected, code in exact_pairs:
        if actual != expected:
            raise ArtifactWakeBridgeError(code)

    for field in (
        "execution_authorized",
        "effect_authorized",
        "provider_calls_authorized",
        "runtime_execution_proven",
        "background_execution_claimed",
    ):
        if evidence.get(field) is not False:
            raise ArtifactWakeBridgeError("CANONICAL_TRANSITION_EVIDENCE_AUTHORITY_WIDENING", field)
    return evidence


def verify_canonical_reopen_transition(
    *,
    proposal: ArtifactDependencyReadyProposal,
    transition_receipt: Mapping[str, Any],
    after_projection: Mapping[str, Any],
    canonical_transition_resolver: Callable[[str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify persisted canonical REOPEN evidence before allowing the H-G wake scan."""
    receipt = _mapping(transition_receipt, "WORKGRAPH_TRANSITION_RECEIPT_MAPPING_REQUIRED")
    projection = _mapping(after_projection, "AFTER_PROJECTION_MAPPING_REQUIRED")
    if receipt.get("schema") != WORKGRAPH_TRANSITION_RECEIPT_SCHEMA:
        raise ArtifactWakeBridgeError("WORKGRAPH_TRANSITION_RECEIPT_SCHEMA_INVALID")
    if projection.get("schema") != WORKGRAPH_PROJECTION_SCHEMA:
        raise ArtifactWakeBridgeError("AFTER_PROJECTION_SCHEMA_INVALID")
    if receipt.get("action") != "REOPEN":
        raise ArtifactWakeBridgeError("WORKGRAPH_TRANSITION_NOT_REOPEN")
    for actual, expected, code in (
        (receipt.get("project_id"), proposal.project_id, "TRANSITION_PROJECT_MISMATCH"),
        (receipt.get("cell_id"), proposal.target_cell_id, "TRANSITION_CELL_MISMATCH"),
        (receipt.get("basis_graph_digest"), proposal.basis_graph_digest, "TRANSITION_BASIS_MISMATCH"),
        (projection.get("project_id"), proposal.project_id, "AFTER_PROJECT_MISMATCH"),
        (projection.get("currentness_ref"), proposal.currentness_ref, "AFTER_CURRENTNESS_MISMATCH"),
        (receipt.get("after_graph_digest"), projection.get("graph_digest"), "AFTER_GRAPH_DIGEST_MISMATCH"),
    ):
        if actual != expected:
            raise ArtifactWakeBridgeError(code)
    if receipt.get("runtime_execution_proven") is not False or receipt.get("provider_calls") != 0:
        raise ArtifactWakeBridgeError("TRANSITION_RECEIPT_AUTHORITY_WIDENING")

    evidence = _resolve_canonical_transition_evidence(
        resolver=canonical_transition_resolver,
        transition_receipt=receipt,
        proposal=proposal,
        after_projection=projection,
    )

    cell = _target_cell(projection, proposal.target_cell_id)
    if cell.get("state") != "OPEN" or cell.get("effective_state") != "OPEN":
        raise ArtifactWakeBridgeError("REOPEN_TRANSITION_NOT_VISIBLE_AS_OPEN")

    body = {
        "schema": VERIFICATION_SCHEMA,
        "decision": "POST_TRANSITION_WAKE_SCAN_ALLOWED",
        "proposal_id": proposal.proposal_id,
        "project_id": proposal.project_id,
        "artifact_sid": proposal.artifact_sid,
        "persistence_receipt_id": proposal.persistence_receipt_id,
        "target_cell_id": proposal.target_cell_id,
        "before_graph_digest": proposal.basis_graph_digest,
        "after_graph_digest": projection.get("graph_digest"),
        "currentness_ref": proposal.currentness_ref,
        "transition_receipt_digest": evidence.get("transition_receipt_digest"),
        "canonical_workgraph_owner_ref": evidence.get("canonical_workgraph_owner_ref"),
        "canonical_store_ref": evidence.get("canonical_store_ref"),
        "persistence_verification_ref": evidence.get("persistence_verification_ref"),
        "readback_ref": evidence.get("readback_ref"),
        "requires_existing_h_g_wake_scan": True,
        "wake_intent_emitted": False,
        "execution_authorized": False,
        "effect_authorized": False,
        "provider_calls_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
    }
    body["verification_id"] = "adtv-" + _digest("ARTIFACT_DEPENDENCY_TRANSITION_VERIFICATION_V1", body)[:32]
    return body
