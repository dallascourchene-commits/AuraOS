"""Deterministic P4 Director for the Construction Spatial Foundry.

The Director is a bounded presentation/workflow coordinator.  It does not own
Construction truth, renderer truth, Runtime Profile V2 proof, Attempt Archive,
rollback authority, U7 learning, patching, publication, or merge authority.
Consequential chapter effects are executed only by the existing canonical
owners after this module admits an exact guarded transition.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import re
import secrets
import threading
from typing import Any

DIRECTOR_VERSION = "AURA_CONSTRUCTION_FOUNDRY_DIRECTOR_V1"
DIRECTOR_MANIFEST_VERSION = "AURA_CONSTRUCTION_FOUNDRY_DIRECTOR_MANIFEST_V1"
DIRECTOR_RECEIPT_VERSION = "AURA_CONSTRUCTION_FOUNDRY_DIRECTOR_RECEIPT_V1"
FAULT_FIXTURE_VERSION = "AURA_CONSTRUCTION_DEMO_FAULT_FIXTURE_V1"
MAX_SESSIONS = 8
MAX_RECEIPTS = 256
_HEX = re.compile(r"^[0-9a-f]{64}$")
_STATE_HEX = re.compile(r"^(?:[0-9a-f]{32}|[0-9a-f]{40,64})$")
_SLOT_KEYS = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")

_FALSE_AUTHORITY = {
    "construction_truth": False,
    "visual_truth": False,
    "renderer_authority": False,
    "patch": False,
    "commit": False,
    "push": False,
    "pull_request": False,
    "merge": False,
    "deployment": False,
    "production_mutation": False,
    "professional_authority": False,
    "physical_work_authority": False,
    "payment_release": False,
    "access_control": False,
    "learning_promotion": False,
    "automatic_crystallization": False,
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def runtime_binding_digest(value: Any) -> str:
    """Match Runtime Profile V2 candidate/requirement identity."""
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=32).hexdigest()


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
        raise ValueError(f"{name} must be a 64-character lowercase hexadecimal digest")
    return text


def _state_digest_text(value: Any, name: str) -> str:
    text = _required_text(value, name, limit=128).lower()
    if not _STATE_HEX.fullmatch(text):
        raise ValueError(f"{name} must be a 32-character or 40-64 character lowercase hexadecimal digest")
    return text


def _strings(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    result = tuple(_required_text(item, name, limit=1024) for item in value)
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _slots(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping) or tuple(value) != _SLOT_KEYS:
        raise ValueError(f"six_slot_packet must contain {_SLOT_KEYS} in canonical order")
    return {key: _required_text(value[key], f"six_slot_packet.{key}", limit=128) for key in _SLOT_KEYS}


class DirectorControl(str, Enum):
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    NEXT = "NEXT"
    PREVIOUS = "PREVIOUS"
    RESTART = "RESTART"
    JUMP = "JUMP"


@dataclass(frozen=True)
class RequiredAsset:
    path: str
    sha256: str

    def __post_init__(self) -> None:
        path = _required_text(self.path, "required asset path", limit=2048)
        if path.startswith("/") or "\\" in path or ".." in path.split("/"):
            raise ValueError("required asset path must be a safe repository-relative POSIX path")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "sha256", _digest_text(self.sha256, "required asset sha256"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoFaultFixture:
    fixture_id: str
    marker: str
    event_type: str
    hypothesis: Mapping[str, Any]
    runtime_candidate_id: str
    runtime_candidate_digest: str
    last_verified_digest: str
    degraded_health_before: Mapping[str, Any]
    degraded_health_after: Mapping[str, Any]
    successful_health_before: Mapping[str, Any]
    successful_health_after: Mapping[str, Any]
    rollback_reason: str
    version: str = FAULT_FIXTURE_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "fixture_id", _required_text(self.fixture_id, "fixture_id", limit=256))
        object.__setattr__(self, "marker", _required_text(self.marker, "marker", limit=1024))
        object.__setattr__(self, "event_type", _required_text(self.event_type, "event_type", limit=128))
        if not isinstance(self.hypothesis, Mapping) or not self.hypothesis:
            raise ValueError("hypothesis must be a non-empty object")
        object.__setattr__(self, "hypothesis", dict(self.hypothesis))
        object.__setattr__(
            self,
            "runtime_candidate_id",
            _required_text(self.runtime_candidate_id, "runtime_candidate_id", limit=512),
        )
        object.__setattr__(
            self,
            "runtime_candidate_digest",
            _digest_text(self.runtime_candidate_digest, "runtime_candidate_digest"),
        )
        object.__setattr__(
            self,
            "last_verified_digest",
            _digest_text(self.last_verified_digest, "last_verified_digest"),
        )
        for name in (
            "degraded_health_before",
            "degraded_health_after",
            "successful_health_before",
            "successful_health_after",
        ):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise ValueError(f"{name} must be an object")
            object.__setattr__(self, name, dict(value))
        if self.degraded_health_before.get("ok") is not True:
            raise ValueError("degraded_health_before must begin healthy")
        if self.degraded_health_after.get("ok") is not False:
            raise ValueError("degraded_health_after must deliberately demonstrate degradation")
        if self.successful_health_before.get("ok") is not True or self.successful_health_after.get("ok") is not True:
            raise ValueError("successful preview health must remain healthy")
        object.__setattr__(self, "rollback_reason", _required_text(self.rollback_reason, "rollback_reason", limit=1024))
        if self.version != FAULT_FIXTURE_VERSION:
            raise ValueError("unsupported fault fixture version")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DirectorChapter:
    chapter_id: str
    order: int
    title: str
    from_state: str
    to_state: str
    effect: str
    required_evidence: tuple[str, ...]
    six_slot_packet: Mapping[str, str]
    presenter_notes: tuple[str, ...]
    ui_directive: Mapping[str, Any] = field(default_factory=dict)
    consequential: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "chapter_id", _required_text(self.chapter_id, "chapter_id", limit=128).upper())
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise ValueError("chapter order must be a non-negative integer")
        object.__setattr__(self, "title", _required_text(self.title, "title", limit=256))
        object.__setattr__(self, "from_state", _required_text(self.from_state, "from_state", limit=128).upper())
        object.__setattr__(self, "to_state", _required_text(self.to_state, "to_state", limit=128).upper())
        if self.from_state == self.to_state:
            raise ValueError("chapter transition must advance to a distinct state")
        object.__setattr__(self, "effect", _required_text(self.effect, "effect", limit=128).upper())
        object.__setattr__(
            self,
            "required_evidence",
            _strings(self.required_evidence, "required_evidence"),
        )
        object.__setattr__(self, "six_slot_packet", _slots(self.six_slot_packet))
        object.__setattr__(
            self,
            "presenter_notes",
            _strings(self.presenter_notes, "presenter_notes", required=True),
        )
        if not isinstance(self.ui_directive, Mapping):
            raise ValueError("ui_directive must be an object")
        object.__setattr__(self, "ui_directive", dict(self.ui_directive))
        if not isinstance(self.consequential, bool):
            raise ValueError("consequential must be a boolean")

    @property
    def chapter_digest(self) -> str:
        return digest(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "chapter_digest": self.chapter_digest}


@dataclass(frozen=True)
class ConstructionFoundryDirectorManifest:
    chapters: tuple[DirectorChapter, ...]
    required_assets: tuple[RequiredAsset, ...]
    fault_fixture: ConstructionDemoFaultFixture
    runtime_profile_path: str
    confirmation_packet_path: str
    initial_state: str = "FRAME"
    terminal_state: str = "DISSOLVED"
    version: str = DIRECTOR_MANIFEST_VERSION

    def __post_init__(self) -> None:
        chapters = tuple(self.chapters)
        if not chapters:
            raise ValueError("Director manifest must contain chapters")
        if tuple(item.order for item in chapters) != tuple(range(len(chapters))):
            raise ValueError("Director chapter order must be contiguous from zero")
        ids = tuple(item.chapter_id for item in chapters)
        if len(ids) != len(set(ids)):
            raise ValueError("Director chapter IDs must be unique")
        for previous, current in zip(chapters, chapters[1:]):
            if previous.to_state != current.from_state:
                raise ValueError(
                    f"Director chain is discontinuous between {previous.chapter_id} and {current.chapter_id}"
                )
        initial = _required_text(self.initial_state, "initial_state", limit=128).upper()
        terminal = _required_text(self.terminal_state, "terminal_state", limit=128).upper()
        if chapters[0].from_state != initial or chapters[-1].to_state != terminal:
            raise ValueError("Director manifest endpoints do not match the chapter chain")
        assets = tuple(self.required_assets)
        if not assets or len({item.path for item in assets}) != len(assets):
            raise ValueError("Director required assets must be non-empty and unique")
        if not isinstance(self.fault_fixture, ConstructionDemoFaultFixture):
            raise ValueError("fault_fixture must be a ConstructionDemoFaultFixture")
        object.__setattr__(self, "chapters", chapters)
        object.__setattr__(self, "required_assets", assets)
        object.__setattr__(self, "initial_state", initial)
        object.__setattr__(self, "terminal_state", terminal)
        object.__setattr__(
            self,
            "runtime_profile_path",
            RequiredAsset(self.runtime_profile_path, "0" * 64).path,
        )
        object.__setattr__(
            self,
            "confirmation_packet_path",
            RequiredAsset(self.confirmation_packet_path, "0" * 64).path,
        )
        paths = {item.path for item in assets}
        if self.runtime_profile_path not in paths or self.confirmation_packet_path not in paths:
            raise ValueError("runtime profile and confirmation packet must be bound required assets")
        if self.version != DIRECTOR_MANIFEST_VERSION:
            raise ValueError("unsupported Director manifest version")

    @property
    def manifest_digest(self) -> str:
        return digest(
            {
                "version": self.version,
                "chapters": [item.to_dict() for item in self.chapters],
                "required_assets": [item.to_dict() for item in self.required_assets],
                "fault_fixture": self.fault_fixture.to_dict(),
                "runtime_profile_path": self.runtime_profile_path,
                "confirmation_packet_path": self.confirmation_packet_path,
                "initial_state": self.initial_state,
                "terminal_state": self.terminal_state,
            }
        )

    def chapter(self, chapter_id: str) -> DirectorChapter:
        target = _required_text(chapter_id, "chapter_id", limit=128).upper()
        rows = [item for item in self.chapters if item.chapter_id == target]
        if len(rows) != 1:
            raise ValueError(f"unknown Director chapter: {target}")
        return rows[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "manifest_digest": self.manifest_digest,
            "initial_state": self.initial_state,
            "terminal_state": self.terminal_state,
            "runtime_profile_path": self.runtime_profile_path,
            "confirmation_packet_path": self.confirmation_packet_path,
            "chapters": [item.to_dict() for item in self.chapters],
            "required_assets": [item.to_dict() for item in self.required_assets],
            "fault_fixture": self.fault_fixture.to_dict(),
            "offline_deterministic": True,
            "external_model_required": False,
            "internet_required": False,
            "random_generation": False,
            "human_review_required": True,
            "authority": {**_FALSE_AUTHORITY},
        }


def _chapter(
    order: int,
    chapter_id: str,
    title: str,
    from_state: str,
    to_state: str,
    effect: str,
    required: Sequence[str],
    slots: Sequence[str],
    notes: Sequence[str],
    *,
    ui: Mapping[str, Any] | None = None,
    consequential: bool = False,
) -> DirectorChapter:
    return DirectorChapter(
        chapter_id=chapter_id,
        order=order,
        title=title,
        from_state=from_state,
        to_state=to_state,
        effect=effect,
        required_evidence=tuple(required),
        six_slot_packet=dict(zip(_SLOT_KEYS, slots, strict=True)),
        presenter_notes=tuple(notes),
        ui_directive=dict(ui or {}),
        consequential=consequential,
    )


def build_default_manifest(
    required_assets: Sequence[RequiredAsset],
    *,
    runtime_profile_path: str,
    confirmation_packet_path: str,
    runtime_candidate_id: str = "construction-demo-b10-candidate",
) -> ConstructionFoundryDirectorManifest:
    candidate_id = _required_text(runtime_candidate_id, "runtime_candidate_id", limit=512)
    candidate_digest = runtime_binding_digest(candidate_id)
    fault = ConstructionDemoFaultFixture(
        fixture_id="construction-p4-pascal-selection-rebind",
        marker="Pascal selection changed while the synchronized as-built view retained the prior target.",
        event_type="PASCAL_SELECTION_SYNC_FAULT",
        hypothesis={
            "failure_class": "INTERFACE",
            "cause": "selection acknowledgement arrived after a newer synchronized view transition",
            "preservation": "Construction state and source geometry remain unchanged",
        },
        runtime_candidate_id=candidate_id,
        runtime_candidate_digest=candidate_digest,
        last_verified_digest=digest("construction-p4-last-verified-presentation"),
        degraded_health_before={"ok": True, "selection_synchronized": True, "resources_released": True},
        degraded_health_after={"ok": False, "selection_synchronized": False, "resources_released": True},
        successful_health_before={"ok": True, "selection_synchronized": True, "resources_released": True},
        successful_health_after={"ok": True, "selection_synchronized": True, "resources_released": True},
        rollback_reason="The deliberately degraded isolated preview lost exact selection synchronization.",
    )
    chapters = (
        _chapter(0, "FRAME_CONSTRUCTION", "Frame the Construction objective", "FRAME", "CONSTRUCTION_GROUNDED", "FRAME_CONSTRUCTION", ("p3_available", "construction_identity_bound"), ("construction_scene", "inspect", "spatial_projection", "selected_project", "presentation_only", "show_design"), ("Confirm that Aura remains the truth, evidence, and authority system.", "Introduce Pascal as the disposable geometry body."), ui={"active_view": "DESIGN"}),
        _chapter(1, "SHOW_FLOOR_PLAN", "Open the exact floor plan", "CONSTRUCTION_GROUNDED", "FLOORPLAN_READY", "SET_VIEW", ("pascal_artifact_bound", "coordinate_receipt_bound"), ("construction_storey", "inspect", "floorplan_projection", "selected_storey", "presentation_only", "show_floorplan"), ("Show the exact storey and node binding.",), ui={"active_view": "FLOOR_PLAN"}),
        _chapter(2, "SHOW_AS_BUILT", "Project the Aura-derived as-built state", "FLOORPLAN_READY", "AS_BUILT_READY", "SET_VIEW", ("as_built_scene_bound",), ("construction_scene", "compare", "evidence_projection", "selected_project", "derived_only", "show_as_built"), ("The as-built view is derived evidence, not survey truth.",), ui={"active_view": "AS_BUILT"}),
        _chapter(3, "COMPARE_REPRESENTATIONS", "Compare design and as-built", "AS_BUILT_READY", "COMPARE_READY", "SET_VIEW", ("compare_receipt_bound",), ("construction_scene", "compare", "synchronized_projection", "selected_target", "review_only", "compare_representations"), ("Keep the Pascal and Aura renderers technically separate.",), ui={"active_view": "COMPARE"}),
        _chapter(4, "REVIEW_CANDIDATES", "Review bounded Construction alternatives", "COMPARE_READY", "CANDIDATES_READY", "FOCUS_CANDIDATES", ("construction_candidates_bound", "domain_decision_bound"), ("construction_plan", "assess", "coordination_candidate", "authorized_reviewer", "proposal_only", "compare_candidate"), ("Ready for human review is not approval.",), ui={"panel": "coordination_candidates"}),
        _chapter(5, "AURA_WATCH_THIS", "Aura, watch this", "CANDIDATES_READY", "CAPTURE_ACTIVE", "START_CAPTURE", ("identity_current", "operator_authorized"), ("foundry_session", "bounded_observe", "incident_capture", "human_operator", "explicitly_authorized", "start_capture"), ("Start one explicit bounded capture; unrestricted recording remains off.",), consequential=True),
        _chapter(6, "MARK_INCIDENT", "Mark the exact presentation fault", "CAPTURE_ACTIVE", "INCIDENT_MARKED", "MARK_INCIDENT", ("capture_active", "fault_fixture_bound"), ("foundry_session", "observe", "incident_marker", "human_operator", "attest", "mark_incident"), ("The fixture demonstrates an interface fault, not a Construction decision.",), consequential=True),
        _chapter(7, "FINALIZE_REPLAY", "Dissolve capture and retain replay", "INCIDENT_MARKED", "REPLAY_READY", "FINALIZE_CAPTURE", ("incident_marker_present", "required_assets_bound"), ("foundry_session", "finalize", "verified_replay_packet", "retained_incident", "evidence_only", "compile_replay"), ("Listeners, timers, and buffers dissolve before replay.",), consequential=True),
        _chapter(8, "RUN_RUNTIME_V2", "Run exact Runtime Profile V2 replay", "REPLAY_READY", "RUNTIME_PROVEN", "RUN_RUNTIME_REPLAY", ("capture_dissolved", "replay_packet_retained"), ("runtime_profile", "reproduce", "verified_replay", "retained_incident", "evidence_only", "execute_replay"), ("Consume the retained proof reference; never trust a browser readiness boolean.",), consequential=True),
        _chapter(9, "ROUTE_REPAIR", "Derive the repair route", "RUNTIME_PROVEN", "REPAIR_ASSESSED", "RECORD_REPAIR_ATTEMPT", ("runtime_proof_retained",), ("repair_plan", "assess", "software_repair", "verified_candidate", "proposal_only", "derive_route"), ("Local failures return to Surgeon; structural failures return to Council.",), consequential=True),
        _chapter(10, "DEGRADED_PREVIEW", "Demonstrate exact rollback", "REPAIR_ASSESSED", "ROLLBACK_DEMONSTRATED", "PREVIEW_DEGRADED", ("repair_attempt_retained", "rollback_adapter_ready"), ("isolated_environment", "preview", "software_repair", "verified_candidate", "proposal_only", "preview_candidate"), ("The fixture deliberately degrades in isolation and restores the exact last verified digest.",), consequential=True),
        _chapter(11, "SUCCESSFUL_PREVIEW", "Demonstrate successful isolated preview", "ROLLBACK_DEMONSTRATED", "PREVIEWED", "PREVIEW_SUCCESS", ("rollback_receipt_retained",), ("isolated_environment", "preview", "software_repair", "verified_candidate", "proposal_only", "preview_candidate"), ("A successful preview remains proposal-only and cannot deploy itself.",), consequential=True),
        _chapter(12, "CURRENT_REPROOF", "Run P0, P1, current reproof, and disposition", "PREVIEWED", "REPROOF_RETAINED", "RUN_GOVERNED_U7", ("successful_preview_retained", "u7_bridge_ready"), ("continuity", "reprove", "governed_learning", "verified_repair", "human_review_required", "current_reproof"), ("Canonical U7 remains the only learning-to-reproof owner.",), consequential=True),
        _chapter(13, "RETURN_TO_CONSTRUCTION", "Return to Construction without changing truth", "REPROOF_RETAINED", "CONSTRUCTION_RETURNED", "RETURN_CONSTRUCTION", ("human_disposition_retained",), ("construction_scene", "inspect", "spatial_projection", "selected_project", "presentation_only", "return_to_construction"), ("The software repair lane cannot approve physical work or mutate Construction state.",), ui={"active_view": "COMPARE"}),
        _chapter(14, "DISSOLVE", "Dissolve the presentation session", "CONSTRUCTION_RETURNED", "DISSOLVED", "DISSOLVE", ("construction_state_unchanged", "capture_resources_dissolved"), ("presentation_session", "terminate", "lifecycle_cleanup", "active_session", "mandatory", "dissolve"), ("Finish with exact cleanup and a separately governed human review decision.",), consequential=True),
    )
    return ConstructionFoundryDirectorManifest(
        chapters=chapters,
        required_assets=tuple(required_assets),
        fault_fixture=fault,
        runtime_profile_path=runtime_profile_path,
        confirmation_packet_path=confirmation_packet_path,
    )


@dataclass
class DirectorSession:
    session_id: str
    manifest_digest: str
    identity_digest: str
    construction_state_digest: str
    current_state: str
    selected_index: int = -1
    executed_index: int = -1
    sequence: int = 0
    playing: bool = False
    dissolved: bool = False
    p3_sync_pending: bool = False
    evidence: dict[str, bool] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    receipts: list[dict[str, Any]] = field(default_factory=list)

    def snapshot(self, manifest: ConstructionFoundryDirectorManifest) -> dict[str, Any]:
        next_index = self.executed_index + 1
        next_chapter = manifest.chapters[next_index].chapter_id if next_index < len(manifest.chapters) else None
        selected = (
            manifest.chapters[self.selected_index].chapter_id
            if 0 <= self.selected_index < len(manifest.chapters)
            else None
        )
        return {
            "version": DIRECTOR_VERSION,
            "session_id": self.session_id,
            "manifest_digest": self.manifest_digest,
            "identity_digest": self.identity_digest,
            "construction_state_digest": self.construction_state_digest,
            "current_state": self.current_state,
            "selected_chapter_id": selected,
            "next_chapter_id": next_chapter,
            "selected_index": self.selected_index,
            "executed_index": self.executed_index,
            "sequence": self.sequence,
            "playing": self.playing,
            "dissolved": self.dissolved,
            "evidence": dict(sorted(self.evidence.items())),
            "context": dict(self.context),
            "receipt_count": len(self.receipts),
            "p3_sync_pending": self.p3_sync_pending,
            "human_review_required": True,
            "authority": {**_FALSE_AUTHORITY},
        }


class ConstructionFoundryDirector:
    """Thread-safe guarded Director state; canonical effects are injected by the server."""

    def __init__(self, manifest: ConstructionFoundryDirectorManifest) -> None:
        if not isinstance(manifest, ConstructionFoundryDirectorManifest):
            raise ValueError("manifest must be a ConstructionFoundryDirectorManifest")
        self.manifest = manifest
        self._lock = threading.RLock()
        self._sessions: dict[str, DirectorSession] = {}
        self._transition_claims: dict[str, tuple[str, str]] = {}  # session_id → (transition_digest, claim_token)

    def start_session(
        self,
        *,
        identity_digest: str,
        construction_state_digest: str,
        initial_evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        identity = _digest_text(identity_digest, "identity_digest")
        state = _state_digest_text(construction_state_digest, "construction_state_digest")
        evidence = {str(key): value is True for key, value in dict(initial_evidence).items()}
        session_id = "P4-" + digest(
            {
                "manifest_digest": self.manifest.manifest_digest,
                "identity_digest": identity,
                "construction_state_digest": state,
            }
        )[:24]
        with self._lock:
            existing = self._sessions.get(session_id)
            if existing is not None and not existing.dissolved:
                raise ValueError("an active Director session already exists for these exact identities")
            if len(self._sessions) >= MAX_SESSIONS:
                dissolved = [key for key, item in self._sessions.items() if item.dissolved]
                if not dissolved:
                    raise ValueError("Director session budget exhausted")
                self._sessions.pop(dissolved[0], None)
            session = DirectorSession(
                session_id=session_id,
                manifest_digest=self.manifest.manifest_digest,
                identity_digest=identity,
                construction_state_digest=state,
                current_state=self.manifest.initial_state,
                evidence=evidence,
            )
            self._sessions[session_id] = session
            return session.snapshot(self.manifest)

    def require_session(self, session_id: str) -> DirectorSession:
        key = _required_text(session_id, "session_id", limit=128)
        with self._lock:
            session = self._sessions.get(key)
            if session is None:
                raise ValueError("Director session not found")
            return session

    def update_evidence(self, session_id: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(evidence, Mapping):
            raise ValueError("evidence must be an object")
        session = self.require_session(session_id)
        with self._lock:
            for key, value in evidence.items():
                if not isinstance(key, str) or not key.strip() or not isinstance(value, bool):
                    raise ValueError("evidence entries must be non-empty string keys and exact booleans")
                session.evidence[key.strip()] = value
            return session.snapshot(self.manifest)

    def project_next(self, session_id: str) -> dict[str, Any]:
        session = self.require_session(session_id)
        with self._lock:
            return self._project_next_locked(session)

    def claim_next(self, session_id: str) -> dict[str, Any]:
        """Atomically project and reserve the next transition for this session."""
        session = self.require_session(session_id)
        with self._lock:
            # Block progression if a P3 presentation sync is still pending.
            if session.p3_sync_pending:
                raise ValueError(
                    "Director progression blocked: P3 presentation sync "
                    "acknowledgement is pending"
                )
            # Fail closed if a claim is already active for this session.
            if session.session_id in self._transition_claims:
                raise ValueError(
                    "Director transition is already claimed by another "
                    "in-flight request for this session"
                )
            projection = self._project_next_locked(session)
            if projection.get("admitted") is True:
                claim_token = secrets.token_hex(16)
                self._transition_claims[session.session_id] = (
                    projection["transition_digest"],
                    claim_token,
                )
                projection["claim_token"] = claim_token
            return projection

    def release_claim(self, session_id: str, *, claim_token: str = "") -> None:
        """Release an active transition claim only if the token matches.

        Requires a non-empty claim_token.  A missing or mismatched token
        is a no-op (fail-closed) so a stale or unauthenticated error path
        cannot remove another request's claim.
        """
        with self._lock:
            active = self._transition_claims.get(session_id)
            if active is not None:
                _expected_digest, expected_token = active
                if not claim_token or expected_token != claim_token:
                    return  # Token missing or mismatch — fail closed
                self._transition_claims.pop(session_id, None)

    def record_failure_ledger(self, session_id: str, entry: Mapping[str, Any]) -> None:
        """Atomically record a failure-ledger entry under the Director lock.

        Used for orphan-cleanup traceability when a transition fails after
        a canonical owner has produced artifacts.
        """
        with self._lock:
            session = self.require_session(session_id)
            ledger = session.context.setdefault("_failure_ledger", [])
            ledger.append(dict(entry))

    def acknowledge_p3_sync(
        self,
        session_id: str,
        *,
        presentation_receipt: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Acknowledge that the P3 presentation sync has completed.

        Validates that the supplied receipt binds to the session's last
        committed chapter, the manifest-required active_view, and the
        session identity, and that receipt_digest is present.

        Digest provenance is NOT verified here.  The caller must validate
        the receipt against the P3-retained record before calling this
        method; see the ack-p3-sync route.
        """
        session = self.require_session(session_id)
        with self._lock:
            if not session.p3_sync_pending:
                raise ValueError("no P3 presentation sync is pending for this session")
            if not isinstance(presentation_receipt, Mapping):
                raise ValueError("P3 presentation receipt must be an object")
            # Validate the receipt is bound to the last committed chapter.
            if not session.receipts:
                raise ValueError("no committed chapter receipt to acknowledge against")
            last_receipt = session.receipts[-1]
            expected_chapter_id = presentation_receipt.get("chapter_id")
            if expected_chapter_id != last_receipt.get("chapter_id"):
                raise ValueError(
                    "P3 presentation receipt chapter_id does not match the "
                    "last committed chapter"
                )
            expected_view = presentation_receipt.get("active_view")
            # Resolve the required view from the manifest chapter definition,
            # not from the committed receipt (which does not contain a
            # "chapter" key — only chapter_id, chapter_digest, etc.).
            required_chapter = self.manifest.chapter(last_receipt.get("chapter_id", ""))
            required_view = dict(required_chapter.ui_directive or {}).get("active_view")
            if required_view and expected_view != required_view:
                raise ValueError(
                    "P3 presentation receipt active_view does not match the "
                    "required presentation view"
                )
            # Validate the receipt is bound to the session identity.
            receipt_identity = str(presentation_receipt.get("identity_digest") or "")
            if not receipt_identity:
                raise ValueError(
                    "P3 presentation receipt must include a non-empty identity_digest"
                )
            if receipt_identity != session.identity_digest:
                raise ValueError(
                    "P3 presentation receipt identity does not match the session"
                )
            # Validate the receipt includes a P3-issued receipt digest.
            receipt_digest = str(presentation_receipt.get("receipt_digest") or "")
            if not receipt_digest:
                raise ValueError(
                    "P3 presentation receipt must include a non-empty receipt_digest"
                )
            session.p3_sync_pending = False
            return {"ok": True, "session": session.snapshot(self.manifest)}

    def _project_next_locked(self, session: DirectorSession) -> dict[str, Any]:
        """Project the next chapter transition.  Caller must hold self._lock."""
        next_index = session.executed_index + 1
        if next_index >= len(self.manifest.chapters):
            return {
                "admitted": False,
                "terminal": True,
                "missing_evidence": [],
                "next_chapter": None,
                "session": session.snapshot(self.manifest),
            }
        chapter = self.manifest.chapters[next_index]
        if chapter.from_state != session.current_state:
            raise ValueError("Director session state differs from the manifest chain")
        missing = [name for name in chapter.required_evidence if session.evidence.get(name) is not True]
        projection = {
            "version": DIRECTOR_RECEIPT_VERSION,
            "manifest_digest": self.manifest.manifest_digest,
            "session_id": session.session_id,
            "sequence": session.sequence + 1,
            "chapter": chapter.to_dict(),
            "from_state": session.current_state,
            "to_state": chapter.to_state,
            "missing_evidence": missing,
            "admitted": not missing,
            "recommended": not missing,
            "execution_authority": False,
            "construction_state_mutation": False,
            "human_review_required": True,
            "authority": {**_FALSE_AUTHORITY},
        }
        projection["transition_digest"] = digest(projection)
        return {**projection, "session": session.snapshot(self.manifest)}

    def commit_next(
        self,
        session_id: str,
        *,
        transition_digest: str,
        effect_receipt: Mapping[str, Any],
        claim_token: str = "",
        evidence_updates: Mapping[str, Any] | None = None,
        context_updates: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Validate everything before acquiring the lock or mutating anything.
        # This ensures no session state changes on rejection.
        if not isinstance(effect_receipt, Mapping):
            raise ValueError("effect_receipt must be an object")
        if effect_receipt.get("ok") is not True:
            raise ValueError("canonical chapter effect did not return an exact successful receipt")
        if evidence_updates:
            for key, value in evidence_updates.items():
                if not isinstance(key, str) or not isinstance(value, bool):
                    raise ValueError("evidence_updates must contain exact boolean evidence")
        if context_updates is not None and not isinstance(context_updates, Mapping):
            raise ValueError("context_updates must be an object")
        # Single critical section: project, validate, and commit atomically
        # so a consequential chapter cannot commit twice and no mutations
        # occur if any validation or budget check fails.
        with self._lock:
            session = self.require_session(session_id)
            # Require an active claim with a matching token.  Reject absent,
            # stale, or mismatched claims to enforce the reservation contract.
            active_claim = self._transition_claims.get(session.session_id)
            if active_claim is None:
                raise ValueError(
                    "Director commit rejected: no active transition claim; "
                    "call claim_next before executing the chapter effect"
                )
            expected_digest, expected_token = active_claim
            if expected_digest != transition_digest or expected_token != claim_token:
                raise ValueError(
                    "Director transition claim is stale or mismatched: another "
                    "request already claimed or committed this chapter"
                )
            # Re-project inside the lock to get the current expected transition
            expected = self._project_next_locked(session)
            if expected.get("admitted") is not True:
                raise ValueError(f"Director transition is blocked by evidence: {expected.get('missing_evidence')}")
            if _digest_text(transition_digest, "transition_digest") != expected["transition_digest"]:
                raise ValueError("Director transition digest is stale or mismatched")
            chapter = self.manifest.chapters[session.executed_index + 1]
            # Check budget BEFORE appending or mutating anything
            if len(session.receipts) + 1 > MAX_RECEIPTS:
                raise ValueError("Director receipt budget exhausted")
            receipt = {
                "version": DIRECTOR_RECEIPT_VERSION,
                "session_id": session.session_id,
                "manifest_digest": self.manifest.manifest_digest,
                "sequence": session.sequence + 1,
                "chapter_id": chapter.chapter_id,
                "chapter_digest": chapter.chapter_digest,
                "transition_digest": transition_digest,
                "from_state": chapter.from_state,
                "to_state": chapter.to_state,
                "six_slot_packet": dict(chapter.six_slot_packet),
                "effect": chapter.effect,
                "effect_receipt": dict(effect_receipt),
                "construction_state_digest_before": session.construction_state_digest,
                "construction_state_digest_after": session.construction_state_digest,
                "construction_state_unchanged": True,
                "human_review_required": True,
                "authority": {**_FALSE_AUTHORITY},
            }
            receipt["receipt_digest"] = digest(receipt)
            session.sequence += 1
            session.executed_index += 1
            session.selected_index = session.executed_index
            session.current_state = chapter.to_state
            if evidence_updates:
                for key, value in evidence_updates.items():
                    session.evidence[key] = value
            if context_updates:
                session.context.update(dict(context_updates))
            session.receipts.append(receipt)
            session.dissolved = chapter.to_state == self.manifest.terminal_state
            if session.dissolved:
                session.playing = False
            # Mark P3 sync as pending for presentation chapters that carry
            # a ui_directive with an active_view, so progression is blocked
            # until the browser acknowledges the sync.
            ui = dict(chapter.ui_directive) if chapter.ui_directive else {}
            session.p3_sync_pending = bool(ui.get("active_view"))
            # Clear the transition claim after successful commit
            self._transition_claims.pop(session.session_id, None)
            return {"ok": True, "receipt": receipt, "session": session.snapshot(self.manifest)}

    def control(
        self,
        session_id: str,
        *,
        control: DirectorControl | str,
        chapter_id: str = "",
    ) -> dict[str, Any]:
        try:
            action = control if isinstance(control, DirectorControl) else DirectorControl(str(control).upper())
        except ValueError as exc:
            raise ValueError(f"unsupported Director control: {control}") from exc
        session = self.require_session(session_id)
        with self._lock:
            # Guard: block PLAY, NEXT, and JUMP while P3 presentation sync
            # is pending.  PAUSE and PREVIOUS are safe because they do not
            # advance progression or execute effects.
            if session.p3_sync_pending and action in (
                DirectorControl.PLAY,
                DirectorControl.NEXT,
                DirectorControl.JUMP,
            ):
                raise ValueError(
                    "Director control blocked: P3 presentation sync is "
                    "pending — acknowledge the sync before advancing"
                )
            if action is DirectorControl.PLAY:
                if session.dissolved:
                    raise ValueError("a dissolved session must be restarted before Play")
                session.playing = True
            elif action is DirectorControl.PAUSE:
                session.playing = False
            elif action is DirectorControl.PREVIOUS:
                session.playing = False
                session.selected_index = max(-1, session.selected_index - 1)
            elif action is DirectorControl.NEXT:
                if session.selected_index < session.executed_index:
                    session.selected_index += 1
            elif action is DirectorControl.JUMP:
                target = self.manifest.chapter(chapter_id)
                if target.order > session.executed_index:
                    raise ValueError("chapter jump cannot execute or skip unproven chapters")
                session.playing = False
                session.selected_index = target.order
            elif action is DirectorControl.RESTART:
                if not session.dissolved:
                    raise ValueError("Restart requires the prior presentation session to be dissolved")
                session.current_state = self.manifest.initial_state
                session.selected_index = -1
                session.executed_index = -1
                session.sequence = 0
                session.playing = False
                session.dissolved = False
                session.p3_sync_pending = False
                session.context.clear()
                session.receipts.clear()
                session.evidence = {
                    key: value
                    for key, value in session.evidence.items()
                    if key in {
                        "p3_available",
                        "construction_identity_bound",
                        "pascal_artifact_bound",
                        "coordinate_receipt_bound",
                        "as_built_scene_bound",
                        "compare_receipt_bound",
                        "construction_candidates_bound",
                        "domain_decision_bound",
                        "identity_current",
                        "operator_authorized",
                        "fault_fixture_bound",
                        "required_assets_bound",
                        "rollback_adapter_ready",
                        "u7_bridge_ready",
                        "construction_state_unchanged",
                        "capture_resources_dissolved",
                    }
                }
            return {"ok": True, "control": action.value, "session": session.snapshot(self.manifest)}

    def receipts(self, session_id: str) -> tuple[dict[str, Any], ...]:
        session = self.require_session(session_id)
        with self._lock:
            return tuple(dict(item) for item in session.receipts)

    def close(self) -> None:
        with self._lock:
            for session in self._sessions.values():
                session.context.clear()
                session.receipts.clear()
                session.playing = False
                session.dissolved = True
            self._sessions.clear()
            self._transition_claims.clear()


__all__ = [
    "ConstructionDemoFaultFixture",
    "ConstructionFoundryDirector",
    "ConstructionFoundryDirectorManifest",
    "DirectorChapter",
    "DirectorControl",
    "DirectorSession",
    "RequiredAsset",
    "build_default_manifest",
    "canonical_bytes",
    "digest",
    "runtime_binding_digest",
]
