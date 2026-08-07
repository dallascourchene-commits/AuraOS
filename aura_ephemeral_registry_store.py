"""
Aura Ephemeral Registry Store — persistent SQLite-backed lifecycle registry.

Solves the cross-process CLI problem: separate `ephemeral-plan` and
`ephemeral-run` commands cannot share an in-memory singleton.

Default location: .aura/runtime/ephemeral_registry.sqlite3
WAL mode with schema migrations. No secrets. No raw private prompts.

Dependencies: stdlib only (sqlite3).
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SCHEMA_VERSION = 2


def _default_db_path(repo_root: str | Path = ".") -> Path:
    return Path(repo_root).resolve() / ".aura" / "runtime" / "ephemeral_registry.sqlite3"


class EphemeralRegistryStore:
    """Persistent SQLite store for ephemeral organ lifecycle records."""

    def __init__(self, db_path: str | Path | None = None, *, repo_root: str | Path = ".") -> None:
        if db_path is None:
            db_path = _default_db_path(repo_root)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._connect()
        self._migrate()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(
            str(self.db_path),
            isolation_level=None,  # autocommit
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def _migrate(self) -> None:
        conn = self._conn
        assert conn is not None
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at REAL)")
        cur = conn.execute("SELECT MAX(version) FROM schema_migrations")
        row = cur.fetchone()
        current = row[0] if row and row[0] is not None else 0
        if current < 1:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ephemeral_organs (
                    organ_id TEXT PRIMARY KEY,
                    manifest_digest TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'DRAFTED',
                    objective TEXT DEFAULT '',
                    ttl_seconds INTEGER DEFAULT 300,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    capability_lease TEXT DEFAULT '[]',
                    sandbox_path TEXT DEFAULT '',
                    verifier_status TEXT DEFAULT 'pending',
                    dissolution_receipt TEXT DEFAULT '{}',
                    crystallization_proposal TEXT DEFAULT '{}',
                    manifest_json TEXT DEFAULT '{}',
                    transition_evidence TEXT DEFAULT '[]',
                    lease_status TEXT DEFAULT 'active',
                    revoked_at REAL,
                    revocation_reason TEXT DEFAULT '',
                    revoked_capabilities TEXT DEFAULT '[]',
                    audit_summary TEXT DEFAULT '{}',
                    finalized_manifest TEXT DEFAULT '{}',
                    previous_manifest_digest TEXT DEFAULT '',
                    manifest_state TEXT DEFAULT 'DRAFT',
                    session_id TEXT DEFAULT '',
                    domain TEXT DEFAULT 'ephemeral',
                    organ_type TEXT DEFAULT '',
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_organ_state ON ephemeral_organs(state)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_organ_expires ON ephemeral_organs(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_organ_lease_status ON ephemeral_organs(lease_status)")
            conn.execute("INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (1, ?)", (time.time(),))
        if current < 2:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ephemeral_workspaces_v2 (
                    workspace_id TEXT PRIMARY KEY,
                    recipe_json TEXT NOT NULL,
                    recipe_digest TEXT NOT NULL,
                    graph_json TEXT NOT NULL,
                    graph_digest TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    activation_nonce TEXT NOT NULL UNIQUE,
                    lease_status TEXT NOT NULL DEFAULT 'ACTIVE',
                    sandbox_path TEXT NOT NULL DEFAULT '',
                    node_receipts TEXT NOT NULL DEFAULT '{}',
                    failure_records TEXT NOT NULL DEFAULT '[]',
                    usage_json TEXT NOT NULL DEFAULT '{}',
                    cleanup_receipt TEXT NOT NULL DEFAULT '{}',
                    certificate_json TEXT NOT NULL DEFAULT '{}',
                    terminal_reason TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workspace_v2_state ON ephemeral_workspaces_v2(state)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workspace_v2_expires ON ephemeral_workspaces_v2(expires_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workspace_v2_lease ON ephemeral_workspaces_v2(lease_status)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (2, ?)",
                (time.time(),),
            )

    def register(self, record: dict[str, Any]) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        now = time.time()
        conn.execute("""
            INSERT OR REPLACE INTO ephemeral_organs
            (organ_id, manifest_digest, state, objective, ttl_seconds, created_at, expires_at,
             capability_lease, sandbox_path, verifier_status, dissolution_receipt,
             crystallization_proposal, manifest_json, transition_evidence, lease_status,
             revoked_at, revocation_reason, revoked_capabilities, audit_summary,
             finalized_manifest, previous_manifest_digest, manifest_state, session_id,
             domain, organ_type, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            record.get("organ_id", ""),
            record.get("manifest_digest", ""),
            record.get("state", "DRAFTED"),
            record.get("objective", ""),
            record.get("ttl_seconds", 300),
            record.get("created_at", now),
            record.get("expires_at", now + 300),
            json.dumps(record.get("capability_lease", [])),
            record.get("sandbox_path", ""),
            record.get("verifier_status", "pending"),
            json.dumps(record.get("dissolution_receipt", {})),
            json.dumps(record.get("crystallization_proposal", {})),
            json.dumps(record.get("manifest_json", record.get("manifest", {}))),
            json.dumps(record.get("transition_evidence", [])),
            record.get("lease_status", "active"),
            record.get("revoked_at"),
            record.get("revocation_reason", ""),
            json.dumps(record.get("revoked_capabilities", [])),
            json.dumps(record.get("audit_summary", {})),
            json.dumps(record.get("finalized_manifest", {})),
            record.get("previous_manifest_digest", ""),
            record.get("manifest_state", "DRAFT"),
            record.get("session_id", ""),
            record.get("domain", "ephemeral"),
            record.get("organ_type", ""),
            now,
        ))
        return {"ok": True, "organ_id": record.get("organ_id", ""),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def get(self, organ_id: str) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT * FROM ephemeral_organs WHERE organ_id = ?", (organ_id,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": f"organ not found: {organ_id}",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "organ": self._row_to_dict(row, cur),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def _row_to_dict(self, row: tuple, cur: sqlite3.Cursor | None = None) -> dict[str, Any]:
        if cur is not None:
            cols = [d[0] for d in cur.description]
        else:
            cols = [f"col_{i}" for i in range(len(row))]
        d = dict(zip(cols, row, strict=True))
        for key in ("capability_lease", "dissolution_receipt", "crystallization_proposal",
                     "manifest_json", "transition_evidence", "revoked_capabilities",
                     "audit_summary", "finalized_manifest"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    def update_state(self, organ_id: str, new_state: str, *, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        """Atomic state update with compare-and-set support."""
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT state, transition_evidence FROM ephemeral_organs WHERE organ_id = ?", (organ_id,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": f"organ not found: {organ_id}"}
        current_state = row[0]
        evidence_list = []
        try:
            evidence_list = json.loads(row[1]) if row[1] else []
        except (json.JSONDecodeError, TypeError):
            pass
        if evidence:
            evidence_list.append({**evidence, "timestamp": time.time()})
        conn.execute(
            "UPDATE ephemeral_organs SET state = ?, transition_evidence = ?, updated_at = ? WHERE organ_id = ?",
            (new_state, json.dumps(evidence_list), time.time(), organ_id),
        )
        return {"ok": True, "organ_id": organ_id, "previous_state": current_state,
                "state": new_state,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def transition_organ(self, organ_id: str, expected_from: str, to: str, *, evidence_ref: str = "") -> dict[str, Any]:
        """Compare-and-set transition. Fails if current state doesn't match expected_from."""
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT state, transition_evidence FROM ephemeral_organs WHERE organ_id = ?", (organ_id,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": f"organ not found: {organ_id}",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        current_state = row[0]
        if current_state != expected_from:
            return {"ok": False, "error": f"stale_state: expected {expected_from}, actual {current_state}",
                    "organ_id": organ_id, "expected": expected_from, "actual": current_state,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        evidence_list = []
        try:
            evidence_list = json.loads(row[1]) if row[1] else []
        except (json.JSONDecodeError, TypeError):
            pass
        evidence_list.append({"from": expected_from, "to": to, "evidence_ref": evidence_ref, "timestamp": time.time()})
        conn.execute(
            "UPDATE ephemeral_organs SET state = ?, transition_evidence = ?, updated_at = ? WHERE organ_id = ?",
            (to, json.dumps(evidence_list), time.time(), organ_id),
        )
        return {"ok": True, "organ_id": organ_id, "from": expected_from, "to": to,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def set_dissolution_receipt(self, organ_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        conn.execute(
            "UPDATE ephemeral_organs SET dissolution_receipt = ?, state = 'DISSOLVED', lease_status = 'REVOKED', updated_at = ? WHERE organ_id = ?",
            (json.dumps(receipt), time.time(), organ_id),
        )
        return {"ok": True, "organ_id": organ_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def set_crystallization_proposal(self, organ_id: str, proposal: dict[str, Any]) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        conn.execute(
            "UPDATE ephemeral_organs SET crystallization_proposal = ?, state = 'CRYSTALLIZATION_PROPOSED', updated_at = ? WHERE organ_id = ?",
            (json.dumps(proposal), time.time(), organ_id),
        )
        return {"ok": True, "organ_id": organ_id, "note": "proposal_only_no_automatic_promotion",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def revoke_lease(self, organ_id: str, reason: str = "dissolution") -> dict[str, Any]:
        """Persist lease revocation. Post-revocation adapter calls must fail."""
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT capability_lease FROM ephemeral_organs WHERE organ_id = ?", (organ_id,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": f"organ not found: {organ_id}"}
        caps = []
        try:
            caps = json.loads(row[0]) if row[0] else []
        except (json.JSONDecodeError, TypeError):
            pass
        conn.execute(
            "UPDATE ephemeral_organs SET lease_status = 'REVOKED', revoked_at = ?, revocation_reason = ?, revoked_capabilities = ?, updated_at = ? WHERE organ_id = ?",
            (time.time(), reason, json.dumps(caps), time.time(), organ_id),
        )
        return {"ok": True, "organ_id": organ_id, "revoked_capabilities": caps,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def is_lease_active(self, organ_id: str) -> bool:
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT lease_status FROM ephemeral_organs WHERE organ_id = ?", (organ_id,))
        row = cur.fetchone()
        if not row:
            return False
        return row[0] == "active"

    def set_audit_summary(self, organ_id: str, summary: dict[str, Any]) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        conn.execute(
            "UPDATE ephemeral_organs SET audit_summary = ?, updated_at = ? WHERE organ_id = ?",
            (json.dumps(summary), time.time(), organ_id),
        )
        return {"ok": True, "organ_id": organ_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def set_finalized_manifest(self, organ_id: str, manifest: dict[str, Any], digest: str) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        conn.execute(
            "UPDATE ephemeral_organs SET finalized_manifest = ?, manifest_digest = ?, manifest_state = 'FINALIZED', updated_at = ? WHERE organ_id = ?",
            (json.dumps(manifest), digest, time.time(), organ_id),
        )
        return {"ok": True, "organ_id": organ_id, "digest": digest,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def list_active(self) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT * FROM ephemeral_organs WHERE state NOT IN ('DISSOLVED', 'FAILED') AND expires_at > ?",
                           (time.time(),))
        rows = cur.fetchall()
        active = [self._row_to_dict(r, cur) for r in rows]
        return {"ok": True, "active_organs": active, "count": len(active),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def list_all(self) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT * FROM ephemeral_organs ORDER BY created_at DESC")
        rows = cur.fetchall()
        all_records = [self._row_to_dict(r, cur) for r in rows]
        return {"ok": True, "organs": all_records, "count": len(all_records),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def check_expired(self) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        cur = conn.execute(
            "SELECT organ_id FROM ephemeral_organs WHERE expires_at <= ? AND state NOT IN ('DISSOLVED', 'DISSOLVING', 'FAILED')",
            (time.time(),),
        )
        rows = cur.fetchall()
        expired = [r[0] for r in rows]
        return {"ok": True, "expired_organ_ids": expired, "count": len(expired),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def reap_expired(self) -> dict[str, Any]:
        """Dissolve all expired organs. Returns count reaped."""
        expired = self.check_expired()
        reaped = []
        for organ_id in expired.get("expired_organ_ids", []):
            self.update_state(organ_id, "DISSOLVING", evidence={"reason": "ttl_expired"})
            self.revoke_lease(organ_id, reason="ttl_expired")
            self.update_state(organ_id, "DISSOLVED", evidence={"reason": "ttl_expired_dissolved"})
            reaped.append(organ_id)
        return {"ok": True, "reaped": reaped, "count": len(reaped),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def export_audit(self) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT organ_id, manifest_digest, state, created_at, expires_at, verifier_status, lease_status, domain, organ_type FROM ephemeral_organs")
        rows = cur.fetchall()
        records = []
        for r in rows:
            records.append({
                "organ_id": r[0], "manifest_digest": r[1], "state": r[2],
                "created_at": r[3], "expires_at": r[4], "verifier_status": r[5],
                "lease_status": r[6], "domain": r[7], "organ_type": r[8],
            })
        return {"ok": True, "audit_records": records, "count": len(records),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    # ------------------------------------------------------------------
    # Verified Ephemeral Workspace V2 — additive, separate from V1 organs.
    # ------------------------------------------------------------------

    @staticmethod
    def _workspace_v2_json(value: Any, name: str) -> str:
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{name} must be canonical JSON") from exc

    @staticmethod
    def _workspace_v2_row(row: tuple[Any, ...], cur: sqlite3.Cursor) -> dict[str, Any]:
        record = dict(zip((item[0] for item in cur.description), row, strict=True))
        for name in (
            "recipe_json", "graph_json", "node_receipts", "failure_records",
            "usage_json", "cleanup_receipt", "certificate_json",
        ):
            try:
                record[name] = json.loads(record[name])
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(f"stored workspace {name} is invalid") from exc
        return record

    def register_workspace_v2(self, record: dict[str, Any]) -> dict[str, Any]:
        """Atomically register one admitted V2 workspace; duplicate IDs/nonces fail."""
        if type(record) is not dict:
            raise ValueError("workspace record must be an exact object")
        required = {
            "workspace_id", "recipe_json", "recipe_digest", "graph_json", "graph_digest",
            "state", "created_at", "expires_at", "activation_nonce",
        }
        if set(record) - {
            *required, "lease_status", "sandbox_path", "node_receipts", "failure_records",
            "usage_json", "cleanup_receipt", "certificate_json", "terminal_reason",
        } or not required <= set(record):
            raise ValueError("workspace record fields are incomplete or unknown")
        conn = self._conn
        assert conn is not None
        now = time.time()
        try:
            conn.execute(
                """
                INSERT INTO ephemeral_workspaces_v2
                (workspace_id, recipe_json, recipe_digest, graph_json, graph_digest,
                 state, created_at, updated_at, expires_at, activation_nonce,
                 lease_status, sandbox_path, node_receipts, failure_records,
                 usage_json, cleanup_receipt, certificate_json, terminal_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    record["workspace_id"],
                    self._workspace_v2_json(record["recipe_json"], "recipe_json"),
                    record["recipe_digest"],
                    self._workspace_v2_json(record["graph_json"], "graph_json"),
                    record["graph_digest"],
                    record["state"],
                    record["created_at"],
                    now,
                    record["expires_at"],
                    record["activation_nonce"],
                    record.get("lease_status", "ACTIVE"),
                    record.get("sandbox_path", ""),
                    self._workspace_v2_json(record.get("node_receipts", {}), "node_receipts"),
                    self._workspace_v2_json(record.get("failure_records", []), "failure_records"),
                    self._workspace_v2_json(record.get("usage_json", {}), "usage_json"),
                    self._workspace_v2_json(record.get("cleanup_receipt", {}), "cleanup_receipt"),
                    self._workspace_v2_json(record.get("certificate_json", {}), "certificate_json"),
                    record.get("terminal_reason", ""),
                ),
            )
        except sqlite3.IntegrityError:
            return {"ok": False, "error": "duplicate_workspace_or_activation_nonce",
                    "workspace_id": record.get("workspace_id", ""),
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "workspace_id": record["workspace_id"], "state": record["state"],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def get_workspace_v2(self, workspace_id: str) -> dict[str, Any]:
        conn = self._conn
        assert conn is not None
        cur = conn.execute(
            "SELECT * FROM ephemeral_workspaces_v2 WHERE workspace_id = ?", (workspace_id,)
        )
        row = cur.fetchone()
        if row is None:
            return {"ok": False, "error": f"workspace not found: {workspace_id}",
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "workspace": self._workspace_v2_row(row, cur),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def transition_workspace_v2(
        self,
        workspace_id: str,
        expected_from: str | tuple[str, ...],
        to: str,
        *,
        terminal_reason: str = "",
    ) -> dict[str, Any]:
        """Compare-and-set one V2 lifecycle transition."""
        expected = (expected_from,) if type(expected_from) is str else expected_from
        if type(expected) is not tuple or not expected or any(type(v) is not str for v in expected):
            raise ValueError("expected_from must be a state or non-empty state tuple")
        conn = self._conn
        assert conn is not None
        placeholders = ",".join("?" for _ in expected)
        params: tuple[Any, ...] = (to, time.time(), terminal_reason, workspace_id, *expected)
        cur = conn.execute(
            f"UPDATE ephemeral_workspaces_v2 SET state = ?, updated_at = ?, terminal_reason = ? "
            f"WHERE workspace_id = ? AND state IN ({placeholders})",
            params,
        )
        if cur.rowcount != 1:
            current = self.get_workspace_v2(workspace_id)
            actual = current.get("workspace", {}).get("state", "MISSING")
            return {"ok": False, "error": "stale_workspace_state", "workspace_id": workspace_id,
                    "expected": list(expected), "actual": actual,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "workspace_id": workspace_id, "from": list(expected), "to": to,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def update_workspace_v2(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        """Update only bounded V2 evidence fields; lifecycle state is CAS-only."""
        allowed = {
            "sandbox_path", "node_receipts", "failure_records", "usage_json",
            "cleanup_receipt", "certificate_json", "lease_status", "terminal_reason",
        }
        if not fields or not set(fields) <= allowed:
            raise ValueError("unknown or empty workspace evidence update")
        encoded: dict[str, Any] = {}
        for name, value in fields.items():
            encoded[name] = (
                self._workspace_v2_json(value, name)
                if name in {"node_receipts", "failure_records", "usage_json",
                            "cleanup_receipt", "certificate_json"}
                else value
            )
        assignments = ", ".join(f"{name} = ?" for name in sorted(encoded))
        params = [encoded[name] for name in sorted(encoded)]
        params.extend([time.time(), workspace_id])
        conn = self._conn
        assert conn is not None
        cur = conn.execute(
            f"UPDATE ephemeral_workspaces_v2 SET {assignments}, updated_at = ? WHERE workspace_id = ?",
            tuple(params),
        )
        return {"ok": cur.rowcount == 1, "workspace_id": workspace_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def commit_workspace_v2_node_execution(
        self,
        workspace_id: str,
        *,
        expected_node_receipts: dict[str, Any],
        expected_usage: dict[str, Any],
        node_receipts: dict[str, Any],
        usage_json: dict[str, Any],
        now: float | None = None,
    ) -> dict[str, Any]:
        """Atomically persist node evidence only while execution authority remains active."""
        for name, value in (
            ("expected_node_receipts", expected_node_receipts),
            ("expected_usage", expected_usage),
            ("node_receipts", node_receipts),
            ("usage_json", usage_json),
        ):
            if type(value) is not dict:
                raise ValueError(f"{name} must be an exact object")
        current_time = time.time() if now is None else now
        if type(current_time) not in {int, float}:
            raise ValueError("now must be a finite number")
        current_time = float(current_time)
        if not (current_time == current_time and abs(current_time) != float("inf")):
            raise ValueError("now must be a finite number")
        expected_receipts_json = self._workspace_v2_json(
            expected_node_receipts, "expected_node_receipts"
        )
        expected_usage_json = self._workspace_v2_json(expected_usage, "expected_usage")
        receipts_json = self._workspace_v2_json(node_receipts, "node_receipts")
        usage_encoded = self._workspace_v2_json(usage_json, "usage_json")
        conn = self._conn
        assert conn is not None
        cur = conn.execute(
            """
            UPDATE ephemeral_workspaces_v2
            SET node_receipts = ?, usage_json = ?, updated_at = ?
            WHERE workspace_id = ?
              AND state = 'ACTIVE'
              AND lease_status = 'ACTIVE'
              AND expires_at > ?
              AND node_receipts = ?
              AND usage_json = ?
            """,
            (
                receipts_json,
                usage_encoded,
                current_time,
                workspace_id,
                current_time,
                expected_receipts_json,
                expected_usage_json,
            ),
        )
        if cur.rowcount == 1:
            return {
                "ok": True,
                "workspace_id": workspace_id,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        row = conn.execute(
            """
            SELECT state, lease_status, expires_at
            FROM ephemeral_workspaces_v2
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        if row is None:
            error = "workspace_execution_invalidated"
            state, lease_status, expires_at = "MISSING", "MISSING", 0.0
        else:
            state, lease_status, expires_at = row
            error = (
                "workspace_execution_invalidated"
                if state != "ACTIVE"
                or lease_status != "ACTIVE"
                or current_time >= expires_at
                else "stale_workspace_evidence"
            )
        return {
            "ok": False,
            "error": error,
            "workspace_id": workspace_id,
            "state": state,
            "lease_status": lease_status,
            "expires_at": expires_at,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def revoke_workspace_v2_lease(self, workspace_id: str, *, reason: str) -> dict[str, Any]:
        if type(reason) is not str or not reason:
            raise ValueError("lease revocation reason is required")
        return self.update_workspace_v2(
            workspace_id, lease_status="REVOKED", terminal_reason=reason
        )

    def is_workspace_v2_lease_active(self, workspace_id: str) -> bool:
        conn = self._conn
        assert conn is not None
        row = conn.execute(
            "SELECT lease_status, expires_at, state FROM ephemeral_workspaces_v2 WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        return bool(row and row[0] == "ACTIVE" and time.time() < row[1]
                    and row[2] not in {"DISSOLVING", "DISSOLVED"})

    def list_expired_workspaces_v2(self, *, now: float | None = None) -> dict[str, Any]:
        current = time.time() if now is None else now
        conn = self._conn
        assert conn is not None
        rows = conn.execute(
            "SELECT workspace_id FROM ephemeral_workspaces_v2 "
            "WHERE expires_at <= ? AND state != 'DISSOLVED'",
            (current,),
        ).fetchall()
        values = [row[0] for row in rows]
        return {"ok": True, "workspace_ids": values, "count": len(values),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @classmethod
    def for_tests(cls, tmp_path: str | Path) -> EphemeralRegistryStore:
        """Create a test-isolated store."""
        return cls(db_path=Path(tmp_path) / "test_ephemeral_registry.sqlite3")
