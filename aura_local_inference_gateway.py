"""Policy-bound, backend-neutral inference membrane for Aura.

P0 deliberately owns neither source slicing nor provider/runtime authority. It
binds an already-bounded context to Aura's existing route-component registry,
requires independent capability validation before any model callback, revalidates
policy immediately before effect, and emits candidate-only receipts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from aura_route_capsule_registry import load_registry_component

GATEWAY_VERSION = "AURA_LOCAL_INFERENCE_GATEWAY_V1"
POLICY_SCHEMA = "AURA_MODEL_POLICY_V1"

_BACKEND_FOR_POLICY_TARGET = {
    "no_model": "deterministic",
    "local_model": "local_model",
    "external_model": "external",
}
_ALLOWED_POLICY_FIELDS = {
    "schema_version",
    "component_id",
    "kind",
    "default",
    "fallback",
    "external_allowed",
    "maximum_model_calls",
    "escalation_requires",
}


class PolicyResolutionError(ValueError):
    """Fail-closed policy resolution error with a stable machine code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    body = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return body.encode("utf-8")


def _canonical_digest(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def canonical_context_digest(context_payload: Mapping[str, Any]) -> str:
    """Digest protected context content, excluding its self-reported digest label."""
    protected = {
        str(key): value
        for key, value in context_payload.items()
        if str(key) != "context_slice_digest"
    }
    return _canonical_digest(protected)


def _string_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise PolicyResolutionError(f"{field_name}_must_be_list")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PolicyResolutionError(f"{field_name}_contains_invalid_item")
        item = item.strip()
        if item in seen:
            raise PolicyResolutionError(f"{field_name}_contains_duplicate")
        seen.add(item)
        result.append(item)
    return tuple(result)


@dataclass(frozen=True)
class PolicyDecision:
    policy_ref: str
    policy_blob_digest: str
    schema_version: str
    component_id: str
    default: str
    fallback: str
    external_allowed: bool
    maximum_model_calls: int
    escalation_requirements: tuple[str, ...]
    allowed_backend_classes: tuple[str, ...]
    currentness: str = "CURRENT_AT_RESOLUTION"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["escalation_requirements"] = list(self.escalation_requirements)
        result["allowed_backend_classes"] = list(self.allowed_backend_classes)
        return result


class ModelPolicyResolver:
    """Resolve model policy through Aura's existing route-component registry."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()

    def resolve(
        self,
        policy_ref: str,
        *,
        expected_blob_digest: str | None = None,
    ) -> PolicyDecision:
        try:
            component = load_registry_component(
                self.repo_root,
                policy_ref,
                field_name="model_policy_ref",
            )
        except FileNotFoundError as exc:
            raise PolicyResolutionError("policy_unreadable") from exc
        except (TypeError, ValueError, OSError) as exc:
            message = str(exc).casefold()
            if (
                "symlink" in message
                or "escape" in message
                or "repository-relative" in message
                or "unsafe path" in message
            ):
                code = "policy_ref_unsafe"
            else:
                code = "policy_registry_resolution_failed"
            raise PolicyResolutionError(code) from exc

        digest = component.digest
        if expected_blob_digest is not None and digest != str(expected_blob_digest):
            raise PolicyResolutionError("policy_digest_mismatch")

        payload = component.payload
        unknown = set(payload) - _ALLOWED_POLICY_FIELDS
        missing = _ALLOWED_POLICY_FIELDS - set(payload)
        if missing:
            raise PolicyResolutionError("policy_missing_required_fields")
        if unknown:
            raise PolicyResolutionError("policy_unknown_fields")

        if component.schema_version != POLICY_SCHEMA:
            raise PolicyResolutionError("policy_schema_unknown")
        if component.kind != "model_policy":
            raise PolicyResolutionError("policy_kind_invalid")
        if not isinstance(payload["component_id"], str) or not payload["component_id"].strip():
            raise PolicyResolutionError("policy_component_id_invalid")

        default = payload["default"]
        fallback = payload["fallback"]
        if not isinstance(default, str):
            raise PolicyResolutionError("policy_default_must_be_string")
        if default not in _BACKEND_FOR_POLICY_TARGET:
            raise PolicyResolutionError("policy_default_unknown")
        if not isinstance(fallback, str):
            raise PolicyResolutionError("policy_fallback_must_be_string")
        if fallback not in _BACKEND_FOR_POLICY_TARGET:
            raise PolicyResolutionError("policy_fallback_unknown")

        external_allowed = payload["external_allowed"]
        if not isinstance(external_allowed, bool):
            raise PolicyResolutionError("policy_external_allowed_must_be_bool")

        maximum_model_calls = payload["maximum_model_calls"]
        if (
            isinstance(maximum_model_calls, bool)
            or not isinstance(maximum_model_calls, int)
            or maximum_model_calls < 0
        ):
            raise PolicyResolutionError("policy_maximum_model_calls_invalid")

        escalation_requirements = _string_tuple(
            payload["escalation_requires"],
            field_name="policy_escalation_requires",
        )

        backend_classes: list[str] = []
        for target in (default, fallback):
            backend_class = _BACKEND_FOR_POLICY_TARGET[target]
            if backend_class == "external" and not external_allowed:
                continue
            if backend_class not in backend_classes:
                backend_classes.append(backend_class)
        if external_allowed and "external" not in backend_classes:
            backend_classes.append("external")

        return PolicyDecision(
            policy_ref=component.relative_path,
            policy_blob_digest=digest,
            schema_version=POLICY_SCHEMA,
            component_id=component.component_id,
            default=default,
            fallback=fallback,
            external_allowed=external_allowed,
            maximum_model_calls=maximum_model_calls,
            escalation_requirements=escalation_requirements,
            allowed_backend_classes=tuple(backend_classes),
        )


@dataclass(frozen=True)
class InferenceRequestV1:
    request_id: str
    objective_id: str
    policy_ref: str
    context_slice_digest: str
    source_refs: tuple[str, ...] = ()
    currentness_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    privacy_refs: tuple[str, ...] = ()
    reopen_refs: tuple[str, ...] = ()
    expected_policy_digest: str | None = None
    requested_backend_label: str | None = None
    escalation_evidence: tuple[str, ...] = ()

    def protected_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "objective_id": self.objective_id,
            "policy_ref": self.policy_ref,
            "context_slice_digest": self.context_slice_digest,
            "source_refs": list(self.source_refs),
            "currentness_refs": list(self.currentness_refs),
            "authority_refs": list(self.authority_refs),
            "privacy_refs": list(self.privacy_refs),
            "reopen_refs": list(self.reopen_refs),
            "expected_policy_digest": self.expected_policy_digest,
            "requested_backend_label": self.requested_backend_label,
            "escalation_evidence": list(self.escalation_evidence),
        }


@dataclass(frozen=True)
class BackendAdapter:
    backend_id: str
    backend_class: str
    callback: Callable[[Mapping[str, Any]], Any]
    available: bool = True
    network_required: bool = False
    artifact_ref: str | None = None
    capability_ref: str | None = None


@dataclass(frozen=True)
class InferenceReceiptV1:
    request_id: str
    objective_id: str
    request_digest: str
    policy_ref: str
    policy_blob_digest: str | None
    policy_currentness: str
    context_slice_digest: str
    selected_backend_id: str | None
    selected_backend_class: str | None
    backend_artifact_ref: str | None
    model_call_count: int
    status: str
    output_digest: str | None
    uncertainty: str | None
    effect_state: str = "CANDIDATE_ONLY"
    measurements: Mapping[str, Any] = field(
        default_factory=lambda: {
            "latency_ms": "UNKNOWN",
            "input_tokens": "UNKNOWN",
            "output_tokens": "UNKNOWN",
            "provider_cost": "UNKNOWN",
        }
    )
    reopen_refs: tuple[str, ...] = ()
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reopen_refs"] = list(self.reopen_refs)
        return result


class AuraLocalInferenceGateway:
    """Route bounded requests under exact policy and verified capability bindings."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        policy_resolver: ModelPolicyResolver | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.policy_resolver = policy_resolver or ModelPolicyResolver(self.repo_root)
        self._model_call_usage: dict[tuple[str, str, str], int] = {}

    @staticmethod
    def _safe_request_digest(request: InferenceRequestV1) -> str:
        try:
            return _canonical_digest(request.protected_dict())
        except (TypeError, ValueError, RecursionError):
            return "UNAVAILABLE_NONCANONICAL_REQUEST"

    @classmethod
    def _blocked(
        cls,
        request: InferenceRequestV1,
        *,
        reason: str,
        policy: PolicyDecision | None = None,
        model_call_count: int = 0,
        attempted_backend: BackendAdapter | None = None,
    ) -> dict[str, Any]:
        receipt = InferenceReceiptV1(
            request_id=request.request_id,
            objective_id=request.objective_id,
            request_digest=cls._safe_request_digest(request),
            policy_ref=request.policy_ref,
            policy_blob_digest=policy.policy_blob_digest if policy else None,
            policy_currentness=policy.currentness if policy else "UNKNOWN",
            context_slice_digest=request.context_slice_digest,
            selected_backend_id=attempted_backend.backend_id if attempted_backend else None,
            selected_backend_class=attempted_backend.backend_class if attempted_backend else None,
            backend_artifact_ref=attempted_backend.artifact_ref if attempted_backend else None,
            model_call_count=model_call_count,
            status="BLOCKED_UNKNOWN",
            output_digest=None,
            uncertainty="UNKNOWN",
            reopen_refs=request.reopen_refs,
            blocked_reason=reason,
        )
        return {
            "ok": False,
            "status": receipt.status,
            "receipt": receipt.to_dict(),
            "output": None,
        }

    @staticmethod
    def _context_payload(
        request: InferenceRequestV1,
        context_compiler: Callable[[InferenceRequestV1], Mapping[str, Any]] | None,
    ) -> tuple[Mapping[str, Any] | None, str | None]:
        if context_compiler is None:
            return None, "context_compiler_required"
        try:
            context = context_compiler(request)
        except Exception:
            return None, "context_compiler_failed"
        if not isinstance(context, Mapping):
            return None, "context_compiler_invalid_result"
        claimed = context.get("context_slice_digest")
        if not isinstance(claimed, str) or not claimed:
            return None, "context_slice_digest_missing"
        try:
            observed = canonical_context_digest(context)
        except (TypeError, ValueError, RecursionError):
            return None, "context_not_canonicalizable"
        if claimed != observed:
            return None, "context_claimed_digest_mismatch"
        if observed != request.context_slice_digest:
            return None, "context_slice_digest_mismatch"
        return context, None

    @staticmethod
    def _run_adapter(
        adapter: BackendAdapter,
        payload: Mapping[str, Any],
    ) -> tuple[bool, Any, str | None]:
        if not adapter.available:
            return False, None, "backend_unavailable"
        try:
            result = adapter.callback(payload)
        except Exception:
            return False, None, "backend_call_failed"
        if isinstance(result, Mapping) and result.get("satisfied") is False:
            return (
                False,
                result.get("output"),
                str(result.get("reason") or "backend_unsatisfied"),
            )
        if isinstance(result, Mapping) and "output" in result:
            return True, result["output"], None
        return True, result, None

    def _revalidate_policy(
        self,
        request: InferenceRequestV1,
        policy: PolicyDecision,
    ) -> PolicyDecision | None:
        try:
            rebound = self.policy_resolver.resolve(
                request.policy_ref,
                expected_blob_digest=policy.policy_blob_digest,
            )
        except PolicyResolutionError:
            return None
        if rebound.to_dict() != policy.to_dict():
            return None
        return rebound

    @staticmethod
    def _capability_verified(
        adapter: BackendAdapter,
        policy: PolicyDecision,
        capability_validator: Callable[[BackendAdapter, PolicyDecision], bool] | None,
    ) -> bool:
        if adapter.backend_class == "deterministic":
            return not adapter.network_required
        if capability_validator is None:
            return False
        try:
            return capability_validator(adapter, policy) is True
        except Exception:
            return False

    def run(
        self,
        request: InferenceRequestV1,
        *,
        context_compiler: Callable[[InferenceRequestV1], Mapping[str, Any]] | None,
        deterministic_backend: BackendAdapter | None = None,
        local_backend: BackendAdapter | None = None,
        external_backend: BackendAdapter | None = None,
        capability_validator: Callable[[BackendAdapter, PolicyDecision], bool] | None = None,
    ) -> dict[str, Any]:
        try:
            policy = self.policy_resolver.resolve(
                request.policy_ref,
                expected_blob_digest=request.expected_policy_digest,
            )
        except PolicyResolutionError as exc:
            return self._blocked(request, reason=exc.code)

        request_digest = self._safe_request_digest(request)
        if request_digest.startswith("UNAVAILABLE_"):
            return self._blocked(request, reason="request_not_canonicalizable", policy=policy)

        context, context_error = self._context_payload(request, context_compiler)
        if context_error:
            return self._blocked(request, reason=context_error, policy=policy)
        assert context is not None

        usage_key = (request.request_id, request.objective_id, policy.policy_blob_digest)
        model_call_count = self._model_call_usage.get(usage_key, 0)

        adapters = {
            "deterministic": deterministic_backend,
            "local_model": local_backend,
            "external": external_backend,
        }
        escalation = set(request.escalation_evidence)
        targets = [policy.default]
        if policy.fallback != policy.default:
            targets.append(policy.fallback)

        last_reason = "no_eligible_backend"
        last_attempted: BackendAdapter | None = None
        for index, target in enumerate(targets):
            backend_class = _BACKEND_FOR_POLICY_TARGET[target]

            if backend_class == "external" and not policy.external_allowed:
                last_reason = "external_backend_forbidden_by_policy"
                continue
            if backend_class not in policy.allowed_backend_classes:
                last_reason = "backend_class_forbidden_by_policy"
                continue

            if index > 0 and policy.escalation_requirements:
                missing = set(policy.escalation_requirements) - escalation
                if missing:
                    last_reason = "fallback_escalation_requirements_unsatisfied"
                    continue

            adapter = adapters.get(backend_class)
            if adapter is None or not adapter.available:
                last_reason = "backend_capability_missing"
                continue
            if adapter.backend_class != backend_class:
                last_reason = "backend_capability_class_mismatch"
                continue
            if adapter.network_required and backend_class != "external":
                last_reason = "local_backend_declares_network_requirement"
                continue
            if not self._capability_verified(adapter, policy, capability_validator):
                last_reason = "backend_capability_unverified"
                continue

            if (
                backend_class in {"local_model", "external"}
                and model_call_count >= policy.maximum_model_calls
            ):
                last_reason = "maximum_model_calls_exhausted"
                continue

            rebound = self._revalidate_policy(request, policy)
            if rebound is None:
                return self._blocked(
                    request,
                    reason="policy_digest_mismatch",
                    policy=policy,
                    model_call_count=model_call_count,
                    attempted_backend=adapter,
                )
            policy = rebound
            last_attempted = adapter

            if backend_class in {"local_model", "external"}:
                model_call_count += 1
                self._model_call_usage[usage_key] = model_call_count

            payload = {
                "version": GATEWAY_VERSION,
                "request": request.protected_dict(),
                "context": dict(context),
                "policy": policy.to_dict(),
                "backend": {
                    "backend_id": adapter.backend_id,
                    "backend_class": adapter.backend_class,
                    "network_required": adapter.network_required,
                    "artifact_ref": adapter.artifact_ref,
                    "capability_ref": adapter.capability_ref,
                },
                "effect_state": "CANDIDATE_ONLY",
            }
            satisfied, output, error = self._run_adapter(adapter, payload)
            if not satisfied:
                last_reason = error or "backend_unsatisfied"
                continue

            try:
                output_digest = _canonical_digest({"output": output})
            except (TypeError, ValueError, RecursionError):
                return self._blocked(
                    request,
                    reason="backend_output_not_canonicalizable",
                    policy=policy,
                    model_call_count=model_call_count,
                    attempted_backend=adapter,
                )

            receipt = InferenceReceiptV1(
                request_id=request.request_id,
                objective_id=request.objective_id,
                request_digest=request_digest,
                policy_ref=policy.policy_ref,
                policy_blob_digest=policy.policy_blob_digest,
                policy_currentness=policy.currentness,
                context_slice_digest=request.context_slice_digest,
                selected_backend_id=adapter.backend_id,
                selected_backend_class=adapter.backend_class,
                backend_artifact_ref=adapter.artifact_ref,
                model_call_count=model_call_count,
                status="COMPLETED_CANDIDATE",
                output_digest=output_digest,
                uncertainty=None,
                reopen_refs=request.reopen_refs,
            )
            return {
                "ok": True,
                "status": receipt.status,
                "receipt": receipt.to_dict(),
                "output": output,
            }

        return self._blocked(
            request,
            reason=last_reason,
            policy=policy,
            model_call_count=model_call_count,
            attempted_backend=last_attempted,
        )


__all__ = [
    "AuraLocalInferenceGateway",
    "BackendAdapter",
    "GATEWAY_VERSION",
    "InferenceReceiptV1",
    "InferenceRequestV1",
    "ModelPolicyResolver",
    "POLICY_SCHEMA",
    "PolicyDecision",
    "PolicyResolutionError",
    "canonical_context_digest",
]
