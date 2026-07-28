"""Human-facing archive for successful, denied, and failed Arena attempts.

The ArenaExperience ledger remains the authoritative observable learning record. This
archive serves a different purpose: preserve inspectable worker output, candidate diffs,
failed tests, verifier denials, gate dialogue, and bounded topology context so a human
can copy, compare, annotate, and reuse them during later refactoring.

Archived output never gains patch, verifier, merge, or learning authority merely by
being stored.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Any

from aura_arena_experience import sanitize_experience_payload

ATTEMPT_ARCHIVE_VERSION = "AURA_ARENA_ATTEMPT_ARCHIVE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_SCHEMA_VERSION = 1
_MAX_STRING = 16 * 1024 * 1024
_MAX_COPY_TEXT = 1_800_000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS arena_attempt_artifacts (
 artifact_id TEXT PRIMARY KEY,
 created_at REAL NOT NULL,
 arena_id TEXT NOT NULL,
 workflow_id TEXT NOT NULL DEFAULT '',
 phase TEXT NOT NULL DEFAULT '',
 route TEXT NOT NULL DEFAULT '',
 action_id TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT '',
 ok INTEGER NOT NULL DEFAULT 0,
 objective TEXT NOT NULL DEFAULT '',
 selected_node_json TEXT NOT NULL DEFAULT '{}',
 gate_context_json TEXT NOT NULL DEFAULT '{}',
 request_json TEXT NOT NULL DEFAULT '{}',
 result_json TEXT NOT NULL DEFAULT '{}',
 candidate_diff TEXT NOT NULL DEFAULT '',
 observable_output TEXT NOT NULL DEFAULT '',
 failure_summary TEXT NOT NULL DEFAULT '',
 tags_json TEXT NOT NULL DEFAULT '[]',
 redactions_json TEXT NOT NULL DEFAULT '[]',
 artifact_digest TEXT NOT NULL,
 reusable_for_refactoring INTEGER NOT NULL DEFAULT 1,
 verified INTEGER NOT NULL DEFAULT 0,
 production_authority INTEGER NOT NULL DEFAULT 0,
 schema_version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_attempt_created ON arena_attempt_artifacts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attempt_status ON arena_attempt_artifacts(status,ok);
CREATE INDEX IF NOT EXISTS idx_attempt_action ON arena_attempt_artifacts(arena_id,action_id);
CREATE INDEX IF NOT EXISTS idx_attempt_workflow ON arena_attempt_artifacts(workflow_id,created_at DESC);
"""


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any, *, size: int = 20) -> str:
    return hashlib.blake2b(_json(value).encode("utf-8"), digest_size=size).hexdigest()


def _text(value: Any, limit: int = _MAX_STRING) -> str:
    return str(value or "")[:limit]


def _bounded(value: Any, *, depth: int = 0) -> Any:
    if depth >= 9:
        return "[MAX_DEPTH]"
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for index, (raw_key, raw_value) in enumerate(value.items()):
            if index >= 120:
                output["__truncated_items__"] = len(value) - index
                break
            output[str(raw_key)[:180]] = _bounded(raw_value, depth=depth + 1)
        return output
    if isinstance(value, (list, tuple, set)):
        sequence = list(value)
        output = [_bounded(item, depth=depth + 1) for item in sequence[:200]]
        if len(sequence) > 200:
            output.append({"__truncated_items__": len(sequence) - 200})
        return output
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")[:_MAX_STRING]
    if isinstance(value, str):
        return value[:_MAX_STRING]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:_MAX_STRING]


def _safe(value: Any) -> tuple[Any, list[str]]:
    bounded = _bounded(value)
    sanitized, redactions = sanitize_experience_payload(bounded)
    return sanitized, sorted(set(str(item) for item in redactions))


def _find_first(value: Any, keys: set[str]) -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in keys and isinstance(item, (str, bytes)):
                text = _text(item)
                if text.strip():
                    return text
        for item in value.values():
            found = _find_first(item, keys)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _find_first(item, keys)
            if found:
                return found
    return ""


