from __future__ import annotations

from unittest.mock import patch

from scripts.aura_workcapsule_scoped_higher_owner_portable_continuity import (
    SCOPED_PREFIX,
    verify_scoped_higher_owner_portable_continuity,
)
from scripts.aura_workcapsule_scoped_portable_target_identity import (
    verify_shared_target_coordinates,
)
from tests.test_aura_workcapsule_scoped_higher_owner_portable_continuity import (
    WorkCapsuleScopedHigherOwnerPortableContinuityTests,
)


class WorkCapsuleRecursivePortableCurrentSharedOwnerTests(
    WorkCapsuleScopedHigherOwnerPortableContinuityTests
):
    def test_current_pr555_shared_coordinate_owner_is_live_dependency(self) -> None:
        sentinel = "SENTINEL_CURRENT_SHARED_TARGET_OWNER"
        with patch(
            "scripts.aura_workcapsule_scoped_portable_target_identity.verify_shared_target_coordinates",
            return_value=[sentinel],
        ):
            violations = verify_scoped_higher_owner_portable_continuity(**self.o29_kwargs())
        self.assertIn(SCOPED_PREFIX + sentinel, violations)

    def test_current_owner_exposes_receipt_level_canonical_comparator(self) -> None:
        self.assertTrue(callable(verify_shared_target_coordinates))


if __name__ == "__main__":
    import unittest

    unittest.main()
