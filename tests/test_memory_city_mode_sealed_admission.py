import sys,unittest
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_coverage_membrane import (
    AdmissionMode,PositiveTrace,compile_coverage_certificate,
    compile_proof_carrying_typed_admission,TECC_SCHEMA,
)

def hx(s):return sha256(s.encode()).hexdigest()
def coverage():
    p,d,g=hx('program'),hx('domain'),3
    o=('world',)
    pos=(PositiveTrace('world',p,d,g,hx('trace'),True,True),)
    return compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=o,positive=pos)
def admission(mode=AdmissionMode.READ_ONLY,horizon=0,future=None):
    return compile_proof_carrying_typed_admission(
        typed_closure_receipt_root=hx('typed'),coverage=coverage(),support_root=hx('support'),
        influence_root=hx('influence'),transition_model_root=hx('transition'),
        future_congruence_root=future,horizon=horizon,mode=mode)
class ModeSealTests(unittest.TestCase):
    def test_read_only_ready(self):
        x=admission();self.assertEqual(x['disposition'],'READY_D0');self.assertEqual(x['admission_mode'],'READ_ONLY')
    def test_effect_bound_never_ready_here(self):
        x=admission(AdmissionMode.EFFECT_BOUND);self.assertEqual(x['disposition'],'HOLD_TECC_REQUIRED_D0');self.assertEqual(x['required_verifier_schema'],TECC_SCHEMA)
    def test_mode_binds_receipt_identity(self):
        self.assertNotEqual(admission()['receipt_root'],admission(AdmissionMode.EFFECT_BOUND)['receipt_root'])
    def test_horizon_requires_future_congruence_for_read(self):
        self.assertEqual(admission(horizon=2)['disposition'],'HOLD_D0');self.assertEqual(admission(horizon=2,future=hx('future'))['disposition'],'READY_D0')
    def test_effect_bound_still_holds_with_future_congruence(self):
        self.assertEqual(admission(AdmissionMode.EFFECT_BOUND,2,hx('future'))['disposition'],'HOLD_TECC_REQUIRED_D0')
    def test_no_authority_widening(self):
        for x in (admission(),admission(AdmissionMode.EFFECT_BOUND)):
            self.assertFalse(x['authority_minted']);self.assertFalse(x['mutation_authority']);self.assertFalse(x['effect_authority']);self.assertFalse(x['gate10'])
    def test_raw_mode_rejected(self):
        with self.assertRaises(ValueError):
            compile_proof_carrying_typed_admission(typed_closure_receipt_root=hx('t'),coverage=coverage(),support_root=hx('s'),influence_root=hx('i'),transition_model_root=hx('m'),future_congruence_root=None,horizon=0,mode='READ_ONLY')
if __name__=='__main__':unittest.main()
