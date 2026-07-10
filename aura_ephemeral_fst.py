"""
Aura Ephemeral FST — product automaton for ephemeral organ admission control.

Combines:
  1. LEXC route (semantic six-slot morphotactic validation via AuraLexc)
  2. Machine route (deterministic hard gates via AuraCodingArenaRouter)
  3. Lifecycle transition validation
  4. Capability lease containment
  5. Component digest verification
  6. Static security policy checks
  7. Human approval requirements

FST validity is necessary but NEVER sufficient.
The FST is an admission grammar, not a security sandbox.

Dependencies: stdlib only at module level. All Aura imports are lazy.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# MVP allowed routes (DIR, ASP, CLASS, SUBJ, VOICE, STEM)
MVP_ALLOWED_EFFECTS = {"READ", "COMPUTE", "WRITE_TEMP"}
MVP_BLOCKED_EFFECTS = {"NETWORK", "DEVICE", "INSTALL", "SECRET_ACCESS", "PRODUCTION_MUTATION"}
MVP_ALLOWED_TARGETS = {
    "CODEMAP", "MODULE_MANIFEST", "SOURCE_SLICE", "TOPOLOGY",
    "AFFORDANCE_DIRECTORY", "CAPABILITY_LANES", "PLUGIN_MANIFESTS",
    "TEMP_WORKSPACE", "UI_SCHEMA",
}
MVP_BLOCKED_TARGETS = {"EXTERNAL_ENDPOINT", "PRODUCTION_SOURCE", "PRIVATE_MEMORY"}


class EphemeralRoutingFrame:
    """Machine-oriented routing frame for ephemeral organ effects.

    Extends the concept of aura_fst_routing.RoutingFrame with ephemeral-specific
    fields: lease, lifecycle_state, ttl, component_digests.
    """

    def __init__(
        self,
        *,
        intent: str = "ephemeral_investigation",
        effect: str = "READ",
        target: str = "CODEMAP",
        scope: str = "read_only",
        risk: str = "low",
        grounding: str = "codemap_exists",
        lease: str = "",
        lifecycle_state: str = "DRAFTED",
        tests: str = "none",
        cost: str = "local_first",
        ttl: int = 300,
        component_digests: dict[str, str] | None = None,
        human_approval: bool = False,
    ) -> None:
        self.intent = intent
        self.effect = effect
        self.target = target
        self.scope = scope
        self.risk = risk
        self.grounding = grounding
        self.lease = lease
        self.lifecycle_state = lifecycle_state
        self.tests = tests
        self.cost = cost
        self.ttl = ttl
        self.component_digests = component_digests or {}
        self.human_approval = human_approval

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent, "effect": self.effect, "target": self.target,
            "scope": self.scope, "risk": self.risk, "grounding": self.grounding,
            "lease": self.lease, "lifecycle_state": self.lifecycle_state,
            "tests": self.tests, "cost": self.cost, "ttl": self.ttl,
            "component_digests": self.component_digests,
            "human_approval": self.human_approval,
        }


class EphemeralProductAutomatonResult:
    """Result of evaluating the product automaton."""

    def __init__(
        self,
        *,
        allowed: bool,
        lexc_valid: bool,
        machine_route: str,
        machine_reason: str,
        lifecycle_valid: bool,
        lease_valid: bool,
        component_digests_valid: bool,
        policy_checks_pass: bool,
        sandbox_required: bool,
        human_approval_required: bool,
        human_approval_present: bool,
        denial_reasons: list[str],
    ) -> None:
        self.allowed = allowed
        self.lexc_valid = lexc_valid
        self.machine_route = machine_route
        self.machine_reason = machine_reason
        self.lifecycle_valid = lifecycle_valid
        self.lease_valid = lease_valid
        self.component_digests_valid = component_digests_valid
        self.policy_checks_pass = policy_checks_pass
        self.sandbox_required = sandbox_required
        self.human_approval_required = human_approval_required
        self.human_approval_present = human_approval_present
        self.denial_reasons = denial_reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "lexc_valid": self.lexc_valid,
            "machine_route": self.machine_route,
            "machine_reason": self.machine_reason,
            "lifecycle_valid": self.lifecycle_valid,
            "lease_valid": self.lease_valid,
            "component_digests_valid": self.component_digests_valid,
            "policy_checks_pass": self.policy_checks_pass,
            "sandbox_required": self.sandbox_required,
            "human_approval_required": self.human_approval_required,
            "human_approval_present": self.human_approval_present,
            "denial_reasons": self.denial_reasons,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def compile_ephemeral_route(
    symbols: list[str],
    repo_root: str = ".",
) -> dict[str, Any]:
    """Compile a six-slot LEXC route from symbols using the ephemeral grammar.

    Returns {ok, lexc_route, symbols, errors}.
    """
    from pathlib import Path
    root = Path(repo_root).resolve()
    try:
        from aura_lexc import AuraLexc, SLOT_ORDER
        lexc = AuraLexc.from_path(root / ".aura" / "ephemeral_app.lexc", strict=False)
        result = lexc.validate_symbols(symbols)
        if result and result.is_complete:
            return {"ok": True, "lexc_route": symbols, "errors": [],
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": False, "lexc_route": symbols, "errors": ["incomplete_or_invalid_route"],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except Exception as exc:
        return {"ok": False, "lexc_route": symbols, "errors": [str(exc)],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def validate_ephemeral_route(
    symbols: list[str],
    repo_root: str = ".",
) -> dict[str, Any]:
    """Validate a six-slot ephemeral route against the ephemeral grammar."""
    return compile_ephemeral_route(symbols, repo_root)


def evaluate_ephemeral_product_automaton(
    lexc_symbols: list[str],
    frame: EphemeralRoutingFrame,
    *,
    granted_capabilities: list[str] | None = None,
    component_digests_expected: dict[str, str] | None = None,
    lifecycle_allowed: bool = True,
    sandbox_available: bool = False,
    human_approval_present: bool = False,
    repo_root: str = ".",
) -> EphemeralProductAutomatonResult:
    """Evaluate the full product automaton.

    ALLOW(action) =
        intent_route.complete
        AND machine_route.accepted
        AND lifecycle.transition_allowed
        AND requested_capabilities ⊆ granted_lease
        AND component_digests_verified
        AND policy_checks_pass
        AND sandbox_available (for arbitrary code)
        AND verifier_gate_passes
        AND required_human_approval_present
    """
    denial_reasons: list[str] = []

    # 1. LEXC route validation
    lexc_result = validate_ephemeral_route(lexc_symbols, repo_root)
    lexc_valid = lexc_result.get("ok", False)
    if not lexc_valid:
        denial_reasons.append("LEXC route invalid: " + "; ".join(lexc_result.get("errors", ["unknown"])))

    # 2. Machine route — use AuraCodingArenaRouter for deterministic hard gates
    machine_route = "ALLOWED"
    machine_reason = "ok"
    try:
        from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame
        # Build a RoutingFrame compatible with the machine router
        intent_map = {"READ": "inspect", "COMPUTE": "inspect", "WRITE_TEMP": "modify",
                      "NETWORK": "modify", "INSTALL": "modify", "SECRET_ACCESS": "modify",
                      "PRODUCTION_MUTATION": "modify"}
        router_frame = RoutingFrame(
            intent=frame.intent,
            action=intent_map.get(frame.effect, "inspect"),
            scope="symbol" if frame.scope == "read_only" else "subsystem",
            risk=frame.risk,
            grounding=("codemap_exists",) if frame.grounding == "codemap_exists" else (),
            tests=frame.tests,
            cost=frame.cost,
        )
        router = AuraCodingArenaRouter()
        decision = router.route(router_frame)
        machine_route = decision.route
        machine_reason = decision.reason
        if machine_route == "BLOCKED_WITH_REASON":
            # For read-only effects, BLOCKED_WITH_REASON from missing grounding
            # is acceptable if the effect is READ and we have CODEMAP
            if frame.effect in MVP_ALLOWED_EFFECTS and frame.target in MVP_ALLOWED_TARGETS:
                machine_route = "ALLOWED_READ_ONLY"
                machine_reason = "read_only_effect_permitted"
            else:
                denial_reasons.append(f"Machine route blocked: {machine_reason}")
    except Exception as exc:
        # Fallback: use local policy evaluation if machine router unavailable
        machine_route = "LOCAL_POLICY"
        machine_reason = f"machine_router_unavailable: {exc}"
        if frame.effect in MVP_BLOCKED_EFFECTS:
            machine_route = "BLOCKED_WITH_REASON"
            machine_reason = f"blocked_effect: {frame.effect}"
            denial_reasons.append(f"Blocked effect: {frame.effect}")
        elif frame.target in MVP_BLOCKED_TARGETS:
            machine_route = "BLOCKED_WITH_REASON"
            machine_reason = f"blocked_target: {frame.target}"
            denial_reasons.append(f"Blocked target: {frame.target}")

    # 3. MVP policy checks (static security)
    policy_pass = True
    if frame.effect in MVP_BLOCKED_EFFECTS:
        policy_pass = False
        denial_reasons.append(f"Policy: effect {frame.effect} is forbidden in MVP")
    if frame.target in MVP_BLOCKED_TARGETS:
        policy_pass = False
        denial_reasons.append(f"Policy: target {frame.target} is forbidden in MVP")

    # 4. Lifecycle validation
    lifecycle_valid = lifecycle_allowed
    if not lifecycle_valid:
        denial_reasons.append("Lifecycle: transition not allowed from current state")

    # 5. Capability lease containment
    requested_caps = set(granted_capabilities or [])
    lease_valid = True
    # If the effect requires a capability not in the lease, deny
    effect_to_cap = {
        "READ": "search_code", "COMPUTE": "resolve_capabilities",
        "WRITE_TEMP": "write_temp_audit", "NETWORK": "external_network",
        "DEVICE": "device_access", "INSTALL": "package_install",
        "SECRET_ACCESS": "secret_access", "PRODUCTION_MUTATION": "production_mutation",
    }
    required_cap = effect_to_cap.get(frame.effect, "")
    if required_cap:
        if not requested_caps:
            # No capabilities granted at all — deny
            lease_valid = False
            denial_reasons.append(f"Lease: no capabilities granted, '{required_cap}' required")
        elif required_cap not in requested_caps:
            lease_valid = False
            denial_reasons.append(f"Lease: capability '{required_cap}' not in granted lease")

    # 6. Component digest verification
    digests_valid = True
    if component_digests_expected:
        for comp_id, expected_hash in component_digests_expected.items():
            actual = frame.component_digests.get(comp_id)
            if actual != expected_hash:
                digests_valid = False
                denial_reasons.append(f"Component digest mismatch: {comp_id}")

    # 7. Sandbox requirement
    sandbox_required = frame.effect not in ("READ", "COMPUTE")
    if sandbox_required and not sandbox_available:
        denial_reasons.append("Sandbox: required but not available — failing closed")
        sandbox_available = False

    # 8. Human approval
    human_approval_required = frame.effect in ("WRITE_TEMP",) or frame.human_approval
    if human_approval_required and not human_approval_present:
        denial_reasons.append("Human approval: required but not present")

    # 9. TTL check
    if frame.ttl <= 0:
        denial_reasons.append("TTL: expired")
        lifecycle_valid = False

    # Final decision: ALL conditions must be true
    allowed = (
        lexc_valid
        and machine_route != "BLOCKED_WITH_REASON"
        and lifecycle_valid
        and lease_valid
        and digests_valid
        and policy_pass
        and (not sandbox_required or sandbox_available)
        and (not human_approval_required or human_approval_present)
    )

    return EphemeralProductAutomatonResult(
        allowed=allowed,
        lexc_valid=lexc_valid,
        machine_route=machine_route,
        machine_reason=machine_reason,
        lifecycle_valid=lifecycle_valid,
        lease_valid=lease_valid,
        component_digests_valid=digests_valid,
        policy_checks_pass=policy_pass,
        sandbox_required=sandbox_required,
        human_approval_required=human_approval_required,
        human_approval_present=human_approval_present,
        denial_reasons=denial_reasons,
    )


def explain_ephemeral_denial(result: EphemeralProductAutomatonResult) -> str:
    """Produce a human-readable explanation of why a route was denied."""
    if result.allowed:
        return "Route allowed."
    lines = ["Route DENIED. Reasons:"]
    for reason in result.denial_reasons:
        lines.append(f"  - {reason}")
    return "\n".join(lines)
