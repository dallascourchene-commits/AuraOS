import random,tempfile,unittest
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import tools.awj032.training_o1_reference.training_admission as mod
from tools.awj032.training_o1_reference.training_admission import *
R=lambda s:sha256(s.encode()).hexdigest(); REPO=Path(__file__).resolve().parents[3]/'.awj032_airllm_upstream_fixture'
def targets(): return ('layers.0.q_proj','layers.0.v_proj')
def keys(ts=None): return tuple(sorted(derived_expected_adapter_keys(ts or targets())))
def vals(ks=None): ks=ks or keys(); return {k:k.encode() for k in ks}
def verifier(gen=2): return SourceAuditVerifier({'src':b'source-secret'},'src',gen)
def source(v=None): return (v or verifier())._issue_exact(observed_at=100)
def man(fam='qwen3_5',trainer='AirLLMLoRA',ts=None):
    ts=tuple(sorted(ts or targets())); ks=keys(ts); vv=vals(ks); return AdapterManifest(R('base'),R('config'),R('tok'),R('runtime'),AIRLLM_COMMIT,fam,trainer,ts,16,32,False,ks,tuple(h_bytes(vv[k]) for k in ks))
def good(m=None,src=None,v=None,**kw):
    v=v or verifier(); src=src or source(v); m=m or man(); p=dict(source_verifier=v,source=src,manifest=m,observed_base_checkpoint_root=m.base_checkpoint_root,observed_config_root=m.base_config_root,observed_tokenizer_root=m.tokenizer_root,observed_runtime_root=m.runtime_root,observed_target_paths=set(m.target_paths),provided_adapter_values=vals(m.adapter_keys),observed_at=101);p.update(kw);return admit(**p)
class T(unittest.TestCase):
    def test_valid(self):
        a=good(); self.assertEqual(a.action,'ADMIT_D0_ADAPTER_LOAD'); self.assertTrue(verifier().verify_admission(a)); self.assertEqual(a.model_family,'qwen3_5'); self.assertEqual(a.base_checkpoint_root,R('base'))
    def test_qwen38(self): self.assertEqual(good(m=man('qwen3_8_dense','AirLLMLoRA')).action,'ADMIT_D0_ADAPTER_LOAD')
    def test_qwen4(self): self.assertEqual(good(m=man('qwen4_exp','AirLLMLoRAQwen4Exp')).action,'ADMIT_D0_ADAPTER_LOAD')
    def test_glm_hold(self): self.assertEqual(good(m=man('glm_moe_dsa','AirLLMLoRA')).action,'HOLD_PORT_REQUIRED')
    def test_direct_signing_forbidden(self):
        with self.assertRaises(ValueError): verifier().sign_admission(action='ADMIT_D0_ADAPTER_LOAD')
    def test_empty_signing_key_rejected(self):
        with self.assertRaises(ValueError): SourceAuditVerifier({'src':b''},'src',2)
    def test_forged_source(self): self.assertEqual(good(src=replace(source(),mac=R('bad'))).action,'HOLD_SOURCE_RECEIPT_INVALID')
    def test_value_tamper(self):
        m=man();v=vals(m.adapter_keys);v[m.adapter_keys[0]]=b'bad';self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_VALUE_MISMATCH')
    def test_nonbytes(self):
        m=man();v=vals(m.adapter_keys);v[m.adapter_keys[0]]='bad';self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_VALUE_EVIDENCE')
    def test_missing_key(self):
        m=man();v=vals(m.adapter_keys);v.pop(m.adapter_keys[0]);self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_KEY_COVERAGE')
    def test_manifest_keys_independent(self):
        m=man()
        with self.assertRaises(ValueError): replace(m,adapter_keys=(m.adapter_keys[0],),adapter_value_roots=(m.adapter_value_roots[0],))
    def test_base_drift(self): self.assertEqual(good(observed_base_checkpoint_root=R('x')).action,'HOLD_REBIND_REQUIRED')
    def test_target_drift(self): self.assertEqual(good(observed_target_paths={'layers.0.q_proj'}).action,'HOLD_TARGET_TOPOLOGY_MISMATCH')
    def _tree(self,root):
        a=Path(root)/'air_llm/airllm';a.mkdir(parents=True);l=b'class AirLLMQwen3_5: pass\nclass AirLLMQwen4Exp: pass\nclass AirLLMLoRA(AirLLMQwen3_5): pass\nclass AirLLMLoRAQwen4Exp(AirLLMQwen4Exp): pass\n';q=b'def load_lora_state_dict(module,state):\n    owned = dict(module.named_parameters())\n    for name, value in state.items():\n        pass\n';r=b'x\n';fs={'air_llm/airllm/airllm_lora.py':l,'air_llm/airllm/lora_linear.py':q,'README.md':r}
        for rel,d in fs.items(): p=Path(root)/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d)
        return {rel:h_bytes(d) for rel,d in fs.items()}
    def test_synthetic_audit(self):
        with tempfile.TemporaryDirectory() as td:
            roots=self._tree(td)
            with patch.object(mod,'REQ_FILES',roots): self.assertTrue(verifier().verify(mod.audit_source(Path(td),AIRLLM_COMMIT,verifier(),observed_at=100)))
    @unittest.skipUnless(REPO.exists(),'pinned AirLLM fixture not provisioned')
    def test_pinned_fixture_audit(self): self.assertTrue(verifier().verify(audit_source(REPO,AIRLLM_COMMIT,verifier(),observed_at=100)))
    def test_random_tamper(self):
        rng=random.Random(41);m=man()
        for _ in range(1000):
            v=vals(m.adapter_keys);k=rng.choice(m.adapter_keys);v[k]=str(rng.random()).encode();self.assertEqual(good(m=m,provided_adapter_values=v).action,'HOLD_ADAPTER_VALUE_MISMATCH')
if __name__=='__main__': unittest.main()
