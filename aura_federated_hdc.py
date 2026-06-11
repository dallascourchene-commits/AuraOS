"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f1-[Q-SYS:FEDERATED_HDC_CORE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: asyncio, numpy, concurrent.futures, aura_core, async_palace, aura_validation
FUNCTIONS: ResourceEfficientFederatedHDC, HDCSubModel, FederatedHDCResult
SYNOPSIS: Resource-efficient federated HDC processor with pure asyncio.
          Integrates with AuraHyperdimensionalCore for 10,000-D VSA operations.
          Addresses DEEP_AUDIT_REPORT issues: ProcessPoolExecutor (not Thread),
          proper error handling, logging, and AsyncMemoryPalace persistence.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

# ── AuraOS native imports ────────────────────────────────────────────────────
from aura_core import AuraHyperdimensionalCore
from async_palace import AsyncMemoryPalace
from aura_validation import calculate_rubric_score

logger = logging.getLogger("aura.federated_hdc")


# ============================================================================
# Data containers
# ============================================================================

@dataclass
class HDCSubModel:
    """
    Resource-efficient HDC sub-model unit with AuraOS integration.

    Attributes
    ----------
    submodel_id   : unique identifier for tracking
    weights       : 10,000-D hypervector for this submodel
    dimensionality: dimensionality slice for federated operation
    dropout_rate  : stochastic dropout for regularisation
    """

    submodel_id: str
    weights: np.ndarray
    dimensionality: int
    dropout_rate: float = 0.2

    def __post_init__(self) -> None:
        if self.weights.shape[0] != 10000:
            raise ValueError(
                f"HDC weights must be 10,000-D, got {self.weights.shape}"
            )
        if self.dimensionality <= 0:
            raise ValueError(
                f"Dimensionality must be positive, got {self.dimensionality}"
            )


@dataclass
class FederatedHDCResult:
    """Result container for federated HDC operations."""

    final_weights: np.ndarray
    total_processed: int
    submodel_results: List[Dict[str, Any]]
    resonance_score: float
    processing_time_ms: float


# ============================================================================
# CPU-bound refinement (runs in a worker process — must be module-level)
# ============================================================================

def _refine_submodel_worker(
    weights: np.ndarray,
    submodel_id: str,
    dropout_rate: float,
    dimensionality: int,
    batch_len: int,
) -> Dict[str, Any]:
    """
    CPU-bound submodel refinement.  Runs in a ProcessPoolExecutor worker to
    avoid GIL contention.  Module-level so it is picklable.
    """
    import numpy as _np  # local import for worker process

    try:
        mask = _np.random.random(weights.shape) > dropout_rate
        refined = _np.where(mask, weights, 0.0)
        return {
            "submodel_id": submodel_id,
            "weights": refined,
            "dimensionality": dimensionality,
            "processed_count": batch_len,
            "weight_norm": float(_np.linalg.norm(refined)),
            "dropout_applied": float(dropout_rate),
        }
    except Exception as exc:
        return {
            "submodel_id": submodel_id,
            "error": str(exc),
            "processed_count": 0,
        }


# ============================================================================
# Main class
# ============================================================================

