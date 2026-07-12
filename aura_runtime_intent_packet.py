"""Deterministic observable intent-packet construction for Phase C2 routing."""
from __future__ import annotations

import re
from typing import Any, Mapping

from aura_polysynthetic_intent import PolysyntheticIntentPacket

RUNTIME_INTENT_PACKET_VERSION = "AURA_RUNTIME_INTENT_PACKET_V1"


def infer_runtime_intent_packet(
    *, input_text: str, current_state: str,
    context: Mapping[str, Any] | None = None,
    policy: Mapping[str, Any] | None = None,
) -> PolysyntheticIntentPacket:
    context = dict(context or {})
    policy = dict(policy or {})
    normalized = " ".join(re.findall(r"[a-z0-9_]+", str(input_text).casefold()))
    tokens = set(normalized.split())
    return PolysyntheticIntentPacket.from_slots(
        {
            "DIR": str(context.get("routing_direction") or "OUT").upper(),
            "ASP": str(context.get("routing_aspect") or _aspect(current_state)).upper(),
            "CLASS": _class(tokens),
            "SUBJ": str(
                context.get("exact_target") or context.get("target_symbol")
                or context.get("target_file") or "REPOSITORY"
            ).upper(),
            "VOICE": str(context.get("request_voice") or "HUMAN_AGENT").upper(),
            "STEM": _stem(tokens, normalized),
        },
        adjuncts={
            "risk": str(policy.get("risk_class") or "low"),
            "grounding": str(policy.get("grounding_class") or "exact_source_hashes"),
            "context_class": str(policy.get("context_class") or "bounded_route_capsule"),
            "model_class": str(
                policy.get("model_class") or context.get("requested_model") or "no_model"
            ),
            "resource_budget": str(policy.get("resource_budget") or "capsule_pinned"),
        },
        objective=str(context.get("objective") or input_text or ""),
    )


def _class(tokens: set[str]) -> str:
    for vocabulary, label in (
        ({"localize", "find", "locate", "search"}, "LOCALIZE"),
        ({"test", "tests", "verify", "verification"}, "VERIFY"),
        ({"patch", "edit", "change", "refactor"}, "PATCH"),
        ({"review", "approve", "reject"}, "REVIEW"),
        ({"scope", "plan"}, "SCOPE"),
    ):
        if tokens & vocabulary:
            return label
    return "ROUTE"


def _stem(tokens: set[str], normalized: str) -> str:
    for value in (
        "localize", "find", "locate", "search", "verify", "test", "patch",
        "refactor", "review", "scope", "plan", "inspect",
    ):
        if value in tokens:
            return value.upper()
    return (normalized.replace(" ", "_")[:80] or "INSPECT").upper()


def _aspect(state: str) -> str:
    upper = str(state or "").upper()
    if "TEST" in upper or "VERIFIED" in upper:
        return "VERIFY"
    if "REVIEW" in upper or "PR_READY" in upper:
        return "REVIEW"
    if upper in {"TASK_SCOPED", "CONTEXT_FILTERED", "CODE_LOCALIZED"}:
        return "GROUND"
    return "ROUTE"
