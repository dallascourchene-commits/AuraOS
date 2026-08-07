"""Aura Ephemeral Adapter Registry — exact operational artifact identities.

The registry preserves the V1 public API while adding the behavioral identity,
host compatibility, rollback, and revocation evidence required by the verified
Ephemeral Workspace V2 lifecycle.  An adapter declaration is evidence only;
execution still requires an active workspace lease and exact current binding.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ADAPTER_IDENTITY_VERSION = "AURA_EPHEMERAL_ADAPTER_IDENTITY_V2"
OPERATIONAL_STATUSES = (
    "DECLARED", "REGISTERED", "OPERATIONAL", "DEGRADED", "NOT_OPERATIONAL", "DENIED",
)
_REVOCATION_STATES = ("ACTIVE", "REVOKED")


def _canonical_json(value: Any) -> str:
    """Serialize a bounded metadata value deterministically."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("adapter metadata is not canonical JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _callable_digest(implementation: Callable[..., Any]) -> str:
    """Bind a Python implementation to portable source identity."""
    try:
        source = inspect.getsource(implementation).encode("utf-8")
    except (OSError, TypeError) as exc:
        raise ValueError(
            "adapter implementation source is unavailable for stable identity"
        ) from exc
    identity = {
        "module": str(getattr(implementation, "__module__", "")),
        "qualname": str(getattr(implementation, "__qualname__", "")),
        "source_sha256": hashlib.sha256(source).hexdigest(),
    }
    return _digest(identity)

def _strict_mapping(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{name} must be an exact object")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{name} keys must be strings")
    # Round trip once so caller-owned nested containers cannot mutate the record.
    try:
        return json.loads(_canonical_json(value))
    except json.JSONDecodeError as exc:  # pragma: no cover - canonical output is valid
        raise ValueError(f"{name} is invalid") from exc


@dataclass
class AdapterMetadata:
    """Versioned behavior identity for one bounded adapter implementation."""

    adapter_id: str
    domain: str = "ephemeral"
    version: str = "1.0.0"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    side_effect_class: str = "read_only"
    source_allowlist: list[str] = field(default_factory=list)
    data_classes: list[str] = field(default_factory=list)
    resource_cost_class: str = "low"
    human_approval_policy: str = "not_required"
    operational_status: str = "DECLARED"
    implementation_ref: str = ""
    tests: list[str] = field(default_factory=list)
    host_compatibility: list[str] = field(default_factory=lambda: ["python-stdlib"])
    rollback_ref: str = ""
    revocation_state: str = "ACTIVE"
    revocation_reason: str = ""
    input_schema_digest: str = ""
    output_schema_digest: str = ""
    implementation_digest: str = ""
    adapter_digest: str = ""
    identity_version: str = ADAPTER_IDENTITY_VERSION

    def _identity_body(self) -> dict[str, Any]:
        return {
            "identity_version": self.identity_version,
            "adapter_id": self.adapter_id,
            "domain": self.domain,
            "version": self.version,
            "input_schema_digest": self.input_schema_digest,
            "output_schema_digest": self.output_schema_digest,
            "required_capabilities": list(self.required_capabilities),
            "side_effect_class": self.side_effect_class,
            "source_allowlist": list(self.source_allowlist),
            "data_classes": list(self.data_classes),
            "resource_cost_class": self.resource_cost_class,
            "human_approval_policy": self.human_approval_policy,
            "operational_status": self.operational_status,
            "implementation_ref": self.implementation_ref,
            "implementation_digest": self.implementation_digest,
            "tests": list(self.tests),
            "host_compatibility": list(self.host_compatibility),
            "rollback_ref": self.rollback_ref,
            "revocation_state": self.revocation_state,
            "revocation_reason": self.revocation_reason,
        }

    def finalize_identity(self, implementation: Callable[..., Any] | None = None) -> None:
        if type(self.adapter_id) is not str or not self.adapter_id:
            raise ValueError("adapter_id must be a non-empty string")
        if self.operational_status not in OPERATIONAL_STATUSES:
            raise ValueError("invalid operational_status")
        if self.revocation_state not in _REVOCATION_STATES:
            raise ValueError("invalid revocation_state")
        self.input_schema = _strict_mapping(self.input_schema, "input_schema")
        self.output_schema = _strict_mapping(self.output_schema, "output_schema")
        for name in (
            "required_capabilities", "source_allowlist", "data_classes", "tests", "host_compatibility",
        ):
            values = getattr(self, name)
            if type(values) is not list or any(type(item) is not str or not item for item in values):
                raise ValueError(f"{name} must be a list of non-empty strings")
            setattr(self, name, sorted(set(values)))
        self.input_schema_digest = _digest(self.input_schema)
        self.output_schema_digest = _digest(self.output_schema)
        if implementation is not None:
            self.implementation_digest = _callable_digest(implementation)
        elif not self.implementation_digest:
            self.implementation_digest = "0" * 64
        if len(self.implementation_digest) != 64:
            raise ValueError("implementation_digest must be an exact SHA-256 digest")
        self.adapter_digest = _digest(self._identity_body())

    def to_dict(self) -> dict[str, Any]:
        return json.loads(_canonical_json(asdict(self)))

    def binding(self) -> dict[str, Any]:
        """Return only behavior-defining fields needed by a graph node."""
        if not self.adapter_digest:
            raise ValueError("adapter identity has not been finalized")
        return {
            "identity_version": self.identity_version,
            "adapter_id": self.adapter_id,
            "version": self.version,
            "adapter_digest": self.adapter_digest,
            "implementation_digest": self.implementation_digest,
            "input_schema_digest": self.input_schema_digest,
            "output_schema_digest": self.output_schema_digest,
            "side_effect_class": self.side_effect_class,
            "human_approval_policy": self.human_approval_policy,
            "host_compatibility": list(self.host_compatibility),
            "rollback_ref": self.rollback_ref,
            "revocation_state": self.revocation_state,
        }


