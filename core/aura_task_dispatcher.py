#!/usr/bin/env python3
"""AuraOS local task dispatcher.

A small stdlib-only SQLite WAL queue with explicit leases. It is a transport and
coordination primitive, not an authority plane: claiming a task does not grant
permission beyond the task's pre-existing human/governance authority.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class TaskDispatcher:
    def __init__(self, db_path: str | Path = "aura_workspace/dispatcher.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=30.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=30000")
        return con

    def _init_db(self) -> None:
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks(
                    task_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('PENDING','LEASED','DONE','FAILED')),
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    leased_by TEXT,
                    lease_until REAL,
                    result_json TEXT
                )
                """
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at)"
            )

    def enqueue(self, kind: str, payload: dict[str, Any] | None = None) -> str:
        now = time.time()
        task_id = uuid.uuid4().hex
        with self.connect() as con:
            con.execute(
                """INSERT INTO tasks(task_id, kind, payload_json, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'PENDING', ?, ?)""",
                (task_id, kind, json.dumps(payload or {}, sort_keys=True), now, now),
            )
        return task_id

    def claim(self, worker_id: str, lease_seconds: float = 60.0) -> dict[str, Any] | None:
        now = time.time()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """UPDATE tasks
                   SET status='PENDING', leased_by=NULL, lease_until=NULL, updated_at=?
                   WHERE status='LEASED' AND lease_until IS NOT NULL AND lease_until < ?""",
                (now, now),
            )
            row = con.execute(
                """SELECT * FROM tasks
                   WHERE status='PENDING'
                   ORDER BY created_at, task_id
                   LIMIT 1"""
            ).fetchone()
            if row is None:
                con.commit()
                return None
            lease_until = now + lease_seconds
            con.execute(
                """UPDATE tasks
                   SET status='LEASED', leased_by=?, lease_until=?, updated_at=?
                   WHERE task_id=? AND status='PENDING'""",
                (worker_id, lease_until, now, row["task_id"]),
            )
            con.commit()
            return {
                "task_id": row["task_id"],
                "kind": row["kind"],
                "payload": json.loads(row["payload_json"]),
                "leased_by": worker_id,
                "lease_until": lease_until,
            }

    def finish(self, task_id: str, worker_id: str, *, ok: bool, result: dict[str, Any]) -> None:
        now = time.time()
        status = "DONE" if ok else "FAILED"
        with self.connect() as con:
            cur = con.execute(
                """UPDATE tasks
                   SET status=?, result_json=?, updated_at=?, lease_until=NULL
                   WHERE task_id=? AND status='LEASED' AND leased_by=?""",
                (status, json.dumps(result, sort_keys=True), now, task_id, worker_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("task lease mismatch or task is not currently leased")

    def status(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT task_id, kind, status, created_at, updated_at, leased_by, lease_until, result_json "
                "FROM tasks ORDER BY created_at, task_id"
            ).fetchall()
        return [dict(row) for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="aura_workspace/dispatcher.db")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_enqueue = sub.add_parser("enqueue")
    p_enqueue.add_argument("kind")
    p_enqueue.add_argument("--payload", default="{}")
    sub.add_parser("status")
    args = parser.parse_args()

    dispatcher = TaskDispatcher(args.db)
    if args.cmd == "enqueue":
        payload = json.loads(args.payload)
        print(dispatcher.enqueue(args.kind, payload))
    elif args.cmd == "status":
        print(json.dumps(dispatcher.status(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
