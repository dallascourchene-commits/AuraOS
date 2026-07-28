"""Bounded B11-B15 bilateral live-repair adapter.

Composes Aura's existing Attempt Archive, Runtime Harness, Crucible and U7
reproof owners. It grants no patch, publication, deployment, professional,
physical-work, merge, or learning-promotion authority.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import time
from typing import Any, Iterable, Mapping, Sequence

VERSION = "AURA_BILATERAL_LIVE_REPAIR_FOUNDRY_V1"
MAX_EVENTS = 256
MAX_ATTEMPTS = 8
_SECRET_KEY = re.compile(
    r"secret|token|password|authorization|cookie|api[_-]?key|private[_-]?key",
    re.I,
)
_SECRET_VALUE = re.compile(
    r"sk-[\w-]{12,}|Bearer\s+[\w.~/+-]+=*|gh[pousr]_[A-Za-z0-9]{20,}"
)


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require_digest(name: str, value: str) -> str:
    value = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name} must be a sha256 digest")
    return value


def require_text(name: str, value: str, limit: int = 512) -> str:
    value = str(value or "").strip()
    if not value or len(value) > limit:
        raise ValueError(f"invalid {name}")
    return value


def sanitize(value: Any, depth: int = 0) -> tuple[Any, tuple[str, ...]]:
    if depth > 10:
        return "[MAX_DEPTH]", ("max_depth",)
    redactions: set[str] = set()
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in list(value.items())[:128]:
            key = str(key)[:160]
            if _SECRET_KEY.search(key):
                out[key] = "[REDACTED]"
                redactions.add(key)
            else:
                out[key], nested = sanitize(item, depth + 1)
                redactions.update(nested)
        if len(value) > 128:
            out["__truncated_items__"] = len(value) - 128
        return out, tuple(sorted(redactions))
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in list(value)[:256]:
            clean, nested = sanitize(item, depth + 1)
            out.append(clean)
            redactions.update(nested)
        return out, tuple(sorted(redactions))
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if isinstance(value, str):
        bounded = value[:32768]
        clean = _SECRET_VALUE.sub("[REDACTED]", bounded)
        return clean, (("secret_pattern",) if clean != bounded else ())
    if value is None or isinstance(value, (bool, int, float)):
        return value, ()
    return str(value)[:32768], ()


@dataclass(frozen=True)
class BilateralIdentity:
    intent_digest: str
    confirmation_digest: str
    semantic_ledger_digest: str
    guardrail_set_digest: str
    intent_revision_id: str
    repository_head: str
    source_tree_digest: str
    runtime_profile_digest: str

    def __post_init__(self) -> None:
        for name in (
            "intent_digest",
            "confirmation_digest",
            "semantic_ledger_digest",
            "guardrail_set_digest",
            "source_tree_digest",
            "runtime_profile_digest",
        ):
            object.__setattr__(self, name, require_digest(name, getattr(self, name)))
        object.__setattr__(
            self,
            "intent_revision_id",
            require_text("intent_revision_id", self.intent_revision_id),
        )
        object.__setattr__(
            self,
            "repository_head",
            require_text("repository_head", self.repository_head, 128),
        )

    @property
    def identity_digest(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class IncidentEvent:
    sequence: int
    event_type: str
    observed_at: float
    payload: Mapping[str, Any]
    payload_digest: str
    redactions: tuple[str, ...] = ()


@dataclass(frozen=True)
class IncidentReplayPacket:
    packet_id: str
    identity: BilateralIdentity
    release_id: str
    environment_id: str
    marker: str
    events: tuple[IncidentEvent, ...]
    expected_positive: tuple[str, ...]
    expected_negative: tuple[str, ...]
    preservation_claims: tuple[str, ...]
    created_at: float
    packet_digest: str
    authority: Mapping[str, bool]


class BoundedIncidentCapture:
    def __init__(
        self,
        *,
        identity: BilateralIdentity,
        release_id: str,
        environment_id: str,
    ) -> None:
        self.identity = identity
        self.release_id = require_text("release_id", release_id)
        self.environment_id = require_text("environment_id", environment_id)
        self._events: list[IncidentEvent] = []
        self._marked = False
        self._closed = False

    def observe(
        self,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        *,
        observed_at: float | None = None,
    ) -> IncidentEvent:
        if self._closed:
            raise RuntimeError("capture is closed")
        clean, redactions = sanitize(dict(payload or {}))
        event = IncidentEvent(
            len(self._events),
            require_text("event_type", event_type),
            float(time.time() if observed_at is None else observed_at),
            clean,
            digest(clean),
            redactions,
        )
        self._events.append(event)
        if len(self._events) > MAX_EVENTS:
            retained = self._events[-MAX_EVENTS:]
            self._events = [
                IncidentEvent(
                    index,
                    item.event_type,
                    item.observed_at,
                    item.payload,
                    item.payload_digest,
                    item.redactions,
                )
                for index, item in enumerate(retained)
            ]
        return event

    def mark_incident(
        self,
        marker: str,
        payload: Mapping[str, Any] | None = None,
    ) -> IncidentEvent:
        if self._marked:
            raise RuntimeError("incident already marked")
        self._marked = True
        return self.observe(
            "INCIDENT_MARKER",
            {"marker": require_text("marker", marker), **dict(payload or {})},
        )

    def finalize(
        self,
        *,
        expected_positive: Iterable[str],
        expected_negative: Iterable[str],
        preservation_claims: Iterable[str],
    ) -> IncidentReplayPacket:
        if self._closed:
            raise RuntimeError("capture is closed")
        if not self._marked:
            raise ValueError("incident marker is required")
        positive = tuple(
            dict.fromkeys(require_text("positive", item) for item in expected_positive)
        )
        negative = tuple(
            dict.fromkeys(require_text("negative", item) for item in expected_negative)
        )
        preservation = tuple(
            dict.fromkeys(
                require_text("preservation", item) for item in preservation_claims
            )
        )
        if not positive or not negative or not preservation:
            raise ValueError(
                "positive, negative, and preservation obligations are required"
            )
        marker = next(
            str(item.payload.get("marker", ""))
            for item in self._events
            if item.event_type == "INCIDENT_MARKER"
        )
        body = {
            "version": VERSION,
            "identity": asdict(self.identity),
            "release_id": self.release_id,
            "environment_id": self.environment_id,
            "marker": marker,
            "events": [asdict(item) for item in self._events],
            "positive": positive,
            "negative": negative,
            "preservation": preservation,
        }
        packet_hash = digest(body)
        events = tuple(self._events)
        self._events.clear()
        self._closed = True
        return IncidentReplayPacket(
            f"IRP-{packet_hash[:24]}",
            self.identity,
            self.release_id,
            self.environment_id,
            marker,
            events,
            positive,
            negative,
            preservation,
            time.time(),
            packet_hash,
            {
                "patch": False,
                "commit": False,
                "push": False,
                "pull_request": False,
                "merge": False,
                "deployment": False,
                "production_mutation": False,
                "professional": False,
                "physical_work": False,
                "learning_promotion": False,
                "human_review_required": True,
            },
        )


@dataclass(frozen=True)
class RepairCandidateResult:
    attempt_id: str
    hypothesis_digest: str
    candidate_digest: str
    replay_packet_digest: str
    positive_passed: bool
    negative_passed: bool
    preservation_passed: bool
    adjacent_regressions_passed: bool
    minimized_counterexample: Mapping[str, Any] | None
    failure_class: str
    created_at: float
    promotion_ready: bool


class BoundedRepairFoundry:
    def __init__(
        self,
        replay_packet: IncidentReplayPacket,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        if not 1 <= max_attempts <= MAX_ATTEMPTS:
            raise ValueError("invalid max_attempts")
        self.replay_packet = replay_packet
        self.max_attempts = max_attempts
        self._seen: set[str] = set()
        self._attempts: list[RepairCandidateResult] = []

    @property
    def attempts(self) -> tuple[RepairCandidateResult, ...]:
        return tuple(self._attempts)

    def record_candidate(
        self,
        *,
        hypothesis: Mapping[str, Any],
        candidate_digest: str,
        positive_passed: bool,
        negative_passed: bool,
        preservation_passed: bool,
        adjacent_regressions_passed: bool,
        minimized_counterexample: Mapping[str, Any] | None = None,
        failure_class: str = "",
    ) -> RepairCandidateResult:
        if len(self._attempts) >= self.max_attempts:
            raise RuntimeError("repair attempt budget exhausted")
        hypothesis_hash = digest(hypothesis)
        if hypothesis_hash in self._seen:
            raise ValueError("repeated failed hypothesis is forbidden")
        self._seen.add(hypothesis_hash)
        ready = all(
            (
                positive_passed,
                negative_passed,
                preservation_passed,
                adjacent_regressions_passed,
            )
        )
        counterexample, _ = (
            sanitize(minimized_counterexample)
            if minimized_counterexample is not None
            else (None, ())
        )
        result = RepairCandidateResult(
            f"RA-{len(self._attempts) + 1:03d}-{hypothesis_hash[:12]}",
            hypothesis_hash,
            require_digest("candidate_digest", candidate_digest),
            self.replay_packet.packet_digest,
            bool(positive_passed),
            bool(negative_passed),
            bool(preservation_passed),
            bool(adjacent_regressions_passed),
            counterexample,
            str(failure_class or ("" if ready else "CONTRACT_UNSATISFIED"))[:160],
            time.time(),
            ready,
        )
        self._attempts.append(result)
        return result


@dataclass(frozen=True)
class PreviewReceipt:
    preview_id: str
    candidate_digest: str
    last_verified_digest: str
    health_before_digest: str
    health_after_digest: str
    rollback_triggered: bool
    rollback_reason: str
    human_promotion_required: bool = True
    production_mutation: bool = False


def build_preview_receipt(
    *,
    candidate_digest: str,
    last_verified_digest: str,
    health_before: Mapping[str, Any],
    health_after: Mapping[str, Any],
    rollback_triggered: bool,
    rollback_reason: str = "",
) -> PreviewReceipt:
    candidate = require_digest("candidate_digest", candidate_digest)
    verified = require_digest("last_verified_digest", last_verified_digest)
    if rollback_triggered and not rollback_reason.strip():
        raise ValueError("rollback_reason is required")
    key = digest(
        {
            "candidate": candidate,
            "verified": verified,
            "before": health_before,
            "after": health_after,
        }
    )
    return PreviewReceipt(
        f"PREVIEW-{key[:24]}",
        candidate,
        verified,
        digest(health_before),
        digest(health_after),
        bool(rollback_triggered),
        rollback_reason[:500],
    )


@dataclass(frozen=True)
class CurrentReproofReceipt:
    reproof_id: str
    identity_digest: str
    replay_packet_digest: str
    candidate_digest: str
    p0_positive: bool
    p0_negative: bool
    p1_guardrail: bool
    p1_preservation: bool
    independent_verifier_id: str
    human_community_disposition: str
    relationship_experience_ref: str
    qdkt_eligible: bool
    durable_learning_authorized: bool


def build_current_reproof(
    *,
    identity: BilateralIdentity,
    replay_packet_digest: str,
    candidate_digest: str,
    p0_positive: bool,
    p0_negative: bool,
    p1_guardrail: bool,
    p1_preservation: bool,
    independent_verifier_id: str,
    human_community_disposition: str,
    relationship_experience_ref: str = "",
    qdkt_eligible: bool = False,
) -> CurrentReproofReceipt:
    replay = require_digest("replay_packet_digest", replay_packet_digest)
    candidate = require_digest("candidate_digest", candidate_digest)
    verifier = require_text("independent_verifier_id", independent_verifier_id)
    disposition = str(human_community_disposition).strip().upper()
    if disposition not in {"CONFIRMED", "REJECTED", "DEFERRED"}:
        raise ValueError("invalid human_community_disposition")
    durable = (
        all((p0_positive, p0_negative, p1_guardrail, p1_preservation))
        and disposition == "CONFIRMED"
        and bool(relationship_experience_ref)
    )
    eligible = bool(qdkt_eligible and durable)
    key = digest(
        {
            "identity": identity.identity_digest,
            "replay": replay,
            "candidate": candidate,
            "verifier": verifier,
            "disposition": disposition,
            "experience": relationship_experience_ref,
        }
    )
    return CurrentReproofReceipt(
        f"REPROOF-{key[:24]}",
        identity.identity_digest,
        replay,
        candidate,
        bool(p0_positive),
        bool(p0_negative),
        bool(p1_guardrail),
        bool(p1_preservation),
        verifier,
        disposition,
        relationship_experience_ref,
        eligible,
        durable,
    )


def build_spatial_foundry_projection(
    *,
    identity: BilateralIdentity,
    incident: IncidentReplayPacket,
    attempts: Sequence[RepairCandidateResult],
    preview: PreviewReceipt | None,
    reproof: CurrentReproofReceipt | None,
    intent: Mapping[str, Any],
    plan: Mapping[str, Any],
    code_targets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    key = digest(
        {
            "identity": identity.identity_digest,
            "incident": incident.packet_digest,
            "attempts": [item.attempt_id for item in attempts],
            "preview": preview.preview_id if preview else "",
            "reproof": reproof.reproof_id if reproof else "",
        }
    )
    return {
        "version": VERSION,
        "projection_only": True,
        "identity": {
            **asdict(identity),
            "identity_digest": identity.identity_digest,
        },
        "intent": dict(intent),
        "negative_intent": list(incident.expected_negative),
        "guardrails": list(incident.preservation_claims),
        "plan": dict(plan),
        "code_targets": [dict(item) for item in code_targets],
        "live_runtime": {
            "release_id": incident.release_id,
            "environment_id": incident.environment_id,
            "incident_marker": incident.marker,
            "event_count": len(incident.events),
        },
        "failures": [asdict(item) for item in attempts if not item.promotion_ready],
        "proof": {
            "incident_packet_digest": incident.packet_digest,
            "attempts": [asdict(item) for item in attempts],
            "preview": asdict(preview) if preview else None,
            "current_reproof": asdict(reproof) if reproof else None,
        },
        "human_approvals": {
            "promotion_required": True,
            "community_disposition": (
                reproof.human_community_disposition if reproof else "PENDING"
            ),
        },
        "authority": {
            "visual_truth": False,
            "patch": False,
            "commit": False,
            "push": False,
            "pull_request": False,
            "merge": False,
            "deployment": False,
            "production_mutation": False,
            "professional": False,
            "physical_work": False,
            "learning_promotion": False,
        },
        "projection_digest": key,
    }
