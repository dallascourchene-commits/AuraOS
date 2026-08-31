from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path

from scripts.aura_workcapsule_portable_derived_scoped_rebind import (
    admit_portable_derived_scoped_rebind,
    derive_post_edit_witness_from_portable_target,
    verify_portable_derived_scoped_rebind,
)
from scripts.aura_workcapsule_raw_owner_stale_safe_reentry import VERSION as REENTRY_VERSION
from scripts.aura_workcapsule_scoped_post_repair_rebind import SELECTED_SOURCES
from tests.test_aura_workcapsule_post_source_portable_higher_owner_continuity import (
    WorkCapsulePostSourcePortableHigherOwnerContinuityTests,
)

KEY = {"file_id": 17, "relative_path": "src/a.py"}


class WorkCapsulePortableDerivedScopedRebindTests(
    WorkCapsulePostSourcePortableHigherOwnerContinuityTests
):
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

    def derived_kwargs(self, *, owner_projection=None, source_observation=None) -> dict:
        out = super().child_kwargs(owner_projection=owner_projection)
        out.update(
            {
                "reentry_admission": self.reentry_admission(),
                "source_observation": copy.deepcopy(
                    source_observation
                    if source_observation is not None
                    else self.rejected_source_observation()
                ),
                "dependency_key": copy.deepcopy(KEY),
            }
        )
        return out

    def test_exact_portable_target_derives_pr532_witness_and_consumes_both_parents(self) -> None:
        owner = self.owner_chain_projection()
        witness = derive_post_edit_witness_from_portable_target(
            portable_higher_owner_projection=owner,
            source_observation=self.rejected_source_observation(),
        )
        self.assertEqual(42, witness["pre_source_generation"])
        self.assertEqual(43, witness["post_source_generation"])
        self.assertEqual(self.repaired_sha, witness["post_body_sha256"])
        self.assertEqual(len(self.repaired), witness["post_byte_len"])
        self.assertEqual("ab" * 32, witness["semantic_handle_digest"])
        self.assertFalse(witness["producer_authenticated"])

        self.assertEqual([], verify_portable_derived_scoped_rebind(**self.derived_kwargs(owner_projection=owner)))
        admitted = admit_portable_derived_scoped_rebind(**self.derived_kwargs(owner_projection=owner))
        self.assertTrue(admitted["portable_higher_owner_post_source_continuity_consumed"])
        self.assertTrue(admitted["post_world_scoped_rebind_consumed"])
        self.assertTrue(admitted["post_edit_witness_derived_from_portable_target"])
        self.assertFalse(admitted["caller_post_edit_witness_accepted"])
        self.assertEqual(43, admitted["post_source_generation"])
        self.assertEqual(self.repaired_sha, admitted["post_body_sha256"])
        self.assertEqual("ab" * 32, admitted["semantic_handle_digest"])
        self.assertFalse(admitted["post_edit_scope_handle_bound_to_raw_bytes"])
        self.assertFalse(admitted["semantic_repair_correctness_proven"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_pre_stale_generation_is_derived_not_caller_selected(self) -> None:
        source = self.rejected_source_observation()
        source["expected_source_identity"]["source_generation_coordinate"]["value"] = 43
        violations = verify_portable_derived_scoped_rebind(
            **self.derived_kwargs(source_observation=source)
        )
        self.assertIn("SCOPED_PR532_POST_SOURCE_GENERATION_NOT_ADVANCED", violations)

    def test_unknown_pre_state_keeps_pre_generation_absent(self) -> None:
        source = {
            "prior_file_id": 17,
            "relative_path": "src/a.py",
            "currentness": "UNKNOWN",
            "identity_guessed": False,
            "observed_bytes_bound_to_source_generation": False,
        }
        witness = derive_post_edit_witness_from_portable_target(
            portable_higher_owner_projection=self.owner_chain_projection(),
            source_observation=source,
        )
        self.assertIsNone(witness["pre_source_generation"])
        self.assertEqual(43, witness["post_source_generation"])

    def test_portable_handle_can_change_without_becoming_raw_byte_or_semantic_authority(self) -> None:
        nested = self.projection(selected_target_semantic_handle_digest_hex="cd" * 32)
        owner = self.owner_chain_projection(nested_projection=nested)
        admitted = admit_portable_derived_scoped_rebind(
            **self.derived_kwargs(owner_projection=owner)
        )
        self.assertEqual("cd" * 32, admitted["semantic_handle_digest"])
        self.assertFalse(admitted["post_edit_scope_handle_bound_to_raw_bytes"])
        self.assertFalse(admitted["semantic_repair_correctness_proven"])
        self.assertFalse(admitted["portable_projection_producer_authenticated"])

    def test_public_boundary_has_one_portable_target_and_no_caller_post_edit_witness(self) -> None:
        params = inspect.signature(verify_portable_derived_scoped_rebind).parameters
        self.assertIn("portable_higher_owner_projection", params)
        self.assertIn("source_observation", params)
        self.assertNotIn("post_edit_witness", params)
        self.assertNotIn("astge_projection", params)
        self.assertNotIn("canonical_target_projection", params)

        source = Path("scripts/aura_workcapsule_portable_derived_scoped_rebind.py").read_text()
        self.assertIn("verify_post_source_portable_higher_owner_continuity", source)
        self.assertIn("verify_post_world_bound_scoped_rebind", source)
        self.assertNotIn("compile_source_reentry_observations", source)
        self.assertNotIn("derive_post_reentry_candidate", source)


if __name__ == "__main__":
    import unittest

    unittest.main()
