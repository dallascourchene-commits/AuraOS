"""Policy-bound, backend-neutral inference membrane for Aura.

This module deliberately does not own source slicing, model/provider credentials,
patch authority, worker liveness, or Human/Gate disposition.  It consumes an
already-bounded context slice and an exact model-policy reference, then routes
only through injected callbacks that satisfy that policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

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


def _canonical_digest(value: Any) -> str:
    body = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return _sha256_bytes(body.encode("utf-8"))


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
    """Load one exact repository policy reference and fail closed on ambiguity."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.policy_root = (self.repo_root / ".aura" / "model_policies").resolve()

    def _resolve_path(self, policy_ref: str) -> Path:
        ref = str(policy_ref or "").strip().replace("\\", "/")
        if not ref or ref.startswith("/"):
            raise PolicyResolutionError("policy_ref_invalid")
        path = (self.repo_root / ref).resolve()
        try:
            path.relative_to(self.policy_root)
        except ValueError as exc:
            raise PolicyResolutionError("policy_ref_outside_model_policy_root") from exc
        if path.suffix.lower() != ".json":
            raise PolicyResolutionError("policy_ref_must_be_json")
        return path

    def resolve(
        self,
        policy_ref: str,
        *,
        expected_blob_digest: str | None = None,
    ) -> PolicyDecision:
        path = self._resolve_path(policy_ref)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PolicyResolutionError("policy_unreadable") from exc

        blob_digest = _sha256_bytes(raw)
        if expected_blob_digest is not None and blob_digest != str(expected_blob_digest):
            raise PolicyResolutionError("policy_digest_mismatch")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PolicyResolutionError("policy_malformed_json") from exc
        if not isinstance(payload, dict):
            raise PolicyResolutionError("policy_must_be_object")

        unknown = set(payload) - _ALLOWED_POLICY_FIELDS
        missing = _ALLOWED_POLICY_FIELDS - set(payload)
        if missing:
            raise PolicyResolutionError("policy_missing_required_fields")
        if unknown:
            raise PolicyResolutionError("policy_unknown_fields")

        if payload["schema_version"] != POLICY_SCHEMA:
            raise PolicyResolutionError("policy_schema_unknown")
        if payload["kind"] != "model_policy":
            raise PolicyResolutionError("policy_kind_invalid")
        if not isinstance(payload["component_id"], str) or not payload["component_id"].strip():
            raise PolicyResolutionError("policy_component_id_invalid")

        default = payload["default"]
        fallback = payload["fallback"]
        if default not in _BACKEND_FOR_POLICY_TARGET:
            raise PolicyResolutionError("policy_default_unknown")
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
            policy_ref=str(policy_ref).replace("\\", "/"),
            policy_blob_digest=blob_digest,
            schema_version=POLICY_SCHEMA,
            component_id=payload["component_id"].strip(),
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
    """Route one bounded request under an exact current model-policy decision.

    Context is supplied by an injected compiler/owner.  The gateway never opens
    repository source to build context itself.
    """

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        policy_resolver: ModelPolicyResolver | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.policy_resolver = policy_resolver or ModelPolicyResolver(self.repo_root)

    @staticmethod
    def _blocked(
        request: InferenceRequestV1,
        *,
        reason: str,
        policy: PolicyDecision | None = None,
        model_call_count: int = 0,
    ) -> dict[str, Any]:
        receipt = InferenceReceiptV1(
            request_id=request.request_id,
            objective_id=request.objective_id,
            request_digest=_canonical_digest(request.protected_dict()),
            policy_ref=request.policy_ref,
            policy_blob_digest=policy.policy_blob_digest if policy else None,
            policy_currentness=policy.currentness if policy else "UNKNOWN",
            context_slice_digest=request.context_slice_digest,
            selected_backend_id=None,
            selected_backend_class=None,
            backend_artifact_ref=None,
            model_call_count=model_call_count,
            status="BLOCKED_UNKNOWN",
            output_digest=None,
            uncertainty="UNKNOWN",
            reopen_refs=request.reopen_refs,
            blocked_reason=reason,
        )
        return {"ok": False, "status": receipt.status, "receipt": receipt.to_dict(), "output": None}

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
        observed_digest = context.get("context_slice_digest")
        if not isinstance(observed_digest, str) or not observed_digest:
            return None, "context_slice_digest_missing"
        if observed_digest != request.context_slice_digest:
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
            return False, result.get("output"), str(result.get("reason") or "backend_unsatisfied")
        if isinstance(result, Mapping) and "output" in result:
            return True, result["output"], None
        return True, result, None

    def run(
        self,
        request: InferenceRequestV1,
        *,
        context_compiler: Callable[[InferenceRequestV1], Mapping[str, Any]] | None,
        deterministic_backend: BackendAdapter | None = None,
        local_backend: BackendAdapter | None = None,
        external_backend: BackendAdapter | None = None,
    ) -> dict[str, Any]:
        try:
            policy = self.policy_resolver.resolve(
                request.policy_ref,
                expected_blob_digest=request.expected_policy_digest,
            )
        except PolicyResolutionError as exc:
            return self._blocked(request, reason=exc.code)

        context, context_error = self._context_payload(request, context_compiler)
        if context_error:
            return self._blocked(request, reason=context_error, policy=policy)
        assert context is not None

        adapters = {
            "deterministic": deterministic_backend,
            "local_model": local_backend,
            "external": external_backend,
        }
        model_call_count = 0
        escalation = set(request.escalation_evidence)

        targets = [policy.default]
        if policy.fallback != policy.default:
            targets.append(policy.fallback)

        last_reason = "no_eligible_backend"
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

            if backend_class in {"local_model", "external"}:
                if model_call_count >= policy.maximum_model_calls:
                    last_reason = "maximum_model_calls_exhausted"
                    continue
                model_call_count += 1

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
                },
                "effect_state": "CANDIDATE_ONLY",
            }
            satisfied, output, error = self._run_adapter(adapter, payload)
            if not satisfied:
                last_reason = error or "backend_unsatisfied"
                continue

            output_digest = _canonical_digest({"output": output})
            receipt = InferenceReceiptV1(
                request_id=request.request_id,
                objective_id=request.objective_id,
                request_digest=_canonical_digest(request.protected_dict()),
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
]
