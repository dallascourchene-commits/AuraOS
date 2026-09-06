import unittest
from liveness_witness import *

NOW=1_000_000
HEAD=Head("GEN25","d91e0a39358901c5")

def cmd(cid="C1", created=900_000, generation="GEN25", execution=False):
    return Command(cid, created, generation, "d91e0a39358901c5", "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND", execution)

def rec(cid="C1", t=950_000, kind="ACK", state="ACK_ACCEPTED"):
    return Receipt(cid,t,kind,state)

class T(unittest.TestCase):
    def plan(self, commands, receipts=(), consumer=ConsumerObservation(False), starve=3600, reducer=3600):
        return compile_recovery(now_s=NOW, head=HEAD, commands=commands, receipts=receipts, consumer=consumer, starvation_after_s=starve, reducer_stall_after_s=reducer)
    def test_no_receipt_old_command_is_starved(self):
        p=self.plan([cmd()]); self.assertEqual(p.system_state,SystemState.ACTIVE_INGRESS_EGRESS_STARVATION); self.assertFalse(p.provider_fanout_allowed)
    def test_unrelated_old_bus_activity_never_satisfies_command(self):
        p=self.plan([cmd("NEW")],[rec("OLD",990_000,"RESULT","TERMINAL_SUCCESS")]); self.assertEqual(p.commands[0].state,CommandState.ADMISSION_STARVED)
    def test_receipt_before_command_does_not_count(self):
        p=self.plan([cmd("C",900_000)],[rec("C",899_999)]); self.assertEqual(p.commands[0].state,CommandState.ADMISSION_STARVED)
    def test_future_bound_receipt_fails_closed(self):
        with self.assertRaisesRegex(E,"FUTURE_RECEIPT"): self.plan([cmd()],[rec(t=NOW+1)])
    def test_ack_is_admitted_not_terminal(self):
        p=self.plan([cmd()],[rec()]); self.assertEqual(p.commands[0].state,CommandState.ADMITTED_NOT_TERMINAL)
    def test_old_ack_becomes_post_ack_reducer_stall(self):
        p=self.plan([cmd()],[rec(t=900_001)],reducer=1000); self.assertEqual(p.system_state,SystemState.POST_ACK_REDUCER_STALL); self.assertIn("DO_NOT_REPLAY_EFFECT",p.recovery_steps)
    def test_result_terminal(self):
        p=self.plan([cmd()],[rec(kind="RESULT",state="TERMINAL_SUCCESS")]); self.assertEqual(p.system_state,SystemState.HEALTHY_PROGRESS); self.assertTrue(p.local_progress_proven); self.assertFalse(p.provider_fanout_allowed)
    def test_error_terminal(self):
        p=self.plan([cmd()],[rec(kind="ERROR",state="TERMINAL_ERROR")]); self.assertEqual(p.commands[0].state,CommandState.TERMINAL); self.assertTrue(p.local_progress_proven); self.assertFalse(p.provider_fanout_allowed)
    def test_typed_rejection(self):
        p=self.plan([cmd()],[rec(kind="ACK",state="CURRENTNESS_REJECTED")]); self.assertEqual(p.commands[0].state,CommandState.TYPED_REJECTED)
    def test_stale_head_precedes_liveness(self):
        p=self.plan([cmd(generation="GEN24")]); self.assertEqual(p.system_state,SystemState.CURRENTNESS_BLOCK)
    def test_same_generation_wrong_digest_is_stale(self):
        c=Command("C",900_000,"GEN25","wrong","READY",False); p=self.plan([c]); self.assertEqual(p.system_state,SystemState.CURRENTNESS_BLOCK)
    def test_unobserved_consumer_never_authorizes_restart(self):
        p=self.plan([cmd()]); self.assertEqual(p.restart_budget,0); self.assertNotIn("RESTART_AURA_PROJECT006_ONCE",p.recovery_steps)
    def test_unobserved_consumer_cannot_smuggle_state(self):
        with self.assertRaisesRegex(E,"UNOBSERVED_CONSUMER_HAS_STATE"): self.plan([cmd()],consumer=ConsumerObservation(False,service_active=False))
    def test_observed_consumer_requires_complete_restart_surface(self):
        with self.assertRaisesRegex(E,"INCOMPLETE_CONSUMER_OBSERVATION"): self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,lease_current=None))
    def test_observed_inactive_consumer_allows_one_restart(self):
        p=self.plan([cmd()],consumer=ConsumerObservation(True,service_active=False,lease_current=False)); self.assertEqual(p.restart_budget,1); self.assertEqual(p.recovery_steps.count("RESTART_AURA_PROJECT006_ONCE"),1)
    def test_observed_active_current_consumer_no_restart(self):
        p=self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,lease_current=True)); self.assertEqual(p.restart_budget,0)
    def test_future_consumer_time_fails_closed(self):
        with self.assertRaisesRegex(E,"FUTURE_CURSOR_TIME"): self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,lease_current=True,cursor_s=NOW+1))
    def test_bad_consumer_bool_fails_closed(self):
        with self.assertRaisesRegex(E,"BAD_SERVICE_ACTIVE"): self.plan([cmd()],consumer=ConsumerObservation(True,service_active=1,lease_current=True))
    def test_duplicate_command_ids_fail_closed(self):
        with self.assertRaises(E): self.plan([cmd("X"),cmd("X")])
    def test_future_command_fails_closed(self):
        with self.assertRaises(E): self.plan([cmd(created=NOW+1)])
    def test_bad_bool_fails_closed(self):
        with self.assertRaises(E): self.plan([Command("C",900_000,"GEN25","d91e0a39358901c5","Q",1)])
    def test_bad_receipt_state_fails_closed(self):
        with self.assertRaisesRegex(E,"BAD_RECEIPT_STATE"): self.plan([cmd()],[Receipt("C1",950_000,"ACK",1)])
    def test_bad_receipt_time_fails_closed_before_temporal_filter(self):
        with self.assertRaisesRegex(E,"BAD_RECEIPT_TIME"): self.plan([cmd()],[Receipt("C1",-1,"ACK","ACK_ACCEPTED")])
    def test_recent_starved_command_requires_visibility_not_false_death(self):
        p=self.plan([cmd(created=NOW-100)],starve=1000); self.assertEqual(p.system_state,SystemState.HOST_VISIBILITY_REQUIRED)
    def test_empty_ingress(self):
        p=self.plan([]); self.assertEqual(p.system_state,SystemState.NO_ACTIVE_INGRESS)
    def test_receipt_root_deterministic(self):
        a=self.plan([cmd("A"),cmd("B",800_000)]); b=self.plan([cmd("A"),cmd("B",800_000)]); self.assertEqual(a.receipt_root,b.receipt_root)
    def test_omega8_exactly_one_keeper(self):
        import itertools
        self.assertEqual(sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8)),1)
    def test_13d_tail_cannot_repair_invalid_core(self):
        import itertools
        core=(2,2,2,2,2,2,2,1)
        self.assertEqual(sum(context13_preserves_invalid(core,t) for t in itertools.product(range(3),repeat=5)),0)

if __name__=='__main__': unittest.main()
