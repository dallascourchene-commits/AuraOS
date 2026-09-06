import unittest
from liveness_witness import *
NOW=1_000_000; HEAD=Head('GEN25','d91e0a39358901c5')
def cmd(cid='C1',created=900_000,generation='GEN25',queue='READY'): return Command(cid,created,generation,'d91e0a39358901c5',queue,False)
def rec(cid='C1',attempt='A1',seq=0,t=950_000,event=EventClass.ACK_ACCEPTED,detail='OK'): return TypedReceipt(cid,attempt,seq,t,event,detail)
class T(unittest.TestCase):
 def test_ack(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec()]).state,CommandState.ADMITTED_NOT_TERMINAL)
 def test_terminal(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec(event=EventClass.TERMINAL_RESULT)]).state,CommandState.TERMINAL)
 def test_rejected(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec(event=EventClass.REJECTED)]).state,CommandState.TYPED_REJECTED)
 def test_starved(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[]).state,CommandState.ADMISSION_STARVED)
 def test_stale(self): self.assertEqual(classify_command(NOW,HEAD,cmd(generation='GEN24'),[]).state,CommandState.STALE_HEAD)
 def test_ambiguous_attempt_holds(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec(attempt='A1'),rec(attempt='A2',seq=1)]).state,CommandState.RECEIPT_INTEGRITY_HOLD)
 def test_sequence_equivocation_holds(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec(detail='X'),rec(detail='Y')]).state,CommandState.RECEIPT_INTEGRITY_HOLD)
 def test_exact_duplicate_is_idempotent(self): self.assertIsNone(project_receipt_ledger('C1',900_000,[rec(),rec(t=960_000)],NOW).hold_reason)
 def test_duplicate_ack_cannot_refresh_progress(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec(t=910_000),rec(t=990_000)]).progress_age_s,90_000)
 def test_post_terminal_holds(self): self.assertEqual(project_receipt_ledger('C1',900_000,[rec(seq=0,event=EventClass.TERMINAL_RESULT),rec(seq=1)],NOW).hold_reason,'EVENT_AFTER_TERMINAL_OR_REJECTION')
 def test_post_rejection_holds(self): self.assertEqual(project_receipt_ledger('C1',900_000,[rec(seq=0,event=EventClass.REJECTED),rec(seq=1)],NOW).hold_reason,'EVENT_AFTER_TERMINAL_OR_REJECTION')
 def test_future_receipt_fails(self):
  with self.assertRaisesRegex(E,'FUTURE_RECEIPT'): classify_command(NOW,HEAD,cmd(),[rec(t=NOW+1)])
 def test_old_receipt_ignored(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec(t=899_999)]).state,CommandState.ADMISSION_STARVED)
 def test_unrelated_ignored(self): self.assertEqual(classify_command(NOW,HEAD,cmd(),[rec(cid='OTHER')]).state,CommandState.ADMISSION_STARVED)
 def test_inactive(self): self.assertEqual(classify_command(NOW,HEAD,cmd(queue='CANCELLED'),[]).state,CommandState.INACTIVE_QUEUE)
 def test_unknown_queue(self): self.assertEqual(classify_command(NOW,HEAD,cmd(queue='???'),[]).state,CommandState.UNKNOWN)
if __name__=='__main__': unittest.main()
