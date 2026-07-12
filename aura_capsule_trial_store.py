"""Independent SQLite WAL ledger for C3 trial runs, observations, and IR proposals."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any

from aura_capsule_trial_types import (
    PROCEDURE_INDUCTION_PROPOSED,
    InducedProcedureProposal,
    canonical_digest,
)

CAPSULE_TRIAL_STORE_VERSION = "AURA_CAPSULE_TRIAL_STORE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_SCHEMA_VERSION = 1
_SCHEMA = """
CREATE TABLE IF NOT EXISTS c3_trial_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    winner_variant_id TEXT NOT NULL,
    report_json TEXT NOT NULL,
    report_digest TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS c3_trial_observations (
    trial_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    dataset TEXT NOT NULL CHECK(dataset IN ('TRAIN','VALIDATION','SHADOW')),
    observation_json TEXT NOT NULL,
    observation_digest TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_c3_trials_run ON c3_trial_observations(run_id);
CREATE INDEX IF NOT EXISTS idx_c3_trials_dataset ON c3_trial_observations(dataset, variant_id);
CREATE TABLE IF NOT EXISTS c3_procedure_proposals (
    procedure_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status = 'PROCEDURE_INDUCTION_PROPOSED'),
    ir_floor TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    proposal_json TEXT NOT NULL,
    proposal_digest TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_c3_procedure_run ON c3_procedure_proposals(run_id);
CREATE TABLE IF NOT EXISTS c3_trial_migrations (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);
"""


class CapsuleTrialStore:
    """Proposal store deliberately exposing no apply, install, promote, or merge method."""

    def __init__(self, repo_root: str | Path = ".", *, db_path: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.db_path = (
            Path(db_path).resolve()
            if db_path is not None
            else self.repo_root / "Aura_Memory" / "capsule_trial_crucible.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(_SCHEMA)
        self._conn.execute(
            "INSERT OR IGNORE INTO c3_trial_migrations(version, applied_at) VALUES (?, ?)",
            (_SCHEMA_VERSION, time.time()),
        )
        self._conn.commit()

    def record_observation(self, observation: dict[str, Any]) -> dict[str, Any]:
        raw = dict(observation or {})
        trial_id = str(raw.get("trial_id") or "")
        required = ("run_id", "variant_id", "case_id", "dataset")
        missing = [key for key in required if not raw.get(key)]
        if not trial_id or missing:
            return _denial("missing_trial_fields", missing=missing + ([] if trial_id else ["trial_id"]))
        if str(raw.get("dataset")) not in {"TRAIN", "VALIDATION", "SHADOW"}:
            return _denial("invalid_trial_dataset")
        return self._insert(
            table="c3_trial_observations",
            id_column="trial_id",
            identifier=trial_id,
            digest_column="observation_digest",
            digest=canonical_digest(raw),
            sql="""INSERT INTO c3_trial_observations(
                trial_id, run_id, variant_id, case_id, dataset,
                observation_json, observation_digest, created_at
                ) VALUES (?,?,?,?,?,?,?,?)""",
            params=(
                trial_id,
                str(raw["run_id"]),
                str(raw["variant_id"]),
                str(raw["case_id"]),
                str(raw["dataset"]),
                _json(raw),
                canonical_digest(raw),
                time.time(),
            ),
        )

    def record_procedure(self, proposal: InducedProcedureProposal | dict[str, Any]) -> dict[str, Any]:
        if isinstance(proposal, InducedProcedureProposal):
            raw = proposal.to_dict()
        else:
            candidate = dict(proposal or {})
            candidate.pop("procedure_digest", None)
            try:
                raw = InducedProcedureProposal(**candidate).to_dict()
            except (TypeError, ValueError) as exc:
                return _denial(f"invalid_procedure_contract:{type(exc).__name__}")
        if raw.get("status") != PROCEDURE_INDUCTION_PROPOSED:
            return _denial("invalid_procedure_status")
        if raw.get("executable_code_generated") is not False or raw.get("automatic_code_installation") is not False:
            return _denial("procedure_must_remain_non_executable_and_uninstalled")
        procedure_id = str(raw.get("procedure_id") or "")
        digest = str(raw.get("procedure_digest") or canonical_digest(raw))
        return self._insert(
            table="c3_procedure_proposals",
            id_column="procedure_id",
            identifier=procedure_id,
            digest_column="proposal_digest",
            digest=digest,
            sql="""INSERT INTO c3_procedure_proposals(
                procedure_id, run_id, status, ir_floor, variant_id,
                proposal_json, proposal_digest, created_at
                ) VALUES (?,?,?,?,?,?,?,?)""",
            params=(
                procedure_id,
                str(raw.get("run_id") or ""),
                PROCEDURE_INDUCTION_PROPOSED,
                str(raw.get("ir_floor") or ""),
                str(raw.get("variant_id") or ""),
                _json({key: value for key, value in raw.items() if key != "procedure_digest"}),
                digest,
                float(raw.get("created_at") or time.time()),
            ),
        )

    def record_run(self, report: dict[str, Any]) -> dict[str, Any]:
        raw = dict(report or {})
        run_id = str(raw.get("run_id") or "")
        if not run_id:
            return _denial("run_id_required")
        digest = canonical_digest(raw)
        return self._insert(
            table="c3_trial_runs",
            id_column="run_id",
            identifier=run_id,
            digest_column="report_digest",
            digest=digest,
            sql="""INSERT INTO c3_trial_runs(
                run_id, status, policy_id, winner_variant_id,
                report_json, report_digest, created_at
                ) VALUES (?,?,?,?,?,?,?)""",
            params=(
                run_id,
                str(raw.get("status") or ""),
                str((raw.get("policy") or {}).get("policy_id") or ""),
                str(raw.get("winner_variant_id") or ""),
                _json(raw),
                digest,
                time.time(),
            ),
        )

    def get_procedure(self, procedure_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT proposal_json, proposal_digest FROM c3_procedure_proposals WHERE procedure_id = ?",
            (str(procedure_id),),
        ).fetchone()
        if row is None:
            return None
        data = json.loads(row["proposal_json"])
        data["procedure_digest"] = row["proposal_digest"]
        return data

    def list_procedures(self, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT proposal_json, proposal_digest FROM c3_procedure_proposals ORDER BY created_at DESC LIMIT ?",
            (max(1, min(int(limit), 1000)),),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            data = json.loads(row["proposal_json"])
            data["procedure_digest"] = row["proposal_digest"]
            result.append(data)
        return result

    def status(self) -> dict[str, Any]:
        journal = str(self._conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        return {
            "ok": True,
            "version": CAPSULE_TRIAL_STORE_VERSION,
            "schema_version": _SCHEMA_VERSION,
            "db_path": str(self.db_path),
            "journal_mode": journal,
            "run_count": int(self._conn.execute("SELECT COUNT(*) FROM c3_trial_runs").fetchone()[0]),
            "observation_count": int(self._conn.execute("SELECT COUNT(*) FROM c3_trial_observations").fetchone()[0]),
            "procedure_proposal_count": int(self._conn.execute("SELECT COUNT(*) FROM c3_procedure_proposals").fetchone()[0]),
            "terminal_status": PROCEDURE_INDUCTION_PROPOSED,
            "apply_operation_available": False,
            "promotion_operation_available": False,
            "installation_operation_available": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "CapsuleTrialStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _insert(
        self,
        *,
        table: str,
        id_column: str,
        identifier: str,
        digest_column: str,
        digest: str,
        sql: str,
        params: tuple[Any, ...],
    ) -> dict[str, Any]:
        if not identifier:
            return _denial(f"{id_column}_required")
        existing = self._conn.execute(
            f"SELECT {digest_column} FROM {table} WHERE {id_column} = ?",
            (identifier,),
        ).fetchone()
        if existing:
            if str(existing[digest_column]) == digest:
                return {"ok": True, id_column: identifier, digest_column: digest, "idempotent_replay": True}
            return _denial(f"{id_column}_digest_conflict")
        try:
            self._conn.execute(sql, params)
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            return _denial(f"database_write_failed:{type(exc).__name__}")
        return {"ok": True, id_column: identifier, digest_column: digest, "idempotent_replay": False}


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _denial(reason: str, *, missing: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "missing": list(missing or []),
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_code_installation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }
