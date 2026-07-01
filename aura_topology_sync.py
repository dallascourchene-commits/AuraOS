"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f1-[Q-SYS:TOPOLOGY_SYNC]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Incremental Sync)
DEPENDENCIES: hashlib, json, os, pathlib, sqlite3, time, typing, dataclasses
FUNCTIONS: SyncState, ChangeDetector, TopologySync, load_sync_state, save_sync_state, detect_changes, sync_incremental
SYNOPSIS: Incremental sync layer for the Obsidian + Graphify bridge. Detects which
files, Arena runs, QDKT events, DREAM scores, sidecar refs, verifier reports, and
hot-swap capsules have changed since the last export and returns only the changed
set so the bridge can re-export just those notes/graph nodes. Exact truth remains
in sidecars, CODEMAP, QDKT databases, files, tests, and verifier reports.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any

SYNC_STATE_PATH = Path(".aura/obsidian_graph_sync_state.json")


# ---------------------------------------------------------------------------
# Sync state — persisted fingerprint of the last successful export
# ---------------------------------------------------------------------------

@dataclass
class SyncState:
    """Fingerprints of every source record at the time of the last export."""
    last_sync_unix: float = 0.0
    file_hashes: dict[str, str] = field(default_factory=dict)
    arena_run_hashes: dict[str, str] = field(default_factory=dict)
    qdkt_event_ids: set[str] = field(default_factory=set)
    qdkt_crystal_keys: set[str] = field(default_factory=set)
    dream_score_hashes: dict[str, str] = field(default_factory=dict)
    sidecar_hashes: dict[str, str] = field(default_factory=dict)
    verifier_hashes: dict[str, str] = field(default_factory=dict)
    hot_swap_hashes: dict[str, str] = field(default_factory=dict)
    savings_max_id: int = 0
    fractal_max_block_ts: float = 0.0
    pricing_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_sync_unix": self.last_sync_unix,
            "file_hashes": self.file_hashes,
            "arena_run_hashes": self.arena_run_hashes,
            "qdkt_event_ids": sorted(self.qdkt_event_ids),
            "qdkt_crystal_keys": sorted(self.qdkt_crystal_keys),
            "dream_score_hashes": self.dream_score_hashes,
            "sidecar_hashes": self.sidecar_hashes,
            "verifier_hashes": self.verifier_hashes,
            "hot_swap_hashes": self.hot_swap_hashes,
            "savings_max_id": self.savings_max_id,
            "fractal_max_block_ts": self.fractal_max_block_ts,
            "pricing_hash": self.pricing_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncState:
        return cls(
            last_sync_unix=float(data.get("last_sync_unix", 0.0)),
            file_hashes=dict(data.get("file_hashes", {})),
            arena_run_hashes=dict(data.get("arena_run_hashes", {})),
            qdkt_event_ids=set(data.get("qdkt_event_ids", [])),
            qdkt_crystal_keys=set(data.get("qdkt_crystal_keys", [])),
            dream_score_hashes=dict(data.get("dream_score_hashes", {})),
            sidecar_hashes=dict(data.get("sidecar_hashes", {})),
            verifier_hashes=dict(data.get("verifier_hashes", {})),
            hot_swap_hashes=dict(data.get("hot_swap_hashes", {})),
            savings_max_id=int(data.get("savings_max_id", 0)),
            fractal_max_block_ts=float(data.get("fractal_max_block_ts", 0.0)),
            pricing_hash=str(data.get("pricing_hash", "")),
        )


def load_sync_state(path: str | Path = SYNC_STATE_PATH) -> SyncState:
    p = Path(path)
    if not p.exists():
        return SyncState()
    try:
        return SyncState.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return SyncState()


