"""Import, export, drift, experiment, and outbox operations for the Cognome store."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Mapping

from aura_dikwp_router_pipeline import DIKWPEnvelope
from aura_model_cognome import (
    BEHAVIORAL_SURROGATE, INFERRED, PATCH_AUTHORITY, SCHEMA_VERSION,
    VSA_PATCH_AUTHORITY, CapabilityPosterior, EndpointStatus, ModelAccessClass,
    ModelCapabilityEdge, ModelEndpointIdentity, ModelObservation, RouteDecision,
    TaskContext, stable_digest, stable_id,
)
from aura_model_cognome_store_schema import (
    STORE_SCHEMA_VERSION, STORE_VERSION, dataclass_from_dict, parse_timestamp,
    sanitize_for_storage,
)


class CognomeIOMixin:
    _conn: sqlite3.Connection

    def record_price_snapshot(self, snapshot: Mapping[str, Any]) -> str:
        clean = sanitize_for_storage(dict(snapshot)); digest = str(clean.get("price_snapshot_digest") or stable_digest(clean)); encoded = json.dumps(clean,sort_keys=True,separators=(",",":"))
        with self._conn:
            self._conn.execute("INSERT OR IGNORE INTO price_snapshots VALUES(?,?,?,?,?,?)", (digest,str(clean.get("provider","")),str(clean.get("model","")),str(clean.get("effective_at","")),encoded,time.time()))
        return digest

    def record_experiment_comparison(self, comparison: Mapping[str, Any]) -> str:
        clean = sanitize_for_storage(dict(comparison)); mode = str(clean.get("measurement_mode","")); approved = bool(clean.get("approved_live",False))
        if mode not in {"REPLAY","SHADOW","PAIRED_LIVE"}: raise ValueError(f"Unknown measurement mode: {mode}")
        if mode == "PAIRED_LIVE" and not approved: raise ValueError("PAIRED_LIVE requires explicit approval")
        comparison_id = str(clean.get("comparison_id") or stable_id("comparison", clean)); payload = clean | {"comparison_id": comparison_id,"approved_live": approved}; encoded = json.dumps(payload,sort_keys=True,separators=(",",":"))
        with self._conn:
            self._conn.execute("INSERT OR IGNORE INTO experiment_comparisons VALUES(?,?,?,?,?)", (comparison_id,mode,int(approved),encoded,float(clean.get("created_at",time.time()))))
        return comparison_id

    def record_drift_event(self, event: Mapping[str, Any]) -> str:
        clean = sanitize_for_storage(dict(event)); profile_id = str(clean.get("profile_id","")); self._endpoint(profile_id)
        status = str(clean.get("status","WARNING")); created = float(clean.get("created_at",time.time())); event_id = str(clean.get("drift_event_id") or stable_id("drift", clean | {"created_at": created})); payload = clean | {"drift_event_id": event_id,"created_at": created}; encoded = json.dumps(payload,sort_keys=True,separators=(",",":"))
        with self._conn:
            self._conn.execute("INSERT INTO drift_events VALUES(?,?,?,?,?,?,?,?)", (event_id,profile_id,str(clean.get("reference_fingerprint","")),str(clean.get("current_fingerprint","")),clean.get("drift_score"),status,encoded,created))
            if status in {EndpointStatus.STALE.value,EndpointStatus.QUARANTINED.value,EndpointStatus.RETIRED.value}:
                row = self._endpoint(profile_id); data = json.loads(row["record_json"]); data["status"] = status
                self._conn.execute("UPDATE model_endpoints SET status=?,record_json=?,updated_at=? WHERE profile_id=?", (status,json.dumps(data,sort_keys=True,separators=(",",":")),time.time(),profile_id))
        return event_id

    def enqueue_sync_event(self, event_type: str, record_id: str, payload: Any) -> str:
        clean = sanitize_for_storage(payload); digest = stable_digest(clean); outbox_id = stable_id("outbox", {"event_type":event_type,"record_id":record_id,"payload_digest":digest}); encoded = json.dumps(clean,sort_keys=True,separators=(",",":"))
        with self._conn:
            self._conn.execute("INSERT OR IGNORE INTO storage_sync_outbox VALUES(?,?,?,?,?,?,?,NULL)", (outbox_id,event_type,record_id,digest,encoded,"PENDING",time.time()))
        return outbox_id

    def mark_outbox_synced(self, outbox_id: str, *, synced_at: float | None = None) -> None:
        with self._conn:
            cursor = self._conn.execute("UPDATE storage_sync_outbox SET status='SYNCED',synced_at=? WHERE outbox_id=?", (time.time() if synced_at is None else float(synced_at),outbox_id))
            if cursor.rowcount != 1: raise ValueError(f"Unknown outbox event: {outbox_id}")

    def import_legacy_model_probe_ledger(self, path: str | Path) -> dict[str, Any]:
        source = Path(path)
        if not source.exists(): return {"ok":True,"imported":0,"skipped":0,"already_imported":False}
        raw = source.read_bytes(); digest = stable_digest(raw)
        old = self._conn.execute("SELECT row_count,skipped_count FROM legacy_model_probe_imports WHERE source_digest=?", (digest,)).fetchone()
        if old: return {"ok":True,"imported":0,"skipped":0,"already_imported":True,"source_digest":digest,"previous_row_count":old[0],"previous_skipped_count":old[1]}
        imported = skipped = 0
        for index,line in enumerate(raw.decode("utf-8",errors="replace").splitlines()):
            if not line.strip(): continue
            try: row = json.loads(line)
            except json.JSONDecodeError: skipped += 1; continue
            provider, model = str(row.get("provider","")), str(row.get("model",""))
            provider, model = provider.strip(), model.strip()
            if not provider or not model: skipped += 1; continue
            observed = parse_timestamp(row.get("updated_at")); endpoint = ModelEndpointIdentity.create(provider=provider,requested_model=model,returned_model=model,access_class=ModelAccessClass.BLACK_BOX,fingerprint_version="legacy-identity-v1",provider_revision="legacy-aggregate-profile",first_seen_at=observed,last_seen_at=observed); self.upsert_endpoint(endpoint)
            clean = sanitize_for_storage(row); obs = ModelObservation(observation_id=stable_id("legacy-probe",{"source_digest":digest,"index":index,"row":clean}),profile_id=endpoint.profile_id,cost_status="COST_UNKNOWN",usage_measurement_class="UNAVAILABLE",field_measurement_classes={"legacy_profile":INFERRED},failure_class="LEGACY_AGGREGATE_PROFILE",measurement_class=INFERRED,evidence_class=BEHAVIORAL_SURROGATE,extra_evidence={"legacy_model_probe_profile":clean,"source_digest":digest,"source_index":index},created_at=observed); self.record_observation(obs); imported += 1
        with self._conn: self._conn.execute("INSERT INTO legacy_model_probe_imports VALUES(?,?,?,?,?)", (digest,str(source),imported,skipped,time.time()))
        return {"ok":True,"imported":imported,"skipped":skipped,"already_imported":False,"source_digest":digest}

    def export_bundle(self, destination: str | Path, filters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        dest = Path(destination).resolve(); dest.parent.mkdir(parents=True,exist_ok=True); profile_id = str((filters or {}).get("profile_id",""))
        tables = ("model_endpoints","task_contexts","route_decisions","model_observations","model_capability_edges","capability_posteriors","dikwp_envelopes")
        records: dict[str,list[dict[str,Any]]] = {}
        for table in tables:
            where = " WHERE profile_id=?" if profile_id and "profile_id" in self._columns(table) else ""; params = (profile_id,) if where else ()
            records[table] = [json.loads(row[0]) for row in self._conn.execute(f"SELECT record_json FROM {table}{where} ORDER BY rowid", params)]
        bundle = {"store_version":STORE_VERSION,"cognome_schema_version":SCHEMA_VERSION,"store_schema_version":STORE_SCHEMA_VERSION,"exported_at":time.time(),"filters":sanitize_for_storage(dict(filters or {})),"records":records,"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":VSA_PATCH_AUTHORITY}
        dest.write_text(json.dumps(bundle,indent=2,sort_keys=True),encoding="utf-8"); return {"ok":True,"destination":str(dest),"bundle_digest":stable_digest(bundle)}

    def import_bundle(self, source: str | Path) -> dict[str, Any]:
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        if payload.get("store_version") != STORE_VERSION: raise ValueError("Unsupported Model Cognome bundle version")
        if payload.get("patch_authority") != PATCH_AUTHORITY or payload.get("vsa_patch_authority") is not False: raise ValueError("Bundle authority invariants are invalid")
        records = payload.get("records")
        if not isinstance(records,dict): raise ValueError("Bundle records must be an object")
        actions = (("model_endpoints",ModelEndpointIdentity,self.upsert_endpoint),("task_contexts",TaskContext,self.record_task_context),("route_decisions",RouteDecision,self.record_route_decision),("model_observations",ModelObservation,self.record_observation),("model_capability_edges",ModelCapabilityEdge,self.upsert_model_capability_edge),("capability_posteriors",CapabilityPosterior,self.upsert_capability_posterior),("dikwp_envelopes",DIKWPEnvelope,self.record_dikwp_envelope))
        counts = {}
        for table,cls,action in actions:
            rows = records.get(table,[])
            for row in rows: action(dataclass_from_dict(cls,row))
            counts[table] = len(rows)
        return {"ok":True,"counts":counts,"bundle_digest":stable_digest(payload)}
