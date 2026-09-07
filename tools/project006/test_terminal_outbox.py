import os, subprocess, tempfile, unittest
import unittest.mock as mock
from tools.project006.terminal_outbox import *

class TerminalOutboxTests(unittest.TestCase):
    def ident(self,n="C"):
        return CommandIdentity(n,n+"-IDEMP","FILE","REV","d"*64)
    def journal(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        return OutboxJournal(os.path.join(td.name,"j.db"))
    def test_negative_is_publishable_without_provider(self):
        j=self.journal(); r=TerminalResponse(self.ident(),"COMMAND_BLOCKED","EFFECT_CEILING_NOT_D0",0,{"x":1})
        j.stage_terminal(r); calls=[]
        self.assertEqual(j.publish_pending("C",lambda p:(calls.append(p) or "DRIVE-1")),"DRIVE-1")
        self.assertEqual(len(calls),1); self.assertEqual(j.status("C")["state"],"RETURN_WRITTEN")
    def test_replay_does_not_republish_after_written(self):
        j=self.journal(); r=TerminalResponse(self.ident(),"COMMAND_BLOCKED","X"); j.stage_terminal(r); n=[0]
        def w(p): n[0]+=1; return "D1"
        self.assertEqual(j.publish_pending("C",w),"D1"); self.assertEqual(j.publish_pending("C",w),"D1"); self.assertEqual(n[0],1)
    def test_writer_failure_retries_writer_only(self):
        j=self.journal(); j.stage_terminal(TerminalResponse(self.ident(),"RESULT",provider_request_count=1,payload={"answer":"ok"})); n=[0]
        def w(p):
            n[0]+=1
            if n[0]==1: raise RuntimeError("fail")
            return "D2"
        with self.assertRaises(RuntimeError): j.publish_pending("C",w)
        self.assertEqual(j.status("C")["state"],"RETURN_PENDING"); self.assertEqual(j.publish_pending("C",w),"D2"); self.assertEqual(n[0],2)
    def test_negative_provider_count_forbidden(self):
        with self.assertRaisesRegex(ValueError,"NEGATIVE_RESPONSE_HAS_PROVIDER_EFFECT"):
            TerminalResponse(self.ident(),"COMMAND_BLOCKED",provider_request_count=1).canonical()
    def test_equivocation_forbidden(self):
        j=self.journal(); j.stage_terminal(TerminalResponse(self.ident(),"COMMAND_BLOCKED","A"))
        with self.assertRaisesRegex(ValueError,"TERMINAL_EQUIVOCATION"): j.stage_terminal(TerminalResponse(self.ident(),"COMMAND_BLOCKED","B"))
    def test_idempotency_conflict_forbidden(self):
        j=self.journal(); j.ingest(self.ident())
        with self.assertRaisesRegex(ValueError,"IDEMPOTENCY_CONFLICT"): j.ingest(CommandIdentity("C","OTHER","FILE","REV","d"*64))
    def test_all_negative_kinds(self):
        for k in sorted(NEGATIVE_KINDS): TerminalResponse(self.ident(k),k,provider_request_count=0).canonical()
    def test_exact_writer_line_protocol(self):
        payload=TerminalResponse(self.ident(),"COMMAND_BLOCKED","X").canonical()
        cp=subprocess.CompletedProcess([],0,"BUS_WRITE_OK=True\nFILE_ID=DRIVE-X\nFILE_NAME=AURA_BUS_X_COMMAND_BLOCKED.json\nCHANNEL=01_AURA_TO_SWARM\nBYTES=10\nWRITE_SCOPE=AURA_DRIVE\n","")
        with mock.patch("tools.project006.terminal_outbox.subprocess.run", return_value=cp) as run:
            ref=AuraDriveBusWriterV1("/venv/bin/python","/writer.py")(payload)
        self.assertEqual(ref,"DRIVE-X")
        self.assertEqual(run.call_args.args[0],["/venv/bin/python","/writer.py","--channel","aura_to_swarm","--kind","COMMAND_BLOCKED","--objective","C"])
        self.assertIn('"provider_request_count":0',run.call_args.kwargs["input"])
    def test_bad_kind(self):
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_TERMINAL_KIND"): TerminalResponse(self.ident(),"MYSTERY").canonical()
if __name__=="__main__":unittest.main()
