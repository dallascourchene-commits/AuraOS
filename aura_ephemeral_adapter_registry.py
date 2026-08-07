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
import multiprocessing
import os
import signal
import time
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


def _bounded_callback_worker(
    implementation: Callable[..., dict[str, Any]],
    expected_implementation_digest: str,
    params: dict[str, Any],
    connection: Any,
    max_output_bytes: int,
    max_memory_mb: int,
) -> None:
    """Execute one exact registered callback in a new POSIX process group."""
    try:
        os.setsid()
        try:
            import resource
            if not hasattr(resource, "RLIMIT_AS"):
                raise RuntimeError("RLIMIT_AS is unavailable")
            limit_bytes = max_memory_mb * 1024 * 1024
            _soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
            if hard_limit != resource.RLIM_INFINITY:
                limit_bytes = min(limit_bytes, hard_limit)
            if limit_bytes < 1:
                raise RuntimeError("effective address-space limit is invalid")
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
        except Exception as exc:
            connection.send_bytes(_canonical_json({
                "kind": "worker_error",
                "error": f"bounded_adapter_memory_limit_failed: {type(exc).__name__}: {str(exc)[:1024]}",
                "failure_class": "environment",
            }).encode("utf-8"))
            return
        try:
            current_digest = _callable_digest(implementation)
        except Exception as exc:
            connection.send_bytes(_canonical_json({
                "kind": "worker_error",
                "error": f"bounded_adapter_identity_unavailable: {type(exc).__name__}: {str(exc)[:1024]}",
                "failure_class": "stale",
            }).encode("utf-8"))
            return
        if current_digest != expected_implementation_digest:
            connection.send_bytes(_canonical_json({
                "kind": "worker_error",
                "error": "bounded_adapter_implementation_digest_mismatch",
                "failure_class": "stale",
            }).encode("utf-8"))
            return
        connection.send_bytes(b'{"kind":"ready"}')
        if connection.recv_bytes() != b"execute":
            return
        try:
            result = implementation(**params)
        except BaseException as exc:
            if isinstance(exc, Exception):
                envelope = {
                    "kind": "callback_error",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:2048],
                }
            else:
                envelope = {
                    "kind": "base_exception",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:2048],
                }
        else:
            if not isinstance(result, Mapping):
                envelope = {"kind": "result_error", "error": "adapter_result_must_be_mapping"}
            else:
                try:
                    detached = dict(result)
                    result_json = _canonical_json(detached)
                except Exception as exc:
                    envelope = {
                        "kind": "result_error",
                        "error": f"adapter_result_not_canonical: {type(exc).__name__}: {str(exc)[:1024]}",
                    }
                else:
                    encoded = result_json.encode("utf-8")
                    if len(encoded) > max_output_bytes:
                        envelope = {
                            "kind": "result_error",
                            "error": "adapter_result_transport_limit_exceeded",
                            "failure_class": "budget",
                        }
                    else:
                        envelope = {"kind": "result", "result_json": result_json}
        connection.send_bytes(_canonical_json(envelope).encode("utf-8"))
        # Keep the process-group leader alive until the authority-owning parent
        # kills/reaps the whole group, including any callback descendants.
        try:
            connection.recv_bytes()
        except EOFError:
            pass
    except BaseException:
        pass
    finally:
        connection.close()


def _kill_bounded_process_group(process: Any) -> None:
    pid = getattr(process, "pid", None)
    if pid is None:
        return
    if os.name == "posix":
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            if process.is_alive():
                process.kill()
    elif process.is_alive():
        process.kill()
    process.join(timeout=1.0)
    if process.is_alive():
        process.kill()
        process.join(timeout=1.0)


def _bounded_event(
    event: str,
    error: str,
    failure_class: str,
) -> tuple[dict[str, Any], bool]:
    return ({
        "ok": False,
        "error": error,
        "failure_class": failure_class,
        "_aura_bounded_event": event,
    }, True)


