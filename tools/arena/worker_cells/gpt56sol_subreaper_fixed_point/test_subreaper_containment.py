import json, os, subprocess, sys, unittest
from pathlib import Path
import subreaper_containment as sc

HERE=Path(__file__).parent
WORKER=str(HERE/'tree_worker.py')

class Tests(unittest.TestCase):
    def test_01_capabilities(self):
        self.assertEqual(sys.platform,'linux')
        self.assertTrue(hasattr(os,'pidfd_open'))
    def test_02_group_only_is_falsified_by_setsid(self):
        r=sc.group_only_falsifier(worker=WORKER,mode='escaped')
        self.assertTrue(r['falsified']); self.assertGreaterEqual(r['group_only_survivors'],1)
    def test_03_subreaper_contains_escaped_session(self):
        r=sc.fixed_point_contain(worker=WORKER,mode='escaped')
        self.assertEqual(r.disposition,'CONTAINED'); self.assertEqual(r.survivors,0)
        self.assertGreaterEqual(r.adopted_seen,1)
    def test_04_subreaper_contains_doublefork_endpoint(self):
        r=sc.fixed_point_contain(worker=WORKER,mode='doublefork')
        self.assertEqual(r.disposition,'CONTAINED'); self.assertEqual(r.survivors,0)
    def test_05_subreaper_contains_fanout(self):
        r=sc.fixed_point_contain(worker=WORKER,mode='fanout8',max_descendants=32)
        self.assertEqual(r.disposition,'CONTAINED'); self.assertEqual(r.survivors,0)
        self.assertGreaterEqual(r.identities_seen,1)
    def test_06_budget_holds_but_cleanup_completes(self):
        r=sc.fixed_point_contain(worker=WORKER,mode='fanout8',max_descendants=1)
        self.assertEqual(r.disposition,'HOLD_DESCENDANT_BUDGET')
        self.assertEqual(sc.direct_children(),[])
    def test_07_receipt_excludes_pid_and_time(self):
        r=sc.fixed_point_contain(worker=WORKER,mode='escaped')
        s=json.dumps(r.semantic_dict(),sort_keys=True)
        self.assertNotIn('worker_pid',s); self.assertNotIn('wall',s); self.assertEqual(len(r.root()),64)
    def test_08_cgroup_gap_is_explicit(self):
        r=sc.fixed_point_contain(worker=WORKER,mode='doublefork')
        self.assertEqual(r.cgroup_direct,'UNAVAILABLE_NOT_WRITABLE')
    def test_09_pidfd_signal_path_used(self):
        r=sc.fixed_point_contain(worker=WORKER,mode='escaped')
        self.assertTrue(r.pidfd_supported); self.assertGreaterEqual(r.pidfd_signals,1)

if __name__=='__main__': unittest.main()
