"""Fail-closed materialization of compiled Aura Executable Route Capsules.

C2 materialization converts a validated capsule into a bounded runtime aperture. It
never executes tools, retrieves repository content, selects a model, or grants a
lease. Callers provide already-authorized context and explicit measured usage.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from aura_route_capsule_registry import load_registry_component
from aura_route_capsule_types import CompiledRouteCapsule, REFERENCE_FIELDS

ROUTE_CAPSULE_MATERIALIZER_VERSION = "AURA_ROUTE_CAPSULE_MATERIALIZER_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_BUDGET_KEYS = (
    "input_tokens",
    "output_tokens",
    "tool_calls",
    "model_calls",
    "wall_seconds",
)


@dataclass(frozen=True)
class MaterializedRouteCapsule:
    capsule_id: str
    transition_id: str
    capsule_digest: str
    aperture_digest: str
    data_aperture: dict[str, Any]
    memory_aperture: dict[str, Any]
    tool_bundle: dict[str, Any]
    model_policy: dict[str, Any]
    execution_budget: dict[str, Any]
    verifier_contract: dict[str, Any]
    output_schema: dict[str, Any]
    component_digests: dict[str, str]
    actual_context_items: tuple[dict[str, Any], ...] = ()
    actual_memory_refs: tuple[str, ...] = ()
    requested_model: str = ""
    selected_model: str = ""
    budget_consumed: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": ROUTE_CAPSULE_MATERIALIZER_VERSION,
            "capsule_id": self.capsule_id,
            "transition_id": self.transition_id,
            "capsule_digest": self.capsule_digest,
            "aperture_digest": self.aperture_digest,
            "data_aperture": dict(self.data_aperture),
            "memory_aperture": dict(self.memory_aperture),
            "tool_bundle": dict(self.tool_bundle),
            "model_policy": dict(self.model_policy),
            "execution_budget": dict(self.execution_budget),
            "verifier_contract": dict(self.verifier_contract),
            "output_schema": dict(self.output_schema),
            "component_digests": dict(sorted(self.component_digests.items())),
            "actual_context_items": [dict(item) for item in self.actual_context_items],
            "actual_memory_refs": list(self.actual_memory_refs),
            "requested_model": self.requested_model,
            "selected_model": self.selected_model,
            "budget_consumed": dict(self.budget_consumed or {}),
            "routing_authority": "advisory_after_hard_guards",
            "runtime_execution_performed": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_activation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }


def materialize_route_capsule(
    compiled: CompiledRouteCapsule,
    *,
    repo_root: str | Path = ".",
    context: Mapping[str, Any] | None = None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Revalidate every component pin and emit a bounded, non-executing aperture."""
    root = Path(repo_root).resolve()
    context = dict(context or {})
    policy = dict(policy or {})
    if policy.get("route_capsules_enabled") is not True:
        return _denial("route_capsule_feature_disabled")

    components: dict[str, dict[str, Any]] = {}
    for field_name in REFERENCE_FIELDS:
        try:
            loaded = load_registry_component(
                root,
                getattr(compiled.capsule, field_name),
                field_name=field_name,
            )
        except Exception as exc:  # noqa: BLE001 - fail-closed boundary
            return _denial(f"component_reload_failed:{field_name}:{type(exc).__name__}")
        pinned = str(compiled.component_digests.get(field_name) or "")
        if not pinned or loaded.digest != pinned:
            return _denial(f"component_digest_mismatch:{field_name}")
        components[field_name] = dict(loaded.payload)

    lease = {str(item) for item in context.get("lease_capabilities", ()) or ()}
    required = set(compiled.capsule.requested_capabilities)
    missing = sorted(required - lease)
    if missing:
        return _denial("capsule_lease_missing_capability", missing=missing)

    data_aperture = _bounded_component(
        components["data_aperture_ref"],
        allowed=(
            "schema_version", "component_id", "kind", "source", "maximum_files",
            "maximum_symbols", "maximum_lines", "require_source_hashes",
            "allow_unbounded_repository_context",
        ),
    )
    memory_aperture = _bounded_component(
        components["memory_aperture_ref"],
        allowed=(
            "schema_version", "component_id", "kind", "arena_id", "states",
            "transition_ids", "maximum_experiences", "exclude",
        ),
    )
    tool_bundle = _bounded_component(
        components["tool_bundle_ref"],
        allowed=(
            "schema_version", "component_id", "kind", "requested_capabilities",
            "forbidden_capabilities", "parallel_groups",
        ),
    )
    model_policy = _bounded_component(
        components["model_policy_ref"],
        allowed=(
            "schema_version", "component_id", "kind", "default", "fallback",
            "external_allowed", "maximum_model_calls", "escalation_requires",
        ),
    )
    execution_budget = _bounded_component(
        components["execution_budget_ref"],
        allowed=(
            "schema_version", "component_id", "kind", "input_tokens", "output_tokens",
            "tool_calls", "model_calls", "wall_seconds", "budget_authority",
        ),
    )
    verifier_contract = _bounded_component(
        components["verifier_contract_ref"],
        allowed=(
            "schema_version", "component_id", "kind", "required",
            "human_review_required", "self_verification_sufficient",
        ),
    )
    output_schema = _bounded_component(
        components["output_schema_ref"],
        allowed=(
            "schema_version", "component_id", "kind", "type", "required_fields",
            "additional_properties",
        ),
    )

    if bool(data_aperture.get("allow_unbounded_repository_context")):
        return _denial("unbounded_repository_context_forbidden")
    limits = _validate_limits(data_aperture, memory_aperture, execution_budget)
    if not limits["ok"]:
        return _denial(str(limits["reason"]), missing=list(limits.get("missing") or []))

    actual_context = _bounded_context_items(
        context.get("capsule_context_items") or (),
        max_files=limits["maximum_files"],
        max_symbols=limits["maximum_symbols"],
        max_lines=limits["maximum_lines"],
        require_source_hashes=bool(data_aperture.get("require_source_hashes")),
    )
    actual_memory_refs = _bounded_memory_refs(
        context.get("capsule_memory_refs") or (),
        maximum=limits["maximum_experiences"],
    )

    requested_model = str(context.get("requested_model") or "").strip()
    selected_model = _select_model(requested_model, model_policy)
    if selected_model is None:
        return _denial("requested_model_not_allowed")

    consumed = _numeric_budget(context.get("capsule_budget_consumed") or {})
    exceeded = _budget_exceeded(limits["execution_budget"], consumed)
    if exceeded:
        return _denial("capsule_budget_exceeded", missing=exceeded)

    aperture_payload = {
        "capsule_id": compiled.capsule.capsule_id,
        "transition_id": compiled.capsule.transition_id,
        "capsule_digest": compiled.capsule.digest(),
        "data_aperture": data_aperture,
        "memory_aperture": memory_aperture,
        "tool_bundle": tool_bundle,
        "model_policy": model_policy,
        "execution_budget": limits["execution_budget"],
        "verifier_contract": verifier_contract,
        "output_schema": output_schema,
        "component_digests": dict(sorted(compiled.component_digests.items())),
        "actual_context_items": actual_context,
        "actual_memory_refs": actual_memory_refs,
        "requested_model": requested_model,
        "selected_model": selected_model,
        "budget_consumed": consumed,
    }
    aperture_digest = _digest(aperture_payload)
    materialized = MaterializedRouteCapsule(
        capsule_id=compiled.capsule.capsule_id,
        transition_id=compiled.capsule.transition_id,
        capsule_digest=compiled.capsule.digest(),
        aperture_digest=aperture_digest,
        data_aperture=data_aperture,
        memory_aperture=memory_aperture,
        tool_bundle={
            **tool_bundle,
            "capability_bindings": [dict(item) for item in compiled.capability_bindings],
        },
        model_policy=model_policy,
        execution_budget=limits["execution_budget"],
        verifier_contract=verifier_contract,
        output_schema=output_schema,
        component_digests=dict(compiled.component_digests),
        actual_context_items=tuple(actual_context),
        actual_memory_refs=tuple(actual_memory_refs),
        requested_model=requested_model,
        selected_model=selected_model,
        budget_consumed=consumed,
    )
    return {
        "ok": True,
        "materialized": materialized.to_dict(),
        "aperture_digest": aperture_digest,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_activation": False,
    }


