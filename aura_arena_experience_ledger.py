"""SQLite WAL ledger for authoritative ArenaExperience V3 records."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any

from aura_relationship_experience import (
    RelationshipExperienceObservation,
    project_relationship_timeline,
)

from aura_arena_experience import (
    ARENA_EXPERIENCE_VERSION,
    ArenaExperience,
    OutcomeVector,
    canonical_experience_digest,
    sanitize_experience_payload,
)

ARENA_EXPERIENCE_LEDGER_VERSION = "AURA_ARENA_EXPERIENCE_LEDGER_V4"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_SCHEMA_VERSION = 4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS arena_experiences (
 experience_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, task_id TEXT, workflow_id TEXT,
 arena_id TEXT NOT NULL, arena_version TEXT NOT NULL, grammar_version TEXT NOT NULL,
 grammar_manifest_digest TEXT NOT NULL DEFAULT '', runtime_version TEXT NOT NULL, compiler_version TEXT NOT NULL,
 started_at REAL NOT NULL, completed_at REAL NOT NULL, state_before TEXT NOT NULL, state_after TEXT NOT NULL,
 selected_transition TEXT, final_outcome TEXT NOT NULL, outcome_vector_json TEXT NOT NULL DEFAULT '{}',
 admissible_alternatives_json TEXT NOT NULL DEFAULT '[]', predictions_json TEXT NOT NULL DEFAULT '[]',
 route_observation_digest TEXT NOT NULL DEFAULT '', intent_packet_digest TEXT NOT NULL DEFAULT '',
 vsa_profile_digest TEXT NOT NULL DEFAULT '', route_capsule_digest TEXT NOT NULL DEFAULT '',
 aperture_digest TEXT NOT NULL DEFAULT '', actual_context_digest TEXT NOT NULL DEFAULT '',
 actual_tool_calls_json TEXT NOT NULL DEFAULT '[]', actual_model TEXT NOT NULL DEFAULT '',
 budget_requested_json TEXT NOT NULL DEFAULT '{}', budget_consumed_json TEXT NOT NULL DEFAULT '{}',
 repository_commit_sha TEXT, working_tree_digest TEXT, objective_hash TEXT, source_hash_digest TEXT,
 provider TEXT, model TEXT, measurement_class TEXT, cost_run_id TEXT,
 trace_atom_ids_json TEXT NOT NULL, raw_evidence_refs_json TEXT NOT NULL, redactions_json TEXT NOT NULL,
 payload_json TEXT NOT NULL, experience_digest TEXT NOT NULL, schema_version TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_experience_arena_state ON arena_experiences(arena_id,state_before,selected_transition);
CREATE INDEX IF NOT EXISTS idx_experience_task ON arena_experiences(task_id);
CREATE INDEX IF NOT EXISTS idx_experience_correlation ON arena_experiences(correlation_id);
CREATE INDEX IF NOT EXISTS idx_experience_commit ON arena_experiences(repository_commit_sha);
CREATE INDEX IF NOT EXISTS idx_experience_outcome ON arena_experiences(final_outcome);
CREATE TABLE IF NOT EXISTS relationship_experiences (
 observation_id TEXT PRIMARY KEY, relationship_id TEXT NOT NULL, relationship_digest TEXT NOT NULL,
 repository_head TEXT NOT NULL, working_tree_digest TEXT NOT NULL, valid_from_head TEXT NOT NULL,
 valid_to_head TEXT NOT NULL DEFAULT '', transaction_time REAL NOT NULL, outcome TEXT NOT NULL,
 human_disposition TEXT NOT NULL, privacy_class TEXT NOT NULL, observation_digest TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_relationship_experience_identity ON relationship_experiences(relationship_id,transaction_time);
CREATE INDEX IF NOT EXISTS idx_relationship_experience_head ON relationship_experiences(repository_head);
CREATE TABLE IF NOT EXISTS arena_experience_migrations(version INTEGER PRIMARY KEY,applied_at REAL NOT NULL);
"""

_JSON_FIELDS = {
    "outcome_vector": "outcome_vector_json",
    "admissible_alternatives": "admissible_alternatives_json",
    "predictions": "predictions_json",
    "actual_tool_calls": "actual_tool_calls_json",
    "budget_requested": "budget_requested_json",
    "budget_consumed": "budget_consumed_json",
    "trace_atom_ids": "trace_atom_ids_json",
    "raw_evidence_refs": "raw_evidence_refs_json",
    "redactions": "redactions_json",
    "payload": "payload_json",
}

