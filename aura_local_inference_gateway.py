"""Policy-bound backend-neutral inference gateway for Aura.

This is a thin membrane around existing Aura owners. It does not read repository
source for model context, choose work decomposition, grant provider permission,
or mutate production state. Callers supply a bounded context compiler and
backend adapters; the gateway binds an exact model policy before any backend can
run and emits deterministic nonauthority receipts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

POLICY_SCHEMA = "AURA_MODEL_POLICY_V1"
REQUEST_SCHEMA = "AURA_LOCAL_INFERENCE_REQUEST_V1"
CONTEXT_SCHEMA = "AURA_LOCAL_INFERENCE_CONTEXT_V1"
CAPABILITY_SCHEMA = "AURA_LOCAL_INFERENCE_BACKEND_CAPABILITY_V1"
RECEIPT_SCHEMA = "AURA_LOCAL_INFERENCE_RECEIPT_V1"

SUPPORTED_POLICY_BACKENDS = {"no_model", "local_model", "external_model"}
BACKEND_CLASS_BY_POLICY_VALUE = {
    "no_model": "no_model",
    "local_model": "local_model",
    "external_model": "external_model",
}
FORBIDDEN_CONTEXT_CLASSES = frozenset({"secrets", "hidden_reasoning", "unrelated_sessions"})
NONAUTHORITY_EFFECT_STATE = "NO_PRODUCTION_MUTATION"


class PolicyResolutionError(ValueError):
    """Raised when an exact model policy cannot be admitted."""


class StalePolicyError(PolicyResolutionError):
    """Raised when an expected policy digest no longer matches."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _require_nonempty_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name}_required")
    return value