def _validate_limits(
    data_aperture: Mapping[str, Any],
    memory_aperture: Mapping[str, Any],
    execution_budget: Mapping[str, Any],
) -> dict[str, Any]:
    missing = [
        name
        for name in ("maximum_files", "maximum_symbols", "maximum_lines")
        if name not in data_aperture
    ]
    if "maximum_experiences" not in memory_aperture:
        missing.append("maximum_experiences")
    missing.extend(name for name in _BUDGET_KEYS if name not in execution_budget)
    if missing:
        return {"ok": False, "reason": "capsule_limits_missing", "missing": sorted(set(missing))}
    try:
        maximum_files = int(data_aperture["maximum_files"])
        maximum_symbols = int(data_aperture["maximum_symbols"])
        maximum_lines = int(data_aperture["maximum_lines"])
        maximum_experiences = int(memory_aperture["maximum_experiences"])
        normalized_budget = {
            key: float(execution_budget[key])
            for key in _BUDGET_KEYS
        }
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "reason": "capsule_limits_invalid", "missing": []}
    if min(maximum_files, maximum_symbols, maximum_lines) <= 0:
        return {"ok": False, "reason": "capsule_context_limits_must_be_positive", "missing": []}
    if maximum_experiences < 0 or any(value < 0 for value in normalized_budget.values()):
        return {"ok": False, "reason": "capsule_limits_must_be_nonnegative", "missing": []}
    return {
        "ok": True,
        "maximum_files": maximum_files,
        "maximum_symbols": maximum_symbols,
        "maximum_lines": maximum_lines,
        "maximum_experiences": maximum_experiences,
        "execution_budget": {
            **execution_budget,
            **normalized_budget,
        },
    }


