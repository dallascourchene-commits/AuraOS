"""
Aura Ephemeral Adapter Registry — operational capability metadata.

Separates DECLARED, REGISTERED, OPERATIONAL, DEGRADED, NOT_OPERATIONAL, DENIED.
Each adapter declares metadata. Unknown or unregistered adapters fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

OPERATIONAL_STATUSES = ("DECLARED", "REGISTERED", "OPERATIONAL", "DEGRADED", "NOT_OPERATIONAL", "DENIED")


@dataclass
class AdapterMetadata:
    adapter_id: str
    domain: str = "ephemeral"
    version: str = "1.0.0"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    side_effect_class: str = "read_only"  # read_only, write_temp, compute, network, device
    source_allowlist: list[str] = field(default_factory=list)
    data_classes: list[str] = field(default_factory=list)
    resource_cost_class: str = "low"
    human_approval_policy: str = "not_required"
    operational_status: str = "DECLARED"
    implementation_ref: str = ""
    tests: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OperationalAdapterRegistry:
    """Registry of built-in adapters with operational status metadata."""

    def __init__(self) -> None:
        self._adapters: dict[str, AdapterMetadata] = {}
        self._implementations: dict[str, Callable[..., dict[str, Any]]] = {}

    def declare(self, meta: AdapterMetadata, *, implementation: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
        self._adapters[meta.adapter_id] = meta
        status = "REGISTERED" if implementation else "DECLARED"
        meta.operational_status = status
        if implementation:
            self._implementations[meta.adapter_id] = implementation
            meta.operational_status = "OPERATIONAL"
        return {"ok": True, "adapter_id": meta.adapter_id, "status": meta.operational_status,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def get(self, adapter_id: str) -> dict[str, Any]:
        meta = self._adapters.get(adapter_id)
        if not meta:
            return {"ok": False, "error": f"unknown_adapter: {adapter_id}",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "metadata": meta.to_dict(),
                "has_implementation": adapter_id in self._implementations,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def execute(self, adapter_id: str, *, params: dict[str, Any] | None = None,
                lease_active: bool = True) -> dict[str, Any]:
        params = params or {}
        meta = self._adapters.get(adapter_id)
        if not meta:
            return {"ok": False, "error": f"unknown_adapter: {adapter_id}", "status": "DENIED",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if meta.operational_status in ("DECLARED", "NOT_OPERATIONAL", "DEGRADED"):
            return {"ok": False, "error": f"adapter_not_operational: {adapter_id} ({meta.operational_status})",
                    "status": meta.operational_status,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if meta.operational_status == "DENIED":
            return {"ok": False, "error": f"adapter_denied: {adapter_id}", "status": "DENIED",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if not lease_active:
            return {"ok": False, "error": "lease_revoked: adapter calls blocked",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        impl = self._implementations.get(adapter_id)
        if not impl:
            return {"ok": False, "error": f"no_implementation: {adapter_id}", "status": "NOT_OPERATIONAL",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        try:
            result = impl(**params)
            result["adapter"] = adapter_id
            result["operational_status"] = "OPERATIONAL"
            result["patch_authority"] = PATCH_AUTHORITY
            result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
            return result
        except Exception as exc:
            return {"ok": False, "error": str(exc), "adapter": adapter_id,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def list_adapters(self) -> dict[str, Any]:
        return {"ok": True,
                "adapters": [m.to_dict() for m in self._adapters.values()],
                "count": len(self._adapters),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def is_operational(self, adapter_id: str) -> bool:
        meta = self._adapters.get(adapter_id)
        return meta is not None and meta.operational_status == "OPERATIONAL" and adapter_id in self._implementations


# Global singleton
_global_registry: OperationalAdapterRegistry | None = None


def get_global_adapter_registry() -> OperationalAdapterRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = OperationalAdapterRegistry()
        _register_default_adapters(_global_registry)
    return _global_registry


def _register_default_adapters(reg: OperationalAdapterRegistry) -> None:
    """Register the built-in read-only adapters with full metadata."""
    from aura_ephemeral_sandbox import BUILTIN_ADAPTERS
    for adapter_id, impl in BUILTIN_ADAPTERS.items():
        side_effect = "read_only"
        if adapter_id == "write_temp_audit":
            side_effect = "write_temp"
        elif adapter_id == "emit_telemetry":
            side_effect = "compute"
        meta = AdapterMetadata(
            adapter_id=adapter_id,
            domain="ephemeral",
            side_effect_class=side_effect,
            operational_status="OPERATIONAL",
            implementation_ref=f"aura_ephemeral_sandbox.BUILTIN_ADAPTERS[{adapter_id!r}]",
            tests=[],
        )
        reg.declare(meta, implementation=impl)
