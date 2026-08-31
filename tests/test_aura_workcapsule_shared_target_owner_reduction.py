from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts import aura_workcapsule_portable_derived_scoped_rebind as derived
from scripts import aura_workcapsule_scoped_portable_target_identity as shared
from tests.test_aura_workcapsule_portable_derived_scoped_rebind import (
    WorkCapsulePortableDerivedScopedRebindTests,
)


class WorkCapsuleSharedTargetOwnerReductionTests(
    WorkCapsulePortableDerivedScopedRebindTests
):
    def admitted_pair(self):
        kwargs = self.derived_kwargs(owner_projection=self.owner_chain_projection())
        witness = derived.derive_post_edit_witness_from_portable_target(
            portable_higher_owner_projection=kwargs["portable_higher_owner_projection"],
            source_observation=kwargs["source_observation"],
        )
        portable = derived.admit_post_source_portable_higher_owner_continuity(
            **derived._portable_kwargs(kwargs)
        )
        scoped = derived.admit_post_world_bound_scoped_rebind(
            **derived._scoped_kwargs(kwargs, witness)
        )
        return kwargs, scoped["scoped_post_repair_rebind"], portable

    def test_pr548_receipt_owner_accepts_stronger_pr542_receipt(self) -> None:
        _, scoped_receipt, portable_receipt = self.admitted_pair()
        self.assertEqual(
            [],
            shared.verify_shared_target_coordinates(
                scoped_receipt=scoped_receipt,
                source_receipt=portable_receipt,
            ),
        )

    def test_canonical_receipt_owner_catches_syntax_ordinal_drift_for_stronger_path(self) -> None:
        _, scoped_receipt, portable_receipt = self.admitted_pair()
        drifted = dict(portable_receipt)
        drifted["selected_target_syntax_ordinal"] = int(
            portable_receipt["selected_target_syntax_ordinal"]
        ) + 1
        self.assertIn(
            shared.SYNTAX_ORDINAL_MISMATCH,
            shared.verify_shared_target_coordinates(
                scoped_receipt=scoped_receipt,
                source_receipt=drifted,
            ),
        )

    def test_canonical_receipt_owner_catches_exact_span_drift_for_stronger_path(self) -> None:
        _, scoped_receipt, portable_receipt = self.admitted_pair()
        drifted = dict(portable_receipt)
        drifted["selected_target_byte_start"] = int(
            portable_receipt["selected_target_byte_start"]
        ) + 1
        self.assertIn(
            shared.TARGET_SPAN_MISMATCH,
            shared.verify_shared_target_coordinates(
                scoped_receipt=scoped_receipt,
                source_receipt=drifted,
            ),
        )

    def test_pr549_delegates_shared_coordinate_consequence_to_pr548_owner(self) -> None:
        kwargs = self.derived_kwargs(owner_projection=self.owner_chain_projection())
        with patch.object(
            derived.shared_target_owner,
            "verify_shared_target_coordinates",
            return_value=["SENTINEL_OWNER_FAILURE"],
        ) as delegated:
            violations = derived.verify_portable_derived_scoped_rebind(**kwargs)
        delegated.assert_called_once()
        self.assertEqual(["SHARED_TARGET_SENTINEL_OWNER_FAILURE"], violations)

    def test_pr549_contains_no_second_field_by_field_shared_target_owner(self) -> None:
        source = Path("scripts/aura_workcapsule_portable_derived_scoped_rebind.py").read_text()
        self.assertIn("shared_target_owner.verify_shared_target_coordinates", source)
        for legacy_duplicate in (
            "SHARED_DEPENDENCY_MISMATCH",
            "SHARED_GENERATION_MISMATCH",
            "SHARED_BODY_SHA_MISMATCH",
            "SHARED_BODY_LENGTH_MISMATCH",
            "SHARED_HANDLE_MISMATCH",
        ):
            self.assertNotIn(legacy_duplicate, source)
        canonical = Path("scripts/aura_workcapsule_scoped_portable_target_identity.py").read_text()
        self.assertIn("def verify_shared_target_coordinates", canonical)
        self.assertIn("SYNTAX_ORDINAL_MISMATCH", canonical)
        self.assertIn("TARGET_SPAN_MISMATCH", canonical)

    def test_reduced_admission_names_canonical_shared_target_owner(self) -> None:
        receipt = derived.admit_portable_derived_scoped_rebind(
            **self.derived_kwargs(owner_projection=self.owner_chain_projection())
        )
        self.assertTrue(receipt["shared_target_coordinate_reproved"])
        self.assertEqual(
            "scripts.aura_workcapsule_scoped_portable_target_identity.verify_shared_target_coordinates",
            receipt["shared_target_coordinate_owner"],
        )
        self.assertFalse(receipt["semantic_repair_correctness_proven"])
        self.assertFalse(receipt["post_edit_scope_handle_bound_to_raw_bytes"])
        self.assertFalse(any(receipt["authority"].values()))


if __name__ == "__main__":
    import unittest

    unittest.main()
