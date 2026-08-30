"""AS-06 C1 -> AS-07 generation-currentness membrane for artifact-triggered wake.

Coordination/evidence only. AS-06 C1 guarantees monotonic persistence generations
when receipts enter the canonical artifact index. AS-07 C0 proves a canonical
WorkGraph REOPEN was persisted/read back before allowing the existing wake scanner.
This wrapper closes the remaining cross-lane seam: an ArtifactAvailableEventV1 may
trigger REOPEN only while its resource generation is still the canonical current
head, and that same generation must remain current after the REOPEN transition.

It never mutates the artifact index or WorkGraph, emits no WakeIntent, and grants
no execution/effect/provider/background authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

try:
    from . import artifact_workgraph_wake_bridge as core
except ImportError:
    import artifact_workgraph_wake_bridge as core

GENERATION_EVIDENCE_SCHEMA = "CanonicalArtifactGenerationEvidenceV1"
FENCED_PROPOSAL_SCHEMA = "GenerationFencedArtifactDependencyProposalV1"
FENCED_VERIFICATION_SCHEMA = "GenerationFencedArtifactWakeVerificationV1"


class GenerationFenceError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


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
        raise GenerationFenceError("NONCANONICAL_GENERATION_EVIDENCE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenerationFenceError(code)
    return value.strip()


def _generation(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GenerationFenceError(code)
    return value


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GenerationFenceError(code)
    return value


def _zero_authority(row: Mapping[str, Any], code: str) -> None:
    for field in (
        "execution_authorized",
        "effect_authorized",
        "provider_calls_authorized",
        "runtime_execution_proven",
        "background_execution_claimed",
    ):
        if row.get(field) is not False:
            raise GenerationFenceError(code, field)


def generation_evidence_digest(evidence: Mapping[str, Any]) -> str:
    row = _mapping(evidence, "GENERATION_EVIDENCE_MAPPING_REQUIRED")
    if row.get("schema") != GENERATION_EVIDENCE_SCHEMA:
        raise GenerationFenceError("GENERATION_EVIDENCE_SCHEMA_INVALID")
    body = {
        "schema": GENERATION_EVIDENCE_SCHEMA,
        "status": _text(row.get("status"), "GENERATION_EVIDENCE_STATUS_REQUIRED"),
        "project_id": _text(row.get("project_id"), "GENERATION_EVIDENCE_PROJECT_REQUIRED"),
        "persisted_surface": _text(row.get("persisted_surface"), "GENERATION_EVIDENCE_SURFACE_REQUIRED"),
        "resource_ref": _text(row.get("resource_ref"), "GENERATION_EVIDENCE_RESOURCE_REQUIRED"),
        "resource_generation": _generation(row.get("resource_generation"), "GENERATION_EVIDENCE_GENERATION_INVALID"),
        "artifact_sid": _text(row.get("artifact_sid"), "GENERATION_EVIDENCE_ARTIFACT_REQUIRED"),
        "persistence_receipt_id": _text(row.get("persistence_receipt_id"), "GENERATION_EVIDENCE_RECEIPT_REQUIRED"),
        "currentness_ref": _text(row.get("currentness_ref"), "GENERATION_EVIDENCE_CURRENTNESS_REQUIRED"),
        "current_live_index_revision": _text(row.get("current_live_index_revision"), "GENERATION_EVIDENCE_INDEX_REVISION_REQUIRED"),
        "canonical_artifact_index_owner_ref": _text(row.get("canonical_artifact_index_owner_ref"), "GENERATION_EVIDENCE_OWNER_REQUIRED"),
        "canonical_store_ref": _text(row.get("canonical_store_ref"), "GENERATION_EVIDENCE_STORE_REQUIRED"),
        "readback_ref": _text(row.get("readback_ref"), "GENERATION_EVIDENCE_READBACK_REF_REQUIRED"),
        "readback_verified": row.get("readback_verified"),
        "execution_authorized": row.get("execution_authorized"),
        "effect_authorized": row.get("effect_authorized"),
        "provider_calls_authorized": row.get("provider_calls_authorized"),
        "runtime_execution_proven": row.get("runtime_execution_proven"),
        "background_execution_claimed": row.get("background_execution_claimed"),
    }
    return _digest("CANONICAL_ARTIFACT_GENERATION_EVIDENCE_V1", body)


def _resolve_generation_evidence(
    *,
    resolver: Callable[[str, str, str], Mapping[str, Any]] | None,
    event: Mapping[str, Any],
) -> Mapping[str, Any]:
    if resolver is None or not callable(resolver):
        raise GenerationFenceError("CANONICAL_GENERATION_RESOLVER_REQUIRED")
    project_id = _text(event.get("project_id"), "ARTIFACT_PROJECT_REQUIRED")
    surface = _text(event.get("persisted_surface"), "ARTIFACT_PERSISTED_SURFACE_REQUIRED")
    resource_ref = _text(event.get("resource_ref"), "ARTIFACT_RESOURCE_REF_REQUIRED")
    generation = _generation(event.get("source_event_generation"), "ARTIFACT_SOURCE_GENERATION_REQUIRED")
    artifact_sid = _text(event.get("artifact_sid"), "ARTIFACT_SID_REQUIRED")
    receipt_id = _text(event.get("persistence_receipt_id"), "PERSISTENCE_RECEIPT_ID_REQUIRED")
    currentness_ref = _text(event.get("currentness_ref"), "ARTIFACT_CURRENTNESS_REQUIRED")

    evidence = _mapping(
        resolver(project_id, surface, resource_ref),
        "GENERATION_EVIDENCE_MAPPING_REQUIRED",
    )
    if evidence.get("schema") != GENERATION_EVIDENCE_SCHEMA:
        raise GenerationFenceError("GENERATION_EVIDENCE_SCHEMA_INVALID")
    if evidence.get("status") != "VERIFIED_CURRENT_RESOURCE_GENERATION":
        raise GenerationFenceError("RESOURCE_GENERATION_NOT_CURRENT")
    if evidence.get("readback_verified") is not True:
        raise GenerationFenceError("RESOURCE_GENERATION_READBACK_REQUIRED")
    _zero_authority(evidence, "GENERATION_EVIDENCE_AUTHORITY_WIDENING")

    exact = (
        (evidence.get("project_id"), project_id, "GENERATION_EVIDENCE_PROJECT_MISMATCH"),
        (evidence.get("persisted_surface"), surface, "GENERATION_EVIDENCE_SURFACE_MISMATCH"),
        (evidence.get("resource_ref"), resource_ref, "GENERATION_EVIDENCE_RESOURCE_MISMATCH"),
        (evidence.get("resource_generation"), generation, "ARTIFACT_GENERATION_STALE"),
        (evidence.get("artifact_sid"), artifact_sid, "RESOURCE_HEAD_ARTIFACT_MISMATCH"),
        (evidence.get("persistence_receipt_id"), receipt_id, "RESOURCE_HEAD_RECEIPT_MISMATCH"),
        (evidence.get("currentness_ref"), currentness_ref, "GENERATION_EVIDENCE_CURRENTNESS_MISMATCH"),
    )
    for actual, expected, code in exact:
        if actual != expected:
            raise GenerationFenceError(code)

    supplied = _text(evidence.get("evidence_digest"), "GENERATION_EVIDENCE_DIGEST_REQUIRED")
    expected = generation_evidence_digest(evidence)
    if supplied != expected:
        raise GenerationFenceError("GENERATION_EVIDENCE_DIGEST_MISMATCH")
    return evidence


@dataclass(frozen=True)
class GenerationFencedReadyProposal:
    inner_proposal: core.ArtifactDependencyReadyProposal
    persisted_surface: str
    resource_ref: str
    source_event_generation: int
    generation_evidence_digest: str
    generation_evidence_index_revision: str
    proposal_id: str = ""
    schema: str = FENCED_PROPOSAL_SCHEMA
    wake_scan_allowed: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    provider_calls_authorized: bool = False
    runtime_execution_proven: bool = False
    background_execution_claimed: bool = False

    def __post_init__(self) -> None:
        if self.schema != FENCED_PROPOSAL_SCHEMA:
            raise GenerationFenceError("FENCED_PROPOSAL_SCHEMA_INVALID")
        _text(self.persisted_surface, "FENCED_SURFACE_REQUIRED")
        _text(self.resource_ref, "FENCED_RESOURCE_REQUIRED")
        _generation(self.source_event_generation, "FENCED_GENERATION_INVALID")
        _text(self.generation_evidence_digest, "FENCED_GENERATION_EVIDENCE_DIGEST_REQUIRED")
        _text(self.generation_evidence_index_revision, "FENCED_INDEX_REVISION_REQUIRED")
        for field in (
            "wake_scan_allowed", "execution_authorized", "effect_authorized",
            "provider_calls_authorized", "runtime_execution_proven", "background_execution_claimed",
        ):
            if getattr(self, field) is not False:
                raise GenerationFenceError("FENCED_PROPOSAL_AUTHORITY_WIDENING", field)
        expected = self.compute_proposal_id()
        supplied = str(self.proposal_id or "").strip()
        if supplied and supplied != expected:
            raise GenerationFenceError("FENCED_PROPOSAL_ID_MISMATCH")
        object.__setattr__(self, "proposal_id", expected)

    def logical_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "inner_proposal_id": self.inner_proposal.proposal_id,
            "event_id": self.inner_proposal.event_id,
            "project_id": self.inner_proposal.project_id,
            "artifact_sid": self.inner_proposal.artifact_sid,
            "persistence_receipt_id": self.inner_proposal.persistence_receipt_id,
            "persisted_surface": self.persisted_surface,
            "resource_ref": self.resource_ref,
            "source_event_generation": self.source_event_generation,
            "generation_evidence_digest": self.generation_evidence_digest,
            "generation_evidence_index_revision": self.generation_evidence_index_revision,
            "target_cell_id": self.inner_proposal.target_cell_id,
            "basis_graph_digest": self.inner_proposal.basis_graph_digest,
            "wake_scan_allowed": False,
            "execution_authorized": False,
            "effect_authorized": False,
            "provider_calls_authorized": False,
            "runtime_execution_proven": False,
            "background_execution_claimed": False,
        }

    def compute_proposal_id(self) -> str:
        return "gfap-" + _digest("GENERATION_FENCED_ARTIFACT_PROPOSAL_V1", self.logical_payload())[:32]


def compile_generation_fenced_proposal(
    *,
    artifact_event: Mapping[str, Any],
    binding: core.ArtifactWorkDependencyBinding,
    workgraph_projection: Mapping[str, Any],
    canonical_generation_resolver: Callable[[str, str, str], Mapping[str, Any]] | None,
) -> GenerationFencedReadyProposal:
    event = _mapping(artifact_event, "ARTIFACT_EVENT_MAPPING_REQUIRED")
    generation_evidence = _resolve_generation_evidence(
        resolver=canonical_generation_resolver,
        event=event,
    )
    inner = core.compile_dependency_ready_proposal(
        artifact_event=event,
        binding=binding,
        workgraph_projection=workgraph_projection,
    )
    return GenerationFencedReadyProposal(
        inner_proposal=inner,
        persisted_surface=_text(event.get("persisted_surface"), "ARTIFACT_PERSISTED_SURFACE_REQUIRED"),
        resource_ref=_text(event.get("resource_ref"), "ARTIFACT_RESOURCE_REF_REQUIRED"),
        source_event_generation=_generation(event.get("source_event_generation"), "ARTIFACT_SOURCE_GENERATION_REQUIRED"),
        generation_evidence_digest=_text(generation_evidence.get("evidence_digest"), "GENERATION_EVIDENCE_DIGEST_REQUIRED"),
        generation_evidence_index_revision=_text(
            generation_evidence.get("current_live_index_revision"),
            "GENERATION_EVIDENCE_INDEX_REVISION_REQUIRED",
        ),
    )


def verify_generation_fenced_reopen(
    *,
    fenced_proposal: GenerationFencedReadyProposal,
    artifact_event: Mapping[str, Any],
    transition_receipt: Mapping[str, Any],
    after_projection: Mapping[str, Any],
    canonical_transition_resolver: Callable[[str], Mapping[str, Any]] | None,
    canonical_generation_resolver: Callable[[str, str, str], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    if not isinstance(fenced_proposal, GenerationFencedReadyProposal):
        raise GenerationFenceError("FENCED_PROPOSAL_REQUIRED")
    event = _mapping(artifact_event, "ARTIFACT_EVENT_MAPPING_REQUIRED")
    if event.get("event_id") != fenced_proposal.inner_proposal.event_id:
        raise GenerationFenceError("FENCED_EVENT_ID_MISMATCH")
    if _generation(event.get("source_event_generation"), "ARTIFACT_SOURCE_GENERATION_REQUIRED") != fenced_proposal.source_event_generation:
        raise GenerationFenceError("FENCED_EVENT_GENERATION_MISMATCH")

    # Re-resolve after the WorkGraph effect boundary. If the resource advanced while
    # REOPEN was being persisted, the old artifact may not unlock a wake scan.
    current_evidence = _resolve_generation_evidence(
        resolver=canonical_generation_resolver,
        event=event,
    )
    if current_evidence.get("resource_generation") != fenced_proposal.source_event_generation:
        raise GenerationFenceError("ARTIFACT_GENERATION_ADVANCED_REBASE_REQUIRED")
    if current_evidence.get("artifact_sid") != fenced_proposal.inner_proposal.artifact_sid:
        raise GenerationFenceError("RESOURCE_HEAD_ARTIFACT_MISMATCH")

    inner_verification = core.verify_canonical_reopen_transition(
        proposal=fenced_proposal.inner_proposal,
        transition_receipt=transition_receipt,
        after_projection=after_projection,
        canonical_transition_resolver=canonical_transition_resolver,
    )
    if inner_verification.get("decision") != "POST_TRANSITION_WAKE_SCAN_ALLOWED":
        raise GenerationFenceError("INNER_WAKE_SCAN_NOT_ALLOWED")

    body = {
        "schema": FENCED_VERIFICATION_SCHEMA,
        "decision": "GENERATION_CURRENT_POST_TRANSITION_WAKE_SCAN_ALLOWED",
        "fenced_proposal_id": fenced_proposal.proposal_id,
        "inner_verification_id": inner_verification.get("verification_id"),
        "project_id": fenced_proposal.inner_proposal.project_id,
        "artifact_sid": fenced_proposal.inner_proposal.artifact_sid,
        "persistence_receipt_id": fenced_proposal.inner_proposal.persistence_receipt_id,
        "persisted_surface": fenced_proposal.persisted_surface,
        "resource_ref": fenced_proposal.resource_ref,
        "source_event_generation": fenced_proposal.source_event_generation,
        "pre_transition_generation_evidence_digest": fenced_proposal.generation_evidence_digest,
        "post_transition_generation_evidence_digest": current_evidence.get("evidence_digest"),
        "pre_transition_live_index_revision": fenced_proposal.generation_evidence_index_revision,
        "post_transition_live_index_revision": current_evidence.get("current_live_index_revision"),
        "target_cell_id": fenced_proposal.inner_proposal.target_cell_id,
        "requires_existing_h_g_wake_scan": True,
        "wake_intent_emitted": False,
        "execution_authorized": False,
        "effect_authorized": False,
        "provider_calls_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
    }
    body["verification_id"] = "gfv-" + _digest("GENERATION_FENCED_ARTIFACT_WAKE_VERIFICATION_V1", body)[:32]
    return body
