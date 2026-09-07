from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA = "AuraTerminalBusResponseV1"
VERSION = "PROJECT006_TERMINAL_OUTBOX_V3"
TERMINAL_KINDS = frozenset({
    "ACK_ACCEPTED_PRE_EFFECT", "SCHEMA_REJECTED", "AUTHORITY_REJECTED",
    "IDEMPOTENCY_REJECTED", "IDEMPOTENT_REPLAY", "CURRENTNESS_REJECTED",
    "STALE_REOPEN", "CAPABILITY_REJECTED", "ADMISSION_BLOCKED", "COMMAND_BLOCKED",
    "EXECUTOR_ERROR", "COMPLETION_AMBIGUOUS", "RESULT",
})
PRE_EFFECT_ZERO_PROVIDER_KINDS = frozenset({
    "ACK_ACCEPTED_PRE_EFFECT", "SCHEMA_REJECTED", "AUTHORITY_REJECTED",
    "IDEMPOTENCY_REJECTED", "CURRENTNESS_REJECTED", "STALE_REOPEN",
    "CAPABILITY_REJECTED", "ADMISSION_BLOCKED", "COMMAND_BLOCKED",
})
FINAL_TERMINAL_KINDS = TERMINAL_KINDS - {"ACK_ACCEPTED_PRE_EFFECT"}
NEGATIVE_KINDS = PRE_EFFECT_ZERO_PROVIDER_KINDS - {"ACK_ACCEPTED_PRE_EFFECT"}


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


