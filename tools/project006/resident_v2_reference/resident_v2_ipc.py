"""Aura Project006 Resident V2 staged reference IPC core.

Trusted local control plane only: AF_UNIX, bounded framed canonical JSON,
no provider endpoints/secrets.
"""
from __future__ import annotations

import hashlib
import json
import re
import socket
import struct
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

PROTOCOL_VERSION = "AURA_RESIDENT_IPC_V2"
RECEIPT_VERSION = "AURA_RESIDENT_RECEIPT_V2"
MAX_FRAME_BYTES = 256 * 1024
MAX_DEPTH = 12
MAX_CONTAINER_ITEMS = 2048
MAX_STRING_BYTES = 128 * 1024
MAX_SEEN_REQUESTS = 4096
MAX_TRACKED_WORK = 4096
MAX_TERMINAL_WORK_RECORDS = 4096
MAX_CAPSULE_IDENTITIES = 4096
TERMINAL_WORK_RETENTION_MS = 5 * 60 * 1000
MAX_ACTIVE_CONNECTIONS = 32
FRAME_RECEIVE_TIMEOUT_SECONDS = 2.0

HEADER = struct.Struct("!I")

NORMAL_TYPES = frozenset(
    {"HEALTH", "STATUS", "WORK_SUBMIT", "WORK_STATUS", "WORK_CANCEL"}
)
ADMIN_TYPES = frozenset({"ADMIN_DRAIN", "ADMIN_RECONCILE"})
EFFECTFUL_TYPES = frozenset({"WORK_SUBMIT", "WORK_CANCEL"}) | ADMIN_TYPES
ALLOWED_TYPES = NORMAL_TYPES | ADMIN_TYPES

TOP_LEVEL_FIELDS = frozenset(
    {
        "protocol_version",
        "message_type",
        "request_id",
        "generation",
        "issued_at_ms",
        "expires_at_ms",
        "authority_ref",
        "currentness_ref",
        "payload",
        "extensions",
    }
)
REQUIRED_TOP_LEVEL_FIELDS = frozenset(
    {
        "protocol_version",
        "message_type",
        "request_id",
        "generation",
        "issued_at_ms",
        "expires_at_ms",
        "authority_ref",
        "currentness_ref",
        "payload",
    }
)

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,255}$")
IDENTITY_DOMAIN_FIELDS = frozenset({"generation", "currentness_ref", "authority_ref"})
SENSITIVE_KEY_FRAGMENTS = (
    "token",
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "private_key",
    "credential",
)
NETWORK_KEY_FRAGMENTS = (
    "provider_url",
    "provider_host",
    "network_endpoint",
    "endpoint",
    "http_url",
    "https_url",
    "ip_address",
    "dns_name",
    "hostname",
)


class IPCError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _encoded_string_length(value: str) -> int:
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise IPCError("INVALID_UNICODE_STRING") from exc