_INSERT_COLUMNS = (
    "experience_id", "correlation_id", "task_id", "workflow_id", "arena_id", "arena_version",
    "grammar_version", "grammar_manifest_digest", "runtime_version", "compiler_version",
    "started_at", "completed_at", "state_before", "state_after", "selected_transition",
    "final_outcome", "outcome_vector_json", "admissible_alternatives_json", "predictions_json",
    "route_observation_digest", "intent_packet_digest", "vsa_profile_digest", "route_capsule_digest",
    "aperture_digest", "actual_context_digest", "actual_tool_calls_json", "actual_model",
    "budget_requested_json", "budget_consumed_json", "repository_commit_sha", "working_tree_digest",
    "objective_hash", "source_hash_digest", "provider", "model", "measurement_class", "cost_run_id",
    "trace_atom_ids_json", "raw_evidence_refs_json", "redactions_json", "payload_json",
    "experience_digest", "schema_version", "created_at",
)


class ArenaExperienceLedger:
    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        db_path: str | Path | None = None,
    ) -> None:
        root = Path(repo_root).resolve()
        self.db_path = Path(db_path).resolve() if db_path else root / "Aura_Memory" / "arena_experience.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        columns = {str(row[1]) for row in self._conn.execute("PRAGMA table_info(arena_experiences)")}
        additions = {
            "grammar_manifest_digest": "TEXT NOT NULL DEFAULT ''",
            "outcome_vector_json": "TEXT NOT NULL DEFAULT '{}'",
            "admissible_alternatives_json": "TEXT NOT NULL DEFAULT '[]'",
            "predictions_json": "TEXT NOT NULL DEFAULT '[]'",
            "route_observation_digest": "TEXT NOT NULL DEFAULT ''",
            "intent_packet_digest": "TEXT NOT NULL DEFAULT ''",
            "vsa_profile_digest": "TEXT NOT NULL DEFAULT ''",
            "route_capsule_digest": "TEXT NOT NULL DEFAULT ''",
            "aperture_digest": "TEXT NOT NULL DEFAULT ''",
            "actual_context_digest": "TEXT NOT NULL DEFAULT ''",
            "actual_tool_calls_json": "TEXT NOT NULL DEFAULT '[]'",
            "actual_model": "TEXT NOT NULL DEFAULT ''",
            "budget_requested_json": "TEXT NOT NULL DEFAULT '{}'",
            "budget_consumed_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for name, declaration in additions.items():
            if name not in columns:
                self._conn.execute(f"ALTER TABLE arena_experiences ADD COLUMN {name} {declaration}")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_experience_grammar_digest "
            "ON arena_experiences(arena_id,grammar_version,grammar_manifest_digest)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_experience_capsule_digest "
            "ON arena_experiences(route_capsule_digest,aperture_digest)"
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO arena_experience_migrations(version,applied_at) VALUES (?,?)",
            (_SCHEMA_VERSION, time.time()),
        )

    def record(self, experience: ArenaExperience | dict[str, Any]) -> dict[str, Any]:
        raw = experience.to_dict() if isinstance(experience, ArenaExperience) else dict(experience)
        raw["payload"], red0 = sanitize_experience_payload(raw.get("payload") or {})
        raw["admissible_alternatives"], red1 = sanitize_experience_payload(raw.get("admissible_alternatives") or [])
        raw["predictions"], red2 = sanitize_experience_payload(raw.get("predictions") or [])
        raw["redactions"] = sorted(set([str(item) for item in raw.get("redactions", [])] + red0 + red1 + red2))
        raw.setdefault("version", ARENA_EXPERIENCE_VERSION)
        raw.setdefault("actual_tool_calls", [])
        raw.setdefault("budget_requested", {})
        raw.setdefault("budget_consumed", {})

        required = (
            "experience_id", "correlation_id", "arena_id", "arena_version", "grammar_version",
            "grammar_manifest_digest", "runtime_version", "compiler_version", "state_before",
            "state_after", "final_outcome", "outcome_vector",
        )
        missing = [key for key in required if not _present(raw.get(key))]
        if missing:
            return _deny("missing_required_fields", missing=missing)
        try:
            raw["outcome_vector"] = OutcomeVector.from_dict(raw["outcome_vector"]).to_dict()
        except (TypeError, ValueError) as exc:
            return _deny(f"invalid_outcome_vector:{type(exc).__name__}")
        if not isinstance(raw["admissible_alternatives"], list) or not all(
            isinstance(item, dict) for item in raw["admissible_alternatives"]
        ):
            return _deny("invalid_admissible_alternatives")
        if not isinstance(raw["predictions"], list) or not all(
            isinstance(item, dict) for item in raw["predictions"]
        ):
            return _deny("invalid_predictions")
        if not isinstance(raw.get("budget_requested"), dict) or not isinstance(raw.get("budget_consumed"), dict):
            return _deny("invalid_capsule_budget_fields")
        try:
            started = float(raw.get("started_at"))
            completed = float(raw.get("completed_at"))
        except (TypeError, ValueError):
            return _deny("invalid_timestamps")
        if completed < started:
            return _deny("completed_before_started")

        digest = canonical_experience_digest(raw)
        experience_id = str(raw["experience_id"])
        prior = self._conn.execute(
            "SELECT experience_digest FROM arena_experiences WHERE experience_id=?",
            (experience_id,),
        ).fetchone()
        if prior:
            if prior["experience_digest"] == digest:
                return {
                    "ok": True,
                    "experience_id": experience_id,
                    "experience_digest": digest,
                    "idempotent_replay": True,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": False,
                }
            return _deny("experience_id_digest_conflict", experience_id=experience_id)

        values: list[Any] = []
        for column in _INSERT_COLUMNS:
            if column == "experience_digest":
                values.append(digest)
            elif column == "schema_version":
                values.append(str(raw.get("version") or ARENA_EXPERIENCE_VERSION))
            elif column == "created_at":
                values.append(time.time())
            elif column == "started_at":
                values.append(started)
            elif column == "completed_at":
                values.append(completed)
            elif column.endswith("_json"):
                source = next(key for key, mapped in _JSON_FIELDS.items() if mapped == column)
                values.append(_json(raw.get(source) or ([] if source.endswith("s") else {})))
            else:
                values.append(str(raw.get(column) or ""))

        placeholders = ",".join("?" for _ in _INSERT_COLUMNS)
        sql = f"INSERT INTO arena_experiences({','.join(_INSERT_COLUMNS)}) VALUES ({placeholders})"
        try:
            self._conn.execute(sql, values)
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            return _deny(f"database_write_failed:{type(exc).__name__}")
        return {
            "ok": True,
            "experience_id": experience_id,
            "experience_digest": digest,
            "idempotent_replay": False,
            "redactions": raw["redactions"],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }


    def record_relationship_observation(
        self,
        observation: RelationshipExperienceObservation | dict[str, Any],
    ) -> dict[str, Any]:
        """Append one canonical relationship receipt projection to the derived ledger."""
        try:
            item = (
                observation
                if isinstance(observation, RelationshipExperienceObservation)
                else RelationshipExperienceObservation.from_dict(observation)
            )
        except (TypeError, ValueError) as exc:
            return _deny(f"invalid_relationship_observation:{type(exc).__name__}")
        if item.privacy_class == "PRIVATE_REDACTED":
            private_refs = [*item.verifier_evidence_refs, *item.receipt_refs, *item.source_refs]
            if (
                any(not str(value).startswith("redacted:") for value in private_refs)
                or item.reason not in {"", "[REDACTED]"}
            ):
                return _deny(
                    "private_relationship_observation_requires_redaction",
                    observation_id=item.observation_id,
                )
        payload = item.to_dict()
        digest = str(payload["observation_digest"])
        prior = self._conn.execute(
            "SELECT observation_digest FROM relationship_experiences WHERE observation_id=?",
            (item.observation_id,),
        ).fetchone()
        if prior:
            if str(prior["observation_digest"]) == digest:
                return {
                    "ok": True,
                    "observation_id": item.observation_id,
                    "observation_digest": digest,
                    "idempotent_replay": True,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": False,
                }
            return _deny(
                "relationship_observation_id_digest_conflict",
                observation_id=item.observation_id,
            )
        try:
            self._conn.execute(
                "INSERT INTO relationship_experiences("
                "observation_id,relationship_id,relationship_digest,repository_head,working_tree_digest,"
                "valid_from_head,valid_to_head,transaction_time,outcome,human_disposition,privacy_class,"
                "observation_digest,payload_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item.observation_id,
                    item.relationship_id,
                    item.relationship_digest,
                    item.repository_head,
                    item.working_tree_digest,
                    item.valid_from_head,
                    item.valid_to_head,
                    item.transaction_time,
                    item.outcome.value,
                    item.human_disposition.value,
                    item.privacy_class,
                    digest,
                    _json(payload),
                    time.time(),
                ),
            )
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            self._conn.rollback()
            return _deny(f"relationship_database_write_failed:{type(exc).__name__}")
        return {
            "ok": True,
            "observation_id": item.observation_id,
            "observation_digest": digest,
            "idempotent_replay": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }

    def relationship_history(
        self,
        *,
        relationship_id: str = "",
        repository_head: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if relationship_id:
            clauses.append("relationship_id=?")
            params.append(str(relationship_id))
        if repository_head:
            clauses.append("repository_head=?")
            params.append(str(repository_head))
        params.append(max(1, min(int(limit), 10000)))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT payload_json FROM relationship_experiences {where} ORDER BY transaction_time ASC LIMIT ?",
            params,
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                result.append(json.loads(str(row["payload_json"])))
            except json.JSONDecodeError:
                continue
        return result

    def relationship_timeline(
        self,
        *,
        current_repository_head: str,
        relationship_id: str = "",
        now: float | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return project_relationship_timeline(
            self.relationship_history(relationship_id=relationship_id, limit=limit),
            current_repository_head=current_repository_head,
            now=now,
        )

    def rebuild_relationship_projection(
        self,
        receipts: list[RelationshipExperienceObservation | dict[str, Any]],
    ) -> dict[str, Any]:
        """Replay canonical receipts into an empty or recovered derived projection."""
        recorded = 0
        idempotent = 0
        rejected: list[dict[str, Any]] = []
        for receipt in receipts:
            result = self.record_relationship_observation(receipt)
            if result.get("ok"):
                recorded += 1
                idempotent += int(bool(result.get("idempotent_replay")))
            else:
                rejected.append(result)
        return {
            "ok": not rejected,
            "recorded": recorded,
            "idempotent": idempotent,
            "rejected": rejected,
            "recoverable_from_canonical_receipts": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }

    def get(self, experience_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM arena_experiences WHERE experience_id=?", (str(experience_id),)
        ).fetchone()
        return _decode(row) if row else None

    def history(
        self,
        *,
        arena_id: str = "",
        task_id: str = "",
        grammar_manifest_digest: str = "",
        route_capsule_digest: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for column, value in (
            ("arena_id", arena_id),
            ("task_id", task_id),
            ("grammar_manifest_digest", grammar_manifest_digest),
            ("route_capsule_digest", route_capsule_digest),
        ):
            if value:
                clauses.append(f"{column}=?")
                params.append(value)
        params.append(max(1, min(int(limit), 10000)))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return [
            _decode(row)
            for row in self._conn.execute(
                f"SELECT * FROM arena_experiences {where} ORDER BY completed_at DESC LIMIT ?",
                params,
            ).fetchall()
        ]

    def export_jsonl(self, path: str | Path, *, arena_id: str = "", limit: int = 10000) -> dict[str, Any]:
        rows = self.history(arena_id=arena_id, limit=limit)
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(json.dumps(row, sort_keys=True, ensure_ascii=True, default=str) + "\n" for row in reversed(rows)),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "path": str(output),
            "record_count": len(rows),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }

    def status(self) -> dict[str, Any]:
        count = int(self._conn.execute("SELECT COUNT(*) FROM arena_experiences").fetchone()[0])
        complete = int(self._conn.execute(
            "SELECT COUNT(*) FROM arena_experiences "
            "WHERE grammar_manifest_digest!='' AND outcome_vector_json!='{}'"
        ).fetchone()[0])
        capsule_records = int(self._conn.execute(
            "SELECT COUNT(*) FROM arena_experiences WHERE route_capsule_digest!=''"
        ).fetchone()[0])
        relationship_records = int(self._conn.execute(
            "SELECT COUNT(*) FROM relationship_experiences"
        ).fetchone()[0])
        return {
            "ok": True,
            "version": ARENA_EXPERIENCE_LEDGER_VERSION,
            "schema_version": _SCHEMA_VERSION,
            "db_path": str(self.db_path),
            "journal_mode": str(self._conn.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
            "record_count": count,
            "v2_complete_record_count": complete,
            "v3_complete_record_count": complete,
            "capsule_record_count": capsule_records,
            "relationship_experience_count": relationship_records,
            "legacy_record_count": count - complete,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ArenaExperienceLedger":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


def _decode(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    defaults = {
        "trace_atom_ids_json": [],
        "raw_evidence_refs_json": [],
        "redactions_json": [],
        "payload_json": {},
        "outcome_vector_json": {},
        "admissible_alternatives_json": [],
        "predictions_json": [],
        "actual_tool_calls_json": [],
        "budget_requested_json": {},
        "budget_consumed_json": {},
    }
    for key, default in defaults.items():
        value = data.pop(key, "")
        output_key = key.removesuffix("_json")
        try:
            data[output_key] = json.loads(value) if value else default
        except json.JSONDecodeError:
            data[output_key] = default
    data["version"] = data.pop("schema_version", ARENA_EXPERIENCE_VERSION)
    data["legacy_record"] = not bool(data.get("grammar_manifest_digest") and data.get("outcome_vector"))
    data.update(
        patch_authority=PATCH_AUTHORITY,
        vsa_patch_authority=False,
        learned_weight_patch_authority=False,
        crystallization_patch_authority=False,
    )
    return data


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _present(value: Any) -> bool:
    return bool(value) if isinstance(value, dict) else bool(str(value or "").strip())


def _deny(
    reason: str,
    *,
    missing: list[str] | None = None,
    experience_id: str = "",
    observation_id: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "reason": reason,
        "missing": list(missing or []),
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    if experience_id:
        result["experience_id"] = experience_id
    if observation_id:
        result["observation_id"] = observation_id
    return result
