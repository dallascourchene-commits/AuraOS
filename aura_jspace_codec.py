"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f0-[Q-SYS:JSPACE_CODEC]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Compact Advisory Routing State)
DEPENDENCIES: __future__, collections.abc, dataclasses, hashlib, json, re, typing
FUNCTIONS: compact_frame_input, compact_route_output, next_state_for_decision, build_jspace_packet, parse_jspace_packet, active_concepts_from_packet, attach_jspace_to_capsule
SYNOPSIS: Stdlib-only AuraJSpace codec for compact Coding Arena route/capsule state. JSpace packets are advisory only; exact source spans, hashes, tests, and verifier gates remain patch authority.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


JSPACE_CODEC_VERSION = "AURA_JSPACE_CODEC_V0"
DEFAULT_ACTIVE_LIMIT = 25
PATCH_AUTHORITY_DEFAULT = "exact_source_spans_and_hashes_only"

_PACKET_PREFIX = "J0"
_INPUT_SLOT_NAMES = ("intent", "artifact", "action", "scope", "risk", "grounding", "tests", "quality", "cost")
_OUTPUT_SLOT_NAMES = ("route", "model", "context", "reason", "verifier")

_INTENT_COMPACT = {
    "code_refactor": "REF",
    "localize": "LOC",
    "test_generate": "TST",
    "verify": "VER",
    "repair": "REP",
    "benchmark": "BEN",
    "research_rank": "RSR",
    "explain": "EXP",
    "hotswap": "HOT",
}
_ARTIFACT_COMPACT = {
    "python_module": "PY",
    "test_file": "TF",
    "codemap": "CM",
    "manifest": "MF",
    "patch": "PT",
    "transaction_log": "TX",
    "research_item": "RI",
    "documentation": "DC",
}
_ACTION_COMPACT = {
    "inspect": "IN",
    "create": "CR",
    "modify": "MO",
    "rank": "RK",
    "verify": "VR",
    "repair": "RP",
    "rollback": "RB",
    "promote": "PR",
}
_SCOPE_COMPACT = {
    "symbol": "SYM",
    "file": "FIL",
    "capsule": "CAP",
    "subsystem": "SUB",
    "repo": "REP",
}
_RISK_COMPACT = {
    "low": "L",
    "medium": "M",
    "high": "H",
    "live": "V",
}
_GROUNDING_COMPACT = {
    "file_exists": "F",
    "symbol_exists": "S",
    "tests_exist": "T",
    "manifest_owner": "M",
    "codemap_grounded": "C",
}
_GROUNDING_ORDER = ("file_exists", "symbol_exists", "tests_exist", "manifest_owner", "codemap_grounded")
_TEST_COMPACT = {
    "none": "0",
    "existing": "1",
    "generated": "G",
    "required": "R",
}
_QUALITY_COMPACT = {
    "fast": "F",
    "balanced": "B",
    "accuracy_first": "A",
    "verifier_required": "V",
}
_COST_COMPACT = {
    "no_model": "0",
    "local_first": "L",
    "cheap_first": "C",
    "premium_allowed": "P",
    "premium_required": "PR",
}
_ROUTE_COMPACT = {
    "LOCALIZE_FIRST": "LOC",
    "PLAN_ONLY": "PLAN",
    "MUSIC_RANK_ONLY": "MUSIC",
    "BUILDER_PATCH": "BUILD",
    "TEST_GAP_FILL": "TEST",
    "VERIFY_ONLY": "VERIFY",
    "REPAIR_PATCH": "REPAIR",
    "BLOCKED_WITH_REASON": "BLOCK",
    "EXTERNAL_CALL_CONTEXT": "EXT",
    "EMERGENT_CAPABILITY_AUDIT": "AUDIT",
}
_MODEL_COMPACT = {
    "no_model": "0",
    "local_first": "L",
    "local_model": "L",
    "cheap_first": "C",
    "cheap_model": "C",
    "premium_allowed": "P",
    "premium_required": "P",
    "premium_model": "P",
}
_CONTEXT_COMPACT = {
    "SUMMARY": "SUM",
    "SYMBOLIC": "SYM",
    "PATCH": "PAT",
    "TEST": "TST",
    "VERIFIER": "VER",
    "EXTERNAL": "EXT",
    "AUDIT": "AUD",
}
_REASON_COMPACT = {
    "target_symbol_unresolved": "SYM0",
    "missing_tests": "TEST0",
    "missing_tests_or_verifier_evidence": "TEST0",
    "research_not_patch_evidence": "RG0",
    "scope_too_broad_for_act_capsule": "SCOPE",
    "live_risk_requires_verification": "LIVE",
    "hotswap_requires_full_grounding": "HOT0",
    "missing_grounding": "GROUND0",
    "route_valid": "OK",
    "benchmark_before_optimization": "BENCH",
    "repair_after_failed_patch": "REPAIR",
    "external_call_context": "EXT",
    "emergent_capability_audit": "AUDIT",
    "unsafe_parse_diagnostics": "UNSAFE",
    "target_symbol_unresolved": "SYM0",
    "external_call_unresolved": "EXT0",
    "no_exact_target_provided": "TARGET0",
}

