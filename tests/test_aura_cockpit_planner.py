"""Tests for Aura Cockpit Planner."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_cockpit_planner import (
    PATCH_AUTHORITY,
    compile_grounded_phase_capsules,
    objective_to_phase_capsules,
    phase_capsules_to_agent_runbook,
    phase_capsules_to_workflow_gates,
    plan_objective_with_goap,
)


def _grounding() -> dict:
    return {
        "version": "AURA_CODING_ARENA_GROUNDING_V1",
        "anchor_version": "TEST_ANCHOR",
        "grounding_ok": True,
        "route": "BUILDER_PATCH",
        "target_file": "aura_target.py",
        "target_symbol": "target_symbol",
        "source_spans": (
            {
                "node_id": "aura_target.py::target_symbol",
                "file_path": "aura_target.py",
                "line_range": (10, 20),
                "source_hash": "span-hash",
                "file_source_hash": "file-hash",
            },
        ),
        "tests": ("tests/test_target.py",),
        "hashes": {
            "aura_target.py::target_symbol": "span-hash",
            "aura_target.py": "file-hash",
        },
        "candidate_files": [{"path": "advisory_only.py"}],
        "route_reasons": ("exact_symbol_hit",),
        "safety_policy": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }


class TestGOAPPlan:
    def test_produces_phases(self):
        result = plan_objective_with_goap(
            "Refactor Fireworks egress", repo_root=REPO_ROOT
        )
        assert result["ok"] is True
        assert len(result["plan"]["phases"]) == 9

    def test_phase_has_required_fields(self):
        result = plan_objective_with_goap("test", repo_root=REPO_ROOT)
        for phase in result["plan"]["phases"]:
            assert "allowed_actions" in phase
            assert "blocked_actions" in phase
            assert "human_approval_required" in phase

    def test_invariants(self):
        result = plan_objective_with_goap("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestPhaseCapsules:
    def test_produces_legacy_capsules_unchanged(self):
        result = objective_to_phase_capsules("test", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["phase_capsules"]) == 9
        assert "grounding_evidence" not in result

    def test_grounded_capsules_preserve_exact_evidence_without_scope_expansion(self):
        grounding = _grounding()
        first = objective_to_phase_capsules(
            "Refactor target",
            repo_root=REPO_ROOT,
            grounding_packet=grounding,
        )
        second = objective_to_phase_capsules(
            "Refactor target",
            repo_root=REPO_ROOT,
            grounding_packet=grounding,
        )

        assert first == second
        assert first["ok"] is True
        assert len(first["phase_capsules"]) == 9
        evidence = first["grounding_evidence"]
        assert evidence["allowed_files"] == ["aura_target.py"]
        assert "advisory_only.py" not in evidence["allowed_files"]
        assert evidence["source_spans"][0]["line_range"] == [10, 20]
        assert evidence["source_hashes"] == grounding["hashes"]
        assert evidence["required_tests"] == ["tests/test_target.py"]
        assert all(
            capsule["grounding_evidence_id"]
            == first["grounding_evidence_id"]
            for capsule in first["phase_capsules"]
        )
        accounting = first["context_cost_accounting"]
        assert accounting["classification"] == "PROJECTED_STRUCTURAL_TOKEN_PROXY"
        assert accounting["measurement_class"] == "ESTIMATED"
        assert accounting["provider_reported"] is False
        assert accounting["tokenizer_exact"] is False
        assert (
            accounting["repeated_evidence_counterfactual_token_proxy"]
            > accounting["shared_evidence_total_token_proxy"]
        )
        assert accounting["avoided_token_proxy"] > 0
        assert accounting["projected_savings_percent"] > 0

    @pytest.mark.parametrize(
        ("packet", "error"),
        [
            ("not-a-packet", "grounding_packet_must_be_a_mapping"),
            ({**_grounding(), "grounding_ok": False}, "grounding_not_admitted"),
            ({**_grounding(), "source_spans": []}, "exact_source_spans_required"),
            ({**_grounding(), "hashes": {}}, "exact_source_hashes_required"),
            ({**_grounding(), "vsa_patch_authority": True}, "vsa_patch_authority_must_be_false"),
            (
                {key: value for key, value in _grounding().items() if key != "safety_policy"},
                "exact_patch_authority_required",
            ),
            (
                {**_grounding(), "route": "LOCALIZE_FIRST"},
                "grounding_route_not_patch_admitted",
            ),
            (
                {
                    **_grounding(),
                    "target_file": "advisory_only.py",
                },
                "target_file_not_exactly_grounded",
            ),
            (
                {
                    **_grounding(),
                    "source_spans": [*_grounding()["source_spans"], "bad"],
                },
                "source_span_must_be_a_mapping",
            ),
            (
                {
                    **_grounding(),
                    "hashes": {
                        **_grounding()["hashes"],
                        "aura_target.py::target_symbol": "wrong",
                    },
                },
                "node_hash_binding_mismatch",
            ),
            (
                {
                    **_grounding(),
                    "source_spans": [
                        {
                            **_grounding()["source_spans"][0],
                            "line_range": (20, 10),
                        }
                    ],
                },
                "source_span_end_before_start",
            ),
        ],
    )
    def test_grounded_capsules_fail_closed(self, packet, error):
        result = objective_to_phase_capsules(
            "Refactor target",
            repo_root=REPO_ROOT,
            grounding_packet=packet,
        )
        assert result["ok"] is False
        assert result["error"] == error
        assert result["phase_capsules"] == []

    def test_live_grounding_compiles_into_digest_bound_capsules(self):
        result = compile_grounded_phase_capsules(
            "Refactor the grounded phase-capsule compiler",
            repo_root=REPO_ROOT,
            target_symbol="objective_to_phase_capsules",
        )
        assert result["ok"] is True
        assert result["grounding_evidence_id"].startswith("GPE-")
        assert (
            "aura_cockpit_planner.py"
            in result["grounding_evidence"]["allowed_files"]
        )
        assert result["grounding_evidence"]["source_spans"]
        assert result["grounding_evidence"]["source_hashes"]
        assert result["context_cost_accounting"]["avoided_token_proxy"] > 0


class TestWorkflowGates:
    def test_mapping(self):
        capsules = objective_to_phase_capsules("test", repo_root=REPO_ROOT)
        result = phase_capsules_to_workflow_gates(
            capsules["phase_capsules"], repo_root=REPO_ROOT
        )
        assert result["ok"] is True
        assert len(result["gate_mapping"]) == 9


class TestRunbook:
    def test_produces_runbook(self):
        capsules = objective_to_phase_capsules("test", repo_root=REPO_ROOT)
        result = phase_capsules_to_agent_runbook(
            capsules["phase_capsules"], repo_root=REPO_ROOT
        )
        assert result["ok"] is True
        assert len(result["runbook"]) > 0
