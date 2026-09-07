from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "AuraTerminalBusResponseV1"
VERSION = "PROJECT006_TERMINAL_OUTBOX_V1"
TERMINAL_KINDS = frozenset({
    "ACK_ACCEPTED_PRE_EFFECT", "SCHEMA_REJECTED", "AUTHORITY_REJECTED",
    "IDEMPOTENCY_REJECTED", "IDEMPOTENT_REPLAY", "CURRENTNESS_REJECTED",
    "STALE_REOPEN", "CAPABILITY_REJECTED", "ADMISSION_BLOCKED", "COMMAND_BLOCKED",
    "EXECUTOR_ERROR", "COMPLETION_AMBIGUOUS", "RESULT",
})
NEGATIVE_KINDS = TERMINAL_KINDS - {"ACK_ACCEPTED_PRE_EFFECT", "RESULT"}

class TxState(str, Enum):
    INGESTED = "INGESTED"
    DECIDED_TERMINAL = "DECIDED_TERMINAL"
    RETURN_PENDING = "RETURN_PENDING"
    ACK_WRITTEN_PRE_EFFECT = "ACK_WRITTEN_PRE_EFFECT"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    RESULT_OBSERVED = "RESULT_OBSERVED"
    ERROR_TERMINAL = "ERROR_TERMINAL"
    COMPLETION_AMBIGUOUS = "COMPLETION_AMBIGUOUS"
    RETURN_WRITTEN = "RETURN_WRITTEN"

@dataclass(frozen=True)
class CommandIdentity:
    command_id: str
    idempotency_key: str
    source_file_id: str
    source_revision: str
    source_digest: str

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, str) or not value or len(value) > 2048:
                raise ValueError(f"INVALID_{name.upper()}")

@dataclass(frozen=True)
class TerminalResponse:
    identity: CommandIdentity
    kind: str
    first_failing_gate: str | None = None
    provider_request_count: int = 0
    payload: Mapping[str, Any] | None = None

    def canonical(self) -> dict[str, Any]:
        self.identity.validate()
        if self.kind not in TERMINAL_KINDS:
            raise ValueError("UNSUPPORTED_TERMINAL_KIND")
        if type(self.provider_request_count) is not int or self.provider_request_count < 0:
            raise ValueError("INVALID_PROVIDER_REQUEST_COUNT")
        if self.kind in NEGATIVE_KINDS and self.provider_request_count != 0:
            raise ValueError("NEGATIVE_RESPONSE_HAS_PROVIDER_EFFECT")
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "command_id": self.identity.command_id,
            "idempotency_key": self.identity.idempotency_key,
            "source_file_id": self.identity.source_file_id,
            "source_revision": self.identity.source_revision,
            "source_digest": self.identity.source_digest,
            "kind": self.kind,
            "first_failing_gate": self.first_failing_gate,
            "provider_request_count": self.provider_request_count,
            "payload": dict(self.payload or {}),
        }

    def digest(self) -> str:
        body = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return hashlib.sha256(body.encode()).hexdigest()

