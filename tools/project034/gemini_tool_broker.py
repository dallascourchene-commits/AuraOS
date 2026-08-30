from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, MutableMapping, Optional

from gemini_webchat_endpoint import (
    ArenaTurnEnvelopeV1,
    AuraToolRequestV1,
    AuraToolResultV1,
    BridgeRefusal,
    EFFECT_RANK,
    admit_tool_request,
    canonical_json,
    sha256_text,
)


TOOL_ADMISSION_VERSION = "AURA_GEMINI_TOOL_ADMISSION_V1"

_FORBIDDEN_CALLER_CONTROL_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "access_token",
        "refresh_token",
        "cookie",
        "cookies",
        "password",
        "secret",
        "credential",
        "credentials",
        "executor",
        "executor_id",
        "effect_class",
        "authority_ref",
        "fence_ref",
        "fencing_token",
        "claim_lease",
        "currentness_hash",
        "arena_head",
        "admission",
        "admission_ref",
    }
)

_SENSITIVE_RESULT_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "access_token",
        "refresh_token",
        "cookie",
        "cookies",
        "password",
        "secret",
        "credential",
        "credentials",
        "fencing_token",
    }
)


@dataclass(frozen=True)
class ToolRouteV1:
    tool_id: str
    executor_id: str
    capability_ref: str
    effect_class: str
    max_result_bytes: int = 65536

    def validate(self) -> None:
        if not self.tool_id.strip() or not self.executor_id.strip() or not self.capability_ref.strip():
            raise BridgeRefusal("TOOL_ROUTE_INCOMPLETE", self.tool_id)
        if self.effect_class not in EFFECT_RANK:
            raise BridgeRefusal("UNKNOWN_EFFECT_CLASS", self.effect_class)
        if self.max_result_bytes < 1 or self.max_result_bytes > 1_000_000:
            raise BridgeRefusal("TOOL_RESULT_BOUND_INVALID", str(self.max_result_bytes))


