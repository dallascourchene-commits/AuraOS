"""Schema and storage helpers for the local Model Cognome store."""
from __future__ import annotations

from dataclasses import fields as dc_fields, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping

from aura_model_cognome import canonical_json

STORE_VERSION = "AURA_MODEL_COGNOME_STORE_V1"
STORE_SCHEMA_VERSION = 2
DEFAULT_DB_NAME = "model_cognome.db"
_SECRET_KEY = re.compile(r"(?:api[_-]?key|x[_-]?api[_-]?key|secret|password|authorization|credential|access[_-]?token|refresh[_-]?token|private[_-]?key|cookie|session[_-]?key)", re.I)
_REASONING_KEY = re.compile(r"(?:chain[_-]?of[_-]?thought|private[_-]?reasoning|reasoning[_-]?trace|hidden[_-]?thoughts|raw[_-]?prompt|full[_-]?prompt|internal[_-]?scratchpad)", re.I)
_SECRET_VALUES = (
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.I),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS model_endpoints(
 profile_id TEXT PRIMARY KEY, provider TEXT NOT NULL, requested_model TEXT NOT NULL,
 returned_model TEXT NOT NULL, base_url_digest TEXT NOT NULL, access_class TEXT NOT NULL,
 endpoint_fingerprint TEXT NOT NULL, fingerprint_version TEXT NOT NULL,
 provider_revision TEXT NOT NULL, tokenizer_family TEXT NOT NULL,
 price_snapshot_digest TEXT NOT NULL, first_seen_at REAL NOT NULL, last_seen_at REAL NOT NULL,
 status TEXT NOT NULL, record_json TEXT NOT NULL, updated_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_endpoint_status ON model_endpoints(status);
CREATE INDEX IF NOT EXISTS idx_endpoint_fingerprint ON model_endpoints(endpoint_fingerprint);
CREATE TABLE IF NOT EXISTS endpoint_fingerprints(
 fingerprint_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
 endpoint_fingerprint TEXT NOT NULL, fingerprint_version TEXT NOT NULL, observed_at REAL NOT NULL,
 drift_score REAL, status TEXT NOT NULL, record_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS probe_suites(
 probe_suite_id TEXT PRIMARY KEY, suite_digest TEXT NOT NULL, access_class TEXT NOT NULL,
 created_at REAL NOT NULL, record_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS task_contexts(
 task_context_id TEXT PRIMARY KEY, objective_hash TEXT NOT NULL, purpose_digest TEXT NOT NULL,
 task_family TEXT NOT NULL, domain TEXT NOT NULL, context_tokens INTEGER NOT NULL,
 capability_graph_digest TEXT NOT NULL, topology_digest TEXT NOT NULL, source_hash_digest TEXT NOT NULL,
 privacy_class TEXT NOT NULL, data_egress_allowed INTEGER NOT NULL, verifier_id TEXT NOT NULL DEFAULT '',
 record_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS route_decisions(
 route_decision_id TEXT PRIMARY KEY, task_context_id TEXT NOT NULL REFERENCES task_contexts(task_context_id),
 purpose_digest TEXT NOT NULL, policy_mode TEXT NOT NULL, policy_version TEXT NOT NULL,
 selected_profile_ids TEXT NOT NULL, capability_graph_digest TEXT NOT NULL,
 knowledge_snapshot_digest TEXT NOT NULL, proposal_only INTEGER NOT NULL,
 created_at REAL NOT NULL, record_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_observations(
 observation_id TEXT PRIMARY KEY, route_decision_id TEXT REFERENCES route_decisions(route_decision_id),
 task_context_id TEXT REFERENCES task_contexts(task_context_id),
 profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id), call_id TEXT NOT NULL,
 policy_mode TEXT NOT NULL, verifier_pass INTEGER, cost_usd REAL, cost_status TEXT NOT NULL,
 end_to_end_ms REAL, time_to_verified_outcome_ms REAL, measurement_class TEXT NOT NULL,
 evidence_class TEXT NOT NULL, failure_class TEXT NOT NULL, created_at REAL NOT NULL,
 record_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_observation_profile ON model_observations(profile_id);
CREATE INDEX IF NOT EXISTS idx_observation_call ON model_observations(call_id);
CREATE TABLE IF NOT EXISTS model_capability_edges(
 edge_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
 aura_capability_id TEXT NOT NULL, task_bucket TEXT NOT NULL, support_level TEXT NOT NULL,
 verified_success_probability REAL, p50_time_to_verified_ms REAL, p95_time_to_verified_ms REAL,
 mean_cost_usd REAL, tool_reliability REAL, format_reliability REAL, evidence_count INTEGER NOT NULL,
 evidence_digest TEXT NOT NULL, capability_graph_digest TEXT NOT NULL DEFAULT '',
 last_validated_at REAL NOT NULL, status TEXT NOT NULL, record_json TEXT NOT NULL,
 UNIQUE(profile_id,aura_capability_id,task_bucket));
CREATE INDEX IF NOT EXISTS idx_edge_lookup ON model_capability_edges(aura_capability_id,task_bucket,status);
CREATE TABLE IF NOT EXISTS capability_posteriors(
 profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id), task_bucket TEXT NOT NULL,
 context_bucket TEXT NOT NULL, verifier_id TEXT NOT NULL, validation_split TEXT NOT NULL,
 sample_count INTEGER NOT NULL, verified_success_alpha REAL NOT NULL,
 verified_success_beta REAL NOT NULL, evidence_digest TEXT NOT NULL, status TEXT NOT NULL,
 last_validated_at REAL NOT NULL, record_json TEXT NOT NULL,
 PRIMARY KEY(profile_id,task_bucket,context_bucket,verifier_id,validation_split));
CREATE TABLE IF NOT EXISTS latency_distributions(
 distribution_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
 task_bucket TEXT NOT NULL, context_bucket TEXT NOT NULL, sample_count INTEGER NOT NULL,
 p50_ms REAL, p95_ms REAL, p99_ms REAL, cold_warm_cache_class TEXT NOT NULL,
 record_json TEXT NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS price_snapshots(
 price_snapshot_digest TEXT PRIMARY KEY, provider TEXT NOT NULL, model TEXT NOT NULL,
 effective_at TEXT NOT NULL, record_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS experiment_comparisons(
 comparison_id TEXT PRIMARY KEY, measurement_mode TEXT NOT NULL, approved_live INTEGER NOT NULL,
 record_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS drift_events(
 drift_event_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES model_endpoints(profile_id),
 reference_fingerprint TEXT NOT NULL, current_fingerprint TEXT NOT NULL, drift_score REAL,
 status TEXT NOT NULL, record_json TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS dikwp_envelopes(
 envelope_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, stage TEXT NOT NULL,
 payload_digest TEXT NOT NULL, purpose_digest TEXT NOT NULL, proposal_only INTEGER NOT NULL,
 source_record_ids TEXT NOT NULL, created_at REAL NOT NULL, record_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS storage_sync_outbox(
 outbox_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, record_id TEXT NOT NULL,
 payload_digest TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL,
 created_at REAL NOT NULL, synced_at REAL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_idempotency
 ON storage_sync_outbox(event_type,record_id,payload_digest);
CREATE TABLE IF NOT EXISTS legacy_model_probe_imports(
 source_digest TEXT PRIMARY KEY, source_path TEXT NOT NULL, row_count INTEGER NOT NULL,
 skipped_count INTEGER NOT NULL DEFAULT 0, imported_at REAL NOT NULL);
"""


def db_path(repo_root: str | Path = ".", explicit: str | Path | None = None) -> Path:
    path = Path(explicit).resolve() if explicit is not None else Path(repo_root).resolve() / "Aura_Memory" / DEFAULT_DB_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_for_storage(value: Any) -> Any:
    if is_dataclass(value):
        value = value.to_dict() if hasattr(value, "to_dict") else value.__dict__
    if isinstance(value, Mapping):
        return {str(k): "[REDACTED]" if _SECRET_KEY.search(str(k)) or _REASONING_KEY.search(str(k)) else sanitize_for_storage(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [sanitize_for_storage(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((sanitize_for_storage(item) for item in value), key=canonical_json)
    if isinstance(value, str):
        for pattern in _SECRET_VALUES:
            value = pattern.sub("[REDACTED]", value)
    return value


def record_json(value: Any) -> str:
    return canonical_json(sanitize_for_storage(value))


def parse_timestamp(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
        except ValueError:
            pass
    return time.time()


def dataclass_from_dict(cls: type[Any], data: Mapping[str, Any]) -> Any:
    allowed = {item.name for item in dc_fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in allowed}
    tuple_fields = {"selected_profile_ids","admitted_profile_ids","required_capabilities","required_tools","required_capability_ids","capability_path","capability_truth_boundaries","capability_risks","capability_tests","capability_token_savings_roles","source_record_ids"}
    for name in tuple_fields:
        if isinstance(kwargs.get(name), list):
            kwargs[name] = tuple(kwargs[name])
    return cls(**kwargs)


def context_bucket(tokens: int) -> str:
    return "small" if tokens <= 8_000 else "medium" if tokens <= 64_000 else "large"
