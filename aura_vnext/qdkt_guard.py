"""Non-authoritative QDKT projection for AuraOS vNext.

The historical repo's ``aura_qdkt.py`` can auto-crystallize after repeated high
confidence observations. Current Aura governance requires the opposite boundary:
QDKT estimates knowledge/readiness/usefulness; it does not mint truth, authority,
or crystallization. This module defines the vNext contract without deleting the
historical implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Iterable


@dataclass(frozen=True, slots=True)
class QDKTObservation:
    concept: str
    event_type: str
    usefulness: float
    confidence: float
    source_generation: str
    source_ref: str
    verifier: str = "UNKNOWN"
    independent: bool = False
    invalidators: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QDKTState:
    concept: str
    readiness: float
    uncertainty: float
    independent_support: int
    observation_count: int
    source_generations: tuple[str, ...]
    reopen_required: bool
    status: str = "PROJECTION_ONLY"
    authority: bool = False
    crystallized: bool = False
    promotion_allowed: bool = False
    digest: str = ""


class QDKTGuardedProjection:
    """Compute a bounded epistemic projection; never promote or authorize."""

    def project(
        self,
        concept: str,
        observations: Iterable[QDKTObservation],
        *,
        current_source_generation: str,
    ) -> QDKTState:
        relevant = [item for item in observations if item.concept == concept]
        if not relevant:
            return self._seal(QDKTState(
                concept=concept,
                readiness=0.0,
                uncertainty=1.0,
                independent_support=0,
                observation_count=0,
                source_generations=(),
                reopen_required=True,
            ))

        current = [item for item in relevant if item.source_generation == current_source_generation]
        stale = len(current) != len(relevant)
        if not current:
            return self._seal(QDKTState(
                concept=concept,
                readiness=0.0,
                uncertainty=1.0,
                independent_support=0,
                observation_count=len(relevant),
                source_generations=tuple(sorted({item.source_generation for item in relevant})),
                reopen_required=True,
            ))

        # Geometric-like confidence aggregation is intentionally conservative;
        # repeated correlated observations do not count as independent evidence.
        weighted = []
        independent_keys: set[tuple[str, str]] = set()
        for item in current:
            usefulness = min(1.0, max(0.0, float(item.usefulness)))
            confidence = min(1.0, max(0.0, float(item.confidence)))
            verifier_factor = 1.0 if item.verifier == "PASS" else 0.6 if item.verifier == "UNKNOWN" else 0.0
            weighted.append(usefulness * confidence * verifier_factor)
            if item.independent and item.verifier == "PASS":
                independent_keys.add((item.source_ref, item.event_type))

        readiness = sum(weighted) / len(weighted)
        # Penalize a single correlated lineage. This is routing/readiness only.
        independence = len(independent_keys)
        if independence == 0:
            readiness *= 0.65
        elif independence == 1:
            readiness *= 0.85
        uncertainty = min(1.0, max(0.0, 1.0 - readiness))
        invalidated = any(item.invalidators for item in current)
        return self._seal(QDKTState(
            concept=concept,
            readiness=round(readiness, 6),
            uncertainty=round(uncertainty, 6),
            independent_support=independence,
            observation_count=len(relevant),
            source_generations=tuple(sorted({item.source_generation for item in relevant})),
            reopen_required=stale or invalidated or readiness < 0.75,
        ))

    @staticmethod
    def _seal(state: QDKTState) -> QDKTState:
        data = asdict(state)
        data["digest"] = ""
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        digest = hashlib.sha256(payload).hexdigest()
        return QDKTState(**{**data, "digest": digest})
