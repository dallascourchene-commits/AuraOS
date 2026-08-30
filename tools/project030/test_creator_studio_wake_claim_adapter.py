from pathlib import Path
import tempfile
import unittest

from creator_studio_claim_lease import ClaimLeaseStore, StaleFence
from creator_studio_continuation_harness import HarnessState, WorkItem, WorkerContext
from creator_studio_wake_adapter import WakeIntent
from creator_studio_wake_claim_adapter import (
    WakeClaimRefusal,
    accept_work_wake,
    revalidate_execution_fence,
)


MISSION = "CS-HARNESS-001"
CANONICAL = "CREATOR-STUDIO-PUBG"


def wake(worker="W-A", work="A", version="v1", mission=MISSION, **flags):
    return WakeIntent(
        schema="CreatorStudioWakeIntentV1",
        event_id=f"event-{worker}-{work}-{version}",
        event_type="WORK_ELIGIBLE",
        mission_id=mission,
        worker_id=worker,
        work_id=work,
        work_version=version,
        reason="eligible",
        **flags,
    )


class WakeClaimAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ClaimLeaseStore(Path(self.tmp.name) / "claims.json")
        self.state = HarnessState(MISSION, CANONICAL, temporary_mission=True)
        self.state.add_work(WorkItem("A", MISSION, "work", required_capabilities=frozenset({"python"})))
        self.worker = WorkerContext("W-A", frozenset({"python", "verify"}))

    def tearDown(self):
        self.tmp.cleanup()

    def accept(self, intent=None, **kwargs):
        return accept_work_wake(
            intent or wake(),
            state=self.state,
            worker=kwargs.pop("worker", self.worker),
            visit_id=kwargs.pop("visit_id", "visit-a"),
            source_cut=kwargs.pop("source_cut", "creator-head-1"),
            current_work_version=kwargs.pop("current_work_version", "v1"),
            lease_store=self.store,
            lease_s=10,
            now=kwargs.pop("now", 100),
            **kwargs,
        )

    def test_good_wake_becomes_fenced_d0_claim(self):
        accepted = self.accept()
        self.assertEqual(accepted.status, "CLAIMED_D0")
        self.assertGreaterEqual(accepted.claim.fence, 1)
        self.assertEqual(self.state.claims["A"], "W-A")
        self.assertEqual(self.state.work["A"].state, "ACTIVE")

    def test_wake_never_grants_execution_or_provider_authority(self):
        for flag in (
            {"execution_authorized": True},
            {"provider_calls_authorized": True},
            {"background_execution_claimed": True},
        ):
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(WakeClaimRefusal, "WAKE_AUTHORITY_WIDENING_REFUSED"):
                    self.accept(wake(**flag))

    def test_wrong_worker_is_refused(self):
        with self.assertRaisesRegex(WakeClaimRefusal, "WAKE_WORKER_MISMATCH"):
            self.accept(wake(worker="W-B"))

    def test_stale_mission_is_refused(self):
        with self.assertRaisesRegex(WakeClaimRefusal, "WAKE_MISSION_STALE"):
            self.accept(wake(mission="OLD"))

    def test_stale_currentness_is_refused_before_claim(self):
        self.state.currentness = "STALE"
        with self.assertRaisesRegex(WakeClaimRefusal, "SUPERSEDED_CURRENTNESS"):
            self.accept()
        self.assertEqual(self.store.snapshot()["claims"], {})

    def test_stale_work_version_is_refused(self):
        with self.assertRaisesRegex(WakeClaimRefusal, "WAKE_WORK_VERSION_STALE"):
            self.accept(wake(version="v1"), current_work_version="v2")

    def test_missing_dependency_is_refused(self):
        self.state.work["A"].dependencies = ("PRE",)
        with self.assertRaisesRegex(WakeClaimRefusal, "WAKE_DEPENDENCY_NOT_CLOSED"):
            self.accept()

    def test_capability_mismatch_is_refused(self):
        weak = WorkerContext("W-A", frozenset({"verify"}))
        with self.assertRaisesRegex(WakeClaimRefusal, "WAKE_CAPABILITY_MISMATCH"):
            self.accept(worker=weak)

    def test_second_acceptance_cannot_duplicate_live_claim(self):
        first = self.accept()
        # Simulate a second scheduler projection that has not yet observed the
        # first in-memory claim; the durable lease must still prevent duplicate ownership.
        self.state.claims.pop("A", None)
        self.state.work["A"].state = "OPEN"
        with self.assertRaisesRegex(WakeClaimRefusal, "WAKE_CLAIM_BUSY"):
            self.accept(now=101)
        self.assertEqual(self.store.snapshot()["claims"]["A"]["fence"], first.claim.fence)

    def test_execution_fence_revalidates_source_cut(self):
        accepted = self.accept()
        refreshed = revalidate_execution_fence(
            accepted,
            lease_store=self.store,
            source_cut="creator-head-1",
            lease_s=10,
            now=105,
        )
        self.assertEqual(refreshed.lease_expires_at, 115)
        with self.assertRaises(StaleFence):
            revalidate_execution_fence(
                accepted,
                lease_store=self.store,
                source_cut="creator-head-2",
                now=106,
            )


if __name__ == "__main__":
    unittest.main()