class AckState(str, Enum):
    STAGED = "STAGED"
    WRITE_INFLIGHT = "WRITE_INFLIGHT"
    WRITE_AMBIGUOUS = "WRITE_AMBIGUOUS"
    WRITTEN = "WRITTEN"


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
        if self.kind in PRE_EFFECT_ZERO_PROVIDER_KINDS and self.provider_request_count != 0:
            raise ValueError("NEGATIVE_RESPONSE_HAS_PROVIDER_EFFECT")
        if self.kind == "COMPLETION_AMBIGUOUS" and self.provider_request_count < 1:
            raise ValueError("AMBIGUOUS_COMPLETION_REQUIRES_EFFECT_ATTEMPT")
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
    """Durable final-return journal plus a distinct ACK publication table.

    ACK remains nonterminal. The ACK table exists only to migrate legacy receipt
    publication safely: it commits WRITE_INFLIGHT before calling the external
    writer, so a crash cannot turn unknown ACK delivery into blind resend.
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
            con.execute("""CREATE TABLE IF NOT EXISTS ack_tx(
              command_id TEXT PRIMARY KEY,
              idempotency_key TEXT NOT NULL,
              source_digest TEXT NOT NULL,
              state TEXT NOT NULL,
              response_digest TEXT NOT NULL,
              response_json TEXT NOT NULL,
              outbound_ref TEXT,
              writer_attempts INTEGER NOT NULL DEFAULT 0
            )""")
            con.commit()
        finally:
            con.close()

    @contextmanager
    def _con(self, *, immediate: bool = False):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            if immediate:
                con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

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
        if response.kind not in FINAL_TERMINAL_KINDS:
            raise ValueError("ACK_IS_NOT_TERMINAL_RETURN")
        canonical = response.canonical()
        response_digest = response.digest()
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.ingest(response.identity)
        with self._con() as con:
            row = con.execute("SELECT * FROM tx WHERE command_id=?", (response.identity.command_id,)).fetchone()
            if row["state"] == TxState.RETURN_WRITTEN.value:
                if row["response_digest"] != response_digest:
                    raise ValueError("TERMINAL_EQUIVOCATION")
                return response_digest
            if row["response_digest"] and row["response_digest"] != response_digest:
                raise ValueError("TERMINAL_EQUIVOCATION")
            con.execute("UPDATE tx SET state=?,response_digest=?,response_json=? WHERE command_id=?",
                        (TxState.RETURN_PENDING.value, response_digest, encoded, response.identity.command_id))
        return response_digest

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

    def stage_ack(self, response: TerminalResponse) -> str:
        if response.kind != "ACK_ACCEPTED_PRE_EFFECT":
            raise ValueError("NOT_ACK_RESPONSE")
        canonical = response.canonical()
        response_digest = response.digest()
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM ack_tx WHERE command_id=?", (response.identity.command_id,)).fetchone()
            if row is None:
                con.execute("""INSERT INTO ack_tx(command_id,idempotency_key,source_digest,state,response_digest,response_json)
                               VALUES(?,?,?,?,?,?)""",
                            (response.identity.command_id, response.identity.idempotency_key, response.identity.source_digest,
                             AckState.STAGED.value, response_digest, encoded))
                return response_digest
            if row["idempotency_key"] != response.identity.idempotency_key or row["source_digest"] != response.identity.source_digest:
                raise ValueError("ACK_IDENTITY_CONFLICT")
            if row["response_digest"] != response_digest:
                raise ValueError("ACK_EQUIVOCATION")
            return response_digest

    def publish_ack_pending(self, command_id: str, writer: Callable[[Mapping[str, Any]], str]) -> str:
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM ack_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None:
                raise ValueError("ACK_NOT_STAGED")
            state = AckState(row["state"])
            if state is AckState.WRITTEN:
                return str(row["outbound_ref"])
            if state in (AckState.WRITE_INFLIGHT, AckState.WRITE_AMBIGUOUS):
                raise ValueError("ACK_RECONCILIATION_REQUIRED")
            con.execute("UPDATE ack_tx SET state=?,writer_attempts=writer_attempts+1 WHERE command_id=?",
                        (AckState.WRITE_INFLIGHT.value, command_id))
            payload = json.loads(row["response_json"])
        try:
            ref = writer(payload)
        except Exception:
            with self._con(immediate=True) as con:
                row2 = con.execute("SELECT * FROM ack_tx WHERE command_id=?", (command_id,)).fetchone()
                if row2 is not None and row2["state"] == AckState.WRITE_INFLIGHT.value:
                    con.execute("UPDATE ack_tx SET state=? WHERE command_id=?",
                                (AckState.WRITE_AMBIGUOUS.value, command_id))
            raise
        if not isinstance(ref, str) or not ref:
            with self._con(immediate=True) as con:
                con.execute("UPDATE ack_tx SET state=? WHERE command_id=?",
                            (AckState.WRITE_AMBIGUOUS.value, command_id))
            raise ValueError("ACK_WRITER_DID_NOT_RETURN_REF")
        with self._con(immediate=True) as con:
            row3 = con.execute("SELECT * FROM ack_tx WHERE command_id=?", (command_id,)).fetchone()
            if row3 is None or row3["state"] != AckState.WRITE_INFLIGHT.value:
                raise ValueError("ACK_CONFIRMATION_STATE_MOVED")
            con.execute("UPDATE ack_tx SET state=?,outbound_ref=? WHERE command_id=?",
                        (AckState.WRITTEN.value, ref, command_id))
        return ref

    def resolve_ack_written(self, command_id: str, outbound_ref: str) -> str:
        if not isinstance(outbound_ref, str) or not outbound_ref:
            raise ValueError("ACK_OUTBOUND_REF_REQUIRED")
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM ack_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None or row["state"] not in (AckState.WRITE_INFLIGHT.value, AckState.WRITE_AMBIGUOUS.value):
                raise ValueError("ACK_RECONCILIATION_STATE_INVALID")
            con.execute("UPDATE ack_tx SET state=?,outbound_ref=? WHERE command_id=?",
                        (AckState.WRITTEN.value, outbound_ref, command_id))
        return outbound_ref

    def ack_status(self, command_id: str) -> dict[str, Any]:
        with self._con() as con:
            row = con.execute("SELECT * FROM ack_tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None:
                raise ValueError("ACK_NOT_STAGED")
            return dict(row)

    def status(self, command_id: str) -> dict[str, Any]:
        with self._con() as con:
            row = con.execute("SELECT * FROM tx WHERE command_id=?", (command_id,)).fetchone()
            if row is None:
                raise ValueError("COMMAND_NOT_INGESTED")
            return dict(row)


class AuraDriveBusWriterV1:
    """Exact adapter for installed ``aura_drive_bus_writer_v1.py`` line protocol."""
    def __init__(self, python: str, script: str, *, timeout_s: int = 60):
        if not python or not script:
            raise ValueError("INVALID_WRITER_BINDING")
        self.python = python
        self.script = script
        self.timeout_s = timeout_s

    def __call__(self, payload: Mapping[str, Any]) -> str:
        kind = payload.get("kind")
        command_id = payload.get("command_id")
        if kind not in TERMINAL_KINDS or not isinstance(command_id, str) or not command_id:
            raise ValueError("INVALID_TERMINAL_FOR_WRITER")
        argv = [self.python, self.script, "--channel", "aura_to_swarm",
                "--kind", str(kind), "--objective", command_id]
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"
        p = subprocess.run(argv, input=body, text=True, capture_output=True,
                           timeout=self.timeout_s, check=False)
        if p.returncode != 0:
            raise RuntimeError("BUS_WRITER_FAILED")
        fields: dict[str, str] = {}
        for line in p.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                fields[key.strip()] = value.strip()
        if fields.get("BUS_WRITE_OK") != "True":
            raise RuntimeError("BUS_WRITER_NOT_OK")
        file_id = fields.get("FILE_ID")
        if not file_id:
            raise RuntimeError("BUS_WRITER_MISSING_FILE_ID")
        return file_id