def _bounded_component(payload: Mapping[str, Any], *, allowed: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in allowed if key in payload}


def _bounded_context_items(
    raw_items: Any,
    *,
    max_files: int,
    max_symbols: int,
    max_lines: int,
    require_source_hashes: bool,
) -> list[dict[str, Any]]:
    if not isinstance(raw_items, (list, tuple)):
        return []
    output: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    seen_symbols: set[str] = set()
    line_total = 0
    for raw in raw_items:
        if not isinstance(raw, Mapping):
            continue
        path = _safe_relative_path(raw.get("path") or raw.get("file") or "")
        if not path:
            continue
        symbol = str(raw.get("symbol") or "").strip()
        lines = _nonnegative_int(raw.get("line_count"), 0)
        source_hash = str(raw.get("source_hash") or "").strip()[:160]
        if require_source_hashes and not source_hash:
            continue
        if path not in seen_files and len(seen_files) >= max_files:
            continue
        if symbol and symbol not in seen_symbols and len(seen_symbols) >= max_symbols:
            continue
        if line_total + lines > max_lines:
            continue
        seen_files.add(path)
        if symbol:
            seen_symbols.add(symbol)
        line_total += lines
        output.append({
            "path": path,
            "symbol": symbol,
            "line_start": _nonnegative_int(raw.get("line_start"), 0),
            "line_end": _nonnegative_int(raw.get("line_end"), 0),
            "line_count": lines,
            "source_hash": source_hash,
        })
    return output


def _bounded_memory_refs(raw: Any, *, maximum: int) -> list[str]:
    if not isinstance(raw, (list, tuple)) or maximum == 0:
        return []
    refs: list[str] = []
    for value in raw:
        text = str(value or "").strip()
        if not text or text in refs:
            continue
        if any(term in text.casefold() for term in ("secret", "hidden_reasoning", "scratchpad")):
            continue
        refs.append(text[:240])
        if len(refs) >= maximum:
            break
    return refs


def _safe_relative_path(value: Any) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw:
        return ""
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        return ""
    if ":" in pure.parts[0]:
        return ""
    return pure.as_posix()


def _select_model(requested: str, policy: Mapping[str, Any]) -> str | None:
    default = str(policy.get("default") or "no_model").strip()
    fallback = str(policy.get("fallback") or "").strip()
    external_allowed = bool(policy.get("external_allowed"))
    if not requested:
        return default
    allowed = {value for value in (default, fallback) if value}
    if requested in allowed:
        return requested
    if requested.startswith("external:") and external_allowed:
        return requested
    return None


def _numeric_budget(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {key: 0.0 for key in _BUDGET_KEYS}
    result: dict[str, float] = {}
    for key in _BUDGET_KEYS:
        try:
            result[key] = max(0.0, float(value.get(key, 0.0)))
        except (TypeError, ValueError, OverflowError):
            result[key] = 0.0
    return result


def _budget_exceeded(budget: Mapping[str, Any], consumed: Mapping[str, float]) -> list[str]:
    exceeded: list[str] = []
    for key in _BUDGET_KEYS:
        used = float(consumed.get(key, 0.0))
        limit = float(budget[key])
        if used > limit:
            exceeded.append(key)
    return exceeded


def _nonnegative_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def _denial(reason: str, *, missing: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "missing": list(missing or []),
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_activation": False,
    }
