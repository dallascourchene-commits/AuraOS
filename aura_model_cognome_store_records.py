"""Core record operations for the Model Cognome SQLite store."""
from __future__ import annotations

import json
import math
import sqlite3
import time
from typing import Any

from aura_dikwp_router_pipeline import DIKWPEnvelope
from aura_model_cognome import (
    CapabilityPosterior, ModelCapabilityEdge, ModelEndpointIdentity, ModelObservation,
    RouteDecision, TaskContext, canonical_json, stable_digest, validate_evidence_claim,
)
from aura_model_cognome_store_schema import context_bucket, dataclass_from_dict, record_json


class CognomeRecordMixin:
    _conn: sqlite3.Connection

    def _idempotent(self, table: str, id_col: str, record_id: str, encoded: str) -> bool:
        row = self._conn.execute(f"SELECT record_json FROM {table} WHERE {id_col}=?", (record_id,)).fetchone()
        if row is None:
            return False
        if row[0] != encoded:
            raise ValueError(f"Idempotency conflict for {table}.{record_id}")
        return True

    def _endpoint(self, profile_id: str) -> sqlite3.Row:
        row = self._conn.execute("SELECT * FROM model_endpoints WHERE profile_id=?", (profile_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown model profile: {profile_id}")
        return row

    def upsert_endpoint(self, endpoint: ModelEndpointIdentity) -> str:
        old = self._conn.execute("SELECT first_seen_at,last_seen_at FROM model_endpoints WHERE profile_id=?", (endpoint.profile_id,)).fetchone()
        first = min(float(old[0]), endpoint.first_seen_at) if old else endpoint.first_seen_at
        last = max(float(old[1]), endpoint.last_seen_at) if old else endpoint.last_seen_at
        encoded = record_json(endpoint.to_dict() | {"first_seen_at": first, "last_seen_at": last})
        with self._conn:
            self._conn.execute("""INSERT INTO model_endpoints VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
             ON CONFLICT(profile_id) DO UPDATE SET returned_model=excluded.returned_model,
             endpoint_fingerprint=excluded.endpoint_fingerprint,fingerprint_version=excluded.fingerprint_version,
             provider_revision=excluded.provider_revision,tokenizer_family=excluded.tokenizer_family,
             price_snapshot_digest=excluded.price_snapshot_digest,first_seen_at=excluded.first_seen_at,
             last_seen_at=excluded.last_seen_at,status=excluded.status,record_json=excluded.record_json,
             updated_at=excluded.updated_at""",
             (endpoint.profile_id,endpoint.provider,endpoint.requested_model,endpoint.returned_model,
              endpoint.base_url_digest,endpoint.access_class,endpoint.endpoint_fingerprint,
              endpoint.fingerprint_version,endpoint.provider_revision,endpoint.tokenizer_family,
              endpoint.price_snapshot_digest,first,last,endpoint.status,encoded,time.time()))
        return endpoint.profile_id

    def record_task_context(self, context: TaskContext) -> str:
        encoded = record_json(context)
        if self._idempotent("task_contexts","task_context_id",context.task_context_id,encoded): return context.task_context_id
        with self._conn:
            self._conn.execute("INSERT INTO task_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (context.task_context_id,context.objective_hash,context.purpose_digest,context.task_family,
               context.domain,context.context_tokens,context.capability_graph_digest,context.topology_digest,
               context.source_hash_digest,context.privacy_class,int(context.data_egress_allowed),context.verifier_id,
               encoded,time.time()))
        return context.task_context_id

    def record_route_decision(self, decision: RouteDecision) -> str:
        context = self._conn.execute("SELECT purpose_digest,capability_graph_digest FROM task_contexts WHERE task_context_id=?", (decision.task_context_id,)).fetchone()
        if context is None: raise ValueError(f"Unknown task context: {decision.task_context_id}")
        if decision.purpose_digest != context[0]: raise ValueError("RouteDecision purpose_digest does not match TaskContext")
        if decision.capability_graph_digest and context[1] and decision.capability_graph_digest != context[1]:
            raise ValueError("RouteDecision capability_graph_digest does not match TaskContext")
        for profile_id in set(decision.selected_profile_ids) | set(decision.admitted_profile_ids): self._endpoint(profile_id)
        encoded = record_json(decision)
        if self._idempotent("route_decisions","route_decision_id",decision.route_decision_id,encoded): return decision.route_decision_id
        with self._conn:
            self._conn.execute("INSERT INTO route_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
              (decision.route_decision_id,decision.task_context_id,decision.purpose_digest,decision.policy_mode,
               decision.policy_version,canonical_json(decision.selected_profile_ids),decision.capability_graph_digest,
               decision.knowledge_snapshot_digest,int(decision.proposal_only),decision.created_at,encoded))
        return decision.route_decision_id

    def record_observation(self, observation: ModelObservation) -> str:
        endpoint = self._endpoint(observation.profile_id)
        validate_evidence_claim(str(endpoint["access_class"]), observation.evidence_class)
        if observation.task_context_id and not self._conn.execute("SELECT 1 FROM task_contexts WHERE task_context_id=?", (observation.task_context_id,)).fetchone():
            raise ValueError(f"Unknown task context: {observation.task_context_id}")
        if observation.route_decision_id:
            route = self._conn.execute("SELECT task_context_id FROM route_decisions WHERE route_decision_id=?", (observation.route_decision_id,)).fetchone()
            if route is None: raise ValueError(f"Unknown route decision: {observation.route_decision_id}")
            if observation.task_context_id and observation.task_context_id != route[0]: raise ValueError("Observation task_context_id does not match RouteDecision")
        encoded = record_json(observation)
        if self._idempotent("model_observations","observation_id",observation.observation_id,encoded): return observation.observation_id
        with self._conn:
            self._conn.execute("INSERT INTO model_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (observation.observation_id,observation.route_decision_id or None,observation.task_context_id or None,
               observation.profile_id,observation.call_id,observation.policy_mode,
               None if observation.verifier_pass is None else int(observation.verifier_pass),observation.cost_usd,
               observation.cost_status,observation.end_to_end_ms,observation.time_to_verified_outcome_ms,
               observation.measurement_class,observation.evidence_class,observation.failure_class,
               observation.created_at,encoded))
        return observation.observation_id

    def upsert_model_capability_edge(self, edge: ModelCapabilityEdge) -> str:
        self._endpoint(edge.profile_id)
        if edge.status == "VALIDATED" and (edge.evidence_count <= 0 or not edge.evidence_digest or edge.last_validated_at <= 0 or not edge.capability_graph_digest):
            raise ValueError("VALIDATED model-capability edges require evidence and a capability graph digest")
        encoded = record_json(edge)
        with self._conn:
            self._conn.execute("""INSERT INTO model_capability_edges VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
             ON CONFLICT(profile_id,aura_capability_id,task_bucket) DO UPDATE SET
             edge_id=excluded.edge_id,support_level=excluded.support_level,
             verified_success_probability=excluded.verified_success_probability,
             p50_time_to_verified_ms=excluded.p50_time_to_verified_ms,
             p95_time_to_verified_ms=excluded.p95_time_to_verified_ms,mean_cost_usd=excluded.mean_cost_usd,
             tool_reliability=excluded.tool_reliability,format_reliability=excluded.format_reliability,
             evidence_count=excluded.evidence_count,evidence_digest=excluded.evidence_digest,
             capability_graph_digest=excluded.capability_graph_digest,last_validated_at=excluded.last_validated_at,
             status=excluded.status,record_json=excluded.record_json""",
             (edge.edge_id,edge.profile_id,edge.aura_capability_id,edge.task_bucket,edge.support_level,
              edge.verified_success_probability,edge.p50_time_to_verified_ms,edge.p95_time_to_verified_ms,
              edge.mean_cost_usd,edge.tool_reliability,edge.format_reliability,edge.evidence_count,
              edge.evidence_digest,edge.capability_graph_digest,edge.last_validated_at,edge.status,encoded))
        return edge.edge_id

    def upsert_capability_posterior(self, posterior: CapabilityPosterior) -> dict[str, Any]:
        self._endpoint(posterior.profile_id); encoded = record_json(posterior)
        with self._conn:
            self._conn.execute("""INSERT INTO capability_posteriors VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
             ON CONFLICT(profile_id,task_bucket,context_bucket,verifier_id,validation_split) DO UPDATE SET
             sample_count=excluded.sample_count,verified_success_alpha=excluded.verified_success_alpha,
             verified_success_beta=excluded.verified_success_beta,evidence_digest=excluded.evidence_digest,
             status=excluded.status,last_validated_at=excluded.last_validated_at,record_json=excluded.record_json""",
             (posterior.profile_id,posterior.task_bucket,posterior.context_bucket,posterior.verifier_id,
              posterior.validation_split,posterior.sample_count,posterior.verified_success_alpha,
              posterior.verified_success_beta,posterior.evidence_digest,posterior.status,
              posterior.last_validated_at,encoded))
        return posterior.to_dict()

    def update_posterior(self, observation_id: str, *, validation_split: str = "TRAIN") -> dict[str, Any]:
        row = self._conn.execute("SELECT profile_id,task_context_id,verifier_pass FROM model_observations WHERE observation_id=?", (observation_id,)).fetchone()
        if row is None: raise ValueError(f"Unknown observation: {observation_id}")
        if row[1] is None or row[2] is None: raise ValueError("Posterior updates require task context and verifier outcome")
        context = self._conn.execute("SELECT task_family,context_tokens,verifier_id FROM task_contexts WHERE task_context_id=?", (row[1],)).fetchone()
        verifier = str(context[2])
        if not verifier: raise ValueError("Posterior updates require a verifier_id")
        key = (row[0],str(context[0]),context_bucket(int(context[1])),verifier,validation_split)
        existing = self._conn.execute("SELECT record_json FROM capability_posteriors WHERE profile_id=? AND task_bucket=? AND context_bucket=? AND verifier_id=? AND validation_split=?", key).fetchone()
        posterior = dataclass_from_dict(CapabilityPosterior,json.loads(existing[0])) if existing else CapabilityPosterior(profile_id=key[0],task_bucket=key[1],context_bucket=key[2],verifier_id=key[3],validation_split=validation_split)
        updated = posterior.update_verified_outcome(bool(row[2]), evidence_digest=stable_digest({"observation_id": observation_id, "split": validation_split}))
        return self.upsert_capability_posterior(updated)

    def record_dikwp_envelope(self, envelope: DIKWPEnvelope) -> str:
        encoded = record_json(envelope.to_dict())
        if self._idempotent("dikwp_envelopes","envelope_id",envelope.envelope_id,encoded): return envelope.envelope_id
        with self._conn:
            self._conn.execute("INSERT INTO dikwp_envelopes VALUES(?,?,?,?,?,?,?,?,?)",
             (envelope.envelope_id,envelope.correlation_id,envelope.stage,envelope.payload_digest,
              envelope.purpose_digest,int(envelope.proposal_only),canonical_json(envelope.source_record_ids),
              envelope.created_at,encoded))
        return envelope.envelope_id

    def get_endpoint(self, profile_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT record_json FROM model_endpoints WHERE profile_id=?", (profile_id,)).fetchone(); return json.loads(row[0]) if row else None

    def get_observation(self, observation_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT record_json FROM model_observations WHERE observation_id=?", (observation_id,)).fetchone(); return json.loads(row[0]) if row else None

    def query_candidates(self, context: TaskContext) -> list[dict[str, Any]]:
        """Return verifier-backed, graph-pinned routing evidence for complete paths.

        Endpoint identity alone is never a routing candidate. Every returned row
        supports every required capability on the current graph and carries the
        weakest-link edge evidence plus an optional VALIDATION/SHADOW posterior.
        """
        required = tuple(dict.fromkeys(str(item) for item in context.required_capability_ids))
        if not required or not context.capability_graph_digest:
            return []
        task = str(context.task_family or context.domain or "ANY")
        bucket = context_bucket(int(context.context_tokens))
        marks = ",".join("?" for _ in required)
        profile_rows = self._conn.execute(
            f"""SELECT e.profile_id,e.record_json,COUNT(DISTINCT m.aura_capability_id) supported
            FROM model_endpoints e JOIN model_capability_edges m ON m.profile_id=e.profile_id
            WHERE e.status='ACTIVE' AND m.status='VALIDATED' AND m.evidence_count>0
              AND m.evidence_digest<>'' AND m.last_validated_at>0
              AND m.aura_capability_id IN ({marks})
              AND m.task_bucket IN (?, '*', 'ANY')
              AND m.capability_graph_digest=?
            GROUP BY e.profile_id,e.record_json HAVING supported=?
            ORDER BY e.provider,e.returned_model""",
            (*required, task, context.capability_graph_digest, len(required)),
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for profile_row in profile_rows:
            profile_id = str(profile_row[0])
            endpoint = json.loads(profile_row[1])
            edge_rows = self._conn.execute(
                f"""SELECT record_json FROM model_capability_edges
                WHERE profile_id=? AND status='VALIDATED' AND evidence_count>0
                  AND evidence_digest<>'' AND last_validated_at>0
                  AND aura_capability_id IN ({marks})
                  AND task_bucket IN (?, '*', 'ANY')
                  AND capability_graph_digest=?
                ORDER BY aura_capability_id,task_bucket""",
                (profile_id, *required, task, context.capability_graph_digest),
            ).fetchall()
            edges = [json.loads(row[0]) for row in edge_rows]
            supported = {str(edge.get("aura_capability_id", "")) for edge in edges}
            if not set(required).issubset(supported):
                continue

            posterior: dict[str, Any] | None = None
            if context.verifier_id:
                posterior_row = self._conn.execute(
                    """SELECT record_json FROM capability_posteriors
                    WHERE profile_id=? AND task_bucket IN (?, '*', 'ANY')
                      AND context_bucket=? AND verifier_id=?
                      AND validation_split IN ('SHADOW','VALIDATION')
                      AND status='VALIDATED' AND sample_count>0 AND evidence_digest<>''
                    ORDER BY CASE validation_split WHEN 'SHADOW' THEN 0 ELSE 1 END,
                             CASE task_bucket WHEN ? THEN 0 ELSE 1 END,
                             last_validated_at DESC LIMIT 1""",
                    (profile_id, task, bucket, context.verifier_id, task),
                ).fetchone()
                if posterior_row is not None:
                    posterior = json.loads(posterior_row[0])

            def complete_values(name: str) -> list[float]:
                values = [edge.get(name) for edge in edges]
                if not values or any(value is None for value in values):
                    return []
                return [float(value) for value in values]

            edge_success = complete_values("verified_success_probability")
            edge_costs = complete_values("mean_cost_usd")
            edge_times = complete_values("p50_time_to_verified_ms")
            success = min(edge_success) if edge_success else None
            cost = max(edge_costs) if edge_costs else None
            verified_time = max(edge_times) if edge_times else None
            repair = None
            scope_rate = None
            uncertainty = None
            evidence_split = "VALIDATED_EDGE"
            if posterior is not None:
                success = posterior.get("verified_success_mean", success)
                cost = posterior.get("mean_cost_usd") if posterior.get("mean_cost_usd") is not None else cost
                verified_time = (
                    posterior.get("mean_time_to_verified_ms")
                    if posterior.get("mean_time_to_verified_ms") is not None
                    else verified_time
                )
                repair = posterior.get("mean_repair_attempts")
                scope_rate = posterior.get("scope_violation_rate")
                evidence_split = str(posterior.get("validation_split") or "")
                uncertainty_values: list[float] = []
                if posterior.get("calibration_error") is not None:
                    uncertainty_values.append(float(posterior["calibration_error"]))
                alpha = float(posterior.get("verified_success_alpha") or 0.0)
                beta = float(posterior.get("verified_success_beta") or 0.0)
                denominator = alpha + beta
                if alpha > 0 and beta > 0 and denominator > 0:
                    variance = alpha * beta / (denominator * denominator * (denominator + 1.0))
                    uncertainty_values.append(math.sqrt(variance))
                uncertainty = max(uncertainty_values) if uncertainty_values else None

            edge_counts = [int(edge.get("evidence_count") or 0) for edge in edges]
            evidence_count = min(edge_counts) if edge_counts else 0
            if posterior is not None:
                evidence_count = min(evidence_count, int(posterior.get("sample_count") or 0))
            evidence_digest = stable_digest(
                {
                    "profile_id": profile_id,
                    "graph_digest": context.capability_graph_digest,
                    "required": required,
                    "edges": [
                        {
                            "edge_id": edge.get("edge_id"),
                            "capability_id": edge.get("aura_capability_id"),
                            "evidence_digest": edge.get("evidence_digest"),
                            "last_validated_at": edge.get("last_validated_at"),
                        }
                        for edge in edges
                    ],
                    "posterior": (
                        {
                            "split": posterior.get("validation_split"),
                            "evidence_digest": posterior.get("evidence_digest"),
                            "last_validated_at": posterior.get("last_validated_at"),
                        }
                        if posterior
                        else None
                    ),
                }
            )
            drift_row = self._conn.execute(
                "SELECT drift_score FROM endpoint_fingerprints WHERE profile_id=? "
                "ORDER BY observed_at DESC LIMIT 1",
                (profile_id,),
            ).fetchone()
            endpoint.update(
                {
                    "capability_ids": list(required),
                    "verified_success_probability": success,
                    "mean_cost_usd": cost,
                    "mean_time_to_verified_ms": verified_time,
                    "mean_repair_attempts": repair,
                    "scope_violation_rate": scope_rate,
                    "endpoint_drift_score": drift_row[0] if drift_row is not None else None,
                    "uncertainty": uncertainty,
                    "evidence_count": evidence_count,
                    "evidence_digest": evidence_digest,
                    "evidence_split": evidence_split,
                    "capability_graph_digest": context.capability_graph_digest,
                    "context_bucket": bucket,
                    "task_bucket": task,
                    "supported_tools": list(endpoint.get("supported_tools", [])),
                    "context_window": endpoint.get("context_window"),
                }
            )
            candidates.append(endpoint)
        return sorted(candidates, key=lambda item: (str(item.get("provider")), str(item.get("returned_model"))))