def _require_string_tuple(values: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field_name}_must_be_sequence")
    normalized = tuple(_require_nonempty_text(value, field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name}_duplicates_forbidden")
    return normalized


@dataclass(frozen=True)
class PolicyDecision:
    policy_ref: str
    policy_blob_digest: str
    allowed_backend_classes: tuple[str, ...]
    default: str
    fallback: str
    external_allowed: bool
    max_calls: int
    escalation_requirements: tuple[str, ...]
    currentness: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelPolicyResolver:
    """Resolve one exact repository-local model policy and fail closed."""

    _required_keys = frozenset(
        {
            "schema_version",
            "component_id",
            "kind",
            "default",
            "fallback",
            "external_allowed",
            "maximum_model_calls",
            "escalation_requires",
        }
    )

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()

    def resolve(self, policy_ref: str, *, expected_sha256: str | None = None) -> PolicyDecision:
        normalized_ref = self._validate_policy_ref(policy_ref)
        path = (self.repo_root / normalized_ref).resolve()
        try:
            path.relative_to(self.repo_root)
        except ValueError as exc:
            raise PolicyResolutionError("policy_ref_outside_repository") from exc
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PolicyResolutionError("policy_unreadable") from exc
        digest = _sha256_bytes(raw)
        if expected_sha256 is not None and digest != str(expected_sha256):
            raise StalePolicyError("policy_digest_mismatch")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PolicyResolutionError("policy_malformed_json") from exc
        decision = self._validate_payload(payload, normalized_ref, digest)
        if expected_sha256 is None:
            return decision
        return PolicyDecision(**{**decision.to_dict(), "currentness": "EXACT_DIGEST_MATCH"})

    @classmethod
    def _validate_policy_ref(cls, policy_ref: str) -> str:
        ref = _require_nonempty_text(policy_ref, "policy_ref").replace("\\", "/")
        path = Path(ref)
        if path.is_absolute() or ".." in path.parts:
            raise PolicyResolutionError("policy_ref_invalid")
        parts = path.parts
        if len(parts) < 3 or parts[0] != ".aura" or parts[1] != "model_policies":
            raise PolicyResolutionError("policy_ref_wrong_owner")
        return path.as_posix()

    @classmethod
    def _validate_payload(cls, payload: Any, policy_ref: str, digest: str) -> PolicyDecision:
        if not isinstance(payload, dict):
            raise PolicyResolutionError("policy_must_be_object")
        keys = frozenset(payload)
        missing = cls._required_keys - keys
        unknown = keys - cls._required_keys
        if missing:
            raise PolicyResolutionError(f"policy_missing_fields:{','.join(sorted(missing))}")
        if unknown:
            raise PolicyResolutionError(f"policy_unknown_fields:{','.join(sorted(unknown))}")
        if payload["schema_version"] != POLICY_SCHEMA:
            raise PolicyResolutionError("policy_schema_unsupported")
        if payload["kind"] != "model_policy":
            raise PolicyResolutionError("policy_kind_invalid")
        _require_nonempty_text(payload["component_id"], "component_id")
        default = _require_nonempty_text(payload["default"], "default")
        fallback = _require_nonempty_text(payload["fallback"], "fallback")
        if default not in SUPPORTED_POLICY_BACKENDS or fallback not in SUPPORTED_POLICY_BACKENDS:
            raise PolicyResolutionError("policy_backend_class_unsupported")
        external_allowed = payload["external_allowed"]
        if not isinstance(external_allowed, bool):
            raise PolicyResolutionError("external_allowed_must_be_bool")
        max_calls = payload["maximum_model_calls"]
        if isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls < 0:
            raise PolicyResolutionError("maximum_model_calls_invalid")
        requirements = _require_string_tuple(payload["escalation_requires"], "escalation_requires")
        backend_values = (default, fallback)
        if "external_model" in backend_values and not external_allowed:
            raise PolicyResolutionError("external_backend_forbidden_by_policy")
        allowed: list[str] = []
        for value in backend_values:
            backend_class = BACKEND_CLASS_BY_POLICY_VALUE[value]
            if backend_class not in allowed:
                allowed.append(backend_class)
        if external_allowed and "external_model" not in allowed:
            allowed.append("external_model")
        return PolicyDecision(
            policy_ref=policy_ref,
            policy_blob_digest=digest,
            allowed_backend_classes=tuple(allowed),
            default=default,
            fallback=fallback,
            external_allowed=external_allowed,
            max_calls=max_calls,
            escalation_requirements=requirements,
            currentness="OBSERVED_AT_RESOLUTION",
        )


@dataclass(frozen=True)
class InferenceRequestV1:
    request_id: str
    objective: str
    model_policy_ref: str
    expected_policy_sha256: str | None = None
    bound_context_digest: str | None = None
    backend_hint: str | None = None
    coordinate_hint: str | None = None
    required_evidence: tuple[str, ...] = ("source", "currentness", "authority", "privacy")
    required_privacy_exclusions: tuple[str, ...] = ()
    escalation_evidence: tuple[str, ...] = ()

    def protected_dict(self) -> dict[str, Any]:
        return {
            "schema_id": REQUEST_SCHEMA,
            "schema_version": 1,
            "request_id": self.request_id,
            "objective": self.objective,
            "model_policy_ref": self.model_policy_ref,
            "expected_policy_sha256": self.expected_policy_sha256,
            "bound_context_digest": self.bound_context_digest,
            "backend_hint": self.backend_hint,
            "coordinate_hint": self.coordinate_hint,
            "required_evidence": list(self.required_evidence),
            "required_privacy_exclusions": list(self.required_privacy_exclusions),
            "escalation_evidence": list(self.escalation_evidence),
        }

    @property
    def digest(self) -> str:
        return _sha256_json(self.protected_dict())


@dataclass(frozen=True)
class CompiledContextV1:
    source_refs: tuple[str, ...]
    currentness_refs: tuple[str, ...]
    authority_refs: tuple[str, ...]
    privacy_refs: tuple[str, ...]
    reopen_refs: tuple[str, ...]
    privacy_exclusions: tuple[str, ...]
    payload: Mapping[str, Any] = field(default_factory=dict)

    def protected_dict(self) -> dict[str, Any]:
        return {
            "schema_id": CONTEXT_SCHEMA,
            "schema_version": 1,
            "source_refs": list(self.source_refs),
            "currentness_refs": list(self.currentness_refs),
            "authority_refs": list(self.authority_refs),
            "privacy_refs": list(self.privacy_refs),
            "reopen_refs": list(self.reopen_refs),
            "privacy_exclusions": list(self.privacy_exclusions),
            "payload": dict(self.payload),
        }

    @property
    def digest(self) -> str:
        return _sha256_json(self.protected_dict())


@dataclass(frozen=True)
class BackendCapabilityV1:
    backend_id: str
    backend_class: str
    available: bool
    network_required: bool = False
    artifact_ref: str | None = None
    resource_state: Mapping[str, Any] = field(default_factory=dict)

    def protected_dict(self) -> dict[str, Any]:
        return {
            "schema_id": CAPABILITY_SCHEMA,
            "schema_version": 1,
            "backend_id": self.backend_id,
            "backend_class": self.backend_class,
            "available": self.available,
            "network_required": self.network_required,
            "artifact_ref": self.artifact_ref,
            "resource_state": dict(self.resource_state),
        }

    @property
    def digest(self) -> str:
        return _sha256_json(self.protected_dict())


@dataclass(frozen=True)
class BackendResultV1:
    satisfied: bool
    output: str = ""
    uncertainty: tuple[str, ...] = ()
    counterevidence: tuple[str, ...] = ()
    measurements: Mapping[str, Any] = field(default_factory=dict)
    measurement_class: str = "UNKNOWN"


class BackendAdapter(Protocol):
    capability: BackendCapabilityV1
    counts_as_model_call: bool

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        ...


class DeterministicBackend:
    counts_as_model_call = False

    def __init__(
        self,
        callback: Callable[[InferenceRequestV1, CompiledContextV1], str | None],
        *,
        backend_id: str = "deterministic",
    ) -> None:
        self.callback = callback
        self.capability = BackendCapabilityV1(
            backend_id=backend_id,
            backend_class="no_model",
            available=True,
            resource_state={"class": "deterministic", "state": "AVAILABLE"},
        )

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        output = self.callback(request, context)
        if output is None:
            return BackendResultV1(
                satisfied=False,
                uncertainty=("deterministic_path_insufficient",),
                measurement_class="MEASURED_LOCAL",
            )
        return BackendResultV1(satisfied=True, output=str(output), measurement_class="MEASURED_LOCAL")


class FakeLocalBackend:
    """Test-only local-model class adapter; never installs or calls a real model."""

    counts_as_model_call = True

    def __init__(
        self,
        callback: Callable[[InferenceRequestV1, CompiledContextV1], str],
        *,
        backend_id: str = "fake-local",
        available: bool = True,
    ) -> None:
        self.callback = callback
        self.call_count = 0
        self.capability = BackendCapabilityV1(
            backend_id=backend_id,
            backend_class="local_model",
            available=bool(available),
            artifact_ref="fake://local-test-backend",
            resource_state={"cpu": "UNKNOWN", "ram": "UNKNOWN", "gpu": "UNKNOWN", "vram": "UNKNOWN"},
        )

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        self.call_count += 1
        return BackendResultV1(
            satisfied=True,
            output=str(self.callback(request, context)),
            measurements={"model_calls": 1},
            measurement_class="MEASURED_FAKE",
        )


class ExternalBackendForTest:
    """Negative-test adapter proving external labels cannot bypass policy."""

    counts_as_model_call = True

    def __init__(self, *, backend_id: str = "external-test") -> None:
        self.call_count = 0
        self.capability = BackendCapabilityV1(
            backend_id=backend_id,
            backend_class="external_model",
            available=True,
            network_required=True,
            artifact_ref="test://external",
            resource_state={"network": "AVAILABLE"},
        )

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        self.call_count += 1
        return BackendResultV1(satisfied=True, output="external", measurement_class="TEST_ONLY")


def request_from_route_capsule(
    route_capsule: Mapping[str, Any],
    *,
    request_id: str,
    objective: str,
    **kwargs: Any,
) -> InferenceRequestV1:
    policy_ref = route_capsule.get("model_policy_ref")
    if not isinstance(policy_ref, str) or not policy_ref:
        raise ValueError("route_capsule_model_policy_ref_required")
    return InferenceRequestV1(
        request_id=_require_nonempty_text(request_id, "request_id"),
        objective=_require_nonempty_text(objective, "objective"),
        model_policy_ref=policy_ref,
        **kwargs,
    )


class LocalInferenceGateway:
    """Bind policy -> bounded context -> eligible backend -> nonauthority receipt."""

    def __init__(
        self,
        *,
        policy_resolver: ModelPolicyResolver,
        context_compiler: Callable[[InferenceRequestV1], CompiledContextV1],
        backends: tuple[BackendAdapter, ...] | list[BackendAdapter],
    ) -> None:
        self.policy_resolver = policy_resolver
        self.context_compiler = context_compiler
        self.backends = tuple(backends)

    def run(self, request: InferenceRequestV1) -> dict[str, Any]:
        try:
            self._validate_request(request)
            policy = self.policy_resolver.resolve(
                request.model_policy_ref,
                expected_sha256=request.expected_policy_sha256,
            )
        except StalePolicyError:
            return self._blocked_receipt(request, "BLOCKED_STALE_POLICY")
        except (PolicyResolutionError, ValueError) as exc:
            return self._blocked_receipt(request, "BLOCKED_POLICY_INVALID", details={"error": str(exc)})

        if request.backend_hint == "external_model" and not policy.external_allowed:
            return self._blocked_receipt(request, "BLOCKED_POLICY_EXTERNAL_FORBIDDEN", policy=policy)

        try:
            context = self.context_compiler(request)
        except Exception as exc:  # context-owner failure never authorizes broader hydration
            return self._blocked_receipt(
                request,
                "BLOCKED_CONTEXT_UNAVAILABLE",
                policy=policy,
                details={"error_type": type(exc).__name__},
            )
        if not isinstance(context, CompiledContextV1):
            return self._blocked_receipt(request, "BLOCKED_CONTEXT_SCHEMA", policy=policy)
        context_problem = self._context_problem(request, context)
        if context_problem:
            return self._blocked_receipt(request, context_problem, policy=policy, context=context)

        attempts: list[dict[str, Any]] = []
        model_calls = 0
        for backend_class in self._ordered_backend_classes(policy):
            if backend_class == "external_model" and not policy.external_allowed:
                continue
            adapter = self._find_backend(backend_class)
            if adapter is None:
                attempts.append({"backend_class": backend_class, "status": "UNAVAILABLE", "capability_digest": None})
                continue
            capability = adapter.capability
            if not capability.available:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "backend_id": capability.backend_id,
                        "status": "UNAVAILABLE",
                        "capability_digest": capability.digest,
                    }
                )
                continue
            if backend_class == "local_model" and capability.network_required:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "backend_id": capability.backend_id,
                        "status": "BLOCKED_LOCAL_BACKEND_REQUIRES_NETWORK",
                        "capability_digest": capability.digest,
                    }
                )
                continue
            if backend_class == "external_model":
                missing = set(policy.escalation_requirements) - set(request.escalation_evidence)
                if missing:
                    attempts.append(
                        {
                            "backend_class": backend_class,
                            "backend_id": capability.backend_id,
                            "status": "BLOCKED_ESCALATION_EVIDENCE",
                            "missing": sorted(missing),
                            "capability_digest": capability.digest,
                        }
                    )
                    continue
            if adapter.counts_as_model_call:
                if model_calls >= policy.max_calls:
                    attempts.append(
                        {
                            "backend_class": backend_class,
                            "backend_id": capability.backend_id,
                            "status": "BLOCKED_MODEL_CALL_BUDGET",
                            "capability_digest": capability.digest,
                        }
                    )
                    continue
                model_calls += 1
            try:
                result = adapter.invoke(request, context)
            except Exception as exc:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "backend_id": capability.backend_id,
                        "status": "FAILED_TYPED",
                        "error_type": type(exc).__name__,
                        "capability_digest": capability.digest,
                    }
                )
                continue
            attempts.append(
                {
                    "backend_class": backend_class,
                    "backend_id": capability.backend_id,
                    "status": "SATISFIED" if result.satisfied else "INSUFFICIENT",
                    "capability_digest": capability.digest,
                    "measurement_class": result.measurement_class,
                    "measurements": dict(result.measurements),
                }
            )
            if result.satisfied:
                return self._success_receipt(
                    request=request,
                    policy=policy,
                    context=context,
                    capability=capability,
                    result=result,
                    attempts=attempts,
                    model_calls=model_calls,
                )

        return self._blocked_receipt(
            request,
            "BLOCKED_NO_ELIGIBLE_BACKEND",
            policy=policy,
            context=context,
            details={"attempts": attempts, "model_calls": model_calls},
        )

    @staticmethod
    def _validate_request(request: InferenceRequestV1) -> None:
        _require_nonempty_text(request.request_id, "request_id")
        _require_nonempty_text(request.objective, "objective")
        _require_nonempty_text(request.model_policy_ref, "model_policy_ref")
        _require_string_tuple(request.required_evidence, "required_evidence")
        _require_string_tuple(request.required_privacy_exclusions, "required_privacy_exclusions")
        _require_string_tuple(request.escalation_evidence, "escalation_evidence")
        if not set(request.required_evidence) <= {"source", "currentness", "authority", "privacy"}:
            raise ValueError("required_evidence_unknown")
        if request.backend_hint is not None and request.backend_hint not in SUPPORTED_POLICY_BACKENDS:
            raise ValueError("backend_hint_unknown")

    @staticmethod
    def _context_problem(request: InferenceRequestV1, context: CompiledContextV1) -> str | None:
        evidence = {
            "source": context.source_refs,
            "currentness": context.currentness_refs,
            "authority": context.authority_refs,
            "privacy": context.privacy_refs,
        }
        for key in request.required_evidence:
            if not evidence[key]:
                return "BLOCKED_REQUIRED_EVIDENCE_UNRESOLVED"
        if request.bound_context_digest is not None and request.bound_context_digest != context.digest:
            return "BLOCKED_CONTEXT_DIGEST_MISMATCH"
        if not set(request.required_privacy_exclusions) <= set(context.privacy_exclusions):
            return "BLOCKED_PRIVACY_EXCLUSIONS_INCOMPLETE"
        included_classes = context.payload.get("included_classes", [])
        if not isinstance(included_classes, (list, tuple, set)):
            return "BLOCKED_CONTEXT_SCHEMA"
        if FORBIDDEN_CONTEXT_CLASSES & set(included_classes):
            return "BLOCKED_FORBIDDEN_CONTEXT_CLASS"
        return None

    def _find_backend(self, backend_class: str) -> BackendAdapter | None:
        matches = [backend for backend in self.backends if backend.capability.backend_class == backend_class]
        if len(matches) != 1:
            return None
        return matches[0]

    @staticmethod
    def _ordered_backend_classes(policy: PolicyDecision) -> tuple[str, ...]:
        ordered: list[str] = []
        for policy_value in (policy.default, policy.fallback):
            backend_class = BACKEND_CLASS_BY_POLICY_VALUE[policy_value]
            if backend_class not in ordered:
                ordered.append(backend_class)
        if policy.external_allowed and "external_model" not in ordered:
            ordered.append("external_model")
        return tuple(ordered)

    @staticmethod
    def _base_receipt(
        request: InferenceRequestV1,
        *,
        status: str,
        policy: PolicyDecision | None,
        context: CompiledContextV1 | None,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        receipt = {
            "schema_id": RECEIPT_SCHEMA,
            "schema_version": 1,
            "status": status,
            "request_digest": request.digest,
            "request_id": request.request_id,
            "policy_ref": policy.policy_ref if policy else request.model_policy_ref,
            "policy_digest": policy.policy_blob_digest if policy else request.expected_policy_sha256,
            "policy_currentness": policy.currentness if policy else "UNKNOWN",
            "context_digest": context.digest if context else request.bound_context_digest,
            "context_reopen_refs": list(context.reopen_refs) if context else [],
            "backend": None,
            "backend_capability_digest": None,
            "model_calls": 0,
            "output_digest": None,
            "uncertainty": [],
            "counterevidence": [],
            "measurement_class": "UNKNOWN",
            "measurements": {},
            "effect_state": NONAUTHORITY_EFFECT_STATE,
            "production_mutation": False,
            "runtime_authority": False,
            "provider_authority": False,
            "human_gate": False,
            "details": dict(details or {}),
        }
        receipt["receipt_digest"] = _sha256_json(receipt)
        return receipt

    def _blocked_receipt(
        self,
        request: InferenceRequestV1,
        status: str,
        *,
        policy: PolicyDecision | None = None,
        context: CompiledContextV1 | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._base_receipt(request, status=status, policy=policy, context=context, details=details)

    @staticmethod
    def _success_receipt(
        *,
        request: InferenceRequestV1,
        policy: PolicyDecision,
        context: CompiledContextV1,
        capability: BackendCapabilityV1,
        result: BackendResultV1,
        attempts: list[dict[str, Any]],
        model_calls: int,
    ) -> dict[str, Any]:
        receipt = {
            "schema_id": RECEIPT_SCHEMA,
            "schema_version": 1,
            "status": "SATISFIED",
            "request_digest": request.digest,
            "request_id": request.request_id,
            "policy_ref": policy.policy_ref,
            "policy_digest": policy.policy_blob_digest,
            "policy_currentness": policy.currentness,
            "context_digest": context.digest,
            "context_reopen_refs": list(context.reopen_refs),
            "backend": {
                "backend_id": capability.backend_id,
                "backend_class": capability.backend_class,
                "artifact_ref": capability.artifact_ref,
                "network_required": capability.network_required,
            },
            "backend_capability_digest": capability.digest,
            "model_calls": model_calls,
            "output_digest": _sha256_bytes(result.output.encode("utf-8")),
            "output": result.output,
            "uncertainty": list(result.uncertainty),
            "counterevidence": list(result.counterevidence),
            "measurement_class": result.measurement_class,
            "measurements": dict(result.measurements),
            "attempts": list(attempts),
            "effect_state": NONAUTHORITY_EFFECT_STATE,
            "production_mutation": False,
            "runtime_authority": False,
            "provider_authority": False,
            "human_gate": False,
            "details": {},
        }
        receipt["receipt_digest"] = _sha256_json(receipt)
        return receipt