class OutboxJournal:
    """Durable transaction journal separating provider terminality from Drive return.

    The provider effect is never invoked by this class. A caller may record ACK/EXECUTION/RESULT,
    but retries here only retry the outbound writer for an already-decided response.
    """
    def __init__(self, path: str | Path):
        self.path = str(path)
        con = sqlite3.connect(self.path)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("""CREATE TABLE IF NOT EXISTS tx(
              command_id TEXT PRIMARY KEY,
              idempotency_key TEXT NOT NULL,
              source_digest TEXT NOT NULL,
              state TEXT NOT NULL,
              response_digest TEXT,
              response_json TEXT,
              outbound_ref TEXT,
              writer_attempts INTEGER NOT NULL DEFAULT 0
            )""")
            con.commit()
        finally:
            con.close()

    def _con(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def ingest(self, ident: CommandIdentity) -> None:
        ident.validate()
        with self._con() as con:
            row = con.execute("SELECT * FROM tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                con.execute("INSERT INTO tx(command_id,idempotency_key,source_digest,state) VALUES(?,?,?,?)",
                            (ident.command_id, ident.idempotency_key, ident.source_digest, TxState.INGESTED.value))
                return
            if row["idempotency_key"] != ident.idempotency_key or row["source_digest"] != ident.source_digest:
                raise ValueError("IDEMPOTENCY_CONFLICT")

    def stage_terminal(self, response: TerminalResponse) -> str:
        canonical = response.canonical()
        digest = response.digest()
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.ingest(response.identity)
        with self._con() as con:
            row = con.execute("SELECT * FROM tx WHERE command_id=?", (response.identity.command_id,)).fetchone()
            if row["state"] == TxState.RETURN_WRITTEN.value:
                if row["response_digest"] != digest:
                    raise ValueError("TERMINAL_EQUIVOCATION")
                return digest
            if row["response_digest"] and row["response_digest"] != digest:
                raise ValueError("TERMINAL_EQUIVOCATION")
            con.execute("UPDATE tx SET state=?,response_digest=?,response_json=? WHERE command_id=?",
                        (TxState.RETURN_PENDING.value, digest, encoded, response.identity.command_id))
        return digest

    def publish_pending(self, command_id: str, writer: Callable[[Mapping[str, Any]], str]) -> str:
        with self._con() as con:
            row = con.execute("SELECT * FROM tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None:
                raise ValueError("COMMAND_NOT_INGESTED")
            if row["state"] == TxState.RETURN_WRITTEN.value:
                return str(row["outbound_ref"])
            if not row["response_json"]:
                raise ValueError("NO_TERMINAL_RESPONSE")
            con.execute("UPDATE tx SET writer_attempts=writer_attempts+1 WHERE command_id=?", (command_id,))
            payload = json.loads(row["response_json"])
        ref = writer(payload)
        if not isinstance(ref, str) or not ref:
            raise ValueError("WRITER_DID_NOT_RETURN_REF")
        with self._con() as con:
            row2 = con.execute("SELECT * FROM tx WHERE command_id=?", (command_id,)).fetchone()
            if row2["response_digest"] != hashlib.sha256(row2["response_json"].encode()).hexdigest():
                raise ValueError("DURABLE_RESPONSE_CORRUPT")
            con.execute("UPDATE tx SET state=?,outbound_ref=? WHERE command_id=?",
                        (TxState.RETURN_WRITTEN.value, ref, command_id))
        return ref

    def status(self, command_id: str) -> dict[str, Any]:
        with self._con() as con:
            row = con.execute("SELECT * FROM tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None:
                raise ValueError("COMMAND_NOT_INGESTED")
            return dict(row)

class BusWriterCLI:
    """Adapter for the installed bounded writer using JSON stdin."""
    def __init__(self, argv: Sequence[str], *, timeout_s: int = 60):
        if not argv or any(not isinstance(x, str) or not x for x in argv):
            raise ValueError("INVALID_WRITER_ARGV")
        self.argv = tuple(argv)
        self.timeout_s = timeout_s

    def __call__(self, payload: Mapping[str, Any]) -> str:
        p = subprocess.run(self.argv, input=json.dumps(payload, sort_keys=True)+"\n", text=True,
                           capture_output=True, timeout=self.timeout_s, check=False)
        if p.returncode != 0:
            raise RuntimeError("BUS_WRITER_FAILED")
        out = p.stdout.strip()
        if not out:
            raise RuntimeError("BUS_WRITER_EMPTY")
        try:
            obj = json.loads(out.splitlines()[-1])
            if isinstance(obj, dict):
                for key in ("file_id", "drive_file_id", "outbound_ref", "id"):
                    val = obj.get(key)
                    if isinstance(val, str) and val:
                        return val
        except json.JSONDecodeError:
            pass
        return out.splitlines()[-1]