def save_sync_state(state: SyncState, path: str | Path = SYNC_STATE_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Change set — what needs to be re-exported
# ---------------------------------------------------------------------------

@dataclass
class ChangeSet:
    changed_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    changed_arena_runs: list[str] = field(default_factory=list)
    removed_arena_runs: list[str] = field(default_factory=list)
    new_qdkt_events: list[str] = field(default_factory=list)
    new_qdkt_crystals: list[str] = field(default_factory=list)
    changed_dream_scores: list[str] = field(default_factory=list)
    changed_sidecars: list[str] = field(default_factory=list)
    changed_verifiers: list[str] = field(default_factory=list)
    changed_hot_swaps: list[str] = field(default_factory=list)
    new_savings_ids: list[int] = field(default_factory=list)
    new_fractal_blocks: list[str] = field(default_factory=list)
    pricing_changed: bool = False
    full_resync: bool = False

    @property
    def has_changes(self) -> bool:
        return (
            bool(self.changed_files)
            or bool(self.removed_files)
            or bool(self.changed_arena_runs)
            or bool(self.removed_arena_runs)
            or bool(self.new_qdkt_events)
            or bool(self.new_qdkt_crystals)
            or bool(self.changed_dream_scores)
            or bool(self.changed_sidecars)
            or bool(self.changed_verifiers)
            or bool(self.changed_hot_swaps)
            or bool(self.new_savings_ids)
            or bool(self.new_fractal_blocks)
            or self.pricing_changed
            or self.full_resync
        )

    def summary(self) -> str:
        if self.full_resync:
            return "full resync requested"
        parts = []
        if self.changed_files:
            parts.append(f"{len(self.changed_files)} files")
        if self.removed_files:
            parts.append(f"{len(self.removed_files)} removed files")
        if self.changed_arena_runs:
            parts.append(f"{len(self.changed_arena_runs)} arena runs")
        if self.new_qdkt_events:
            parts.append(f"{len(self.new_qdkt_events)} QDKT events")
        if self.new_qdkt_crystals:
            parts.append(f"{len(self.new_qdkt_crystals)} QDKT crystals")
        if self.changed_dream_scores:
            parts.append(f"{len(self.changed_dream_scores)} DREAM scores")
        if self.changed_sidecars:
            parts.append(f"{len(self.changed_sidecars)} sidecars")
        if self.changed_verifiers:
            parts.append(f"{len(self.changed_verifiers)} verifiers")
        if self.changed_hot_swaps:
            parts.append(f"{len(self.changed_hot_swaps)} hot-swap capsules")
        if self.new_savings_ids:
            parts.append(f"{len(self.new_savings_ids)} savings rows")
        if self.new_fractal_blocks:
            parts.append(f"{len(self.new_fractal_blocks)} fractal blocks")
        if self.pricing_changed:
            parts.append("pricing")
        return ", ".join(parts) if parts else "no changes"


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def _file_hash(path: Path) -> str:
    try:
        return hashlib.blake2b(path.read_bytes(), digest_size=16).hexdigest()
    except Exception:
        return ""


def _json_hash(data: Any) -> str:
    body = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


# ---------------------------------------------------------------------------
# Change detector
# ---------------------------------------------------------------------------

class ChangeDetector:
    """Detects which source records have changed since the last sync state."""

    def __init__(self, root: str | Path = ".",
                 *, exclude_paths: set[str] | None = None) -> None:
        self.root = Path(root).resolve()
        self.exclude_paths = exclude_paths or set()

    # -- files --

    def detect_file_changes(self, state: SyncState) -> tuple[list[str], list[str]]:
        """Return (changed, removed) file paths relative to root."""
        changed: list[str] = []
        current_paths: set[str] = set()

        for path in self._iter_source_files():
            rel = path.relative_to(self.root).as_posix()
            if rel in self.exclude_paths:
                continue
            current_paths.add(rel)
            digest = _file_hash(path)
            if state.file_hashes.get(rel) != digest:
                changed.append(rel)

        removed = sorted(set(state.file_hashes) - current_paths)
        return sorted(changed), removed

    def _iter_source_files(self) -> list[Path]:
        skip_dirs = {
            ".git", "__pycache__", ".pytest_cache", ".mypy_cache",
            ".ruff_cache", "node_modules", "Aura_Memory", ".venv",
            "venv", "env", ".tox", ".nox", "site-packages", "build",
            "dist", ".eggs", ".aura",
        }
        skip_suffixes = {".bak", ".db", ".docx", ".pdf", ".png", ".jpg",
                         ".jpeg", ".gif", ".ttf", ".zip", ".save"}
        paths: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
            for filename in sorted(filenames):
                p = Path(dirpath) / filename
                if p.suffix.lower() in skip_suffixes:
                    continue
                if filename.startswith("."):
                    continue
                paths.append(p)
        return paths

    # -- arena runs --

    def detect_arena_changes(self, state: SyncState) -> tuple[list[str], list[str]]:
        """Return (changed, removed) arena run ids."""
        changed: list[str] = []
        current: set[str] = set()
        for arena_dir in (self.root / "Aura_Memory" / "arenas",
                          self.root / "Aura_Memory" / "icm_workspaces"):
            if not arena_dir.exists():
                continue
            for json_file in arena_dir.rglob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                arena_id = str(data.get("arena_id") or data.get("id") or json_file.stem)
                current.add(arena_id)
                digest = _json_hash(data)
                if state.arena_run_hashes.get(arena_id) != digest:
                    changed.append(arena_id)
        removed = sorted(set(state.arena_run_hashes) - current)
        return sorted(changed), removed

    # -- QDKT events + crystals --

    def detect_qdkt_changes(self, state: SyncState) -> tuple[list[str], list[str]]:
        """Return (new_event_ids, new_crystal_keys)."""
        new_events: list[str] = []
        new_crystals: list[str] = []
        workspace_db = self.root / "Aura_Memory" / "qdkt_index.db"
        if workspace_db.exists():
            try:
                conn = sqlite3.connect(str(workspace_db))
                for event_id, in conn.execute(
                    "SELECT event_id FROM qdkt_events ORDER BY ts"
                ).fetchall():
                    if event_id not in state.qdkt_event_ids:
                        new_events.append(event_id)
                for key, in conn.execute(
                    "SELECT concept_key FROM qdkt_crystals"
                ).fetchall():
                    if key not in state.qdkt_crystal_keys:
                        new_crystals.append(key)
                conn.close()
            except Exception:
                pass
        # Also check the crystal cache JSON
        crystal_json = self.root / "Aura_Memory" / "qdkt_crystal_cache.json"
        if crystal_json.exists():
            try:
                data = json.loads(crystal_json.read_text(encoding="utf-8"))
                for key in data:
                    if key not in state.qdkt_crystal_keys and key not in new_crystals:
                        new_crystals.append(key)
            except Exception:
                pass
        return new_events, new_crystals

    # -- DREAM scores --

    def detect_dream_changes(self, state: SyncState) -> list[str]:
        """Return changed DREAM score phase_hashes."""
        changed: list[str] = []
        ledger = self.root / "Aura_Memory" / "dream_retrieval_ledger.jsonl"
        if not ledger.exists():
            return changed
        try:
            with ledger.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    phase_hash = str(row.get("phase_hash", ""))
                    if not phase_hash:
                        continue
                    digest = _json_hash(row)
                    if state.dream_score_hashes.get(phase_hash) != digest:
                        changed.append(phase_hash)
        except Exception:
            pass
        return changed

    # -- sidecars --

    def detect_sidecar_changes(self, state: SyncState) -> list[str]:
        sidecar_names = [
            "travel_price_sidecar.py", "travel_price_verifier.py",
            "travel_vsa_pointer_index.py", "travel_media_assets.py",
            "travel_package_arena.py", "travel_scraper_core.py",
            "travel_source_registry.py",
        ]
        changed: list[str] = []
        for name in sidecar_names:
            p = self.root / name
            if not p.exists():
                continue
            rel = p.relative_to(self.root).as_posix()
            digest = _file_hash(p)
            if state.sidecar_hashes.get(rel) != digest:
                changed.append(rel)
        return sorted(changed)

    # -- verifiers --

    def detect_verifier_changes(self, state: SyncState) -> list[str]:
        verifier_names = ["aura_validation.py", "travel_price_verifier.py",
                          "aura_tokenizer_guard.py", "aura_resonant_test_oracle.py"]
        changed: list[str] = []
        for name in verifier_names:
            p = self.root / name
            if not p.exists():
                continue
            rel = p.relative_to(self.root).as_posix()
            digest = _file_hash(p)
            if state.verifier_hashes.get(rel) != digest:
                changed.append(rel)
        return sorted(changed)

    # -- hot-swap capsules (phase capsules) --

    def detect_hot_swap_changes(self, state: SyncState) -> list[str]:
        """Phase capsules are the closest existing hot-swap concept."""
        changed: list[str] = []
        # Phase capsules are not persisted to a fixed path; they are captured
        # in-memory. We scan for any persisted phase capsule artifacts.
        for pattern in ("Aura_Memory/phase_capsule_*.json",
                        "Aura_Memory/hot_swap_*.json",
                        "Aura_Memory/phase_*.json"):
            for p in self.root.glob(pattern):
                rel = p.relative_to(self.root).as_posix()
                digest = _file_hash(p)
                if state.hot_swap_hashes.get(rel) != digest:
                    changed.append(rel)
        return sorted(changed)

    # -- savings DB --

    def detect_savings_changes(self, state: SyncState) -> list[int]:
        new_ids: list[int] = []
        db_path = self.root / "Aura_Memory" / "aura_savings.db"
        if not db_path.exists():
            return new_ids
        try:
            conn = sqlite3.connect(str(db_path))
            rows = conn.execute(
                "SELECT id FROM llm_calls WHERE id > ? ORDER BY id",
                (state.savings_max_id,),
            ).fetchall()
            conn.close()
            new_ids = [row[0] for row in rows]
        except Exception:
            pass
        return new_ids

    # -- fractal ledger --

    def detect_fractal_changes(self, state: SyncState) -> list[str]:
        new_blocks: list[str] = []
        db_path = self.root / "aura_ledger.db"
        if not db_path.exists():
            return new_blocks
        try:
            conn = sqlite3.connect(str(db_path))
            rows = conn.execute(
                "SELECT block_hash FROM ledger_blocks WHERE timestamp > ? ORDER BY timestamp",
                (state.fractal_max_block_ts,),
            ).fetchall()
            conn.close()
            new_blocks = [row[0] for row in rows]
        except Exception:
            pass
        return new_blocks

    # -- pricing --

    def detect_pricing_changes(self, state: SyncState) -> bool:
        p = self.root / ".aura" / "pricing.json"
        if not p.exists():
            return False
        digest = _file_hash(p)
        return state.pricing_hash != digest

    # -- full detection --

    def detect(self, state: SyncState, *, force_full: bool = False) -> ChangeSet:
        if force_full or state.last_sync_unix == 0.0:
            return ChangeSet(full_resync=True)

        changed_files, removed_files = self.detect_file_changes(state)
        changed_arena, removed_arena = self.detect_arena_changes(state)
        new_events, new_crystals = self.detect_qdkt_changes(state)
        return ChangeSet(
            changed_files=changed_files,
            removed_files=removed_files,
            changed_arena_runs=changed_arena,
            removed_arena_runs=removed_arena,
            new_qdkt_events=new_events,
            new_qdkt_crystals=new_crystals,
            changed_dream_scores=self.detect_dream_changes(state),
            changed_sidecars=self.detect_sidecar_changes(state),
            changed_verifiers=self.detect_verifier_changes(state),
            changed_hot_swaps=self.detect_hot_swap_changes(state),
            new_savings_ids=self.detect_savings_changes(state),
            new_fractal_blocks=self.detect_fractal_changes(state),
            pricing_changed=self.detect_pricing_changes(state),
        )


def detect_changes(root: str | Path = ".",
                   state: SyncState | None = None,
                   *,
                   force_full: bool = False) -> ChangeSet:
    """Convenience: detect changes against a (loaded) sync state."""
    detector = ChangeDetector(root=root)
    current_state = state if state is not None else load_sync_state()
    return detector.detect(current_state, force_full=force_full)


# ---------------------------------------------------------------------------
# TopologySync — orchestrates a full or incremental sync
# ---------------------------------------------------------------------------

class TopologySync:
    """Orchestrates incremental sync and updates the persisted sync state."""

    def __init__(self, root: str | Path = ".",
                 state_path: str | Path = SYNC_STATE_PATH) -> None:
        self.root = Path(root).resolve()
        self.state_path = Path(state_path)
        # Exclude the sync state file itself from change detection so that
        # writing it does not trigger a spurious "changed file" on the next run.
        state_rel = ""
        try:
            state_rel = self.state_path.relative_to(self.root).as_posix()
        except ValueError:
            pass
        self.detector = ChangeDetector(root=self.root,
                                       exclude_paths={state_rel} if state_rel else set())

    def plan(self, *, force_full: bool = False) -> tuple[ChangeSet, SyncState]:
        """Return (changes, current_state) without mutating anything."""
        state = load_sync_state(self.state_path)
        changes = self.detector.detect(state, force_full=force_full)
        return changes, state

    def commit(self, changes: ChangeSet, state: SyncState) -> SyncState:
        """Update ``state`` in place to reflect the records that were exported.

        Call this *after* the bridge has successfully written the Obsidian notes
        and graph JSON for the changed records.  It advances the fingerprints so
        the next ``plan()`` call will not re-export the same records.
        """
        if changes.full_resync:
            # Rebuild all fingerprints from scratch
            state = SyncState()
            state.file_hashes = {
                rel: _file_hash(self.root / rel)
                for rel in self._all_source_rels()
            }
            state.arena_run_hashes = self._all_arena_hashes()
            state.qdkt_event_ids = set(self._all_qdkt_event_ids())
            state.qdkt_crystal_keys = set(self._all_qdkt_crystal_keys())
            state.dream_score_hashes = self._all_dream_hashes()
            state.sidecar_hashes = self._all_sidecar_hashes()
            state.verifier_hashes = self._all_verifier_hashes()
            state.hot_swap_hashes = self._all_hot_swap_hashes()
            state.savings_max_id = self._savings_max_id()
            state.fractal_max_block_ts = self._fractal_max_ts()
            state.pricing_hash = self._pricing_hash()
        else:
            for rel in changes.changed_files:
                state.file_hashes[rel] = _file_hash(self.root / rel)
            for rel in changes.removed_files:
                state.file_hashes.pop(rel, None)
            for arena_id in changes.changed_arena_runs:
                state.arena_run_hashes[arena_id] = self._arena_hash(arena_id)
            for arena_id in changes.removed_arena_runs:
                state.arena_run_hashes.pop(arena_id, None)
            state.qdkt_event_ids.update(changes.new_qdkt_events)
            state.qdkt_crystal_keys.update(changes.new_qdkt_crystals)
            for phase_hash in changes.changed_dream_scores:
                state.dream_score_hashes[phase_hash] = self._dream_hash(phase_hash)
            for rel in changes.changed_sidecars:
                state.sidecar_hashes[rel] = _file_hash(self.root / rel)
            for rel in changes.changed_verifiers:
                state.verifier_hashes[rel] = _file_hash(self.root / rel)
            for rel in changes.changed_hot_swaps:
                state.hot_swap_hashes[rel] = _file_hash(self.root / rel)
            if changes.new_savings_ids:
                state.savings_max_id = max(state.savings_max_id,
                                           max(changes.new_savings_ids))
            if changes.new_fractal_blocks:
                state.fractal_max_block_ts = self._fractal_max_ts()
            if changes.pricing_changed:
                state.pricing_hash = self._pricing_hash()

        state.last_sync_unix = time.time()
        save_sync_state(state, self.state_path)
        return state

    # -- helpers for commit --

    def _all_source_rels(self) -> list[str]:
        return [
            p.relative_to(self.root).as_posix()
            for p in self.detector._iter_source_files()
        ]

    def _all_arena_hashes(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for arena_dir in (self.root / "Aura_Memory" / "arenas",
                          self.root / "Aura_Memory" / "icm_workspaces"):
            if not arena_dir.exists():
                continue
            for json_file in arena_dir.rglob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                arena_id = str(data.get("arena_id") or data.get("id") or json_file.stem)
                result[arena_id] = _json_hash(data)
        return result

    def _arena_hash(self, arena_id: str) -> str:
        for arena_dir in (self.root / "Aura_Memory" / "arenas",
                          self.root / "Aura_Memory" / "icm_workspaces"):
            if not arena_dir.exists():
                continue
            for json_file in arena_dir.rglob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if str(data.get("arena_id") or data.get("id") or json_file.stem) == arena_id:
                    return _json_hash(data)
        return ""

    def _all_qdkt_event_ids(self) -> list[str]:
        ids: list[str] = []
        db = self.root / "Aura_Memory" / "qdkt_index.db"
        if db.exists():
            try:
                conn = sqlite3.connect(str(db))
                ids = [row[0] for row in conn.execute(
                    "SELECT event_id FROM qdkt_events").fetchall()]
                conn.close()
            except Exception:
                pass
        return ids

    def _all_qdkt_crystal_keys(self) -> list[str]:
        keys: list[str] = []
        db = self.root / "Aura_Memory" / "qdkt_index.db"
        if db.exists():
            try:
                conn = sqlite3.connect(str(db))
                keys = [row[0] for row in conn.execute(
                    "SELECT concept_key FROM qdkt_crystals").fetchall()]
                conn.close()
            except Exception:
                pass
        crystal_json = self.root / "Aura_Memory" / "qdkt_crystal_cache.json"
        if crystal_json.exists():
            try:
                keys.extend(json.loads(crystal_json.read_text(encoding="utf-8")).keys())
            except Exception:
                pass
        return keys

    def _all_dream_hashes(self) -> dict[str, str]:
        result: dict[str, str] = {}
        ledger = self.root / "Aura_Memory" / "dream_retrieval_ledger.jsonl"
        if not ledger.exists():
            return result
        try:
            with ledger.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    phase_hash = str(row.get("phase_hash", ""))
                    if phase_hash:
                        result[phase_hash] = _json_hash(row)
        except Exception:
            pass
        return result

    def _dream_hash(self, phase_hash: str) -> str:
        return self._all_dream_hashes().get(phase_hash, "")

    def _all_sidecar_hashes(self) -> dict[str, str]:
        names = [
            "travel_price_sidecar.py", "travel_price_verifier.py",
            "travel_vsa_pointer_index.py", "travel_media_assets.py",
            "travel_package_arena.py", "travel_scraper_core.py",
            "travel_source_registry.py",
        ]
        result: dict[str, str] = {}
        for name in names:
            p = self.root / name
            if p.exists():
                result[p.relative_to(self.root).as_posix()] = _file_hash(p)
        return result

    def _all_verifier_hashes(self) -> dict[str, str]:
        names = ["aura_validation.py", "travel_price_verifier.py",
                 "aura_tokenizer_guard.py", "aura_resonant_test_oracle.py"]
        result: dict[str, str] = {}
        for name in names:
            p = self.root / name
            if p.exists():
                result[p.relative_to(self.root).as_posix()] = _file_hash(p)
        return result

    def _all_hot_swap_hashes(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for pattern in ("Aura_Memory/phase_capsule_*.json",
                        "Aura_Memory/hot_swap_*.json",
                        "Aura_Memory/phase_*.json"):
            for p in self.root.glob(pattern):
                result[p.relative_to(self.root).as_posix()] = _file_hash(p)
        return result

    def _savings_max_id(self) -> int:
        db = self.root / "Aura_Memory" / "aura_savings.db"
        if not db.exists():
            return 0
        try:
            conn = sqlite3.connect(str(db))
            row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM llm_calls").fetchone()
            conn.close()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def _fractal_max_ts(self) -> float:
        db = self.root / "aura_ledger.db"
        if not db.exists():
            return 0.0
        try:
            conn = sqlite3.connect(str(db))
            row = conn.execute(
                "SELECT COALESCE(MAX(timestamp), 0) FROM ledger_blocks"
            ).fetchone()
            conn.close()
            return float(row[0]) if row else 0.0
        except Exception:
            return 0.0

    def _pricing_hash(self) -> str:
        p = self.root / ".aura" / "pricing.json"
        return _file_hash(p) if p.exists() else ""


def sync_incremental(root: str | Path = ".",
                     *,
                     force_full: bool = False,
                     state_path: str | Path = SYNC_STATE_PATH) -> ChangeSet:
    """One-shot convenience: detect changes and return them without committing.

    Use ``TopologySync`` directly to commit after a successful export.
    """
    changes, _ = TopologySync(root=root, state_path=state_path).plan(force_full=force_full)
    return changes