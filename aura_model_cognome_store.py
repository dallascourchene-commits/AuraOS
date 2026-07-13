"""Local-first SQLite facade for Aura's Model Cognome V1."""
from __future__ import annotations

from pathlib import Path
import sqlite3
import time
from typing import Any

from aura_model_cognome import PATCH_AUTHORITY, SCHEMA_VERSION, VSA_PATCH_AUTHORITY
from aura_model_cognome_store_io import CognomeIOMixin
from aura_model_cognome_store_records import CognomeRecordMixin
from aura_model_cognome_store_schema import (
    SCHEMA, STORE_SCHEMA_VERSION, STORE_VERSION, db_path, sanitize_for_storage,
)

__all__ = ["ModelCognomeStore", "sanitize_for_storage"]


class ModelCognomeStore(CognomeRecordMixin, CognomeIOMixin):
    """SQLite implementation of the Model Cognome storage protocol."""

    def __init__(self, repo_root: str | Path = ".", *, db_path: str | Path | None = None) -> None:
        self.db_path = globals()["db_path"](repo_root, db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._conn.commit()

    def _columns(self, table: str) -> set[str]:
        return {str(row[1]) for row in self._conn.execute(f"PRAGMA table_info({table})")}

    def _migrate(self) -> None:
        current = self._conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        if current < 1:
            self._conn.execute("INSERT OR REPLACE INTO schema_migrations VALUES(1,?)", (time.time(),)); current = 1
        if current < 2:
            if "capability_graph_digest" not in self._columns("model_capability_edges"):
                self._conn.execute("ALTER TABLE model_capability_edges ADD COLUMN capability_graph_digest TEXT NOT NULL DEFAULT ''")
            if "verifier_id" not in self._columns("task_contexts"):
                self._conn.execute("ALTER TABLE task_contexts ADD COLUMN verifier_id TEXT NOT NULL DEFAULT ''")
            info = self._conn.execute("PRAGMA table_info(capability_posteriors)").fetchall()
            pk = [str(row[1]) for row in sorted(info, key=lambda row: int(row[5])) if int(row[5]) > 0]
            if "validation_split" not in self._columns("capability_posteriors") or pk[-1:] != ["validation_split"]:
                self._conn.execute("ALTER TABLE capability_posteriors RENAME TO capability_posteriors_v1")
                self._conn.execute("""CREATE TABLE capability_posteriors(
                 profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id), task_bucket TEXT NOT NULL,
                 context_bucket TEXT NOT NULL, verifier_id TEXT NOT NULL, validation_split TEXT NOT NULL,
                 sample_count INTEGER NOT NULL, verified_success_alpha REAL NOT NULL,
                 verified_success_beta REAL NOT NULL, evidence_digest TEXT NOT NULL, status TEXT NOT NULL,
                 last_validated_at REAL NOT NULL, record_json TEXT NOT NULL,
                 PRIMARY KEY(profile_id,task_bucket,context_bucket,verifier_id,validation_split))""")
                old = self._columns("capability_posteriors_v1")
                if old:
                    split = "validation_split" if "validation_split" in old else "'TRAIN'"
                    self._conn.execute(f"""INSERT INTO capability_posteriors
                     SELECT profile_id,task_bucket,context_bucket,verifier_id,{split},sample_count,
                     verified_success_alpha,verified_success_beta,evidence_digest,status,last_validated_at,record_json
                     FROM capability_posteriors_v1""")
                self._conn.execute("DROP TABLE capability_posteriors_v1")
            for table,column,declaration in (("latency_distributions","cold_warm_cache_class","TEXT NOT NULL DEFAULT 'UNSPECIFIED'"),("storage_sync_outbox","payload_json","TEXT NOT NULL DEFAULT '{}'"),("legacy_model_probe_imports","skipped_count","INTEGER NOT NULL DEFAULT 0")):
                if column not in self._columns(table): self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
            self._conn.execute("INSERT OR REPLACE INTO schema_migrations VALUES(2,?)", (time.time(),))

    def schema_status(self) -> dict[str, Any]:
        tables = [row[0] for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        version = self._conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        return {"ok":True,"cognome_schema_version":SCHEMA_VERSION,"store_schema_version":int(version),
                "journal_mode":self._conn.execute("PRAGMA journal_mode").fetchone()[0].lower(),
                "foreign_keys":bool(self._conn.execute("PRAGMA foreign_keys").fetchone()[0]),
                "tables":tables,"db_path":str(self.db_path),"store_version":STORE_VERSION,
                "patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":VSA_PATCH_AUTHORITY}

    def close(self) -> None: self._conn.close()
    def __enter__(self) -> "ModelCognomeStore": return self
    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None: self.close()
