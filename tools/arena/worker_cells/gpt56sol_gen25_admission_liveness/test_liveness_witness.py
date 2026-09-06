import itertools, unittest
from liveness_witness import *
NOW=1_000_000; HEAD=Head('GEN25','d91e0a39358901c5')
def cmd(cid='C1',created=900_000,generation='GEN25',execution=False,queue='AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND',digest='d91e0a39358901c5'): return Command(cid,created,generation,digest,queue,execution)
def rec(cid='C1',t=950_000,event=EventClass.ACK_ACCEPTED,detail='OK',attempt='A1',seq=0): return TypedReceipt(cid,attempt,seq,t,event,detail)
class T(unittest.TestCase):
 def plan(self,commands,receipts=(),consumer=ConsumerObservation(False),starve=3600,reducer=3600): return compile_recovery(now_s=NOW,head=HEAD,commands=commands,receipts=receipts,consumer=consumer,starvation_after_s=starve,reducer_stall_after_s=reducer)
 def test_no_receipt_old_command_is_starved(self): self.assertEqual(self.plan([cmd()]).system_state,SystemState.ACTIVE_INGRESS_EGRESS_STARVATION)
 def test_unrelated_old_bus_activity_never_satisfies_command(self): self.assertEqual(self.plan([cmd('NEW')],[rec('OLD',event=EventClass.TERMINAL_RESULT)]).commands[0].state,CommandState.ADMISSION_STARVED)
 def test_receipt_before_command_does_not_count(self): self.assertEqual(self.plan([cmd('C')],[rec('C',t=899_999)]).commands[0].state,CommandState.ADMISSION_STARVED)
 def test_future_bound_receipt_fails_closed(self):
  with self.assertRaisesRegex(E,'FUTURE_RECEIPT'): self.plan([cmd()],[rec(t=NOW+1)])
 def test_ack_is_admitted_not_terminal(self): self.assertEqual(self.plan([cmd()],[rec()]).commands[0].state,CommandState.ADMITTED_NOT_TERMINAL)
 def test_old_ack_becomes_post_ack_reducer_stall(self): self.assertEqual(self.plan([cmd()],[rec(t=900_001)],reducer=1000).system_state,SystemState.POST_ACK_REDUCER_STALL)
 def test_result_terminal(self): self.assertEqual(self.plan([cmd()],[rec(event=EventClass.TERMINAL_RESULT,detail='SUCCESS')]).system_state,SystemState.HEALTHY_PROGRESS)
 def test_error_terminal(self): self.assertEqual(self.plan([cmd()],[rec(event=EventClass.TERMINAL_ERROR,detail='ERROR')]).commands[0].state,CommandState.TERMINAL)
 def test_typed_rejection(self): self.assertEqual(self.plan([cmd()],[rec(event=EventClass.REJECTED,detail='CURRENTNESS_REJECTED')]).commands[0].state,CommandState.TYPED_REJECTED)
 def test_stale_head_precedes_liveness(self): self.assertEqual(self.plan([cmd(generation='GEN24')]).system_state,SystemState.CURRENTNESS_BLOCK)
 def test_same_generation_wrong_digest_is_stale(self): self.assertEqual(self.plan([cmd(digest='wrong')]).system_state,SystemState.CURRENTNESS_BLOCK)
 def test_inactive_queue_never_creates_starvation(self):
  for q in INACTIVE_QUEUE_STATES: self.assertEqual(self.plan([cmd(queue=q)]).system_state,SystemState.NO_ACTIVE_INGRESS)
 def test_unknown_queue_requires_visibility(self): self.assertEqual(self.plan([cmd(queue='MYSTERY')]).system_state,SystemState.HOST_VISIBILITY_REQUIRED)
 def test_inactive_stale_head_does_not_create_currentness_block(self): self.assertEqual(self.plan([cmd(generation='GEN24',queue='CANCELLED')]).system_state,SystemState.NO_ACTIVE_INGRESS)
 def test_unobserved_consumer_never_authorizes_restart(self): self.assertEqual(self.plan([cmd()]).restart_budget,0)
 def test_unobserved_consumer_cannot_smuggle_state(self):
  with self.assertRaisesRegex(E,'UNOBSERVED_CONSUMER_HAS_STATE'): self.plan([cmd()],consumer=ConsumerObservation(False,service_active=False))
 def test_observed_consumer_requires_service_state(self):
  with self.assertRaisesRegex(E,'INCOMPLETE_CONSUMER_OBSERVATION'): self.plan([cmd()],consumer=ConsumerObservation(True))
 def test_lease_is_optional_advisory(self): self.assertEqual(self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True)).restart_budget,0)
 def test_observed_inactive_consumer_allows_one_restart(self): self.assertEqual(self.plan([cmd()],consumer=ConsumerObservation(True,service_active=False)).restart_budget,1)
 def test_observed_active_unknown_progress_no_restart_yet(self): self.assertIn('COMPARE_CURSOR_STATE_RECEIPT_MOVEMENT',self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,progress_moved=None)).recovery_steps)
 def test_observed_active_stuck_allows_one_restart(self): self.assertEqual(self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,progress_moved=False)).restart_budget,1)
 def test_observed_active_progress_blocks_restart(self): self.assertEqual(self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,progress_moved=True)).restart_budget,0)
 def test_future_consumer_time_fails_closed(self):
  with self.assertRaisesRegex(E,'FUTURE_CURSOR_TIME'): self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,cursor_s=NOW+1))
 def test_bad_consumer_bool_fails_closed(self):
  with self.assertRaisesRegex(E,'BAD_SERVICE_ACTIVE'): self.plan([cmd()],consumer=ConsumerObservation(True,service_active=1))
 def test_duplicate_command_ids_fail_closed(self):
  with self.assertRaisesRegex(E,'DUPLICATE_COMMAND_ID'): self.plan([cmd('X'),cmd('X')])
 def test_future_command_fails_closed(self):
  with self.assertRaisesRegex(E,'FUTURE_COMMAND'): self.plan([cmd(created=NOW+1)])
 def test_bad_bool_fails_closed(self):
  with self.assertRaisesRegex(E,'BAD_EXEC_AUTH'): self.plan([cmd(execution=1)])
 def test_bad_receipt_event_fails_closed(self):
  with self.assertRaisesRegex(E,'BAD_EVENT_CLASS'): self.plan([cmd()],[TypedReceipt('C1','A1',0,950_000,'ACK_ACCEPTED','OK')])
 def test_bad_receipt_time_fails_closed(self):
  with self.assertRaisesRegex(E,'BAD_RECEIPT_TIME'): self.plan([cmd()],[rec(t=-1)])
 def test_recent_starved_requires_visibility(self): self.assertEqual(self.plan([cmd(created=NOW-100)],starve=1000).system_state,SystemState.HOST_VISIBILITY_REQUIRED)
 def test_empty_ingress(self): self.assertEqual(self.plan([]).system_state,SystemState.NO_ACTIVE_INGRESS)
 def test_receipt_root_deterministic(self): self.assertEqual(self.plan([cmd('A')]).receipt_root,self.plan([cmd('A')]).receipt_root)
 def test_receipt_root_binds_consumer_observation(self): self.assertNotEqual(self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,progress_moved=False,evidence_root='a'*64)).receipt_root,self.plan([cmd()],consumer=ConsumerObservation(True,service_active=True,progress_moved=True,evidence_root='b'*64)).receipt_root)
 def test_ambiguous_attempt_holds(self): self.assertEqual(self.plan([cmd()],[rec(attempt='A1'),rec(attempt='A2',seq=1)]).system_state,SystemState.RECEIPT_INTEGRITY_HOLD)
 def test_sequence_equivocation_holds(self): self.assertEqual(self.plan([cmd()],[rec(detail='X'),rec(detail='Y')]).system_state,SystemState.RECEIPT_INTEGRITY_HOLD)
 def test_exact_duplicate_idempotent_and_cannot_refresh(self): self.assertEqual(self.plan([cmd()],[rec(t=900_001),rec(t=990_000)],reducer=1000).system_state,SystemState.POST_ACK_REDUCER_STALL)
 def test_post_terminal_holds(self): self.assertEqual(self.plan([cmd()],[rec(seq=0,event=EventClass.TERMINAL_RESULT),rec(seq=1)]).system_state,SystemState.RECEIPT_INTEGRITY_HOLD)
 def test_post_rejection_holds(self): self.assertEqual(self.plan([cmd()],[rec(seq=0,event=EventClass.REJECTED),rec(seq=1)]).system_state,SystemState.RECEIPT_INTEGRITY_HOLD)
 def test_omega8_exactly_one_keeper(self): self.assertEqual(sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8)),1)
 def test_13d_tail_cannot_repair_invalid_core(self): self.assertEqual(sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5)),0)
if __name__=='__main__': unittest.main()
