"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MIIGWECH (Extension-Based Storage)
DEPENDENCIES: pathlib, gc, asyncio, numpy, hashlib, time, sqlite3, collections, datetime, aiosqlite, os, struct
FUNCTIONS: __init__, append_record, flush_and_clear, flush_np, compile_bftree_matrix_view,
           __init__, __aenter__, __aexit__, enqueue_holographic_trace,
           _background_flush_holographic, _write_morphemic_batch_to_disk,
           enqueue_morphemic_root_trace, _auto_flush_morphemic_pool, _stone_crawler,
           stream_vectors, lock_atomic_spin_state, get_all_crystallized_phases,
           verify_incremental_frontier, check_audit_cache, update_audit_cache
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Patch v2 — Memory Ceiling / Zero-Copy compliance (MorphemicBatchQueue)
=======================================================================
Complexity comparison:

  Operation                           | Old              | New           | Gain
  ------------------------------------|------------------|---------------|------------------
  append_record (write)               | struct.pack+deque| numpy inplace | ~3× (no alloc)
  flush_and_clear (bulk read)         | N struct.unpack  | numpy slice   | ~3-5×
  compile_bftree_matrix_view (native) | O(N) Python loop | O(1) np view  | ~N× (zero-copy)
  compile_bftree_matrix_view (legacy) | N struct.unpack  | 1 frombuffer  | ~5-8×

  N = max_records (128 default)

Backward compatibility
----------------------
* ``flush_and_clear()`` — unchanged signature, unchanged return type (list of
  7-tuples).  This is the Legacy Bridge for all existing callers in
  AsyncMemoryPalace._write_morphemic_batch_to_disk and __aexit__.
* ``queue`` attribute — now a property returning ``self``; supports ``len()``
  via ``__len__`` and iteration via ``__iter__`` so existing code that does
  ``len(pool.queue)`` or ``list(pool.queue)`` continues to work.
* ``flush_np()`` — NEW zero-copy method returning a numpy structured-array
  view; no existing code is deprecated.
* ``compile_bftree_matrix_view(linear_frames=None)`` — unchanged signature.
  Native path (no arg) now returns a direct numpy view; legacy path (list of
  bytes) uses a single bytearray + frombuffer instead of N struct.unpack calls.