_LEGACY_INPUT_SLOT_TABLES = (
    {"I:REF": "REF", "I:LOC": "LOC", "I:TST": "TST", "I:VER": "VER", "I:REP": "REP", "I:BEN": "BEN", "I:RSR": "RSR", "I:EXP": "EXP", "I:HOT": "HOT"},
    {"A:PY": "PY", "A:TF": "TF", "A:CM": "CM", "A:MF": "MF", "A:PT": "PT", "A:TX": "TX", "A:RI": "RI", "A:DC": "DC"},
    {"X:IN": "IN", "X:CR": "CR", "X:MO": "MO", "X:RK": "RK", "X:VR": "VR", "X:RP": "RP", "X:RB": "RB", "X:PR": "PR"},
    {"S:SYM": "SYM", "S:FIL": "FIL", "S:CAP": "CAP", "S:SUB": "SUB", "S:REP": "REP"},
    {"R:L": "L", "R:M": "M", "R:H": "H", "R:V": "V"},
    {},
    {"T:0": "0", "T:1": "1", "T:G": "G", "T:R": "R"},
    {"Q:F": "F", "Q:B": "B", "Q:A": "A", "Q:V": "V"},
    {"C:0": "0", "C:L": "L", "C:C": "C", "C:P": "P", "C:PR": "PR"},
)


@dataclass(frozen=True)
class AuraJPacket:
    version: str
    input_compact: str
    output_compact: str
    next_state: str
    packet: str
    phase_hash: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "input_compact": self.input_compact,
            "output_compact": self.output_compact,
            "next_state": self.next_state,
            "packet": self.packet,
            "phase_hash": self.phase_hash,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class AuraJState:
    version: str
    packet: str
    active_concepts: tuple[dict[str, object], ...]
    next_state: str
    route: str
    verifier_required: bool
    patch_authority: str
    vsa_patch_authority: bool
    phase_hash: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "packet": self.packet,
            "active_concepts": list(self.active_concepts),
            "next_state": self.next_state,
            "route": self.route,
            "verifier_required": self.verifier_required,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "phase_hash": self.phase_hash,
            "warnings": list(self.warnings),
        }


def compact_frame_input(frame: RoutingFrame | Mapping[str, Any]) -> str:
    """Return the fixed-order compact input string for a RoutingFrame-like value."""
    return ".".join(
        [
            _compact_lookup(_INTENT_COMPACT, _field(frame, "intent", "code_refactor")),
            _compact_lookup(_ARTIFACT_COMPACT, _field(frame, "artifact", "python_module")),
            _compact_lookup(_ACTION_COMPACT, _field(frame, "action", "modify")),
            _compact_lookup(_SCOPE_COMPACT, _field(frame, "scope", "symbol")),
            _compact_lookup(_RISK_COMPACT, _field(frame, "risk", "medium")),
            _compact_grounding(_field(frame, "grounding", ())),
            _compact_lookup(_TEST_COMPACT, _field(frame, "tests", "none")),
            _compact_lookup(_QUALITY_COMPACT, _field(frame, "quality", "balanced")),
            _compact_lookup(_COST_COMPACT, _field(frame, "cost", "local_first")),
        ]
    )


