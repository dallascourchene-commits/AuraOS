"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9d0-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy / Unified Knowledge)
DEPENDENCIES: __future__, hashlib, json, os, pathlib, sqlite3, struct, time,
              asyncio, typing, numpy, aura_hv_cache, aura_token_economics
FUNCTIONS: UnifiedQDKT, observe, query, crystallize, promote_to_crystal,
           _route_to_holographic, _route_to_cognitive_evolution,
           _route_to_causal_ledger, _check_crystallization
SYNOPSIS: Pure-asyncio unified QDKT hub (lock-free, single-threaded). Routes
          knowledge events across all five pre-existing DKT subsystems and the
          new semantic-bridge tables.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_MEMPALACE_DB   = Path.home() / ".mempalace" / "aura_memory.db"
_WORKSPACE_DB   = Path("Aura_Memory/qdkt_index.db")
_CRYSTAL_JSON   = Path("Aura_Memory/qdkt_crystal_cache.json")

_CRYSTAL_CONFIRM_THRESHOLD = 3
_CRYSTAL_CONFIDENCE_THRESHOLD = 0.75

# Lock-free — pure asyncio single-threaded execution
_CRYSTAL_CACHE: dict[str, dict] = {}


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

    def _load_crystal_cache(self) -> None:
        global _CRYSTAL_CACHE
        if _CRYSTAL_JSON.exists():
            try:
                with open(_CRYSTAL_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                _CRYSTAL_CACHE.update(data)
            except Exception:
                pass
        try:
            with _db(_WORKSPACE_DB) as conn:
                rows = conn.execute(
                    "SELECT concept_key, action, confidence, count, last_confirmed "
                    "FROM qdkt_crystals"
                ).fetchall()
            for key, action, conf, count, ts in rows:
                if key not in _CRYSTAL_CACHE:
                    _CRYSTAL_CACHE[key] = {
                        "action": action, "confidence": conf,
                        "count": count, "last_confirmed": ts,
                    }
        except Exception:
            pass

    def _save_crystal_cache(self) -> None:
        try:
            _CRYSTAL_JSON.parent.mkdir(parents=True, exist_ok=True)
            snapshot = dict(_CRYSTAL_CACHE)
            with open(_CRYSTAL_JSON, "w", encoding="utf-8") as f:
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
        self._check_crystallization(concept_str, confidence, payload)

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
            "knowledge_index": [],
            "cognitive": [],
            "causal": None,
            "changelog": [],
        }
        key = _concept_key(concept)
        crystal = _CRYSTAL_CACHE.get(key)
        if crystal:
            results["fast_path"] = crystal
            return results
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

    def crystallize(
        self,
        concept: str,
        recommended_action: str,
        *,
        confidence: float = 1.0,
        source: str = "explicit",
    ) -> None:
        key = _concept_key(concept)
        entry = {
            "action": recommended_action,
            "confidence": confidence,
            "count": 1,
            "first_seen": time.time(),
            "last_confirmed": time.time(),
            "source": source,
        }
        existing = _CRYSTAL_CACHE.get(key)
        if existing:
            entry["count"] = existing.get("count", 0) + 1
            entry["first_seen"] = existing.get("first_seen", entry["first_seen"])
        _CRYSTAL_CACHE[key] = entry
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
        return _CRYSTAL_CACHE.get(_concept_key(concept))

    def learning_summary(self) -> str:
        lines = ["[QDKT UNIFIED LEARNING SUMMARY]", ""]
        n_crystals = len(_CRYSTAL_CACHE)
        lines.append(f"  Crystallized patterns : {n_crystals}")
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

    def _check_crystallization(self, concept, confidence, payload):
        key = _concept_key(concept)
        existing = _CRYSTAL_CACHE.get(key)
        count = (existing.get("count", 0) + 1) if existing else 1
        running_conf = (
            (existing.get("confidence", 0.5) * (count - 1) + confidence) / count
            if existing else confidence
        )
        if (count >= _CRYSTAL_CONFIRM_THRESHOLD and
                running_conf >= _CRYSTAL_CONFIDENCE_THRESHOLD):
            action = payload.get("recommended_action") or payload.get("action", "")
            if action:
                self.crystallize(concept, action, confidence=running_conf,
                                 source="auto_threshold")
                return
        entry = {
            "action": payload.get("action", ""),
            "confidence": running_conf,
            "count": count,
            "first_seen": (existing or {}).get("first_seen", time.time()),
            "last_confirmed": time.time(),
        }
        _CRYSTAL_CACHE[key] = entry


# Module-level singleton
_INSTANCE: UnifiedQDKT | None = None


def get_qdkt() -> UnifiedQDKT:
    global _INSTANCE
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