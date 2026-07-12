"""Presenter-safe bulk-intent trace for the unified Aura showcase.

This adapter does not introduce a second parser or router. It calls Aura's existing
intent-ingestion, Coding Arena FST, LEXC, six-slot, VSA, Context Crusher, grounding,
and topology-facing contracts, then exposes a bounded explanatory trace.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
from typing import Any, Iterable

import aura_intent_ingestion as ingestion
from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame
from aura_lexc import AuraLexc
from aura_polysynthetic_intent import PolysyntheticIntentPacket, bind_intent_packet

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
INTENT_TRACE_VERSION = "AURA_SHOWCASE_BULK_INTENT_TRACE_V1"
MAX_BULK_INTENT_CHARS = 12_000
MAX_TOKEN_TRACE = 64
SLOT_KEYS = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")

DEFAULT_BULK_INTENT = (
    "Improve the Learning Arena demo by updating compile_intent_packet so a person can paste "
    "a long natural-language intention and watch Aura classify it without an LLM, display the "
    "six-slot packet and FST tags, localize the relevant topology, and prepare a bounded proposal "
    "for a replaceable coding worker. Preserve existing tests and human review. Never access "
    "secrets, commit, push, or merge."
)

_TAG_GROUPS = (
    ("operation", ingestion._OP_KEYWORDS),
    ("domain", ingestion._DOMAIN_KEYWORDS),
    ("target", ingestion._TARGET_KEYWORDS),
    ("output", ingestion._OUTPUT_KEYWORDS),
)

_INPUT_TAG_LEGEND = {
    "I": "intent",
    "A": "artifact",
    "X": "action",
    "S": "scope",
    "R": "risk",
    "G": "grounding",
    "T": "tests",
    "Q": "quality",
    "C": "cost/model policy",
}
_OUTPUT_TAG_LEGEND = {
    "O": "selected route",
    "M": "model policy",
    "K": "context class",
    "E": "routing reason",
    "V": "verifier requirement",
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+\-/=]{8,}"),
    re.compile(r"(?i)\b(api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
)


def compile_bulk_intent_trace(
    text: str,
    *,
    repo_root: str | Path = ".",
    include_grounding: bool = True,
) -> dict[str, Any]:
    """Compile free-form bulk intention into an inspectable, non-LLM routing trace."""
    root = Path(repo_root).resolve()
    raw = str(text or "").strip()
    if not raw:
        return _error("bulk_intent_required")
    if len(raw) > MAX_BULK_INTENT_CHARS:
        return _error("bulk_intent_too_large", max_chars=MAX_BULK_INTENT_CHARS)

    sanitized, redactions = _redact_secrets(raw)
    objective = " ".join(sanitized.split())
    structured = f"[AURA_INTENT]\nOBJECTIVE: {objective}\n"
    compiled = ingestion.compile_intent_packet(
        structured,
        repo_root=root,
        skip_grounding=not include_grounding,
    )
    if not compiled.get("ok"):
        return _error(str(compiled.get("error") or "intent_compilation_failed"))

    lexical = _lexical_trace(objective, root)
    tag_trace = _tag_trace(objective)
    frame = _routing_frame(compiled)
    decision = AuraCodingArenaRouter().route(frame)
    six_slot = _six_slot_packet(frame, decision.to_dict(), objective)
    handoff = ingestion.intent_to_agent_handoff(compiled, agent="replaceable_worker", repo_root=root)
    lexc = _lexc_trace(objective, frame, root)

    likely_files = [str(value) for value in compiled.get("likely_files", []) if str(value)][:10]
    likely_symbols = [str(value) for value in compiled.get("likely_symbols", []) if str(value)][:10]
    keywords = ingestion._extract_keywords(objective)[:16]

    return {
        "ok": True,
        "version": INTENT_TRACE_VERSION,
        "raw_intent": sanitized,
        "objective": objective,
        "redactions_applied": redactions,
        "model_calls_made": 0,
        "parse_mode": "deterministic_local_pre_llm",
        "pipeline": [
            "bulk_human_intention",
            "4096_primitive_lexical_addressing",
            "local_tag_extraction",
            "canonical_six_slot_packet",
            "machine_fst_hard_gate",
            "codemap_localization",
            "bounded_agent_handoff",
        ],
        "lexical_codebook": lexical,
        "tag_trace": tag_trace,
        "compressed_objective": compiled.get("polysynthetic_packet", ""),
        "raw_objective_tokens_est": compiled.get("raw_objective_tokens_est", 0),
        "compressed_tokens_est": compiled.get("compressed_tokens_est", 0),
        "six_slot_packet": six_slot,
        "routing_frame": frame.to_dict(),
        "machine_route": decision.to_dict(),
        "machine_symbol_trace": {
            "input": _symbol_segments(frame.symbol_input(), _INPUT_TAG_LEGEND),
            "output": _symbol_segments(decision.symbol_output(), _OUTPUT_TAG_LEGEND),
            "compact_input": frame.compact_input(),
            "compact_output": decision.compact_output(),
            "jspace_packet": decision.jspace_packet(),
        },
        "lexc_trace": lexc,
        "grounding": compiled.get("grounding", {}),
        "likely_files": likely_files,
        "likely_symbols": likely_symbols,
        "keywords": keywords,
        "context_crush_summary": compiled.get("context_crush_summary", {}),
        "st3gg_decision": compiled.get("st3gg_decision", {}),
        "jspace_state": compiled.get("jspace_state", {}),
        "agent_handoff": {
            "agent": handoff.get("agent", "replaceable_worker"),
            "compressed_context": handoff.get("compressed_context", ""),
            "compressed_tokens_est": handoff.get("compressed_tokens_est", 0),
            "likely_files": handoff.get("likely_files", []),
            "likely_symbols": handoff.get("likely_symbols", []),
            "route_decision": handoff.get("route_decision", {}),
            "note": handoff.get("note", ""),
        },
        "guardrails": {
            "admitted": [
                "parse local text",
                "address known lexical primitives",
                "classify intent and routing features",
                "localize CODEMAP candidates",
                "prepare bounded context for a replaceable worker",
            ],
            "blocked": [
                "secret disclosure",
                "private reasoning capture",
                "unrelated repository access",
                "visual topology as patch authority",
                "automatic commit",
                "automatic push",
                "automatic pull request",
                "automatic merge",
            ],
        },
        "truth_notice": (
            "The 4,096-word codebook supplies stable lexical addresses; local tag extraction and "
            "the machine FST perform classification and admission. The six-slot order is a software "
            "contract inspired by Athabaskan morphotactics. Anishinaabemowin governance alignments, "
            "the six-slot contract, and Aura's machine routing DSL remain distinct layers."
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def _routing_frame(compiled: dict[str, Any]) -> RoutingFrame:
    raw = dict(compiled.get("routing_frame") or {})
    grounding = dict(compiled.get("grounding") or {})
    target_file = str(grounding.get("target_file") or "") or None
    target_symbol = str(grounding.get("target_symbol") or "") or None
    return RoutingFrame(
        intent=str(raw.get("intent") or "explain"),
        artifact=str(raw.get("artifact") or "python_module"),
        action=str(raw.get("action") or "inspect"),
        scope=str(raw.get("scope") or "symbol"),
        risk=str(raw.get("risk") or "low"),
        grounding=tuple(raw.get("grounding") or ("none",)),
        tests=str(raw.get("tests") or "none"),
        quality=str(raw.get("quality") or "balanced"),
        cost=str(raw.get("cost") or "local_first"),
        target_file=target_file,
        target_symbol=target_symbol,
    )


def _six_slot_packet(frame: RoutingFrame, decision: dict[str, Any], objective: str) -> dict[str, Any]:
    if frame.scope in {"subsystem", "repo"}:
        aspect = "DECOMPOSE_FIRST"
    elif frame.tests == "none" and frame.action in {"modify", "repair"}:
        aspect = "TEST_GAP_FIRST"
    else:
        aspect = "BOUNDED"
    voice_parts = [str(decision.get("model") or "no_model").upper()]
    if decision.get("verifier_required"):
        voice_parts.append("VERIFIER_REQUIRED")
    slots = {
        "DIR": str(decision.get("route") or "PLAN_ONLY"),
        "ASP": aspect,
        "CLASS": frame.intent.upper(),
        "SUBJ": f"{frame.artifact.upper()}:{frame.scope.upper()}",
        "VOICE": "+".join(voice_parts),
        "STEM": frame.action.upper(),
    }
    packet = PolysyntheticIntentPacket.from_slots(
        slots,
        adjuncts={
            "risk": frame.risk,
            "grounding": "+".join(frame.grounding),
            "tests": frame.tests,
            "quality": frame.quality,
            "cost": frame.cost,
            "model_class": str(decision.get("model") or "no_model"),
        },
        objective=objective,
    )
    result = packet.canonical_dict()
    result["digest"] = packet.digest()
    result["derivation"] = {
        "DIR": "selected machine route / lifecycle direction",
        "ASP": "bounded, decompose-first, or test-gap execution aspect",
        "CLASS": "classified intent/effect class",
        "SUBJ": "target artifact and scope",
        "VOICE": "model and verifier execution context",
        "STEM": "terminal operation",
    }
    try:
        bound = bind_intent_packet(packet)
        result["vsa_binding"] = bound.to_dict()
    except Exception as exc:
        result["vsa_binding"] = {"available": False, "reason": type(exc).__name__}
    return result


def _lexical_trace(objective: str, root: Path) -> dict[str, Any]:
    path = root / "english_lexicon.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    inverse = {str(word).casefold(): str(address) for address, word in raw.items()}
    words = re.findall(r"[A-Za-z][A-Za-z0-9_'-]*", objective.casefold())
    unique = list(dict.fromkeys(words))
    records = []
    recognized = 0
    for word in unique[:MAX_TOKEN_TRACE]:
        address = inverse.get(word)
        if address is not None:
            recognized += 1
            records.append({
                "token": word,
                "known": True,
                "address": address,
                "index": int(address, 2),
                "source": "english_lexicon_12_bit",
            })
        else:
            checksum = sum(ord(char) for char in word) % 4096
            records.append({
                "token": word,
                "known": False,
                "address": format(checksum, "012b"),
                "index": checksum,
                "source": "deterministic_checksum_fallback",
            })
    known_total = sum(1 for word in unique if word in inverse)
    return {
        "path": "english_lexicon.json",
        "primitive_count": len(raw),
        "address_width_bits": 12,
        "unique_input_tokens": len(unique),
        "recognized_unique_tokens": known_total,
        "coverage_ratio": round(known_total / max(1, len(unique)), 4),
        "shown_token_count": len(records),
        "tokens": records,
        "role": "stable lexical addressing, not semantic authority by itself",
    }


def _tag_trace(objective: str) -> dict[str, Any]:
    lowered = objective.casefold()
    groups: dict[str, Any] = {}
    for group, mappings in _TAG_GROUPS:
        records = []
        for pattern, tag in mappings:
            matches = sorted(set(match.group(0) for match in re.finditer(pattern, lowered)))
            if matches:
                records.append({"tag": tag, "matched_text": matches, "pattern": pattern})
        groups[group] = records
    groups["fixed"] = [
        {"tag": "PYTHON", "slot": "ENV"},
        {"tag": "TOKEN_SPARING", "slot": "CONSTRAINT"},
    ]
    return groups


def _lexc_trace(objective: str, frame: RoutingFrame, root: Path) -> dict[str, Any]:
    path = root / "aura.lexc"
    try:
        lexc = AuraLexc.from_path(path, strict=False)
    except Exception as exc:
        return {"available": False, "reason": type(exc).__name__}

    by_slot: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for arc in lexc.arcs:
        key = arc.slot.value
        if arc.lexical in seen[key] or len(by_slot[key]) >= 12:
            continue
        seen[key].add(arc.lexical)
        by_slot[key].append({
            "symbol": arc.lexical,
            "source_layer": arc.source,
            "target_layer": arc.target,
        })

    desired = {
        "code_refactor": ("refactor", "+SYS_MOD", "+MUTATE"),
        "repair": ("+SYS_ERR", "_RESOLVE", "_ROLLBACK"),
        "localize": ("+QUERY", "+T1_RAM"),
        "research_rank": ("analyze",),
        "explain": ("analyze",),
        "verify": ("_VALIDATE",),
    }.get(frame.intent, ())
    objective_terms = set(re.findall(r"[a-z_]+", objective.casefold()))
    candidates = []
    for route in lexc.complete_routes(limit=256):
        symbols = list(route.symbols)
        score = sum(8 for symbol in desired if symbol in symbols)
        score += sum(2 for symbol in symbols if symbol.casefold().lstrip("+_") in objective_terms)
        if score:
            candidates.append((score, symbols, route))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = candidates[0][2] if candidates else None
    return {
        "available": True,
        "path": "aura.lexc",
        "lexicon_layer_count": len(lexc.lexicons),
        "arc_count": len(lexc.arcs),
        "complete_route_count_bounded": len(lexc.complete_routes(limit=256)),
        "slot_layers": {key: by_slot.get(key, []) for key in SLOT_KEYS},
        "candidate_route": ({
            "valid_complete_route": True,
            "selection_basis": "classified intent symbol matched to an existing complete LEXC route",
            "states": list(selected.states),
            "slots": {arc.slot.value: arc.lexical for arc in selected.arcs},
            "arcs": [
                {
                    "slot": arc.slot.value,
                    "source": arc.source,
                    "target": arc.target,
                    "lexical": arc.lexical,
                    "surface": arc.surface,
                    "line": arc.line,
                }
                for arc in selected.arcs
            ],
            "advisory_only": True,
        } if selected else None),
        "note": (
            "This is the repository LEXC vocabulary and a structurally valid candidate path. "
            "The machine Coding Arena FST remains the operative hard-gate route for this demo."
        ),
    }


def _symbol_segments(value: str, legend: dict[str, str]) -> list[dict[str, str]]:
    records = []
    for raw in str(value or "").split("|"):
        if not raw:
            continue
        prefix = raw.split(":", 1)[0]
        records.append({"symbol": raw, "meaning": legend.get(prefix, "routing feature")})
    return records


def _redact_secrets(text: str) -> tuple[str, int]:
    output = text
    count = 0
    for pattern in _SECRET_PATTERNS:
        output, replaced = pattern.subn("[REDACTED_SECRET]", output)
        count += replaced
    return output, count


def _error(error: str, **extra: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "version": INTENT_TRACE_VERSION,
        "error": error,
        **extra,
        "model_calls_made": 0,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }
