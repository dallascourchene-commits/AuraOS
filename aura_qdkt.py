"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MIIGWECH (Extension-Based Storage)
DEPENDENCIES: json, __future__, aura_token_economics, contextlib, sqlite3, typing, time, pathlib, aura_hv_cache, hashlib
FUNCTIONS: _get_hv_substrate, _get_token_economics, _concept_key, _hv_bytes, _db, _observation_fingerprint, _source_fingerprint, _crystal_fast_path_eligible, get_qdkt, commit_to_dkt_shim, log_dkt_commit_shim, __init__, _init_schemas, _load_crystal_cache, _load_pattern_accumulator, _save_crystal_cache, _save_pattern_accumulator, observe, observe_retrieval_usefulness, query, crystallization_candidate, crystallize, fast_path, learning_summary, _route_to_holographic, _route_to_cognitive_evolution, _route_to_causal_ledger, _route_to_changelog, _route_to_token_economics, _write_knowledge_index, _write_workspace_event, _write_retrieval_usefulness, _check_crystallization
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_MEMPALACE_DB   = Path.home() / ".mempalace" / "aura_memory.db"
_WORKSPACE_DB   = Path("Aura_Memory/qdkt_index.db")
_CRYSTAL_JSON   = Path("Aura_Memory/qdkt_crystal_cache.json")
_ACCUMULATOR_JSON = Path("Aura_Memory/qdkt_pattern_accumulator.json")

_CRYSTAL_CONFIRM_THRESHOLD = 3
_CRYSTAL_CONFIDENCE_THRESHOLD = 0.75

# Lock-free — pure asyncio single-threaded execution.
# Accepted crystals are deliberately separate from pre-crystallization state.
_CRYSTAL_CACHE: dict[str, dict] = {}
_PATTERN_ACCUMULATOR: dict[str, dict] = {}


def _get_hv_substrate():
    try:
        from aura_hv_cache import HVCacheSubstrate
        return HVCacheSubstrate()
    except Exception:
        return None


def _get_token_economics():
    try:
        from aura_token_economics import TokenEconomics
        return TokenEconomics()
    except Exception:
        return None


def _concept_key(text: str) -> str:
    return hashlib.sha256(text.lower().strip().encode("utf-8")).hexdigest()[:24]


