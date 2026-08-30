from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from gemini_webchat_endpoint import (
    ArenaTurnEnvelopeV1,
    ArenaTurnResultV1,
    AuraToolRequestV1,
    AuraToolResultV1,
    BridgeLedgerV1,
    BridgeRefusal,
    EndpointBindingV1,
    admit_result,
    admit_tool_request,
    admit_turn,
    canonical_json,
    sha256_text,
)


class RelayStoreV1:
    """Append-only filesystem transport for one local browser bridge instance.

    This store deliberately does not automate Gemini. It provides durable, atomic,
    replay-resistant handoff objects for a browser extension/native-message host.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.turn_outbox = self.root / "turn_outbox"
        self.turn_results = self.root / "turn_results"
        self.tool_requests = self.root / "tool_requests"
        self.tool_results = self.root / "tool_results"
        self.receipts = self.root / "receipts"
        self.state_dir = self.root / "state"
        for path in (
            self.turn_outbox,
            self.turn_results,
            self.tool_requests,
            self.tool_results,
            self.receipts,
            self.state_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.state_dir / "bridge_ledger_v1.json"
        self.binding_path = self.state_dir / "endpoint_binding_v1.json"
        self._ledger = self._load_ledger()

    def _atomic_create_json(self, path: Path, payload: Mapping[str, Any]) -> str:
        """Create-once atomic publish. Existing path is a replay/collision."""
        if path.exists():
            raise BridgeRefusal("RELAY_OBJECT_ALREADY_EXISTS", path.name)
        data = (canonical_json(payload) + "\n").encode("utf-8")
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(tmp_name, path)
            except FileExistsError as exc:
                raise BridgeRefusal("RELAY_OBJECT_ALREADY_EXISTS", path.name) from exc
            landed = path.read_bytes()
            if landed != data:
                path.unlink(missing_ok=True)
                raise BridgeRefusal("RELAY_LANDED_BYTES_MISMATCH", path.name)
            return sha256_text(landed.decode("utf-8"))
        finally:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass

    def _replace_state_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        data = (canonical_json(payload) + "\n").encode("utf-8")
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass

    def _load_ledger(self) -> BridgeLedgerV1:
        if not self.ledger_path.exists():
            return BridgeLedgerV1()
        data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        if data.get("schema") != "BridgeLedgerV1":
            raise BridgeRefusal("RELAY_LEDGER_SCHEMA_MISMATCH", str(data.get("schema")))
        return BridgeLedgerV1(
            sent_turn_ids=set(data.get("sent_turn_ids", [])),
            completed_turn_ids=set(data.get("completed_turn_ids", [])),
            accepted_tool_request_ids=set(data.get("accepted_tool_request_ids", [])),
        )

    def _persist_ledger(self) -> None:
        self._replace_state_json(self.ledger_path, self._ledger.to_dict())

    def bind_endpoint(self, binding: EndpointBindingV1) -> str:
        binding.validate()
        payload = {"schema": "EndpointBindingV1", **asdict(binding)}
        digest = sha256_text(canonical_json(payload))
        if self.binding_path.exists():
            existing = json.loads(self.binding_path.read_text(encoding="utf-8"))
            if existing != payload:
                raise BridgeRefusal("ENDPOINT_REBIND_REQUIRES_EXPLICIT_RELEASE", binding.endpoint_id)
            return digest
        self._replace_state_json(self.binding_path, payload)
        return digest

    def load_binding(self) -> EndpointBindingV1:
        if not self.binding_path.exists():
            raise BridgeRefusal("ENDPOINT_NOT_BOUND")
        data = json.loads(self.binding_path.read_text(encoding="utf-8"))
        if data.pop("schema", None) != "EndpointBindingV1":
            raise BridgeRefusal("ENDPOINT_BINDING_SCHEMA_MISMATCH")
        binding = EndpointBindingV1(**data)
        binding.validate()
        return binding

    def release_endpoint(self, *, endpoint_id: str, visit_id: str) -> None:
        binding = self.load_binding()
        if binding.endpoint_id != endpoint_id or binding.visit_id != visit_id:
            raise BridgeRefusal("ENDPOINT_RELEASE_BINDING_MISMATCH", endpoint_id)
        self.binding_path.unlink()

    def publish_turn(
        self,
        envelope: ArenaTurnEnvelopeV1,
        *,
        current_arena_head: str,
        currentness_hash: str,
    ) -> Dict[str, str]:
        binding = self.load_binding()
        admit_turn(
            binding,
            envelope,
            current_arena_head=current_arena_head,
            currentness_hash=currentness_hash,
        )
        self._ledger.mark_turn_sent(envelope.turn_id)
        payload = {"schema": "ArenaTurnEnvelopeV1", **asdict(envelope)}
        path = self.turn_outbox / f"{envelope.turn_id}.json"
        try:
            digest = self._atomic_create_json(path, payload)
        except Exception:
            self._ledger.sent_turn_ids.discard(envelope.turn_id)
            raise
        self._persist_ledger()
        receipt = self._write_receipt(
            event="TURN_PUBLISHED",
            object_id=envelope.turn_id,
            object_digest=digest,
            endpoint_id=binding.endpoint_id,
            visit_id=binding.visit_id,
        )
        return {"path": str(path), "digest": digest, "receipt": receipt}

    def accept_turn_result(
        self,
        envelope: ArenaTurnEnvelopeV1,
        result: ArenaTurnResultV1,
        *,
        current_arena_head: str,
        currentness_hash: str,
    ) -> Dict[str, str]:
        binding = self.load_binding()
        admit_result(
            binding,
            envelope,
            result,
            current_arena_head=current_arena_head,
            currentness_hash=currentness_hash,
        )
        self._ledger.accept_result(result)
        payload = {"schema": "ArenaTurnResultV1", **asdict(result)}
        path = self.turn_results / f"{result.turn_id}.json"
        try:
            digest = self._atomic_create_json(path, payload)
        except Exception:
            self._ledger.completed_turn_ids.discard(result.turn_id)
            raise
        self._persist_ledger()
        receipt = self._write_receipt(
            event="TURN_RESULT_ACCEPTED",
            object_id=result.turn_id,
            object_digest=digest,
            endpoint_id=binding.endpoint_id,
            visit_id=binding.visit_id,
        )
        return {"path": str(path), "digest": digest, "receipt": receipt}

    def accept_tool_request(
        self,
        envelope: ArenaTurnEnvelopeV1,
        request: AuraToolRequestV1,
        *,
        current_arena_head: str,
        currentness_hash: str,
        tool_effect_classes: Mapping[str, str],
    ) -> Dict[str, str]:
        admit_tool_request(
            envelope,
            request,
            current_arena_head=current_arena_head,
            currentness_hash=currentness_hash,
            tool_effect_classes=tool_effect_classes,
        )
        self._ledger.accept_tool_request(request)
        payload = {"schema": "AuraToolRequestV1", **asdict(request)}
        path = self.tool_requests / f"{request.request_id}.json"
        try:
            digest = self._atomic_create_json(path, payload)
        except Exception:
            self._ledger.accepted_tool_request_ids.discard(request.request_id)
            raise
        self._persist_ledger()
        receipt = self._write_receipt(
            event="TOOL_REQUEST_ACCEPTED",
            object_id=request.request_id,
            object_digest=digest,
            endpoint_id=self.load_binding().endpoint_id,
            visit_id=self.load_binding().visit_id,
        )
        return {"path": str(path), "digest": digest, "receipt": receipt}

    def publish_tool_result(self, result: AuraToolResultV1) -> Dict[str, str]:
        result.validate()
        if result.request_id not in self._ledger.accepted_tool_request_ids:
            raise BridgeRefusal("TOOL_RESULT_WITHOUT_ACCEPTED_REQUEST", result.request_id)
        payload = {"schema": "AuraToolResultV1", **asdict(result)}
        path = self.tool_results / f"{result.request_id}.json"
        digest = self._atomic_create_json(path, payload)
        binding = self.load_binding()
        receipt = self._write_receipt(
            event="TOOL_RESULT_PUBLISHED",
            object_id=result.request_id,
            object_digest=digest,
            endpoint_id=binding.endpoint_id,
            visit_id=binding.visit_id,
        )
        return {"path": str(path), "digest": digest, "receipt": receipt}

    def list_pending_turns(self) -> Iterable[Path]:
        completed = self._ledger.completed_turn_ids
        return tuple(
            path for path in sorted(self.turn_outbox.glob("*.json")) if path.stem not in completed
        )

    def _write_receipt(
        self,
        *,
        event: str,
        object_id: str,
        object_digest: str,
        endpoint_id: str,
        visit_id: str,
    ) -> str:
        receipt_payload = {
            "schema": "GeminiWebchatRelayReceiptV1",
            "event": event,
            "object_id": object_id,
            "object_digest": object_digest,
            "endpoint_id": endpoint_id,
            "visit_id": visit_id,
        }
        receipt_id = sha256_text(canonical_json(receipt_payload))[:24]
        path = self.receipts / f"{receipt_id}.json"
        if not path.exists():
            self._atomic_create_json(path, receipt_payload)
        return str(path)
