"""
Aura Intent Ingestion — polysynthetic intent document parser and compiler.

Parses Aura-native Markdown intent documents (.aura/intents/*.aura.md) and
compiles them into IntentPackets that route through Aura's architecture:
  * Polysynthetic compression (lightweight local tag extractor)
  * LEXC route validation (aura.lexc)
  * FST routing (lightweight local RoutingFrame + route decision)
  * Affordance Directory lookup
  * Concept Workspace search
  * CODEMAP file/symbol localization
  * DREAM-lite reranking
  * Context Crusher compression
  * ST3GG egress decision
  * Coding Arena Grounding
  * JSpace advisory state
  * QDKT fast-path lookup
  * Agent handoff packet generation

Dependencies: stdlib only at module level. All Aura imports are lazy.
numpy is NOT required — all numpy-dependent modules are wrapped in try/except.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants and invariants
# ---------------------------------------------------------------------------

INGESTION_VERSION = "AURA_INTENT_INGESTION_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# All recognized [AURA_*] section names.
_AURA_SECTIONS = [
    "AURA_INTENT",
    "AURA_CONTEXT",
    "AURA_POLYSYNTHETIC_PACKET",
    "AURA_LEXC_ROUTE",
    "AURA_CAPABILITIES",
    "AURA_ROUTE_HINTS",
    "AURA_CONSTRAINTS",
    "AURA_GATES",
    "AURA_HANDOFF",
    "AURA_ACCEPTANCE",
    "AURA_RISKS",
    "AURA_TOKEN_BUDGET",
    "AURA_MEMORY_FEEDBACK",
]

# Polysynthetic tag keyword mapping.
_OP_KEYWORDS = [
    (r"refactor|improve|change|modify|update|rewrite|move", "IMPROVE"),
    (r"test|verify|check|validate", "VERIFY"),
    (r"find|locate|where|isolate", "LOCATE"),
    (r"fix|repair|debug|heal", "REPAIR"),
    (r"build|create|add|new|generate|implement", "BUILD"),
    (r"research|rank|compare|survey", "RESEARCH"),
]
_DOMAIN_KEYWORDS = [
    (r"coding.?arena|coding_arena", "CODING_ARENA"),
    (r"agent.?arena|agent_arena|bridge", "AGENT_ARENA"),
    (r"human.?agent|human_agent", "HUMAN_AGENT"),
    (r"llm.?egress|egress|fireworks", "LLM_EGRESS"),
    (r"context|crush|compress", "CONTEXT"),
    (r"routing|fst|lexc|jspace", "ROUTING"),
    (r"topology|codemap|graph", "TOPOLOGY"),
    (r"token|economics|savings", "TOKEN_ECONOMY"),
]
_TARGET_KEYWORDS = [
    (r"cockpit|native", "NATIVE_COCKPIT"),
    (r"ingestion|intent", "INTENT_INGESTION"),
    (r"connectome|capability", "CAPABILITY_CONNECTOME"),
    (r"gates|workflow", "WORKFLOW_GATES"),
    (r"egress|fireworks", "EGRESS"),
    (r"router|routing", "ROUTER"),
]
_OUTPUT_KEYWORDS = [
    (r"checkpoint|gate", "CHECKPOINTED_HANDOFF"),
    (r"handoff|packet|capsule", "COMPACT_HANDOFF"),
    (r"report|summary", "REPORT"),
    (r"patch|diff", "PATCH"),
    (r"test|verify", "TEST_RESULT"),
]

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "to", "for", "of", "in", "on", "and", "or",
    "with", "by", "from", "that", "this", "it", "as", "at", "be", "was",
    "will", "can", "could", "should", "would", "may", "might", "must",
    "shall", "do", "does", "did", "has", "have", "had", "not", "but",
    "about", "into", "out", "up", "down", "over", "under", "again",
    "more", "most", "some", "any", "all", "both", "each", "few",
    "where", "when", "why", "how", "what", "who",
})


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


# ---------------------------------------------------------------------------
# CODEMAP loader (lightweight, cached)
# ---------------------------------------------------------------------------

_CODEMAP_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CODEMAP_TTL = 120.0


def _load_codemap(repo_root: Path) -> dict[str, Any]:
    import time as _time
    path = repo_root / ".aura" / "CODEMAP.json"
    key = str(path)
    now = _time.time()
    if key in _CODEMAP_CACHE:
        ts, data = _CODEMAP_CACHE[key]
        if now - ts < _CODEMAP_TTL:
            return data
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _CODEMAP_CACHE[key] = (now, data)
        return data
    except Exception:
        return {}


def _suggest_files_from_codemap(codemap: dict, keywords: list[str], max_results: int = 10) -> list[str]:
    files = codemap.get("files", [])
    file_list = []
    if isinstance(files, list):
        file_list = [str(f.get("path", "")) for f in files if isinstance(f, dict) and f.get("path")]
    elif isinstance(files, dict):
        file_list = list(files.keys())

    scored: list[tuple[float, str]] = []
    for fp in file_list:
        if not fp or fp.endswith((".json", ".bak", ".save", ".txt", ".pdf", ".tex")):
            continue
        fp_lower = fp.lower()
        score = sum(1.0 for kw in keywords if kw in fp_lower)
        if fp.endswith(".py"):
            score += 0.3
        if score > 0:
            scored.append((score, fp))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [fp for _, fp in scored[:max_results]]


def _suggest_symbols_from_codemap(codemap: dict, keywords: list[str], max_results: int = 10) -> list[str]:
    symbol_index = codemap.get("symbol_index", {})
    if not isinstance(symbol_index, dict):
        return []
    scored: list[tuple[float, str]] = []
    for sym_name in symbol_index:
        sym_lower = sym_name.lower()
        score = sum(1.0 for kw in keywords if kw in sym_lower)
        if score > 0:
            scored.append((score, sym_name))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [sym for _, sym in scored[:max_results]]


# ---------------------------------------------------------------------------
# Polysynthetic tag extractor (lightweight, numpy-free)
# ---------------------------------------------------------------------------


def _match_tags(text: str, keyword_map: list[tuple[str, str]]) -> list[str]:
    """Match text against keyword patterns and return tags."""
    text_lower = text.lower()
    tags: list[str] = []
    seen: set[str] = set()
    for pattern, tag in keyword_map:
        if re.search(pattern, text_lower):
            if tag not in seen:
                tags.append(tag)
                seen.add(tag)
    return tags


def _extract_polysynthetic_packet(objective: str) -> str:
    """Extract a polysynthetic packet from an objective string."""
    op_tags = _match_tags(objective, _OP_KEYWORDS) or ["IMPROVE"]
    domain_tags = _match_tags(objective, _DOMAIN_KEYWORDS) or ["CODING_ARENA"]
    target_tags = _match_tags(objective, _TARGET_KEYWORDS) or ["TARGET"]
    output_tags = _match_tags(objective, _OUTPUT_KEYWORDS) or ["COMPACT_HANDOFF"]

    parts = [
        f"[OP:{op_tags[0]}]",
        f"[DOMAIN:{domain_tags[0]}]",
        f"[TARGET:{target_tags[0]}]",
        "[ENV:PYTHON]",
        "[CONSTRAINT:TOKEN_SPARING]",
        f"[OUTPUT:{output_tags[0]}]",
    ]
    return "".join(parts)


# ---------------------------------------------------------------------------
# Lightweight FST routing (numpy-free)
# ---------------------------------------------------------------------------


def _build_routing_frame(objective: str, route_hints: dict | None = None,
                         grounding_result: dict | None = None) -> dict[str, Any]:
    """Build a lightweight RoutingFrame dict without numpy."""
    obj_lower = objective.lower()

    # Intent
    if any(w in obj_lower for w in ["refactor", "change", "modify", "update", "rewrite", "move", "build", "create", "add", "implement"]):
        intent = "code_refactor"
    elif any(w in obj_lower for w in ["test", "verify", "check", "validate"]):
        intent = "verify"
    elif any(w in obj_lower for w in ["find", "locate", "where", "isolate"]):
        intent = "localize"
    elif any(w in obj_lower for w in ["fix", "repair", "debug", "heal"]):
        intent = "repair"
    elif any(w in obj_lower for w in ["research", "rank", "compare", "survey"]):
        intent = "research_rank"
    else:
        intent = "explain"

    # Action
    action_map = {"code_refactor": "modify", "verify": "verify", "localize": "inspect",
                  "repair": "repair", "research_rank": "rank", "explain": "inspect"}
    action = action_map.get(intent, "inspect")

    # Scope
    if any(w in obj_lower for w in ["repo", "repository", "all", "everything", "subsystem", "system", "whole"]):
        scope = "subsystem"
    elif any(w in obj_lower for w in ["file", "module", "path"]):
        scope = "file"
    else:
        scope = "symbol"

    # Risk
    risk = "low"
    if any(w in obj_lower for w in ["live", "production", "critical", "hot"]):
        risk = "live"
    elif any(w in obj_lower for w in ["high", "danger", "breaking"]):
        risk = "high"
    elif any(w in obj_lower for w in ["medium", "moderate"]):
        risk = "medium"

    # Grounding
    grounding = ("none",)
    if grounding_result:
        if grounding_result.get("grounding_ok"):
            grounding = ("codemap_grounded", "file_exists")
        elif grounding_result.get("candidate_files"):
            grounding = ("file_exists",)

    # Tests
    tests = "none"
    if grounding_result and grounding_result.get("tests"):
        tests = "existing"

    # Quality
    quality = "balanced"
    if "verifier" in obj_lower or "verify" in obj_lower:
        quality = "verifier_required"
    elif "fast" in obj_lower or "quick" in obj_lower:
        quality = "fast"

    # Cost
    cost = "local_first"
    if intent in ("explain", "localize"):
        cost = "no_model"

    frame = {
        "intent": intent,
        "artifact": "python_module",
        "action": action,
        "scope": scope,
        "risk": risk,
        "grounding": list(grounding),
        "tests": tests,
        "quality": quality,
        "cost": cost,
    }

    # Override from route hints
    if route_hints:
        for key in ("intent", "action", "scope", "risk", "quality", "cost", "tests"):
            if key in route_hints:
                val = str(route_hints[key]).strip().lower()
                if val:
                    frame[key] = val
        # Handle grounding specially (comma-separated list)
        if "grounding" in route_hints:
            val = str(route_hints["grounding"]).strip()
            if val:
                grounding_list = [v.strip().lower() for v in val.split(",") if v.strip()]
                frame["grounding"] = grounding_list

    return frame


def _route_decision(frame: dict[str, Any]) -> dict[str, Any]:
    """Determine route from a routing frame (mirrors FST hard-gate logic)."""
    intent = frame.get("intent", "explain")
    scope = frame.get("scope", "symbol")
    grounding = set(frame.get("grounding", ["none"]))
    tests = frame.get("tests", "none")
    risk = frame.get("risk", "low")

    # Hard gates (priority order)
    if "none" in grounding or not grounding - {"none"}:
        return {"route": "LOCALIZE_FIRST", "reason": "missing_grounding", "model": "no_model",
                "verifier_required": False, "next_state": "LOCALIZE_FIRST"}

    if scope in ("subsystem", "repo"):
        return {"route": "PLAN_ONLY", "reason": "broad_scope_decompose_first", "model": "no_model",
                "verifier_required": False, "next_state": "PLAN_ONLY"}

    if tests == "none" and intent in ("code_refactor", "repair"):
        if risk in ("high", "live"):
            return {"route": "TEST_GAP_FILL", "reason": "missing_tests_high_risk", "model": "local_first",
                    "verifier_required": True, "next_state": "NEED_TEST"}
        return {"route": "TEST_GAP_FILL", "reason": "missing_tests", "model": "local_first",
                "verifier_required": False, "next_state": "NEED_TEST"}

    if intent == "verify":
        return {"route": "VERIFY_ONLY", "reason": "verify_intent", "model": "local_first",
                "verifier_required": True, "next_state": "VERIFY_ONLY"}

    if intent in ("explain", "research_rank"):
        return {"route": "PLAN_ONLY", "reason": "read_only_intent", "model": "no_model",
                "verifier_required": False, "next_state": "PLAN_ONLY"}

    if intent == "localize":
        return {"route": "LOCALIZE_FIRST", "reason": "localize_intent", "model": "no_model",
                "verifier_required": False, "next_state": "LOCALIZE_FIRST"}

    if risk == "live":
        return {"route": "BLOCKED_WITH_REASON", "reason": "live_risk_requires_human_gate", "model": "no_model",
                "verifier_required": True, "next_state": "BLOCKED"}

    # Grounded refactor with tests -> builder
    if intent == "code_refactor" and "codemap_grounded" in grounding and tests in ("existing", "generated"):
        return {"route": "BUILDER_PATCH", "reason": "grounded_refactor_with_tests", "model": "local_first",
                "verifier_required": risk in ("high", "live"), "next_state": "HUMAN_GATE"}

    if intent == "repair":
        return {"route": "REPAIR_PATCH", "reason": "repair_intent", "model": "local_first",
                "verifier_required": True, "next_state": "HUMAN_GATE"}

    return {"route": "PLAN_ONLY", "reason": "default_no_grounded_route", "model": "no_model",
            "verifier_required": False, "next_state": "PLAN_ONLY"}


# ---------------------------------------------------------------------------
# 1. parse_intent_document
# ---------------------------------------------------------------------------


def parse_intent_document(path_or_text: str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Parse an Aura-native Markdown intent document.

    Accepts a file path or raw text. Returns a dict with:
    - frontmatter: dict of YAML frontmatter key-values
    - sections: dict mapping section names to their text content
    - objective: extracted objective string
    - raw_text: the full document text
    - ok: True if parsing succeeded
    """
    root = Path(repo_root).resolve()

    # Determine if path_or_text is a file path or raw text
    raw_text = ""
    source_path = None
    if "\n" not in path_or_text and len(path_or_text) < 500:
        candidate = root / path_or_text
        if candidate.exists() and candidate.is_file():
            try:
                raw_text = candidate.read_text(encoding="utf-8")
                source_path = str(path_or_text)
            except OSError:
                pass
    if not raw_text:
        raw_text = path_or_text

    result: dict[str, Any] = {
        "ok": True,
        "version": INGESTION_VERSION,
        "source_path": source_path,
        "raw_text": raw_text,
        "frontmatter": {},
        "sections": {},
        "objective": "",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

    # Parse YAML frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw_text, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        for line in fm_text.splitlines():
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if key and value:
                    result["frontmatter"][key] = value
        body = raw_text[fm_match.end():]
    else:
        body = raw_text

    # Parse [AURA_*] sections
    sections: dict[str, str] = {}
    # Match [SECTION_NAME] followed by content until next [SECTION_NAME] or EOF
    section_pattern = re.compile(
        r"^\[(" + "|".join(_AURA_SECTIONS) + r")\]\s*$\n",
        re.MULTILINE,
    )
    matches = list(section_pattern.finditer(body))
    if matches:
        for i, match in enumerate(matches):
            section_name = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            section_content = body[start:end].strip()
            sections[section_name] = section_content
    else:
        # No structured sections found — treat as unstructured markdown
        # Try to extract an objective from the first non-empty line
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        if lines:
            sections["AURA_INTENT"] = body.strip()

    result["sections"] = sections

    # Extract objective from AURA_INTENT section
    intent_section = sections.get("AURA_INTENT", "")
    obj_match = re.search(r"OBJECTIVE:\s*(.+?)(?:\n|$)", intent_section, re.IGNORECASE)
    if obj_match:
        result["objective"] = obj_match.group(1).strip()
    elif intent_section:
        # Use first line as objective
        result["objective"] = intent_section.split("\n")[0].strip()[:200]
    else:
        result["objective"] = ""

    return result


# ---------------------------------------------------------------------------
# 2. compile_intent_packet
# ---------------------------------------------------------------------------


def compile_intent_packet(parsed_doc: dict | str, repo_root: str | Path = ".",
                          skip_grounding: bool = False) -> dict[str, Any]:
    """Compile a parsed intent document into an IntentPacket.

    Accepts a parsed dict (from parse_intent_document) or a raw string.
    Set skip_grounding=True to skip the slow grounding call (for tests/fast mode).
    """
    root = Path(repo_root).resolve()

    if isinstance(parsed_doc, str):
        parsed_doc = parse_intent_document(parsed_doc, repo_root=root)

    objective = parsed_doc.get("objective", "")
    sections = parsed_doc.get("sections", {})
    frontmatter = parsed_doc.get("frontmatter", {})

    if not objective:
        return {
            "ok": False,
            "error": "No objective found in intent document.",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # --- Token estimates ---
    raw_objective_tokens_est = _estimate_tokens(objective)

    # --- Polysynthetic packet ---
    poly_section = sections.get("AURA_POLYSYNTHETIC_PACKET", "")
    if poly_section:
        polysynthetic_packet = poly_section.strip()
    else:
        polysynthetic_packet = _extract_polysynthetic_packet(objective)
    compressed_tokens_est = _estimate_tokens(polysynthetic_packet)

    # --- LEXC route ---
    lexc_result = route_intent_to_lexc(parsed_doc, repo_root=root)

    # --- Route hints ---
    route_hints_text = sections.get("AURA_ROUTE_HINTS", "")
    route_hints: dict[str, Any] = {}
    for line in route_hints_text.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key and value:
                route_hints[key] = value

    # --- Grounding ---
    grounding_result: dict[str, Any] = {}
    grounding_warning = ""
    if not skip_grounding:
        try:
            from aura_coding_arena_grounding import ground_coding_arena_intent
            grounding_result = ground_coding_arena_intent(objective, root)
        except Exception as exc:
            grounding_warning = f"Grounding lookup failed: {exc}"

    # --- FST routing ---
    fst_result = route_intent_to_fst(parsed_doc, repo_root=root, route_hints=route_hints,
                                     grounding_result=grounding_result)

    # --- Affordances ---
    affordance_result = route_intent_to_affordances(objective, repo_root=root)

    # --- Concept Workspace ---
    concept_result = route_intent_to_concept_workspace(objective, repo_root=root)

    # --- CODEMAP localization ---
    codemap = _load_codemap(root)
    keywords = _extract_keywords(objective)
    likely_files = _suggest_files_from_codemap(codemap, keywords)
    likely_symbols = _suggest_symbols_from_codemap(codemap, keywords)

    # Merge with grounding candidate files
    if grounding_result.get("candidate_files"):
        for cf in grounding_result["candidate_files"][:3]:
            if isinstance(cf, dict):
                fp = cf.get("path", "")
            else:
                fp = str(cf)
            if fp and fp not in likely_files:
                likely_files.insert(0, fp)
    likely_files = likely_files[:10]

    # Suggested searches and read-slices
    suggested_searches: list[str] = []
    for kw in keywords[:3]:
        suggested_searches.append(f'python -m aura_agent_arena_cli search --query "{kw}" --kind symbol')

    suggested_read_slices: list[str] = []
    for fp in likely_files[:3]:
        for sym in likely_symbols[:3]:
            suggested_read_slices.append(f"python -m aura_agent_arena_cli read-slice --file {fp} --symbol {sym}")
    suggested_read_slices = suggested_read_slices[:5]

    # --- DREAM-lite reranking ---
    dream_ranked: list[dict[str, Any]] = []
    dream_warning = ""
    try:
        from aura_dream_retrieval import rerank_for_arena
        candidates = [{"candidate_id": fp, "candidate_type": "context", "source": "codemap",
                       "content": fp} for fp in likely_files[:5]]
        candidates.extend([{"candidate_id": sym, "candidate_type": "capability", "source": "codemap",
                            "content": sym} for sym in likely_symbols[:3]])
        dream_result = rerank_for_arena(objective, candidates, "code")
        dream_ranked = dream_result.get("ranked_candidates", [])
    except Exception as exc:
        dream_warning = f"DREAM-lite reranking failed: {exc}"

    # --- QDKT fast-path ---
    qdkt_fast_path: dict[str, Any] | None = None
    try:
        from aura_qdkt import get_qdkt
        qdkt = get_qdkt()
        # QDKT may have crystallized patterns — check for fast path
        # We just record that QDKT is available; actual pattern lookup is domain-specific
        qdkt_fast_path = {"available": True, "note": "QDKT is available for pattern crystallization."}
    except Exception:
        qdkt_fast_path = None

    # --- Context Crush ---
    context_crush_summary: dict[str, Any] = {}
    try:
        from aura_context_crusher import apply_context_crush_to_prompt
        crush_result = apply_context_crush_to_prompt(objective, source_hint="intent_ingestion")
        context_crush_summary = {
            "original_tokens_est": getattr(crush_result, "original_tokens_est", 0),
            "compressed_tokens_est": getattr(crush_result, "compressed_tokens_est", 0),
            "savings_ratio": getattr(crush_result, "savings_ratio", 0),
        }
    except Exception:
        context_crush_summary = {"error": "Context Crusher not available"}

    # --- ST3GG decision ---
    st3gg_decision: dict[str, Any] = {}
    try:
        from aura_arena_st3gg_codec import should_st3gg_encode_arena_capsule
        capsule = {"objective": objective, "likely_files": likely_files}
        decision = should_st3gg_encode_arena_capsule(capsule)
        st3gg_decision = {
            "enabled": getattr(decision, "enabled", False),
            "reason": getattr(decision, "reason", ""),
            "raw_tokens_est": getattr(decision, "raw_tokens_est", 0),
            "compressed_tokens_est": getattr(decision, "compressed_tokens_est", 0),
        }
    except Exception:
        st3gg_decision = {"error": "ST3GG codec not available"}

    # --- JSpace state ---
    jspace_state: dict[str, Any] = {}
    try:
        from aura_jspace_codec import build_jspace_packet, active_concepts_from_packet
        frame = fst_result.get("routing_frame", {})
        decision = fst_result.get("route_decision", {})
        jpacket = build_jspace_packet(frame, {"route": decision.get("route", ""),
                                               "model": decision.get("model", ""),
                                               "context": "SUMMARY",
                                               "reason": decision.get("reason", "")})
        jstate = active_concepts_from_packet(jpacket)
        jspace_state = jstate.to_dict() if hasattr(jstate, "to_dict") else {}
    except Exception:
        jspace_state = {}

    # --- Checkpoint plan ---
    gates_section = sections.get("AURA_GATES", "")
    checkpoint_plan: list[dict[str, str]] = []
    for line in gates_section.splitlines():
        line = line.strip()
        if line.startswith("GATE_"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                checkpoint_plan.append({
                    "gate": parts[0].strip(),
                    "requirement": parts[1].strip(),
                })

    # --- Handoff mode ---
    handoff_section = sections.get("AURA_HANDOFF", "")
    handoff_mode = "hermes"
    for line in handoff_section.splitlines():
        if "agent:" in line.lower():
            handoff_mode = line.split(":", 1)[1].strip()
            break

    # --- Token budget ---
    budget_section = sections.get("AURA_TOKEN_BUDGET", "")
    token_budget: dict[str, Any] = {}
    for line in budget_section.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            try:
                token_budget[key] = int(value)
            except ValueError:
                token_budget[key] = value

    # --- Concept workspace summary ---
    concept_summary: dict[str, Any] = {}
    if isinstance(concept_result, dict) and concept_result.get("ok"):
        concept_summary = {
            "files": concept_result.get("files", [])[:5],
            "symbols": concept_result.get("symbols", [])[:5],
            "tests": concept_result.get("tests", [])[:3],
            "docs": concept_result.get("docs", [])[:3],
        }

    # --- Grounding summary ---
    grounding_summary: dict[str, Any] = {}
    if grounding_result:
        grounding_summary = {
            "grounding_ok": grounding_result.get("grounding_ok", False),
            "route": grounding_result.get("route", ""),
            "target_file": grounding_result.get("target_file", ""),
            "target_symbol": grounding_result.get("target_symbol", ""),
            "exact_hits": grounding_result.get("exact_hits", []),
            "source_spans": grounding_result.get("source_spans", [])[:3],
            "tests": grounding_result.get("tests", []),
            "hashes": grounding_result.get("hashes", {}),
        }

    return {
        "ok": True,
        "version": INGESTION_VERSION,
        "objective": objective,
        "raw_objective_tokens_est": raw_objective_tokens_est,
        "compressed_objective": polysynthetic_packet,
        "compressed_tokens_est": compressed_tokens_est,
        "polysynthetic_packet": polysynthetic_packet,
        "lexc_symbols": lexc_result.get("symbols", []),
        "lexc_valid": lexc_result.get("valid", False),
        "lexc_route_packet": lexc_result.get("route_packet", {}),
        "routing_frame": fst_result.get("routing_frame", {}),
        "route_decision": fst_result.get("route_decision", {}),
        "recommended_affordances": affordance_result.get("recommended_affordances", []),
        "concept_workspace_summary": concept_summary,
        "grounding": grounding_summary,
        "grounding_warning": grounding_warning,
        "likely_files": likely_files,
        "likely_symbols": likely_symbols,
        "suggested_searches": suggested_searches,
        "suggested_read_slices": suggested_read_slices,
        "dream_ranked_candidates": dream_ranked[:5],
        "dream_warning": dream_warning,
        "qdkt_fast_path": qdkt_fast_path,
        "context_crush_summary": context_crush_summary,
        "st3gg_decision": st3gg_decision,
        "jspace_state": jspace_state,
        "checkpoint_plan": checkpoint_plan,
        "handoff_mode": handoff_mode,
        "token_budget": token_budget,
        "frontmatter": frontmatter,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# 3. compress_intent_for_agent
# ---------------------------------------------------------------------------


def compress_intent_for_agent(intent_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    """Apply Context Crusher to an intent packet for agent handoff."""
    objective = intent_packet.get("objective", "")
    likely_files = intent_packet.get("likely_files", [])

    # Build a context string from the packet
    context_parts = [f"Objective: {objective}"]
    if intent_packet.get("polysynthetic_packet"):
        context_parts.append(f"Packet: {intent_packet['polysynthetic_packet']}")
    if intent_packet.get("routing_frame"):
        context_parts.append(f"Route: {json.dumps(intent_packet['routing_frame'])}")
    if likely_files:
        context_parts.append(f"Files: {', '.join(likely_files[:5])}")
    if intent_packet.get("likely_symbols"):
        context_parts.append(f"Symbols: {', '.join(intent_packet['likely_symbols'][:5])}")
    raw_context = "\n".join(context_parts)

    raw_tokens = _estimate_tokens(raw_context)

    compressed_payload = raw_context
    compressed_tokens = raw_tokens
    try:
        from aura_context_crusher import apply_context_crush_to_prompt
        result = apply_context_crush_to_prompt(raw_context, source_hint="intent_agent_handoff")
        compressed_payload = getattr(result, "compressed_payload", raw_context)
        compressed_tokens = getattr(result, "compressed_tokens_est", compressed_tokens)
    except Exception:
        pass

    return {
        "ok": True,
        "version": INGESTION_VERSION,
        "raw_context": raw_context,
        "raw_tokens_est": raw_tokens,
        "compressed_payload": compressed_payload,
        "compressed_tokens_est": compressed_tokens,
        "estimated_tokens_saved": max(0, raw_tokens - compressed_tokens),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# 4. route_intent_to_lexc
# ---------------------------------------------------------------------------


def route_intent_to_lexc(parsed_doc: dict | str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Validate the LEXC route from an intent document."""
    root = Path(repo_root).resolve()

    if isinstance(parsed_doc, str):
        parsed_doc = parse_intent_document(parsed_doc, repo_root=root)

    lexc_section = parsed_doc.get("sections", {}).get("AURA_LEXC_ROUTE", "")
    if not lexc_section:
        return {
            "ok": True,
            "valid": False,
            "symbols": [],
            "route_packet": {},
            "warning": "No AURA_LEXC_ROUTE section found.",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # Parse LEXC route symbols from the section
    symbols: list[str] = []
    slot_values: dict[str, str] = {}
    for line in lexc_section.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key and value:
                slot_values[key] = value
                # Extract the first +symbol or _symbol
                for part in value.split("+"):
                    part = part.strip()
                    if part and part not in symbols:
                        symbols.append(part)
                for part in value.split("_"):
                    part = part.strip()
                    if part and part not in symbols:
                        symbols.append(part)

    # Validate against aura.lexc if available
    lexc_valid = False
    route_packet: dict[str, Any] = {}
    try:
        from aura_lexc import AuraLexc, SLOT_ORDER
        lexc_path = root / "aura.lexc"
        if lexc_path.exists():
            lexc = AuraLexc.from_path(lexc_path, strict=False)
            # Use SLOT_ORDER to derive canonical ordered slot names
            expected_slots = list(SLOT_ORDER)
            # Check if we have all required slots
            if set(expected_slots).issubset(set(slot_values.keys())):
                # Build ordered symbols list
                ordered_symbols = [slot_values[slot] for slot in expected_slots]
                # Always call validate_symbols
                route = lexc.validate_symbols(ordered_symbols)
                if route and route.is_complete:
                    lexc_valid = True
                    route_packet = route.packet()
    except Exception:
        # Fallback: cannot validate without proper FST
        try:
            from aura_lexc import SLOT_ORDER
            expected_slots = list(SLOT_ORDER)
        except Exception:
            expected_slots = ["DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"]
        lexc_valid = False
        route_packet = {}

    return {
        "ok": True,
        "valid": lexc_valid,
        "symbols": symbols,
        "slot_values": slot_values,
        "route_packet": route_packet,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# 5. route_intent_to_fst
# ---------------------------------------------------------------------------


def route_intent_to_fst(
    parsed_doc: dict | str,
    repo_root: str | Path = ".",
    route_hints: dict | None = None,
    grounding_result: dict | None = None,
) -> dict[str, Any]:
    """Build a RoutingFrame and RouteDecision for an intent document."""
    root = Path(repo_root).resolve()

    if isinstance(parsed_doc, str):
        parsed_doc = parse_intent_document(parsed_doc, repo_root=root)

    objective = parsed_doc.get("objective", "")
    if not objective:
        return {
            "ok": False,
            "error": "No objective found.",
            "routing_frame": {},
            "route_decision": {},
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    frame = _build_routing_frame(objective, route_hints=route_hints, grounding_result=grounding_result)
    decision = _route_decision(frame)

    return {
        "ok": True,
        "routing_frame": frame,
        "route_decision": decision,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# 6. route_intent_to_affordances
# ---------------------------------------------------------------------------


def route_intent_to_affordances(objective: str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Find recommended affordances for an objective."""
    root = Path(repo_root).resolve()
    try:
        from aura_affordance_directory import find_affordances
        result = find_affordances(objective, repo_root=root, top_k=7)
        return {
            "ok": True,
            "recommended_affordances": result.get("recommended_affordances", []),
            "prompt_cards": result.get("prompt_cards", []),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Affordance lookup failed: {exc}",
            "recommended_affordances": [],
            "prompt_cards": [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


# ---------------------------------------------------------------------------
# 7. route_intent_to_concept_workspace
# ---------------------------------------------------------------------------


def route_intent_to_concept_workspace(objective: str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Build a concept workspace for an objective."""
    root = Path(repo_root).resolve()
    try:
        from aura_human_agent_concepts import build_concept_workspace
        # Extract a concept keyword from the objective
        keywords = _extract_keywords(objective)
        concept = keywords[0] if keywords else "coding_arena"
        result = build_concept_workspace(concept, repo_root=root)
        return {
            "ok": True,
            "concept": concept,
            "files": result.get("files", []),
            "symbols": result.get("symbols", []),
            "tests": result.get("tests", []),
            "docs": result.get("docs", []),
            "neighbors": result.get("neighbors", []),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Concept workspace failed: {exc}",
            "files": [],
            "symbols": [],
            "tests": [],
            "docs": [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


# ---------------------------------------------------------------------------
# 8. intent_to_agent_handoff
# ---------------------------------------------------------------------------


def intent_to_agent_handoff(
    intent_packet: dict,
    agent: str = "hermes",
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Produce a compact agent handoff packet from an IntentPacket."""
    root = Path(repo_root).resolve()

    # Compress for agent
    compressed = compress_intent_for_agent(intent_packet, repo_root=root)

    # Build handoff packet
    handoff: dict[str, Any] = {
        "ok": True,
        "version": INGESTION_VERSION,
        "agent": agent,
        "objective": intent_packet.get("objective", ""),
        "polysynthetic_packet": intent_packet.get("polysynthetic_packet", ""),
        "compressed_context": compressed.get("compressed_payload", ""),
        "compressed_tokens_est": compressed.get("compressed_tokens_est", 0),
        "routing_frame": intent_packet.get("routing_frame", {}),
        "route_decision": intent_packet.get("route_decision", {}),
        "likely_files": intent_packet.get("likely_files", [])[:5],
        "likely_symbols": intent_packet.get("likely_symbols", [])[:5],
        "grounding": intent_packet.get("grounding", {}),
        "recommended_affordances": intent_packet.get("recommended_affordances", [])[:3],
        "st3gg_decision": intent_packet.get("st3gg_decision", {}),
        "jspace_state": intent_packet.get("jspace_state", {}),
        "checkpoint_plan": intent_packet.get("checkpoint_plan", []),
        "lexc_valid": intent_packet.get("lexc_valid", False),
        "token_budget": intent_packet.get("token_budget", {}),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "note": (
            "This is a compact handoff packet. Agents receive compressed context, "
            "routing decisions, grounding, and advisory state only. "
            "Patch authority remains exact source spans and hashes."
        ),
    }

    # Add Hermes-specific contract if agent is hermes
    if agent == "hermes":
        try:
            from aura_hermes_arena_mode import generate_hermes_contract
            contract = generate_hermes_contract(
                objective=handoff["objective"],
                mode="pr",
                repo_root=root,
            )
            handoff["hermes_contract"] = contract.get("contract", "")[:500]
        except Exception:
            pass

    return handoff


# ---------------------------------------------------------------------------
# 9. write_intent_capsule
# ---------------------------------------------------------------------------


def write_intent_capsule(intent_packet: dict, path: str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Write an intent packet to a JSON file."""
    root = Path(repo_root).resolve()
    output_path = root / path

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(intent_packet, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        return {
            "ok": False,
            "error": f"Cannot write intent capsule: {exc}",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    return {
        "ok": True,
        "path": str(path).replace("\\", "/"),
        "bytes_written": output_path.stat().st_size if output_path.exists() else 0,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