def _hv_bytes(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()


def _observation_fingerprint(concept: str, payload: dict[str, Any]) -> str:
    """Stable fingerprint used to distinguish duplicate replay from new evidence."""
    try:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        normalized = repr(sorted(payload.items(), key=lambda item: str(item[0])))
    return hashlib.sha256(f"{concept}\0{normalized}".encode("utf-8")).hexdigest()[:32]


def _source_fingerprint(concept: str, payload: dict[str, Any]) -> str:
    """Prefer an explicit source identity; otherwise conservatively fingerprint payload."""
    for field in ("source_id", "source_ref", "evidence_ref", "source_uri", "source"):
        value = payload.get(field)
        if value not in (None, ""):
            return hashlib.sha256(f"{field}:{value}".encode("utf-8")).hexdigest()[:32]
    if payload.get("file_path") or payload.get("commit_hash"):
        value = f"{payload.get('file_path', '')}@{payload.get('commit_hash', '')}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return _observation_fingerprint(concept, payload)


def _crystal_fast_path_eligible(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    if entry.get("status", "accepted") != "accepted":
        return False
    if entry.get("revalidation_required"):
        return False
    if str(entry.get("freshness_state", "CURRENT")).upper() in {
        "STALE", "REVALIDATE", "REJECTED", "BLOCKED"
    }:
        return False
    # Recurrence-generated legacy entries must never regain authority-like fast path.
    if str(entry.get("source", "")).lower() in {
        "auto_threshold", "repetition", "recurrence"
    }:
        return False
    return True


_SCHEMA_MEMPALACE = """
CREATE TABLE IF NOT EXISTS qdkt_knowledge_index (
    event_id        TEXT PRIMARY KEY,
    event_type      TEXT NOT NULL,
    concept_tags    TEXT,
    rationale       TEXT,
    hv_hash         BLOB,
    confidence      REAL DEFAULT 0.5,
    subsystem_refs  TEXT,
    ts              REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS qdkt_crystal_cache (
    concept_key         TEXT PRIMARY KEY,
    pattern_summary     TEXT,
    recommended_action  TEXT,
    confidence          REAL DEFAULT 0.5,
    observation_count   INTEGER DEFAULT 0,
    first_seen          REAL,
    last_confirmed      REAL,
    hv_blob             BLOB
);
CREATE TABLE IF NOT EXISTS qdkt_retrieval_usefulness (
    event_id            TEXT PRIMARY KEY,
    query               TEXT,
    target_type         TEXT,
    candidate_id        TEXT,
    candidate_type      TEXT,
    source              TEXT,
    usefulness_score    REAL,
    semantic_score      REAL,
    verifier_result     TEXT,
    phase_hash          TEXT,
    failure_reason      TEXT,
    ts                  REAL
);
"""

_SCHEMA_WORKSPACE = """
CREATE TABLE IF NOT EXISTS qdkt_events (
    event_id    TEXT PRIMARY KEY,
    event_type  TEXT,
    concept     TEXT,
    rationale   TEXT,
    confidence  REAL,
    ts          REAL
);
CREATE TABLE IF NOT EXISTS qdkt_crystals (
    concept_key     TEXT PRIMARY KEY,
    action          TEXT,
    confidence      REAL,
    count           INTEGER,
    last_confirmed  REAL
);
CREATE TABLE IF NOT EXISTS qdkt_retrieval_usefulness (
    event_id            TEXT PRIMARY KEY,
    query               TEXT,
    target_type         TEXT,
    candidate_id        TEXT,
    candidate_type      TEXT,
    source              TEXT,
    usefulness_score    REAL,
    semantic_score      REAL,
    verifier_result     TEXT,
    phase_hash          TEXT,
    failure_reason      TEXT,
    ts                  REAL
);
"""


@contextmanager
def _db(path: Path, timeout: float = 10.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class UnifiedQDKT:
    """Central knowledge tracing hub — pure-asyncio, lock-free."""

    def __init__(self) -> None:
        self._init_schemas()
        self._load_pattern_accumulator()
        self._load_crystal_cache()

    def _init_schemas(self) -> None:
        try:
            with _db(_MEMPALACE_DB) as conn:
                conn.executescript(_SCHEMA_MEMPALACE)
        except Exception as exc:
            print(f"[QDKT] MemPalace schema init warning: {exc}")
        try:
            with _db(_WORKSPACE_DB) as conn:
                conn.executescript(_SCHEMA_WORKSPACE)
        except Exception as exc:
            print(f"[QDKT] Workspace schema init warning: {exc}")

    def _load_pattern_accumulator(self) -> None:
        _PATTERN_ACCUMULATOR.clear()
        if not _ACCUMULATOR_JSON.exists():
            return
        try:
            with open(_ACCUMULATOR_JSON, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key, entry in data.items():
                    if isinstance(entry, dict):
                        _PATTERN_ACCUMULATOR[str(key)] = entry
        except Exception:
            # Accumulator corruption must not create a crystal or fast path.
            pass

    def _load_crystal_cache(self) -> None:
        """Load accepted crystals and fail-closed migrate conflated legacy state."""
        _CRYSTAL_CACHE.clear()
        raw_json: dict[str, dict] = {}
        if _CRYSTAL_JSON.exists():
            try:
                with open(_CRYSTAL_JSON, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    raw_json = {
                        str(key): value for key, value in data.items()
                        if isinstance(value, dict)
                    }
            except Exception:
                raw_json = {}

        migration_changed = False
        seen_legacy: set[str] = set()
        for key, entry in raw_json.items():
            source = str(entry.get("source", "")).lower()
            # Explicit/reviewed crystals have provenance that accumulation entries lack.
            if source and source not in {"auto_threshold", "repetition", "recurrence"}:
                normalized = dict(entry)
                normalized.setdefault("status", "accepted")
                normalized.setdefault("freshness_state", "CURRENT")
                normalized.setdefault("revalidation_required", False)
                _CRYSTAL_CACHE[key] = normalized
                continue

            migrated = dict(entry)
            migrated.update({
                "state": "candidate",
                "migration_reason": (
                    "legacy_auto_threshold_requires_revalidation"
                    if source == "auto_threshold"
                    else "legacy_conflated_cache_unverified"
                ),
                "migrated_from": "qdkt_crystal_cache.json",
                "fast_path_eligible": False,
            })
            _PATTERN_ACCUMULATOR[key] = {
                **_PATTERN_ACCUMULATOR.get(key, {}),
                **migrated,
            }
            seen_legacy.add(key)
            migration_changed = True

        # Historical DB rows do not encode source/reviewer provenance. If there is no
        # accepted JSON record proving promotion, retain them as candidates, not truth.
        legacy_rows: dict[str, dict] = {}
        try:
            with _db(_WORKSPACE_DB) as conn:
                rows = conn.execute(
                    "SELECT concept_key, action, confidence, count, last_confirmed "
                    "FROM qdkt_crystals"
                ).fetchall()
            for key, action, conf, count, ts in rows:
                legacy_rows[str(key)] = {
                    "action": action or "", "confidence": conf,
                    "count": count, "last_confirmed": ts,
                    "migrated_from": "qdkt_crystals",
                }
        except Exception:
            pass
        try:
            with _db(_MEMPALACE_DB) as conn:
                rows = conn.execute(
                    "SELECT concept_key, recommended_action, confidence, "
                    "observation_count, first_seen, last_confirmed "
                    "FROM qdkt_crystal_cache"
                ).fetchall()
            for key, action, conf, count, first_seen, ts in rows:
                candidate = legacy_rows.setdefault(str(key), {})
                candidate.update({
                    "action": candidate.get("action") or action or "",
                    "confidence": max(float(candidate.get("confidence") or 0.0), float(conf or 0.0)),
                    "count": max(int(candidate.get("count") or 0), int(count or 0)),
                    "first_seen": first_seen,
                    "last_confirmed": max(float(candidate.get("last_confirmed") or 0.0), float(ts or 0.0)),
                    "migrated_from": "qdkt_crystals+qdkt_crystal_cache",
                })
        except Exception:
            pass

        for key, row in legacy_rows.items():
            if key in _CRYSTAL_CACHE:
                continue
            if key in seen_legacy:
                # Preserve richer JSON migration metadata while filling missing fields.
                target = _PATTERN_ACCUMULATOR[key]
                for field, value in row.items():
                    target.setdefault(field, value)
                continue
            target = _PATTERN_ACCUMULATOR.setdefault(key, {})
            target.update({
                **row,
                "state": "candidate",
                "migration_reason": "legacy_db_crystal_unverified",
                "fast_path_eligible": False,
            })
            migration_changed = True

        if migration_changed:
            self._save_pattern_accumulator()
            # Sanitize the fast-path file in place while preserving all demoted data in
            # the separate accumulator JSON. DB rows remain untouched as historical data.
            self._save_crystal_cache()

    def _save_crystal_cache(self) -> None:
        try:
            _CRYSTAL_JSON.parent.mkdir(parents=True, exist_ok=True)
            snapshot = dict(_CRYSTAL_CACHE)
            with open(_CRYSTAL_JSON, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception:
            pass

    def _save_pattern_accumulator(self) -> None:
        try:
            _ACCUMULATOR_JSON.parent.mkdir(parents=True, exist_ok=True)
            snapshot = dict(_PATTERN_ACCUMULATOR)
            with open(_ACCUMULATOR_JSON, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception:
            pass

    def observe(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        rationale: str = "",
        concept: str = "",
        confidence: float = 0.5,
        subsystem: str = "unknown",
        node_ref: Any = None,
    ) -> str:
        event_id = (
            "QDKT-" +
            hashlib.sha256(
                f"{event_type}:{concept}:{time.time()}".encode()
            ).hexdigest()[:16]
        )
        ts = time.time()
        concept_str = concept or event_type
        hv_hash = _hv_bytes(concept_str + rationale)
        refs: dict[str, str] = {}

        if node_ref is not None:
            refs["holographic"] = self._route_to_holographic(
                node_ref, event_id, concept_str, payload, ts
            )
        if event_type in ("code_change", "heal_commit", "architecture_decision"):
            refs["cognitive"] = self._route_to_cognitive_evolution(
                event_id, payload.get("file_path", concept_str), rationale
            )
        if event_type in ("causal_update", "benchmark_result", "cloud_inference",
                          "provider_failover"):
            refs["causal"] = self._route_to_causal_ledger(
                concept_str,
                payload.get("hypothesis", event_type),
                success=payload.get("success", True),
                error=payload.get("error", 0.0),
            )
        if event_type == "code_change":
            refs["changelog"] = self._route_to_changelog(payload, rationale)
        if event_type in ("token_economics", "cloud_inference"):
            refs["economics"] = self._route_to_token_economics(payload)

        self._write_knowledge_index(
            event_id, event_type, concept_str, rationale,
            hv_hash, confidence, refs, ts
        )
        self._write_workspace_event(event_id, event_type, concept_str, rationale,
                                    confidence, ts)
        self._check_crystallization(concept_str, confidence, payload, event_id=event_id)

        return event_id

    def observe_retrieval_usefulness(self, score_row: dict[str, Any]) -> str:
        """Record DREAM-lite retrieval usefulness as first-class QDKT feedback."""
        query = str(score_row.get("query") or "")
        candidate_id = str(score_row.get("candidate_id") or "")
        target_type = str(score_row.get("target_type") or "")
        phase_hash = str(score_row.get("phase_hash") or "")
        ts = float(score_row.get("ts") or time.time())
        event_id = str(
            score_row.get("event_id")
            or "QDKT-DREAM-"
            + hashlib.sha256(f"{query}:{candidate_id}:{target_type}:{phase_hash}:{ts}".encode()).hexdigest()[:16]
        )
        usefulness = float(score_row.get("usefulness_score") or 0.0)
        semantic = float(score_row.get("semantic_score") or 0.0)
        row = {
            "event_id": event_id,
            "query": query[:512],
            "target_type": target_type[:128],
            "candidate_id": candidate_id[:256],
            "candidate_type": str(score_row.get("candidate_type") or "")[:128],
            "source": str(score_row.get("source") or "")[:128],
            "usefulness_score": usefulness,
            "semantic_score": semantic,
            "verifier_result": json.dumps(score_row.get("verifier_result"), sort_keys=True, default=str)[:1024],
            "phase_hash": phase_hash[:128],
            "failure_reason": str(score_row.get("failure_reason") or "")[:512],
            "ts": ts,
        }
        self._write_retrieval_usefulness(row)
        refs = {"retrieval_usefulness": f"dream:{event_id}"}
        self._write_knowledge_index(
            event_id,
            "retrieval_usefulness",
            f"{target_type}:{candidate_id}",
            str(score_row.get("rationale") or "DREAM-lite downstream usefulness feedback"),
            _hv_bytes(query + candidate_id + target_type),
            usefulness,
            refs,
            ts,
        )
        self._write_workspace_event(
            event_id,
            "retrieval_usefulness",
            f"{target_type}:{candidate_id}",
            str(score_row.get("rationale") or ""),
            usefulness,
            ts,
        )
        return event_id

    def query(
        self,
        concept: str,
        *,
        top_k: int = 5,
        include_binary: bool = False,
    ) -> dict[str, Any]:
        results: dict[str, Any] = {
            "concept": concept,
            "fast_path": None,
            "crystallization_candidate": None,
            "crystal_state": None,
            "knowledge_index": [],
            "cognitive": [],
            "causal": None,
            "changelog": [],
        }
        key = _concept_key(concept)
        candidate = _PATTERN_ACCUMULATOR.get(key)
        if candidate:
            results["crystallization_candidate"] = dict(candidate)
        crystal = _CRYSTAL_CACHE.get(key)
        if _crystal_fast_path_eligible(crystal):
            results["fast_path"] = dict(crystal)
            return results
        if crystal:
            results["crystal_state"] = {
                "status": crystal.get("status", "accepted"),
                "freshness_state": crystal.get("freshness_state", "CURRENT"),
                "revalidation_required": bool(crystal.get("revalidation_required")),
                "revalidation_reason": crystal.get("revalidation_reason"),
            }
        try:
            with _db(_MEMPALACE_DB) as conn:
                rows = conn.execute(
                    "SELECT event_id, event_type, concept_tags, rationale, "
                    "confidence, subsystem_refs, ts "
                    "FROM qdkt_knowledge_index "
                    "WHERE concept_tags LIKE ? OR rationale LIKE ? "
                    "ORDER BY ts DESC LIMIT ?",
                    (f"%{concept}%", f"%{concept}%", top_k),
                ).fetchall()
            results["knowledge_index"] = [
                {"event_id": r[0], "type": r[1], "tags": r[2],
                 "rationale": r[3], "confidence": r[4],
                 "refs": r[5], "ts": r[6]} for r in rows
            ]
        except Exception:
            pass
        try:
            with _db(_MEMPALACE_DB) as conn:
                rows = conn.execute(
                    "SELECT thought_id, timestamp, target_file, logic "
                    "FROM cognitive_evolution "
                    "WHERE target_file LIKE ? OR logic LIKE ? "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (f"%{concept}%", f"%{concept}%", top_k),
                ).fetchall()
            results["cognitive"] = [
                {"thought_id": r[0], "ts": r[1], "file": r[2], "logic": r[3]}
                for r in rows
            ]
        except Exception:
            pass
        try:
            with _db(_MEMPALACE_DB) as conn:
                row = conn.execute(
                    "SELECT hypothesis, attempts, successes, avg_error "
                    "FROM causal_ledger WHERE observation LIKE ? LIMIT 1",
                    (f"%{concept}%",),
                ).fetchone()
            if row:
                results["causal"] = {
                    "hypothesis": row[0], "attempts": row[1],
                    "successes": row[2], "avg_error": row[3],
                }
        except Exception:
            pass
        try:
            from aura_hv_cache import ChangeLogStore
            store = ChangeLogStore()
            matches = store.search_by_rationale(concept, top_k=top_k)
            results["changelog"] = [
                {"score": s, "ts": r.get("ts"), "file": r.get("file_path"),
                 "rationale": r.get("rationale"), "author": r.get("author")}
                for s, r in matches
            ]
        except Exception:
            pass
        return results

    def crystallization_candidate(self, concept: str) -> dict | None:
        candidate = _PATTERN_ACCUMULATOR.get(_concept_key(concept))
        return dict(candidate) if candidate else None

    def crystallize(
        self,
        concept: str,
        recommended_action: str,
        *,
        confidence: float = 1.0,
        source: str = "explicit",
        evidence_refs: list[str] | None = None,
        reviewed_by: str | None = None,
        policy_ref: str | None = None,
        source_generation: str | int | None = None,
    ) -> None:
        if str(source).lower() in {"auto_threshold", "repetition", "recurrence"}:
            raise ValueError(
                "recurrence may create a crystallization candidate but cannot self-authorize a crystal"
            )
        key = _concept_key(concept)
        now = time.time()
        entry = {
            "action": recommended_action,
            "confidence": confidence,
            "count": 1,
            "first_seen": now,
            "last_confirmed": now,
            "source": source,
            "status": "accepted",
            "freshness_state": "CURRENT",
            "revalidation_required": False,
            "evidence_refs": list(evidence_refs or []),
            "reviewed_by": reviewed_by,
            "policy_ref": policy_ref,
            "source_generation": source_generation,
        }
        existing = _CRYSTAL_CACHE.get(key)
        if existing:
            entry["count"] = existing.get("count", 0) + 1
            entry["first_seen"] = existing.get("first_seen", entry["first_seen"])
        _CRYSTAL_CACHE[key] = entry
        candidate = _PATTERN_ACCUMULATOR.get(key)
        if candidate:
            candidate["state"] = "promoted"
            candidate["promoted_at"] = now
            candidate["promotion_source"] = source
            candidate["fast_path_eligible"] = False
            self._save_pattern_accumulator()
        self._save_crystal_cache()
        try:
            with _db(_WORKSPACE_DB) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO qdkt_crystals "
                    "(concept_key, action, confidence, count, last_confirmed) "
                    "VALUES (?,?,?,?,?)",
                    (key, recommended_action, confidence,
                     entry["count"], entry["last_confirmed"]),
                )
        except Exception:
            pass
        try:
            with _db(_MEMPALACE_DB) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO qdkt_crystal_cache "
                    "(concept_key, pattern_summary, recommended_action, "
                    " confidence, observation_count, first_seen, last_confirmed, hv_blob) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (key, concept[:256], recommended_action[:512],
                     confidence, entry["count"],
                     entry["first_seen"], entry["last_confirmed"],
                     _hv_bytes(concept)),
                )
        except Exception:
            pass
        print(f"[QDKT] ✦ Crystallized: '{concept[:60]}' → action logged "
              f"(confidence={confidence:.2f}, count={entry['count']})")

    def fast_path(self, concept: str) -> dict | None:
        crystal = _CRYSTAL_CACHE.get(_concept_key(concept))
        return dict(crystal) if _crystal_fast_path_eligible(crystal) else None

    def learning_summary(self) -> str:
        lines = ["[QDKT UNIFIED LEARNING SUMMARY]", ""]
        n_crystals = len(_CRYSTAL_CACHE)
        n_candidates = sum(
            1 for entry in _PATTERN_ACCUMULATOR.values()
            if entry.get("state") in {"candidate", "revalidation_candidate"}
        )
        lines.append(f"  Crystallized patterns : {n_crystals}")
        lines.append(f"  Candidate patterns    : {n_candidates}")
        try:
            with _db(_MEMPALACE_DB) as conn:
                n_idx = conn.execute(
                    "SELECT COUNT(*) FROM qdkt_knowledge_index"
                ).fetchone()[0]
            lines.append(f"  Knowledge index events: {n_idx}")
        except Exception:
            lines.append("  Knowledge index events: (unavailable)")
        try:
            with _db(_MEMPALACE_DB) as conn:
                n_cog = conn.execute(
                    "SELECT COUNT(*) FROM cognitive_evolution"
                ).fetchone()[0]
            lines.append(f"  Cognitive evolution   : {n_cog} engrams")
        except Exception:
            pass
        try:
            with _db(_MEMPALACE_DB) as conn:
                row = conn.execute(
                    "SELECT COUNT(*), SUM(successes), SUM(attempts) FROM causal_ledger"
                ).fetchone()
            if row and row[2]:
                rate = round(row[1] / row[2] * 100, 1) if row[2] else 0
                lines.append(
                    f"  Causal ledger         : {row[0]} hypotheses, "
                    f"{rate}% success rate"
                )
        except Exception:
            pass
        try:
            with _db(_WORKSPACE_DB) as conn:
                n_dream = conn.execute(
                    "SELECT COUNT(*) FROM qdkt_retrieval_usefulness"
                ).fetchone()[0]
            lines.append(f"  DREAM retrieval rows  : {n_dream}")
        except Exception:
            pass
        try:
            from aura_hv_cache import ChangeLogStore
            n_cl = len(ChangeLogStore().all_records())
            lines.append(f"  Change log entries    : {n_cl}")
        except Exception:
            pass
        try:
            with _db(_MEMPALACE_DB) as conn:
                n_holo = conn.execute(
                    "SELECT COUNT(*) FROM dkt_holographic_log"
                ).fetchone()[0]
            lines.append(f"  Holographic blobs     : {n_holo}")
        except Exception:
            pass
        top_c = sorted(
            _CRYSTAL_CACHE.items(),
            key=lambda kv: kv[1].get("confidence", 0) * kv[1].get("count", 1),
            reverse=True,
        )[:3]
        if top_c:
            lines.append("")
            lines.append("  Top crystallized patterns:")
            for key, data in top_c:
                lines.append(
                    f"    [{data.get('count', 1)}x conf={data.get('confidence',0):.2f}] "
                    f"{data.get('action', '?')[:80]}"
                )
        return "\n".join(lines)

    # -- Internal routing --

    def _route_to_holographic(self, node_ref, event_id, concept, payload, ts):
        try:
            gw = getattr(node_ref, "gateway", None)
            if gw and hasattr(gw, "log_dkt_commit"):
                numeric_id = int(
                    hashlib.sha256(event_id.encode()).hexdigest()[:8], 16
                ) % (2**31)
                cpu_temp = payload.get("cpu_temp_c", 42.0)
                exec_ms  = payload.get("execution_ms", 0.0)
                success  = payload.get("success", True)
                gw.log_dkt_commit(numeric_id, concept, cpu_temp, exec_ms, success)
                return f"holographic:{numeric_id}"
        except Exception as exc:
            return f"holographic:error:{exc}"
        return "holographic:no_gateway"

    def _route_to_cognitive_evolution(self, event_id, target_file, logic):
        try:
            with _db(_MEMPALACE_DB) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS cognitive_evolution "
                    "(thought_id TEXT, timestamp TEXT, target_file TEXT, logic TEXT)"
                )
                conn.execute(
                    "INSERT INTO cognitive_evolution VALUES (?,?,?,?)",
                    (event_id, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     target_file, logic[:512]),
                )
            return f"cognitive:{event_id}"
        except Exception as exc:
            return f"cognitive:error:{exc}"

    def _route_to_causal_ledger(self, observation, hypothesis, *, success=True, error=0.0):
        try:
            with _db(_MEMPALACE_DB) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS causal_ledger "
                    "(observation TEXT, hypothesis TEXT, attempts INTEGER DEFAULT 0, "
                    " successes INTEGER DEFAULT 0, avg_error REAL DEFAULT 0.0, "
                    " UNIQUE(observation, hypothesis))"
                )
                conn.execute(
                    """INSERT INTO causal_ledger (observation, hypothesis, attempts,
                       successes, avg_error) VALUES (?, ?, 1, ?, ?)
                       ON CONFLICT(observation, hypothesis) DO UPDATE SET
                        attempts  = attempts + 1,
                        successes = successes + excluded.successes,
                        avg_error = (avg_error * attempts + excluded.avg_error)
                                    / (attempts + 1)""",
                    (observation[:256], hypothesis[:256],
                     1 if success else 0, error),
                )
            return f"causal:{observation[:32]}"
        except Exception as exc:
            return f"causal:error:{exc}"

    def _route_to_changelog(self, payload, rationale):
        try:
            from aura_hv_cache import ChangeLogStore
            store = ChangeLogStore()
            rec = store.log_change(
                file_path=payload.get("file_path", "unknown"),
                line_start=payload.get("line_start", 0),
                line_end=payload.get("line_end", 0),
                old_content=payload.get("old_content", ""),
                new_content=payload.get("new_content", ""),
                rationale=rationale,
                author=payload.get("author", "aura_qdkt"),
                commit_hash=payload.get("commit_hash", ""),
            )
            return f"changelog:{rec.get('hv_idx', '?')}"
        except Exception as exc:
            return f"changelog:error:{exc}"

    def _route_to_token_economics(self, payload):
        try:
            eco = _get_token_economics()
            if eco is None:
                return "economics:unavailable"
            delta = eco.compute_delta(
                model=payload.get("model", "claude-sonnet-4-6"),
                raw_in=payload.get("raw_in_tokens", 0),
                raw_out=payload.get("raw_out_tokens", 0),
                aura_in=payload.get("aura_in_tokens", 0),
                aura_out=payload.get("aura_out_tokens", 0),
            )
            eco.log_call(delta, task=payload.get("task", ""),
                         provider=payload.get("provider", ""))
            return f"economics:saved=${delta['saved_usd']:.6f}"
        except Exception as exc:
            return f"economics:error:{exc}"

    def _write_knowledge_index(self, event_id, event_type, concept,
                               rationale, hv_hash, confidence, refs, ts):
        try:
            with _db(_MEMPALACE_DB) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO qdkt_knowledge_index "
                    "(event_id, event_type, concept_tags, rationale, hv_hash, "
                    " confidence, subsystem_refs, ts) VALUES (?,?,?,?,?,?,?,?)",
                    (event_id, event_type, concept[:256], rationale[:512],
                     hv_hash, confidence, json.dumps(refs), ts),
                )
        except Exception:
            pass

    def _write_workspace_event(self, event_id, event_type, concept,
                               rationale, confidence, ts):
        try:
            with _db(_WORKSPACE_DB) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO qdkt_events "
                    "(event_id, event_type, concept, rationale, confidence, ts) "
                    "VALUES (?,?,?,?,?,?)",
                    (event_id, event_type, concept[:256],
                     rationale[:512], confidence, ts),
                )
        except Exception:
            pass

    def _write_retrieval_usefulness(self, row: dict[str, Any]) -> None:
        columns = (
            "event_id", "query", "target_type", "candidate_id",
            "candidate_type", "source", "usefulness_score", "semantic_score",
            "verifier_result", "phase_hash", "failure_reason", "ts",
        )
        values = tuple(row.get(column) for column in columns)
        sql = (
            "INSERT OR REPLACE INTO qdkt_retrieval_usefulness "
            f"({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})"
        )
        for path in (_MEMPALACE_DB, _WORKSPACE_DB):
            try:
                with _db(path) as conn:
                    conn.execute(sql, values)
            except Exception:
                pass

    def _check_crystallization(self, concept, confidence, payload, *, event_id=None):
        key = _concept_key(concept)
        existing = _PATTERN_ACCUMULATOR.get(key, {})
        count = int(existing.get("count", 0)) + 1
        running_conf = (
            (float(existing.get("confidence", 0.5)) * (count - 1) + confidence) / count
            if existing else confidence
        )
        action = payload.get("recommended_action") or payload.get("action", "")
        obs_fingerprint = _observation_fingerprint(concept, payload)
        source_fingerprint = _source_fingerprint(concept, payload)
        observation_fingerprints = list(existing.get("observation_fingerprints", []))
        source_fingerprints = list(existing.get("source_fingerprints", []))
        evidence_event_ids = list(existing.get("evidence_event_ids", []))
        if obs_fingerprint not in observation_fingerprints:
            observation_fingerprints.append(obs_fingerprint)
        if source_fingerprint not in source_fingerprints:
            source_fingerprints.append(source_fingerprint)
        if event_id and event_id not in evidence_event_ids:
            evidence_event_ids.append(event_id)

        candidate_ready = bool(
            count >= _CRYSTAL_CONFIRM_THRESHOLD
            and running_conf >= _CRYSTAL_CONFIDENCE_THRESHOLD
            and action
        )
        state = "candidate" if candidate_ready else "accumulating"
        if candidate_ready and len(source_fingerprints) < _CRYSTAL_CONFIRM_THRESHOLD:
            candidate_reason = "recurrence_only_or_source_independence_unproven"
        elif candidate_ready:
            candidate_reason = "threshold_met_candidate_only"
        else:
            candidate_reason = "threshold_not_met"

        crystal = _CRYSTAL_CACHE.get(key)
        contradiction = bool(
            payload.get("contradiction")
            or payload.get("is_contradiction")
            or payload.get("contradicts_crystal")
            or payload.get("contradicts")
        )
        freshness_state = str(payload.get("freshness_state", "")).upper()
        stale_source = bool(payload.get("source_stale")) or freshness_state in {
            "STALE", "REVALIDATE", "REJECTED", "BLOCKED"
        }
        if crystal and (contradiction or stale_source):
            crystal["revalidation_required"] = True
            crystal["freshness_state"] = "STALE" if stale_source else "REVALIDATE"
            crystal["revalidation_reason"] = (
                "stale_source_generation" if stale_source else "contradictory_fresh_evidence"
            )
            crystal["revalidation_event_id"] = event_id
            crystal["last_revalidation_signal"] = time.time()
            self._save_crystal_cache()
            state = "revalidation_candidate"

        entry = {
            "action": action,
            "confidence": running_conf,
            "count": count,
            "unique_observation_count": len(observation_fingerprints),
            "independent_source_count": len(source_fingerprints),
            "observation_fingerprints": observation_fingerprints[-64:],
            "source_fingerprints": source_fingerprints[-64:],
            "evidence_event_ids": evidence_event_ids[-64:],
            "first_seen": existing.get("first_seen", time.time()),
            "last_confirmed": time.time(),
            "state": state,
            "candidate_reason": candidate_reason,
            "fast_path_eligible": False,
            "contradiction_count": int(existing.get("contradiction_count", 0)) + (1 if contradiction else 0),
            "last_source_generation": payload.get("source_generation"),
            "last_freshness_state": freshness_state or None,
        }
        _PATTERN_ACCUMULATOR[key] = entry
        self._save_pattern_accumulator()


