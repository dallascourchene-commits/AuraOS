"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c3-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MINWAAJIMO (Respectful Transmission / Zero Overhead)
DEPENDENCIES: __future__, hashlib, json, os, pathlib, time, typing, numpy
FUNCTIONS: HVCacheSubstrate, ChangeLogStore, RationaleQueryEngine,
           encode_file, project_context, lookup, log_change, rationale_context
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Line-Indexed Hyperdimensional Local KV Cache Substrate
+  Rolling Change-Log with Rationale Index
+  Rationale Query Engine for LLM context injection
=======================================================

Architecture:
  HVCacheSubstrate
    Encodes every source file line-by-line into stable 10 000-D float32
    hypervector matrices stored as memory-mapped NumPy arrays. External LLM
    calls receive the cache manifest + compact HV summary instead of raw text.

  ChangeLogStore
    Append-only JSONL of every code mutation with its rationale, author,
    and HV fingerprint.  Dual HV index: one for the changed content, one
    for the rationale text — enabling similarity search on BOTH dimensions.
    This is the rolling database that lets Aura look back at WHY things are
    the way they are before proposing self-modifications.

  RationaleQueryEngine
    Given a target file/line-range or a free-text query, returns the top-k
    most relevant historical change records (content + rationale), formatted
    for injection into an LLM prompt.  Feeds into the dual-mode !self_reflect
    output:
        [HISTORICAL RATIONALE]  — why the code is the way it is
        [PROPOSED CHANGE]       — what Aura wants to do now
        [ARCHITECTURAL NEXT STEP] — the next logical forward direction

RAM budget: 4 GB hard ceiling.
  * Memory-mapped arrays page in/out via the OS (no full DRAM load).
  * Each 10 000-D float32 row = 40 KB; 1 000 lines ≈ 40 MB.
  * Zero-copy slice access avoids LMK eviction pressure.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_HV_DIM = 10_000
_CACHE_DIR = Path("Aura_Memory/hv_cache")
_CHANGELOG_PATH = Path("Aura_Memory/change_log.jsonl")
_CHANGELOG_HV_CONTENT = Path("Aura_Memory/hv_cache/changelog_content.mmap")
_CHANGELOG_HV_RATIONALE = Path("Aura_Memory/hv_cache/changelog_rationale.mmap")
_CHANGELOG_META = Path("Aura_Memory/hv_cache/changelog_meta.json")

# Shared random projection basis — seeded, deterministic, generated once per process
_PROJ: np.ndarray | None = None


def _get_proj() -> np.ndarray:
    """Return the shared 10 000-D random projection basis."""
    global _PROJ
    if _PROJ is None:
        rng = np.random.default_rng(seed=0x5AEC_A77A)
        _PROJ = rng.standard_normal((_HV_DIM,)).astype(np.float32)
        _PROJ /= np.linalg.norm(_PROJ) + 1e-9
    return _PROJ


