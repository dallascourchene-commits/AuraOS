"""Cost-first cognitive allocation policy for AuraOS.

This module chooses a *policy route* only. It does not call providers, spend money,
widen authority, or claim that ChatGPT subscription access is programmatically
available to the resident. Host/runtime owners provide current availability,
authorization, cost evidence and currentness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CognitionRequest:
    task_class: str
    consequence_class: str = "D0"
    gate_target: int = 10

    # Reuse / deterministic / local lanes are always considered before paid APIs.
    current_reuse_available: bool = False
    reuse_current: bool = True
    deterministic_sufficient: bool = False
    local_model_available: bool = False
    local_model_sufficient: bool = False

    # Interactive ChatGPT is a human-facing control-plane option, not an AuraOS API.
    interactive_chatgpt_available: bool = False
    top_level_reasoning_needed: bool = False

    # DeepSeek is the default paid remote swarm provider.
    deepseek_available: bool = True
    deepseek_authorized: bool = True
    deepseek_cost_upper_bound_known: bool = True

    # Expensive provider/model use is exceptional and owner-authorized.
    frontier_reasoning_earned: bool = False
    expensive_provider: str | None = None
    expensive_provider_authorized: bool = False
    expensive_cost_upper_bound_known: bool = False


AMORTIZATION_ARTIFACTS = (
    "SOURCE_CURRENTNESS_BOUND_RESULT_RECEIPT",
    "WORKCAPSULE_RESULT_DIGEST",
    "COORDINATE_MEMORY_PLACEMENT_OR_REOPEN_POINTER",
    "L0_SUCCESSOR_SUMMARY",
    "REUSABLE_CODE_TEST_EQUATION_OR_PROOF_WHERE_PRODUCED",
    "COUNTEREVIDENCE_INVALIDATORS_RESIDUALS",
    "PROVIDER_MODEL_ATTEMPT_COST_EVIDENCE_CLASS",
    "REBASE_TRIGGERS",
)


def choose_cognition_route(req: CognitionRequest) -> dict[str, Any]:
    """Choose the lowest-cost lawful route for one bounded consequence.

    Priority is current reuse -> AuraOS/no-model -> interactive ChatGPT control
    plane when available -> local model -> DeepSeek paid swarm -> explicitly
    authorized expensive frontier. No paid fallback is implicit.
    """
    if req.consequence_class != "D0":
        return {"route": "HUMAN_GATE", "reason": "D1_PLUS_REQUIRES_SEPARATE_AUTHORITY"}
    if req.gate_target > 10:
        return {"route": "BLOCK", "reason": "AUTONOMY_STOPS_AT_GATE10"}

    if req.current_reuse_available and req.reuse_current:
        return {"route": "REUSE_COORDINATE_MEMORY", "provider": None}

    if req.deterministic_sufficient:
        return {"route": "AURAOS_NO_MODEL", "provider": None}

    if req.interactive_chatgpt_available and req.top_level_reasoning_needed:
        return {
            "route": "CHATGPT_CONTROL_PLANE",
            "provider": None,
            "reason": "USE_EXISTING_INTERACTIVE_REASONING_BEFORE_PAID_API",
        }

    if req.local_model_available and req.local_model_sufficient:
        return {
            "route": "LOCAL_MODEL",
            "provider": None,
            "reason": "LOWER_INCREMENTAL_PROVIDER_SPEND",
        }

    # An expensive frontier route is not a fallback. It must be earned and named.
    if req.frontier_reasoning_earned and req.expensive_provider is not None:
        if not req.expensive_provider_authorized:
            return {
                "route": "BLOCKED_EXPENSIVE_PROVIDER_APPROVAL",
                "provider": req.expensive_provider,
                "reason": "EXPLICIT_OWNER_SPEND_AUTHORIZATION_REQUIRED",
            }
        if not req.expensive_cost_upper_bound_known:
            return {
                "route": "BLOCKED_ACCOUNTING_UNKNOWN",
                "provider": req.expensive_provider,
            }
        return {
            "route": "EXPENSIVE_FRONTIER_EXCEPTION",
            "provider": req.expensive_provider,
            "requires_amortization": AMORTIZATION_ARTIFACTS,
        }

    if req.deepseek_available and req.deepseek_authorized:
        if not req.deepseek_cost_upper_bound_known:
            return {"route": "BLOCKED_ACCOUNTING_UNKNOWN", "provider": "deepseek"}
        return {
            "route": "DEEPSEEK_SWARM",
            "provider": "deepseek",
            "requires_amortization": AMORTIZATION_ARTIFACTS,
        }

    # Deliberately do not choose Kimi/Fireworks/OpenRouter/etc. as an automatic
    # fallback. A different paid route requires a new current owner decision.
    return {
        "route": "BLOCKED_DEEPSEEK_UNAVAILABLE",
        "reason": "NO_IMPLICIT_PAID_PROVIDER_FALLBACK",
    }


def paid_inference_amortization_contract() -> tuple[str, ...]:
    """Return the reusable cognition that every paid inference must materialize."""
    return AMORTIZATION_ARTIFACTS