def canonical_json_bytes(obj: Any) -> bytes:
    try:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise IPCError("INVALID_UNICODE_STRING") from exc


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IPCError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _walk_limits(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise IPCError("STRUCTURE_TOO_DEEP")
    if isinstance(value, str):
        if _encoded_string_length(value) > MAX_STRING_BYTES:
            raise IPCError("STRING_TOO_LARGE")
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        raise IPCError("FLOAT_NOT_ALLOWED")
    if isinstance(value, list):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise IPCError("CONTAINER_TOO_LARGE")
        for item in value:
            _walk_limits(item, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise IPCError("CONTAINER_TOO_LARGE")
        for key, item in value.items():
            if not isinstance(key, str):
                raise IPCError("NON_STRING_KEY")
            if _encoded_string_length(key) > MAX_STRING_BYTES:
                raise IPCError("STRING_TOO_LARGE")
            lowered = key.lower()
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                raise IPCError("SENSITIVE_FIELD_FORBIDDEN")
            if any(fragment in lowered for fragment in NETWORK_KEY_FRAGMENTS):
                raise IPCError("NETWORK_ENDPOINT_FIELD_FORBIDDEN")
            _walk_limits(item, depth + 1)
        return
    raise IPCError("UNSUPPORTED_JSON_TYPE")


def decode_frame_payload(payload: bytes) -> Dict[str, Any]:
    if not payload or len(payload) > MAX_FRAME_BYTES:
        raise IPCError("FRAME_SIZE_INVALID")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IPCError("INVALID_UTF8") from exc
    try:
        obj = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=lambda _x: (_ for _ in ()).throw(
                IPCError("NONFINITE_NUMBER")
            ),
        )
    except IPCError:
        raise
    except Exception as exc:
        raise IPCError("MALFORMED_JSON") from exc
    if not isinstance(obj, dict):
        raise IPCError("TOP_LEVEL_NOT_OBJECT")
    _walk_limits(obj)
    return obj


def encode_frame(obj: Dict[str, Any]) -> bytes:
    body = canonical_json_bytes(obj)
    if not body or len(body) > MAX_FRAME_BYTES:
        raise IPCError("FRAME_SIZE_INVALID")
    return HEADER.pack(len(body)) + body


def recv_exact(sock: socket.socket, count: int, deadline_monotonic: float) -> bytes:
    out = bytearray()
    while len(out) < count:
        remaining = deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise IPCError("FRAME_RECEIVE_TIMEOUT")
        sock.settimeout(remaining)
        try:
            chunk = sock.recv(count - len(out))
        except (socket.timeout, TimeoutError) as exc:
            raise IPCError("FRAME_RECEIVE_TIMEOUT") from exc
        if not chunk:
            raise IPCError("TRUNCATED_FRAME")
        out.extend(chunk)
    return bytes(out)


def recv_frame(
    sock: socket.socket, timeout_seconds: float = FRAME_RECEIVE_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise IPCError("INVALID_FRAME_TIMEOUT")
    deadline = time.monotonic() + float(timeout_seconds)
    prior_timeout = sock.gettimeout()
    try:
        length = HEADER.unpack(recv_exact(sock, HEADER.size, deadline))[0]
        if length < 2 or length > MAX_FRAME_BYTES:
            raise IPCError("FRAME_SIZE_INVALID")
        return decode_frame_payload(recv_exact(sock, length, deadline))
    finally:
        sock.settimeout(prior_timeout)


def send_frame(sock: socket.socket, obj: Dict[str, Any]) -> None:
    sock.sendall(encode_frame(obj))


def _validate_ref(name: str, value: Any) -> str:
    if not isinstance(value, str) or not REF_RE.fullmatch(value):
        raise IPCError("INVALID_" + name.upper())
    return value


def _require_exact_payload(payload, required, optional=()):
    required_set = set(required)
    optional_set = set(optional)
    keys = set(payload)
    if required_set - keys:
        raise IPCError("PAYLOAD_MISSING_REQUIRED_FIELD")
    if keys - (required_set | optional_set):
        raise IPCError("PAYLOAD_UNKNOWN_FIELD")


def _validate_payload(message_type: str, payload: Dict[str, Any]) -> None:
    if message_type in {"HEALTH", "STATUS", "ADMIN_RECONCILE"}:
        _require_exact_payload(payload, ())
        return
    if message_type == "WORK_SUBMIT":
        _require_exact_payload(
            payload,
            ("capsule_id", "capsule_digest", "route_ref", "deadline_ms"),
            ("source_refs", "dependency_ids", "body_ref"),
        )
        _validate_ref("capsule_id", payload["capsule_id"])
        _validate_ref("route_ref", payload["route_ref"])
        if not isinstance(payload["capsule_digest"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", payload["capsule_digest"]
        ):
            raise IPCError("INVALID_CAPSULE_DIGEST")
        if not isinstance(payload["deadline_ms"], int) or isinstance(
            payload["deadline_ms"], bool
        ):
            raise IPCError("INVALID_DEADLINE")
        for list_field in ("source_refs", "dependency_ids"):
            if list_field in payload:
                values = payload[list_field]
                if not isinstance(values, list) or len(values) > 256:
                    raise IPCError("INVALID_" + list_field.upper())
                for value in values:
                    _validate_ref(list_field[:-1], value)
        if "body_ref" in payload:
            _validate_ref("body_ref", payload["body_ref"])
        return
    if message_type in {"WORK_STATUS", "WORK_CANCEL"}:
        _require_exact_payload(
            payload,
            ("capsule_id",),
            ("reason_code",) if message_type == "WORK_CANCEL" else (),
        )
        _validate_ref("capsule_id", payload["capsule_id"])
        if "reason_code" in payload:
            _validate_ref("reason_code", payload["reason_code"])
        return
    if message_type == "ADMIN_DRAIN":
        _require_exact_payload(payload, ("reason_code",))
        _validate_ref("reason_code", payload["reason_code"])
        return
    raise IPCError("UNKNOWN_MESSAGE_TYPE")


def validate_envelope(obj: Dict[str, Any]) -> Dict[str, Any]:
    _walk_limits(obj)
    keys = set(obj)
    if REQUIRED_TOP_LEVEL_FIELDS - keys:
        raise IPCError("MISSING_REQUIRED_FIELD")
    if keys - TOP_LEVEL_FIELDS:
        raise IPCError("UNKNOWN_TOP_LEVEL_FIELD")
    if obj["protocol_version"] != PROTOCOL_VERSION:
        raise IPCError("UNSUPPORTED_PROTOCOL_VERSION")
    if not isinstance(obj["message_type"], str) or obj["message_type"] not in ALLOWED_TYPES:
        raise IPCError("UNKNOWN_MESSAGE_TYPE")
    if not isinstance(obj["request_id"], str) or not REQUEST_ID_RE.fullmatch(
        obj["request_id"]
    ):
        raise IPCError("INVALID_REQUEST_ID")
    _validate_ref("generation", obj["generation"])
    _validate_ref("authority_ref", obj["authority_ref"])
    _validate_ref("currentness_ref", obj["currentness_ref"])
    for field_name in ("issued_at_ms", "expires_at_ms"):
        if not isinstance(obj[field_name], int) or isinstance(obj[field_name], bool):
            raise IPCError("INVALID_" + field_name.upper())
    if obj["expires_at_ms"] < obj["issued_at_ms"]:
        raise IPCError("INVALID_EXPIRY_WINDOW")
    if not isinstance(obj["payload"], dict):
        raise IPCError("PAYLOAD_NOT_OBJECT")
    if "extensions" in obj:
        if not isinstance(obj["extensions"], dict):
            raise IPCError("EXTENSIONS_NOT_OBJECT")
        if obj["extensions"]:
            # No extension wire is authority-reviewed yet. Empty is accepted for
            # forward framing compatibility; non-empty extensions fail closed.
            raise IPCError("EXTENSIONS_UNSUPPORTED")
    _validate_payload(obj["message_type"], obj["payload"])
    return dict(obj)


@dataclass
class WorkRecord:
    state: str
    owner_uid: int
    terminal_at_ms: int | None = None


# request_id -> (request_digest, immutable decision receipt, retain_until_ms,
#                generation, currentness_ref, authority_ref, authorized_peer_uid)
SeenRecord = Tuple[str, Dict[str, Any], int, str, str, str, int]


@dataclass
class ResidentState:
    generation: str
    currentness_ref: str
    authority_ref: str
    owner_uid: int
    state_epoch: int = 1
    draining: bool = False
    work_records: Dict[str, WorkRecord] = field(default_factory=dict)
    seen: Dict[str, SeenRecord] = field(default_factory=dict)
    # capsule_id -> (capsule_digest, generation, currentness_ref, authority_ref)
    # The fence is generation-scoped. currentness_ref/authority_ref are retained
    # as provenance of first acceptance, but only a generation transition may
    # retire the fence.
    capsule_identities: Dict[str, Tuple[str, str, str, str]] = field(
        default_factory=dict
    )
    _lock: threading.RLock = field(
        default_factory=threading.RLock, repr=False, compare=False
    )

    def __setattr__(self, name: str, value: Any) -> None:
        if name in IDENTITY_DOMAIN_FIELDS and name in self.__dict__:
            raise AttributeError("IDENTITY_DOMAIN_DIRECT_MUTATION_FORBIDDEN")
        object.__setattr__(self, name, value)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "generation": self.generation,
                "currentness_ref": self.currentness_ref,
                "authority_ref": self.authority_ref,
                "state_epoch": self.state_epoch,
                "draining": self.draining,
                "accepted_work_count": sum(
                    1
                    for record in self.work_records.values()
                    if record.state == "ACCEPTED"
                ),
                "tracked_work_count": len(self.work_records),
                "capsule_identity_count": len(self.capsule_identities),
            }


def _clone_jsonable(value: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(canonical_json_bytes(value).decode("utf-8"))


def _decision_receipt(
    req: Dict[str, Any],
    state: ResidentState,
    decision: str,
    reason: str,
    result=None,
) -> Dict[str, Any]:
    core = {
        "receipt_version": RECEIPT_VERSION,
        "request_id": req.get("request_id", "UNBOUND"),
        "request_digest": sha256_hex(canonical_json_bytes(req)),
        "decision": decision,
        "reason_code": reason,
        "state_snapshot": state.snapshot(),
        "result": dict(result or {}),
    }
    core["decision_digest"] = sha256_hex(canonical_json_bytes(core))
    return core


def _prune_seen(state: ResidentState, now_ms: int) -> int:
    stale = [
        request_id
        for request_id, record in state.seen.items()
        if record[2] < now_ms
        or record[3] != state.generation
        or record[4] != state.currentness_ref
        or record[5] != state.authority_ref
    ]
    for request_id in stale:
        del state.seen[request_id]
    return len(stale)


def _prune_work_records(state: ResidentState, now_ms: int) -> int:
    removed = 0
    expired = [
        capsule_id
        for capsule_id, record in state.work_records.items()
        if record.state != "ACCEPTED"
        and record.terminal_at_ms is not None
        and record.terminal_at_ms + TERMINAL_WORK_RETENTION_MS < now_ms
    ]
    for capsule_id in expired:
        del state.work_records[capsule_id]
        removed += 1

    terminals = sorted(
        (
            (record.terminal_at_ms or 0, capsule_id)
            for capsule_id, record in state.work_records.items()
            if record.state != "ACCEPTED"
        ),
        key=lambda pair: (pair[0], pair[1]),
    )
    overflow = max(0, len(terminals) - MAX_TERMINAL_WORK_RECORDS)
    for _terminal_at, capsule_id in terminals[:overflow]:
        del state.work_records[capsule_id]
        removed += 1
    return removed


def _prune_capsule_identities(state: ResidentState) -> int:
    """Drop capsule fences only after an explicit generation transition."""
    stale = [
        capsule_id
        for capsule_id, record in state.capsule_identities.items()
        if record[1] != state.generation
    ]
    for capsule_id in stale:
        del state.capsule_identities[capsule_id]
    return len(stale)


def rebase_identity_domain(
    state: ResidentState,
    *,
    generation: str,
    currentness_ref: str,
    authority_ref: str,
) -> Dict[str, Any]:
    """Atomically rebind Resident identity witnesses and retire old-generation fences.

    currentness/authority changes within one generation do not release capsule-ID
    history. An actual generation transition updates all three witnesses and
    retires only the previous generation's capsule fences under the same lock
    used by consequence processing.
    """
    _validate_ref("generation", generation)
    _validate_ref("currentness_ref", currentness_ref)
    _validate_ref("authority_ref", authority_ref)
    with state._lock:
        generation_changed = generation != state.generation
        changed = (
            generation_changed
            or currentness_ref != state.currentness_ref
            or authority_ref != state.authority_ref
        )
        object.__setattr__(state, "generation", generation)
        object.__setattr__(state, "currentness_ref", currentness_ref)
        object.__setattr__(state, "authority_ref", authority_ref)
        if generation_changed:
            _prune_capsule_identities(state)
        if changed:
            state.state_epoch += 1
        return state.snapshot()


def _capsule_has_live_effect_history(state: ResidentState, capsule_id: str) -> bool:
    for record in state.seen.values():
        result = record[1].get("result")
        if isinstance(result, dict) and result.get("capsule_id") == capsule_id:
            return True
    return False


def _cache_effect_receipt(
    state: ResidentState,
    req: Dict[str, Any],
    digest: str,
    receipt: Dict[str, Any],
    peer_uid: int,
) -> None:
    state.seen[req["request_id"]] = (
        digest,
        _clone_jsonable(receipt),
        req["expires_at_ms"],
        req["generation"],
        req["currentness_ref"],
        req["authority_ref"],
        peer_uid,
    )


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _process_request(
    raw: Dict[str, Any],
    state: ResidentState,
    sock: socket.socket,
) -> Dict[str, Any]:
    """Process one consequence against identity/time derived inside the trusted seam.

    There is deliberately no peer UID or caller-supplied timestamp parameter.
    ``get_peer_uid`` reads SO_PEERCRED from ``sock`` and ``_now_ms`` is sampled
    when this function starts, which is after ``serve_connected_once`` has
    completed frame receipt.
    """
    peer_uid = get_peer_uid(sock)
    now_ms = _now_ms()
    req = validate_envelope(raw)
    digest = sha256_hex(canonical_json_bytes(req))
    request_id = req["request_id"]

    with state._lock:
        _prune_seen(state, now_ms)
        _prune_work_records(state, now_ms)
        _prune_capsule_identities(state)

        def reject(reason: str, result=None) -> Dict[str, Any]:
            # Rejections do not occupy the effect-idempotency ledger.
            return _decision_receipt(req, state, "REJECT", reason, result)

        # Use-time source/authority/time checks precede replay resolution.
        if req["generation"] != state.generation:
            return reject("STALE_OR_FOREIGN_GENERATION")
        if req["currentness_ref"] != state.currentness_ref:
            return reject("CURRENTNESS_MISMATCH")
        if req["authority_ref"] != state.authority_ref:
            return reject("AUTHORITY_MISMATCH")
        if now_ms < req["issued_at_ms"]:
            return reject("REQUEST_NOT_YET_VALID")
        if now_ms > req["expires_at_ms"]:
            return reject("REQUEST_EXPIRED")
        if req["message_type"] in ADMIN_TYPES and peer_uid != state.owner_uid:
            return reject("ADMIN_PEER_NOT_OWNER")

        prior = state.seen.get(request_id)
        if prior:
            if prior[0] != digest:
                return reject("REQUEST_ID_COLLISION")
            if prior[6] != peer_uid:
                return reject("REPLAY_PEER_MISMATCH")
            return _clone_jsonable(prior[1])

        message_type = req["message_type"]
        payload = req["payload"]

        if message_type == "HEALTH":
            return _decision_receipt(
                req, state, "ACCEPT", "HEALTH_OK", {"healthy": True}
            )
        if message_type == "STATUS":
            return _decision_receipt(
                req, state, "ACCEPT", "STATUS_OK", state.snapshot()
            )
        if message_type == "WORK_STATUS":
            capsule_id = payload["capsule_id"]
            record = state.work_records.get(capsule_id)
            return _decision_receipt(
                req,
                state,
                "ACCEPT",
                "WORK_STATUS_OK",
                {
                    "capsule_id": capsule_id,
                    "work_state": record.state if record else "UNKNOWN",
                },
            )

        # Only consequence-bearing operations consume the idempotency ledger.
        # Capacity is reclaimable by request expiry or generation/currentness/authority rebase.
        if len(state.seen) >= MAX_SEEN_REQUESTS:
            return reject("IDEMPOTENCY_CAPACITY_EXHAUSTED")

        if message_type == "WORK_SUBMIT":
            if state.draining:
                return reject("RESIDENT_DRAINING")
            if payload["deadline_ms"] < now_ms:
                return reject("WORK_DEADLINE_EXPIRED")
            capsule_id = payload["capsule_id"]
            if capsule_id in state.work_records:
                return reject("CAPSULE_ALREADY_TRACKED")
            if _capsule_has_live_effect_history(state, capsule_id):
                return reject("CAPSULE_HISTORY_RETAINED")
            prior_identity = state.capsule_identities.get(capsule_id)
            if prior_identity is not None:
                if prior_identity[0] != payload["capsule_digest"]:
                    return reject("CAPSULE_IDENTITY_CONFLICT")
                return reject("CAPSULE_IDENTITY_REUSED")
            active_count = sum(
                1
                for record in state.work_records.values()
                if record.state == "ACCEPTED"
            )
            if active_count >= MAX_TRACKED_WORK:
                return reject("WORK_CAPACITY_EXHAUSTED")
            if len(state.capsule_identities) >= MAX_CAPSULE_IDENTITIES:
                return reject("CAPSULE_IDENTITY_CAPACITY_EXHAUSTED")
            state.capsule_identities[capsule_id] = (
                payload["capsule_digest"],
                state.generation,
                state.currentness_ref,
                state.authority_ref,
            )
            state.work_records[capsule_id] = WorkRecord("ACCEPTED", peer_uid)
            state.state_epoch += 1
            receipt = _decision_receipt(
                req,
                state,
                "ACCEPT",
                "WORK_ACCEPTED",
                {"capsule_id": capsule_id, "route_ref": payload["route_ref"]},
            )
            _cache_effect_receipt(state, req, digest, receipt, peer_uid)
            return receipt

        if message_type == "WORK_CANCEL":
            capsule_id = payload["capsule_id"]
            record = state.work_records.get(capsule_id)
            if record is None:
                return reject("CAPSULE_UNKNOWN")
            if peer_uid not in {state.owner_uid, record.owner_uid}:
                return reject("CANCEL_PEER_NOT_AUTHORIZED")
            if record.state != "ACCEPTED":
                return reject("CAPSULE_NOT_ACTIVE")
            record.state = "CANCELLED"
            record.terminal_at_ms = now_ms
            state.state_epoch += 1
            _prune_work_records(state, now_ms)
            receipt = _decision_receipt(
                req,
                state,
                "ACCEPT",
                "WORK_CANCELLED",
                {"capsule_id": capsule_id},
            )
            _cache_effect_receipt(state, req, digest, receipt, peer_uid)
            return receipt

        if message_type == "ADMIN_DRAIN":
            state.draining = True
            state.state_epoch += 1
            receipt = _decision_receipt(req, state, "ACCEPT", "DRAIN_ENABLED")
            _cache_effect_receipt(state, req, digest, receipt, peer_uid)
            return receipt

        if message_type == "ADMIN_RECONCILE":
            state.state_epoch += 1
            receipt = _decision_receipt(req, state, "ACCEPT", "RECONCILE_MARKED")
            _cache_effect_receipt(state, req, digest, receipt, peer_uid)
            return receipt

        return reject("UNKNOWN_MESSAGE_TYPE")


def make_unix_listener(path: str, backlog: int = 32) -> socket.socket:
    if not hasattr(socket, "AF_UNIX"):
        raise RuntimeError("AF_UNIX unavailable")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(path)
        listener.listen(backlog)
        return listener
    except Exception:
        listener.close()
        raise


def get_peer_uid(sock: socket.socket) -> int:
    """Return the kernel-witnessed UID for the active Linux/WSL AF_UNIX peer."""
    if not hasattr(socket, "SO_PEERCRED"):
        raise IPCError("PEER_CREDENTIALS_UNAVAILABLE")
    raw = sock.getsockopt(
        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
    )
    _pid, uid, _gid = struct.unpack("3i", raw)
    return uid


class ConnectionGate:
    """Fail-closed bounded active-connection gate for server wrappers."""

    def __init__(self, limit: int = MAX_ACTIVE_CONNECTIONS):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        self.limit = limit
        self._semaphore = threading.BoundedSemaphore(limit)

    @contextmanager
    def slot(self):
        if not self._semaphore.acquire(blocking=False):
            raise IPCError("CONNECTION_CAPACITY_EXHAUSTED")
        try:
            yield
        finally:
            self._semaphore.release()


def serve_connected_once(
    sock: socket.socket,
    state: ResidentState,
    gate: ConnectionGate,
    frame_timeout_seconds: float = FRAME_RECEIVE_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Serve exactly one connected AF_UNIX peer under bounded liveness/authority.

    The complete frame is received before identity/time-bound consequence
    processing begins. The caller cannot supply an authorization UID or stale
    processing timestamp.
    """
    with gate.slot():
        req = recv_frame(sock, timeout_seconds=frame_timeout_seconds)
        receipt = _process_request(req, state, sock)
        send_frame(sock, receipt)
        return receipt