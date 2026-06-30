"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:HDC_PROBE_BRIDGE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Explanability)
DEPENDENCIES: __future__, math, typing
FUNCTIONS: AuraHyperdimensionalProbeBridge, bind_concept, decode_vector
SYNOPSIS: Binds high-dimensional vector representations to semantic labels using VSA cosine similarity.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple


class AuraHyperdimensionalProbeBridge:
    """
    Decodes high-dimensional phasor/VSA vectors into human-interpretable labels
    via cosine similarity scoring, providing explainable semantic alignment.
    """

    def __init__(self):
        self.codebook: Dict[str, List[float]] = {}

    def bind_concept(self, label: str, vector: List[float]) -> None:
        """Registers a concept vector signature in the VSA codebook."""
        self.codebook[label] = vector

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculates cosine similarity between two float vectors."""
        if len(v1) != len(v2) or not v1:
            return 0.0
        dot_product = sum(x * y for x, y in zip(v1, v2))
        magnitude_v1 = math.sqrt(sum(x * x for x in v1))
        magnitude_v2 = math.sqrt(sum(y * y for y in v2))
        if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
            return 0.0
        return dot_product / (magnitude_v1 * magnitude_v2)

    def decode_vector(self, vector: List[float]) -> Tuple[str, float]:
        """Decodes an active vector to find the closest matching semantic label."""
        best_label = "UNKNOWN"
        best_score = -1.0

        for label, concept_vector in self.codebook.items():
            sim = self.cosine_similarity(vector, concept_vector)
            if sim > best_score:
                best_score = sim
                best_label = label

        return best_label, round(best_score, 4)