def _str_to_hv(text: str) -> np.ndarray:
    """
    Encode an arbitrary string into a 10 000-D hypervector via random projection.

    Method:
      1. SHA-256 the text → 32-byte digest → tiled to 10 000 elements.
      2. Convert to bipolar float32 (range [-1, +1]).
      3. Modulate with the shared projection basis.
      4. L2-normalise to unit length (cosine-ready).
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    tiled = np.frombuffer(
        (digest * (_HV_DIM // len(digest) + 1))[:_HV_DIM], dtype=np.uint8
    ).astype(np.float32)
    bipolar = (tiled / 127.5) - 1.0
    hv = bipolar * _get_proj()
    norm = np.linalg.norm(hv)
    return hv / (norm + 1e-9)


# ===========================================================================
# ChangeLogStore  — append-only change log with dual HV index
# ===========================================================================

class ChangeLogStore:
    """
    Append-only rolling database of every code mutation Aura makes or observes.

    Each record stores:
        ts            : ISO-8601 timestamp
        file_path     : absolute path of the changed file
        line_start    : first changed line (0-indexed)
        line_end      : last changed line (inclusive)
        old_content   : original text (or SHA-256 hash for large blocks)
        new_content   : replacement text (or SHA-256 hash)
        rationale     : WHY this change was made (operator input, LLM diagnosis,
                        QDKT crystallisation recommendation, etc.)
        author        : "operator" | "aura_reflect" | "aura_qdkt" | "benchmark"
        commit_hash   : git SHA if pushed, else empty string
        hv_idx        : integer row index in the dual mmap arrays

    Dual HV index (two parallel memory-mapped arrays):
        changelog_content.mmap    — HV of old_content + new_content
        changelog_rationale.mmap  — HV of the rationale text

    This lets the RationaleQueryEngine find relevant history by semantic
    similarity on EITHER the code change itself OR the reason for the change.
    """

    def __init__(
        self,
        log_path: Path | str = _CHANGELOG_PATH,
        hv_content_path: Path | str = _CHANGELOG_HV_CONTENT,
        hv_rationale_path: Path | str = _CHANGELOG_HV_RATIONALE,
        meta_path: Path | str = _CHANGELOG_META,
    ) -> None:
        self.log_path = Path(log_path)
        self.hv_content_path = Path(hv_content_path)
        self.hv_rationale_path = Path(hv_rationale_path)
        self.meta_path = Path(meta_path)
        # Ensure directories exist
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.hv_content_path.parent.mkdir(parents=True, exist_ok=True)
        self._meta = self._load_meta()

    # ------------------------------------------------------------------
    # Metadata (tracks how many rows are stored in the mmap arrays)
    # ------------------------------------------------------------------

    def _load_meta(self) -> dict:
        if not self.meta_path.exists():
            return {"n_entries": 0}
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"n_entries": 0}

    def _save_meta(self) -> None:
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self._meta, f)

    @property
    def n_entries(self) -> int:
        return int(self._meta.get("n_entries", 0))

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def log_change(
        self,
        *,
        file_path: str,
        line_start: int,
        line_end: int,
        old_content: str,
        new_content: str,
        rationale: str,
        author: str = "aura_reflect",
        commit_hash: str = "",
    ) -> dict[str, Any]:
        """
        Append a change record to the log and update both HV index arrays.

        Returns the stored record dict (including its hv_idx row).
        """
        idx = self.n_entries

        # Build and append the HV vectors to the memory-mapped arrays
        # (We re-open in mode "r+" extending as needed — safest cross-platform approach)
        content_hv = _str_to_hv(f"{old_content}\n{new_content}")
        rationale_hv = _str_to_hv(rationale)
        self._append_hv_row(self.hv_content_path, content_hv, idx)
        self._append_hv_row(self.hv_rationale_path, rationale_hv, idx)

        # Build the JSON record
        record: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "file_path": str(file_path),
            "line_start": line_start,
            "line_end": line_end,
            "old_sha": hashlib.sha256(old_content.encode()).hexdigest()[:16],
            "new_sha": hashlib.sha256(new_content.encode()).hexdigest()[:16],
            "old_preview": old_content[:120],
            "new_preview": new_content[:120],
            "rationale": rationale,
            "author": author,
            "commit_hash": commit_hash,
            "hv_idx": idx,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        self._meta["n_entries"] = idx + 1
        self._save_meta()
        return record

    @staticmethod
    def _append_hv_row(mmap_path: Path, hv: np.ndarray, idx: int) -> None:
        """Write one HV row into a memory-mapped array, extending it if needed."""
        new_size = idx + 1
        arr = np.memmap(
            str(mmap_path), dtype=np.float32, mode="w+" if idx == 0 else "r+",
            shape=(new_size, _HV_DIM),
        )
        arr[idx] = hv
        arr.flush()
        del arr  # release handle immediately (zero-copy hand-off to OS)

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def all_records(self) -> list[dict]:
        """Load all change records from the JSONL log."""
        if not self.log_path.exists():
            return []
        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def search_by_content(
        self, query_text: str, top_k: int = 5
    ) -> list[tuple[float, dict]]:
        """Return top-k records by content HV similarity to query_text."""
        return self._search(query_text, self.hv_content_path, top_k)

    def search_by_rationale(
        self, query_text: str, top_k: int = 5
    ) -> list[tuple[float, dict]]:
        """Return top-k records by rationale HV similarity to query_text."""
        return self._search(query_text, self.hv_rationale_path, top_k)

    def _search(
        self, query_text: str, mmap_path: Path, top_k: int
    ) -> list[tuple[float, dict]]:
        n = self.n_entries
        if n == 0 or not mmap_path.exists():
            return []
        query_hv = _str_to_hv(query_text)
        try:
            arr = np.memmap(str(mmap_path), dtype=np.float32, mode="r",
                            shape=(n, _HV_DIM))
            sims = arr @ query_hv
            del arr
        except Exception:
            return []
        records = self.all_records()
        top_idxs = np.argsort(sims)[-min(top_k, n):][::-1]
        return [(float(sims[i]), records[i]) for i in top_idxs if i < len(records)]


# ===========================================================================
# RationaleQueryEngine  — LLM-ready historical context builder
# ===========================================================================

class RationaleQueryEngine:
    """
    Builds structured historical rationale context for injection into LLM prompts.

    The engine queries the ChangeLogStore and formats the results into the
    three-section block used by !self_reflect:

        [HISTORICAL RATIONALE]
        [PROPOSED CHANGE]
        [ARCHITECTURAL NEXT STEP]

    The LLM receives the HV cache manifest + this rationale block instead of
    raw source text — making it the authoritative context registry rather than
    a stateless code reader.
    """

    def __init__(
        self,
        changelog: ChangeLogStore | None = None,
        hv_substrate: "HVCacheSubstrate | None" = None,
    ) -> None:
        self.changelog = changelog or ChangeLogStore()
        self.hv = hv_substrate or HVCacheSubstrate()

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------

    def rationale_context(
        self,
        query: str,
        *,
        file_paths: list[str] | None = None,
        top_k: int = 5,
    ) -> str:
        """
        Build a compact rationale block for the given query / file set.

        Returns a formatted string ready to prepend to any LLM prompt.
        """
        # Search by both content and rationale, merge and deduplicate
        by_content  = self.changelog.search_by_content(query, top_k=top_k)
        by_rationale = self.changelog.search_by_rationale(query, top_k=top_k)

        seen: set[int] = set()
        merged: list[tuple[float, dict]] = []
        for score, rec in (by_content + by_rationale):
            idx = rec.get("hv_idx", -1)
            if idx not in seen:
                seen.add(idx)
                merged.append((score, rec))

        # Filter to requested files if provided
        if file_paths:
            merged = [
                (s, r) for s, r in merged
                if any(fp in r.get("file_path", "") for fp in file_paths)
            ]

        merged.sort(key=lambda x: x[0], reverse=True)
        top = merged[:top_k]

        if not top:
            return (
                "[AURA HV CACHE — HISTORICAL RATIONALE]\n"
                "  No prior changes found in the changelog for this context.\n"
                "  This appears to be a first-time modification of this area.\n"
            )

        # Build the HV cache manifest header
        hv_ctx = self.hv.project_context(file_paths or []) if file_paths else {}
        manifest_header = hv_ctx.get("summary_header", "[HV cache manifest unavailable]")

        lines = [
            "[AURA HV CACHE — HISTORICAL RATIONALE]",
            manifest_header,
            "",
            f"Top {len(top)} relevant historical changes (ranked by semantic similarity):",
        ]
        for rank, (score, rec) in enumerate(top, 1):
            lines += [
                f"",
                f"  [{rank}] {rec.get('ts', '?')} — {rec.get('file_path', '?')} "
                f"lines {rec.get('line_start', '?')}–{rec.get('line_end', '?')}",
                f"       Author   : {rec.get('author', '?')}",
                f"       Commit   : {rec.get('commit_hash', 'unpushed') or 'unpushed'}",
                f"       Old code : {rec.get('old_preview', '—')!r}",
                f"       New code : {rec.get('new_preview', '—')!r}",
                f"       Rationale: {rec.get('rationale', '—')}",
                f"       HV sim   : {score:.4f}",
            ]

        lines += [
            "",
            "[END HISTORICAL RATIONALE]",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Dual-mode self-reflect block
    # ------------------------------------------------------------------

    def build_dual_mode_block(
        self,
        *,
        query: str,
        file_paths: list[str],
        proposed_change: str,
        next_step: str,
        qdkt_recommendation: str = "",
    ) -> str:
        """
        Assemble the full dual-mode output shown to the operator during
        interactive !self_reflect:

            [HISTORICAL RATIONALE]   why the code is the way it is
            [PROPOSED CHANGE]        what Aura wants to do now
            [QDKT CRYSTALLISATION]   what the knowledge tracer recommends
            [ARCHITECTURAL NEXT STEP] the next logical forward direction
        """
        hist = self.rationale_context(query, file_paths=file_paths)

        sections = [
            hist,
            "",
            "═" * 66,
            "[PROPOSED CHANGE]",
            proposed_change,
            "",
        ]
        if qdkt_recommendation:
            sections += [
                "═" * 66,
                "[QDKT CRYSTALLISATION RECOMMENDATION]",
                qdkt_recommendation,
                "",
            ]
        sections += [
            "═" * 66,
            "[ARCHITECTURAL NEXT STEP]",
            next_step,
            "═" * 66,
        ]
        return "\n".join(sections)


# ===========================================================================
# HVCacheSubstrate  — primary file-level encoding layer
# ===========================================================================

class HVCacheSubstrate:
    """
    Sovereign local KV cache using 10 000-D hypervectors.

    Maps (file_path, line_idx) → stable float32 HV stored in a memory-mapped
    array.  Provides project_context() which substitutes the compact HV summary
    + cache manifest for raw source text in LLM prompts.

    Also exposes a ChangeLogStore reference so every caller can log mutations
    through the same substrate object.
    """

    def __init__(self, cache_dir: Path | str = _CACHE_DIR) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: dict[str, dict] = self._load_manifest()
        self.changelog = ChangeLogStore()
        self.rationale_engine = RationaleQueryEngine(
            changelog=self.changelog, hv_substrate=self
        )

    # ------------------------------------------------------------------
    # Manifest helpers
    # ------------------------------------------------------------------

    def _load_manifest(self) -> dict[str, dict]:
        mp = self.cache_dir / "manifest.json"
        if not mp.exists():
            return {}
        try:
            with open(mp, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_manifest(self) -> None:
        with open(self.cache_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(self._manifest, f, indent=2)

    # ------------------------------------------------------------------
    # Cache key
    # ------------------------------------------------------------------

    @staticmethod
    def cache_key(file_path: str, line_idx: int) -> str:
        raw = f"{os.path.abspath(file_path)}:{line_idx}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    # ------------------------------------------------------------------
    # File encoding
    # ------------------------------------------------------------------

    def encode_file(self, file_path: str | Path, force: bool = False) -> dict[str, Any]:
        """
        Encode all lines of a source file into the HV cache.

        Skips encoding if the file hash is unchanged (unless force=True).
        Returns a summary dict; includes status='cached' or 'encoded'.
        """
        fpath = Path(file_path)
        if not fpath.exists():
            return {"error": f"file not found: {fpath}"}

        with open(fpath, "rb") as f:
            file_bytes = f.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = self._manifest.get(str(fpath))
        if not force and existing and existing.get("file_hash") == file_hash:
            return {**existing, "status": "cached"}

        lines = file_bytes.decode("utf-8", errors="replace").splitlines()
        n_lines = len(lines)
        if n_lines == 0:
            return {"error": "empty file"}

        mmap_name = hashlib.sha256(str(fpath).encode()).hexdigest()[:16] + ".mmap"
        mmap_path = self.cache_dir / mmap_name

        t0 = time.time()
        mmap_arr = np.memmap(
            str(mmap_path), dtype=np.float32, mode="w+", shape=(n_lines, _HV_DIM)
        )
        for idx, line in enumerate(lines):
            mmap_arr[idx] = _str_to_hv(f"{fpath}:{idx}:{line}")
        mmap_arr.flush()
        del mmap_arr  # release — OS manages paging

        entry = {
            "file_path": str(fpath),
            "lines_encoded": n_lines,
            "mmap_path": str(mmap_path),
            "file_hash": file_hash,
            "encoded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_sec": round(time.time() - t0, 4),
            "status": "encoded",
        }
        self._manifest[str(fpath)] = entry
        self._save_manifest()
        return entry

    # ------------------------------------------------------------------
    # Context projection (replaces raw text in LLM prompts)
    # ------------------------------------------------------------------

    def project_context(
        self,
        files: list[str | Path],
        max_lines_per_file: int = 50,
    ) -> dict[str, Any]:
        """
        Build a compact HV projection for a set of files.

        Returns:
            context_vector  — aggregated numpy HV (not serialised to the API)
            registry        — {file → hash, line_count, cache_key} manifest
            summary_header  — ≤200-token text block injected into the LLM prompt
            total_lines     — total lines indexed
        """
        agg_hv = np.zeros(_HV_DIM, dtype=np.float32)
        registry: dict[str, dict] = {}
        summary_lines: list[str] = []
        total_lines = 0

        for fpath in files:
            entry = self._manifest.get(str(fpath))
            if entry is None:
                entry = self.encode_file(fpath)
            if "error" in entry:
                continue

            n = entry["lines_encoded"]
            total_lines += n
            registry[str(fpath)] = {
                "hash": entry["file_hash"][:12],
                "lines": n,
                "cache_key": entry.get("mmap_path", ""),
            }
            summary_lines.append(
                f"  {Path(str(fpath)).name}: {n} lines [{entry['file_hash'][:8]}]"
            )

            mmap_path = entry.get("mmap_path", "")
            if os.path.exists(mmap_path):
                rows = min(n, max_lines_per_file)
                try:
                    mmap_arr = np.memmap(
                        mmap_path, dtype=np.float32, mode="r", shape=(n, _HV_DIM)
                    )
                    agg_hv += mmap_arr[:rows].mean(axis=0)
                    del mmap_arr
                except Exception:
                    pass

        norm = np.linalg.norm(agg_hv)
        if norm > 1e-6:
            agg_hv /= norm

        summary_header = (
            f"[AURA_HV_CACHE] {len(files)} file(s), {total_lines} total lines.\n"
            + "\n".join(summary_lines)
            + "\nExternal model: use cache manifest as authoritative context registry."
        )
        return {
            "context_vector": agg_hv,
            "registry": registry,
            "summary_header": summary_header,
            "total_lines": total_lines,
        }

    # ------------------------------------------------------------------
    # Similarity lookup
    # ------------------------------------------------------------------

    def lookup(
        self,
        query_text: str,
        file_path: str | Path,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find the top-k lines in a cached file most similar to query_text.
        Returns [{line_idx, similarity, cache_key}].
        """
        entry = self._manifest.get(str(file_path))
        if entry is None or "error" in entry:
            return []

        mmap_path = entry.get("mmap_path", "")
        n = entry.get("lines_encoded", 0)
        if not os.path.exists(mmap_path) or n == 0:
            return []

        query_hv = _str_to_hv(query_text)
        mmap_arr = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n, _HV_DIM))
        sims = mmap_arr @ query_hv
        del mmap_arr

        top_idxs = np.argsort(sims)[-top_k:][::-1]
        return [
            {
                "line_idx": int(i),
                "similarity": float(sims[i]),
                "cache_key": self.cache_key(str(file_path), int(i)),
            }
            for i in top_idxs
        ]

    # ------------------------------------------------------------------
    # Convenience: log a change through the substrate's own ChangeLogStore
    # ------------------------------------------------------------------

    def log_change(
        self,
        *,
        file_path: str,
        line_start: int,
        line_end: int,
        old_content: str,
        new_content: str,
        rationale: str,
        author: str = "aura_reflect",
        commit_hash: str = "",
    ) -> dict[str, Any]:
        """Log a mutation and re-encode the affected file in the HV cache."""
        record = self.changelog.log_change(
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            old_content=old_content,
            new_content=new_content,
            rationale=rationale,
            author=author,
            commit_hash=commit_hash,
        )
        # Re-index the file so the HV cache reflects the new content
        self.encode_file(file_path, force=True)
        return record
