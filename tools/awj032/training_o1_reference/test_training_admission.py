import random, unittest, tempfile
from dataclasses import replace
from hashlib import sha256
from itertools import product
from pathlib import Path
from unittest.mock import patch
import tools.awj032.training_o1_reference.training_admission as mod
from tools.awj032.training_o1_reference.training_admission import *
R=lambda s:sha256(s.encode()).hexdigest()
REPO=Path(__file__).resolve().parents[4]/'.awj032_airllm_upstream_fixture'

def targets(): return ('layers.0.q_proj','layers.0.v_proj')
def keys(ts=None): return tuple(sorted(derived_expected_adapter_keys(ts or targets())))
def vals(ks=None):
    ks=ks or keys(); return {k:k.encode() for k in ks}
def verifier(gen=2): return SourceAuditVerifier({'src':b'source-secret'},'src',gen)
def source(v=None): return (v or verifier())._issue_exact(observed_at=100)
def man(fam='qwen3_5',trainer='AirLLMLoRA',ts=None):
    ts=tuple(sorted(ts or targets())); ks=keys(ts); vv=vals(ks)
    return AdapterManifest(R('base'),R('config'),R('tok'),R('runtime'),AIRLLM_COMMIT,fam,trainer,ts,16,32,False,ks,tuple(h_bytes(vv[k]) for k in ks))
def good(m=None,src=None,v=None,**kw):
    v=v or verifier(); src=src or source(v); m=m or man(); p=dict(source_verifier=v,source=src,manifest=m,
        observed_base_checkpoint_root=m.base_checkpoint_root,observed_config_root=m.base_config_root,
        observed_tokenizer_root=m.tokenizer_root,observed_runtime_root=m.runtime_root,
        observed_target_paths=set(m.target_paths),provided_adapter_values=vals(m.adapter_keys),observed_at=101); p.update(kw); return admit(**p)

class TrainingAdmissionTest(unittest.TestCase):
    def test_valid(self):
        a=good(); self.assertEqual(a.action,'ADMIT_D0_ADAPTER_LOAD'); self.assertTrue(verifier().verify_admission(a))
    def test_qwen38_consistent(self): self.assertEqual(good(m=man('qwen3_8_dense','AirLLMLoRA')).action,'ADMIT_D0_ADAPTER_LOAD')
    def test_qwen4(self): self.assertEqual(good(m=man('qwen4_exp','AirLLMLoRAQwen4Exp')).action,'ADMIT_D0_ADAPTER_LOAD')
    def test_glm_hold(self): self.assertEqual(good(m=man('glm_moe_dsa','AirLLMLoRA')).action,'HOLD_PORT_REQUIRED')
    def test_forged_source_signature(self):
        v=verifier(); s=source(v); bad=replace(s,mac=R('bad')); self.assertEqual(good(src=bad,v=v).action,'HOLD_SOURCE_RECEIPT_INVALID')
    def test_source_generation_currentness(self):
        old=verifier(1); new=verifier(2); self.assertEqual(good(src=source(old),v=new).action,'HOLD_SOURCE_RECEIPT_INVALID')
    def test_deep_immutable(self):
        s=source(); self.assertIsInstance(s.file_roots,tuple); self.assertIsInstance(s.family_routes,tuple)
    def test_base_drift(self): self.assertEqual(good(observed_base_checkpoint_root=R('x')).action,'HOLD_REBIND_REQUIRED')
    def test_target_drift(self): self.assertEqual(good(observed_target_paths={'layers.0.q_proj'}).action,'HOLD_TARGET_TOPOLOGY_MISMATCH')
    def test_manifest_keys_independently_derived(self):
        m=man()
        with self.assertRaises(ValueError): AdapterManifest(m.base_checkpoint_root,m.base_config_root,m.tokenizer_root,m.runtime_root,AIRLLM_COMMIT,m.family,m.trainer_class,m.target_paths,16,32,False,(m.adapter_keys[0],),(m.adapter_value_roots[0],))
    def test_value_tamper(self):
        m=man(); v=vals(m.adapter_keys); v[m.adapter_keys[0]]=b'tampered'; self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_VALUE_MISMATCH')
    def test_nonbytes(self):
        m=man(); v=vals(m.adapter_keys); v[m.adapter_keys[0]]='oops'; self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_VALUE_EVIDENCE')
    def test_missing_key(self):
        m=man(); v=vals(m.adapter_keys); v.pop(m.adapter_keys[0]); self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_KEY_COVERAGE')
    def test_wrong_trainer(self): self.assertEqual(good(m=man(trainer='AirLLMLoRAQwen4Exp')).action,'HOLD_FAMILY_MISMATCH')
    def _synthetic_source_tree(self, root):
        a=Path(root)/'air_llm/airllm'; a.mkdir(parents=True)
        lora='class AirLLMQwen3_5: pass\nclass AirLLMQwen4Exp: pass\nclass AirLLMLoRA(AirLLMQwen3_5): pass\nclass AirLLMLoRAQwen4Exp(AirLLMQwen4Exp): pass\n'
        linear='def load_lora_state_dict(module,state):\n    owned = dict(module.named_parameters())\n    for name, value in state.items():\n        pass\n'
        readme='synthetic pinned-audit fixture\n'
        files={'air_llm/airllm/airllm_lora.py':lora.encode(),'air_llm/airllm/lora_linear.py':linear.encode(),'README.md':readme.encode()}
        for rel,data in files.items(): q=Path(root)/rel; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(data)
        return {rel:h_bytes(data) for rel,data in files.items()}
    def test_source_audit_runs_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            roots=self._synthetic_source_tree(td)
            with patch.object(mod,'REQ_FILES',roots):
                v=verifier(); r=mod.audit_source(Path(td),AIRLLM_COMMIT,v,observed_at=100); self.assertTrue(v.verify(r))
    def test_source_audit_detects_drift_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            roots=self._synthetic_source_tree(td); (Path(td)/'README.md').write_text('drift')
            with patch.object(mod,'REQ_FILES',roots):
                with self.assertRaises(ValueError): mod.audit_source(Path(td),AIRLLM_COMMIT,verifier(),observed_at=100)
    def test_random_adapter_tamper(self):
        rng=random.Random(41); m=man()
        for _ in range(3000):
            v=vals(m.adapter_keys); k=rng.choice(m.adapter_keys); v[k]=str(rng.random()).encode()
            self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_VALUE_MISMATCH')
    def test_random_runtime_drift(self):
        rng=random.Random(7)
        for _ in range(3000): self.assertEqual(good(observed_runtime_root=R(str(rng.random()))).action,'HOLD_REBIND_REQUIRED')
    def test_omega8(self): self.assertEqual(1,sum(omega8(x) for x in product((0,1),repeat=8)))

if __name__=='__main__': unittest.main()