def _execute_bounded_callback(
    implementation: Callable[..., dict[str, Any]],
    *,
    expected_implementation_digest: str,
    params: dict[str, Any],
    deadline_monotonic: float,
    authority_check: Callable[[], bool],
    max_output_bytes: int,
    max_memory_mb: int,
) -> tuple[dict[str, Any], bool]:
    """Execute one exact adapter with parent-owned hard authority/deadline checks."""
    if os.name != "posix" or "spawn" not in multiprocessing.get_all_start_methods():
        return _bounded_event(
            "WORKER_ERROR", "bounded_adapter_execution_unavailable_on_host", "environment"
        )
    if type(deadline_monotonic) not in {int, float} or type(deadline_monotonic) is bool:
        raise ValueError("deadline_monotonic must be a finite positive number")
    if deadline_monotonic != deadline_monotonic or deadline_monotonic in {float("inf"), float("-inf")} \
            or deadline_monotonic <= 0:
        raise ValueError("deadline_monotonic must be a finite positive number")
    if type(max_output_bytes) is not int or type(max_output_bytes) is bool or max_output_bytes < 1:
        raise ValueError("max_output_bytes must be a positive integer")
    if type(max_memory_mb) is not int or type(max_memory_mb) is bool or max_memory_mb < 1:
        raise ValueError("max_memory_mb must be a positive integer")
    if not callable(authority_check):
        raise ValueError("authority_check must be callable")

    try:
        if authority_check() is not True:
            return _bounded_event(
                "AUTHORITY_REVOKED", "execution_authority_revoked", "cancellation"
            )
    except Exception as exc:
        return _bounded_event(
            "AUTHORITY_CHECK_FAILED",
            f"execution_authority_check_failed: {type(exc).__name__}: {exc}",
            "environment",
        )
    if time.monotonic() >= deadline_monotonic:
        return _bounded_event("DEADLINE", "adapter_deadline_exceeded", "budget")

    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=True)
    process = context.Process(
        target=_bounded_callback_worker,
        args=(
            implementation,
            expected_implementation_digest,
            params,
            child,
            max_output_bytes,
            max_memory_mb,
        ),
        daemon=False,
    )
    try:
        process.start()
    except Exception as exc:
        parent.close()
        child.close()
        return _bounded_event(
            "WORKER_ERROR",
            f"bounded_adapter_start_failed: {type(exc).__name__}: {exc}",
            "environment",
        )
    child.close()
    ready = False
    try:
        while True:
            try:
                authority_active = authority_check() is True
            except Exception as exc:
                return _bounded_event(
                    "AUTHORITY_CHECK_FAILED",
                    f"execution_authority_check_failed: {type(exc).__name__}: {exc}",
                    "environment",
                )
            if not authority_active:
                return _bounded_event(
                    "AUTHORITY_REVOKED", "execution_authority_revoked", "cancellation"
                )
            remaining = deadline_monotonic - time.monotonic()
            if remaining <= 0:
                return _bounded_event("DEADLINE", "adapter_deadline_exceeded", "budget")
            if parent.poll(min(0.01, remaining)):
                try:
                    envelope = json.loads(parent.recv_bytes().decode("utf-8"))
                except (EOFError, UnicodeDecodeError, json.JSONDecodeError):
                    return _bounded_event(
                        "WORKER_ERROR", "bounded_adapter_protocol_failure", "environment"
                    )
                kind = envelope.get("kind")
                if kind == "ready" and not ready:
                    ready = True
                    try:
                        if authority_check() is not True:
                            return _bounded_event(
                                "AUTHORITY_REVOKED", "execution_authority_revoked", "cancellation"
                            )
                    except Exception as exc:
                        return _bounded_event(
                            "AUTHORITY_CHECK_FAILED",
                            f"execution_authority_check_failed: {type(exc).__name__}: {exc}",
                            "environment",
                        )
                    if time.monotonic() >= deadline_monotonic:
                        return _bounded_event("DEADLINE", "adapter_deadline_exceeded", "budget")
                    try:
                        parent.send_bytes(b"execute")
                    except OSError:
                        return _bounded_event(
                            "WORKER_ERROR", "bounded_adapter_protocol_failure", "environment"
                        )
                    continue
                if kind == "result" and ready:
                    try:
                        if authority_check() is not True:
                            return _bounded_event(
                                "AUTHORITY_REVOKED", "execution_authority_revoked", "cancellation"
                            )
                    except Exception as exc:
                        return _bounded_event(
                            "AUTHORITY_CHECK_FAILED",
                            f"execution_authority_check_failed: {type(exc).__name__}: {exc}",
                            "environment",
                        )
                    if time.monotonic() >= deadline_monotonic:
                        return _bounded_event("DEADLINE", "adapter_deadline_exceeded", "budget")
                    try:
                        decoded = json.loads(envelope["result_json"])
                    except (KeyError, TypeError, json.JSONDecodeError):
                        return _bounded_event(
                            "WORKER_ERROR", "bounded_adapter_result_decode_failed", "structural"
                        )
                    if type(decoded) is not dict:
                        return _bounded_event(
                            "WORKER_ERROR", "bounded_adapter_result_must_be_object", "structural"
                        )
                    # A callback cannot forge parent-owned lifecycle/control events.
                    decoded.pop("_aura_bounded_event", None)
                    return decoded, False
                if kind == "callback_error":
                    return ({
                        "ok": False,
                        "error": (
                            f"adapter_callback_failed: {envelope.get('error_type', 'Exception')}: "
                            f"{envelope.get('error', '')}"
                        ),
                        "failure_class": "environment",
                    }, True)
                if kind == "result_error":
                    return ({
                        "ok": False,
                        "error": envelope.get("error", "adapter_result_invalid"),
                        "failure_class": envelope.get("failure_class", "structural"),
                    }, True)
                if kind == "worker_error":
                    return _bounded_event(
                        "WORKER_ERROR",
                        envelope.get("error", "bounded_adapter_worker_error"),
                        envelope.get("failure_class", "environment"),
                    )
                if kind == "base_exception":
                    # Child callback exception names/text are diagnostics only. They
                    # must never select a parent-process control-flow exception.
                    error_type = str(envelope.get("error_type", "BaseException"))[:128]
                    message = str(envelope.get("error", ""))[:2048]
                    return _bounded_event(
                        "WORKER_ERROR",
                        f"bounded_adapter_worker_interruption: {error_type}: {message}",
                        "environment",
                    )
                return _bounded_event(
                    "WORKER_ERROR", "bounded_adapter_protocol_failure", "environment"
                )
            if not process.is_alive():
                return _bounded_event(
                    "WORKER_ERROR", "bounded_adapter_worker_exited_without_result", "environment"
                )
    finally:
        _kill_bounded_process_group(process)
        parent.close()


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
        if self.identity_version != ADAPTER_IDENTITY_VERSION:
            raise ValueError("invalid identity_version")
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

    def execute(
        self,
        adapter_id: str,
        *,
        params: dict[str, Any] | None = None,
        lease_active: bool = True,
        deadline_monotonic: float | None = None,
        authority_check: Callable[[], bool] | None = None,
        max_output_bytes: int = 4_000_000,
        max_memory_mb: int = 512,
    ) -> dict[str, Any]:
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

        trusted_failure = False
        if deadline_monotonic is None:
            # Historical/V1-compatible path: no new process boundary is imposed on
            # callers that did not opt into the V2 bounded execution contract.
            try:
                result = impl(**params)
            except Exception as exc:
                result = {
                    "ok": False,
                    "error": f"adapter_callback_failed: {type(exc).__name__}: {exc}",
                    "failure_class": "environment",
                }
                trusted_failure = True
        else:
            if authority_check is None:
                raise ValueError("authority_check is required for bounded adapter execution")
            result, trusted_failure = _execute_bounded_callback(
                impl,
                expected_implementation_digest=meta.implementation_digest,
                params=params,
                deadline_monotonic=deadline_monotonic,
                authority_check=authority_check,
                max_output_bytes=max_output_bytes,
                max_memory_mb=max_memory_mb,
            )

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
        if not trusted_failure:
            # Callback-controlled text cannot select failure attribution or forge
            # the registry/runtime's private lifecycle-control channel.
            detached.pop("_aura_bounded_event", None)
            if detached["ok"] is False:
                detached["failure_class"] = "local"
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
