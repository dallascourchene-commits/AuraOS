from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from creator_studio_claim_lease import (
    ClaimBusy,
    ClaimLeaseStore,
    CurrentnessRequired,
    LeaseError,
    StaleFence,
    dependency_wake_candidates,
)


class ClaimLeaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "claims.json"
        self.store = ClaimLeaseStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def claim(self, worker, now=100):
        return self.store.claim(
            "W08",
            worker_id=worker,
            visit_id=f"visit-{worker}",
            capabilities=("python", "verify"),
            currentness="CURRENT",
            source_cut="creator-head-1",
            lease_s=10,
            now=now,
        )

    def test_concurrent_claim_race_has_one_winner(self):
        def attempt(i):
            try:
                return self.claim(f"worker-{i}", now=100).worker_id
            except ClaimBusy:
                return None
        with ThreadPoolExecutor(max_workers=16) as pool:
            winners = [x for x in pool.map(attempt, range(32)) if x]
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(self.store.snapshot()["claims"]), 1)

    def test_stale_claim_can_be_recovered_with_new_fence(self):
        old = self.claim("old", now=100)
        new = self.claim("new", now=111)
        self.assertGreater(new.fence, old.fence)
        self.assertEqual(new.worker_id, "new")

    def test_stale_worker_cannot_heartbeat_after_reclaim(self):
        old = self.claim("old", now=100)
        self.claim("new", now=111)
        with self.assertRaises(StaleFence):
            self.store.heartbeat(old, now=112)

    def test_stale_worker_cannot_release_after_reclaim(self):
        old = self.claim("old", now=100)
        self.claim("new", now=111)
        with self.assertRaises(StaleFence):
            self.store.release(old, now=112)

    def test_heartbeat_extends_live_lease(self):
        r = self.claim("a", now=100)
        r2 = self.store.heartbeat(r, source_cut="creator-head-1", lease_s=10, now=105)
        self.assertEqual(r2.lease_expires_at, 115)

    def test_source_cut_change_fails_closed(self):
        r = self.claim("a", now=100)
        with self.assertRaises(StaleFence):
            self.store.heartbeat(r, source_cut="creator-head-2", now=105)

    def test_stale_currentness_cannot_claim_or_heartbeat(self):
        with self.assertRaises(CurrentnessRequired):
            self.store.claim("W", worker_id="a", visit_id="v", currentness="STALE", source_cut="h")
        r = self.claim("a", now=100)
        with self.assertRaises(CurrentnessRequired):
            self.store.heartbeat(r, currentness="STALE", now=105)

    def test_release_allows_new_claim_with_new_fence(self):
        first = self.claim("a", now=100)
        self.store.release(first, now=101)
        second = self.claim("b", now=102)
        self.assertGreater(second.fence, first.fence)

    def test_restart_reads_same_live_claim(self):
        r = self.claim("a", now=100)
        other = ClaimLeaseStore(self.path)
        with self.assertRaises(ClaimBusy):
            other.claim("W08", worker_id="b", visit_id="vb", currentness="CURRENT", source_cut="creator-head-1", now=101)
        self.assertEqual(other.snapshot()["claims"]["W08"]["fence"], r.fence)

    def test_recover_stale_removes_expired_claim(self):
        self.claim("a", now=100)
        self.assertEqual(self.store.recover_stale(now=111), ("W08",))
        self.assertEqual(self.store.snapshot()["claims"], {})

    def test_capability_digest_and_effect_ceiling_are_bound(self):
        r = self.claim("a", now=100)
        self.assertEqual(r.effect_ceiling, "D0")
        self.assertEqual(len(r.capabilities_digest), 64)
        self.assertEqual(r.source_cut, "creator-head-1")

    def test_schema_tamper_fails_closed(self):
        data = self.store.snapshot()
        data["schema"] = "wrong"
        self.path.write_text(__import__("json").dumps(data), encoding="utf-8")
        with self.assertRaises(LeaseError):
            self.store.snapshot()

    def test_dependency_wake_candidates(self):
        work = {
            "A": {"state": "CLOSED", "dependencies": []},
            "B": {"state": "OPEN", "dependencies": ["A"]},
            "C": {"state": "OPEN", "dependencies": ["A", "D"]},
            "E": {"state": "BLOCKED", "dependencies": ["A"]},
        }
        self.assertEqual(dependency_wake_candidates(work, {"A"}), ("B",))


if __name__ == "__main__":
    unittest.main()
