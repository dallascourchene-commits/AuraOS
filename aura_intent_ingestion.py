"""Bilateral intent facade over Aura's canonical ingestion implementation.

The exact pre-refactor implementation remains in ``aura_intent_ingestion_core``
as a private compatibility core. This module remains the sole public ingestion
owner and adds deterministic polarity extraction, contradiction evidence, and
negation-preserving compression/handoff. It grants no new authority.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import aura_intent_ingestion_core as _core
from aura_event_contracts import stable_digest
from aura_intent_refinement import (
    NegativeRequirement,
    detect_requirement_contradictions,
    extract_negative_requirements,
)

# Preserve every prior module attribute, including private helpers used by
# repository tests and internal callers. Bilateral overrides are defined below.
for _export_name in dir(_core):
    if not _export_name.startswith("__"):
        globals()[_export_name] = getattr(_core, _export_name)

INGESTION_VERSION = "AURA_INTENT_INGESTION_V2_BILATERAL"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
BILATERAL_INTENT_OWNER = True
MEMORY_OWNER = TRUTH_OWNER = POLICY_OWNER = ROUTING_OWNER = False
VERIFICATION_OWNER = PRODUCTION_MUTATION = False

_BILATERAL_SECTIONS = (
    "AURA_PURPOSE",
    "AURA_MEANING",
    "AURA_REQUIRED_BEHAVIOR",
    "AURA_PROHIBITED_BEHAVIOR",
    "AURA_DEFINITIONS",
    "AURA_DOES_NOT_MEAN",
    "AURA_GUARDRAILS",
    "AURA_AUTHORITY",
    "AURA_FAILURE_BEHAVIOR",
    "AURA_REQUIRED_EVIDENCE",
    "AURA_HUMAN_CONFIRMATION",
)
_NEGATIVE_SOURCE_SECTIONS = (
    "AURA_INTENT",
    "AURA_PROHIBITED_BEHAVIOR",
    "AURA_DOES_NOT_MEAN",
    "AURA_GUARDRAILS",
    "AURA_FAILURE_BEHAVIOR",
    "AURA_AUTHORITY",
)
_NEGATION_KEYWORDS = frozenset(
    {"not", "never", "no", "without", "avoid", "exclude", "except", "only"}
)
_AURA_SECTIONS = list(dict.fromkeys([*_core._AURA_SECTIONS, *_BILATERAL_SECTIONS]))
_STOP_WORDS = frozenset(word for word in _core._STOP_WORDS if word not in _NEGATION_KEYWORDS)
_core._AURA_SECTIONS = _AURA_SECTIONS
_core._STOP_WORDS = _STOP_WORDS

_ORIGINAL_PARSE = _core.parse_intent_document
_ORIGINAL_COMPILE = _core.compile_intent_packet
_ORIGINAL_COMPRESS = _core.compress_intent_for_agent
_ORIGINAL_ROUTE_FST = _core.route_intent_to_fst
_ORIGINAL_HANDOFF = _core.intent_to_agent_handoff


def _extract_keywords(text: str) -> list[str]:
    """Preserve operational negation tokens during keyword compression."""
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    return [word for word in words if word not in _STOP_WORDS and len(word) > 1]


_core._extract_keywords = _extract_keywords


def _section_statements(text: str) -> list[str]:
    statements: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", raw_line).strip()
        if line:
            statements.append(line)
    return statements


def _locate_section(raw_text: str, content: str, cursor: int) -> tuple[int, int]:
    if not content:
        return -1, cursor
    start = raw_text.find(content, cursor)
    if start < 0:
        start = raw_text.find(content)
    if start < 0:
        return -1, cursor
    return start, start + len(content)


def _globalize_requirement(
    requirement: NegativeRequirement,
    *,
    source_section: str,
    section_offset: int,
) -> dict[str, Any]:
    global_start = requirement.source_start + max(section_offset, 0)
    global_end = requirement.source_end + max(section_offset, 0)
    rebound = NegativeRequirement.create(
        statement=requirement.statement,
        classification=requirement.classification,
        source_span=requirement.source_span,
        source_start=global_start,
        source_end=global_end,
        operator=requirement.operator,
        target=requirement.target,
        scope=requirement.scope,
        ambiguous=requirement.ambiguous,
    ).to_dict()
    rebound["source_section"] = source_section
    rebound["polarity"] = "NEGATIVE"
    return rebound


def _extract_bilateral_evidence(parsed_doc: dict[str, Any]) -> dict[str, Any]:
    raw_text = str(parsed_doc.get("raw_text", ""))
    sections = parsed_doc.get("sections", {})
    if not isinstance(sections, dict):
        sections = {}

    positive_requirements = _section_statements(
        str(sections.get("AURA_REQUIRED_BEHAVIOR", ""))
    )
    if not positive_requirements:
        objective = str(parsed_doc.get("objective", "")).strip()
        if objective:
            positive_requirements = [objective]

    negative_requirements: list[dict[str, Any]] = []
    cursor = 0
    seen: set[tuple[int, int, str]] = set()
    source_sections: Iterable[str]
    if sections:
        source_sections = _NEGATIVE_SOURCE_SECTIONS
    else:
        source_sections = ("AURA_INTENT",)

    for section_name in source_sections:
        content = str(sections.get(section_name, ""))
        if not content and section_name == "AURA_INTENT" and not sections:
            content = raw_text
        if not content:
            continue
        section_start, cursor = _locate_section(raw_text, content, cursor)
        for requirement in extract_negative_requirements(content):
            item = _globalize_requirement(
                requirement,
                source_section=section_name,
                section_offset=section_start,
            )
            identity = (item["source_start"], item["source_end"], item["statement"])
            if identity not in seen:
                seen.add(identity)
                negative_requirements.append(item)

    negative_statements = [item["statement"] for item in negative_requirements]
    contradictions = list(
        detect_requirement_contradictions(positive_requirements, negative_statements)
    )
    positive_trace = [
        {
            "polarity": "POSITIVE",
            "statement": statement,
            "source_section": "AURA_REQUIRED_BEHAVIOR"
            if sections.get("AURA_REQUIRED_BEHAVIOR")
            else "AURA_INTENT",
        }
        for statement in positive_requirements
    ]
    polarity_trace = [*positive_trace, *negative_requirements]
    ambiguous_negative_refs = [
        item["requirement_id"] for item in negative_requirements if item["ambiguous"]
    ]
    requires_clarification = bool(contradictions or ambiguous_negative_refs)
    return {
        "positive_requirements": positive_requirements,
        "negative_requirements": negative_requirements,
        "negative_statements": negative_statements,
        "polarity_trace": polarity_trace,
        "requirement_contradictions": contradictions,
        "ambiguous_negative_refs": ambiguous_negative_refs,
        "requires_clarification": requires_clarification,
        "positive_requirements_digest": stable_digest(positive_requirements),
        "negative_requirements_digest": stable_digest(negative_requirements),
        "polarity_trace_digest": stable_digest(polarity_trace),
    }


def _augment_parsed_doc(parsed_doc: dict[str, Any]) -> dict[str, Any]:
    result = dict(parsed_doc)
    result["version"] = INGESTION_VERSION
    result.update(_extract_bilateral_evidence(result))
    result["patch_authority"] = PATCH_AUTHORITY
    result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
    result["memory_owner"] = MEMORY_OWNER
    result["truth_owner"] = TRUTH_OWNER
    result["policy_owner"] = POLICY_OWNER
    result["routing_owner"] = ROUTING_OWNER
    result["verification_owner"] = VERIFICATION_OWNER
    result["production_mutation"] = PRODUCTION_MUTATION
    return result


def parse_intent_document(path_or_text: str, repo_root: str | Path = ".") -> dict[str, Any]:
    """Parse structured or ordinary requests into exact bilateral evidence."""
    return _augment_parsed_doc(_ORIGINAL_PARSE(path_or_text, repo_root=repo_root))


def _bilateral_refs(parsed_doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "positive_requirements_digest": parsed_doc.get("positive_requirements_digest", ""),
        "negative_requirements_digest": parsed_doc.get("negative_requirements_digest", ""),
        "polarity_trace_digest": parsed_doc.get("polarity_trace_digest", ""),
        "requires_clarification": bool(parsed_doc.get("requires_clarification", False)),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def route_intent_to_fst(
    parsed_doc: dict | str,
    repo_root: str | Path = ".",
    route_hints: dict | None = None,
    grounding_result: dict | None = None,
) -> dict[str, Any]:
    """Carry immutable polarity references through routing without granting authority."""
    if isinstance(parsed_doc, str):
        parsed_doc = parse_intent_document(parsed_doc, repo_root=repo_root)
    elif "negative_requirements_digest" not in parsed_doc:
        parsed_doc = _augment_parsed_doc(parsed_doc)
    result = _ORIGINAL_ROUTE_FST(
        parsed_doc,
        repo_root=repo_root,
        route_hints=route_hints,
        grounding_result=grounding_result,
    )
    frame = dict(result.get("routing_frame", {}))
    frame["bilateral_intent_refs"] = _bilateral_refs(parsed_doc)
    decision = dict(result.get("route_decision", {}))
    decision["bilateral_intent_status"] = (
        "CLARIFICATION_REQUIRED"
        if parsed_doc.get("requires_clarification")
        else "POLARITY_PRESERVED"
    )
    result["routing_frame"] = frame
    result["route_decision"] = decision
    result["negative_requirements_digest"] = parsed_doc.get(
        "negative_requirements_digest", ""
    )
    return result


_core.route_intent_to_fst = route_intent_to_fst


def compile_intent_packet(
    parsed_doc: dict | str,
    repo_root: str | Path = ".",
    skip_grounding: bool = False,
) -> dict[str, Any]:
    """Compile the legacy packet plus full bilateral evidence and digests."""
    if isinstance(parsed_doc, str):
        parsed_doc = parse_intent_document(parsed_doc, repo_root=repo_root)
    elif "negative_requirements_digest" not in parsed_doc:
        parsed_doc = _augment_parsed_doc(parsed_doc)
    result = _ORIGINAL_COMPILE(
        parsed_doc,
        repo_root=repo_root,
        skip_grounding=skip_grounding,
    )
    if not result.get("ok"):
        return result
    for key in (
        "positive_requirements",
        "negative_requirements",
        "negative_statements",
        "polarity_trace",
        "requirement_contradictions",
        "ambiguous_negative_refs",
        "requires_clarification",
        "positive_requirements_digest",
        "negative_requirements_digest",
        "polarity_trace_digest",
    ):
        result[key] = parsed_doc.get(key, [] if key.endswith("s") else "")
    result["bilateral_intent_refs"] = _bilateral_refs(parsed_doc)
    result["version"] = INGESTION_VERSION
    result["patch_authority"] = PATCH_AUTHORITY
    result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
    return result


def _negative_block(intent_packet: dict[str, Any]) -> str:
    statements = [
        str(item.get("statement", "")).strip()
        for item in intent_packet.get("negative_requirements", [])
        if isinstance(item, dict) and str(item.get("statement", "")).strip()
    ]
    if not statements:
        statements = [
            str(statement).strip()
            for statement in intent_packet.get("negative_statements", [])
            if str(statement).strip()
        ]
    if not statements:
        return ""
    return "NEGATIVE REQUIREMENTS — FULL TEXT, NOT COMPRESSED:\n" + "\n".join(
        f"- {statement}" for statement in statements
    )


def compress_intent_for_agent(
    intent_packet: dict,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Compress context while retaining canonical negative statements verbatim."""
    result = _ORIGINAL_COMPRESS(intent_packet, repo_root=repo_root)
    negative_block = _negative_block(intent_packet)
    if negative_block:
        result["raw_context"] = "\n".join(
            part for part in (result.get("raw_context", ""), negative_block) if part
        )
        result["compressed_payload"] = "\n".join(
            part for part in (result.get("compressed_payload", ""), negative_block) if part
        )
        result["raw_tokens_est"] = _core._estimate_tokens(result["raw_context"])
        result["compressed_tokens_est"] = _core._estimate_tokens(
            result["compressed_payload"]
        )
        result["estimated_tokens_saved"] = max(
            0, result["raw_tokens_est"] - result["compressed_tokens_est"]
        )
    result["negative_requirements"] = list(
        intent_packet.get("negative_requirements", [])
    )
    result["negative_requirements_digest"] = intent_packet.get(
        "negative_requirements_digest", stable_digest([])
    )
    result["polarity_trace_digest"] = intent_packet.get(
        "polarity_trace_digest", stable_digest([])
    )
    result["negation_preserved"] = True
    result["version"] = INGESTION_VERSION
    return result


