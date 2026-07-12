"""SQLite WAL ledger for authoritative ArenaExperience V3 records."""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from typing import Any
from aura_arena_experience import ARENA_EXPERIENCE_VERSION, ArenaExperience, OutcomeVector, canonical_experience_digest, sanitize_experience_payload
ARENA_EXPERIENCE_LEDGER_VERSION="AURA_ARENA_EXPERIENCE_LEDGER_V3";PATCH_AUTHORITY="exact_source_spans_and_hashes_only";VSA_PATCH_AUTHORITY=False;_SCHEMA_VERSION=3
_SCHEMA="""
CREATE TABLE IF NOT EXISTS arena_experiences (
 experience_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, task_id TEXT, workflow_id TEXT,
 arena_id TEXT NOT NULL, arena_version TEXT NOT NULL, grammar_version TEXT NOT NULL,
 grammar_manifest_digest TEXT NOT NULL DEFAULT '', runtime_version TEXT NOT NULL, compiler_version TEXT NOT NULL,
 started_at REAL NOT NULL, completed_at REAL NOT NULL, state_before TEXT NOT NULL, state_after TEXT NOT NULL,
 selected_transition TEXT, final_outcome TEXT NOT NULL, outcome_vector_json TEXT NOT NULL DEFAULT '{}',
 admissible_alternatives_json TEXT NOT NULL DEFAULT '[]', predictions_json TEXT NOT NULL DEFAULT '[]',
 route_observation_digest TEXT NOT NULL DEFAULT '', route_capsule_observation_json TEXT NOT NULL DEFAULT '{}',
 route_capsule_observation_digest TEXT NOT NULL DEFAULT '', repository_commit_sha TEXT, working_tree_digest TEXT,
 objective_hash TEXT, source_hash_digest TEXT, provider TEXT, model TEXT, measurement_class TEXT, cost_run_id TEXT,
 trace_atom_ids_json TEXT NOT NULL, raw_evidence_refs_json TEXT NOT NULL, redactions_json TEXT NOT NULL,
 payload_json TEXT NOT NULL, experience_digest TEXT NOT NULL, schema_version TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_experience_arena_state ON arena_experiences(arena_id,state_before,selected_transition);
CREATE INDEX IF NOT EXISTS idx_experience_task ON arena_experiences(task_id);
CREATE INDEX IF NOT EXISTS idx_experience_correlation ON arena_experiences(correlation_id);
CREATE INDEX IF NOT EXISTS idx_experience_commit ON arena_experiences(repository_commit_sha);
CREATE INDEX IF NOT EXISTS idx_experience_outcome ON arena_experiences(final_outcome);
CREATE TABLE IF NOT EXISTS arena_experience_migrations(version INTEGER PRIMARY KEY,applied_at REAL NOT NULL);
"""
class ArenaExperienceLedger:
    def __init__(self,repo_root:str|Path=".",*,db_path:str|Path|None=None):
        root=Path(repo_root).resolve();self.db_path=Path(db_path).resolve() if db_path else root/"Aura_Memory"/"arena_experience.db";self.db_path.parent.mkdir(parents=True,exist_ok=True);self._conn=sqlite3.connect(str(self.db_path),timeout=10.);self._conn.row_factory=sqlite3.Row;self._conn.execute("PRAGMA journal_mode=WAL");self._conn.execute("PRAGMA synchronous=NORMAL");self._conn.execute("PRAGMA foreign_keys=ON");self._conn.executescript(_SCHEMA);self._migrate();self._conn.commit()
    def _migrate(self):
        columns={str(r[1]) for r in self._conn.execute("PRAGMA table_info(arena_experiences)")};additions={"grammar_manifest_digest":"TEXT NOT NULL DEFAULT ''","outcome_vector_json":"TEXT NOT NULL DEFAULT '{}'","admissible_alternatives_json":"TEXT NOT NULL DEFAULT '[]'","predictions_json":"TEXT NOT NULL DEFAULT '[]'","route_observation_digest":"TEXT NOT NULL DEFAULT ''","route_capsule_observation_json":"TEXT NOT NULL DEFAULT '{}'","route_capsule_observation_digest":"TEXT NOT NULL DEFAULT ''"}
        for name,decl in additions.items():
            if name not in columns:self._conn.execute(f"ALTER TABLE arena_experiences ADD COLUMN {name} {decl}")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_experience_grammar_digest ON arena_experiences(arena_id,grammar_version,grammar_manifest_digest)");self._conn.execute("CREATE INDEX IF NOT EXISTS idx_experience_capsule_digest ON arena_experiences(route_capsule_observation_digest)");self._conn.execute("INSERT OR IGNORE INTO arena_experience_migrations(version,applied_at) VALUES (?,?)",(_SCHEMA_VERSION,time.time()))
    def record(self,experience:ArenaExperience|dict[str,Any]):
        raw=experience.to_dict() if isinstance(experience,ArenaExperience) else dict(experience);raw["payload"],r0=sanitize_experience_payload(raw.get("payload") or {});raw["admissible_alternatives"],r1=sanitize_experience_payload(raw.get("admissible_alternatives") or []);raw["predictions"],r2=sanitize_experience_payload(raw.get("predictions") or []);raw["route_capsule_observation"],r3=sanitize_experience_payload(raw.get("route_capsule_observation") or {});raw["redactions"]=sorted(set([str(x) for x in raw.get("redactions",[])]+r0+r1+r2+r3));raw.setdefault("version",ARENA_EXPERIENCE_VERSION)
        required=("experience_id","correlation_id","arena_id","arena_version","grammar_version","grammar_manifest_digest","runtime_version","compiler_version","state_before","state_after","final_outcome","outcome_vector");missing=[k for k in required if not _present(raw.get(k))]
        if missing:return _deny("missing_required_fields",missing=missing)
        try:raw["outcome_vector"]=OutcomeVector.from_dict(raw["outcome_vector"]).to_dict()
        except (TypeError,ValueError) as exc:return _deny(f"invalid_outcome_vector:{type(exc).__name__}")
        if not isinstance(raw["admissible_alternatives"],list) or not all(isinstance(x,dict) for x in raw["admissible_alternatives"]):return _deny("invalid_admissible_alternatives")
        if not isinstance(raw["predictions"],list) or not all(isinstance(x,dict) for x in raw["predictions"]):return _deny("invalid_predictions")
        if not isinstance(raw["route_capsule_observation"],dict):return _deny("invalid_route_capsule_observation")
        try:started=float(raw.get("started_at"));completed=float(raw.get("completed_at"))
        except (TypeError,ValueError):return _deny("invalid_timestamps")
        if completed<started:return _deny("completed_before_started")
        digest=canonical_experience_digest(raw);eid=str(raw["experience_id"]);prior=self._conn.execute("SELECT experience_digest FROM arena_experiences WHERE experience_id=?",(eid,)).fetchone()
        if prior:return {"ok":True,"experience_id":eid,"experience_digest":digest,"idempotent_replay":True,"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False} if prior["experience_digest"]==digest else _deny("experience_id_digest_conflict",experience_id=eid)
        values=(eid,str(raw.get("correlation_id") or ""),str(raw.get("task_id") or ""),str(raw.get("workflow_id") or ""),str(raw.get("arena_id") or ""),str(raw.get("arena_version") or ""),str(raw.get("grammar_version") or ""),str(raw.get("grammar_manifest_digest") or ""),str(raw.get("runtime_version") or ""),str(raw.get("compiler_version") or ""),started,completed,str(raw.get("state_before") or ""),str(raw.get("state_after") or ""),str(raw.get("selected_transition") or ""),str(raw.get("final_outcome") or ""),_j(raw.get("outcome_vector") or {}),_j(raw.get("admissible_alternatives") or []),_j(raw.get("predictions") or []),str(raw.get("route_observation_digest") or ""),_j(raw.get("route_capsule_observation") or {}),str(raw.get("route_capsule_observation_digest") or ""),str(raw.get("repository_commit_sha") or ""),str(raw.get("working_tree_digest") or ""),str(raw.get("objective_hash") or ""),str(raw.get("source_hash_digest") or ""),str(raw.get("provider") or ""),str(raw.get("model") or ""),str(raw.get("measurement_class") or "UNAVAILABLE"),str(raw.get("cost_run_id") or ""),_j(raw.get("trace_atom_ids") or []),_j(raw.get("raw_evidence_refs") or []),_j(raw.get("redactions") or []),_j(raw.get("payload") or {}),digest,str(raw.get("version") or ARENA_EXPERIENCE_VERSION),time.time())
        try:self._conn.execute("""INSERT INTO arena_experiences(experience_id,correlation_id,task_id,workflow_id,arena_id,arena_version,grammar_version,grammar_manifest_digest,runtime_version,compiler_version,started_at,completed_at,state_before,state_after,selected_transition,final_outcome,outcome_vector_json,admissible_alternatives_json,predictions_json,route_observation_digest,route_capsule_observation_json,route_capsule_observation_digest,repository_commit_sha,working_tree_digest,objective_hash,source_hash_digest,provider,model,measurement_class,cost_run_id,trace_atom_ids_json,raw_evidence_refs_json,redactions_json,payload_json,experience_digest,schema_version,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",values);self._conn.commit()
        except sqlite3.DatabaseError as exc:self._conn.rollback();return _deny(f"database_write_failed:{type(exc).__name__}")
        return {"ok":True,"experience_id":eid,"experience_digest":digest,"idempotent_replay":False,"redactions":raw["redactions"],"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
    def get(self,experience_id):
        row=self._conn.execute("SELECT * FROM arena_experiences WHERE experience_id=?",(str(experience_id),)).fetchone();return _decode(row) if row else None
    def history(self,*,arena_id="",task_id="",grammar_manifest_digest="",limit=50):
        clauses=[];params=[]
        for column,value in (("arena_id",arena_id),("task_id",task_id),("grammar_manifest_digest",grammar_manifest_digest)):
            if value:clauses.append(f"{column}=?");params.append(value)
        params.append(max(1,min(int(limit),10000)));where=f"WHERE {' AND '.join(clauses)}" if clauses else "";return [_decode(r) for r in self._conn.execute(f"SELECT * FROM arena_experiences {where} ORDER BY completed_at DESC LIMIT ?",params).fetchall()]
    def export_jsonl(self,path,*,arena_id="",limit=10000):
        rows=self.history(arena_id=arena_id,limit=limit);out=Path(path);out.parent.mkdir(parents=True,exist_ok=True);out.write_text("".join(json.dumps(r,sort_keys=True,ensure_ascii=True,default=str)+"\n" for r in reversed(rows)),encoding="utf-8");return {"ok":True,"path":str(out),"record_count":len(rows),"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
    def status(self):
        count=int(self._conn.execute("SELECT COUNT(*) FROM arena_experiences").fetchone()[0]);complete=int(self._conn.execute("SELECT COUNT(*) FROM arena_experiences WHERE grammar_manifest_digest!='' AND outcome_vector_json!='{}'").fetchone()[0]);capsule=int(self._conn.execute("SELECT COUNT(*) FROM arena_experiences WHERE route_capsule_observation_digest!=''").fetchone()[0]);return {"ok":True,"version":ARENA_EXPERIENCE_LEDGER_VERSION,"schema_version":_SCHEMA_VERSION,"db_path":str(self.db_path),"journal_mode":str(self._conn.execute("PRAGMA journal_mode").fetchone()[0]).lower(),"record_count":count,"v3_complete_record_count":complete,"capsule_observation_count":capsule,"legacy_record_count":count-complete,"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
    def close(self):self._conn.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
def _decode(row):
    data=dict(row);defaults={"trace_atom_ids_json":[],"raw_evidence_refs_json":[],"redactions_json":[],"payload_json":{},"outcome_vector_json":{},"admissible_alternatives_json":[],"predictions_json":[],"route_capsule_observation_json":{}}
    for key,default in defaults.items():
        value=data.pop(key,"");out=key.removesuffix("_json")
        try:data[out]=json.loads(value) if value else default
        except json.JSONDecodeError:data[out]=default
    data["version"]=data.pop("schema_version",ARENA_EXPERIENCE_VERSION);data["legacy_record"]=not bool(data.get("grammar_manifest_digest") and data.get("outcome_vector"));data.update(patch_authority=PATCH_AUTHORITY,vsa_patch_authority=False,learned_weight_patch_authority=False,crystallization_patch_authority=False);return data
def _j(value):return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str)
def _present(value):return bool(value) if isinstance(value,dict) else bool(str(value or "").strip())
def _deny(reason,*,missing=None,experience_id=""):return {"ok":False,"reason":reason,"missing":list(missing or []),"experience_id":experience_id,"fail_closed":True,"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
