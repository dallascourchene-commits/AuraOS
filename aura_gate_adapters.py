"""Strict MCP and A2A projections for :class:`AuraGateRuntime`.

The adapter exposes only Aura Gate operations.  Transport/session code must
inject an already verified :class:`VerifiedGateIdentity`; protocol bodies are
never treated as identity or authority evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
import hashlib
import json
import math
import re
from typing import Any
from urllib.parse import urlsplit

from aura_gate import GATE_VERSION, AuraGateRuntime, GateRunRequest
from aura_gate_oidc import VerifiedGateIdentity

GATE_ADAPTER_VERSION = "AURA_GATE_PROTOCOL_ADAPTER_V1"
MCP_PROTOCOL_VERSION = "2025-06-18"
A2A_PROTOCOL_VERSION = "1.0"
MCP_SERVER_NAME = "aura-gate"
MCP_TOOL_NAMES = (
    "aura_gate_prepare",
    "aura_gate_start",
    "aura_gate_submit",
    "aura_gate_status",
    "aura_gate_revoke",
)
A2A_METHODS = ("message/send", "tasks/get", "tasks/cancel")

_MAX_REQUEST_BYTES = 262_144
_MAX_RESPONSE_BYTES = 524_288
_MAX_STRING_BYTES = 131_072
_MAX_IDENTIFIER_BYTES = 256
_MAX_CONTAINER_ITEMS = 256
_MAX_JSON_NODES = 4096
_MAX_JSON_DEPTH = 10
_MAX_INTEGER = 10**15
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_SAFE_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_GATE_REQUEST_FIELDS = frozenset(field.name for field in fields(GateRunRequest) if field.name != "protocol")
_IDENTITY_FIELD_FRAGMENTS = frozenset(
    {
        "actor",
        "actor_id",
        "actor_ref",
        "authorization",
        "authorized_identity",
        "bearer",
        "bearer_token",
        "claims",
        "identity",
        "identity_claims",
        "id_token",
        "oauth",
        "oauth_claims",
        "principal",
        "raw_claims",
        "subject",
        "token",
        "transport_identity",
        "verified_identity",
    }
)
_CONTROL_FIELDS = {
    "human_review_required": True,
    "production_mutation": False,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pull_request": False,
    "automatic_merge": False,
    "automatic_promotion": False,
}
_COMMON_RESULT_FIELDS = frozenset(
    {
        "ok",
        "version",
        "gate_run_id",
        "status",
        "error",
        "stage",
        *_CONTROL_FIELDS,
    }
)
_RESULT_FIELDS = {
    "prepare": _COMMON_RESULT_FIELDS
    | {
        "authority_id",
        "expires_at",
        "forge_contract_id",
        "forge_contract_digest",
        "policy_id",
        "purpose_digest",
        "audit",
    },
    "start": _COMMON_RESULT_FIELDS | {"turn", "egress_capsule"},
    "submit": _COMMON_RESULT_FIELDS | {"forge_status", "decision_eligible", "turn", "egress_capsule"},
    "status": _COMMON_RESULT_FIELDS | {"authority_id", "forge_status", "decision_eligible", "expires_at"},
    "revoke": _COMMON_RESULT_FIELDS,
}
_TOOL_TO_OPERATION = {
    "aura_gate_prepare": "prepare",
    "aura_gate_start": "start",
    "aura_gate_submit": "submit",
    "aura_gate_status": "status",
    "aura_gate_revoke": "revoke",
}
_TASK_STATE_BY_STATUS = {
    "ACTIVE": "TASK_STATE_SUBMITTED",
    "STARTING": "TASK_STATE_WORKING",
    "STARTED": "TASK_STATE_WORKING",
    "WAITING_FOR_MODEL": "TASK_STATE_WORKING",
    "DISSOLVED": "TASK_STATE_COMPLETED",
    "READY_FOR_HUMAN_REVIEW": "TASK_STATE_COMPLETED",
    "REVOKED": "TASK_STATE_CANCELED",
    "EXPIRED": "TASK_STATE_FAILED",
}


class GateProtocolError(ValueError):
    """Bounded protocol failure safe for an HTTP or JSON-RPC boundary."""

    def __init__(
        self,
        code: str,
        *,
        rpc_code: int = -32602,
        http_status: int = 400,
    ) -> None:
        self.code = str(code)
        self.rpc_code = int(rpc_code)
        self.http_status = int(http_status)
        super().__init__(f"Aura Gate protocol request denied: {self.code}")


def _deny(
    code: str,
    *,
    rpc_code: int = -32602,
    http_status: int = 400,
) -> None:
    raise GateProtocolError(code, rpc_code=rpc_code, http_status=http_status)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise GateProtocolError("invalid_json_value") from exc


def _bounded_copy(value: Any, *, response: bool = False) -> Any:
    nodes = 0

    def walk(item: Any, depth: int) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_JSON_NODES or depth > _MAX_JSON_DEPTH:
            _deny("json_structure_too_large")
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            if abs(item) > _MAX_INTEGER:
                _deny("json_number_out_of_range")
            return item
        if type(item) is float:
            if not math.isfinite(item) or abs(item) > _MAX_INTEGER:
                _deny("json_number_out_of_range")
            return item
        if type(item) is str:
            try:
                encoded = item.encode("utf-8")
            except UnicodeError as exc:
                raise GateProtocolError("invalid_json_string") from exc
            if len(encoded) > _MAX_STRING_BYTES or "\x00" in item:
                _deny("json_string_too_large")
            return item
        if isinstance(item, Mapping):
            raw = dict(item)
            if len(raw) > _MAX_CONTAINER_ITEMS:
                _deny("json_object_too_large")
            result: dict[str, Any] = {}
            for key, child in raw.items():
                if type(key) is not str or not key or len(key.encode("utf-8")) > 128:
                    _deny("invalid_json_key")
                result[key] = walk(child, depth + 1)
            return result
        if isinstance(item, (list, tuple)) and not isinstance(item, (str, bytes)):
            if len(item) > _MAX_CONTAINER_ITEMS:
                _deny("json_array_too_large")
            return [walk(child, depth + 1) for child in item]
        _deny("invalid_json_value")

    copied = walk(value, 0)
    encoded = _canonical_json(copied).encode("utf-8")
    limit = _MAX_RESPONSE_BYTES if response else _MAX_REQUEST_BYTES
    if len(encoded) > limit:
        _deny("json_payload_too_large")
    return copied


def _normalize_field(value: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _is_identity_field(value: str) -> bool:
    normalized = _normalize_field(value)
    return (
        normalized in _IDENTITY_FIELD_FRAGMENTS
        or normalized.startswith(("actor_", "authorization_", "claims_", "identity_"))
        or normalized.endswith(("_actor", "_authorization", "_claims", "_identity"))
    )


def _without_body_identity(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _without_body_identity(item) for key, item in value.items() if not _is_identity_field(key)}
    if isinstance(value, list):
        return [_without_body_identity(item) for item in value]
    return value


def _mapping(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _deny(code)
    return dict(value)


def _exact_or_subset(
    value: Mapping[str, Any],
    allowed: set[str] | frozenset[str],
    code: str,
    *,
    required: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    raw = dict(value)
    if not set(raw).issubset(allowed) or not set(required).issubset(raw):
        _deny(code)
    return raw


def _text(
    value: Any,
    code: str,
    *,
    limit: int = _MAX_IDENTIFIER_BYTES,
    pattern: re.Pattern[str] | None = None,
    allow_empty: bool = False,
) -> str:
    if type(value) is not str or value != value.strip() or (not value and not allow_empty):
        _deny(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise GateProtocolError(code) from exc
    if len(encoded) > limit or "\x00" in value or (pattern is not None and pattern.fullmatch(value) is None):
        _deny(code)
    return value


def _identifier(value: Any, code: str) -> str:
    return _text(value, code, pattern=_SAFE_IDENTIFIER)


def _verified_identity(value: Any) -> VerifiedGateIdentity:
    if type(value) is not VerifiedGateIdentity:
        _deny("transport_identity_required", rpc_code=-32000, http_status=401)
    return value


def _validate_endpoint(value: Any) -> str:
    endpoint = _text(value, "invalid_a2a_endpoint", limit=2048)
    try:
        parsed = urlsplit(endpoint)
    except ValueError as exc:
        raise GateProtocolError("invalid_a2a_endpoint") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        _deny("invalid_a2a_endpoint")
    return endpoint


def _json_schema_string(*, max_length: int = 512) -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": max_length}


def _json_schema_strings(*, max_length: int = 512) -> dict[str, Any]:
    return {
        "type": "array",
        "items": _json_schema_string(max_length=max_length),
        "maxItems": _MAX_CONTAINER_ITEMS,
        "uniqueItems": True,
    }


def _prepare_schema() -> dict[str, Any]:
    properties: dict[str, Any] = {
        "policy_id": _json_schema_string(max_length=256),
        "purpose_digest": _json_schema_string(max_length=256),
        "objective": _json_schema_string(max_length=16_000),
        "target_file": _json_schema_string(max_length=1024),
        "target_symbol": _json_schema_string(max_length=512),
        "acceptance_criteria": _json_schema_strings(),
        "risk_map": _json_schema_strings(),
        "constraints": _json_schema_strings(),
        "capabilities": _json_schema_strings(max_length=128),
        "destination": _json_schema_string(max_length=2048),
        "provider": _json_schema_string(max_length=256),
        "model": _json_schema_string(max_length=256),
        "data_classes": _json_schema_strings(max_length=256),
        "retention_class": _json_schema_string(max_length=256),
        "egress_fields": _json_schema_strings(max_length=256),
        "lease_ttl_seconds": {"type": "number", "minimum": 1, "maximum": 86_400},
        "nonce": _json_schema_string(max_length=256),
        "council_mode": {
            "type": "string",
            "enum": ["AUTO", "SELECTIVE_V3", "FULL_V2"],
        },
        "max_context_tokens": {"type": "integer", "minimum": 256, "maximum": 16_000},
        "max_output_tokens": {"type": "integer", "minimum": 128, "maximum": 16_000},
        "max_turns": {"type": "integer", "minimum": 1, "maximum": 40},
        "max_local_repairs": {"type": "integer", "minimum": 0, "maximum": 8},
        "max_provider_calls": {"type": "integer", "minimum": 1, "maximum": 128},
    }
    return {
        "type": "object",
        "properties": properties,
        "required": sorted(_GATE_REQUEST_FIELDS),
        "additionalProperties": False,
    }


def _tool_definitions() -> list[dict[str, Any]]:
    gate_id = _json_schema_string(max_length=256)
    output_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "version": {"type": "string"},
            "human_review_required": {"const": True},
            "production_mutation": {"const": False},
            "automatic_promotion": {"const": False},
        },
        "required": [
            "ok",
            "version",
            "human_review_required",
            "production_mutation",
            "automatic_promotion",
        ],
        "additionalProperties": True,
    }
    return [
        {
            "name": "aura_gate_prepare",
            "title": "Prepare Aura Gate run",
            "description": "Prepare one bounded, purpose-bound run that stops at human review.",
            "inputSchema": _prepare_schema(),
            "outputSchema": output_schema,
        },
        {
            "name": "aura_gate_start",
            "title": "Start Aura Gate run",
            "description": "Start one retained Gate run without promotion authority.",
            "inputSchema": {
                "type": "object",
                "properties": {"gate_run_id": gate_id},
                "required": ["gate_run_id"],
                "additionalProperties": False,
            },
            "outputSchema": output_schema,
        },
        {
            "name": "aura_gate_submit",
            "title": "Submit bounded Gate response",
            "description": "Submit one bounded response to an active Gate run.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gate_run_id": gate_id,
                    "turn_id": _json_schema_string(max_length=256),
                    "response": _json_schema_string(max_length=_MAX_STRING_BYTES),
                    "provider_usage": {
                        "type": "object",
                        "properties": {
                            "input_tokens": {"type": "integer", "minimum": 0},
                            "output_tokens": {"type": "integer", "minimum": 0},
                            "total_tokens": {"type": "integer", "minimum": 0},
                            "cost_usd": {"type": "number", "minimum": 0},
                            "latency_ms": {"type": "number", "minimum": 0},
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["gate_run_id", "turn_id", "response"],
                "additionalProperties": False,
            },
            "outputSchema": output_schema,
        },
        {
            "name": "aura_gate_status",
            "title": "Get Aura Gate status",
            "description": "Return a bounded status projection for one Gate run.",
            "inputSchema": {
                "type": "object",
                "properties": {"gate_run_id": gate_id},
                "required": ["gate_run_id"],
                "additionalProperties": False,
            },
            "outputSchema": output_schema,
            "annotations": {"readOnlyHint": True},
        },
        {
            "name": "aura_gate_revoke",
            "title": "Revoke Aura Gate run",
            "description": "Irreversibly revoke one active Gate lease.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gate_run_id": gate_id,
                    "reason_code": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 128,
                        "pattern": "^[A-Za-z][A-Za-z0-9_.:-]*$",
                    },
                },
                "required": ["gate_run_id", "reason_code"],
                "additionalProperties": False,
            },
            "outputSchema": output_schema,
            "annotations": {"destructiveHint": True},
        },
    ]


class AuraGateProtocolAdapter:
    """Gate-only MCP 2025-06-18 and A2A 1.0 protocol projection."""

    def __init__(
        self,
        runtime: AuraGateRuntime,
        *,
        a2a_endpoint_url: str = "http://127.0.0.1:8765",
    ) -> None:
        if not isinstance(runtime, AuraGateRuntime):
            _deny("invalid_gate_runtime")
        self.runtime = runtime
        self.a2a_endpoint_url = _validate_endpoint(a2a_endpoint_url)

    def agent_card(self) -> dict[str, Any]:
        """Return the exact bounded Agent Card for the A2A 1.0 HTTP profile."""
        card = {
            "name": "Aura Gate",
            "description": "Purpose-bound coding operations that stop at human review.",
            "supportedInterfaces": [
                {
                    "url": self.a2a_endpoint_url,
                    "protocolBinding": "HTTP+JSON",
                    "protocolVersion": A2A_PROTOCOL_VERSION,
                }
            ],
            "version": GATE_ADAPTER_VERSION,
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "extendedAgentCard": False,
            },
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
            "skills": [
                {
                    "id": f"aura-gate-{operation}",
                    "name": f"Aura Gate {operation}",
                    "description": f"Bounded Gate {operation} operation.",
                    "tags": ["aura-gate", "human-review", operation],
                    "inputModes": ["application/json"],
                    "outputModes": ["application/json"],
                }
                for operation in ("prepare", "start", "submit", "status", "revoke")
            ],
            "securitySchemes": {
                "transportOidc": {
                    "httpAuthSecurityScheme": {
                        "description": "OIDC-issued JWT verified by Aura Gate transport.",
                        "scheme": "Bearer",
                        "bearerFormat": "JWT",
                    }
                }
            },
            "securityRequirements": [{"transportOidc": []}],
        }
        return _bounded_copy(card, response=True)

    def handle_mcp(
        self,
        request: Mapping[str, Any],
        *,
        identity: VerifiedGateIdentity,
    ) -> dict[str, Any] | None:
        """Handle one strict MCP JSON-RPC message with injected identity."""
        request_id: str | int | None = None
        try:
            bounded = _bounded_copy(request)
            raw = _without_body_identity(_mapping(bounded, "invalid_jsonrpc_request"))
            request_id = self._request_id(raw)
            if raw.get("jsonrpc") != "2.0":
                _deny("invalid_jsonrpc_version", rpc_code=-32600)
            method = _text(raw.get("method"), "invalid_jsonrpc_method", limit=128)
            if method == "notifications/initialized":
                if "id" in raw or set(raw) - {"jsonrpc", "method", "params"}:
                    _deny("invalid_initialized_notification", rpc_code=-32600)
                params = raw.get("params", {})
                if params not in ({}, None):
                    _deny("invalid_initialized_notification")
                _verified_identity(identity)
                return None
            if request_id is None or set(raw) - {"jsonrpc", "id", "method", "params"}:
                _deny("invalid_jsonrpc_request", rpc_code=-32600)
            verified = _verified_identity(identity)
            params = raw.get("params", {})
            if method == "initialize":
                result = self._mcp_initialize(params)
            elif method == "tools/list":
                result = self._mcp_tools_list(params)
            elif method == "tools/call":
                result = self._mcp_tools_call(params, verified)
            else:
                _deny("method_not_found", rpc_code=-32601, http_status=404)
            return self._rpc_result(request_id, result)
        except GateProtocolError as exc:
            return self._rpc_error(request_id, exc.rpc_code, exc.code)
        except Exception:
            return self._rpc_error(request_id, -32603, "internal_protocol_error")

    def handle_a2a(
        self,
        method: str,
        payload: Mapping[str, Any],
        *,
        identity: VerifiedGateIdentity,
        protocol_version: str,
    ) -> dict[str, Any]:
        """Handle one A2A 1.0 HTTP+JSON operation and return a bounded Task."""
        if protocol_version != A2A_PROTOCOL_VERSION:
            _deny("unsupported_a2a_version", http_status=400)
        verified = _verified_identity(identity)
        bounded = _bounded_copy(payload)
        raw = _without_body_identity(_mapping(bounded, "invalid_a2a_request"))
        operation = _text(method, "unknown_a2a_method", limit=64)
        try:
            if operation == "message/send":
                return self._a2a_message_send(raw, verified)
            if operation == "tasks/get":
                return self._a2a_task_status(raw, verified)
            if operation == "tasks/cancel":
                return self._a2a_task_cancel(raw, verified)
            _deny("unknown_a2a_method", rpc_code=-32601, http_status=404)
        except GateProtocolError:
            raise
        except Exception as exc:
            raise GateProtocolError("internal_protocol_error", rpc_code=-32603, http_status=500) from exc

    @staticmethod
    def _request_id(raw: Mapping[str, Any]) -> str | int | None:
        if "id" not in raw:
            return None
        value = raw["id"]
        if type(value) is int and abs(value) <= 2**53 - 1:
            return value
        if type(value) is str and value and len(value.encode("utf-8")) <= 128:
            return value
        return None

    @staticmethod
    def _rpc_result(request_id: str | int, result: Any) -> dict[str, Any]:
        return _bounded_copy(
            {"jsonrpc": "2.0", "id": request_id, "result": result},
            response=True,
        )

    @staticmethod
    def _rpc_error(
        request_id: str | int | None,
        code: int,
        message: str,
    ) -> dict[str, Any]:
        safe_message = message if _SAFE_CODE.fullmatch(message) else "protocol_error"
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": int(code), "message": safe_message},
        }

    @staticmethod
    def _mcp_initialize(value: Any) -> dict[str, Any]:
        params = _exact_or_subset(
            _mapping(value, "invalid_initialize_params"),
            {"protocolVersion", "capabilities", "clientInfo"},
            "invalid_initialize_params",
            required={"protocolVersion", "capabilities", "clientInfo"},
        )
        if params["protocolVersion"] != MCP_PROTOCOL_VERSION:
            _deny("unsupported_mcp_version")
        _mapping(params["capabilities"], "invalid_client_capabilities")
        client = _exact_or_subset(
            _mapping(params["clientInfo"], "invalid_client_info"),
            {"name", "title", "version"},
            "invalid_client_info",
            required={"name", "version"},
        )
        _text(client["name"], "invalid_client_info", limit=128)
        _text(client["version"], "invalid_client_info", limit=64)
        if "title" in client:
            _text(client["title"], "invalid_client_info", limit=256)
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": MCP_SERVER_NAME, "version": GATE_ADAPTER_VERSION},
            "instructions": "All work remains bounded by Aura Gate and stops at human review.",
        }

    @staticmethod
    def _mcp_tools_list(value: Any) -> dict[str, Any]:
        params = _exact_or_subset(
            _mapping(value, "invalid_tools_list_params"),
            {"cursor"},
            "invalid_tools_list_params",
        )
        if "cursor" in params:
            _deny("invalid_tools_cursor")
        return {"tools": _tool_definitions()}

    def _mcp_tools_call(
        self,
        value: Any,
        identity: VerifiedGateIdentity,
    ) -> dict[str, Any]:
        params = _exact_or_subset(
            _mapping(value, "invalid_tools_call_params"),
            {"name", "arguments"},
            "invalid_tools_call_params",
            required={"name"},
        )
        name = _text(params["name"], "invalid_tool_name", limit=128)
        operation = _TOOL_TO_OPERATION.get(name)
        if operation is None:
            _deny("tool_not_found", rpc_code=-32601, http_status=404)
        arguments = params.get("arguments", {})
        arguments = _without_body_identity(_mapping(arguments, "invalid_tool_arguments"))
        result = self._dispatch(
            operation,
            arguments,
            identity,
            transport_protocol="MCP",
        )
        text = _canonical_json(result)
        return {
            "content": [{"type": "text", "text": text}],
            "structuredContent": result,
            "isError": result["ok"] is False,
        }

    def _a2a_message_send(
        self,
        value: Mapping[str, Any],
        identity: VerifiedGateIdentity,
    ) -> dict[str, Any]:
        body = _exact_or_subset(
            value,
            {"message", "configuration", "metadata", "tenant"},
            "invalid_a2a_send_request",
            required={"message", "configuration"},
        )
        self._validate_empty_metadata(body.get("metadata"), "invalid_a2a_metadata")
        if "tenant" in body:
            _identifier(body["tenant"], "invalid_a2a_tenant")
        self._validate_a2a_configuration(body["configuration"])
        message = _exact_or_subset(
            _mapping(body["message"], "invalid_a2a_message"),
            {
                "messageId",
                "role",
                "parts",
                "contextId",
                "taskId",
                "metadata",
                "extensions",
                "referenceTaskIds",
            },
            "invalid_a2a_message",
            required={"messageId", "role", "parts"},
        )
        message_id = _identifier(message["messageId"], "invalid_a2a_message_id")
        if message["role"] != "ROLE_USER":
            _deny("invalid_a2a_role")
        self._validate_empty_metadata(message.get("metadata"), "invalid_a2a_metadata")
        if message.get("extensions", []) != [] or message.get("referenceTaskIds", []) != []:
            _deny("unsupported_a2a_message_extension")
        parts = message["parts"]
        if not isinstance(parts, list) or len(parts) != 1:
            _deny("invalid_a2a_parts")
        part = _exact_or_subset(
            _mapping(parts[0], "invalid_a2a_data_part"),
            {"data", "mediaType", "metadata"},
            "invalid_a2a_data_part",
            required={"data"},
        )
        if part.get("mediaType", "application/json") != "application/json":
            _deny("invalid_a2a_data_part")
        self._validate_empty_metadata(part.get("metadata"), "invalid_a2a_metadata")
        data = _exact_or_subset(
            _mapping(part["data"], "invalid_a2a_data_part"),
            {"operation", "parameters"},
            "invalid_a2a_data_part",
            required={"operation", "parameters"},
        )
        operation = _text(
            data["operation"],
            "unknown_gate_operation",
            limit=32,
            pattern=_SAFE_CODE,
        ).lower()
        if operation not in _RESULT_FIELDS:
            _deny("unknown_gate_operation")
        parameters = _without_body_identity(_mapping(data["parameters"], "invalid_gate_parameters"))
        expected_id = self._expected_gate_run_id(operation, parameters)
        task_identity_codes = {
            "contextId": "invalid_a2a_context_id",
            "taskId": "invalid_a2a_task_id",
        }
        for key, error_code in task_identity_codes.items():
            if key in message:
                supplied = _identifier(message[key], error_code)
                if not expected_id or supplied != expected_id:
                    _deny("a2a_task_identity_mismatch")
        result = self._dispatch(
            operation,
            parameters,
            identity,
            transport_protocol="A2A",
        )
        gate_run_id = self._result_gate_run_id(result, expected_id)
        if not gate_run_id:
            _deny("gate_operation_denied", http_status=403)
        return self._task_projection(
            operation,
            gate_run_id,
            result,
            message_id=message_id,
        )

    def _a2a_task_status(
        self,
        value: Mapping[str, Any],
        identity: VerifiedGateIdentity,
    ) -> dict[str, Any]:
        body = _exact_or_subset(
            value,
            {"id", "historyLength", "tenant", "metadata"},
            "invalid_a2a_get_task",
            required={"id"},
        )
        gate_run_id = _identifier(body["id"], "invalid_gate_run_id")
        if body.get("historyLength", 0) != 0:
            _deny("unsupported_a2a_history")
        if "tenant" in body:
            _identifier(body["tenant"], "invalid_a2a_tenant")
        self._validate_empty_metadata(body.get("metadata"), "invalid_a2a_metadata")
        result = self._dispatch(
            "status",
            {"gate_run_id": gate_run_id},
            identity,
            transport_protocol="A2A",
        )
        return self._task_projection("status", gate_run_id, result)

    def _a2a_task_cancel(
        self,
        value: Mapping[str, Any],
        identity: VerifiedGateIdentity,
    ) -> dict[str, Any]:
        body = _exact_or_subset(
            value,
            {"id", "tenant", "metadata"},
            "invalid_a2a_cancel_task",
            required={"id"},
        )
        gate_run_id = _identifier(body["id"], "invalid_gate_run_id")
        if "tenant" in body:
            _identifier(body["tenant"], "invalid_a2a_tenant")
        self._validate_empty_metadata(body.get("metadata"), "invalid_a2a_metadata")
        result = self._dispatch(
            "revoke",
            {"gate_run_id": gate_run_id, "reason_code": "A2A_CANCELLED"},
            identity,
            transport_protocol="A2A",
        )
        return self._task_projection("revoke", gate_run_id, result)

    @staticmethod
    def _validate_empty_metadata(value: Any, code: str) -> None:
        if value is None:
            return
        metadata = _mapping(value, code)
        if metadata:
            _deny(code)

    @staticmethod
    def _validate_a2a_configuration(value: Any) -> None:
        config = _exact_or_subset(
            _mapping(value, "invalid_a2a_configuration"),
            {"acceptedOutputModes", "historyLength", "returnImmediately"},
            "invalid_a2a_configuration",
        )
        if config.get("acceptedOutputModes", ["application/json"]) != ["application/json"]:
            _deny("invalid_a2a_configuration")
        if config.get("historyLength", 0) != 0:
            _deny("invalid_a2a_configuration")
        if config.get("returnImmediately") is not True:
            _deny("invalid_a2a_configuration")

    @staticmethod
    def _expected_gate_run_id(
        operation: str,
        parameters: Mapping[str, Any],
    ) -> str:
        if operation == "prepare":
            return ""
        if "gate_run_id" not in parameters:
            _deny("invalid_gate_parameters")
        return _identifier(parameters["gate_run_id"], "invalid_gate_run_id")

    def _dispatch(
        self,
        operation: str,
        parameters: Mapping[str, Any],
        identity: VerifiedGateIdentity,
        *,
        transport_protocol: str,
    ) -> dict[str, Any]:
        params = dict(parameters)
        expected_id = self._expected_gate_run_id(operation, params)
        try:
            if operation == "prepare":
                params.pop("protocol", None)
                if set(params) != _GATE_REQUEST_FIELDS:
                    _deny("invalid_gate_parameters")
                params["protocol"] = transport_protocol
                raw_result = self.runtime.prepare(identity, params)
            elif operation == "start":
                self._require_parameter_fields(params, {"gate_run_id"})
                raw_result = self.runtime.start(identity, expected_id)
            elif operation == "submit":
                self._require_parameter_fields(
                    params,
                    {"gate_run_id", "turn_id", "response"},
                    optional={"provider_usage"},
                )
                turn_id = _identifier(params["turn_id"], "invalid_turn_id")
                response = _text(
                    params["response"],
                    "invalid_model_response",
                    limit=_MAX_STRING_BYTES,
                )
                usage = params.get("provider_usage", {})
                usage = _mapping(usage, "invalid_provider_usage")
                raw_result = self.runtime.submit(
                    identity,
                    expected_id,
                    turn_id=turn_id,
                    response=response,
                    provider_usage=usage,
                )
            elif operation == "status":
                self._require_parameter_fields(params, {"gate_run_id"})
                raw_result = self.runtime.status(identity, expected_id)
            elif operation == "revoke":
                self._require_parameter_fields(params, {"gate_run_id", "reason_code"})
                reason = _text(
                    params["reason_code"],
                    "invalid_reason_code",
                    limit=128,
                    pattern=_SAFE_CODE,
                ).upper()
                raw_result = self.runtime.revoke(
                    identity,
                    expected_id,
                    reason_code=reason,
                )
            else:
                _deny("unknown_gate_operation")
        except GateProtocolError:
            raise
        except Exception as exc:
            raise GateProtocolError("gate_runtime_unavailable", rpc_code=-32603, http_status=500) from exc
        return self._project_result(operation, raw_result, expected_id=expected_id)

    @staticmethod
    def _require_parameter_fields(
        params: Mapping[str, Any],
        required: set[str],
        *,
        optional: set[str] = frozenset(),
    ) -> None:
        if set(params) != required | (set(params) & optional):
            _deny("invalid_gate_parameters")
        if not required.issubset(params):
            _deny("invalid_gate_parameters")

    @staticmethod
    def _project_result(
        operation: str,
        value: Any,
        *,
        expected_id: str,
    ) -> dict[str, Any]:
        raw = _mapping(value, "invalid_gate_runtime_result")
        if type(raw.get("ok")) is not bool:
            _deny("invalid_gate_runtime_result", rpc_code=-32603, http_status=500)
        for field_name, expected in _CONTROL_FIELDS.items():
            if field_name in raw and raw[field_name] is not expected:
                _deny("runtime_authority_expansion", rpc_code=-32603, http_status=500)
        projected = {key: raw[key] for key in _RESULT_FIELDS[operation] if key in raw}
        projected["version"] = str(projected.get("version") or GATE_VERSION)
        projected.update(_CONTROL_FIELDS)
        if expected_id:
            result_id = projected.get("gate_run_id")
            if raw["ok"] is True and result_id != expected_id:
                _deny("gate_run_identity_mismatch", rpc_code=-32603, http_status=500)
            projected["gate_run_id"] = expected_id
        elif raw["ok"] is True:
            projected["gate_run_id"] = _identifier(projected.get("gate_run_id"), "invalid_gate_runtime_result")
        if "error" in projected:
            error = projected["error"]
            projected["error"] = (
                error if type(error) is str and _SAFE_CODE.fullmatch(error) else "gate_operation_denied"
            )
        if "stage" in projected:
            stage = projected["stage"]
            projected["stage"] = stage if type(stage) is str and _SAFE_CODE.fullmatch(stage) else "GATE"
        return _bounded_copy(projected, response=True)

    @staticmethod
    def _result_gate_run_id(result: Mapping[str, Any], expected_id: str) -> str:
        if expected_id:
            return expected_id
        value = result.get("gate_run_id")
        if value in (None, ""):
            return ""
        return _identifier(value, "invalid_gate_runtime_result")

    @staticmethod
    def _task_projection(
        operation: str,
        gate_run_id: str,
        result: Mapping[str, Any],
        *,
        message_id: str = "",
    ) -> dict[str, Any]:
        state = "TASK_STATE_FAILED"
        if result.get("ok") is True:
            status = str(result.get("status") or result.get("forge_status") or "").upper()
            state = _TASK_STATE_BY_STATUS.get(status, "TASK_STATE_WORKING")
            if operation == "revoke":
                state = "TASK_STATE_CANCELED"
        artifact_basis = {
            "gate_run_id": gate_run_id,
            "operation": operation,
            "message_id": message_id,
            "result": result,
        }
        artifact_id = "gate-result-" + hashlib.sha256(_canonical_json(artifact_basis).encode("utf-8")).hexdigest()[:24]
        metadata: dict[str, Any] = {
            "gateRunId": gate_run_id,
            "operation": operation,
            "humanReviewRequired": True,
            "productionMutation": False,
            "automaticPromotion": False,
        }
        if message_id:
            metadata["requestMessageId"] = message_id
        task = {
            "id": gate_run_id,
            "contextId": gate_run_id,
            "status": {"state": state},
            "artifacts": [
                {
                    "artifactId": artifact_id,
                    "name": "Aura Gate result",
                    "parts": [
                        {
                            "data": {
                                "operation": operation,
                                "result": dict(result),
                            },
                            "mediaType": "application/json",
                        }
                    ],
                }
            ],
            "metadata": metadata,
        }
        return _bounded_copy(task, response=True)


__all__ = [
    "A2A_METHODS",
    "A2A_PROTOCOL_VERSION",
    "GATE_ADAPTER_VERSION",
    "MCP_PROTOCOL_VERSION",
    "MCP_SERVER_NAME",
    "MCP_TOOL_NAMES",
    "AuraGateProtocolAdapter",
    "GateProtocolError",
]
