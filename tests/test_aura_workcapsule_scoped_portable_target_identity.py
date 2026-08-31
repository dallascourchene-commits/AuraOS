from __future__ import annotations

import copy
import inspect
from pathlib import Path

from scripts.aura_workcapsule_scoped_portable_target_identity import (
    SEMANTIC_HANDLE_MISMATCH,
    SOURCE_BODY_SHA_MISMATCH,
    SOURCE_GENERATION_MISMATCH,
    SYNTAX_ORDINAL_MISMATCH,
    TARGET_SPAN_MISMATCH,
    SCOPED_PREFIX,
    admit_scoped_portable_target_identity,
    verify_scoped_portable_target_identity,
)
from tests.test_aura_workcapsule_post_repair_source_projection_continuity import (
    WorkCapsulePostRepairSourceProjectionContinuityTests,
)
from tests.test_aura_workcapsule_scoped_post_repair_rebind import (
    KEY,
    closure,
    post,
    reentry,
    stale_observation,
)


class WorkCapsuleScopedPortableTargetIdentityTests(
    WorkCapsulePostRepairSourceProjectionContinuityTests
):
    def scoped_witness(self, **overrides) -> dict:
        witness = post()
        witness.update(
            {
                "post_source_generation": 43,
                "post_body_sha256": self.repaired_sha,
                "post_byte_len": len(self.repaired),
                "syntax_ordinal": 1,
                "byte_start": 0,
                "byte_end": len(self.repaired),
                "semantic_handle_digest": "ab" * 32,
            }
        )
        witness.update(overrides)
        return witness

    def scoped_inputs(self, *, witness=None) -> dict:
        return {
            "closure_admission": closure(),
            "reentry_admission": reentry(),
            "source_observation": stale_observation(),
            "dependency_key": copy.deepcopy(KEY),
            "post_edit_witness": witness if witness is not None else self.scoped_witness(),
        }

    def joined_kwargs(self, *, witness=None, projection=None) -> dict:
        return {
            "scoped_rebind_inputs": self.scoped_inputs(witness=witness),
            "post_source_inputs": self.cross_kwargs(
                projection=projection if projection is not None else self.projection()
            ),
        }

    def test_exact_scoped_witness_and_portable_target_converge_on_one_coordinate(self) -> None:
        self.assertEqual([], verify_scoped_portable_target_identity(**self.joined_kwargs()))
        receipt = admit_scoped_portable_target_identity(**self.joined_kwargs())
        self.assertTrue(receipt["same_post_edit_target_coordinate_proven"])
        self.assertTrue(receipt["same_post_source_instance_proven"])
        self.assertTrue(receipt["same_semantic_handle_proven"])
        self.assertEqual("ab" * 32, receipt["selected_target_semantic_handle_digest_hex"])
        self.assertTrue(receipt["portable_canonical_owner_parent_relation_carried_by_pr539"])
        self.assertFalse(receipt["scoped_witness_owner_parent_relation_proven"])
        self.assertFalse(receipt["cross_parent_owner_parent_equality_proven"])
        self.assertFalse(receipt["reentry_closed"])
        self.assertFalse(receipt["source_currentness_minted_by_child"])
        self.assertFalse(receipt["semantic_repair_correctness_proven"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_independently_valid_scoped_generation_drift_is_rejected(self) -> None:
        witness = self.scoped_witness(post_source_generation=44)
        violations = verify_scoped_portable_target_identity(**self.joined_kwargs(witness=witness))
        self.assertIn(SOURCE_GENERATION_MISMATCH, violations)

    def test_independently_valid_scoped_body_drift_is_rejected(self) -> None:
        witness = self.scoped_witness(post_body_sha256="22" * 32)
        violations = verify_scoped_portable_target_identity(**self.joined_kwargs(witness=witness))
        self.assertIn(SOURCE_BODY_SHA_MISMATCH, violations)

    def test_independently_valid_scoped_syntax_ordinal_drift_is_rejected(self) -> None:
        witness = self.scoped_witness(syntax_ordinal=2)
        violations = verify_scoped_portable_target_identity(**self.joined_kwargs(witness=witness))
        self.assertIn(SYNTAX_ORDINAL_MISMATCH, violations)

    def test_independently_valid_scoped_span_drift_is_rejected(self) -> None:
        witness = self.scoped_witness(byte_start=1, byte_end=len(self.repaired))
        violations = verify_scoped_portable_target_identity(**self.joined_kwargs(witness=witness))
        self.assertIn(TARGET_SPAN_MISMATCH, violations)

    def test_independently_valid_scoped_handle_drift_is_rejected(self) -> None:
        witness = self.scoped_witness(semantic_handle_digest="cd" * 32)
        violations = verify_scoped_portable_target_identity(**self.joined_kwargs(witness=witness))
        self.assertIn(SEMANTIC_HANDLE_MISMATCH, violations)

    def test_scoped_parent_authority_widening_fails_before_join(self) -> None:
        witness = self.scoped_witness(commit_authorized=True)
        violations = verify_scoped_portable_target_identity(**self.joined_kwargs(witness=witness))
        self.assertIn(SCOPED_PREFIX + "POST_EDIT_CEILING_VIOLATED:commit_authorized", violations)

    def test_portable_owner_relation_is_not_recast_as_cross_parent_equality(self) -> None:
        receipt = admit_scoped_portable_target_identity(**self.joined_kwargs())
        self.assertTrue(receipt["portable_canonical_owner_parent_relation_carried_by_pr539"])
        self.assertFalse(receipt["scoped_witness_owner_parent_relation_proven"])
        self.assertFalse(receipt["cross_parent_owner_parent_equality_proven"])

    def test_public_boundary_has_no_third_target_or_raw_replay_escape_hatch(self) -> None:
        params = inspect.signature(verify_scoped_portable_target_identity).parameters
        self.assertEqual({"scoped_rebind_inputs", "post_source_inputs"}, set(params))
        source = Path("scripts/aura_workcapsule_scoped_portable_target_identity.py").read_text()
        self.assertIn("verify_scoped_post_repair_rebind", source)
        self.assertIn("verify_post_repair_source_projection_continuity", source)
        for forbidden in (
            "compile_source_reentry_observations",
            "compile_observation_bound_reentry_closure",
            "parse_python",
            "derive_post_reentry_candidate",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    import unittest

    unittest.main()
