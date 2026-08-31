from __future__ import annotations

import copy
import unittest

from scripts.aura_workcapsule_scoped_post_repair_rebind import (
    FULL_GRAPH,
    SELECTED_SOURCES,
    admit_scoped_post_repair_rebind,
    verify_scoped_post_repair_rebind,
)


def closure(status="HOLD"):
    return {
        "version": "AURA_WORKCAPSULE_OBSERVATION_BOUND_EXACT_VERIFIER_V1",
        "exact_observation_bound_input_reproduction": True,
        "closure_status": status,
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


def reentry(scope=SELECTED_SOURCES, key=None):
    key = key or {"file_id": 17, "relative_path": "src/a.py"}
    return {
        "version": "AURA_WORKCAPSULE_RAW_OWNER_STALE_SAFE_REENTRY_V1",
        "raw_source_owner_bound": True,
        "rejected_currentness_exact_reentry_only": True,
        "rejected_dependency_keys": [copy.deepcopy(key)],
        "minimum_reentry_scope": scope,
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


def stale_observation():
    return {
        "relative_path": "src/a.py",
        "currentness": "STALE",
        "source_generation_coordinate": {"domain": "SOURCE", "value": 42},
        "dependency_identity_source": "EXPECTED_PR488_SOURCE_BODY_WITNESS",
        "observed_bytes_bound_to_source_generation": False,
        "expected_source_identity": {
            "file_id": 17,
            "source_generation_coordinate": {"domain": "SOURCE", "value": 42},
            "expected_byte_len": 34,
            "expected_body_sha256": "old" * 21 + "o",
        },
        "observed_body_sha256": "stale" * 12 + "stal",
        "observed_byte_len": 34,
    }


def unknown_observation():
    return {
        "prior_file_id": 17,
        "relative_path": "src/a.py",
        "prior_source_generation_coordinate": {"domain": "SOURCE", "value": 42},
        "currentness": "UNKNOWN",
        "reason": "PR488_MISSING_SOURCE_BODY_WITNESS",
        "identity_guessed": False,
    }


def post(*, pre=42, post_generation=43, file_id=17, path="src/a.py"):
    return {
        "version": "AURA_ASTGE_POST_EDIT_PROFILED_SCOPE_CURRENT_V1",
        "file_id": file_id,
        "relative_path": path,
        "pre_source_generation": pre,
        "post_source_generation": post_generation,
        "source_generation_domain": "SOURCE",
        "post_body_sha256": "fresh" * 12 + "fres",
        "post_byte_len": 36,
        "syntax_ordinal": 7,
        "byte_start": 13,
        "byte_end": 47,
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


KEY = {"file_id": 17, "relative_path": "src/a.py"}


class ScopedPostRepairRebindTests(unittest.TestCase):
    def verify(self, *, c=None, r=None, o=None, k=None, p=None):
        return verify_scoped_post_repair_rebind(
            closure_admission=c or closure(),
            reentry_admission=r or reentry(),
            source_observation=o or stale_observation(),
            dependency_key=k or KEY,
            post_edit_witness=p or post(),
        )

    def admit(self, *, c=None, r=None, o=None, k=None, p=None):
        return admit_scoped_post_repair_rebind(
            closure_admission=c or closure(),
            reentry_admission=r or reentry(),
            source_observation=o or stale_observation(),
            dependency_key=k or KEY,
            post_edit_witness=p or post(),
        )

    def test_t1_stale_same_dependency_advanced_generation_yields_evidence_only(self):
        receipt = self.admit()
        self.assertTrue(receipt["same_dependency_identity_bound"])
        self.assertTrue(receipt["scoped_post_repair_rebind_evidence"])
        self.assertFalse(receipt["reentry_closed"])
        self.assertEqual(SELECTED_SOURCES, receipt["reentry_scope_after"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_t2_unknown_can_bind_fresh_current_without_inventing_pre_generation(self):
        receipt = self.admit(o=unknown_observation(), p=post(pre=None, post_generation=43))
        self.assertEqual("UNKNOWN", receipt["pre_repair_currentness"])
        self.assertFalse(receipt["pre_unknown_generation_retroactively_invented"])
        self.assertTrue(receipt["historical_stale_unknown_evidence_preserved"])

    def test_t3_same_path_but_different_file_identity_rejects(self):
        wrong = {"file_id": 18, "relative_path": "src/a.py"}
        self.assertIn("DEPENDENCY_NOT_SELECTED_FOR_REENTRY", self.verify(k=wrong))

    def test_t4_stale_pre_generation_mismatch_rejects(self):
        self.assertIn(
            "STALE_PRE_GENERATION_MISMATCH",
            self.verify(p=post(pre=41, post_generation=43)),
        )

    def test_t5_changed_body_cannot_reuse_pre_generation(self):
        self.assertIn(
            "POST_SOURCE_GENERATION_NOT_ADVANCED",
            self.verify(p=post(pre=42, post_generation=42)),
        )

    def test_t6_old_local_scope_id_or_name_cannot_gain_authority(self):
        witness = post()
        witness["old_local_scope_id_currentness_authority"] = True
        witness["local_scope_id"] = 99
        witness["scope_name"] = "target"
        violations = self.verify(p=witness)
        self.assertIn(
            "POST_EDIT_CEILING_VIOLATED:old_local_scope_id_currentness_authority",
            violations,
        )

    def test_t7_fresh_scope_for_dependency_not_selected_by_reentry_rejects(self):
        other = {"file_id": 18, "relative_path": "src/b.py"}
        self.assertIn(
            "DEPENDENCY_NOT_SELECTED_FOR_REENTRY",
            self.verify(r=reentry(key=other)),
        )

    def test_t8_full_graph_reentry_stays_full_graph(self):
        receipt = self.admit(r=reentry(scope=FULL_GRAPH))
        self.assertEqual(FULL_GRAPH, receipt["reentry_scope_before"])
        self.assertEqual(FULL_GRAPH, receipt["reentry_scope_after"])
        self.assertFalse(receipt["reentry_scope_narrowed_by_fresh_scope_context"])

    def test_t9_witness_never_closes_or_changes_reentry_scope(self):
        receipt = self.admit()
        self.assertFalse(receipt["reentry_closed"])
        self.assertEqual(receipt["reentry_scope_before"], receipt["reentry_scope_after"])

    def test_t10_new_or_cold_dependency_cannot_join_active_membership(self):
        new = {"file_id": 19, "relative_path": "src/new.py"}
        self.assertIn(
            "DEPENDENCY_NOT_SELECTED_FOR_REENTRY",
            self.verify(k=new, p=post(file_id=19, path="src/new.py")),
        )

    def test_t11_current_scope_does_not_prove_semantic_repair(self):
        receipt = self.admit()
        self.assertFalse(receipt["semantic_patch_correctness_proven"])
        self.assertFalse(receipt["semantic_truth_minted"])
        self.assertFalse(receipt["b_minus_approved"])

    def test_t12_stale_observed_bytes_cannot_be_relabeled_as_post_generation(self):
        obs = stale_observation()
        witness = post()
        witness["post_body_sha256"] = obs["observed_body_sha256"]
        witness["post_byte_len"] = obs["observed_byte_len"]
        self.assertIn(
            "STALE_OBSERVED_BYTES_RELABELED_AS_POST_GENERATION",
            self.verify(o=obs, p=witness),
        )


if __name__ == "__main__":
    unittest.main()