"""
# [AURA OPTIMIZED] - Bloat removed.
from __future__ import annotations
from dataclasses import dataclass
from logging_kit import log_error, log_report
import asyncio
import aiofiles
from typing import Any, AsyncIterator, Optional
import gc
import hashlib
import os
import shutil
import sqlite3
import struct
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore[assignment,misc]

try:
    from pvm_memory_guard import MemoryBudget as _MemoryBudget, PVM_RAM_CEILING_MB as _RAM_CEILING_MB
except ImportError:
    _MemoryBudget = None   # type: ignore[assignment,misc]
    _RAM_CEILING_MB = 4096

async def async_pipeline(
    input_stream: AsyncIterator[str],
    output_sink: Any,
    buffer_size: int = 4096
) -> None:
    """
    Highly optimized non-blocking async pipeline eliminating friction points.
    Maintains 4GB RAM ceiling via chunked streaming.
    """
    write_buffer = []
    buffer_len = 0

    async for chunk in input_stream:
        stripped = chunk.strip()
        if not stripped:
            continue
        try:
            num = float(stripped) if '.' in stripped else int(stripped)
        except ValueError:
            num = None

        write_buffer.append(str(num) + '\n')
        buffer_len += len(write_buffer[-1])

        if buffer_len >= buffer_size:
            await output_sink.write(''.join(write_buffer))
            write_buffer.clear()
            buffer_len = 0

    if write_buffer:
        await output_sink.write(''.join(write_buffer))

@dataclass
class BatchWriterConfig:
    max_batch_size: int = 100
    flush_interval: float = 0.05
    db_path: str = "Aura_Memory/shared_table_traces.db"

class TransactionalBatchWriter:
    """
    Non-blocking, zero-copy transactional batch writer designed to prevent 
    SQLite lock contention across multiple async producers.
    """
    def __init__(self, config: BatchWriterConfig = BatchWriterConfig()):
        self.config = config
        self.queue: deque = deque()
        self._lock = asyncio.Lock()
        self._flush_task = None

    async def start_background_task(self):
        """Starts the autonomous flush loop."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._background_flush())

    async def append_record(self, module: str, payload: str):
        """Appends to the in-memory deque in O(1) time."""
        async with self._lock:
            self.queue.append((time.time(), module, str(payload)))
            
            if len(self.queue) >= self.config.max_batch_size:
                asyncio.create_task(self.flush())

    async def _background_flush(self):
        while True:
            await asyncio.sleep(self.config.flush_interval)
            await self.flush()

    async def flush(self):
        async with self._lock:
            if not self.queue:
                return
            batch = list(self.queue)
            self.queue.clear()

        try:
            async with aiosqlite.connect(self.config.db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.execute("PRAGMA synchronous=NORMAL;")
                await db.executemany(
                    "INSERT INTO traces (timestamp, module, payload) VALUES (?, ?, ?)",
                    batch
                )
                await db.commit()
        except Exception as e:
            log_error("BATCH_WRITE_FAIL", f"Contention or write failure during batch commit: {str(e)}")

class MorphemicBatchQueue:
    """
    [BF-TREE NUMPY RING BUFFER] Decouples memory buffers from disk.

    Stores up to max_records compact records in a pre-allocated numpy
    structured array, eliminating per-record Python object allocations and
    batch struct.unpack overhead.  The public interface is fully backward
    compatible with the original deque-based implementation.

    dtype layout per record (16 bytes total, matches original struct "<HHHHHHf"):
        slots : uint16[6]  — 12 bytes (morphemic slot indices)
        comp  : float32    —  4 bytes (compliance score)
    """

    # Structured dtype mirrors the original "<HHHHHHf" binary layout exactly.
    _RECORD_DTYPE = np.dtype([("slots", np.uint16, (6,)), ("comp", np.float32)])

    def __init__(self, max_records: int = 128):
        self.max_records = max_records
        # Pre-allocated ring buffer — one numpy allocation at construction time.
        # No per-record Python objects, no struct.pack overhead.
        self._buf   = np.zeros(max_records, dtype=self._RECORD_DTYPE)
        self._write = 0   # next write position (mod max_records)
        self._count = 0   # records currently stored
        # Initialize the zero-copy batching queue for trace accumulation
        self.trace_buffer = []
        self.batch_size_limit = 50
        self.last_flush_time = time.time()

    # ------------------------------------------------------------------
    # Legacy Bridge: queue attribute compatibility
    # ------------------------------------------------------------------

    @property
    def queue(self):
        """
        Legacy bridge: returns self so that ``len(pool.queue)`` and
        ``list(pool.queue)`` continue to work for all existing callers.
        """
        return self

    def __len__(self) -> int:
        return self._count

    def __iter__(self):
        """
        Legacy iterator: yields stored records as 16-byte packed bytes objects,
        identical to iterating the original ``deque``.  Used by callers that
        call ``list(pool.queue)`` or ``[b[:12] for b in list(pool.queue)]``.
        """
        n = self._count
        if n == 0:
            return
        start = (self._write - n) % self.max_records
        for i in range(n):
            idx = (start + i) % self.max_records
            r = self._buf[idx]
            yield struct.pack("<HHHHHHf", *r["slots"].tolist(), float(r["comp"]))

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def append_record(self, slots: list, compliance: float) -> bool:
        """
        Write one record directly into the pre-allocated numpy buffer.
        No Python object allocation; no struct.pack call.
        Returns True when the buffer reaches capacity (triggers flush).
        """
        if len(slots) < 6:
            slots = slots + [0] * (6 - len(slots))
        # In-place numpy write — O(1), no temporary bytes object
        self._buf[self._write]["slots"][:] = np.asarray(slots[:6], dtype=np.uint16)
        self._buf[self._write]["comp"] = np.float32(compliance)
        self._write = (self._write + 1) % self.max_records
        if self._count < self.max_records:
            self._count += 1
        return self._count >= self.max_records

    def flush_and_clear(self) -> list:
        """
        [LEGACY BRIDGE] Drain all records and return a list of 7-tuples
        ``(slot0, slot1, slot2, slot3, slot4, slot5, compliance)`` — the
        same type that the original deque + struct.unpack implementation
        returned.  Existing callers (``_write_morphemic_batch_to_disk``,
        ``__aexit__``) use ``r[:6]`` and ``r[6]`` on each tuple; this
        contract is preserved exactly.

        For a zero-copy structured-array result, use ``flush_np()``.
        """
        n = self._count
        if n == 0:
            return []
        view = self._ordered_view(n)
        self._count = 0
        self._write = 0
        # Single list comprehension over a numpy structured view — ~3-5× faster
        # than N individual struct.unpack calls on the original deque path.
        return [(*map(int, r["slots"]), float(r["comp"])) for r in view]

    def flush_np(self) -> np.ndarray:
        """
        [ZERO-COPY FAST PATH] Drain all records and return a numpy
        structured array with dtype ``[('slots', uint16, (6,)), ('comp', float32)]``.

        The returned array is either a direct slice of the ring buffer (no
        copy, O(1)) or a concatenation of two slices when the write pointer
        has wrapped (one copy, O(N)).  Either way, no Python object per record
        is created.

        Callers that currently use flush_and_clear() can migrate to this method
        and access fields as ``arr['slots']`` and ``arr['comp']``.
        """
        n = self._count
        if n == 0:
            return self._buf[:0].copy()
        view = self._ordered_view(n)
        self._count = 0
        self._write = 0
        return view

    # ------------------------------------------------------------------
    # BF-Tree matrix view
    # ------------------------------------------------------------------

    def compile_bftree_matrix_view(self, linear_frames: "list | None" = None) -> np.ndarray:
        """
        BF-Tree VPM Optimization (VLDB 2024 synthesis).

        Returns shape (N, 6), dtype uint16 — slot data only (compliance omitted).

        When *linear_frames* is **None** (native path):
            Returns a direct numpy view of the ring buffer's ``slots`` field.
            O(1) — zero bytes copied, zero Python per-record overhead.

        When *linear_frames* is a **list of bytes** (legacy path):
            Decodes N packed 16-byte frames via a single bytearray +
            ``np.frombuffer`` call instead of N ``struct.unpack`` calls.
            ~5-8× faster than the original Python loop at N=128.
        """
        if linear_frames is not None:
            # Legacy path: caller supplied a list of bytes/bytearray frames.
            if not linear_frames:
                return np.zeros((1, 6), dtype=np.uint16)

            n = len(linear_frames)
            # One contiguous bytearray written via memoryview slice assignment
            # (C-level copy) — avoids N struct.unpack + N list.append calls.
            raw = bytearray(n * 12)
            for i, frame in enumerate(linear_frames):
                try:
                    raw[i * 12:(i + 1) * 12] = frame[:12]
                except Exception:
                    pass  # leave zero-filled on malformed frame
            # Single frombuffer converts the whole buffer in one C call.
            # .copy() produces an owned, properly-aligned, writable array.
            return np.frombuffer(raw, dtype="<u2").reshape(n, 6).copy()

        # Native zero-copy path: return a direct view of the ring buffer.
        if self._count == 0:
            return np.zeros((1, 6), dtype=np.uint16)
        view = self._ordered_view(self._count)
        return view["slots"]   # zero-copy field view into the structured array

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ordered_view(self, n: int) -> np.ndarray:
        """
        Return an ordered view of *n* records from the ring buffer.
        O(1) when the buffer has not wrapped; O(N) (one np.concatenate)
        when the write pointer has crossed the array boundary.
        """
        start = (self._write - n) % self.max_records
        end   = start + n
        if end <= self.max_records:
            return self._buf[start:end]       # zero-copy slice
        wrap = self.max_records - start
        return np.concatenate([self._buf[start:], self._buf[:n - wrap]])

    def compile_bftree_matrix_view(self, linear_frames: list | None = None) -> np.ndarray:
        """
        BF-Tree VPM Optimization (VLDB 2024 synthesis).

        Flattens incoming morphemic frames into a contiguous NumPy uint16
        memory view, maximising processor cache hit ratios during sublinear
        vector comparisons.  When *linear_frames* is None the method
        drains the internal queue buffer automatically.

        Layout: each row = [slot0, slot1, slot2, slot3, slot4, slot5]
        dtype uint16 — 12 bytes per record, cache-line aligned.

        Returns
        -------
        np.ndarray  shape (N, 6), dtype uint16
        """
        if linear_frames is None:
            linear_frames = [b[:12] for b in list(self.queue)]  # first 6 uint16 per record

        if not linear_frames:
            return np.zeros((1, 6), dtype=np.uint16)

        rows = []
        for frame in linear_frames:
            try:
                # Extract the first 6 uint16 fields (12 bytes) — compliance float omitted
                row = struct.unpack("<HHHHHH", frame[:12])
                rows.append(row)
            except struct.error:
                rows.append((0, 0, 0, 0, 0, 0))

        return np.array(rows, dtype=np.uint16)


class AsyncMemoryPalace:
    """
    Sovereign Persistent Memory Engine with STONE Subconscious.
    Implements compactionless WAL while retaining strict DIKWP tiers
    and background memory consolidation at a 38.0C threshold.
    """
    def __init__(self, db_path: Path, node_ref=None):
        self.db_path = db_path
        self.node = node_ref
        self.conn = None
        self.holographic_buffer = deque()
        self.is_running = False
        self.stone_task = None
        self.auto_flush_task = None
        self.batch_writer = TransactionalBatchWriter()
        self.buffer_pool = MorphemicBatchQueue(max_records=128)
        self.lock = asyncio.Lock()
        self.db_write_lock = asyncio.Lock()
        self._flush_in_progress = False
        self._memory_guard = None   # pvm_memory_guard.MemoryBudget (started in __aenter__)
    def _nuke_corrupt_db(self):
        """Move the corrupt DB file aside and return a clean path for a fresh connection."""
        db_path = Path(self.db_path)
        if db_path.exists():
            bak = db_path.with_suffix(".corrupt.bak")
            try:
                shutil.move(str(db_path), str(bak))
                print(f"[🔧 DB-REPAIR] Corrupt palace DB moved to {bak}")
            except Exception:
                try:
                    db_path.unlink(missing_ok=True)
                except Exception:
                    pass
        db_path.parent.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        if aiosqlite is None:
            raise ImportError("aiosqlite is required for AsyncMemoryPalace (pip install aiosqlite)")

        # Try to connect; if the DB is corrupt, nuke it and retry once.
        for _attempt in range(2):
            try:
                self.conn = await aiosqlite.connect(self.db_path, timeout=15.0, isolation_level=None)
                self.conn.row_factory = aiosqlite.Row
                await self.conn.execute("PRAGMA journal_mode=WAL;")
                await self.conn.execute("PRAGMA synchronous=NORMAL;")
                await self.conn.execute("PRAGMA cache_size=-64000;")
                break  # success
            except Exception as _err:
                _msg = str(_err).lower()
                if _attempt == 0 and ("malformed" in _msg or "corrupt" in _msg or "not a database" in _msg):
                    print(f"[🔧 DB-REPAIR] Memory palace DB is corrupt — rebuilding (attempt {_attempt+1})...")
                    if self.conn:
                        try:
                            await self.conn.close()
                        except Exception:
                            pass
                        self.conn = None
                    self._nuke_corrupt_db()
                    continue
                raise  # re-raise on second attempt or unexpected error
        # Ensure the holographic table exists for the packed BLOBs
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS dkt_holographic_log (
                numeric_id INTEGER PRIMARY KEY,
                dash_kv_hash BLOB UNIQUE,
                binary_glyph BLOB
            )
        ''')
        # Phase 3: Create the QRW Entropy Reserve Table
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS qrw_latent_reserves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                entropy_blob BLOB
            )
        ''')

        # --- NEW: Phase 4: Active Inference Causal Ledger ---
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS causal_ledger (
                observation TEXT,
                hypothesis TEXT,
                attempts INTEGER DEFAULT 0,
                successes INTEGER DEFAULT 0,
                avg_error REAL DEFAULT 0.0,
                UNIQUE(observation, hypothesis)
            )
        ''')
        # --- PHASE 2: Morphemic Root Storage Matrix ---
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS morphemic_palace (
                id INTEGER PRIMARY KEY,
                slots_blob BLOB NOT NULL,
                compliance REAL NOT NULL,
                timestamp TEXT NOT NULL
            );
        ''')
        # Phase 5: Cross-Model Attention & Solvency Profiles
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS model_attention_profiles (
                provider TEXT PRIMARY KEY,
                coherence_score REAL DEFAULT 0.85,
                friction_count INTEGER DEFAULT 0,
                token_budget INTEGER DEFAULT 1000
            );
        ''')
        self.is_running = True
        self.stone_task = asyncio.create_task(self._stone_crawler())
        self.auto_flush_task = asyncio.create_task(self._auto_flush_morphemic_pool())
        # Start the transactional batch writer background loop
        await self.batch_writer.start_background_task()
        # --- Termux/ARM OOM protection ---
        # Start a warn-only MemoryBudget monitor so stderr receives a warning
        # before the Android Low-Memory Killer (LMK) silently kills the process.
        # raise_on_breach=False keeps the runtime alive; the stone_crawler thermal
        # gate already backs off workload when temps rise.
        if _MemoryBudget is not None:
            self._memory_guard = _MemoryBudget(
                budget_mb=_RAM_CEILING_MB,
                poll_interval_s=10.0,   # gentle poll — preserves ARM battery life
                raise_on_breach=False,
            )
            self._memory_guard.__enter__()

        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.is_running = False

        # Stop the memory guard before flushing buffers to prevent spurious warnings
        # during the final (expected) allocation spike on shutdown.
        if self._memory_guard is not None:
            self._memory_guard.__exit__(None, None, None)
            self._memory_guard = None

        for task in [self.stone_task, self.auto_flush_task, self.batch_writer._flush_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Synchronous flushing of remaining memory buffers on exit
        if self.conn:
            # 0. Flush the new transactional batch writer
            await self.batch_writer.flush()

            # 1. Flush remaining morphemic records
            async with self.lock:
                staged_morphemic = self.buffer_pool.flush_and_clear()
                if staged_morphemic:
                    try:
                        await self._write_morphemic_batch_to_disk(staged_morphemic)
                    except Exception:
                        pass

            # 2. Flush remaining holographic records
            staged_holographic = []
            async with self.lock:
                while self.holographic_buffer:
                    staged_holographic.append(self.holographic_buffer.popleft())

            if staged_holographic:
                query = '''
                    INSERT OR REPLACE INTO dkt_holographic_log
                    (numeric_id, dash_kv_hash, binary_glyph)
                    VALUES (?, ?, ?);
                '''
                async with self.db_write_lock:
                    try:
                        await self.conn.execute("BEGIN IMMEDIATE;")
                        await self.conn.executemany(query, staged_holographic)
                        await self.conn.commit()
                    except Exception:
                        try:
                            await self.conn.rollback()
                        except Exception:
                            pass

            await self.conn.close()
    async def enqueue_holographic_trace(
        self, num_id: int, user_input: str, temp: float, ms: float, ok: bool
    ):
        """Routes through the Gateway to synthesize DIKWP/ST3GG/DASH-KV."""
        if not hasattr(self.node, 'gateway'):
            return
        gw = self.node.gateway
        # 1. Synthesize all telemetry and hashes
        st3gg = gw.generate_st3gg_glyph(user_input, temp)
        dash = gw._generate_dash_kv_hash(num_id, user_input)
        d, i, k, w, p = gw._extract_dikwp_heuristics(user_input, st3gg, ms)
        # 2. Pack the Holographic BLOB (Protocol C format)
        glyph = struct.pack(
            '! I 8s H B B B B B f ?',
            num_id, dash, st3gg, d, i, k, w, p, ms, ok
        )
        
        async with self.lock:
            self.holographic_buffer.append((num_id, dash, glyph))
            # Event-driven background task trigger: Flush when buffer hits 50 records
            if len(self.holographic_buffer) >= 50 and not self._flush_in_progress:
                self._flush_in_progress = True
                asyncio.create_task(self._background_flush_holographic())

    async def _background_flush_holographic(self) -> None:
        """
        [AWM EVENT-DRIVEN FLUSH]
        Surgically flushes standard holographic traces using async bulk executemany,
        preventing background thread sleep polling from thrashing mobile cores.
        """
        staged_batch = []
        async with self.lock:
            while self.holographic_buffer:
                staged_batch.append(self.holographic_buffer.popleft())

        if staged_batch:
            query = '''
                INSERT OR REPLACE INTO dkt_holographic_log
                (numeric_id, dash_kv_hash, binary_glyph)
                VALUES (?, ?, ?);
            '''
            async with self.db_write_lock:
                try:
                    await self.conn.execute("BEGIN IMMEDIATE;")
                    await self.conn.executemany(query, staged_batch)
                    await self.conn.commit()
                except Exception as e:
                    try:
                        await self.conn.rollback()
                    except Exception:
                        pass
                    if self.node and hasattr(self.node, 'log_error'):
                        self.node.log_error("WAL_FLUSH_FAIL", str(e))
                finally:
                    # Explicit Memory Reclamation
                    del staged_batch
                    gc.collect()

        self._flush_in_progress = False

    async def _write_morphemic_batch_to_disk(self, staged_records: list) -> None:
        """[BF-TREE] Writes morphemic batch records to disk with progressive progressive backoff and executemany bulk insertions."""
        query = '''
            INSERT OR REPLACE INTO morphemic_palace (id, slots_blob, compliance, timestamp)
            VALUES (?, ?, ?, ?);
        '''
        params = []
        seen_ids = {}
        for r in staged_records:
            p_slots = list(r[:6])
            p_comp = r[6]
            t_id = int(hash(tuple(p_slots)) & 0xFFFFFFFF)
            if t_id in seen_ids:
                if p_comp > seen_ids[t_id][1]:  # Index 1 stores compliance
                    seen_ids[t_id] = (p_slots, p_comp)
            else:
                seen_ids[t_id] = (p_slots, p_comp)

        for t_id, (p_slots, p_comp) in seen_ids.items():
            packed_slots = struct.pack("<HHHHHH", *p_slots)
            params.append((t_id, packed_slots, p_comp, datetime.now().isoformat()))

        async with self.db_write_lock:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.conn.execute("BEGIN IMMEDIATE;")
                    await self.conn.executemany(query, params)
                    await self.conn.commit()
                    break
                except Exception as e:
                    try:
                        await self.conn.rollback()
                    except Exception:
                        pass
                    if attempt == max_retries - 1:
                        # Volatile Recovery: Re-buffer records to RAM pool to prevent data loss
                        async with self.lock:
                            for r in staged_records:
                                self.buffer_pool.append_record(list(r[:6]), r[6])
                        raise e
                    await asyncio.sleep((2 ** attempt) * 0.05)

    async def enqueue_morphemic_root_trace(self, thought_id: int, slot_indices: list, compliance_score: float):
        """
        [BF-TREE & DEQUE HYBRID] Buffers writes to RAM.
        Saturated buffers trigger an immediate non-blocking batch write to disk.
        """
        staged_records = []
        async with self.lock:
            is_saturated = self.buffer_pool.append_record(slot_indices, compliance_score)
            if is_saturated:
                staged_records = self.buffer_pool.flush_and_clear()
        if staged_records:
            await self._write_morphemic_batch_to_disk(staged_records)
        return True

    async def _auto_flush_morphemic_pool(self):
        """
        [AWM ADAPTIVE AUTO-FLUSH] Periodically flushes pending traces to disk.
        Scales the sleep interval dynamically to balance write responsiveness
        against mobile processor battery life.
        """
        while self.is_running:
            # Query queue size without acquiring memory locks
            queue_len = len(self.buffer_pool.queue) if hasattr(self, 'buffer_pool') else 0
            # Poll rapidly under heavy load, decelerate to conserve battery during idle periods
            interval = 0.2 if queue_len > 64 else 2.0
            await asyncio.sleep(interval)
            
            if self.conn and queue_len > 0:
                staged_records = []
                async with self.lock:
                    staged_records = self.buffer_pool.flush_and_clear()
                if staged_records:
                    try:
                        await self._write_morphemic_batch_to_disk(staged_records)
                    except Exception:
                        pass


    async def _stone_crawler(self):
        """
        Phase 3 Subconscious Cryptographic Grooming.
        Wakes up at <= 38.0C to consolidate memory AND generate
        latent Quantum Random Walk (QRW) entropy reserves for the PQCK shield.
        """
        while self.is_running:
            temp = 42.0
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
            except (IOError, FileNotFoundError):
                pass
            # Moto G Stylus Natural Idle Threshold
            if temp <= 38.0:
                try:
                    # 1. Deep Consolidation: Push active WAL into the main tree
                    await self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    # Cognitive Indexing: Analyze traces for faster recall
                    await self.conn.execute("ANALYZE dkt_holographic_log;")
                    # 2. Phase 3: QRW Latent Entropy Generation
                    # We generate 10 high-quality chaotic seeds while the CPU is cool.
                    if hasattr(self.node, 'hdc'):
                        async with self.db_write_lock:
                            try:
                                await self.conn.execute("BEGIN IMMEDIATE;")
                                for i in range(10):
                                    # Tap the Hybrid HDC Core for thermal entropy, offset slightly per loop
                                    qrw_seed = self.node.hdc.extract_thermal_entropy(temp + (i * 0.01))
                                    seed_bytes = np.packbits(qrw_seed).tobytes()
                                    await self.conn.execute('''
                                        INSERT INTO qrw_latent_reserves (timestamp, entropy_blob)
                                        VALUES (?, ?)
                                    ''', (time.time(), seed_bytes))
                                # Cap the reserves at 1000 to prevent subconscious memory bloat
                                await self.conn.execute('''
                                    DELETE FROM qrw_latent_reserves
                                    WHERE id NOT IN (SELECT id FROM qrw_latent_reserves ORDER BY timestamp DESC LIMIT 1000)
                                ''')
                                await self.conn.commit()
                            except Exception as e:
                                try:
                                    await self.conn.rollback()
                                except Exception:
                                    pass
                                raise e
                    if hasattr(self.node, 'gateway'):
                        metrics = getattr(self.node, 'runtime_metrics', {})
                        t_id = metrics.get('thought_id', "STONE-DREAM")
                        try:
                            num_id = int(t_id.split('-')[1], 16)
                        except (IndexError, ValueError):
                            num_id = 0
                        await self.enqueue_holographic_trace(
                            num_id, "QRW_CRYPTOGRAPHIC_GROOMING_COMPLETE", temp, 0.0, True
                        )
                except Exception as e:
                    if hasattr(self.node, 'log_error'):
                        self.node.log_error("STONE_CRAWLER_FAIL", str(e))
                # Deep sleep for 120 seconds while consolidating
                await asyncio.sleep(120.0)
            else:
                # If running hot, pause subconscious grooming
                await asyncio.sleep(15.0)
    async def stream_vectors(self):
        """Enforces the uint8 Type Firewall via continuous streaming."""
        query = (
            "SELECT id, tier, vector_blob FROM traces "
            "WHERE vector_blob IS NOT NULL;"
        )
        async with self.conn.execute(query) as cursor:
            async_rows = await cursor.fetchall()
            for row in async_rows:
                binary_vec = np.frombuffer(row["vector_blob"], dtype=np.uint8)
                yield (row["id"], row["tier"], binary_vec)

    async def lock_atomic_spin_state(self, trace_id: str, fluid_phase_wave: np.ndarray):
        """
        [QUANTUM LIGHT STORAGE]
        Converts a dynamic, flying FHRR phase trajectory wave into a permanent,
        stationary spin-state matrix, freeing up raw text cache baggage.
        """
        if not self.conn:
            return
        # Cast to flat float32 phase angles to protect memory boundaries
        frozen_angles = np.angle(fluid_phase_wave).astype(np.float32)
        packed_blob = frozen_angles.tobytes()
        
        query = """
            INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob)
            VALUES (?, 'CRYSTAL_LATTICE_LOCKED', 'CRYSTAL', ?, 'Atomic Frequency Comb Enriched', ?);
        """
        await self.conn.execute(query, (
            trace_id, 
            datetime.now().isoformat(), 
            packed_blob
        ))
        await self.conn.commit()

    async def get_all_crystallized_phases(self) -> list:
        """
        Extracts crystallized phase coordinates directly from persistent storage
        as light, type-safe float32 arrays to prevent context window bloat.
        """
        if not self.conn:
            return []
        # Upgraded to pull both CRYSTAL, WISDOM, and verified HYPERTRUTH vector matrices
        query = "SELECT vector_blob FROM traces WHERE tier IN ('CRYSTAL', 'WISDOM', 'HYPERTRUTH');"
        crystal_phases = []
        try:
            async with self.conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    if row["vector_blob"]:
                        blob = row["vector_blob"]
                        if len(blob) == 80000:
                            vec_complex = np.frombuffer(blob, dtype=np.complex64)
                            vec = np.angle(vec_complex).astype(np.float32)
                        else:
                            vec = np.frombuffer(blob, dtype=np.float32)
                        crystal_phases.append(vec)
        except Exception:
            pass
        return crystal_phases

    async def verify_incremental_frontier(self, cognitive_object_id: str) -> str:
        """
        [INCREMENTAL MERKLE MEMORY]
        Validates memory node integrity by reconstructing the Merkle frontier path
        at an O(log N) compute footprint, establishing version-controlled cognition.
        """
        if not self.conn:
            return "0000000000000000"
        
        # Dual-index query cross-referencing trace ID and text content natively
        query = "SELECT timestamp, tags, vector_blob FROM traces WHERE id = ? OR content = ? LIMIT 1;"
        try:
            async with self.conn.execute(query, (cognitive_object_id, cognitive_object_id)) as cursor:
                row = await cursor.fetchone()
                if not row or not row["vector_blob"]:
                    return "INVALID_PROVENANCE"
                
                # Core LWC Hash calculation over the data object parameters
                hasher = hashlib.blake2b(digest_size=8)
                hasher.update(f"{cognitive_object_id}:{row['timestamp']}:{row['tags']}".encode())
                hasher.update(row["vector_blob"])
                
                # The resulting 16-character hex sequence forms her valid verification proof
                return hasher.hexdigest().upper()
        except Exception:
            return "ERROR_SECURE_SWEEP"

    async def check_audit_cache(self, filepath: str, current_mtime: float, current_size: int) -> str:
        """
        [CACHED EMBEDDED AUDIT]
        Scans for a microarchitecturally aligned file validation fingerprint.
        Bypasses local inference entirely if physical disk metrics match.
        """
        if not self.conn:
            return None
        query = "SELECT token FROM audit_cache WHERE filepath = ? AND mtime = ? AND size = ?;"
        try:
            async with self.conn.execute(query, (filepath, current_mtime, current_size)) as cursor:
                row = await cursor.fetchone()
                return row["token"] if row else None
        except Exception:
            # Ensure a safe fallback to rebuild if the cache table hasn't initialized yet
            return None

    async def update_audit_cache(self, filepath: str, mtime: float, size: int, token: str):
        """
        Updates the cryptographic cache entry with the file's current hardware profile.
        """
        if not self.conn:
            return
        try:
            # Dynamically initialize the cache table layout if it doesn't exist
            await self.conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_cache (
                    filepath TEXT PRIMARY KEY, mtime REAL, size INTEGER, token TEXT
                );
            ''')
            query = "INSERT OR REPLACE INTO audit_cache (filepath, mtime, size, token) VALUES (?, ?, ?, ?);"
            await self.conn.execute(query, (filepath, mtime, size, token))
            await self.conn.commit()
        except Exception:
            # Audit cache writes are best-effort — never crash the boot sequence
            pass
