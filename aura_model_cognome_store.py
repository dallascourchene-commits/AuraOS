"""Local-first SQLite store for Aura's Model Cognome V1.

The store uses WAL mode, idempotent record identities, append-only DIKWP evidence,
and recursive secret/prompt/reasoning redaction. Cloud synchronization is not
required and is deliberately not implemented in this first schema slice.
"""
from __future__ import annotations

from dataclasses import is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Mapping

from aura_dikwp_router_pipeline import DIKWPEnvelope
from aura_model_cognome import (
    BEHAVIORAL_SURROGATE,
    INFERRED,
    PATCH_AUTHORITY,
    SCHEMA_VERSION,
    VSA_PATCH_AUTHORITY,
    ModelAccessClass,
    ModelCapabilityEdge,
    ModelEndpointIdentity,
    ModelObservation,
    RouteDecision,
    TaskContext,
    canonical_json,
    stable_digest,
    stable_id,
)

STORE_VERSION = "AURA_MODEL_COGNOME_STORE_V1"
DEFAULT_DB_NAME = "model_cognome.db"

_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|secret|password|authorization|access[_-]?token|refresh[_-]?token|private[_-]?key|cookie)",
    re.IGNORECASE,
)
_PRIVATE_REASONING_KEY = re.compile(
    r"(?:chain[_-]?of[_-]?thought|private[_-]?reasoning|reasoning[_-]?trace|hidden[_-]?thoughts|raw[_-]?prompt|full[_-]?prompt)",
    re.IGNORECASE,
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS model_endpoints (
    profile_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    returned_model TEXT NOT NULL,
    base_url_digest TEXT NOT NULL,
    access_class TEXT NOT NULL,
    endpoint_fingerprint TEXT NOT NULL,
    fingerprint_version TEXT NOT NULL,
    provider_revision TEXT NOT NULL,
    tokenizer_family TEXT NOT NULL,
    price_snapshot_digest TEXT NOT NULL,
    first_seen_at REAL NOT NULL,
    last_seen_at REAL NOT NULL,
    status TEXT NOT NULL,
    record_json TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_model_endpoint_fingerprint
    ON model_endpoints(endpoint_fingerprint);
CREATE INDEX IF NOT EXISTS idx_model_endpoint_provider_model
    ON model_endpoints(provider, returned_model);
CREATE INDEX IF NOT EXISTS idx_model_endpoint_status
    ON model_endpoints(status);

CREATE TABLE IF NOT EXISTS endpoint_fingerprints (
    fingerprint_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
    endpoint_fingerprint TEXT NOT NULL,
    fingerprint_version TEXT NOT NULL,
    observed_at REAL NOT NULL,
    drift_score REAL,
    status TEXT NOT NULL,
    record_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS probe_suites (
    probe_suite_id TEXT PRIMARY KEY,
    suite_digest TEXT NOT NULL,
    access_class TEXT NOT NULL,
    created_at REAL NOT NULL,
    record_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_contexts (
    task_context_id TEXT PRIMARY KEY,
    objective_hash TEXT NOT NULL,
    purpose_digest TEXT NOT NULL,
    task_family TEXT NOT NULL,
    domain TEXT NOT NULL,
    context_tokens INTEGER NOT NULL,
    capability_graph_digest TEXT NOT NULL,
    topology_digest TEXT NOT NULL,
    source_hash_digest TEXT NOT NULL,
    privacy_class TEXT NOT NULL,
    data_egress_allowed INTEGER NOT NULL,
    record_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_task_context_capability_digest
    ON task_contexts(capability_graph_digest);

CREATE TABLE IF NOT EXISTS route_decisions (
    route_decision_id TEXT PRIMARY KEY,
    task_context_id TEXT NOT NULL REFERENCES task_contexts(task_context_id),
    purpose_digest TEXT NOT NULL,
    policy_mode TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    selected_profile_ids TEXT NOT NULL,
    capability_graph_digest TEXT NOT NULL,
    knowledge_snapshot_digest TEXT NOT NULL,
    proposal_only INTEGER NOT NULL,
    created_at REAL NOT NULL,
    record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_route_decision_task ON route_decisions(task_context_id);

CREATE TABLE IF NOT EXISTS model_observations (
    observation_id TEXT PRIMARY KEY,
    route_decision_id TEXT REFERENCES route_decisions(route_decision_id),
    task_context_id TEXT REFERENCES task_contexts(task_context_id),
    profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
    call_id TEXT NOT NULL,
    policy_mode TEXT NOT NULL,
    verifier_pass INTEGER,
    cost_usd REAL,
    cost_status TEXT NOT NULL,
    end_to_end_ms REAL,
    time_to_verified_outcome_ms REAL,
    measurement_class TEXT NOT NULL,
    evidence_class TEXT NOT NULL,
    failure_class TEXT NOT NULL,
    created_at REAL NOT NULL,
    record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_observation_profile ON model_observations(profile_id);
CREATE INDEX IF NOT EXISTS idx_observation_route ON model_observations(route_decision_id);
CREATE INDEX IF NOT EXISTS idx_observation_task ON model_observations(task_context_id);

CREATE TABLE IF NOT EXISTS model_capability_edges (
    edge_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
    aura_capability_id TEXT NOT NULL,
    task_bucket TEXT NOT NULL,
    support_level TEXT NOT NULL,
    verified_success_probability REAL,
    p50_time_to_verified_ms REAL,
    p95_time_to_verified_ms REAL,
    mean_cost_usd REAL,
    tool_reliability REAL,
    format_reliability REAL,
    evidence_count INTEGER NOT NULL,
    evidence_digest TEXT NOT NULL,
    last_validated_at REAL NOT NULL,
    status TEXT NOT NULL,
    record_json TEXT NOT NULL,
    UNIQUE(profile_id, aura_capability_id, task_bucket)
);
CREATE INDEX IF NOT EXISTS idx_model_capability_lookup
    ON model_capability_edges(aura_capability_id, task_bucket, status);

CREATE TABLE IF NOT EXISTS capability_posteriors (
    profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
    task_bucket TEXT NOT NULL,
    context_bucket TEXT NOT NULL,
    verifier_id TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    verified_success_alpha REAL NOT NULL,
    verified_success_beta REAL NOT NULL,
    evidence_digest TEXT NOT NULL,
    status TEXT NOT NULL,
    last_validated_at REAL NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY(profile_id, task_bucket, context_bucket, verifier_id)
);

CREATE TABLE IF NOT EXISTS latency_distributions (
    distribution_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
    task_bucket TEXT NOT NULL,
    context_bucket TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    p50_ms REAL,
    p95_ms REAL,
    p99_ms REAL,
    record_json TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    price_snapshot_digest TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    record_json TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_comparisons (
    comparison_id TEXT PRIMARY KEY,
    measurement_mode TEXT NOT NULL,
    approved_live INTEGER NOT NULL,
    record_json TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS drift_events (
    drift_event_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
    reference_fingerprint TEXT NOT NULL,
    current_fingerprint TEXT NOT NULL,
    drift_score REAL,
    status TEXT NOT NULL,
    record_json TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dikwp_envelopes (
    envelope_id TEXT PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    purpose_digest TEXT NOT NULL,
    proposal_only INTEGER NOT NULL,
    source_record_ids TEXT NOT NULL,
    created_at REAL NOT NULL,
    record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dikwp_correlation_stage
    ON dikwp_envelopes(correlation_id, stage);

CREATE TABLE IF NOT EXISTS storage_sync_outbox (
    outbox_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    synced_at REAL
);

CREATE TABLE IF NOT EXISTS legacy_model_probe_imports (
    source_digest TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    imported_at REAL NOT NULL
);
"""


def _db_path(repo_root: str | Path = ".", db_path: str | Path | None = None) -> Path:
    if db_path is not None:
        path = Path(db_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    root = Path(repo_root).resolve()
    memory = root / "Aura_Memory"
    memory.mkdir(parents=True, exist_ok=True)
    return memory / DEFAULT_DB_NAME


def sanitize_for_storage(value: Any) -> Any:
    """Recursively redact credentials, raw prompts, and private reasoning fields."""
    if is_dataclass(value):
        value = value.to_dict() if hasattr(value, "to_dict") else value.__dict__
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _SECRET_KEY.search(key_text) or _PRIVATE_REASONING_KEY.search(key_text):
                sanitized[key_text] = "[REDACTED]"
            else:
                sanitized[key_text] = sanitize_for_storage(item)
        return sanitized
    if isinstance(value, (tuple, list)):
        return [sanitize_for_storage(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(sanitize_for_storage(item) for item in value)
    if isinstance(value, str):
        redacted = value
        for pattern in _SECRET_VALUE_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    return value


def _record_json(value: Any) -> str:
    return canonical_json(sanitize_for_storage(value))


def _parse_timestamp(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
        except ValueError:
            pass
    return time.time()


class ModelCognomeStore:
    """SQLite V1 implementation of the Model Cognome storage protocol."""

    def __init__(self, repo_root: str | Path = ".", *, db_path: str | Path | None = None) -> None:
        self.db_path = _db_path(repo_root, db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        current = self._conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        if current < SCHEMA_VERSION:
            self._conn.execute(
                "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, time.time()),
            )

    def schema_status(self) -> dict[str, Any]:
        tables = [
            row[0]
            for row in self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        journal_mode = self._conn.execute("PRAGMA journal_mode").fetchone()[0]
        foreign_keys = self._conn.execute("PRAGMA foreign_keys").fetchone()[0]
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "journal_mode": str(journal_mode).lower(),
            "foreign_keys": bool(foreign_keys),
            "tables": tables,
            "db_path": str(self.db_path),
            "store_version": STORE_VERSION,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _assert_idempotent(self, table: str, id_column: str, record_id: str, record_json: str) -> bool:
        row = self._conn.execute(
            f"SELECT record_json FROM {table} WHERE {id_column} = ?", (record_id,)
        ).fetchone()
        if row is None:
            return False
        if row[0] != record_json:
            raise ValueError(f"Idempotency conflict for {table}.{record_id}")
        return True

    def upsert_endpoint(self, endpoint: ModelEndpointIdentity) -> str:
        data = sanitize_for_storage(endpoint.to_dict())
        record = canonical_json(data)
        self._conn.execute(
            """INSERT INTO model_endpoints(
                profile_id, provider, requested_model, returned_model, base_url_digest,
                access_class, endpoint_fingerprint, fingerprint_version, provider_revision,
                tokenizer_family, price_snapshot_digest, first_seen_at, last_seen_at,
                status, record_json, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(profile_id) DO UPDATE SET
                returned_model=excluded.returned_model,
                endpoint_fingerprint=excluded.endpoint_fingerprint,
                fingerprint_version=excluded.fingerprint_version,
                provider_revision=excluded.provider_revision,
                tokenizer_family=excluded.tokenizer_family,
                price_snapshot_digest=excluded.price_snapshot_digest,
                last_seen_at=excluded.last_seen_at,
                status=excluded.status,
                record_json=excluded.record_json,
                updated_at=excluded.updated_at""",
            (
                endpoint.profile_id, endpoint.provider, endpoint.requested_model,
                endpoint.returned_model, endpoint.base_url_digest, endpoint.access_class,
                endpoint.endpoint_fingerprint, endpoint.fingerprint_version,
                endpoint.provider_revision, endpoint.tokenizer_family,
                endpoint.price_snapshot_digest, endpoint.first_seen_at,
                endpoint.last_seen_at, endpoint.status, record, time.time(),
            ),
        )
        self._conn.commit()
        return endpoint.profile_id

    def record_task_context(self, context: TaskContext) -> str:
        record = _record_json(context)
        if self._assert_idempotent("task_contexts", "task_context_id", context.task_context_id, record):
            return context.task_context_id
        self._conn.execute(
            """INSERT INTO task_contexts(
                task_context_id, objective_hash, purpose_digest, task_family, domain,
                context_tokens, capability_graph_digest, topology_digest,
                source_hash_digest, privacy_class, data_egress_allowed,
                record_json, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                context.task_context_id, context.objective_hash, context.purpose_digest,
                context.task_family, context.domain, context.context_tokens,
                context.capability_graph_digest, context.topology_digest,
                context.source_hash_digest, context.privacy_class,
                int(context.data_egress_allowed), record, time.time(),
            ),
        )
        self._conn.commit()
        return context.task_context_id

    def record_route_decision(self, decision: RouteDecision) -> str:
        record = _record_json(decision)
        if self._assert_idempotent("route_decisions", "route_decision_id", decision.route_decision_id, record):
            return decision.route_decision_id
        self._conn.execute(
            """INSERT INTO route_decisions(
                route_decision_id, task_context_id, purpose_digest, policy_mode,
                policy_version, selected_profile_ids, capability_graph_digest,
                knowledge_snapshot_digest, proposal_only, created_at, record_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                decision.route_decision_id, decision.task_context_id,
                decision.purpose_digest, decision.policy_mode, decision.policy_version,
                canonical_json(decision.selected_profile_ids), decision.capability_graph_digest,
                decision.knowledge_snapshot_digest, int(decision.proposal_only),
                decision.created_at, record,
            ),
        )
        self._conn.commit()
        return decision.route_decision_id

    def record_observation(self, observation: ModelObservation) -> str:
        record = _record_json(observation)
        if self._assert_idempotent("model_observations", "observation_id", observation.observation_id, record):
            return observation.observation_id
        self._conn.execute(
            """INSERT INTO model_observations(
                observation_id, route_decision_id, task_context_id, profile_id,
                call_id, policy_mode, verifier_pass, cost_usd, cost_status,
                end_to_end_ms, time_to_verified_outcome_ms, measurement_class,
                evidence_class, failure_class, created_at, record_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                observation.observation_id,
                observation.route_decision_id or None,
                observation.task_context_id or None,
                observation.profile_id,
                observation.call_id,
                observation.policy_mode,
                None if observation.verifier_pass is None else int(observation.verifier_pass),
                observation.cost_usd,
                observation.cost_status,
                observation.end_to_end_ms,
                observation.time_to_verified_outcome_ms,
                observation.measurement_class,
                observation.evidence_class,
                observation.failure_class,
                observation.created_at,
                record,
            ),
        )
        self._conn.commit()
        return observation.observation_id

    def upsert_model_capability_edge(self, edge: ModelCapabilityEdge) -> str:
        record = _record_json(edge)
        self._conn.execute(
            """INSERT INTO model_capability_edges(
                edge_id, profile_id, aura_capability_id, task_bucket, support_level,
                verified_success_probability, p50_time_to_verified_ms,
                p95_time_to_verified_ms, mean_cost_usd, tool_reliability,
                format_reliability, evidence_count, evidence_digest,
                last_validated_at, status, record_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(profile_id, aura_capability_id, task_bucket) DO UPDATE SET
                edge_id=excluded.edge_id,
                support_level=excluded.support_level,
                verified_success_probability=excluded.verified_success_probability,
                p50_time_to_verified_ms=excluded.p50_time_to_verified_ms,
                p95_time_to_verified_ms=excluded.p95_time_to_verified_ms,
                mean_cost_usd=excluded.mean_cost_usd,
                tool_reliability=excluded.tool_reliability,
                format_reliability=excluded.format_reliability,
                evidence_count=excluded.evidence_count,
                evidence_digest=excluded.evidence_digest,
                last_validated_at=excluded.last_validated_at,
                status=excluded.status,
                record_json=excluded.record_json""",
            (
                edge.edge_id, edge.profile_id, edge.aura_capability_id,
                edge.task_bucket, edge.support_level,
                edge.verified_success_probability, edge.p50_time_to_verified_ms,
                edge.p95_time_to_verified_ms, edge.mean_cost_usd,
                edge.tool_reliability, edge.format_reliability, edge.evidence_count,
                edge.evidence_digest, edge.last_validated_at, edge.status, record,
            ),
        )
        self._conn.commit()
        return edge.edge_id

    def record_dikwp_envelope(self, envelope: DIKWPEnvelope) -> str:
        record = _record_json(envelope.to_dict())
        if self._assert_idempotent("dikwp_envelopes", "envelope_id", envelope.envelope_id, record):
            return envelope.envelope_id
        self._conn.execute(
            """INSERT INTO dikwp_envelopes(
                envelope_id, correlation_id, stage, payload_digest, purpose_digest,
                proposal_only, source_record_ids, created_at, record_json
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                envelope.envelope_id, envelope.correlation_id, envelope.stage,
                envelope.payload_digest, envelope.purpose_digest,
                int(envelope.proposal_only), canonical_json(envelope.source_record_ids),
                envelope.created_at, record,
            ),
        )
        self._conn.commit()
        return envelope.envelope_id

    def record_price_snapshot(self, snapshot: Mapping[str, Any]) -> str:
        clean = sanitize_for_storage(snapshot)
        digest = stable_digest(clean)
        record = canonical_json(clean)
        if self._assert_idempotent("price_snapshots", "price_snapshot_digest", digest, record):
            return digest
        self._conn.execute(
            """INSERT INTO price_snapshots(
                price_snapshot_digest, provider, model, effective_at, record_json, created_at
            ) VALUES (?,?,?,?,?,?)""",
            (
                digest, str(clean.get("provider", "")), str(clean.get("model", "")),
                str(clean.get("effective_at", "")), record, time.time(),
            ),
        )
        self._conn.commit()
        return digest

    def get_endpoint(self, profile_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT record_json FROM model_endpoints WHERE profile_id = ?", (profile_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def get_observation(self, observation_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT record_json FROM model_observations WHERE observation_id = ?", (observation_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def query_candidates(self, task_context: TaskContext) -> list[dict[str, Any]]:
        required = tuple(dict.fromkeys(task_context.required_capability_ids))
        if not required:
            rows = self._conn.execute(
                "SELECT record_json FROM model_endpoints WHERE status = 'ACTIVE' ORDER BY provider, returned_model"
            ).fetchall()
            return [json.loads(row[0]) for row in rows]
        placeholders = ",".join("?" for _ in required)
        rows = self._conn.execute(
            f"""SELECT e.profile_id, e.record_json, COUNT(DISTINCT m.aura_capability_id) AS supported
                FROM model_endpoints e
                JOIN model_capability_edges m ON m.profile_id = e.profile_id
                WHERE e.status = 'ACTIVE'
                  AND m.status = 'VALIDATED'
                  AND m.aura_capability_id IN ({placeholders})
                GROUP BY e.profile_id, e.record_json
                HAVING supported = ?
                ORDER BY e.provider, e.returned_model""",
            (*required, len(required)),
        ).fetchall()
        return [json.loads(row[1]) for row in rows]

    def import_legacy_model_probe_ledger(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        if not source.exists():
            return {"ok": True, "imported": 0, "skipped": 0, "already_imported": False}
        raw = source.read_bytes()
        source_digest = stable_digest(raw.hex())
        previous = self._conn.execute(
            "SELECT row_count FROM legacy_model_probe_imports WHERE source_digest = ?",
            (source_digest,),
        ).fetchone()
        if previous:
            return {
                "ok": True,
                "imported": 0,
                "skipped": 0,
                "already_imported": True,
                "source_digest": source_digest,
                "previous_row_count": previous[0],
            }

        imported = 0
        skipped = 0
        for index, line in enumerate(raw.decode("utf-8", errors="replace").splitlines()):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            provider = str(row.get("provider", "")).strip()
            model = str(row.get("model", "")).strip()
            if not provider or not model:
                skipped += 1
                continue
            observed_at = _parse_timestamp(row.get("updated_at"))
            endpoint = ModelEndpointIdentity.create(
                provider=provider,
                requested_model=model,
                returned_model=model,
                access_class=ModelAccessClass.BLACK_BOX,
                fingerprint_version="legacy-probe-v1",
                provider_revision="legacy-aggregate-profile",
                first_seen_at=observed_at,
                last_seen_at=observed_at,
            )
            self.upsert_endpoint(endpoint)
            clean_row = sanitize_for_storage(row)
            observation_id = stable_id("legacy-probe", {
                "source_digest": source_digest,
                "index": index,
                "row": clean_row,
            })
            observation = ModelObservation(
                observation_id=observation_id,
                profile_id=endpoint.profile_id,
                call_id="",
                cost_status="COST_UNKNOWN",
                usage_measurement_class="UNAVAILABLE",
                field_measurement_classes={"legacy_profile": INFERRED},
                failure_class="LEGACY_AGGREGATE_PROFILE",
                measurement_class=INFERRED,
                evidence_class=BEHAVIORAL_SURROGATE,
                extra_evidence={
                    "legacy_model_probe_profile": clean_row,
                    "source_digest": source_digest,
                    "source_index": index,
                },
                created_at=observed_at,
            )
            self.record_observation(observation)
            imported += 1

        self._conn.execute(
            "INSERT INTO legacy_model_probe_imports(source_digest, source_path, row_count, imported_at) VALUES (?,?,?,?)",
            (source_digest, str(source), imported, time.time()),
        )
        self._conn.commit()
        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "already_imported": False,
            "source_digest": source_digest,
        }

    def export_bundle(self, destination: str | Path, filters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        destination_path = Path(destination).resolve()
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        profile_id = str((filters or {}).get("profile_id", ""))
        endpoint_rows = self._conn.execute(
            "SELECT record_json FROM model_endpoints" + (" WHERE profile_id = ?" if profile_id else ""),
            ((profile_id,) if profile_id else ()),
        ).fetchall()
        observation_rows = self._conn.execute(
            "SELECT record_json FROM model_observations" + (" WHERE profile_id = ?" if profile_id else ""),
            ((profile_id,) if profile_id else ()),
        ).fetchall()
        bundle = {
            "store_version": STORE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "exported_at": time.time(),
            "filters": sanitize_for_storage(dict(filters or {})),
            "model_endpoints": [json.loads(row[0]) for row in endpoint_rows],
            "model_observations": [json.loads(row[0]) for row in observation_rows],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        destination_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
        return {"ok": True, "destination": str(destination_path), "bundle_digest": stable_digest(bundle)}

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ModelCognomeStore":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