def _collect_output(value: Any, *, limit: int = 300_000) -> str:
    keys = {
        "stdout", "stderr", "output", "output_text", "logs", "log", "traceback",
        "test_output", "verifier_output", "diagnostic", "diagnostics", "message",
    }
    found: list[str] = []

    def walk(item: Any) -> None:
        if sum(len(part) for part in found) >= limit:
            return
        if isinstance(item, dict):
            for raw_key, raw_value in item.items():
                key = str(raw_key).casefold()
                if key in keys and isinstance(raw_value, (str, int, float, bool)):
                    text = str(raw_value).strip()
                    if text and text not in found:
                        found.append(text)
                elif isinstance(raw_value, (dict, list, tuple)):
                    walk(raw_value)
        elif isinstance(item, (list, tuple)):
            for child in item:
                walk(child)

    walk(value)
    return "\n\n".join(found)[:limit]


def _failure_summary(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("error", "reason", "message", "status"):
        value = result.get(key)
        if value not in (None, "", [], {}):
            parts.append(f"{key}: {value}")
    missing = result.get("missing_evidence") or (result.get("denial") or {}).get("missing") or []
    if missing:
        parts.append("missing_evidence: " + ", ".join(str(item) for item in missing))
    remediation = result.get("remediation") or (result.get("denial") or {}).get("remediation") or []
    if remediation:
        rendered = []
        for item in remediation:
            rendered.append(str(item.get("label") or item.get("action") or item) if isinstance(item, dict) else str(item))
        parts.append("remediation: " + " -> ".join(rendered))
    return "\n".join(dict.fromkeys(parts))[:20_000]


def _copy_text(row: dict[str, Any]) -> str:
    node = dict(row.get("selected_node") or {})
    gate = dict(row.get("gate_context") or {})
    request = row.get("request") or {}
    result = row.get("result") or {}
    sections = [
        f"# Aura Arena Attempt {row.get('artifact_id', '')}",
        "",
        f"- Status: {row.get('status', '')}",
        f"- Arena: {row.get('arena_id', '')}",
        f"- Workflow: {row.get('workflow_id', '')}",
        f"- Phase: {row.get('phase', '')}",
        f"- Action: {row.get('action_id', '')}",
        f"- Created: {row.get('created_at', '')}",
        f"- Verified: {str(bool(row.get('verified'))).lower()}",
        "- Authority: archived refactoring evidence only; no patch, commit, push, merge, or learning authority",
    ]
    if row.get("objective"):
        sections += ["", "## Objective", "", str(row["objective"])]
    if node:
        sections += [
            "", "## Selected topology evidence", "",
            f"- Node: {node.get('label') or node.get('id') or '—'}",
            f"- File: {node.get('file_path') or '—'}",
            f"- Symbol: {node.get('symbol') or '—'}",
            f"- Lines: {'-'.join(str(item) for item in node.get('line_range', [])) or '—'}",
        ]
    dialogue = dict(gate.get("gate_dialogue") or {})
    if dialogue.get("human_comment"):
        sections += ["", "## Human gate intent", "", str(dialogue["human_comment"])]
    if dialogue.get("aura_response"):
        sections += ["", "## Aura response", "", str(dialogue["aura_response"])]
    if row.get("failure_summary"):
        sections += ["", "## Failure or denial summary", "", str(row["failure_summary"])]
    if row.get("candidate_diff"):
        sections += ["", "## Candidate diff", "", "```diff", str(row["candidate_diff"]), "```"]
    if row.get("observable_output"):
        sections += ["", "## Observable output", "", "```text", str(row["observable_output"]), "```"]
    sections += [
        "", "## Request packet", "", "```json", json.dumps(request, indent=2, ensure_ascii=False, default=str), "```",
        "", "## Result packet", "", "```json", json.dumps(result, indent=2, ensure_ascii=False, default=str), "```",
    ]
    return "\n".join(sections)[:_MAX_COPY_TEXT]


class ArenaAttemptArchive:
    """SQLite/WAL archive for inspectable and copyable Arena attempt artifacts."""

    def __init__(self, repo_root: str | Path = ".", *, db_path: str | Path | None = None) -> None:
        root = Path(repo_root).resolve()
        self.db_path = Path(db_path).resolve() if db_path else root / "Aura_Memory" / "arena_attempt_artifacts.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def record(
        self,
        *,
        arena_id: str,
        route: str,
        request: dict[str, Any] | None,
        result: dict[str, Any] | None,
        workflow_state: dict[str, Any] | None = None,
        archive_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_request = dict(request or {})
        raw_result = dict(result or {})
        raw_state = dict(workflow_state or {})
        raw_context = dict(archive_context or {})
        safe_request, red0 = _safe(raw_request)
        safe_result, red1 = _safe(raw_result)
        safe_state, red2 = _safe(raw_state)
        safe_context, red3 = _safe(raw_context)
        redactions = sorted(set([*red0, *red1, *red2, *red3]))

        action_id = str(
            raw_request.get("action_id")
            or raw_request.get("tool_id")
            or raw_request.get("command")
            or raw_result.get("action_id")
            or route.rsplit("/", 1)[-1]
        )[:240]
        status = str(raw_result.get("status") or ("COMPLETED" if raw_result.get("ok") else "FAILED")).upper()[:120]
        ok = bool(raw_result.get("ok"))
        phase = str(safe_state.get("current_phase") or safe_context.get("stage_hint") or "")[:120]
        workflow_id = str(safe_state.get("workflow_id") or "")[:240]
        objective = _text(safe_state.get("objective") or safe_context.get("objective"), 120_000)
        selected_node = dict((safe_context or {}).get("node_context", {}).get("selected_node") or {})
        if not selected_node:
            selected_node = dict((safe_context or {}).get("selected_node") or {})
        candidate_diff = _find_first(safe_request, {"candidate_diff", "diff", "patch", "unified_diff"})
        if not candidate_diff:
            candidate_diff = _find_first(safe_result, {"candidate_diff", "diff", "patch", "unified_diff"})
        observable_output = _collect_output(safe_result)
        failure_summary = "" if ok else _failure_summary(dict(safe_result or {}))
        tags = [
            "arena_attempt",
            "successful_attempt" if ok else "failed_or_denied_attempt",
            "copyable",
            "refactoring_evidence",
            "unverified" if not ok else "observed",
        ]
        if candidate_diff:
            tags.append("candidate_diff")
        if selected_node:
            tags.append("topology_anchored")
        created_at = time.time()
        identity = {
            "arena_id": arena_id,
            "workflow_id": workflow_id,
            "route": route,
            "action_id": action_id,
            "status": status,
            "created_at": created_at,
            "request_digest": _digest(safe_request),
            "result_digest": _digest(safe_result),
        }
        artifact_id = "ATT-" + secrets.token_hex(12)
        artifact_digest = _digest({**identity, "artifact_id": artifact_id})
        values = (
            artifact_id,
            created_at,
            str(arena_id or "human_agent")[:120],
            workflow_id,
            phase,
            str(route or "")[:320],
            action_id,
            status,
            int(ok),
            objective,
            _json(selected_node),
            _json(safe_context),
            _json(safe_request),
            _json(safe_result),
            _text(candidate_diff),
            _text(observable_output, 300_000),
            _text(failure_summary, 20_000),
            _json(tags),
            _json(redactions),
            artifact_digest,
            1,
            0,
            0,
            _SCHEMA_VERSION,
        )
        try:
            self._conn.execute(
                """INSERT INTO arena_attempt_artifacts(
                 artifact_id,created_at,arena_id,workflow_id,phase,route,action_id,status,ok,
                 objective,selected_node_json,gate_context_json,request_json,result_json,
                 candidate_diff,observable_output,failure_summary,tags_json,redactions_json,
                 artifact_digest,reusable_for_refactoring,verified,production_authority,schema_version
                 ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                values,
            )
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            return {
                "ok": False,
                "reason": f"attempt_archive_write_failed:{type(exc).__name__}",
                "fail_closed": False,
                "original_attempt_preserved_in_response": True,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        return {
            "ok": True,
            "artifact_id": artifact_id,
            "artifact_digest": artifact_digest,
            "status": status,
            "attempt_ok": ok,
            "has_candidate_diff": bool(candidate_diff),
            "failure_preserved": not ok,
            "copyable": True,
            "reusable_for_refactoring": True,
            "verified": False,
            "production_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def list(
        self,
        *,
        arena_id: str = "",
        workflow_id: str = "",
        route: str = "",
        failures_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if arena_id:
            clauses.append("arena_id=?")
            params.append(str(arena_id))
        if workflow_id:
            clauses.append("workflow_id=?")
            params.append(str(workflow_id))
        if route:
            clauses.append("route=?")
            params.append(str(route))
        if failures_only:
            clauses.append("ok=0")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(int(limit), 500)))
        rows = self._conn.execute(
            f"""SELECT artifact_id,created_at,arena_id,workflow_id,phase,route,action_id,status,ok,
             objective,selected_node_json,failure_summary,tags_json,artifact_digest,
             reusable_for_refactoring,verified,production_authority
             FROM arena_attempt_artifacts {where}
             ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
        return [self._decode_summary(row) for row in rows]

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM arena_attempt_artifacts WHERE artifact_id=?",
            (str(artifact_id),),
        ).fetchone()
        if row is None:
            return None
        decoded = self._decode(row)
        decoded["copy_text"] = _copy_text(decoded)
        decoded["copy_diff"] = decoded.get("candidate_diff", "")
        return decoded

    def export_jsonl(
        self,
        path: str | Path,
        *,
        failures_only: bool = False,
        limit: int = 10_000,
    ) -> dict[str, Any]:
        summaries = self.list(failures_only=failures_only, limit=min(limit, 500))
        rows = [self.get(item["artifact_id"]) for item in reversed(summaries)]
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(_json(row) + "\n" for row in rows if row),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "path": str(output),
            "record_count": len([row for row in rows if row]),
            "failures_only": bool(failures_only),
            "production_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def status(self) -> dict[str, Any]:
        count = int(self._conn.execute("SELECT COUNT(*) FROM arena_attempt_artifacts").fetchone()[0])
        failed = int(self._conn.execute("SELECT COUNT(*) FROM arena_attempt_artifacts WHERE ok=0").fetchone()[0])
        with_diff = int(self._conn.execute("SELECT COUNT(*) FROM arena_attempt_artifacts WHERE candidate_diff!=''").fetchone()[0])
        return {
            "ok": True,
            "version": ATTEMPT_ARCHIVE_VERSION,
            "schema_version": _SCHEMA_VERSION,
            "db_path": str(self.db_path),
            "record_count": count,
            "failed_or_denied_count": failed,
            "candidate_diff_count": with_diff,
            "journal_mode": str(self._conn.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
            "copyable": True,
            "reusable_for_refactoring": True,
            "archived_output_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    @staticmethod
    def _decode_summary(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "artifact_id": row["artifact_id"],
            "created_at": float(row["created_at"]),
            "arena_id": row["arena_id"],
            "workflow_id": row["workflow_id"],
            "phase": row["phase"],
            "route": row["route"],
            "action_id": row["action_id"],
            "status": row["status"],
            "ok": bool(row["ok"]),
            "objective": row["objective"],
            "selected_node": json.loads(row["selected_node_json"] or "{}"),
            "failure_summary": row["failure_summary"],
            "tags": json.loads(row["tags_json"] or "[]"),
            "artifact_digest": row["artifact_digest"],
            "reusable_for_refactoring": bool(row["reusable_for_refactoring"]),
            "verified": bool(row["verified"]),
            "production_authority": bool(row["production_authority"]),
        }

    @classmethod
    def _decode(cls, row: sqlite3.Row) -> dict[str, Any]:
        data = cls._decode_summary(row)
        data.update({
            "version": ATTEMPT_ARCHIVE_VERSION,
            "gate_context": json.loads(row["gate_context_json"] or "{}"),
            "request": json.loads(row["request_json"] or "{}"),
            "result": json.loads(row["result_json"] or "{}"),
            "candidate_diff": row["candidate_diff"],
            "observable_output": row["observable_output"],
            "redactions": json.loads(row["redactions_json"] or "[]"),
            "schema_version": int(row["schema_version"]),
            "archived_output_authority": False,
            "human_review_required_before_reuse": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        })
        return data


__all__ = ["ArenaAttemptArchive", "ATTEMPT_ARCHIVE_VERSION"]