class ResourceEfficientFederatedHDC:
    """
    CLI-Anything aligned federated HDC processor with pure asyncio.

    Features
    --------
    - Pure asyncio architecture (no GIL contention)
    - ProcessPoolExecutor for CPU-bound work
    - Integration with AuraHyperdimensionalCore
    - AsyncMemoryPalace persistence (via db_path)
    - Comprehensive error handling and logging
    - Resource cleanup on shutdown

    Usage
    -----
        processor = ResourceEfficientFederatedHDC(submodel_count=4)
        await processor.initialize()
        await processor.start_background_task()
        await processor.shutdown()
    """

    def __init__(
        self,
        submodel_count: int = 4,
        base_dim: int = 10000,
        batch_size: int = 100,
        max_queue_size: int = 1000,
        db_path: str = "Aura_Memory/shared_table_traces.db",
    ) -> None:
        self.submodel_count = submodel_count
        self.base_dim = base_dim
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size
        self.db_path = db_path

        # AuraOS integrations
        self.hdc_core = AuraHyperdimensionalCore(dimensions=base_dim)

        # Async infrastructure
        self.batch_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.result_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown_event = asyncio.Event()

        # Process pool for CPU-bound work (not ThreadPoolExecutor)
        self._process_executor: Optional[ProcessPoolExecutor] = None

        # Submodels populated in initialize()
        self.submodels: List[HDCSubModel] = []

        # Metrics
        self.total_processed: int = 0
        self.total_errors: int = 0

        logger.info(
            "FederatedHDC init: submodels=%d  batch=%d  queue=%d",
            submodel_count,
            batch_size,
            max_queue_size,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialise submodels and process pool."""
        self._process_executor = ProcessPoolExecutor(
            max_workers=self.submodel_count
        )

        # Build approximate-orthogonal codebook via shared HDC core
        codebook = self.hdc_core.generate_orthogonal_codebook(
            size=self.submodel_count, dimensions=self.base_dim
        )

        self.submodels = []
        dim_slice = self.base_dim // self.submodel_count
        for i in range(self.submodel_count):
            sm = HDCSubModel(
                submodel_id=f"submodel_{i}",
                weights=codebook[i].astype(np.float32),
                dimensionality=dim_slice,
            )
            self.submodels.append(sm)
            logger.debug("Initialised %s", sm.submodel_id)

        logger.info("All %d submodels initialised", self.submodel_count)

    async def shutdown(self) -> None:
        """Graceful shutdown with resource cleanup."""
        logger.info("Shutting down FederatedHDC …")
        self._shutdown_event.set()

        if self._process_executor:
            self._process_executor.shutdown(wait=True)
            logger.info("Process pool shutdown complete")

        logger.info(
            "FederatedHDC done.  processed=%d  errors=%d",
            self.total_processed,
            self.total_errors,
        )

    # ------------------------------------------------------------------
    # Processing pipeline
    # ------------------------------------------------------------------

    async def _refine_submodel(
        self,
        submodel: HDCSubModel,
        batch: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Async wrapper — offloads CPU work to the process pool."""
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                self._process_executor,
                _refine_submodel_worker,
                submodel.weights,
                submodel.submodel_id,
                submodel.dropout_rate,
                submodel.dimensionality,
                len(batch),
            )
            return result
        except Exception as exc:
            logger.error("Process pool error for %s: %s", submodel.submodel_id, exc)
            return {"submodel_id": submodel.submodel_id, "error": str(exc), "processed_count": 0}

    async def _process_batch(
        self, batch: List[Dict[str, Any]]
    ) -> FederatedHDCResult:
        """Non-blocking batch processing with federated HDC refinement."""
        t0 = time.perf_counter()

        tasks = [self._refine_submodel(sm, batch) for sm in self.submodels]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        valid: List[Dict[str, Any]] = []
        for r in raw_results:
            if isinstance(r, Exception):
                logger.error("Submodel exception: %s", r)
                self.total_errors += 1
            elif "error" in r:
                logger.error("Submodel %s error: %s", r["submodel_id"], r["error"])
                self.total_errors += 1
            else:
                valid.append(r)

        if not valid:
            raise RuntimeError("All submodels failed for this batch")

        aggregated = self._aggregate_hdc_results(valid)
        resonance = calculate_rubric_score(
            context={
                "aggregated_vector": aggregated,
                "submodel_count": len(valid),
                "total_processed": sum(r["processed_count"] for r in valid),
                "weight_norms": [r["weight_norm"] for r in valid],
            }
        )

        # Persist to memory palace (best-effort)
        await self._store_trace(batch, aggregated, resonance, valid)

        processing_ms = (time.perf_counter() - t0) * 1000
        self.total_processed += len(batch)

        logger.info(
            "Batch done: items=%d  ok=%d/%d  resonance=%.4f  %.1fms",
            len(batch),
            len(valid),
            self.submodel_count,
            resonance,
            processing_ms,
        )

        return FederatedHDCResult(
            final_weights=aggregated,
            total_processed=len(batch),
            submodel_results=valid,
            resonance_score=resonance,
            processing_time_ms=processing_ms,
        )

    def _aggregate_hdc_results(
        self, results: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Aggregate submodel results using AuraOS HDC bundling + permutation.

        Each submodel's output is permuted (np.roll) then weighted-summed
        proportionally to its weight norm, then passed through tanh to bound
        the aggregate to [-1, 1].
        """
        total_norm = sum(r["weight_norm"] for r in results) or 1.0
        aggregated = np.zeros(self.base_dim, dtype=np.float32)
        for i, r in enumerate(results):
            shift = i * (self.base_dim // self.submodel_count)
            permuted = np.roll(r["weights"], shift)
            weight_factor = r["weight_norm"] / total_norm
            aggregated += permuted * weight_factor
        return np.tanh(aggregated)

    async def _store_trace(
        self,
        batch: List[Dict[str, Any]],
        aggregated: np.ndarray,
        resonance: float,
        results: List[Dict[str, Any]],
    ) -> None:
        """Persist batch trace to memory palace (non-fatal on failure)."""
        try:
            from pathlib import Path as _Path
            _Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.execute(
                    "CREATE TABLE IF NOT EXISTS traces "
                    "(id TEXT PRIMARY KEY, content TEXT, tier TEXT, "
                    "timestamp TEXT, tags TEXT, vector_blob BLOB);"
                )
                trace_id = f"FEDERATED_HDC_{int(time.time() * 1000)}"
                await db.execute(
                    "INSERT OR REPLACE INTO traces "
                    "(id, content, tier, timestamp, tags, vector_blob) "
                    "VALUES (?, ?, 'WISDOM', datetime('now'), 'federated_hdc', ?);",
                    (
                        trace_id,
                        f"batch_size={len(batch)} resonance={resonance:.4f}",
                        aggregated.tobytes(),
                    ),
                )
                await db.commit()
        except Exception as exc:
            logger.debug("Memory palace store skipped: %s", exc)

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    async def async_pipeline(
        self, input_stream: asyncio.Queue
    ) -> None:
        """
        Collect items into batches and enqueue for processing.

        Aligns with async_palace.py's async_pipeline pattern.
        """
        batch: List[Dict[str, Any]] = []
        while not self._shutdown_event.is_set():
            try:
                item = await asyncio.wait_for(input_stream.get(), timeout=0.1)
                batch.append(item)
                if len(batch) >= self.batch_size:
                    await self.batch_queue.put(batch)
                    batch = []
            except asyncio.TimeoutError:
                if batch:
                    await self.batch_queue.put(batch)
                    batch = []
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
        if batch:
            await self.batch_queue.put(batch)

    async def start_background_task(self) -> asyncio.Task:
        """Start the non-blocking background processing task."""

        async def _worker() -> None:
            while not self._shutdown_event.is_set():
                try:
                    batch = await self.batch_queue.get()
                    result = await self._process_batch(batch)
                    await self.result_queue.put(result)
                    self.batch_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Background worker error: %s", exc, exc_info=True)
                    self.batch_queue.task_done()

        task = asyncio.create_task(_worker())
        logger.info("FederatedHDC background worker started")
        return task
