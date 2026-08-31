from __future__ import annotations

import copy
import hashlib
import inspect

from scripts.aura_workcapsule_post_world_bound_scoped_rebind import (
    CLAIM,
    admit_post_world_bound_scoped_rebind,
    verify_post_world_bound_scoped_rebind,
)
from scripts.aura_workcapsule_raw_owner_stale_safe_reentry import VERSION as REENTRY_VERSION
from scripts.aura_workcapsule_scoped_post_repair_rebind import SELECTED_SOURCES
from tests.test_aura_workcapsule_two_phase_observation_bound_exact import (
    WorkCapsuleTwoPhaseObservationBoundExactTests as _TwoPhaseFixture,
)


KEY = {"file_id": 17, "relative_path": "src/a.py"}


class WorkCapsulePostWorldBoundScopedRebindTests(_TwoPhaseFixture):
    def reentry_admission(self) -> dict:
        return {
            "version": REENTRY_VERSION,
            "raw_source_owner_bound": True,
            "rejected_currentness_exact_reentry_only": True,
            "rejected_dependency_keys": [copy.deepcopy(KEY)],
            "minimum_reentry_scope": SELECTED_SOURCES,
            "reentry_required": True,
            "current_source_evidence_admitted": False,
            "source_currentness_minted_by_exact_reproduction": False,
            "authority": {
                "review_authorized": False,
                "mutation_authorized": False,
                "execution_authorized": False,
                "commit_authorized": False,
                "merge_authorized": False,
                "promotion_authorized": False,
                "provider_effect_authorized": False,
                "public_effect_authorized": False,
                "human_authority": False,
            },
        }

    def rejected_source_observation(self) -> dict:
        return {
            "relative_path": "src/a.py",
            "currentness": "STALE",
            "source_generation_coordinate": {"domain": "SOURCE", "value": 42},
            "dependency_identity_source": "EXPECTED_PR488_SOURCE_BODY_WITNESS",
            "observed_bytes_bound_to_source_generation": False,
            "expected_source_identity": {
                "file_id": 17,
                "source_generation_coordinate": {"domain": "SOURCE", "value": 42},
                "expected_byte_len": len(self.original),
                "expected_body_sha256": self.original_sha,
            },
            "observed_body_sha256": hashlib.sha256(self.stale).hexdigest(),
            "observed_byte_len": len(self.stale),
        }

    def post_edit_witness(self) -> dict:
        return {
            "version": "AURA_ASTGE_POST_EDIT_PROFILED_SCOPE_CURRENT_V1",
            "file_id": 17,
            "relative_path": "src/a.py",
            "pre_source_generation": 42,
            "post_source_generation": 43,
            "source_generation_domain": "SOURCE",
            "post_body_sha256": self.repaired_sha,
            "post_byte_len": len(self.repaired),
            "syntax_ordinal": 7,
            "byte_start": 0,
            "byte_end": len(self.repaired),
            "semantic_handle_digest": "ab" * 32,
            "post_edit_profiled_scope_current": True,
            "old_local_scope_id_currentness_authority": False,
            "incremental_parser_reuse_used": False,
            "changed_ranges_currentness_authority": False,
            "runtime_name_resolution_proven": False,
            "call_graph_proven": False,
            "semantic_patch_correctness_proven": False,
            "b_minus_approved": False,
            "commit_authorized": False,
            "execution_authorized": False,
            "human_authority": False,
            "external_effect_authorized": False,
            "producer_authenticated": False,
        }

    def kwargs(self, *, witness: dict | None = None, key: dict | None = None) -> dict:
        return {
            "pre_root": self.pre_root,
            "pre_codemap": self.codemap,
            "pre_anchor_manifest": self.anchors,
            "pre_witness_manifest": self.pre_witness,
            "previous_binding": self.previous,
            "pre_graph_witness": self.graph,
            "reentry_receipt": self.reentry,
            "post_root": self.post_root,
            "post_codemap": self.codemap,
            "post_anchor_manifest": self.anchors,
            "post_witness_manifest": self.post_witness,
            "post_graph_witness": self.graph,
            "observation_bound_receipt": self.observation_receipt,
            "reentry_admission": self.reentry_admission(),
            "source_observation": self.rejected_source_observation(),
            "dependency_key": copy.deepcopy(key if key is not None else KEY),
            "post_edit_witness": copy.deepcopy(witness if witness is not None else self.post_edit_witness()),
        }

    def test_o28_exact_post_world_binds_scoped_repair_evidence_only(self) -> None:
        receipt = admit_post_world_bound_scoped_rebind(**self.kwargs())
        self.assertEqual(CLAIM, receipt["claim"])
        self.assertTrue(receipt["post_world_exact_reproduction"])
        self.assertEqual(receipt["post_projection_receipt_identity"], receipt["post_exact_source_observation_identity"])
        self.assertEqual(self.repaired_sha, receipt["post_body_sha256"])
        self.assertEqual(43, receipt["post_source_generation"])
        self.assertEqual("CURRENT", receipt["post_source_currentness"])
        self.assertFalse(receipt["caller_closure_admission_accepted"])
        self.assertFalse(receipt["caller_post_source_witness_accepted"])
        self.assertFalse(receipt["caller_candidate_binding_accepted"])
        self.assertFalse(receipt["reentry_closed"])
        self.assertFalse(receipt["post_edit_scope_handle_bound_to_raw_bytes"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_o28_foreign_post_body_cannot_impersonate_exact_post_world(self) -> None:
        witness = self.post_edit_witness()
        witness["post_body_sha256"] = "f" * 64
        violations = verify_post_world_bound_scoped_rebind(**self.kwargs(witness=witness))
        self.assertIn("POST_WORLD_BODY_SHA256_MISMATCH", violations)

    def test_o28_foreign_post_generation_cannot_impersonate_exact_post_world(self) -> None:
        witness = self.post_edit_witness()
        witness["post_source_generation"] = 44
        violations = verify_post_world_bound_scoped_rebind(**self.kwargs(witness=witness))
        self.assertIn("POST_WORLD_SOURCE_GENERATION_MISMATCH", violations)

    def test_o28_foreign_post_length_cannot_impersonate_exact_post_world(self) -> None:
        witness = self.post_edit_witness()
        witness["post_byte_len"] += 1
        violations = verify_post_world_bound_scoped_rebind(**self.kwargs(witness=witness))
        self.assertIn("POST_WORLD_BYTE_LENGTH_MISMATCH", violations)

    def test_o28_mutated_post_raw_root_invalidates_old_exact_receipt_before_rebind(self) -> None:
        foreign = b"def target(x):\n    return x + 4\n"
        self.assertEqual(len(self.repaired), len(foreign))
        target = self.post_root / "src/a.py"
        target.write_bytes(foreign)
        try:
            violations = verify_post_world_bound_scoped_rebind(**self.kwargs())
        finally:
            target.write_bytes(self.repaired)
        self.assertTrue(any(item.startswith("POST_WORLD_EXACT_REPLAY_FAILED:") for item in violations))

    def test_o28_integer_truthiness_cannot_enter_source_generation_identity(self) -> None:
        witness = self.post_edit_witness()
        witness["post_source_generation"] = True
        violations = verify_post_world_bound_scoped_rebind(**self.kwargs(witness=witness))
        self.assertIn("POST_SOURCE_GENERATION_NOT_EXACT_INTEGER", violations)

    def test_o28_public_boundary_has_no_caller_closure_or_candidate_slot(self) -> None:
        params = inspect.signature(verify_post_world_bound_scoped_rebind).parameters
        self.assertNotIn("closure_admission", params)
        self.assertNotIn("candidate_binding", params)
        self.assertNotIn("post_source_witness", params)
        self.assertIn("post_root", params)
        self.assertIn("observation_bound_receipt", params)
        self.assertIn("post_edit_witness", params)

    def test_o28_scope_handle_remains_explicit_unowned_ceiling(self) -> None:
        witness = self.post_edit_witness()
        witness["semantic_handle_digest"] = "cd" * 32
        receipt = admit_post_world_bound_scoped_rebind(**self.kwargs(witness=witness))
        self.assertFalse(receipt["post_edit_scope_producer_authenticated"])
        self.assertFalse(receipt["post_edit_scope_handle_bound_to_raw_bytes"])
        self.assertFalse(receipt["semantic_patch_correctness_proven"])


if __name__ == "__main__":
    import unittest
    unittest.main()
