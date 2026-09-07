from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))
from terminal_outbox import (  # noqa: E402
    AuraDriveBusWriterV1,
    CommandIdentity,
    NEGATIVE_KINDS,
    OutboxJournal,
    TerminalResponse,
    TERMINAL_KINDS,
)

VERSION = "PROJECT006_CONSUMER_OUTBOX_WRAPPER_V1"
DEFAULT_CONSUMER = "/home/john_of_wick/.config/aura-drive/bin/aura_drive_swarm_consumer_v1.py"
DEFAULT_RECEIPTS = "/home/john_of_wick/.config/aura-drive/state/swarm_consumer_v1/receipts"
DEFAULT_CONFIG = "/home/john_of_wick/.config/aura-drive/callback-config-v2.json"
DEFAULT_OUTBOX = "/home/john_of_wick/.config/aura-drive/state/swarm_consumer_v1/terminal_outbox.sqlite3"
DEFAULT_WRITER = "/home/john_of_wick/.config/aura-drive/bin/aura_drive_bus_writer_v1.py"
DEFAULT_PYTHON = "/home/john_of_wick/.local/lib/aura/project006/egress-venv/bin/python"

_TERMINAL_HINTS = tuple(sorted(TERMINAL_KINDS, key=len, reverse=True))


def _walk(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key), child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _first_text(value: Any, keys: set[str]) -> str | None:
    for key, child in _walk(value):
        if key.casefold() in keys and isinstance(child, str) and child:
            return child
    return None


def _first_int(value: Any, keys: set[str]) -> int | None:
    for key, child in _walk(value):
        if key.casefold() in keys and type(child) is int and child >= 0:
            return child
    return None


def _infer_kind(value: Any) -> str | None:
    candidates: list[str] = []
    for key, child in _walk(value):
        if key.casefold() in {"kind", "code", "state", "status", "disposition", "result"}:
            if isinstance(child, str):
                candidates.append(child.upper())
    joined = " | ".join(candidates)
    for hint in _TERMINAL_HINTS:
        if hint in joined:
            return hint
    if "BLOCK" in joined:
        return "COMMAND_BLOCKED"
    if "CURRENTNESS" in joined or "STALE" in joined:
        return "CURRENTNESS_REJECTED"
    if "AUTHORITY" in joined or "UNAUTHORIZED" in joined:
        return "AUTHORITY_REJECTED"
    if "SCHEMA" in joined or "PARSE" in joined:
        return "SCHEMA_REJECTED"
    if "CAPABILITY" in joined:
        return "CAPABILITY_REJECTED"
    return None


def _receipt_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_terminal_receipt(path: Path, *, command_filter: str | None = None) -> TerminalResponse | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    command_id = _first_text(raw, {"command_id", "commandid"})
    if not command_id or (command_filter and command_id != command_filter):
        return None
    kind = _infer_kind(raw)
    if not kind:
        return None
    idem = _first_text(raw, {"idempotency_key", "idempotencykey"}) or command_id
    source_file_id = _first_text(raw, {"source_file_id", "sourcefileid", "drive_file_id", "drivefileid"})
    source_revision = _first_text(raw, {"source_revision", "source_version", "revision", "revision_id"})
    source_digest = _first_text(raw, {"source_digest", "payload_sha256", "source_sha256", "sha256"})
    receipt_sha = _receipt_digest(path)
    source_binding = "EXACT_FROM_LOCAL_RECEIPT"
    if not source_file_id:
        source_file_id = f"UNRESOLVED_SOURCE_FILE_FOR:{command_id}"
        source_binding = "PARTIAL_LOCAL_RECEIPT_BINDING"
    if not source_revision:
        source_revision = "UNRESOLVED_SOURCE_REVISION"
        source_binding = "PARTIAL_LOCAL_RECEIPT_BINDING"
    if not source_digest:
        source_digest = f"LOCAL_RECEIPT_SHA256:{receipt_sha}"
        source_binding = "PARTIAL_LOCAL_RECEIPT_BINDING"
    provider_count = _first_int(raw, {"provider_request_count", "providerrequestcount"})
    if kind in NEGATIVE_KINDS:
        provider_count = 0
    elif provider_count is None:
        provider_count = 0
    failing_gate = _first_text(raw, {"first_failing_gate", "firstfailinggate", "blocking_reason", "reason", "error_code"})
    identity = CommandIdentity(command_id, idem, source_file_id, source_revision, source_digest)
    return TerminalResponse(
        identity=identity,
        kind=kind,
        first_failing_gate=failing_gate,
        provider_request_count=provider_count,
        payload={
            "local_receipt_path": str(path),
            "local_receipt_sha256": receipt_sha,
            "source_binding_status": source_binding,
            "local_receipt": raw,
        },
    )


