import unittest
from host_observation_bridge import *
from liveness_witness import Command, SystemState, compile_recovery

NOW = 2_000_000
H = EXPECTED_HEAD
SHA_A = "a"*64
SHA_B = "b"*64
SHA_C = "c"*64
SHA_D = "d"*64

def snap(t=1_900_000, active="active", sub="running", pid=77, consumer=SHA_A, state=SHA_B, receipts=SHA_C, command_receipt=None, cursor=None, scan=None, lease=None):
    if cursor is None: cursor=max(0,t-10_000)
    if scan is None: scan=max(0,t-5_000)
    return HostSnapshot(t, active, sub, pid, consumer, state, receipts, command_receipt, cursor, scan, lease)

def starved_command():
    return Command("C", 1_000_000, H.generation, H.digest, "READY", False)

class T(unittest.TestCase):
    def plan_for(self, obs):
        return compile_recovery(now_s=NOW,head=H,commands=[starved_command()],receipts=[],consumer=obs,starvation_after_s=3600,reducer_stall_after_s=3600)
    def test_probe_plan_is_read_only(self):
        p=compile_read_only_probe(); assert_probe_read_only(p); self.assertEqual(len(p.steps),5)
    def test_probe_plan_pins_exact_owner_host_paths(self):
        p=compile_read_only_probe(); self.assertEqual(p.service,"aura-project006.service"); self.assertIn("aura_drive_swarm_consumer_v1.py",p.consumer_path)
    def test_probe_plan_rejects_wrong_head(self):
        with self.assertRaisesRegex(E,"HEAD_NOT_AUTHORITATIVE_GEN25"): compile_read_only_probe(Head("GEN25","wrong"))
    def test_snapshot_root_deterministic(self):
        s=snap(); self.assertEqual(validate_snapshot(s,observation_cut_s=NOW),validate_snapshot(s,observation_cut_s=NOW))
    def test_snapshot_root_changes_with_consumer_bytes(self):
        a=validate_snapshot(snap(),observation_cut_s=NOW); b=validate_snapshot(snap(consumer=SHA_D),observation_cut_s=NOW); self.assertNotEqual(a,b)
    def test_future_snapshot_rejected(self):
        with self.assertRaisesRegex(E,"FUTURE_HOST_SNAPSHOT"): validate_snapshot(snap(t=NOW+1),observation_cut_s=NOW)
    def test_future_cursor_rejected(self):
        with self.assertRaisesRegex(E,"FUTURE_CURSOR_TIME"): validate_snapshot(snap(cursor=1_950_000,t=1_900_000),observation_cut_s=NOW)
    def test_bad_sha_rejected(self):
        with self.assertRaisesRegex(E,"BAD_CONSUMER_SHA256"): validate_snapshot(snap(consumer="no"),observation_cut_s=NOW)
    def test_active_requires_pid(self):
        self.assertFalse(service_active(snap(pid=0)))
    def test_single_active_observation_does_not_authorize_restart(self):
        p=self.plan_for(single_snapshot_observation(snap(),observation_cut_s=NOW)); self.assertEqual(p.restart_budget,0); self.assertIn("COMPARE_CURSOR_STATE_RECEIPT_MOVEMENT",p.recovery_steps)
    def test_inactive_observation_allows_one_restart(self):
        p=self.plan_for(single_snapshot_observation(snap(active="inactive",sub="dead",pid=0),observation_cut_s=NOW)); self.assertEqual(p.restart_budget,1); self.assertEqual(p.recovery_steps.count("RESTART_AURA_PROJECT006_ONCE"),1)
    def test_no_progress_after_iteration_allows_one_restart(self):
        pair=compare_snapshots(snap(t=1_800_000,cursor=1_700_000,scan=1_700_100),snap(t=1_900_000,cursor=1_700_000,scan=1_700_100),observation_cut_s=NOW); self.assertFalse(pair.progress_moved); p=self.plan_for(pair.observation); self.assertEqual(p.restart_budget,1)
    def test_state_movement_prevents_restart(self):
        pair=compare_snapshots(snap(t=1_800_000),snap(t=1_900_000,state=SHA_D),observation_cut_s=NOW); self.assertTrue(pair.progress_moved); p=self.plan_for(pair.observation); self.assertEqual(p.restart_budget,0)
    def test_receipt_inventory_movement_alone_does_not_count(self):
        pair=compare_snapshots(snap(t=1_800_000,cursor=1_700_000,scan=1_700_100),snap(t=1_900_000,receipts=SHA_D,cursor=1_700_000,scan=1_700_100),observation_cut_s=NOW); self.assertFalse(pair.progress_moved)
    def test_exact_command_receipt_movement_counts(self):
        pair=compare_snapshots(snap(t=1_800_000,cursor=1_700_000,scan=1_700_100),snap(t=1_900_000,command_receipt=SHA_D,cursor=1_700_000,scan=1_700_100),observation_cut_s=NOW); self.assertTrue(pair.progress_moved)
    def test_cursor_movement_counts(self):
        pair=compare_snapshots(snap(t=1_800_000,cursor=1_700_000),snap(t=1_900_000,cursor=1_800_001),observation_cut_s=NOW); self.assertTrue(pair.progress_moved)
    def test_last_scan_movement_counts(self):
        pair=compare_snapshots(snap(t=1_800_000,scan=1_700_000),snap(t=1_900_000,scan=1_850_001),observation_cut_s=NOW); self.assertTrue(pair.progress_moved)
    def test_reversed_snapshot_time_rejected(self):
        with self.assertRaisesRegex(E,"SNAPSHOT_TIME_REVERSED"): compare_snapshots(snap(t=1_900_000,cursor=1_700_000,scan=1_700_100),snap(t=1_800_000,cursor=1_700_000,scan=1_700_100),observation_cut_s=NOW)
    def test_evidence_root_binds_observation(self):
        pair=compare_snapshots(snap(t=1_800_000),snap(t=1_900_000,state=SHA_D),observation_cut_s=NOW); self.assertEqual(len(pair.observation.evidence_root),64)
    def test_lease_is_advisory_not_restart_authority(self):
        pair=compare_snapshots(snap(t=1_800_000,lease=True),snap(t=1_900_000,state=SHA_D,lease=False),observation_cut_s=NOW); p=self.plan_for(pair.observation); self.assertEqual(p.restart_budget,0)
    def test_provider_fanout_always_false(self):
        pair=compare_snapshots(snap(t=1_800_000),snap(t=1_900_000,state=SHA_D),observation_cut_s=NOW); self.assertFalse(self.plan_for(pair.observation).provider_fanout_allowed)

if __name__ == "__main__": unittest.main()
