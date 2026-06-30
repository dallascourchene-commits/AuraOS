"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:LUMINANCE_ENGINE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Visual Grounding)
DEPENDENCIES: __future__, aura_scene_graph_schema
FUNCTIONS: LuminanceEngine, compute
SYNOPSIS: Computes node brightness based on validation metrics and clamps it to zero if grounding is missing.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from aura_scene_graph_schema import SceneNode


class LuminanceEngine:
    """
    Computes node visual brightness (luminance) based on verification metrics.
    Ungrounded or structurally broken nodes are clamped strictly to 0.0.
    """

    @staticmethod
    def clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    @classmethod
    def compute(cls, node: SceneNode) -> float:
        """
        Calculates node brightness based on verification parameters.
        Enforces physical isolation by clamping to 0.0 if grounding vectors are missing.
        """
        if node.source_grounding_score <= 0.0 or node.missing_symbol_penalty > 0.0:
            return 0.0

        # Core System Truth (75% weight mass)
        truth = (
            0.30 * node.verifier_pass_score
            + 0.25 * node.source_grounding_score
            + 0.15 * node.test_coverage_score
            + 0.15 * node.boundary_contract_completeness
        )

        # Optimization & Memory Boosts (15% weight mass)
        learning = (
            0.075 * node.dream_usefulness
            + 0.075 * node.qdkt_confidence
        )

        # Structural Penalty Metrics
        penalty = (
            0.30 * node.failure_penalty
            + 0.20 * node.stale_context_penalty
            + 0.15 * node.overcoupling_penalty
        )

        return round(cls.clamp01(truth + learning - penalty), 3)
