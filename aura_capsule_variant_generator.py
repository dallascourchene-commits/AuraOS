"""Generate bounded, proposal-only C3 variants from a compiled C2 route capsule."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path, PurePosixPath
from typing import Any

from aura_capsule_trial_types import (
    CapsuleTrialPolicy,
    CapsuleVariant,
    SAFE_PROPOSAL_DIMENSIONS,
    canonical_digest,
)
from aura_route_capsule_compiler import compile_route_capsule
from aura_route_capsule_registry import load_registry_component

CAPSULE_VARIANT_GENERATOR_VERSION = "AURA_CAPSULE_VARIANT_GENERATOR_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_DIMENSION_TARGETS = {
    "data_aperture.maximum_files": ("data_aperture", "maximum_files"),
    "data_aperture.maximum_symbols": ("data_aperture", "maximum_symbols"),
    "data_aperture.maximum_lines": ("data_aperture", "maximum_lines"),
    "execution_budget.input_tokens": ("execution_budget", "input_tokens"),
    "execution_budget.output_tokens": ("execution_budget", "output_tokens"),
    "execution_budget.tool_calls": ("execution_budget", "tool_calls"),
    "execution_budget.wall_seconds": ("execution_budget", "wall_seconds"),
}


def load_capsule_trial_policy(
    reference: str,
    *,
    repo_root: str | Path = ".",
) -> CapsuleTrialPolicy:
    path = _resolve_under(repo_root, reference, ".aura/capsule_trial_policies")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("C3 trial policy must contain an object")
    return CapsuleTrialPolicy.from_dict(payload)


def generate_capsule_variants(
    policy: CapsuleTrialPolicy,
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Compile one capsule and create baseline plus single-axis tightening variants."""
    result = compile_route_capsule(policy.route_capsule_ref, repo_root=repo_root)
    if not result.ok or result.compiled is None:
        return _denial(
            "route_capsule_compile_failed",
            diagnostics=[item.to_dict() for item in result.diagnostics],
        )
    compiled = result.compiled
    try:
        data_component = load_registry_component(
            repo_root,
            compiled.capsule.data_aperture_ref,
            field_name="data_aperture_ref",
        )
        budget_component = load_registry_component(
            repo_root,
            compiled.capsule.execution_budget_ref,
            field_name="execution_budget_ref",
        )
    except Exception as exc:  # noqa: BLE001
        return _denial(f"variant_component_load_failed:{type(exc).__name__}")

    baseline = {
        "data_aperture": deepcopy(data_component.payload),
        "execution_budget": deepcopy(budget_component.payload),
    }
    unsafe = _validate_requested_values(policy, baseline)
    if unsafe:
        return _denial("proposal_dimension_expands_or_invalidates_baseline", diagnostics=unsafe)

    variants: list[CapsuleVariant] = []
    variants.append(_variant(
        policy=policy,
        compiled=compiled,
        data_aperture=baseline["data_aperture"],
        execution_budget=baseline["execution_budget"],
        overrides={},
        reason="PINNED_BASELINE",
    ))

    for dimension in sorted(policy.proposal_safe_dimensions):
        target_group, target_key = _DIMENSION_TARGETS[dimension]
        current = int(baseline[target_group][target_key])
        for proposed in sorted(set(policy.proposal_safe_dimensions[dimension])):
            proposed = int(proposed)
            if proposed == current:
                continue
            data_aperture = deepcopy(baseline["data_aperture"])
            execution_budget = deepcopy(baseline["execution_budget"])
            target = data_aperture if target_group == "data_aperture" else execution_budget
            target[target_key] = proposed
            variants.append(_variant(
                policy=policy,
                compiled=compiled,
                data_aperture=data_aperture,
                execution_budget=execution_budget,
                overrides={dimension: proposed},
                reason=f"SINGLE_AXIS_TIGHTENING:{dimension}",
            ))
            if len(variants) >= policy.maximum_variants:
                break
        if len(variants) >= policy.maximum_variants:
            break

    return {
        "ok": True,
        "version": CAPSULE_VARIANT_GENERATOR_VERSION,
        "policy": policy.to_dict(),
        "compiled_capsule": compiled.to_dict(),
        "variant_count": len(variants),
        "variants": [item.to_dict() for item in variants],
        "variant_objects": variants,
        "proposal_safe_dimensions": sorted(SAFE_PROPOSAL_DIMENSIONS),
        "single_axis_only": True,
        "baseline_expansion_allowed": False,
        "capability_mutation_allowed": False,
        "model_policy_mutation_allowed": False,
        "verifier_mutation_allowed": False,
        "output_schema_mutation_allowed": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_capsule_activation": False,
        "automatic_code_installation": False,
    }


def _validate_requested_values(
    policy: CapsuleTrialPolicy,
    baseline: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for dimension, values in policy.proposal_safe_dimensions.items():
        if dimension not in _DIMENSION_TARGETS:
            diagnostics.append({"dimension": dimension, "reason": "unsupported_dimension"})
            continue
        group, key = _DIMENSION_TARGETS[dimension]
        try:
            current = int(baseline[group][key])
        except (KeyError, TypeError, ValueError, OverflowError):
            diagnostics.append({"dimension": dimension, "reason": "baseline_value_missing_or_invalid"})
            continue
        for proposed in values:
            if int(proposed) <= 0:
                diagnostics.append({"dimension": dimension, "value": proposed, "reason": "nonpositive"})
            elif int(proposed) > current:
                diagnostics.append({
                    "dimension": dimension,
                    "value": proposed,
                    "baseline": current,
                    "reason": "expansion_forbidden",
                })
    return diagnostics


def _variant(
    *,
    policy: CapsuleTrialPolicy,
    compiled: Any,
    data_aperture: dict[str, Any],
    execution_budget: dict[str, Any],
    overrides: dict[str, int],
    reason: str,
) -> CapsuleVariant:
    identity = {
        "policy_id": policy.policy_id,
        "capsule_digest": compiled.capsule.digest(),
        "component_digests": compiled.component_digests,
        "overrides": overrides,
    }
    return CapsuleVariant(
        variant_id=f"CVAR-{canonical_digest(identity)[:24]}",
        policy_id=policy.policy_id,
        capsule_id=compiled.capsule.capsule_id,
        capsule_digest=compiled.capsule.digest(),
        capsule_manifest_digest=compiled.capsule_manifest_digest,
        source_path=compiled.source_path,
        requested_capabilities=tuple(compiled.capsule.requested_capabilities),
        component_digests=dict(compiled.component_digests),
        overrides=dict(overrides),
        data_aperture=deepcopy(data_aperture),
        execution_budget=deepcopy(execution_budget),
        generation_reason=reason,
    )


def _resolve_under(repo_root: str | Path, reference: str, expected_root: str) -> Path:
    root = Path(repo_root).resolve()
    raw = str(reference or "").strip().replace("\\", "/")
    relative = PurePosixPath(raw)
    expected = PurePosixPath(expected_root)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("reference must be repository-relative without traversal")
    try:
        relative.relative_to(expected)
    except ValueError as exc:
        raise ValueError(f"reference must remain under {expected.as_posix()}") from exc
    path = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("reference may not traverse symlinks")
    if not path.is_file():
        raise FileNotFoundError(raw)
    resolved = path.resolve()
    resolved.relative_to(root)
    return resolved


def _denial(reason: str, *, diagnostics: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "DENIED",
        "reason": reason,
        "diagnostics": list(diagnostics or []),
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_capsule_activation": False,
        "automatic_code_installation": False,
    }
