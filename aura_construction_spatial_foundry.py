"""Construction-bound adapter over Aura's canonical B11-B15 Spatial Foundry.

The adapter corrects arena attribution and adds Construction projection contracts
without replacing the B15 service, Attempt Archive, Runtime Profile V2, U7, or
Construction truth owners.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path
import re
import secrets
from typing import Any

from aura_arena_attempt_archive import ArenaAttemptArchive
from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    BilateralLiveRepairService,
    PreviewRollbackReceipt,
    RepairCandidateResult,
)
from aura_bilateral_live_repair_foundry_contracts import canonical_sanitize, digest
from aura_construction_adapter import (
    CONSTRUCTION_ADAPTER_VERSION,
    ConstructionCoordinationCandidate,
)
from aura_construction_contracts import PATCH_AUTHORITY
from aura_spatial_foundry_projection import (
    SPATIAL_FOUNDRY_PROJECTION_V2,
    build_spatial_foundry_projection_v2,
    project_guarded_wfst,
    validate_foundry_arena,
)

CONSTRUCTION_CANDIDATE_VERSION = "AURA_CONSTRUCTION_COORDINATION_CANDIDATE_PROJECTION_V1"
DOMAIN_DECISION_VERSION = "AURA_CONSTRUCTION_DOMAIN_DECISION_ENVELOPE_V1"
TRUSTED_IDENTITY_SUMMARY_VERSION = "AURA_TRUSTED_BILATERAL_IDENTITY_SUMMARY_V1"
ARENA_BOUND_SERVICE_VERSION = "AURA_ARENA_BOUND_BILATERAL_LIVE_REPAIR_V1"
_ALLOWED_DECISION_STATUS = frozenset(
    {
        "READY_FOR_HUMAN_REVIEW",
        "DEFERRED",
        "REJECTED",
        "WITHDRAWN",
    }
)
_HEX = re.compile(r"^[0-9a-f]{40,64}$")
_CANONICAL_STATE_HEX = re.compile(r"^(?:[0-9a-f]{32}|[0-9a-f]{40,64})$")
_CANDIDATE_HEX = _CANONICAL_STATE_HEX
MAX_REQUEST_NESTING = 12
MAX_ARCHIVE_SCAN_ROWS = 500
MAX_RETAINED_U7_PACKETS = 64
MAX_RETAINED_U7_RESULTS_PER_PACKET = 32
_RAW_CURRENCY_KEYS = frozenset(
    {
        "identitycurrency",
        "identityiscurrent",
        "currentidentityiscurrent",
        "requestiscurrent",
    }
)


def _required_text(value: Any, name: str, *, limit: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    text = value.strip()
    if len(text.encode("utf-8")) > limit:
        raise ValueError(f"{name} exceeds {limit} UTF-8 bytes")
    return text


def _digest_text(value: Any, name: str) -> str:
    text = _required_text(value, name, limit=128).lower()
    if not _HEX.fullmatch(text):
        raise ValueError(f"{name} must be a 40-64 character lowercase hex digest")
    return text


def _candidate_digest_text(value: Any, name: str) -> str:
    text = _required_text(value, name, limit=128).lower()
    if not _CANDIDATE_HEX.fullmatch(text):
        raise ValueError(f"{name} must be a 32-character or 40-64 character lowercase hex digest")
    return text


def _state_digest_text(value: Any, name: str) -> str:
    text = _required_text(value, name, limit=128).lower()
    if not _CANONICAL_STATE_HEX.fullmatch(text):
        raise ValueError(f"{name} must be a 32-character or 40-64 character lowercase hex digest")
    return text


def _strings(value: Any, name: str, *, limit: int = 256) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(value) > limit:
        raise ValueError(f"{name} exceeds {limit} items")
    result = tuple(_required_text(item, name) for item in value)
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result


@dataclass(frozen=True)
class ConstructionCoordinationCandidateArtifact:
    candidate: ConstructionCoordinationCandidate
    base_state_digest: str
    version: str = CONSTRUCTION_CANDIDATE_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, ConstructionCoordinationCandidate):
            raise ValueError("candidate must be owned by aura_construction_adapter.ConstructionCoordinationCandidate")
        object.__setattr__(
            self,
            "base_state_digest",
            _state_digest_text(self.base_state_digest, "base_state_digest"),
        )
        if self.version != CONSTRUCTION_CANDIDATE_VERSION:
            raise ValueError("unsupported Construction candidate projection version")

    @property
    def candidate_id(self) -> str:
        return self.candidate.candidate_id

    @property
    def candidate_digest(self) -> str:
        return self.candidate.candidate_digest

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ConstructionCoordinationCandidateArtifact:
        if not isinstance(value, Mapping):
            raise ValueError("Construction candidate must be an object")
        if any(
            key in value
            for key in (
                "attempt_id",
                "promotion_ready",
                "runtime_proof_digest",
                "failure_class",
                "route_class",
            )
        ):
            raise ValueError("software repair fields are forbidden in Construction candidates")
        candidate_fields = {
            field.name
            for field in fields(ConstructionCoordinationCandidate)
            if field.name
            not in {
                "version",
                "proposal_only",
                "physical_work_authorized",
                "payment_released",
                "access_controlled",
                "patch_authority",
                "vsa_patch_authority",
            }
        }
        expected = candidate_fields | {
            "base_state_digest",
            "candidate_type",
            "version",
        }
        if set(value) != expected:
            raise ValueError(
                "Construction candidate projection schema mismatch; "
                f"missing={sorted(expected - set(value))}, unknown={sorted(set(value) - expected)}"
            )
        if value.get("candidate_type") != "CONSTRUCTION_COORDINATION":
            raise ValueError("candidate_type must remain CONSTRUCTION_COORDINATION")
        if value.get("version") != CONSTRUCTION_CANDIDATE_VERSION:
            raise ValueError("unsupported Construction candidate projection version")
        canonical = {name: value[name] for name in candidate_fields}
        canonical.update(
            {
                "version": CONSTRUCTION_ADAPTER_VERSION,
                "proposal_only": True,
                "physical_work_authorized": False,
                "payment_released": False,
                "access_controlled": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": False,
            }
        )
        return cls(
            candidate=ConstructionCoordinationCandidate.from_dict(canonical),
            base_state_digest=value["base_state_digest"],
        )

    def to_dict(self) -> dict[str, Any]:
        canonical = self.candidate.to_dict()
        for key in (
            "version",
            "proposal_only",
            "physical_work_authorized",
            "payment_released",
            "access_controlled",
            "patch_authority",
            "vsa_patch_authority",
        ):
            canonical.pop(key, None)
        return {
            **canonical,
            "base_state_digest": self.base_state_digest,
            "candidate_type": "CONSTRUCTION_COORDINATION",
            "version": self.version,
        }


@dataclass(frozen=True)
class DomainDecisionEnvelope:
    status: str
    candidate_id: str
    candidate_digest: str
    recommended_for_human_review: bool
    reasons: tuple[str, ...]
    open_obligations: tuple[str, ...]
    physical_work_authorized: bool = False
    professional_approval: bool = False
    payment_released: bool = False
    access_granted: bool = False
    automatic_execution: bool = False
    survey_authority: bool = False
    construction_truth: bool = False
    human_review_required: bool = True
    version: str = DOMAIN_DECISION_VERSION

    def __post_init__(self) -> None:
        status = _required_text(self.status, "status", limit=128).upper()
        if status not in _ALLOWED_DECISION_STATUS:
            raise ValueError(f"unsupported non-authoritative decision status: {status}")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "candidate_id", _required_text(self.candidate_id, "candidate_id"))
        object.__setattr__(
            self,
            "candidate_digest",
            _candidate_digest_text(self.candidate_digest, "candidate_digest"),
        )
        object.__setattr__(self, "reasons", _strings(self.reasons, "reasons"))
        object.__setattr__(self, "open_obligations", _strings(self.open_obligations, "open_obligations"))
        if type(self.recommended_for_human_review) is not bool:
            raise ValueError("recommended_for_human_review must be a boolean")
        for name in (
            "physical_work_authorized",
            "professional_approval",
            "payment_released",
            "access_granted",
            "automatic_execution",
            "survey_authority",
            "construction_truth",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"{name} must remain false")
        if self.human_review_required is not True:
            raise ValueError("human_review_required must remain true")
        if self.version != DOMAIN_DECISION_VERSION:
            raise ValueError("unsupported domain decision version")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> DomainDecisionEnvelope:
        if not isinstance(value, Mapping):
            raise ValueError("domain decision must be an object")
        expected = {field.name for field in fields(cls)}
        if set(value) != expected:
            raise ValueError(
                "domain decision schema mismatch; "
                f"missing={sorted(expected - set(value))}, unknown={sorted(set(value) - expected)}"
            )
        return cls(**{name: value[name] for name in expected})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _ArenaBoundArchive:
    """Delegating archive adapter that corrects generic B15 arena labels."""

    def __init__(self, delegate: ArenaAttemptArchive) -> None:
        self.delegate = delegate
        self._capture_arenas: dict[str, str] = {}
        self._packet_arenas: OrderedDict[str, str] = OrderedDict()

    def bind_capture(self, capture_id: str, arena_id: str) -> None:
        self._capture_arenas[_required_text(capture_id, "capture_id")] = validate_foundry_arena(arena_id)

    def unbind_capture(self, capture_id: str) -> None:
        self._capture_arenas.pop(str(capture_id or ""), None)

    def bind_packet(self, packet_id: str, arena_id: str) -> None:
        packet = _required_text(packet_id, "packet_id")
        arena = validate_foundry_arena(arena_id)
        previous = self._packet_arenas.get(packet)
        if previous is not None and previous != arena:
            raise BilateralLiveRepairError("replay packet arena binding is immutable")
        self._packet_arenas[packet] = arena
        self._packet_arenas.move_to_end(packet)
        while len(self._packet_arenas) > 64:
            self._packet_arenas.popitem(last=False)

    def arena_for_packet(self, packet_id: str) -> str:
        packet = _required_text(packet_id, "packet_id")
        retained = self._packet_arenas.get(packet)
        if retained:
            return retained
        summaries = self.delegate.list(
            workflow_id=packet,
            route="bilateral-live-repair/incident-capture",
            limit=32,
        )
        arenas = {validate_foundry_arena(summary.get("arena_id")) for summary in summaries if summary.get("arena_id")}
        if len(arenas) != 1:
            raise BilateralLiveRepairError("replay packet has no unique canonical incident-capture arena binding")
        resolved = arenas.pop()
        self.bind_packet(packet, resolved)
        return resolved

    def record(
        self,
        *,
        arena_id: str,
        route: str,
        request: dict[str, Any] | None,
        result: dict[str, Any] | None,
        workflow_state: dict[str, Any] | None = None,
        archive_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_row = dict(request or {})
        result_row = dict(result or {})
        state_row = dict(workflow_state or {})
        context_row = dict(archive_context or {})
        requested = validate_foundry_arena(arena_id)
        workflow_id = str(state_row.get("workflow_id") or "")
        actual = requested
        if route == "bilateral-live-repair/incident-capture":
            capture_id = str(request_row.get("capture_id") or "")
            bound_capture = self._capture_arenas.get(capture_id)
            if bound_capture and bound_capture != requested:
                raise BilateralLiveRepairError("capture arena differs from finalization arena")
            actual = bound_capture or requested
            packet_id = str(result_row.get("packet_id") or workflow_id)
            if packet_id:
                self.bind_packet(packet_id, actual)
        elif workflow_id:
            actual = self.arena_for_packet(workflow_id)
        context_row["arena_binding"] = {
            "arena_id": actual,
            "requested_arena_id": requested,
            "corrected_generic_attribution": requested != actual,
            "immutable_after_incident_finalization": True,
        }
        return self.delegate.record(
            arena_id=actual,
            route=route,
            request=request_row,
            result=result_row,
            workflow_state=state_row,
            archive_context=context_row,
        )

    def list(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.delegate.list(**kwargs)

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        return self.delegate.get(artifact_id)

    def status(self) -> dict[str, Any]:
        return {
            **self.delegate.status(),
            "arena_binding_adapter": ARENA_BOUND_SERVICE_VERSION,
            "bound_packet_count": len(self._packet_arenas),
        }

    def export_jsonl(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.delegate.export_jsonl(*args, **kwargs)


class ArenaBoundBilateralLiveRepairService(BilateralLiveRepairService):
    """Construction-safe adapter retaining every canonical B15 owner."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        attempt_archive: ArenaAttemptArchive | None = None,
        attempt_archive_db_path: str | Path | None = None,
        runtime_runner: Callable[..., Mapping[str, Any]] | None = None,
        current_identity_resolver: Callable[[BilateralIdentity], BilateralIdentity] | None = None,
        allow_reduced_runtime_fixture: bool = False,
    ) -> None:
        self._owns_bound_archive = attempt_archive is None
        delegate = attempt_archive or ArenaAttemptArchive(repo_root, db_path=attempt_archive_db_path)
        self._arena_archive = _ArenaBoundArchive(delegate)
        self._capture_arena: dict[str, str] = {}
        self._u7_results: OrderedDict[
            str,
            OrderedDict[str, tuple[str, dict[str, Any]]],
        ] = OrderedDict()
        super().__init__(
            repo_root,
            attempt_archive=self._arena_archive,
            runtime_runner=runtime_runner,
            current_identity_resolver=current_identity_resolver,
            allow_reduced_runtime_fixture=allow_reduced_runtime_fixture,
        )

    def close(self) -> None:
        try:
            super().close()
        finally:
            self._capture_arena.clear()
            self._u7_results.clear()
            self._arena_archive._capture_arenas.clear()
            if self._owns_bound_archive:
                self._arena_archive.delegate.close()

    def _release_capture_arena(self, capture_id: str) -> None:
        with self._capture_lock:
            self._capture_arena.pop(str(capture_id or ""), None)
            self._arena_archive.unbind_capture(capture_id)

    def _prune_capture_arenas(self) -> None:
        with self._capture_lock:
            retained = set(self._captures)
            stale = [capture_id for capture_id in self._capture_arena if capture_id not in retained]
        for capture_id in stale:
            self._release_capture_arena(capture_id)

    def _expire_capture(self, capture_id: str) -> None:
        try:
            super()._expire_capture(capture_id)
        finally:
            self._release_capture_arena(capture_id)

    def _sweep_expired_captures(self) -> None:
        super()._sweep_expired_captures()
        self._prune_capture_arenas()

    def observe(
        self,
        capture_id: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return super().observe(capture_id, event_type, payload)
        finally:
            self._prune_capture_arenas()

    def start_capture(self, contract: Mapping[str, Any]) -> dict[str, Any]:
        arena = validate_foundry_arena(contract.get("arena_id") or "construction")
        result = super().start_capture({**dict(contract), "arena_id": arena})
        capture_id = str(result["capture_id"])
        with self._capture_lock:
            self._capture_arena[capture_id] = arena
            self._arena_archive.bind_capture(capture_id, arena)
        return {**result, "arena_id": arena, "arena_binding_immutable": True}

    def finalize_capture(self, capture_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
        bound = self._capture_arena.get(_required_text(capture_id, "capture_id"))
        if not bound:
            raise BilateralLiveRepairError("capture has no exact arena binding")
        supplied = contract.get("arena_id")
        if supplied is not None and validate_foundry_arena(supplied) != bound:
            raise BilateralLiveRepairError("capture finalization cannot change arena_id")
        try:
            result = super().finalize_capture(capture_id, {**dict(contract), "arena_id": bound})
            packet_id = str((result.get("packet") or {}).get("packet_id") or "")
            if packet_id:
                self._arena_archive.bind_packet(packet_id, bound)
            return {**result, "arena_id": bound}
        finally:
            self._prune_capture_arenas()

    def packet(self, packet_id: str):
        """Return one canonical replay packet through a stable adapter API."""

        return self._packet(packet_id)

    def assert_current_identity(self, packet_id: str) -> BilateralIdentity:
        """Recheck a packet against the trusted current-identity owner."""

        packet = self.packet(packet_id)
        return self._resolve_current_identity(packet.identity)

    def arena_for_packet(self, packet_id: str) -> str:
        self.packet(packet_id)
        return self._arena_archive.arena_for_packet(packet_id)

    def record_repair_attempt(
        self,
        *,
        packet_id: str,
        hypothesis: Mapping[str, Any],
        candidate_digest: str,
        runtime_proof_ref: str,
        minimized_counterexample: Mapping[str, Any] | None,
        current_identity: BilateralIdentity,
        arena_id: str | None = None,
    ) -> RepairCandidateResult:
        bound = self.arena_for_packet(packet_id)
        if arena_id is not None and validate_foundry_arena(arena_id) != bound:
            raise BilateralLiveRepairError("repair attempt arena differs from replay packet")
        return super().record_repair_attempt(
            packet_id=packet_id,
            hypothesis=hypothesis,
            candidate_digest=candidate_digest,
            runtime_proof_ref=runtime_proof_ref,
            minimized_counterexample=minimized_counterexample,
            current_identity=current_identity,
            arena_id=bound,
        )

    def run_governed_u7(self, **kwargs: Any) -> dict[str, Any]:
        packet_id = _required_text(kwargs.pop("packet_id", None), "packet_id")
        result = dict(super().run_governed_u7(packet_id=packet_id, **kwargs))
        arena = self.arena_for_packet(packet_id)
        result["arena_id"] = arena
        result["arena_binding_immutable"] = True
        clean_result, _ = canonical_sanitize(result)
        if not isinstance(clean_result, Mapping):
            raise BilateralLiveRepairError("canonical U7 owner returned an invalid result")
        retained_result = dict(clean_result)
        result_digest = digest(retained_result)
        binding_digest = _digest_text(
            retained_result.get("u7_binding_digest"),
            "u7_binding_digest",
        )
        archive = self.attempt_archive.record(
            arena_id=arena,
            route="bilateral-live-repair/u7-current-reproof",
            request={
                "packet_id": packet_id,
                "candidate_digest": result.get("candidate_digest"),
                "task_id": result.get("task_id"),
            },
            result={
                "ok": retained_result.get("ok") is True,
                "u7_result": retained_result,
                "u7_result_digest": result_digest,
            },
            workflow_state={
                "workflow_id": packet_id,
                "status": "CURRENT_REPROOF_RETAINED",
            },
            archive_context={
                "canonical_owner": "aura_unified_memory_continuity_learning",
                "projection_only": True,
                "automatic_promotion": False,
            },
        )
        artifact_ref = str(archive.get("artifact_id") or "")
        if not artifact_ref:
            raise BilateralLiveRepairError("canonical Attempt Archive did not retain governed U7 evidence")
        packet_results = self._u7_results.setdefault(packet_id, OrderedDict())
        packet_results[binding_digest] = (result_digest, retained_result)
        packet_results.move_to_end(binding_digest)
        while len(packet_results) > MAX_RETAINED_U7_RESULTS_PER_PACKET:
            packet_results.popitem(last=False)
        self._u7_results.move_to_end(packet_id)
        while len(self._u7_results) > MAX_RETAINED_U7_PACKETS:
            self._u7_results.popitem(last=False)
        return {**retained_result, "archive_artifact_ref": artifact_ref}

    def has_retained_runtime_proof(self, packet_id: str) -> bool:
        """Report verified Runtime Profile V2 evidence independently of attempts."""

        packet = self.packet(packet_id)
        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/runtime-replay",
            limit=MAX_ARCHIVE_SCAN_ROWS,
        ):
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            result = dict((artifact or {}).get("result") or {})
            proof_ref = str(result.get("runtime_proof_digest") or "")
            if result.get("packet_digest") != packet.packet_digest or not proof_ref:
                continue
            proof = self._runtime_proof(packet, proof_ref)
            self._validate_runtime_proof(
                packet,
                proof,
                allow_reduced_fixture=self._allow_reduced_runtime_fixture,
            )
            return True
        return False

    def preview_for_packet(
        self,
        packet_id: str,
        preview_id: str = "",
    ) -> PreviewRollbackReceipt | None:
        """Return a packet-bound preview through a stable adapter API."""

        packet = self.packet(packet_id)
        selected = str(preview_id or "").strip()
        if not selected:
            return self.latest_preview(packet.packet_id)
        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/preview-rollback",
            limit=MAX_ARCHIVE_SCAN_ROWS,
        ):
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            raw = dict((artifact or {}).get("result") or {}).get("preview")
            if not isinstance(raw, Mapping) or raw.get("preview_id") != selected:
                continue
            receipt = PreviewRollbackReceipt.from_mapping(raw)
            if receipt.replay_packet_digest != packet.packet_digest:
                raise BilateralLiveRepairError("requested preview belongs to another incident")
            return receipt
        return None

    def latest_u7_result(
        self,
        packet_id: str,
        *,
        candidate_digests: Sequence[str] = (),
    ) -> dict[str, Any] | None:
        """Read canonical in-process U7 evidence without trusting archive output."""

        packet = self.packet(packet_id)
        allowed = {_candidate_digest_text(item, "candidate_digest") for item in candidate_digests}
        if not allowed:
            return None
        packet_results = self._u7_results.get(packet.packet_id)
        if packet_results is None:
            return None
        self._u7_results.move_to_end(packet.packet_id)
        for result_digest, raw in reversed(packet_results.values()):
            result = dict(raw)
            if digest(result) != result_digest:
                raise BilateralLiveRepairError("retained canonical U7 result content is invalid")
            candidate = str(result.get("candidate_digest") or "")
            binding_payload = {
                "version": "AURA_BILATERAL_LIVE_REPAIR_U7_BINDING_V1",
                "replay_packet_digest": result.get("replay_packet_digest"),
                "bilateral_identity_digest": result.get("bilateral_identity_digest"),
                "candidate_digest": candidate,
                "plan_phase_hash": result.get("plan_phase_hash"),
                "task_id": result.get("task_id"),
            }
            if (
                result.get("replay_packet_digest") != packet.packet_digest
                or result.get("bilateral_identity_digest") != packet.identity.identity_digest
                or candidate not in allowed
                or result.get("u7_binding_digest") != digest(binding_payload)
            ):
                continue
            return result
        return None

    def build_projection_v2(
        self,
        *,
        packet_id: str,
        intent: Mapping[str, Any],
        plan: Mapping[str, Any],
        code_targets: Sequence[Mapping[str, Any]],
        attempts: Sequence[RepairCandidateResult | Mapping[str, Any]],
        preview: PreviewRollbackReceipt | Mapping[str, Any] | None,
        u7_result: Mapping[str, Any] | None,
        source_drilldown: Sequence[Mapping[str, Any]],
        receipt_drilldown: Sequence[Mapping[str, Any]],
        current_identity: BilateralIdentity,
        domain: Mapping[str, Any],
        domain_targets: Sequence[Mapping[str, Any]] = (),
        domain_artifacts: Sequence[Mapping[str, Any]] = (),
        presentation: Mapping[str, Any] | None = None,
        construction: Mapping[str, Any] | None = None,
        coordination_candidates: Sequence[ConstructionCoordinationCandidateArtifact | Mapping[str, Any]] = (),
        domain_decision: DomainDecisionEnvelope | Mapping[str, Any] | None = None,
        transition_state: str = "IDLE",
        transition_evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        bound = self.arena_for_packet(packet_id)
        base = super().build_projection(
            packet_id=packet_id,
            intent=intent,
            plan=plan,
            code_targets=code_targets,
            attempts=attempts,
            preview=preview,
            u7_result=u7_result,
            source_drilldown=source_drilldown,
            receipt_drilldown=receipt_drilldown,
            current_identity=current_identity,
        )
        parsed_candidates = [
            item
            if isinstance(item, ConstructionCoordinationCandidateArtifact)
            else ConstructionCoordinationCandidateArtifact.from_mapping(item)
            for item in coordination_candidates
        ]
        if parsed_candidates:
            domain_state_digest = _state_digest_text(domain.get("state_digest"), "domain.state_digest")
            for item in parsed_candidates:
                if item.base_state_digest != domain_state_digest:
                    raise BilateralLiveRepairError(
                        "Construction candidate base_state_digest differs from domain.state_digest"
                    )
        decision = (
            domain_decision
            if isinstance(domain_decision, DomainDecisionEnvelope)
            else DomainDecisionEnvelope.from_mapping(domain_decision)
            if domain_decision
            else None
        )
        if decision is not None:
            matches = [
                item
                for item in parsed_candidates
                if item.candidate_id == decision.candidate_id and item.candidate_digest == decision.candidate_digest
            ]
            if len(matches) != 1:
                raise BilateralLiveRepairError("domain decision must bind exactly one projected Construction candidate")
        transitions = project_guarded_wfst(
            arena_id=bound,
            current_state=transition_state,
            evidence=({} if transition_evidence is None else transition_evidence),
        )
        return build_spatial_foundry_projection_v2(
            base_projection=base,
            arena_id=bound,
            domain=domain,
            domain_targets=domain_targets,
            domain_artifacts=domain_artifacts,
            presentation=presentation,
            construction=construction,
            coordination_candidates=[item.to_dict() for item in parsed_candidates],
            domain_decision=decision.to_dict() if decision else {},
            transition_projection=transitions,
        )


class TrustedBilateralIdentityBroker:
    """Server-side identity handle issuer; raw requests never establish currency."""

    def __init__(
        self,
        provider: Callable[[], BilateralIdentity],
        *,
        current_identity_resolver: Callable[[BilateralIdentity], BilateralIdentity] | None = None,
        max_handles: int = 8,
    ) -> None:
        self.provider = provider
        self.current_identity_resolver = current_identity_resolver
        self.max_handles = max(1, min(int(max_handles), 64))
        self._handles: OrderedDict[str, BilateralIdentity] = OrderedDict()

    def _current(self) -> BilateralIdentity:
        item = self.provider()
        if not isinstance(item, BilateralIdentity):
            raise BilateralLiveRepairError("trusted identity provider returned an invalid identity")
        current = self.current_identity_resolver(item) if self.current_identity_resolver is not None else item
        item.assert_current(current)
        return item

    def issue_summary(self) -> dict[str, Any]:
        item = self._current()
        handle = f"BID-{secrets.token_hex(16)}"
        while handle in self._handles:
            handle = f"BID-{secrets.token_hex(16)}"
        self._handles[handle] = item
        self._handles.move_to_end(handle)
        while len(self._handles) > self.max_handles:
            self._handles.popitem(last=False)
        return {
            "ok": True,
            "version": TRUSTED_IDENTITY_SUMMARY_VERSION,
            "identity_handle": handle,
            "identity_digest": item.identity_digest,
            "intent_revision_id": item.intent_revision_id,
            "repository_head": item.repository_head,
            "source_tree_digest": item.source_tree_digest,
            "runtime_profile_digest": item.runtime_profile_digest,
            "verifier_id": item.verifier_id,
            "currency": "SERVER_RESOLVED_CURRENT",
            "full_identity_returned": False,
            "request_body_can_declare_currency": False,
            "expires_on_identity_change": True,
            "pins_issued_identity": True,
            "authority": {
                "patch": False,
                "commit": False,
                "push": False,
                "pull_request": False,
                "merge": False,
                "deployment": False,
                "production_mutation": False,
            },
        }

    def resolve(
        self,
        handle: str,
        *,
        expected: BilateralIdentity | None = None,
    ) -> BilateralIdentity:
        key = _required_text(handle, "identity_handle", limit=128)
        retained = self._handles.get(key)
        if retained is None:
            raise BilateralLiveRepairError("trusted identity handle is missing or expired")
        current = self._current()
        retained.assert_current(current)
        if expected is not None:
            expected.assert_current(current)
        self._handles.move_to_end(key)
        return retained


def reject_raw_identity_currency_claim(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("request body must be an object")

    def walk(item: Any, path: str, depth: int) -> None:
        if depth > MAX_REQUEST_NESTING:
            raise BilateralLiveRepairError(f"request nesting exceeds {MAX_REQUEST_NESTING} levels at {path}")
        if isinstance(item, Mapping):
            for key, child in item.items():
                normalized = re.sub(r"[^a-z0-9]+", "", str(key).casefold())
                if normalized in _RAW_CURRENCY_KEYS:
                    raise BilateralLiveRepairError(f"raw request cannot declare identity currency at {path}.{key}")
                walk(child, f"{path}.{key}", depth + 1)
        elif isinstance(item, (list, tuple)):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]", depth + 1)

    walk(value, "$", 0)


__all__ = [
    "ARENA_BOUND_SERVICE_VERSION",
    "CONSTRUCTION_CANDIDATE_VERSION",
    "DOMAIN_DECISION_VERSION",
    "SPATIAL_FOUNDRY_PROJECTION_V2",
    "TRUSTED_IDENTITY_SUMMARY_VERSION",
    "ArenaBoundBilateralLiveRepairService",
    "ConstructionCoordinationCandidateArtifact",
    "DomainDecisionEnvelope",
    "TrustedBilateralIdentityBroker",
    "reject_raw_identity_currency_claim",
]
