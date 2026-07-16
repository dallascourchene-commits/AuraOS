"""Shared human-governed controls for Aura Architect and Surgeon sessions.

The same contract is used by native Aura, Coding Arena, Human Agent Arena,
MCP/third-party agents, and the HTTP/container connector. External surfaces may
request bounded behavior but never gain production mutation or promotion
authority. Native Aura can explicitly choose Council and Surgeon budgets while
human review remains mandatory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

ARCHITECT_CONTROL_VERSION = "AURA_ARCHITECT_CONTROL_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
DEFAULT_OUTPUT_ROOT = "Aura_Staging/refactor_output_vault"

SURFACES = {
    "native",
    "coding_arena",
    "human_agent_arena",
    "mcp_external",
    "http_external",
    "container_external",
}
COUNCIL_MODES = {"OFF", "AUTO", "SELECTIVE_V3", "FULL_V2"}
SURGEON_MODES = {"PLAN_ONLY", "PROPOSE", "STAGE_AND_VERIFY"}
CRITIC_LANES = {"scope", "tests", "sequence", "continuity", "rollback", "cost"}
_EXTERNAL_SURFACES = {"mcp_external", "http_external", "container_external"}


def _digest(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def _bounded_int(value: Any, *, minimum: int, maximum: int, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return parsed


def _strict_bool(value: Any, *, default: bool, field: str) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _clean_lanes(values: Sequence[Any] | None) -> tuple[str, ...]:
    if values is not None and isinstance(values, (str, bytes)):
        raise ValueError("critic_lanes must be an array")
    lanes: list[str] = []
    for value in values or ():
        lane = str(value or "").strip().lower()
        if not lane:
            continue
        if lane not in CRITIC_LANES:
            raise ValueError(f"unknown critic lane: {lane}")
        if lane not in lanes:
            lanes.append(lane)
    return tuple(lanes)


def _safe_output_root(value: Any) -> str:
    raw = str(value or DEFAULT_OUTPUT_ROOT).replace("\\", "/").strip().strip("/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts:
        raise ValueError("output_root must be a repository-relative Aura_Staging path")
    if not path.parts or path.parts[0] != "Aura_Staging":
        raise ValueError("output_root must be beneath Aura_Staging")
    return path.as_posix()


@dataclass(frozen=True)
class ArchitectControlProfile:
    """Bounded controls selected by the human or the invoking Arena surface."""

    surface: str = "native"
    council_mode: str = "AUTO"
    council_call_budget: int = 12
    critic_lanes: tuple[str, ...] = ()
    surgeon_mode: str = "STAGE_AND_VERIFY"
    surgeon_max_turns: int = 12
    surgeon_max_local_repairs: int = 2
    surgeon_context_tokens: int = 2200
    surgeon_output_tokens: int = 2400
    council_replan_allowed: bool = True
    record_outputs: bool = True
    output_root: str = DEFAULT_OUTPUT_ROOT
    human_review_required: bool = True
    production_mutation: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["critic_lanes"] = list(self.critic_lanes)
        payload["version"] = ARCHITECT_CONTROL_VERSION
        payload["control_digest"] = _digest(payload)
        return payload

    @property
    def is_external(self) -> bool:
        return self.surface in _EXTERNAL_SURFACES

    @property
    def output_path(self) -> Path:
        return Path(self.output_root)


def normalize_control_profile(
    value: Mapping[str, Any] | ArchitectControlProfile | None = None,
    *,
    surface: str | None = None,
    benchmark: bool = False,
) -> ArchitectControlProfile:
    """Validate and normalize one immutable control profile.

    Benchmark runs are always recorded. External callers can reduce deliberation,
    but cannot bypass human review, request production mutation, or write evidence
    outside Aura's local staging workspace.
    """

    if isinstance(value, ArchitectControlProfile):
        raw = value.to_dict()
    elif value is None:
        raw = {}
    elif isinstance(value, Mapping):
        raw = dict(value)
    else:
        raise ValueError("control profile must be an object")

    selected_surface = str(surface or raw.get("surface") or "native").strip().lower()
    if selected_surface not in SURFACES:
        raise ValueError(f"unknown architect surface: {selected_surface}")

    council_mode = str(raw.get("council_mode") or "AUTO").strip().upper()
    if council_mode not in COUNCIL_MODES:
        raise ValueError(f"unknown council_mode: {council_mode}")
    council_budget = _bounded_int(
        raw.get("council_call_budget", 12),
        minimum=0,
        maximum=32,
        field="council_call_budget",
    )
    if council_mode == "OFF":
        council_budget = 0
    elif council_budget == 0:
        raise ValueError("enabled Council mode requires a positive call budget")

    surgeon_mode = str(raw.get("surgeon_mode") or "STAGE_AND_VERIFY").strip().upper()
    if surgeon_mode not in SURGEON_MODES:
        raise ValueError(f"unknown surgeon_mode: {surgeon_mode}")

    requested_human_review = raw.get("human_review_required", True)
    requested_mutation = raw.get("production_mutation", False)
    requested_vsa_authority = raw.get("vsa_patch_authority", False)
    if _strict_bool(requested_human_review, default=True, field="human_review_required") is not True:
        raise ValueError("human review cannot be disabled")
    if _strict_bool(requested_mutation, default=False, field="production_mutation") is not False:
        raise ValueError("production mutation cannot be enabled by a control profile")
    if _strict_bool(requested_vsa_authority, default=False, field="vsa_patch_authority") is not False:
        raise ValueError("VSA patch authority cannot be enabled")

    profile = ArchitectControlProfile(
        surface=selected_surface,
        council_mode=council_mode,
        council_call_budget=council_budget,
        critic_lanes=_clean_lanes(raw.get("critic_lanes")),
        surgeon_mode=surgeon_mode,
        surgeon_max_turns=_bounded_int(
            raw.get("surgeon_max_turns", 12),
            minimum=1,
            maximum=40,
            field="surgeon_max_turns",
        ),
        surgeon_max_local_repairs=_bounded_int(
            raw.get("surgeon_max_local_repairs", 2),
            minimum=0,
            maximum=8,
            field="surgeon_max_local_repairs",
        ),
        surgeon_context_tokens=_bounded_int(
            raw.get("surgeon_context_tokens", 2200),
            minimum=256,
            maximum=16000,
            field="surgeon_context_tokens",
        ),
        surgeon_output_tokens=_bounded_int(
            raw.get("surgeon_output_tokens", 2400),
            minimum=128,
            maximum=16000,
            field="surgeon_output_tokens",
        ),
        council_replan_allowed=_strict_bool(
            raw.get("council_replan_allowed"),
            default=True,
            field="council_replan_allowed",
        ),
        record_outputs=True
        if benchmark
        else _strict_bool(raw.get("record_outputs"), default=True, field="record_outputs"),
        output_root=_safe_output_root(raw.get("output_root")),
    )
    return profile


def control_capabilities(surface: str = "native") -> dict[str, Any]:
    profile = normalize_control_profile(surface=surface)
    return {
        "version": ARCHITECT_CONTROL_VERSION,
        "surface": profile.surface,
        "council_modes": sorted(COUNCIL_MODES),
        "surgeon_modes": sorted(SURGEON_MODES),
        "critic_lanes": sorted(CRITIC_LANES),
        "native_explicit_controls": profile.surface in {
            "native",
            "coding_arena",
            "human_agent_arena",
        },
        "external_controls_are_bounded": profile.is_external,
        "output_root_prefix": "Aura_Staging/",
        "human_review_required": True,
        "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "ARCHITECT_CONTROL_VERSION",
    "ArchitectControlProfile",
    "DEFAULT_OUTPUT_ROOT",
    "control_capabilities",
    "normalize_control_profile",
]