def compact_route_output(decision: RouteDecision | Mapping[str, Any]) -> str:
    """Return the fixed-order compact output string for a RouteDecision-like value."""
    route = _decision_route(decision)
    model = _field(decision, "model", "") or _model_for_route(route)
    context = _field(decision, "context", "") or _context_for_route(route)
    reason = _field(decision, "reason", "") or _reason_for_route(route)
    verifier = _decision_verifier_required(decision, route)
    return ".".join(
        [
            _compact_lookup(_ROUTE_COMPACT, route),
            _compact_lookup(_MODEL_COMPACT, model),
            _compact_lookup(_CONTEXT_COMPACT, str(context).upper()),
            _compact_lookup(_REASON_COMPACT, reason),
            "1" if verifier else "0",
        ]
    )


def next_state_for_decision(
    decision: RouteDecision | Mapping[str, Any],
    *,
    grounding: dict[str, Any] | None = None,
) -> str:
    """Map a route decision and optional grounding packet to the next advisory state."""
    route = _decision_route(decision)
    verifier_required = _decision_verifier_required(decision, route)
    if route == "BUILDER_PATCH":
        if not verifier_required:
            return "HUMAN_GATE"
        if not _has_exact_spans_and_hashes(grounding):
            return "NEED_GROUND"
        if not _has_tests(grounding):
            return "NEED_TEST"
        return "READY_PATCH"
    if route == "TEST_GAP_FILL":
        return "NEED_TEST"
    if route == "LOCALIZE_FIRST":
        return "LOCALIZE_FIRST"
    if route == "VERIFY_ONLY":
        return "VERIFY_ONLY"
    if route == "PLAN_ONLY":
        return "PLAN_ONLY"
    if route == "BLOCKED_WITH_REASON":
        return "BLOCKED"
    if route == "EXTERNAL_CALL_CONTEXT":
        return "READ_ONLY_CONTEXT"
    if route == "EMERGENT_CAPABILITY_AUDIT":
        return "READ_ONLY_AUDIT"
    return "HUMAN_GATE"


def build_jspace_packet(
    frame: RoutingFrame | Mapping[str, Any],
    decision: RouteDecision | Mapping[str, Any],
    *,
    grounding: dict[str, Any] | None = None,
    active_limit: int = DEFAULT_ACTIVE_LIMIT,
) -> AuraJPacket:
    """Build a compact AuraJ packet from an existing routing frame and decision."""
    warnings: list[str] = []
    if active_limit < 1:
        warnings.append("active_limit_below_one")
    input_compact = compact_frame_input(frame)
    output_compact = compact_route_output(decision)
    next_state = next_state_for_decision(decision, grounding=grounding)
    packet = f"{_PACKET_PREFIX}/{input_compact}>{output_compact}#{next_state}"
    phase_hash = _hash_payload(
        {
            "version": JSPACE_CODEC_VERSION,
            "packet": packet,
            "grounding_route": grounding.get("route") if isinstance(grounding, dict) else "",
        }
    )
    return AuraJPacket(
        version=JSPACE_CODEC_VERSION,
        input_compact=input_compact,
        output_compact=output_compact,
        next_state=next_state,
        packet=packet,
        phase_hash=phase_hash,
        warnings=tuple(warnings),
    )