@dataclass(frozen=True)
class ToolAdmissionV1:
    admission_ref: str
    request_digest: str
    arena_sid: str
    arena_head: str
    currentness_hash: str
    capsule_id: str
    turn_id: str
    claim_id: str
    claim_lease: str
    tool_id: str
    executor_id: str
    capability_ref: str
    effect_class: str
    authority_ref: str
    fence_ref: str
    authority_decision: str = "ALLOW"
    currentness_decision: str = "CURRENT"
    effect_decision: str = "ALLOW"
    admission_version: str = TOOL_ADMISSION_VERSION

    def validate(
        self,
        envelope: ArenaTurnEnvelopeV1,
        request: AuraToolRequestV1,
        route: ToolRouteV1,
        request_digest: str,
        *,
        current_arena_head: str,
        currentness_hash: str,
    ) -> None:
        required = {
            "admission_ref": self.admission_ref,
            "authority_ref": self.authority_ref,
            "fence_ref": self.fence_ref,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise BridgeRefusal("TOOL_ADMISSION_INCOMPLETE", ",".join(missing))
        expected = {
            "admission_version": (self.admission_version, TOOL_ADMISSION_VERSION),
            "request_digest": (self.request_digest, request_digest),
            "arena_sid": (self.arena_sid, envelope.arena_sid),
            "arena_head": (self.arena_head, current_arena_head),
            "currentness_hash": (self.currentness_hash, currentness_hash),
            "capsule_id": (self.capsule_id, envelope.capsule_id),
            "turn_id": (self.turn_id, envelope.turn_id),
            "claim_id": (self.claim_id, envelope.claim_id),
            "claim_lease": (self.claim_lease, envelope.claim_lease),
            "tool_id": (self.tool_id, request.tool_id),
            "executor_id": (self.executor_id, route.executor_id),
            "capability_ref": (self.capability_ref, route.capability_ref),
            "effect_class": (self.effect_class, route.effect_class),
        }
        mismatch = [name for name, (actual, wanted) in expected.items() if actual != wanted]
        if mismatch:
            raise BridgeRefusal("TOOL_ADMISSION_BINDING_MISMATCH", ",".join(mismatch))
        if self.authority_decision != "ALLOW":
            raise BridgeRefusal("TOOL_AUTHORITY_NOT_ALLOWED", self.authority_decision)
        if self.currentness_decision != "CURRENT":
            raise BridgeRefusal("TOOL_ADMISSION_NOT_CURRENT", self.currentness_decision)
        if self.effect_decision != "ALLOW":
            raise BridgeRefusal("TOOL_EFFECT_NOT_ALLOWED", self.effect_decision)


@dataclass(frozen=True)
class ToolBrokerReceiptV1:
    request_id: str
    request_digest: str
    admission_ref: str
    admission_digest: str
    executor_id: str
    capability_ref: str
    effect_class: str
    result_digest: str
    status: str

    @property
    def receipt_id(self) -> str:
        return sha256_text(canonical_json(asdict(self)))[:32]


AdmissionProvider = Callable[
    [ArenaTurnEnvelopeV1, AuraToolRequestV1, ToolRouteV1, str], ToolAdmissionV1
]
ToolExecutor = Callable[[Mapping[str, Any]], Any]
AckSink = Callable[[Mapping[str, Any]], None]


def _reject_caller_controls(value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).strip().casefold()
            if key in _FORBIDDEN_CALLER_CONTROL_KEYS:
                raise BridgeRefusal("TOOL_CALLER_CONTROL_FORBIDDEN", key)
            _reject_caller_controls(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_caller_controls(child)


def _redact_sensitive_result(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: MutableMapping[str, Any] = {}
        for raw_key, child in value.items():
            key = str(raw_key)
            if key.strip().casefold() in _SENSITIVE_RESULT_KEYS:
                out[key] = "[REDACTED]"
            else:
                out[key] = _redact_sensitive_result(child)
        return dict(out)
    if isinstance(value, tuple):
        return [_redact_sensitive_result(child) for child in value]
    if isinstance(value, list):
        return [_redact_sensitive_result(child) for child in value]
    return value


def _bounded_result(value: Any, maximum: int) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        normalized: Any = _redact_sensitive_result(value)
    else:
        normalized = {"value": _redact_sensitive_result(value)}
    try:
        encoded = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BridgeRefusal("TOOL_RESULT_NOT_JSON_SERIALIZABLE") from exc
    if len(encoded) > maximum:
        raise BridgeRefusal("TOOL_RESULT_TOO_LARGE", str(len(encoded)))
    return normalized


def request_digest(request: AuraToolRequestV1) -> str:
    return sha256_text(canonical_json(asdict(request)))


def execute_admitted_tool(
    envelope: ArenaTurnEnvelopeV1,
    request: AuraToolRequestV1,
    *,
    current_arena_head: str,
    currentness_hash: str,
    routes: Mapping[str, ToolRouteV1],
    executors: Mapping[str, ToolExecutor],
    admission_provider: AdmissionProvider,
    emit_ack: Optional[AckSink] = None,
) -> tuple[AuraToolResultV1, ToolBrokerReceiptV1]:
    """Execute one Gemini-requested tool only after host-owned exact admission.

    The Gemini-visible request can select an allowlisted logical ``tool_id`` and
    arguments. It cannot select provider credentials, executor identity, effect
    authority, fence/currentness, or the host route. Those come from AuraOS-owned
    maps and ``ToolAdmissionV1``.
    """
    _reject_caller_controls(request.args)
    route = routes.get(request.tool_id)
    if route is None:
        raise BridgeRefusal("TOOL_ROUTE_NOT_FOUND", request.tool_id)
    route.validate()

    admit_tool_request(
        envelope,
        request,
        current_arena_head=current_arena_head,
        currentness_hash=currentness_hash,
        tool_effect_classes={tool_id: item.effect_class for tool_id, item in routes.items()},
    )
    if route.effect_class != request.requested_effect_class:
        raise BridgeRefusal("TOOL_ROUTE_EFFECT_MISMATCH", request.tool_id)

    digest = request_digest(request)
    admission = admission_provider(envelope, request, route, digest)
    if not isinstance(admission, ToolAdmissionV1):
        raise BridgeRefusal("TOOL_ADMISSION_TYPE_INVALID")
    admission.validate(
        envelope,
        request,
        route,
        digest,
        current_arena_head=current_arena_head,
        currentness_hash=currentness_hash,
    )

    executor = executors.get(route.executor_id)
    if executor is None:
        raise BridgeRefusal("TOOL_EXECUTOR_UNAVAILABLE", route.executor_id)

    ack = {
        "schema": "AuraToolAckV1",
        "request_id": request.request_id,
        "request_digest": digest,
        "admission_ref": admission.admission_ref,
        "executor_id": route.executor_id,
        "effect_class": route.effect_class,
        "arena_head": current_arena_head,
        "currentness_hash": currentness_hash,
        "status": "ACK_BEFORE_EFFECT",
    }
    if emit_ack is not None:
        emit_ack(ack)

    raw_result = executor(dict(request.args))
    bounded = _bounded_result(raw_result, route.max_result_bytes)
    result = AuraToolResultV1(
        request_id=request.request_id,
        capsule_id=envelope.capsule_id,
        status="OK",
        currentness_hash=currentness_hash,
        bounded_result=bounded,
        receipt_ref=admission.admission_ref,
    )
    result.validate()
    receipt = ToolBrokerReceiptV1(
        request_id=request.request_id,
        request_digest=digest,
        admission_ref=admission.admission_ref,
        admission_digest=sha256_text(canonical_json(asdict(admission))),
        executor_id=route.executor_id,
        capability_ref=route.capability_ref,
        effect_class=route.effect_class,
        result_digest=sha256_text(canonical_json(asdict(result))),
        status="OK",
    )
    return result, receipt