def _snapshot(directory: Path) -> dict[str, tuple[int, int]]:
    if not directory.exists():
        return {}
    out: dict[str, tuple[int, int]] = {}
    for path in directory.glob("*.json"):
        try:
            st = path.stat()
        except OSError:
            continue
        out[str(path)] = (st.st_mtime_ns, st.st_size)
    return out


def _changed(before: Mapping[str, tuple[int, int]], after: Mapping[str, tuple[int, int]]) -> list[Path]:
    return [Path(p) for p, mark in after.items() if before.get(p) != mark]


def _writer_binding(config_path: str) -> tuple[str, str]:
    python = DEFAULT_PYTHON
    writer = DEFAULT_WRITER
    try:
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return python, writer
    for key in ("bridge_python", "python", "python_path"):
        value = config.get(key)
        if isinstance(value, str) and value:
            python = value
            break
    for key in ("writer_script", "bus_writer", "bus_writer_script"):
        value = config.get(key)
        if isinstance(value, str) and value:
            writer = value
            break
    return python, writer


def publish_receipts(paths: Iterable[Path], *, journal_path: str, config_path: str, command_filter: str | None = None) -> list[dict[str, str]]:
    journal = OutboxJournal(journal_path)
    python, writer_script = _writer_binding(config_path)
    writer = AuraDriveBusWriterV1(python, writer_script)
    results: list[dict[str, str]] = []
    for path in sorted(set(paths), key=lambda p: p.stat().st_mtime_ns if p.exists() else 0):
        response = parse_terminal_receipt(path, command_filter=command_filter)
        if response is None:
            continue
        try:
            journal.stage_terminal(response)
            ref = journal.publish_pending(response.identity.command_id, writer)
        except ValueError as exc:
            results.append({"command_id": response.identity.command_id, "status": f"HOLD:{exc}"})
            continue
        results.append({"command_id": response.identity.command_id, "status": "RETURN_WRITTEN", "outbound_file_id": ref})
    return results


def run_once(*, consumer: str, receipts: str, journal: str, config: str, command_filter: str | None = None) -> dict[str, Any]:
    receipt_dir = Path(receipts)
    before = _snapshot(receipt_dir)
    proc = subprocess.run([sys.executable, consumer, "once"], text=True, capture_output=True, check=False, timeout=240)
    after = _snapshot(receipt_dir)
    changed = _changed(before, after)
    # For an explicit command filter, include historical local receipts too. This is how
    # a previously-local-only AWJ033 terminal is repaired without rerunning any provider.
    if command_filter and receipt_dir.exists():
        changed.extend(receipt_dir.glob("*.json"))
    published = publish_receipts(changed, journal_path=journal, config_path=config, command_filter=command_filter)
    return {
        "schema": "PROJECT006_CONSUMER_OUTBOX_RUN_V1",
        "version": VERSION,
        "consumer_exit_code": proc.returncode,
        "consumer_stdout_tail": proc.stdout[-2000:],
        "consumer_stderr_tail": proc.stderr[-2000:],
        "changed_receipt_count": len(_changed(before, after)),
        "published": published,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("once", "flush"))
    ap.add_argument("--consumer", default=DEFAULT_CONSUMER)
    ap.add_argument("--receipts", default=DEFAULT_RECEIPTS)
    ap.add_argument("--journal", default=DEFAULT_OUTBOX)
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--command-id")
    ns = ap.parse_args()
    if ns.command == "once":
        result = run_once(consumer=ns.consumer, receipts=ns.receipts, journal=ns.journal, config=ns.config, command_filter=ns.command_id)
    else:
        paths = list(Path(ns.receipts).glob("*.json")) if Path(ns.receipts).exists() else []
        result = {"schema": "PROJECT006_CONSUMER_OUTBOX_FLUSH_V1", "published": publish_receipts(paths, journal_path=ns.journal, config_path=ns.config, command_filter=ns.command_id)}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