# Module-level singleton
_INSTANCE: UnifiedQDKT | None = None


def get_qdkt() -> UnifiedQDKT:
    global _INSTANCE  # noqa: PLW0603
    if _INSTANCE is None:
        _INSTANCE = UnifiedQDKT()
    return _INSTANCE


def commit_to_dkt_shim(filename, improvement_logic, *, node_ref=None):
    return get_qdkt().observe(
        "heal_commit",
        {"file_path": filename, "action": improvement_logic[:128]},
        rationale=improvement_logic,
        concept=f"heal:{filename}",
        confidence=0.7,
        subsystem="aura_heal",
        node_ref=node_ref,
    )


def log_dkt_commit_shim(node_ref, numeric_id, user_input, cpu_temp_c,
                         execution_ms, success_flag):
    try:
        gw = getattr(node_ref, "gateway", None)
        if gw and hasattr(gw, "log_dkt_commit"):
            gw.log_dkt_commit(numeric_id, user_input, cpu_temp_c,
                              execution_ms, success_flag)
    except Exception:
        pass
    return get_qdkt().observe(
        "user_command",
        {
            "cpu_temp_c": cpu_temp_c,
            "execution_ms": execution_ms,
            "success": success_flag,
            "action": user_input[:128],
        },
        rationale=f"User command: {user_input[:128]}",
        concept=user_input[:64],
        confidence=0.6 if success_flag else 0.3,
        subsystem="repl",
        node_ref=None,
    )
