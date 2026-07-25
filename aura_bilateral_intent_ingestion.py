"""Proposal-only bilateral companion for Aura's canonical intent ingestion.

The canonical owner remains :mod:`aura_intent_ingestion`. This companion adds
explicit polarity evidence and negation-preserving handoff without monkeypatching
or replacing the canonical module.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import aura_intent_ingestion as _canonical
from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest
from aura_intent_refinement import (
    detect_requirement_contradictions,
    extract_negative_requirements,
)

VERSION = "AURA_BILATERAL_INTENT_INGESTION_V1"
CANONICAL_INGESTION_OWNER = "aura_intent_ingestion"
BILATERAL_INTENT_OWNER = False
MEMORY_OWNER = TRUTH_OWNER = POLICY_OWNER = ROUTING_OWNER = False
VERIFICATION_OWNER = PATCH_AUTHORITY_GRANTED = PRODUCTION_MUTATION = False


def _section_ranges(raw_text: str) -> tuple[dict[str, str], tuple[tuple[int, int, str], ...]]:
    headers: list[tuple[int, int, str]] = []
    cursor = 0
    for line in raw_text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            name = stripped[1:-1]
            if name.startswith("AURA_") and name.replace("_", "").isalnum():
                headers.append((cursor, cursor + len(line), name))
        cursor += len(line)
    sections: dict[str, str] = {}
    ranges: list[tuple[int, int, str]] = []
    for index, (header_start, body_start, name) in enumerate(headers):
        del header_start
        body_end = headers[index + 1][0] if index + 1 < len(headers) else len(raw_text)
        content = raw_text[body_start:body_end].strip()
        sections[name] = content
        ranges.append((body_start, body_end, name))
    return sections, tuple(ranges)


def _line_statements(text: str) -> list[str]:
    statements: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        while line and line[0] in "-*+":
            line = line[1:].lstrip()
        digit_end = 0
        while digit_end < len(line) and line[digit_end].isdigit():
            digit_end += 1
        if digit_end and digit_end < len(line) and line[digit_end] in ".)":
            line = line[digit_end + 1:].lstrip()
        if line:
            statements.append(line)
    return statements


def _source_section(offset: int, ranges: tuple[tuple[int, int, str], ...]) -> str:
    for start, end, name in ranges:
        if start <= offset < end:
            return name
    return "AURA_INTENT"


def _bilateral_evidence(raw_text: str, objective: str) -> dict[str, Any]:
    sections, ranges = _section_ranges(raw_text)
    positives = _line_statements(sections.get("AURA_REQUIRED_BEHAVIOR", ""))
    if not positives and objective.strip():
        positives = [objective.strip()]
    negatives = []
    for requirement in extract_negative_requirements(raw_text):
        item = requirement.to_dict()
        item["source_section"] = _source_section(item["source_start"], ranges)
        item["polarity"] = "NEGATIVE"
        negatives.append(item)
    negative_statements = [item["statement"] for item in negatives]
    positive_trace = [
        {
            "polarity": "POSITIVE",
            "statement": statement,
            "source_section": (
                "AURA_REQUIRED_BEHAVIOR"
                if sections.get("AURA_REQUIRED_BEHAVIOR")
                else "AURA_INTENT"
            ),
        }
        for statement in positives
    ]
    polarity_trace = [*positive_trace, *negatives]
    contradictions = list(detect_requirement_contradictions(positives, negative_statements))
    ambiguous_negative_refs = [
        item["requirement_id"] for item in negatives if item["ambiguous"]
    ]
    return {
        "bilateral_sections": sections,
        "positive_requirements": positives,
        "negative_requirements": negatives,
        "negative_statements": negative_statements,
        "polarity_trace": polarity_trace,
        "requirement_contradictions": contradictions,
        "ambiguous_negative_refs": ambiguous_negative_refs,
        "requires_clarification": bool(contradictions or ambiguous_negative_refs),
        "positive_requirements_digest": stable_digest(positives),
        "negative_requirements_digest": stable_digest(negatives),
        "polarity_trace_digest": stable_digest(polarity_trace),
    }


def companion_capabilities() -> dict[str, Any]:
    return {
        "version": VERSION,
        "canonical_ingestion_owner": CANONICAL_INGESTION_OWNER,
        "bilateral_intent_owner": BILATERAL_INTENT_OWNER,
        "memory_owner": MEMORY_OWNER,
        "truth_owner": TRUTH_OWNER,
        "policy_owner": POLICY_OWNER,
        "routing_owner": ROUTING_OWNER,
        "verification_owner": VERIFICATION_OWNER,
        "patch_authority": PATCH_AUTHORITY_GRANTED,
        "production_mutation": PRODUCTION_MUTATION,
        "exact_patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def parse_bilateral_intent_document(
    path_or_text: str,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    canonical = _canonical.parse_intent_document(path_or_text, repo_root=repo_root)
    result = dict(canonical)
    result["canonical_parse"] = canonical
    result.update(
        _bilateral_evidence(
            str(canonical.get("raw_text", "")),
            str(canonical.get("objective", "")),
        )
    )
    result["version"] = VERSION
    result["canonical_ingestion_owner"] = CANONICAL_INGESTION_OWNER
    result["patch_authority"] = PATCH_AUTHORITY
    result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
    return result


def _refs(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "positive_requirements_digest": packet.get("positive_requirements_digest", ""),
        "negative_requirements_digest": packet.get("negative_requirements_digest", ""),
        "polarity_trace_digest": packet.get("polarity_trace_digest", ""),
        "requires_clarification": bool(packet.get("requires_clarification", False)),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def route_bilateral_intent_to_fst(
    parsed_doc: dict | str,
    repo_root: str | Path = ".",
    route_hints: dict | None = None,
    grounding_result: dict | None = None,
) -> dict[str, Any]:
    packet = (
        parse_bilateral_intent_document(parsed_doc, repo_root=repo_root)
        if isinstance(parsed_doc, str)
        else parsed_doc
    )
    canonical = packet.get("canonical_parse", packet)
    result = _canonical.route_intent_to_fst(
        canonical,
        repo_root=repo_root,
        route_hints=route_hints,
        grounding_result=grounding_result,
    )
    frame = dict(result.get("routing_frame", {}))
    frame["bilateral_intent_refs"] = _refs(packet)
    decision = dict(result.get("route_decision", {}))
    decision["bilateral_intent_status"] = (
        "CLARIFICATION_REQUIRED"
        if packet.get("requires_clarification")
        else "POLARITY_PRESERVED"
    )
    result["routing_frame"] = frame
    result["route_decision"] = decision
    result["negative_requirements_digest"] = packet.get(
        "negative_requirements_digest", ""
    )
    return result


def compile_bilateral_intent_packet(
    parsed_doc: dict | str,
    repo_root: str | Path = ".",
    skip_grounding: bool = False,
) -> dict[str, Any]:
    packet = (
        parse_bilateral_intent_document(parsed_doc, repo_root=repo_root)
        if isinstance(parsed_doc, str)
        else parsed_doc
    )
    canonical = packet.get("canonical_parse", packet)
    result = _canonical.compile_intent_packet(
        canonical,
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
        result[key] = packet.get(key)
    route = route_bilateral_intent_to_fst(
        packet,
        repo_root=repo_root,
        grounding_result=result.get("grounding", {}),
    )
    result["routing_frame"] = route.get("routing_frame", result.get("routing_frame", {}))
    result["route_decision"] = route.get("route_decision", result.get("route_decision", {}))
    result["bilateral_intent_refs"] = _refs(packet)
    result["version"] = VERSION
    return result


def _negative_block(intent_packet: dict[str, Any]) -> str:
    statements = [
        str(item.get("statement", "")).strip()
        for item in intent_packet.get("negative_requirements", [])
        if isinstance(item, dict) and str(item.get("statement", "")).strip()
    ]
    if not statements:
        return ""
    return "NEGATIVE REQUIREMENTS — FULL TEXT, NOT COMPRESSED:\n" + "\n".join(
        f"- {statement}" for statement in statements
    )


def compress_bilateral_intent_for_agent(
    intent_packet: dict,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    result = _canonical.compress_intent_for_agent(intent_packet, repo_root=repo_root)
    negative_block = _negative_block(intent_packet)
    if negative_block:
        result["raw_context"] = "\n".join(
            part for part in (result.get("raw_context", ""), negative_block) if part
        )
        result["compressed_payload"] = "\n".join(
            part for part in (result.get("compressed_payload", ""), negative_block) if part
        )
    result["negative_requirements"] = list(intent_packet.get("negative_requirements", []))
    result["negative_requirements_digest"] = intent_packet.get(
        "negative_requirements_digest", stable_digest([])
    )
    result["polarity_trace_digest"] = intent_packet.get(
        "polarity_trace_digest", stable_digest([])
    )
    result["negation_preserved"] = True
    result["version"] = VERSION
    return result


def bilateral_intent_to_agent_handoff(
    intent_packet: dict,
    agent: str = "hermes",
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    handoff = _canonical.intent_to_agent_handoff(
        intent_packet,
        agent=agent,
        repo_root=repo_root,
    )
    compressed = compress_bilateral_intent_for_agent(intent_packet, repo_root=repo_root)
    handoff["compressed_context"] = compressed.get("compressed_payload", "")
    handoff["negative_requirements"] = list(intent_packet.get("negative_requirements", []))
    handoff["negative_requirements_digest"] = intent_packet.get(
        "negative_requirements_digest", ""
    )
    handoff["polarity_trace_digest"] = intent_packet.get("polarity_trace_digest", "")
    handoff["requires_clarification"] = bool(
        intent_packet.get("requires_clarification", False)
    )
    handoff["negation_preserved"] = True
    handoff["version"] = VERSION
    return handoff
