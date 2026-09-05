import itertools, os, random, sys, unittest
from dataclasses import replace
ROOT=os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT,"tools","arena"))
from proof_reuse_admission import *

def base():
    return ProofReuseEvidence("head-a","head-a","result","result","wf-1","wf-1","input","input","deps","deps","steps","steps",2,2,True,True,True)

class T(unittest.TestCase):
    def test_01_exact_reuse(self): self.assertEqual(decide(base()),Admission.REUSE_EXACT)
    def test_02_exact_head_with_changed_paths_reproves(self): self.assertEqual(decide(replace(base(),changed_paths=(".aura/CODEMAP.md",))),Admission.REPROVE)
    def test_03_generated_direct_child_rebind(self):
        e=replace(base(),current_source_head="head-b",direct_child_verified=True,trusted_generator_verified=True,changed_paths=(".aura/CODEMAP.md",".aura/CODEMAP.json")); self.assertEqual(decide(e),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
    def test_04_material_delta_reproves(self):
        e=replace(base(),current_source_head="head-b",direct_child_verified=True,trusted_generator_verified=True,changed_paths=("tools/arena/frontier27_runtime.py",)); self.assertEqual(decide(e),Admission.REPROVE)
    def test_05_unknown_or_untrusted_generator_reproves(self):
        e=replace(base(),current_source_head="head-b",direct_child_verified=True,changed_paths=(".aura/CODEMAP.md",)); self.assertEqual(decide(e),Admission.REPROVE); self.assertEqual(decide(replace(e,direct_child_verified=False,trusted_generator_verified=True)),Admission.REPROVE)
    def test_06_source_truth_is_noncompensatory(self):
        for e in (replace(base(),source_truth_bound=False),replace(base(),internal_receipt_valid=False),replace(base(),required_steps_complete=False)): self.assertEqual(decide(e),Admission.REPROVE)
    def test_07_every_identity_drift_reproves(self):
        fields={"expected_result_root":"different","expected_workflow_generation":"wf-2","expected_input_root":"different","expected_dependency_root":"different","expected_required_step_root":"different","expected_binding_generation":3}
        for name,value in fields.items(): self.assertEqual(decide(replace(base(),**{name:value})),Admission.REPROVE)
    def test_08_authority_request_never_reuses(self): self.assertEqual(decide(replace(base(),authority_requested=True)),Admission.REPROVE)
    def test_09_receipt_is_nonauthorizing_and_self_verifying(self):
        e=base(); r=make_receipt(e); self.assertTrue(r.verify(e)); self.assertFalse(r.fresh_hosted_pass); self.assertFalse(r.authority); self.assertFalse(replace(r,authority=True).verify(e)); self.assertFalse(replace(r,fresh_hosted_pass=True).verify(e))
    def test_10_receipt_tamper_rejected(self):
        e=base(); r=make_receipt(e); self.assertFalse(replace(r,evidence_root="0"*64).verify(e)); self.assertFalse(replace(r,changed_path_root="f"*64).verify(e)); self.assertFalse(r.verify(replace(e,expected_result_root="other")))
    def test_11_path_order_duplicates_canonicalize(self):
        a=replace(base(),current_source_head="b",direct_child_verified=True,trusted_generator_verified=True,changed_paths=(".aura/CODEMAP.md",".aura/CODEMAP.json",".aura/CODEMAP.md")); b=replace(a,changed_paths=(".aura/CODEMAP.json",".aura/CODEMAP.md")); self.assertEqual(evidence_digest(a),evidence_digest(b)); self.assertEqual(make_receipt(a).changed_path_root,make_receipt(b).changed_path_root)
    def test_12_bad_paths_fail_closed(self):
        for path in ("../x","/abs","a\\b",""): self.assertEqual(decide(replace(base(),current_source_head="b",direct_child_verified=True,trusted_generator_verified=True,changed_paths=(path,))),Admission.REPROVE)
    def test_13_custom_allowlist_is_exact(self):
        e=replace(base(),current_source_head="b",direct_child_verified=True,trusted_generator_verified=True,changed_paths=("generated/nav.json",)); self.assertEqual(decide(e),Admission.REPROVE); self.assertEqual(decide(e,allowlist=("generated/nav.json",)),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
    def test_14_shape_errors_fail_closed(self):
        for e in (replace(base(),proved_source_head=""),replace(base(),proved_binding_generation=-1),replace(base(),internal_receipt_valid=1)): self.assertEqual(decide(e),Admission.REPROVE)
    def test_15_omega8_hard_invalid_dominance(self):
        admits=0
        for state in itertools.product((0,1,2),repeat=8):
            e=replace(base(),internal_receipt_valid=state[0]==1,source_truth_bound=state[1]==1,required_steps_complete=state[2]==1,expected_result_root="result" if state[3]==1 else "other",expected_workflow_generation="wf-1" if state[4]==1 else "other",expected_input_root="input" if state[5]==1 else "other",expected_dependency_root="deps" if state[6]==1 else "other",expected_required_step_root="steps" if state[7]==1 else "other")
            d=decide(e); admits += d==Admission.REUSE_EXACT
            if any(x==0 for x in state): self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1)
    def test_16_13d_context_cannot_repair_hard_failure(self):
        bad=replace(base(),source_truth_bound=False)
        for trailing in itertools.product((0,1,2),repeat=5): self.assertEqual(decide(bad),Admission.REPROVE)
    def test_17_randomized_independent_oracle(self):
        rng=random.Random(27027)
        for _ in range(50000):
            exact,truth,receipt,steps,roots,direct,trusted,generated=[rng.choice((True,False)) for _ in range(8)]
            changed=() if exact else ((".aura/CODEMAP.md",) if generated else ("src/material.py",))
            e=replace(base(),current_source_head="head-a" if exact else "head-b",internal_receipt_valid=receipt,source_truth_bound=truth,required_steps_complete=steps,expected_result_root="result" if roots else "other",direct_child_verified=direct,trusted_generator_verified=trusted,changed_paths=changed)
            good=receipt and truth and steps and roots
            oracle=Admission.REUSE_EXACT if good and exact else Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND if good and (not exact) and direct and trusted and generated else Admission.REPROVE
            self.assertEqual(decide(e),oracle)

if __name__=="__main__": unittest.main()
