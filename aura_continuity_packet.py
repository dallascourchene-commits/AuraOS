"""Canonical advisory J2 continuity packets for AuraOS.

J2 consolidates compact route/JSpace state and Arena phase state behind one
digest-bound packet while retaining J0 and J1 compatibility parsing. The packet
contains labels, references, digests, counts, and authority constants only. It
never carries exact evidence, policy bodies, leases, board state, private
reasoning, secrets, or execution authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import base64
import binascii
import json
import re
from typing import Any

from aura_event_contracts import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    canonical_json,
    sanitize_payload,
    stable_digest,
)

J2_CONTINUITY_VERSION = "AURA_CONTINUITY_PACKET_J2"
J2_PACKET_PREFIX = "J2/"
J2_MAX_ACTIVE_CONCEPTS = 25
J2_MAX_EVENT_REFS = 64
J2_MAX_ENCODED_CHARS = 32768

_TOP_LEVEL_KEYS = frozenset(
    {
        "version",
        "trace_id",
        "board_id",
        "board_digest",
        "history_chain_id",
        "history_projection_digest",
        "continuity_report_digest",
        "event_refs",
        "route_view",
        "arena_view",
        "proposal_only",
        "patch_authority",
        "vsa_patch_authority",
    }
)
_ROUTE_VIEW_KEYS = frozenset(
    {
        "route",
        "next_state",
        "verifier_required",
        "phase_digest",
        "source_packet_digest",
        "active_concept_digests",
        "active_concept_count",
    }
)
_ARENA_VIEW_KEYS = frozenset(
    {
        "arena_id",
        "arena_version",
        "grammar_version",
        "phase",
        "substate",
        "state_code",
        "selected_transition",
        "next_state",
        "verifier_requirement",
        "focus_digest",
        "evidence_digest",
        "policy_digest",
        "lease_digest",
        "repository_commit_ref",
        "working_tree_digest",
        "phase_digest",
        "source_packet_digest",
    }
)

_NORMALIZE_KEY_RE = re.compile(r"[^a-z0-9]+")
_DIGEST_RE = re.compile(r"[0-9a-f]{32}")
_PRIVATE_KEY_TOKENS = frozenset(
    {
        "chain_of_thought",
        "chainofthought",
        "cot",
        "hidden_reasoning",
        "hiddenreasoning",
        "private_reasoning",
        "privatereasoning",
        "inner_thought",
        "innerthought",
        "scratchpad",
        "scratch_pad",
    }
)
_SECRET_KEY_TOKENS = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "accesstoken",
        "auth_token",
        "authtoken",
        "authorization",
        "password",
        "private_key",
        "privatekey",
        "refresh_token",
        "refreshtoken",
        "secret",
        "token",
    }
)


class CanonicalRecord:
    def to_dict(self) -> dict[str, Any]:
        return json.loads(canonical_json(self))


def _required(value: Any, field_name: str, *, limit: int = 256) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    if len(text) > limit:
        raise ValueError(f"{field_name} exceeds {limit} characters")
    return text


def _optional(value: Any, field_name: str, *, limit: int = 256) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    text = value.strip()
    if len(text) > limit:
        raise ValueError(f"{field_name} exceeds {limit} characters")
    return text


def _digest(value: Any, field_name: str, *, optional: bool = False) -> str:
    text = _optional(value, field_name) if optional else _required(value, field_name)
    if optional and not text:
        return ""
    if not _DIGEST_RE.fullmatch(text):
        raise ValueError(
            f"{field_name} must be a 32-character lowercase hexadecimal digest"
        )
    return text


def _legacy_field_digest(field_name: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return stable_digest({"legacy_field": field_name, "value": text})


def _strict_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _strings(
    values: Sequence[Any],
    field_name: str,
    *,
    required: bool = False,
    limit: int | None = None,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(
        values,
        Sequence,
    ):
        raise ValueError(f"{field_name} must be an ordered sequence")
    result = tuple(_required(item, field_name) for item in values)
    if required and not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    if limit is not None and len(result) > limit:
        raise ValueError(f"{field_name} exceeds {limit} entries")
    return result


def _assert_safe_payload(payload: Mapping[str, Any]) -> None:
    try:
        sanitized = sanitize_payload(payload)
    except ValueError as exc:
        raise ValueError(
            f"J2 payload contains prohibited private reasoning: {exc}"
        ) from exc
    if canonical_json(sanitized) != canonical_json(payload):
        raise ValueError("J2 payload contains secret-shaped content")


def _normalized_key(value: Any) -> tuple[str, str]:
    normalized = _NORMALIZE_KEY_RE.sub("_", str(value).strip().lower()).strip("_")
    return normalized, normalized.replace("_", "")


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        private_suffixes = tuple(
            f"_{item}" for item in _PRIVATE_KEY_TOKENS if "_" in item
        )
        secret_suffixes = tuple(
            f"_{item}" for item in _SECRET_KEY_TOKENS if "_" in item
        )
        for key, item in value.items():
            normalized, compact = _normalized_key(key)
            if (
                normalized in _PRIVATE_KEY_TOKENS
                or compact in _PRIVATE_KEY_TOKENS
                or normalized in _SECRET_KEY_TOKENS
                or compact in _SECRET_KEY_TOKENS
                or normalized.endswith(private_suffixes)
                or normalized.endswith(secret_suffixes)
            ):
                return True
            if _contains_sensitive_key(item):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    field_name: str,
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{field_name} schema mismatch; missing={missing}, extra={extra}"
        )


@dataclass(frozen=True)
class J2RouteView(CanonicalRecord):
    route: str
    next_state: str
    verifier_required: bool
    phase_digest: str
    source_packet_digest: str
    active_concept_digests: tuple[str, ...] = ()
    active_concept_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "route", _required(self.route, "route_view.route"))
        object.__setattr__(
            self,
            "next_state",
            _required(self.next_state, "route_view.next_state"),
        )
        object.__setattr__(
            self,
            "verifier_required",
            _strict_bool(
                self.verifier_required,
                "route_view.verifier_required",
            ),
        )
        object.__setattr__(
            self,
            "phase_digest",
            _digest(self.phase_digest, "route_view.phase_digest"),
        )
        object.__setattr__(
            self,
            "source_packet_digest",
            _digest(
                self.source_packet_digest,
                "route_view.source_packet_digest",
            ),
        )
        raw_digests = _strings(
            self.active_concept_digests,
            "route_view.active_concept_digests",
            limit=J2_MAX_ACTIVE_CONCEPTS,
        )
        digests = tuple(
            _digest(item, "route_view.active_concept_digests")
            for item in raw_digests
        )
        object.__setattr__(self, "active_concept_digests", digests)
        if type(self.active_concept_count) is not int or self.active_concept_count < 0:
            raise ValueError(
                "route_view.active_concept_count must be a non-negative integer"
            )
        if self.active_concept_count != len(digests):
            raise ValueError(
                "route_view.active_concept_count must equal "
                "active_concept_digests length"
            )


@dataclass(frozen=True)
class J2ArenaView(CanonicalRecord):
    arena_id: str
    arena_version: str
    grammar_version: str
    phase: str
    substate: str
    state_code: str
    selected_transition: str
    next_state: str
    verifier_requirement: str
    focus_digest: str
    evidence_digest: str
    policy_digest: str
    lease_digest: str
    repository_commit_ref: str
    working_tree_digest: str
    phase_digest: str
    source_packet_digest: str

    def __post_init__(self) -> None:
        for field_name in (
            "arena_id",
            "grammar_version",
            "phase",
            "state_code",
            "verifier_requirement",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(
                    getattr(self, field_name),
                    f"arena_view.{field_name}",
                ),
            )
        for field_name in (
            "arena_version",
            "substate",
            "selected_transition",
            "next_state",
            "repository_commit_ref",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional(
                    getattr(self, field_name),
                    f"arena_view.{field_name}",
                ),
            )
        for field_name in (
            "focus_digest",
            "evidence_digest",
            "policy_digest",
            "lease_digest",
            "working_tree_digest",
        ):
            object.__setattr__(
                self,
                field_name,
                _digest(
                    getattr(self, field_name),
                    f"arena_view.{field_name}",
                    optional=True,
                ),
            )
        for field_name in ("phase_digest", "source_packet_digest"):
            object.__setattr__(
                self,
                field_name,
                _digest(
                    getattr(self, field_name),
                    f"arena_view.{field_name}",
                ),
            )


@dataclass(frozen=True)
class J2ContinuityPacket(CanonicalRecord):
    trace_id: str
    board_id: str
    board_digest: str
    history_chain_id: str
    history_projection_digest: str
    continuity_report_digest: str
    event_refs: tuple[str, ...]
    route_view: J2RouteView
    arena_view: J2ArenaView
    version: str = J2_CONTINUITY_VERSION
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        for field_name in ("trace_id", "board_id", "history_chain_id"):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), f"j2.{field_name}"),
            )
        for field_name in (
            "board_digest",
            "history_projection_digest",
            "continuity_report_digest",
        ):
            object.__setattr__(
                self,
                field_name,
                _digest(getattr(self, field_name), f"j2.{field_name}"),
            )
        object.__setattr__(
            self,
            "event_refs",
            _strings(
                self.event_refs,
                "j2.event_refs",
                required=True,
                limit=J2_MAX_EVENT_REFS,
            ),
        )
        if not isinstance(self.route_view, J2RouteView):
            raise ValueError("j2.route_view must be a J2RouteView")
        if not isinstance(self.arena_view, J2ArenaView):
            raise ValueError("j2.arena_view must be a J2ArenaView")
        if self.version != J2_CONTINUITY_VERSION:
            raise ValueError(f"unsupported J2 continuity version: {self.version}")
        if _strict_bool(self.proposal_only, "j2.proposal_only") is not True:
            raise ValueError("J2 continuity packets must remain proposal_only")
        if self.patch_authority != PATCH_AUTHORITY:
            raise ValueError("J2 patch_authority must remain exact-source-only")
        if (
            _strict_bool(
                self.vsa_patch_authority,
                "j2.vsa_patch_authority",
            )
            is not False
        ):
            raise ValueError("J2 VSA/JSpace state cannot be patch authority")
        _assert_safe_payload(self.to_dict())

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def canonical_identity(self) -> tuple[str, ...]:
        return (
            self.version,
            self.trace_id,
            self.board_id,
            self.board_digest,
            self.history_chain_id,
            self.history_projection_digest,
            self.continuity_report_digest,
            self.route_view.source_packet_digest,
            self.arena_view.source_packet_digest,
        )


def route_view_from_j0(
    packet: Any,
    *,
    active_limit: int = J2_MAX_ACTIVE_CONCEPTS,
) -> J2RouteView:
    """Project a legacy J0 packet into a digest-only route view."""

    if (
        type(active_limit) is not int
        or not 1 <= active_limit <= J2_MAX_ACTIVE_CONCEPTS
    ):
        raise ValueError(
            f"active_limit must be between 1 and {J2_MAX_ACTIVE_CONCEPTS}"
        )
    from aura_jspace_codec import AuraJPacket, active_concepts_from_packet

    raw_packet = (
        packet.packet
        if isinstance(packet, AuraJPacket)
        else str(packet or "").strip()
    )
    state = active_concepts_from_packet(
        raw_packet,
        active_limit=active_limit,
    )
    concept_digests = tuple(
        stable_digest({"concept": concept}) for concept in state.active_concepts
    )
    return J2RouteView(
        route=state.route or "UNRESOLVED",
        next_state=state.next_state or "HUMAN_GATE",
        verifier_required=state.verifier_required,
        phase_digest=stable_digest(
            {"legacy_version": "J0", "phase_packet": raw_packet}
        ),
        source_packet_digest=stable_digest({"legacy_packet": raw_packet}),
        active_concept_digests=concept_digests,
        active_concept_count=len(concept_digests),
    )


def arena_view_from_j1(raw_packet: str) -> J2ArenaView:
    """Project a valid legacy J1 packet into a digest/reference-only arena view."""

    from aura_arena_state_packet import (
        ARENA_STATE_PACKET_VERSION,
        parse_arena_state_packet,
    )

    raw = str(raw_packet or "").strip()
    parsed = parse_arena_state_packet(raw)
    if not parsed.get("ok") or parsed.get("legacy"):
        raise ValueError("arena_view_from_j1 requires a valid J1 packet")
    state = parsed.get("state")
    if not isinstance(state, Mapping):
        raise ValueError("J1 state must be a mapping")
    if state.get("packet_version") != ARENA_STATE_PACKET_VERSION:
        raise ValueError("J1 packet_version must remain canonical")
    if state.get("patch_authority") != PATCH_AUTHORITY:
        raise ValueError("J1 patch_authority must remain exact-source-only")
    if type(state.get("vsa_patch_authority")) is not bool:
        raise ValueError("J1 vsa_patch_authority must be a boolean")
    if state.get("vsa_patch_authority") is not False:
        raise ValueError("J1 VSA/JSpace state cannot be patch authority")
    state_code = state.get("state_code") or state.get("phase")
    return J2ArenaView(
        arena_id=state.get("arena_id"),
        arena_version=state.get("arena_version"),
        grammar_version=state.get("grammar_version"),
        phase=state.get("phase"),
        substate=state.get("substate", ""),
        state_code=state_code,
        selected_transition=state.get("selected_transition", ""),
        next_state=state.get("next_state", ""),
        verifier_requirement=state.get("verifier_requirement") or "none",
        focus_digest=_legacy_field_digest(
            "focus_digest",
            state.get("focus_digest"),
        ),
        evidence_digest=_legacy_field_digest(
            "evidence_digest",
            state.get("evidence_digest"),
        ),
        policy_digest=_legacy_field_digest(
            "policy_digest",
            state.get("policy_digest"),
        ),
        lease_digest=_legacy_field_digest(
            "lease_digest",
            state.get("lease_digest"),
        ),
        repository_commit_ref=state.get("repository_commit", ""),
        working_tree_digest=_legacy_field_digest(
            "working_tree_digest",
            state.get("working_tree_digest"),
        ),
        phase_digest=stable_digest(
            {
                "legacy_version": "J1",
                "phase_hash": str(state.get("phase_hash") or ""),
                "state_code": str(state_code or ""),
            }
        ),
        source_packet_digest=stable_digest({"legacy_packet": raw}),
    )


def build_j2_continuity_packet(
    *,
    trace_id: str,
    board_id: str,
    board_digest: str,
    history_chain_id: str,
    history_projection_digest: str,
    continuity_report_digest: str,
    event_refs: Sequence[str],
    route_view: J2RouteView,
    arena_view: J2ArenaView,
) -> tuple[J2ContinuityPacket, str]:
    """Build the canonical deterministic J2 packet."""

    packet = J2ContinuityPacket(
        trace_id=trace_id,
        board_id=board_id,
        board_digest=board_digest,
        history_chain_id=history_chain_id,
        history_projection_digest=history_projection_digest,
        continuity_report_digest=continuity_report_digest,
        event_refs=event_refs,
        route_view=route_view,
        arena_view=arena_view,
    )
    payload = packet.to_dict()
    encoded = base64.urlsafe_b64encode(
        canonical_json(payload).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return packet, f"{J2_PACKET_PREFIX}{encoded}#{packet.digest}"


def parse_continuity_packet(raw_packet: str) -> dict[str, Any]:
    """Parse J2 canonically or delegate unchanged J0/J1 compatibility parsing."""

    if isinstance(raw_packet, str) and raw_packet.strip().startswith(J2_PACKET_PREFIX):
        return parse_j2_continuity_packet(raw_packet)
    raw = str(raw_packet or "").strip()
    if raw.startswith(("J0/", "J1/")):
        from aura_arena_state_packet import parse_arena_state_packet

        return parse_arena_state_packet(raw)
    return {"ok": False, "error": "unsupported_continuity_packet_prefix"}


def parse_j2_continuity_packet(raw_packet: str) -> dict[str, Any]:
    if not isinstance(raw_packet, str):
        return {"ok": False, "error": "j2_packet_not_string"}
    if raw_packet != raw_packet.strip():
        return {"ok": False, "error": "j2_noncanonical_outer_whitespace"}
    raw = raw_packet
    if not raw.startswith(J2_PACKET_PREFIX):
        return {"ok": False, "error": "unsupported_j2_packet_prefix"}

    body = raw[len(J2_PACKET_PREFIX) :]
    encoded, separator, supplied_digest = body.rpartition("#")
    if separator != "#" or not encoded or not supplied_digest:
        return {"ok": False, "error": "malformed_j2_packet"}
    if len(encoded) > J2_MAX_ENCODED_CHARS:
        return {"ok": False, "error": "j2_packet_too_large"}
    if not re.fullmatch(r"[A-Za-z0-9_-]+", encoded):
        return {"ok": False, "error": "invalid_j2_base64"}
    if not _DIGEST_RE.fullmatch(supplied_digest):
        return {"ok": False, "error": "invalid_j2_digest"}

    padding = "=" * ((4 - len(encoded) % 4) % 4)
    try:
        raw_bytes = base64.b64decode(
            (encoded + padding).encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError):
        return {"ok": False, "error": "invalid_j2_base64"}
    canonical_encoded = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")
    if encoded != canonical_encoded:
        return {"ok": False, "error": "j2_noncanonical_base64"}
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return {"ok": False, "error": "invalid_j2_utf8"}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid_j2_json"}
    if not isinstance(payload, Mapping):
        return {"ok": False, "error": "j2_payload_not_object"}
    if _contains_sensitive_key(payload):
        return {"ok": False, "error": "j2_sensitive_field_forbidden"}

    try:
        canonical = canonical_json(payload)
    except (TypeError, ValueError):
        return {"ok": False, "error": "j2_payload_not_canonicalizable"}
    if text != canonical:
        return {"ok": False, "error": "j2_noncanonical_payload"}
    if stable_digest(payload) != supplied_digest:
        return {"ok": False, "error": "j2_digest_suffix_mismatch"}

    try:
        _exact_keys(payload, _TOP_LEVEL_KEYS, "j2")
        route_payload = payload.get("route_view")
        arena_payload = payload.get("arena_view")
        if not isinstance(route_payload, Mapping):
            raise ValueError("j2.route_view must be an object")
        if not isinstance(arena_payload, Mapping):
            raise ValueError("j2.arena_view must be an object")
        _exact_keys(route_payload, _ROUTE_VIEW_KEYS, "j2.route_view")
        _exact_keys(arena_payload, _ARENA_VIEW_KEYS, "j2.arena_view")
        if not isinstance(payload.get("event_refs"), list):
            raise ValueError("j2.event_refs must be an array")
        if not isinstance(route_payload.get("active_concept_digests"), list):
            raise ValueError(
                "j2.route_view.active_concept_digests must be an array"
            )
    except ValueError:
        return {"ok": False, "error": "j2_schema_invalid"}

    try:
        route_view = J2RouteView(
            route=route_payload["route"],
            next_state=route_payload["next_state"],
            verifier_required=route_payload["verifier_required"],
            phase_digest=route_payload["phase_digest"],
            source_packet_digest=route_payload["source_packet_digest"],
            active_concept_digests=tuple(
                route_payload["active_concept_digests"]
            ),
            active_concept_count=route_payload["active_concept_count"],
        )
        arena_view = J2ArenaView(
            arena_id=arena_payload["arena_id"],
            arena_version=arena_payload["arena_version"],
            grammar_version=arena_payload["grammar_version"],
            phase=arena_payload["phase"],
            substate=arena_payload["substate"],
            state_code=arena_payload["state_code"],
            selected_transition=arena_payload["selected_transition"],
            next_state=arena_payload["next_state"],
            verifier_requirement=arena_payload["verifier_requirement"],
            focus_digest=arena_payload["focus_digest"],
            evidence_digest=arena_payload["evidence_digest"],
            policy_digest=arena_payload["policy_digest"],
            lease_digest=arena_payload["lease_digest"],
            repository_commit_ref=arena_payload["repository_commit_ref"],
            working_tree_digest=arena_payload["working_tree_digest"],
            phase_digest=arena_payload["phase_digest"],
            source_packet_digest=arena_payload["source_packet_digest"],
        )
        packet = J2ContinuityPacket(
            trace_id=payload["trace_id"],
            board_id=payload["board_id"],
            board_digest=payload["board_digest"],
            history_chain_id=payload["history_chain_id"],
            history_projection_digest=payload["history_projection_digest"],
            continuity_report_digest=payload["continuity_report_digest"],
            event_refs=tuple(payload["event_refs"]),
            route_view=route_view,
            arena_view=arena_view,
            version=payload["version"],
            proposal_only=payload["proposal_only"],
            patch_authority=payload["patch_authority"],
            vsa_patch_authority=payload["vsa_patch_authority"],
        )
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "error": "j2_contract_invalid"}

    if canonical_json(packet.to_dict()) != canonical:
        return {"ok": False, "error": "j2_contract_normalization_mismatch"}
    if packet.digest != supplied_digest:
        return {"ok": False, "error": "j2_contract_digest_mismatch"}

    return {
        "ok": True,
        "legacy": False,
        "packet_version": J2_CONTINUITY_VERSION,
        "state": packet.to_dict(),
        "packet_digest": packet.digest,
        "canonical_identity": list(packet.canonical_identity()),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
