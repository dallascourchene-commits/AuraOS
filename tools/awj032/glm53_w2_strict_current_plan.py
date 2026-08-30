"""Strict Different-J adapter over the current PR350 W2-bound pager-plan owner.

This adapter does not own a pager or a competing source-plan ABI. It composes the
current PR350 compiler with an independent W2 header validator that additionally
binds `data_offsets` span to dtype × shape byte geometry.
"""
from __future__ import annotations

from typing import Any, Mapping

from tools.awj032.glm53_layout_binding_bridge import compile_pager_source_plan
from tools.awj032.glm53_w2_header_bound_plan import compile_w2_header_bound_pager_source_plan


def compile_strict_current_w2_plan(
    report: Mapping[str, Any],
    *,
    weight_map: Mapping[str, str],
    header_evidence: Mapping[str, Any],
    expected_model_revision: str,
    expected_index_digest: str,
):
    """Return a strict wrapper around the current canonical PR350 per-expert plan."""

    def current_compile(
        current_report: Mapping[str, Any],
        *,
        weight_map: Mapping[str, str],
        headers,
        expected_model_revision: str,
        expected_index_digest: str,
    ):
        return compile_pager_source_plan(
            current_report,
            weight_map=weight_map,
            headers=headers,
            expected_model_revision=expected_model_revision,
            expected_index_digest=expected_index_digest,
            per_expert_header_evidence=header_evidence,
        )

    return compile_w2_header_bound_pager_source_plan(
        report,
        weight_map=weight_map,
        header_evidence=header_evidence,
        expected_model_revision=expected_model_revision,
        expected_index_digest=expected_index_digest,
        compile_fn=current_compile,
    )