def intent_to_agent_handoff(
    intent_packet: dict,
    agent: str = "hermes",
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Add full negative evidence and immutable polarity references to handoff."""
    handoff = _ORIGINAL_HANDOFF(intent_packet, agent=agent, repo_root=repo_root)
    compressed = compress_intent_for_agent(intent_packet, repo_root=repo_root)
    handoff["compressed_context"] = compressed.get("compressed_payload", "")
    handoff["compressed_tokens_est"] = compressed.get("compressed_tokens_est", 0)
    handoff["negative_requirements"] = list(
        intent_packet.get("negative_requirements", [])
    )
    handoff["negative_requirements_digest"] = intent_packet.get(
        "negative_requirements_digest", ""
    )
    handoff["polarity_trace_digest"] = intent_packet.get("polarity_trace_digest", "")
    handoff["requires_clarification"] = bool(
        intent_packet.get("requires_clarification", False)
    )
    handoff["negation_preserved"] = True
    handoff["version"] = INGESTION_VERSION
    return handoff


# Keep callers that imported the compatibility core directly behaviorally aligned.
_core.parse_intent_document = parse_intent_document
_core.compile_intent_packet = compile_intent_packet
_core.compress_intent_for_agent = compress_intent_for_agent
_core.intent_to_agent_handoff = intent_to_agent_handoff
