from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Mapping, MutableSet, Optional, Tuple


PROVIDER_ID = "GEMINI_WEBCHAT"
ALLOWED_ORIGINS = {"https://gemini.google.com"}
TRANSPORT_MODES = {
    "MANUAL_BOOTSTRAP",
    "ASSISTED_EXTENSION",
    "GUARDED_AUTO",
    "RECOMMISSION",
}
EFFECT_RANK = {
    "READ": 0,
    "D0": 1,
    "D1": 2,
    "D2": 3,
    "PUBLIC": 4,
    "DESTRUCTIVE": 5,
    "FINANCIAL": 6,
}


class BridgeRefusal(RuntimeError):
    """Typed fail-closed refusal for the browser-chat endpoint membrane."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_idempotency_key(*parts: str) -> str:
    if not all(str(part).strip() for part in parts):
        raise ValueError("idempotency parts must be non-empty")
    return sha256_text("\x1f".join(parts))


@dataclass(frozen=True)
class EndpointBindingV1:
    endpoint_id: str
    visit_id: str
    arena_sid: str
    provider_id: str = PROVIDER_ID
    browser_origin: str = "https://gemini.google.com"
    conversation_locator_hash: str = ""
    transport_mode: str = "ASSISTED_EXTENSION"
    max_effect_class: str = "D0"
    owner_auto_send_enabled: bool = False

    def validate(self) -> None:
        required = {
            "endpoint_id": self.endpoint_id,
            "visit_id": self.visit_id,
            "arena_sid": self.arena_sid,
            "conversation_locator_hash": self.conversation_locator_hash,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise BridgeRefusal("ENDPOINT_BINDING_INCOMPLETE", ",".join(missing))
        if self.provider_id != PROVIDER_ID:
            raise BridgeRefusal("PROVIDER_MISMATCH", self.provider_id)
        if self.browser_origin not in ALLOWED_ORIGINS:
            raise BridgeRefusal("BROWSER_ORIGIN_NOT_ALLOWED", self.browser_origin)
        if self.transport_mode not in TRANSPORT_MODES:
            raise BridgeRefusal("UNKNOWN_TRANSPORT_MODE", self.transport_mode)
        if self.max_effect_class not in EFFECT_RANK:
            raise BridgeRefusal("UNKNOWN_EFFECT_CLASS", self.max_effect_class)
        if self.transport_mode == "GUARDED_AUTO" and not self.owner_auto_send_enabled:
            raise BridgeRefusal("AUTO_SEND_NOT_OWNER_ENABLED", self.endpoint_id)


@dataclass(frozen=True)
class ArenaTurnEnvelopeV1:
    turn_id: str
    capsule_id: str
    arena_sid: str
    arena_head: str
    currentness_hash: str
    mission_id: str
    mission: str
    purpose: str
    objective: str
    claim_id: str
    claim_lease: str
    idempotency_key: str
    effect_ceiling: str = "D0"
    allowed_tools: Tuple[str, ...] = ()
    context_refs: Tuple[str, ...] = ()
    sibling_claim_refs: Tuple[str, ...] = ()
    response_schema: str = "ArenaTurnResultV1"

    def validate(self) -> None:
        required = {
            "turn_id": self.turn_id,
            "capsule_id": self.capsule_id,
            "arena_sid": self.arena_sid,
            "arena_head": self.arena_head,
            "currentness_hash": self.currentness_hash,
            "mission_id": self.mission_id,
            "mission": self.mission,
            "purpose": self.purpose,
            "objective": self.objective,
            "claim_id": self.claim_id,
            "claim_lease": self.claim_lease,
            "idempotency_key": self.idempotency_key,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise BridgeRefusal("TURN_ENVELOPE_INCOMPLETE", ",".join(missing))
        if self.effect_ceiling not in EFFECT_RANK:
            raise BridgeRefusal("UNKNOWN_EFFECT_CLASS", self.effect_ceiling)
        expected = stable_idempotency_key(
            self.arena_sid,
            self.arena_head,
            self.currentness_hash,
            self.capsule_id,
            self.turn_id,
        )
        if self.idempotency_key != expected:
            raise BridgeRefusal("IDEMPOTENCY_KEY_MISMATCH", self.turn_id)


@dataclass(frozen=True)
class ArenaTurnResultV1:
    turn_id: str
    capsule_id: str
    endpoint_id: str
    visit_id: str
    arena_sid: str
    arena_head: str
    currentness_hash: str
    visible_text: str
    visible_text_sha256: str
    status: str = "COMPLETE"
    residuals: Tuple[str, ...] = ()
    receipt_refs: Tuple[str, ...] = ()
    provider_id: str = PROVIDER_ID

    def validate(self) -> None:
        if self.provider_id != PROVIDER_ID:
            raise BridgeRefusal("PROVIDER_MISMATCH", self.provider_id)
        if self.status not in {"COMPLETE", "BLOCKED", "TOOL_REQUESTED", "REFUSED"}:
            raise BridgeRefusal("UNKNOWN_RESULT_STATUS", self.status)
        if not self.visible_text.strip() and self.status == "COMPLETE":
            raise BridgeRefusal("EMPTY_VISIBLE_RESULT", self.turn_id)
        if sha256_text(self.visible_text) != self.visible_text_sha256:
            raise BridgeRefusal("VISIBLE_RESULT_HASH_MISMATCH", self.turn_id)


@dataclass(frozen=True)
class AuraToolRequestV1:
    request_id: str
    capsule_id: str
    turn_id: str
    tool_id: str
    args: Mapping[str, Any]
    requested_effect_class: str
    reason: str

    def validate(self) -> None:
        if not self.request_id.strip() or not self.tool_id.strip():
            raise BridgeRefusal("TOOL_REQUEST_INCOMPLETE", self.request_id or self.tool_id)
        if self.requested_effect_class not in EFFECT_RANK:
            raise BridgeRefusal("UNKNOWN_EFFECT_CLASS", self.requested_effect_class)
        if not self.reason.strip():
            raise BridgeRefusal("TOOL_REASON_REQUIRED", self.request_id)


@dataclass(frozen=True)
class AuraToolResultV1:
    request_id: str
    capsule_id: str
    status: str
    currentness_hash: str
    bounded_result: Optional[Mapping[str, Any]] = None
    result_ref: Optional[str] = None
    receipt_ref: Optional[str] = None
    refusal_code: Optional[str] = None

    def validate(self) -> None:
        if self.status not in {"OK", "REFUSED", "STALE", "ERROR"}:
            raise BridgeRefusal("UNKNOWN_TOOL_RESULT_STATUS", self.status)
        if self.status == "OK" and self.bounded_result is None and not self.result_ref:
            raise BridgeRefusal("TOOL_RESULT_MISSING_OUTPUT", self.request_id)
        if self.status != "OK" and not self.refusal_code:
            raise BridgeRefusal("TOOL_REFUSAL_CODE_REQUIRED", self.request_id)


@dataclass
class BridgeLedgerV1:
    sent_turn_ids: MutableSet[str] = field(default_factory=set)
    completed_turn_ids: MutableSet[str] = field(default_factory=set)
    accepted_tool_request_ids: MutableSet[str] = field(default_factory=set)

    def mark_turn_sent(self, turn_id: str) -> None:
        if turn_id in self.sent_turn_ids:
            raise BridgeRefusal("DUPLICATE_TURN_SEND", turn_id)
        self.sent_turn_ids.add(turn_id)

    def accept_result(self, result: ArenaTurnResultV1) -> None:
        if result.turn_id not in self.sent_turn_ids:
            raise BridgeRefusal("RESULT_FOR_UNSENT_TURN", result.turn_id)
        if result.turn_id in self.completed_turn_ids:
            raise BridgeRefusal("DUPLICATE_TURN_RESULT", result.turn_id)
        self.completed_turn_ids.add(result.turn_id)

    def accept_tool_request(self, request: AuraToolRequestV1) -> None:
        if request.request_id in self.accepted_tool_request_ids:
            raise BridgeRefusal("DUPLICATE_TOOL_REQUEST", request.request_id)
        self.accepted_tool_request_ids.add(request.request_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "BridgeLedgerV1",
            "sent_turn_ids": sorted(self.sent_turn_ids),
            "completed_turn_ids": sorted(self.completed_turn_ids),
            "accepted_tool_request_ids": sorted(self.accepted_tool_request_ids),
        }


def admit_turn(
    binding: EndpointBindingV1,
    envelope: ArenaTurnEnvelopeV1,
    *,
    current_arena_head: str,
    currentness_hash: str,
) -> None:
    binding.validate()
    envelope.validate()
    if envelope.arena_sid != binding.arena_sid:
        raise BridgeRefusal("ARENA_MISMATCH", envelope.arena_sid)
    if envelope.arena_head != current_arena_head:
        raise BridgeRefusal("STALE_ARENA_HEAD", f"{envelope.arena_head}!={current_arena_head}")
    if envelope.currentness_hash != currentness_hash:
        raise BridgeRefusal("STALE_CURRENTNESS", envelope.currentness_hash)
    if EFFECT_RANK[envelope.effect_ceiling] > EFFECT_RANK[binding.max_effect_class]:
        raise BridgeRefusal("ENDPOINT_EFFECT_CEILING_EXCEEDED", envelope.effect_ceiling)


def admit_result(
    binding: EndpointBindingV1,
    envelope: ArenaTurnEnvelopeV1,
    result: ArenaTurnResultV1,
    *,
    current_arena_head: str,
    currentness_hash: str,
) -> None:
    binding.validate()
    envelope.validate()
    result.validate()
    expected = {
        "turn_id": (result.turn_id, envelope.turn_id),
        "capsule_id": (result.capsule_id, envelope.capsule_id),
        "endpoint_id": (result.endpoint_id, binding.endpoint_id),
        "visit_id": (result.visit_id, binding.visit_id),
        "arena_sid": (result.arena_sid, binding.arena_sid),
        "arena_head": (result.arena_head, current_arena_head),
        "currentness_hash": (result.currentness_hash, currentness_hash),
    }
    mismatches = [name for name, (actual, wanted) in expected.items() if actual != wanted]
    if mismatches:
        raise BridgeRefusal("TURN_RESULT_BINDING_MISMATCH", ",".join(mismatches))


def admit_tool_request(
    envelope: ArenaTurnEnvelopeV1,
    request: AuraToolRequestV1,
    *,
    current_arena_head: str,
    currentness_hash: str,
    tool_effect_classes: Mapping[str, str],
) -> None:
    envelope.validate()
    request.validate()
    if envelope.arena_head != current_arena_head or envelope.currentness_hash != currentness_hash:
        raise BridgeRefusal("STALE_TOOL_CONTEXT", request.request_id)
    if request.capsule_id != envelope.capsule_id or request.turn_id != envelope.turn_id:
        raise BridgeRefusal("TOOL_REQUEST_CAPSULE_MISMATCH", request.request_id)
    if request.tool_id not in envelope.allowed_tools:
        raise BridgeRefusal("TOOL_NOT_ALLOWED", request.tool_id)
    admitted_effect = tool_effect_classes.get(request.tool_id)
    if admitted_effect not in EFFECT_RANK:
        raise BridgeRefusal("TOOL_EFFECT_CLASS_UNRESOLVED", request.tool_id)
    if EFFECT_RANK[request.requested_effect_class] > EFFECT_RANK[envelope.effect_ceiling]:
        raise BridgeRefusal("TOOL_REQUEST_EXCEEDS_CAPSULE_EFFECT", request.tool_id)
    if EFFECT_RANK[admitted_effect] > EFFECT_RANK[envelope.effect_ceiling]:
        raise BridgeRefusal("TOOL_ROUTE_EXCEEDS_CAPSULE_EFFECT", request.tool_id)
    if EFFECT_RANK[request.requested_effect_class] != EFFECT_RANK[admitted_effect]:
        raise BridgeRefusal(
            "TOOL_EFFECT_CLASS_MISMATCH",
            f"requested={request.requested_effect_class} admitted={admitted_effect}",
        )


def compile_bootstrap_prompt(binding: EndpointBindingV1, envelope: ArenaTurnEnvelopeV1) -> str:
    """Compile the visible first-turn contract for a normal Gemini browser chat."""
    binding.validate()
    envelope.validate()
    if binding.arena_sid != envelope.arena_sid:
        raise BridgeRefusal("ARENA_MISMATCH", envelope.arena_sid)

    packet = {
        "schema": "ArenaGeminiBootstrapV1",
        "provider_role": PROVIDER_ID,
        "endpoint_id": binding.endpoint_id,
        "visit_id": binding.visit_id,
        "transport_mode": binding.transport_mode,
        "arena_turn": asdict(envelope),
        "laws": [
            "AuraOS/Arena is source/currentness/authority/tool owner.",
            "Do not claim a tool executed unless an AuraToolResultV1 is returned.",
            "Do not expose or request credentials, cookies, hidden tokens, or hidden reasoning.",
            "Treat context references as source pointers; UNKNOWN remains UNKNOWN.",
            "If a tool is needed, emit one AuraToolRequestV1 and wait for AuraOS result.",
            "Persist material result/residuals through the Arena response contract.",
            "Rebase when currentness/head changes; stale work must not proceed.",
        ],
        "tool_request_contract": {
            "schema": "AuraToolRequestV1",
            "required": [
                "request_id",
                "capsule_id",
                "turn_id",
                "tool_id",
                "args",
                "requested_effect_class",
                "reason",
            ],
        },
        "response_contract": {
            "schema": envelope.response_schema,
            "instruction": "Return a concise visible result. Tool use must go through AuraToolRequestV1; never imply execution from intent or queue state.",
        },
    }
    return "AURA_ARENA_BOOTSTRAP_V1\n" + json.dumps(packet, indent=2, ensure_ascii=False)


def envelope_digest(envelope: ArenaTurnEnvelopeV1) -> str:
    return sha256_text(canonical_json(asdict(envelope)))
