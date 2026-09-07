import os, tempfile, unittest
from tools.project006.windows_wake_broker import *

class WakeBrokerTests(unittest.TestCase):
    def store(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup); return WakeStore(os.path.join(td.name,"w.db"))
    def test_dedup(self):
        s=self.store(); n=[0]
        def w(): n[0]+=1; return 0,"ok"
        msg={"message":{"messageId":"M1"}}
        self.assertEqual(process_message(s,msg,w),"WAKE_OK"); self.assertEqual(process_message(s,msg,w),"DUPLICATE"); self.assertEqual(n[0],1)
    def test_failed_wake_not_replayed_blindly(self):
        s=self.store(); n=[0]
        def w(): n[0]+=1; return 9,"dead"
        msg={"messageId":"M2"}
        self.assertEqual(process_message(s,msg,w),"WAKE_FAILED"); self.assertEqual(process_message(s,msg,w),"DUPLICATE"); self.assertEqual(n[0],1)
    def test_hash_fallback_stable(self):
        a=event_identity({"b":1,"a":2}); b=event_identity({"a":2,"b":1}); self.assertEqual(a,b); self.assertTrue(a.startswith("sha256:"))
if __name__=="__main__":unittest.main()
