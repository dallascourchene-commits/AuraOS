import itertools,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_support_hydration import SupportClosedHydration
from memory_city_adaptive_hydration import SupportFixedPoint,compile_adaptive_hydration_strategy,hard13d_strategy
def h(sel=10,uni=100,status='READY_SUPPORT_CLOSED_HYDRATION_D0'):return SupportClosedHydration(status,('A','B'),(),sel,uni,sel/uni if uni else 0,'p','r')
def f(current=True,converged=True,terminal=1):return SupportFixedPoint('s',current,converged,terminal)
class AdaptiveTests(unittest.TestCase):
    def test_local_for_one_use(self):self.assertEqual(compile_adaptive_hydration_strategy(h(10,100),f(),expected_uses=1,shared_global_available=True).strategy,'LOCAL_SUPPORT_CLOSED')
    def test_global_shared_when_reuse_crosses_break_even(self):self.assertEqual(compile_adaptive_hydration_strategy(h(30,100),f(),expected_uses=4,shared_global_available=True).strategy,'GLOBAL_SHARED')
    def test_no_shared_capability_forces_local(self):self.assertEqual(compile_adaptive_hydration_strategy(h(30,100),f(),expected_uses=10,shared_global_available=False).strategy,'LOCAL_SUPPORT_CLOSED')
    def test_stale_fixed_point_holds(self):self.assertEqual(compile_adaptive_hydration_strategy(h(),f(current=False),expected_uses=2,shared_global_available=True).status,'HOLD_SUPPORT_FIXED_POINT_STALE')
    def test_multiple_terminal_states_hold(self):self.assertEqual(compile_adaptive_hydration_strategy(h(),f(terminal=2),expected_uses=2,shared_global_available=True).status,'HOLD_SUPPORT_NOT_CONVERGED')
    def test_not_converged_holds(self):self.assertEqual(compile_adaptive_hydration_strategy(h(),f(converged=False),expected_uses=2,shared_global_available=True).status,'HOLD_SUPPORT_NOT_CONVERGED')
    def test_never_shrinks_certified_cut(self):self.assertEqual(compile_adaptive_hydration_strategy(h(60,100),f(),expected_uses=2,shared_global_available=True).certified_support_cut,('A','B'))
    def test_unready_hydration_holds(self):self.assertEqual(compile_adaptive_hydration_strategy(h(status='HOLD_ROUTE_SUPPORT'),f(),expected_uses=2,shared_global_available=True).status,'HOLD_HYDRATION_NOT_READY')
    def test_no_authority(self):
        x=compile_adaptive_hydration_strategy(h(),f(),expected_uses=1,shared_global_available=True); self.assertFalse(x.authority_minted); self.assertFalse(x.gate10)
    def test_13d_noncompensation(self):
        for tail in itertools.product(range(3),repeat=5):self.assertEqual(hard13d_strategy((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')
if __name__=='__main__':unittest.main()
