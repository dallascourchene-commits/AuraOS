from __future__ import annotations

from dataclasses import replace
import os
import unittest

from tools.bughound.arena_runtime import (
    BugHoundArenaRuntimeR0,
    BugHoundArenaRuntimeR0SpecV1,
    NETWORK_OFF,
    source_tree_digest,
)
from tools.bughound.target_profile import (
    AURAOS_HARDENING_PROFILE_ID,
    CASH_BOUNTY_PROFILE_ID,
    BugHoundTargetProfileV1,
)


class BugHoundArenaRuntimeR0Tests(unittest.TestCase):
    def source(self):
        return {
            "src/app.py": "VALUE = 1\n",
            "tests/test_app.py": "def test_value():\n    assert 1 == 1\n",
        }

    def profile(self, *, auraos: bool = False) -> BugHoundTargetProfileV1:
        if auraos:
            return BugHoundTargetProfileV1(
                profile_id=AURAOS_HARDENING_PROFILE_ID,
                profile_kind="INTERNAL_AURAOS_HARDENING",
                target_ref="repo://AuraOS",
                target_generation="head-r0",
            )
        return BugHoundTargetProfileV1(
            profile_id=CASH_BOUNTY_PROFILE_ID,
            profile_kind="EXTERNAL_CASH_BOUNTY",
            target_ref="program://authorized/local-snapshot",
            target_generation="target-r0",
        )

    def spec(self, *, auraos: bool = False, **overrides) -> BugHoundArenaRuntimeR0SpecV1:
        values = dict(
            profile=self.profile(auraos=auraos),
            source_digest=source_tree_digest(self.source()),
        )
        values.update(overrides)
        return BugHoundArenaRuntimeR0SpecV1(**values)

    def test_cash_profile_materializes_pre_effect_capsule(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(), self.source())
        receipt = runtime.materialize()
        self.assertEqual(receipt.profile_id, CASH_BOUNTY_PROFILE_ID)
        self.assertEqual(receipt.network_policy, NETWORK_OFF)
        self.assertTrue(receipt.logical_network_policy_off)
        self.assertFalse(receipt.os_network_isolation_proven)
        self.assertFalse(receipt.external_effect)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.payout_authority)
        runtime.teardown()

    def test_auraos_profile_uses_same_r0_without_cash_authority(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(auraos=True), self.source())
        receipt = runtime.materialize()
        self.assertEqual(receipt.profile_id, AURAOS_HARDENING_PROFILE_ID)
        self.assertEqual(receipt.credential_count, 0)
        self.assertFalse(receipt.external_effect)
        runtime.teardown()

    def test_network_enabled_profile_fails_closed(self) -> None:
        runtime = BugHoundArenaRuntimeR0(
            self.spec(network_policy="HOST_NETWORK"), self.source()
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R0_NETWORK_MUST_BE_OFF"):
            runtime.materialize()

    def test_credentials_fail_closed(self) -> None:
        runtime = BugHoundArenaRuntimeR0(
            self.spec(credential_refs=("secret://token",)), self.source()
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R0_CREDENTIALS_FORBIDDEN"):
            runtime.materialize()

    def test_source_digest_mismatch_fails_before_materialization(self) -> None:
        runtime = BugHoundArenaRuntimeR0(
            self.spec(source_digest="wrong"), self.source()
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R0_SOURCE_DIGEST_MISMATCH"):
            runtime.materialize()
        self.assertFalse(runtime.active)

    def test_source_paths_reject_parent_traversal(self) -> None:
        source = {"../escape.py": "x = 1\n"}
        with self.assertRaisesRegex(ValueError, "BUGHOUND_CAPSULE_PATH_INVALID"):
            source_tree_digest(source)

    def test_source_plane_has_no_write_bits(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(), self.source())
        receipt = runtime.materialize()
        self.assertFalse(receipt.source_write_bits_present)
        self.assertEqual(runtime.source_path.stat().st_mode & 0o222, 0)
        for path in runtime.source_path.rglob("*"):
            self.assertEqual(path.stat().st_mode & 0o222, 0)
        runtime.teardown()

    def test_overlay_write_does_not_change_source_digest(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(), self.source())
        runtime.materialize()
        before = runtime.read_source("src/app.py")
        overlay_digest = runtime.write_overlay("src/app.py", "VALUE = 2\n")
        self.assertNotEqual(overlay_digest, source_tree_digest({"x": before}))
        self.assertEqual(runtime.read_source("src/app.py"), before)
        receipt = runtime.teardown()
        self.assertTrue(receipt.source_intact_before_teardown)

    def test_overlay_limit_is_enforced(self) -> None:
        runtime = BugHoundArenaRuntimeR0(
            self.spec(max_overlay_bytes=3), self.source()
        )
        runtime.materialize()
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R0_OVERLAY_BYTE_LIMIT_EXCEEDED"):
            runtime.write_overlay("large.txt", b"1234")
        runtime.teardown()

    def test_evidence_bus_is_separate_and_deterministic(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(), self.source())
        runtime.materialize()
        first = runtime.append_evidence(
            event_type="STATIC_CANDIDATE",
            artifact_ref="artifact://candidate/1",
            artifact_digest="abc123",
        )
        second = runtime.append_evidence(
            event_type="REPRODUCTION",
            artifact_ref="artifact://repro/1",
            artifact_digest="def456",
        )
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)
        self.assertTrue((runtime.evidence_path / "events.jsonl").is_file())
        receipt = runtime.teardown()
        self.assertEqual(receipt.evidence_event_count, 2)
        self.assertTrue(receipt.evidence_digest)

    def test_teardown_removes_root_and_is_idempotent(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(), self.source())
        runtime.materialize()
        root = runtime.root_path
        receipt = runtime.teardown()
        self.assertTrue(receipt.root_removed)
        self.assertFalse(root.exists())
        self.assertIs(runtime.teardown(), receipt)

    def test_source_mutation_is_detected_before_teardown(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(), self.source())
        runtime.materialize()
        target = runtime.source_path / "src" / "app.py"
        os.chmod(runtime.source_path / "src", 0o755)
        os.chmod(target, 0o644)
        target.write_text("VALUE = 999\n", encoding="utf-8")
        receipt = runtime.teardown()
        self.assertFalse(receipt.source_intact_before_teardown)
        self.assertNotEqual(receipt.source_digest_observed, receipt.source_digest_expected)
        self.assertTrue(receipt.root_removed)

    def test_source_file_limit_is_enforced(self) -> None:
        runtime = BugHoundArenaRuntimeR0(
            self.spec(max_source_files=1), self.source()
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R0_SOURCE_FILE_LIMIT_EXCEEDED"):
            runtime.materialize()

    def test_source_byte_limit_is_enforced(self) -> None:
        runtime = BugHoundArenaRuntimeR0(
            self.spec(max_source_bytes=1), self.source()
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R0_SOURCE_BYTE_LIMIT_EXCEEDED"):
            runtime.materialize()

    def test_profile_kind_cross_cast_fails_before_capsule(self) -> None:
        bad = replace(self.profile(auraos=True), profile_kind="EXTERNAL_CASH_BOUNTY")
        runtime = BugHoundArenaRuntimeR0(
            self.spec(auraos=True, profile=bad), self.source()
        )
        with self.assertRaisesRegex(ValueError, "BUGHOUND_PROFILE_KIND_MISMATCH"):
            runtime.materialize()
        self.assertFalse(runtime.active)

    def test_context_manager_tears_down_on_exception(self) -> None:
        runtime = BugHoundArenaRuntimeR0(self.spec(), self.source())
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with runtime:
                self.assertTrue(runtime.active)
                raise RuntimeError("boom")
        self.assertFalse(runtime.active)
        self.assertIsNotNone(runtime.teardown_receipt)
        self.assertTrue(runtime.teardown_receipt.root_removed)


if __name__ == "__main__":
    unittest.main()