class OperationalAdapterRegistry:
    """Registry of built-in adapters with exact identity and revocation state."""

    def __init__(self) -> None:
        self._adapters: dict[str, AdapterMetadata] = {}
        self._implementations: dict[str, Callable[..., dict[str, Any]]] = {}

    def declare(
        self,
        meta: AdapterMetadata,
        *,
        implementation: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if type(meta) is not AdapterMetadata:
            raise ValueError("meta must be an exact AdapterMetadata record")
        meta.operational_status = "OPERATIONAL" if implementation is not None else "DECLARED"
        meta.finalize_identity(implementation)
        if meta.adapter_id in self._adapters:
            existing = self._adapters[meta.adapter_id]
            if existing.adapter_digest != meta.adapter_digest:
                return {"ok": False, "error": f"adapter_already_declared: {meta.adapter_id}"}
        self._adapters[meta.adapter_id] = meta
        if implementation is not None:
            self._implementations[meta.adapter_id] = implementation
        return {
            "ok": True,
            "adapter_id": meta.adapter_id,
            "status": meta.operational_status,
            "adapter_digest": meta.adapter_digest,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def get(self, adapter_id: str) -> dict[str, Any]:
        meta = self._adapters.get(adapter_id)
        if not meta:
            return {"ok": False, "error": f"unknown_adapter: {adapter_id}",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "metadata": meta.to_dict(),
                "has_implementation": adapter_id in self._implementations,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def get_binding(self, adapter_id: str) -> dict[str, Any]:
        result = self.get(adapter_id)
        if not result.get("ok"):
            return result
        meta = self._adapters[adapter_id]
        return {"ok": True, "binding": meta.binding(),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def revoke(self, adapter_id: str, *, reason: str) -> dict[str, Any]:
        meta = self._adapters.get(adapter_id)
        if not meta:
            return {"ok": False, "error": f"unknown_adapter: {adapter_id}"}
        if type(reason) is not str or not reason:
            raise ValueError("revocation reason is required")
        meta.revocation_state = "REVOKED"
        meta.revocation_reason = reason
        meta.operational_status = "DENIED"
        meta.finalize_identity(self._implementations.get(adapter_id))
        return {"ok": True, "adapter_id": adapter_id, "revocation_state": "REVOKED",
                "adapter_digest": meta.adapter_digest,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def execute(self, adapter_id: str, *, params: dict[str, Any] | None = None,
                lease_active: bool = True) -> dict[str, Any]:
        try:
            params = {} if params is None else _strict_mapping(params, "params")
        except ValueError as exc:
            return {"ok": False, "error": f"invalid_adapter_params: {exc}",
                    "failure_class": "structural",
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        meta = self._adapters.get(adapter_id)
        if not meta:
            return {"ok": False, "error": f"unknown_adapter: {adapter_id}", "status": "DENIED",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if meta.revocation_state == "REVOKED" or meta.operational_status == "DENIED":
            return {"ok": False, "error": f"adapter_revoked: {adapter_id}", "status": "DENIED",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if meta.operational_status != "OPERATIONAL":
            return {"ok": False, "error": f"adapter_not_operational: {adapter_id} ({meta.operational_status})",
                    "status": meta.operational_status,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if lease_active is not True:
            return {"ok": False, "error": "lease_revoked: adapter calls blocked",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        impl = self._implementations.get(adapter_id)
        if impl is None:
            return {"ok": False, "error": f"no_implementation: {adapter_id}", "status": "NOT_OPERATIONAL",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        try:
            result = impl(**params)
        except Exception as exc:
            return {"ok": False, "error": f"adapter_callback_failed: {type(exc).__name__}: {exc}",
                    "adapter": adapter_id, "failure_class": "environment",
                    "adapter_digest": meta.adapter_digest,
                    "implementation_digest": meta.implementation_digest,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if not isinstance(result, Mapping):
            return {"ok": False, "error": "adapter_result_must_be_mapping", "adapter": adapter_id,
                    "failure_class": "structural",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        detached = dict(result)
        if type(detached.get("ok")) is not bool:
            return {"ok": False, "error": "adapter_result_missing_status", "adapter": adapter_id,
                    "failure_class": "structural",
                    "adapter_digest": meta.adapter_digest,
                    "implementation_digest": meta.implementation_digest,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        detached["adapter"] = adapter_id
        detached["operational_status"] = "OPERATIONAL"
        detached["adapter_digest"] = meta.adapter_digest
        detached["implementation_digest"] = meta.implementation_digest
        detached["patch_authority"] = PATCH_AUTHORITY
        detached["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return detached

    def list_adapters(self) -> dict[str, Any]:
        return {"ok": True,
                "adapters": [self._adapters[key].to_dict() for key in sorted(self._adapters)],
                "count": len(self._adapters),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def is_operational(self, adapter_id: str) -> bool:
        meta = self._adapters.get(adapter_id)
        return bool(meta is not None and meta.operational_status == "OPERATIONAL"
                    and meta.revocation_state == "ACTIVE" and adapter_id in self._implementations)


_global_registry: OperationalAdapterRegistry | None = None


def get_global_adapter_registry() -> OperationalAdapterRegistry:
    global _global_registry  # noqa: PLW0603
    if _global_registry is None:
        _global_registry = OperationalAdapterRegistry()
        _register_default_adapters(_global_registry)
    return _global_registry


def _register_default_adapters(reg: OperationalAdapterRegistry) -> None:
    """Register existing built-ins without granting arbitrary native execution."""
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
            implementation_ref=f"aura_ephemeral_sandbox.BUILTIN_ADAPTERS[{adapter_id!r}]",
            rollback_ref="aura_ephemeral_sandbox.BUILTIN_ADAPTERS",
            tests=["tests/test_aura_ephemeral_sandbox.py"],
        )
        reg.declare(meta, implementation=impl)