def parse_jspace_packet(packet: str) -> dict[str, object]:
    """Parse a J0 packet into compact and decoded slot dictionaries."""
    raw = str(packet or "").strip()
    if not raw.startswith(f"{_PACKET_PREFIX}/"):
        raise ValueError("AuraJ packet must start with J0/")
    body = raw[len(_PACKET_PREFIX) + 1 :]
    input_compact, sep, after_input = body.partition(">")
    if sep != ">":
        raise ValueError("AuraJ packet is missing route output separator")
    output_compact, hash_sep, next_state = after_input.partition("#")
    if hash_sep != "#":
        raise ValueError("AuraJ packet is missing next-state separator")

    warnings: list[str] = []
    input_slots = _decode_input_slots(input_compact, warnings)
    output_slots = _decode_output_slots(output_compact, warnings)
    return {
        "version": JSPACE_CODEC_VERSION,
        "packet_version": _PACKET_PREFIX,
        "input_compact": input_compact,
        "output_compact": output_compact,
        "next_state": next_state,
        "input_slots": input_slots,
        "output_slots": output_slots,
        "warnings": warnings,
    }


def active_concepts_from_packet(
    packet: str | AuraJPacket,
    *,
    grounding: dict[str, Any] | None = None,
    active_limit: int = DEFAULT_ACTIVE_LIMIT,
) -> AuraJState:
    """Expose a deterministic sparse active concept state for a JSpace packet."""
    raw_packet = packet.packet if isinstance(packet, AuraJPacket) else str(packet or "")
    parsed = parse_jspace_packet(raw_packet)
    input_slots = dict(parsed.get("input_slots", {}) or {})
    output_slots = dict(parsed.get("output_slots", {}) or {})
    next_state = str(parsed.get("next_state") or "")
    patch_authority = _patch_authority(grounding)
    vsa_patch_authority = False
    phase_hash = packet.phase_hash if isinstance(packet, AuraJPacket) else _hash_payload({"packet": raw_packet})

    concepts: list[dict[str, object]] = []
    for slot, weight in (
        ("intent", 0.82),
        ("artifact", 0.80),
        ("action", 0.81),
        ("scope", 0.80),
        ("risk", 0.80),
        ("grounding", 0.86),
        ("tests", 0.86),
        ("quality", 0.78),
        ("cost", 0.74),
    ):
        _add_concept(concepts, slot, input_slots.get(slot), weight, "jspace_packet")
    for slot, weight in (
        ("route", 0.95),
        ("model", 0.82),
        ("context", 0.84),
        ("reason", 0.88),
        ("verifier", 0.90),
    ):
        _add_concept(concepts, slot, output_slots.get(slot), weight, "jspace_packet")
    _add_concept(concepts, "next_state", next_state, 0.94, "jspace_packet")
    _add_concept(concepts, "patch_authority", patch_authority, 0.93, "grounding")
    _add_concept(concepts, "vsa_patch_authority", vsa_patch_authority, 0.93, "grounding")

    limit = max(0, int(active_limit))
    selected = tuple(concepts[:limit])
    route = str(output_slots.get("route") or "")
    verifier_required = bool(output_slots.get("verifier"))
    warnings = tuple(str(item) for item in parsed.get("warnings", []) or [])
    if isinstance(packet, AuraJPacket):
        warnings = (*packet.warnings, *warnings)
    return AuraJState(
        version=JSPACE_CODEC_VERSION,
        packet=raw_packet,
        active_concepts=selected,
        next_state=next_state,
        route=route,
        verifier_required=verifier_required,
        patch_authority=patch_authority,
        vsa_patch_authority=vsa_patch_authority,
        phase_hash=phase_hash,
        warnings=warnings,
    )


