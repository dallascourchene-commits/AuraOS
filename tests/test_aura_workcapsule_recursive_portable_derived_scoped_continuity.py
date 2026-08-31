from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

from scripts import aura_workcapsule_scoped_portable_target_identity as shared_owner
from scripts.aura_workcapsule_recursive_portable_derived_scoped_continuity import (
    admit_recursive_portable_derived_scoped_continuity,
    verify_recursive_portable_derived_scoped_continuity,
)
from tests.test_aura_workcapsule_portable_derived_scoped_rebind import (
    WorkCapsulePortableDerivedScopedRebindTests,
)


class WorkCapsuleRecursivePortableDerivedScopedContinuityTests(
    WorkCapsulePortableDerivedScopedRebindTests
):
    def test_exact_lower_input_path_reaches_recursive_current_owner(self) -> None:
        kwargs = self.derived_kwargs()
        self.assertEqual([], verify_recursive_portable_derived_scoped_continuity(**kwargs))
        admitted = admit_recursive_portable_derived_scoped_continuity(**kwargs)
        self.assertTrue(admitted["portable_derived_scoped_rebind_consumed"])
        self.assertFalse(admitted["caller_scoped_target_inputs_accepted"])
        self.assertFalse(admitted["caller_post_edit_witness_accepted"])
        self.assertTrue(admitted["one_portable_higher_owner_projection_used"])
        self.assertTrue(admitted["current_shared_coordinate_owner_reused"])
        self.assertFalse(admitted["second_shared_coordinate_owner_minted"])
        self.assertTrue(admitted["recursive_cross_runtime_canonicalization_reused"])
        self.assertEqual(43, admitted["post_source_generation"])
        self.assertEqual(self.repaired_sha, admitted["post_source_sha256"])
        self.assertEqual("ab" * 32, admitted["selected_target_semantic_handle_digest_hex"])
        self.assertFalse(admitted["structural_handle_bound_to_raw_bytes"])
        self.assertFalse(admitted["producer_authenticated"])
        self.assertFalse(admitted["semantic_repair_correctness_proven"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_live_pr555_shared_owner_failure_is_observed(self) -> None:
        with patch.object(
            shared_owner,
            "verify_shared_target_coordinates",
            return_value=["SENTINEL_CURRENT_SHARED_OWNER"],
        ):
            violations = verify_recursive_portable_derived_scoped_continuity(
                **self.derived_kwargs()
            )
        self.assertIn("SHARED_OWNER_SENTINEL_CURRENT_SHARED_OWNER", violations)

    def test_public_boundary_removes_legacy_scoped_bundle_and_second_target(self) -> None:
        params = inspect.signature(
            verify_recursive_portable_derived_scoped_continuity
        ).parameters
        self.assertIn("portable_higher_owner_projection", params)
        self.assertIn("source_observation", params)
        self.assertNotIn("scoped_target_inputs", params)
        self.assertNotIn("scoped_rebind_inputs", params)
        self.assertNotIn("post_edit_witness", params)
        self.assertNotIn("astge_projection", params)
        self.assertNotIn("canonical_target_projection", params)

        source = Path(
            "scripts/aura_workcapsule_recursive_portable_derived_scoped_continuity.py"
        ).read_text()
        self.assertIn("verify_portable_derived_scoped_rebind", source)
        self.assertIn("verify_shared_target_coordinates", source)
        self.assertIn("verify_portable_higher_owner_projection", source)
        self.assertNotIn("verify_scoped_portable_target_identity(**", source)

    def test_unknown_pre_state_remains_noninventing_through_recursive_layer(self) -> None:
        source = {
            "prior_file_id": 17,
            "relative_path": "src/a.py",
            "currentness": "UNKNOWN",
            "identity_guessed": False,
            "observed_bytes_bound_to_source_generation": False,
        }
        admitted = admit_recursive_portable_derived_scoped_continuity(
            **self.derived_kwargs(source_observation=source)
        )
        self.assertEqual(43, admitted["post_source_generation"])
        self.assertFalse(admitted["reentry_closed"])
        self.assertFalse(admitted["producer_authenticated"])


if __name__ == "__main__":
    import unittest

    unittest.main()