def attach_jspace_to_capsule(
    capsule: dict[str, object],
    *,
    frame: RoutingFrame | Mapping[str, Any] | None = None,
    decision: RouteDecision | Mapping[str, Any] | None = None,
    grounding: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Return a capsule copy with advisory JSpace packet and state attached."""
    output = dict(capsule or {})
    frame_payload = frame if frame is not None else _frame_from_capsule(output, grounding=grounding)
    decision_payload = decision if decision is not None else _decision_from_capsule(output, grounding=grounding)
    try:
        jpacket = build_jspace_packet(frame_payload, decision_payload, grounding=grounding)
        state = active_concepts_from_packet(jpacket, grounding=grounding)
        output["jspace_packet"] = jpacket.packet
        output["jspace_state"] = state.to_dict()
    except Exception as exc:
        output["jspace_packet"] = ""
        output["jspace_state"] = {
            "version": JSPACE_CODEC_VERSION,
            "packet": "",
            "active_concepts": [],
            "next_state": "HUMAN_GATE",
            "route": "",
            "verifier_required": False,
            "patch_authority": PATCH_AUTHORITY_DEFAULT,
            "vsa_patch_authority": False,
            "phase_hash": _hash_payload({"capsule": output}),
            "warnings": [f"jspace_attach_failed:{type(exc).__name__}"],
        }
    return output


def compact_symbol_input(symbol_input: str) -> str:
    """Convert the older pipe-delimited symbol_input string into JSpace slot order."""
    text = str(symbol_input or "").strip()
    if "." in text and "|" not in text:
        return text
    parts = text.split("|")
    output: list[str] = []
    for index, value in enumerate(parts[: len(_INPUT_SLOT_NAMES)]):
        value = value.strip()
        if index == 5:
            output.append(_compact_legacy_grounding(value))
            continue
        table = _LEGACY_INPUT_SLOT_TABLES[index] if index < len(_LEGACY_INPUT_SLOT_TABLES) else {}
        output.append(table.get(value, _compact_unknown(value.split(":", 1)[-1] if ":" in value else value)))
    while len(output) < len(_INPUT_SLOT_NAMES):
        output.append("0" if len(output) in {5, 6} else "UNK")
    return ".".join(output)


def _field(source: Any, name: str, default: Any = "") -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _compact_lookup(table: Mapping[str, str], value: Any) -> str:
    text = str(value or "").strip()
    if text in table:
        return table[text]
    lower = text.lower()
    if lower in table:
        return table[lower]
    upper = text.upper()
    if upper in table:
        return table[upper]
    return _compact_unknown(text)


def _compact_unknown(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = text.strip("_")
    return (text or "UNK")[:32]


def _as_sequence(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        if "," in value:
            return tuple(item.strip().lower() for item in value.split(",") if item.strip())
        if "+" in value:
            return tuple(item.strip().lower() for item in value.split("+") if item.strip())
        return (value.strip().lower(),) if value.strip() else ()
    try:
        return tuple(str(item).strip().lower() for item in value if str(item).strip())
    except TypeError:
        return (str(value).strip().lower(),) if str(value).strip() else ()


def _compact_grounding(value: Any) -> str:
    items = set(_as_sequence(value))
    if not items or items == {"none"}:
        return "0"
    if "full" in items:
        return "FULL"
    compact = "".join(_GROUNDING_COMPACT[item] for item in _GROUNDING_ORDER if item in items)
    return compact or "0"


def _compact_legacy_grounding(value: str) -> str:
    text = str(value or "").strip()
    if text in {"G:0", "0"}:
        return "0"
    if text in {"G:FULL", "FULL"}:
        return "FULL"
    if text.startswith("G:"):
        text = text[2:]
    parts = [part for part in text.replace("+", "").upper() if part in {"F", "S", "T", "M", "C"}]
    ordered = [letter for letter in ("F", "S", "T", "M", "C") if letter in parts]
    return "".join(ordered) or _compact_unknown(text)


def _decision_route(decision: Any) -> str:
    route = _field(decision, "route", "") or _field(decision, "selected_route", "")
    return str(route or "").strip().upper()


def _decision_verifier_required(decision: Any, route: str) -> bool:
    value = _field(decision, "verifier_required", None)
    if value is None:
        return route in {"BUILDER_PATCH", "TEST_GAP_FILL", "VERIFY_ONLY", "BLOCKED_WITH_REASON"}
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "required"}
    return bool(value)


def _model_for_route(route: str) -> str:
    if route in {"LOCALIZE_FIRST", "BLOCKED_WITH_REASON", "VERIFY_ONLY", "EXTERNAL_CALL_CONTEXT", "EMERGENT_CAPABILITY_AUDIT"}:
        return "no_model"
    if route in {"PLAN_ONLY", "MUSIC_RANK_ONLY", "REPAIR_PATCH"}:
        return "cheap_first"
    return "local_first"


def _context_for_route(route: str) -> str:
    return {
        "BUILDER_PATCH": "PATCH",
        "TEST_GAP_FILL": "TEST",
        "VERIFY_ONLY": "VERIFIER",
        "BLOCKED_WITH_REASON": "VERIFIER",
        "EXTERNAL_CALL_CONTEXT": "EXTERNAL",
        "EMERGENT_CAPABILITY_AUDIT": "AUDIT",
        "MUSIC_RANK_ONLY": "SYMBOLIC",
    }.get(route, "SUMMARY")


def _reason_for_route(route: str) -> str:
    return {
        "BUILDER_PATCH": "route_valid",
        "TEST_GAP_FILL": "missing_tests",
        "LOCALIZE_FIRST": "target_symbol_unresolved",
        "BLOCKED_WITH_REASON": "missing_grounding",
        "EXTERNAL_CALL_CONTEXT": "external_call_context",
        "EMERGENT_CAPABILITY_AUDIT": "emergent_capability_audit",
    }.get(route, "route_valid")


def _has_exact_spans_and_hashes(grounding: dict[str, Any] | None) -> bool:
    if not isinstance(grounding, dict):
        return False
    spans = [item for item in grounding.get("source_spans", []) or [] if isinstance(item, dict)]
    exact_span = any(
        item.get("file_path")
        and item.get("start_line")
        and item.get("end_line")
        and item.get("source_hash")
        for item in spans
    )
    hashes = grounding.get("hashes", {}) or {}
    return exact_span and isinstance(hashes, dict) and bool(hashes)


def _has_tests(grounding: dict[str, Any] | None) -> bool:
    if not isinstance(grounding, dict):
        return False
    return bool(list(grounding.get("tests", []) or grounding.get("test_files", []) or []))


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _reverse(table: Mapping[str, str]) -> dict[str, str]:
    return {value: key for key, value in table.items()}


_INTENT_EXPANDED = _reverse(_INTENT_COMPACT)
_ARTIFACT_EXPANDED = _reverse(_ARTIFACT_COMPACT)
_ACTION_EXPANDED = _reverse(_ACTION_COMPACT)
_SCOPE_EXPANDED = _reverse(_SCOPE_COMPACT)
_RISK_EXPANDED = _reverse(_RISK_COMPACT)
_TEST_EXPANDED = _reverse(_TEST_COMPACT)
_QUALITY_EXPANDED = _reverse(_QUALITY_COMPACT)
_COST_EXPANDED = _reverse(_COST_COMPACT)
_ROUTE_EXPANDED = _reverse(_ROUTE_COMPACT)
_MODEL_EXPANDED = {
    "0": "no_model",
    "L": "local_first",
    "C": "cheap_first",
    "P": "premium_allowed",
}
_CONTEXT_EXPANDED = _reverse(_CONTEXT_COMPACT)
_REASON_EXPANDED = _reverse(_REASON_COMPACT)
_GROUNDING_EXPANDED = {value: key for key, value in _GROUNDING_COMPACT.items()}


def _decode_input_slots(input_compact: str, warnings: list[str]) -> dict[str, object]:
    parts = str(input_compact or "").split(".")
    if len(parts) != len(_INPUT_SLOT_NAMES):
        warnings.append(f"input_slot_count:{len(parts)}")
    parts = [*parts[: len(_INPUT_SLOT_NAMES)], *([""] * len(_INPUT_SLOT_NAMES))][: len(_INPUT_SLOT_NAMES)]
    return {
        "intent": _INTENT_EXPANDED.get(parts[0], parts[0]),
        "artifact": _ARTIFACT_EXPANDED.get(parts[1], parts[1]),
        "action": _ACTION_EXPANDED.get(parts[2], parts[2]),
        "scope": _SCOPE_EXPANDED.get(parts[3], parts[3]),
        "risk": _RISK_EXPANDED.get(parts[4], parts[4]),
        "grounding": _decode_grounding(parts[5]),
        "tests": _TEST_EXPANDED.get(parts[6], parts[6]),
        "quality": _QUALITY_EXPANDED.get(parts[7], parts[7]),
        "cost": _COST_EXPANDED.get(parts[8], parts[8]),
    }


def _decode_output_slots(output_compact: str, warnings: list[str]) -> dict[str, object]:
    parts = str(output_compact or "").split(".")
    if len(parts) != len(_OUTPUT_SLOT_NAMES):
        warnings.append(f"output_slot_count:{len(parts)}")
    parts = [*parts[: len(_OUTPUT_SLOT_NAMES)], *([""] * len(_OUTPUT_SLOT_NAMES))][: len(_OUTPUT_SLOT_NAMES)]
    return {
        "route": _ROUTE_EXPANDED.get(parts[0], parts[0]),
        "model": _MODEL_EXPANDED.get(parts[1], parts[1]),
        "context": _CONTEXT_EXPANDED.get(parts[2], parts[2]),
        "reason": _REASON_EXPANDED.get(parts[3], parts[3]),
        "verifier": parts[4] == "1",
    }


def _decode_grounding(value: str) -> str:
    text = str(value or "")
    if text == "0":
        return "none"
    if text == "FULL":
        return "full"
    items = [_GROUNDING_EXPANDED[item] for item in text if item in _GROUNDING_EXPANDED]
    return "+".join(items) if items else text


def _patch_authority(grounding: dict[str, Any] | None) -> str:
    if isinstance(grounding, dict):
        diagnostics = grounding.get("route_diagnostics", {}) if isinstance(grounding.get("route_diagnostics"), dict) else {}
        value = (
            grounding.get("patch_authority")
            or grounding.get("safety_policy")
            or diagnostics.get("patch_authority")
        )
        if value:
            return str(value)
    return PATCH_AUTHORITY_DEFAULT


def _add_concept(
    concepts: list[dict[str, object]],
    slot: str,
    value: Any,
    weight: float,
    source: str,
) -> None:
    if value is None or value == "":
        return
    concept_value = _concept_value(value)
    concepts.append(
        {
            "id": f"{slot.upper()}::{concept_value}",
            "weight": round(float(weight), 4),
            "source": source,
            "slot": slot,
            "value": value,
        }
    )


def _concept_value(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    text = str(value).strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_") or "EMPTY"


def _frame_from_capsule(capsule: Mapping[str, object], *, grounding: dict[str, Any] | None) -> dict[str, object]:
    context = capsule.get("context", {}) if isinstance(capsule.get("context"), dict) else {}
    target_files = list(context.get("target_files", []) or []) if isinstance(context, dict) else []
    target_symbols = list(context.get("target_symbols", []) or []) if isinstance(context, dict) else []
    tests = list(context.get("tests", []) or []) if isinstance(context, dict) else []
    op = str(capsule.get("op") or "").lower()
    instruction = str(capsule.get("human_instruction") or "").lower()
    text = f"{op} {instruction}"
    grounding_items = _grounding_from_packet_or_capsule(grounding, capsule)
    if target_files:
        grounding_items.add("file_exists")
    if target_symbols:
        grounding_items.add("symbol_exists")
    if tests:
        grounding_items.add("tests_exist")
    if context.get("line_ranges") or "codemap" in str(capsule.get("truth_policy", "")).lower():
        grounding_items.add("codemap_grounded")
    if {"file_exists", "symbol_exists", "tests_exist", "codemap_grounded"} <= grounding_items:
        grounding_items.add("full")
    target_file = str(target_files[0]) if target_files else ""
    return {
        "intent": _intent_from_text(text),
        "artifact": _artifact_from_file(target_file),
        "action": _action_from_text(text),
        "scope": "symbol" if target_symbols else "file" if target_files else "repo",
        "risk": "medium",
        "grounding": tuple(sorted(grounding_items)) or ("none",),
        "tests": "existing" if tests else "none",
        "quality": "verifier_required",
        "cost": "local_first",
        "target_file": target_file or None,
        "target_symbol": str(target_symbols[0]) if target_symbols else None,
    }


def _decision_from_capsule(capsule: Mapping[str, object], *, grounding: dict[str, Any] | None) -> dict[str, object]:
    route_decision = capsule.get("route_decision", {}) if isinstance(capsule.get("route_decision"), dict) else {}
    route = str(route_decision.get("route") or "").strip().upper()
    if not route:
        selected = str(route_decision.get("selected_route") or "").strip().upper()
        route = _route_from_selected_route(selected, grounding)
    if not route and isinstance(grounding, dict):
        route = str(grounding.get("route") or "").strip().upper()
    route = route or "PLAN_ONLY"
    return {
        "route": route,
        "model": route_decision.get("model") or _model_for_route(route),
        "context": route_decision.get("context") or _context_for_route(route),
        "reason": route_decision.get("reason") or _reason_for_route(route),
        "verifier_required": _decision_verifier_required(route_decision, route),
    }


def _grounding_from_packet_or_capsule(
    grounding: dict[str, Any] | None,
    capsule: Mapping[str, object],
) -> set[str]:
    items: set[str] = set()
    if isinstance(grounding, dict):
        if grounding.get("target_file") or grounding.get("source_spans"):
            items.add("file_exists")
        if grounding.get("target_symbol") or grounding.get("exact_hits"):
            items.add("symbol_exists")
        if grounding.get("tests") or grounding.get("test_files"):
            items.add("tests_exist")
        if grounding.get("source_spans") or grounding.get("hashes"):
            items.add("codemap_grounded")
        route = str(grounding.get("route") or "")
        if route == "BUILDER_PATCH" and {"file_exists", "symbol_exists", "tests_exist", "codemap_grounded"} <= items:
            items.add("full")
    if capsule.get("source_spans"):
        items.add("codemap_grounded")
    return items


def _intent_from_text(text: str) -> str:
    if any(term in text for term in ("patch", "fix", "modify", "wire", "connect")):
        return "code_refactor"
    if any(term in text for term in ("test", "verify")):
        return "verify"
    if any(term in text for term in ("localize", "locate", "find")):
        return "localize"
    return "explain"


def _action_from_text(text: str) -> str:
    if any(term in text for term in ("patch", "fix", "modify", "wire", "connect")):
        return "modify"
    if any(term in text for term in ("test", "verify")):
        return "verify"
    return "inspect"


def _artifact_from_file(path: str) -> str:
    name = str(path or "")
    if not name:
        return "python_module"
    if name.endswith(".py") and ("/test_" in f"/{name}" or name.rsplit("/", 1)[-1].startswith("test_")):
        return "test_file"
    if name.endswith(".py"):
        return "python_module"
    if name.endswith((".md", ".rst", ".txt")):
        return "documentation"
    return "python_module"


def _route_from_selected_route(selected: str, grounding: dict[str, Any] | None) -> str:
    if selected == "CODEGEMMA_MICRO_PATCH":
        return "BUILDER_PATCH"
    if selected in {"LOCAL_DETERMINISTIC", "HUMAN_REVIEW", "OPENHANDS_SANDBOX"}:
        return "PLAN_ONLY"
    if selected == "LOCAL_GEMMA_VISUAL_SUMMARY":
        return "LOCALIZE_FIRST"
    if selected == "FIREWORKS_TEXT_REASONER":
        return "PLAN_ONLY"
    if isinstance(grounding, dict) and grounding.get("route"):
        return str(grounding.get("route")).upper()
    return selected or "PLAN_ONLY"
