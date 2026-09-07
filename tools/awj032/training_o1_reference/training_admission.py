from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import ast, hmac, json

SCHEMA='AURA-AWJ032-AIRLLM-TRAINING-ADMISSION-v4'
AIRLLM_COMMIT='55e435087d951da8c25ab3672e969025241a398e'
REQ_FILES={
'air_llm/airllm/airllm_lora.py':'442c70a85a53603089ce14604bdc48550e343e3b3405dccc080a4d841bc50172',
'air_llm/airllm/lora_linear.py':'acda13718742c7f79c2713b04d06787c81999a85d6792aa1fa836ab77e1745f5',
'README.md':'746f35e0bee6598643666792c050c8833b5d441d36e0a60dd0846ae0d34ece73'}
FAMILY_ROUTES={'qwen3_5':'ADMIT_SOURCE_FAMILY','qwen3_8_dense':'ADMIT_SOURCE_FAMILY','qwen4_exp':'ADMIT_SOURCE_FAMILY','glm_moe_dsa':'HOLD_PORT_REQUIRED','glm':'HOLD_PORT_REQUIRED'}
HEX=set('0123456789abcdef')
def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def jhash(v): return sha256(canon(v)).hexdigest()
def h_bytes(data):
    if not isinstance(data,(bytes,bytearray,memoryview)): raise TypeError('observed adapter/source value must be bytes-like')
    return sha256(bytes(data)).hexdigest()
def isroot(v): return isinstance(v,str) and len(v)==64 and set(v)<=HEX
def needroot(v,n):
    if not isroot(v): raise ValueError(f'{n}: lowercase sha256 required')
def valid_int(v): return type(v) is int

def _validate_keyring(keys,active,generation,label):
    if not active or active not in keys or not valid_int(generation) or generation<1: raise ValueError(label)
    if not isinstance(keys[active],(bytes,bytearray)) or not keys[active]: raise ValueError(label)

@dataclass(frozen=True)
class SourceReceipt:
    commit:str; file_roots:tuple[tuple[str,str],...]; family_routes:tuple[tuple[str,str],...]
    partial_load_guard_required:bool; provenance_envelope_required:bool
    key_id:str; verifier_generation:int; observed_at:int; mac:str
    def __post_init__(self):
        if self.commit!=AIRLLM_COMMIT or self.file_roots!=tuple(sorted(REQ_FILES.items())) or self.family_routes!=tuple(sorted(FAMILY_ROUTES.items())): raise ValueError('source audit drift')
        if not self.partial_load_guard_required or not self.provenance_envelope_required: raise ValueError('source audit flags drift')
        if not self.key_id or not valid_int(self.verifier_generation) or self.verifier_generation<1 or not valid_int(self.observed_at) or self.observed_at<0: raise ValueError('invalid source receipt metadata')
        needroot(self.mac,'mac')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'source_audit','commit':self.commit,'file_roots':self.file_roots,'family_routes':self.family_routes,'partial_load_guard_required':self.partial_load_guard_required,'provenance_envelope_required':self.provenance_envelope_required,'key_id':self.key_id,'verifier_generation':self.verifier_generation,'observed_at':self.observed_at}
    @property
    def receipt_root(self): return jhash({**self.signed_payload,'mac':self.mac})
    def route(self,family): return dict(self.family_routes).get(family,'HOLD_UNKNOWN')

@dataclass(frozen=True)
class AdapterManifest:
    base_checkpoint_root:str; base_config_root:str; tokenizer_root:str; runtime_root:str; airllm_commit:str
    family:str; trainer_class:str; target_paths:tuple[str,...]; lora_r:int; lora_alpha:int; packed_experts:bool
    adapter_keys:tuple[str,...]; adapter_value_roots:tuple[str,...]
    def __post_init__(self):
        for n in ('base_checkpoint_root','base_config_root','tokenizer_root','runtime_root'): needroot(getattr(self,n),n)
        if self.airllm_commit!=AIRLLM_COMMIT: raise ValueError('airllm commit drift')
        if not valid_int(self.lora_r) or self.lora_r<1 or not valid_int(self.lora_alpha) or self.lora_alpha<=0: raise ValueError('invalid LoRA hyperparameters')
        if not self.target_paths or self.target_paths!=tuple(sorted(set(self.target_paths))): raise ValueError('target paths must be nonempty canonical tuple')
        if self.adapter_keys!=tuple(sorted(derived_expected_adapter_keys(self.target_paths))): raise ValueError('adapter keys must be independently derived canonical set')
        if len(self.adapter_keys)!=len(self.adapter_value_roots): raise ValueError('key/value root cardinality mismatch')
        for v in self.adapter_value_roots: needroot(v,'adapter_value_root')
    @property
    def identity_root(self): return jhash({'schema':SCHEMA,'kind':'adapter_manifest',**asdict(self)})
    @property
    def adapter_values_root(self): return jhash(self.adapter_value_roots)

def derived_expected_adapter_keys(target_paths): return {f'{p}.lora_A' for p in target_paths}|{f'{p}.lora_B' for p in target_paths}
def target_topology_root(target_paths): return jhash(tuple(sorted(target_paths)))
def expected_family_trainer(family):
    if family in ('qwen3_5','qwen3_8_dense'): return 'AirLLMLoRA'
    if family=='qwen4_exp': return 'AirLLMLoRAQwen4Exp'
    return None

@dataclass(frozen=True)
class Admission:
    action:str; reason:str; source_root:str; adapter_root:str; runtime_root:str; target_topology_root:str
    base_checkpoint_root:str; base_config_root:str; tokenizer_root:str; adapter_values_root:str
    model_family:str; trainer_class:str; key_id:str; verifier_generation:int; observed_at:int; mac:str
    authority:str='D0_NONPROMOTING'; gate10:bool=False
    def __post_init__(self):
        for n in ('source_root','adapter_root','runtime_root','target_topology_root','base_checkpoint_root','base_config_root','tokenizer_root','adapter_values_root','mac'): needroot(getattr(self,n),n)
        if not self.model_family or not self.trainer_class or not self.key_id or not valid_int(self.verifier_generation) or self.verifier_generation<1 or not valid_int(self.observed_at) or self.observed_at<0: raise ValueError('admission metadata')
        if self.authority!='D0_NONPROMOTING' or self.gate10: raise ValueError('authority widening forbidden')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'adapter_admission','action':self.action,'reason':self.reason,'source_root':self.source_root,'adapter_root':self.adapter_root,'runtime_root':self.runtime_root,'target_topology_root':self.target_topology_root,'base_checkpoint_root':self.base_checkpoint_root,'base_config_root':self.base_config_root,'tokenizer_root':self.tokenizer_root,'adapter_values_root':self.adapter_values_root,'model_family':self.model_family,'trainer_class':self.trainer_class,'key_id':self.key_id,'verifier_generation':self.verifier_generation,'observed_at':self.observed_at,'authority':self.authority,'gate10':self.gate10}
    @property
    def admission_root(self): return jhash({**self.signed_payload,'mac':self.mac})

class SourceAuditVerifier:
    def __init__(self,keys:dict[str,bytes],active_key_id:str,generation:int):
        _validate_keyring(keys,active_key_id,generation,'invalid source verifier configuration')
        self._keys={k:bytes(v) for k,v in keys.items()}; self.active_key_id=active_key_id; self.generation=generation
    @staticmethod
    def _mac(key,payload): return hmac.new(key,canon(payload),sha256).hexdigest()
    def _issue_exact(self,*,observed_at:int):
        if not valid_int(observed_at) or observed_at<0: raise ValueError('invalid observed_at')
        p={'schema':SCHEMA,'kind':'source_audit','commit':AIRLLM_COMMIT,'file_roots':tuple(sorted(REQ_FILES.items())),'family_routes':tuple(sorted(FAMILY_ROUTES.items())),'partial_load_guard_required':True,'provenance_envelope_required':True,'key_id':self.active_key_id,'verifier_generation':self.generation,'observed_at':observed_at}
        return SourceReceipt(AIRLLM_COMMIT,tuple(sorted(REQ_FILES.items())),tuple(sorted(FAMILY_ROUTES.items())),True,True,self.active_key_id,self.generation,observed_at,self._mac(self._keys[self.active_key_id],p))
    def verify(self,r:SourceReceipt):
        if r.key_id!=self.active_key_id or r.key_id not in self._keys or r.verifier_generation!=self.generation: return False
        try: SourceReceipt(r.commit,r.file_roots,r.family_routes,r.partial_load_guard_required,r.provenance_envelope_required,r.key_id,r.verifier_generation,r.observed_at,r.mac)
        except ValueError: return False
        return hmac.compare_digest(self._mac(self._keys[r.key_id],r.signed_payload),r.mac)
    def verify_admission(self,a:Admission):
        if a.key_id!=self.active_key_id or a.key_id not in self._keys or a.verifier_generation!=self.generation: return False
        return hmac.compare_digest(self._mac(self._keys[a.key_id],a.signed_payload),a.mac)
    def sign_admission(self,**kwargs):
        raise ValueError('direct admission signing forbidden; use admit() validation path')


def _issue_validated_admission(verifier:SourceAuditVerifier,*,action,reason,source_root,manifest:AdapterManifest,target_root,observed_at):
    p={'schema':SCHEMA,'kind':'adapter_admission','action':action,'reason':reason,'source_root':source_root,'adapter_root':manifest.identity_root,'runtime_root':manifest.runtime_root,'target_topology_root':target_root,'base_checkpoint_root':manifest.base_checkpoint_root,'base_config_root':manifest.base_config_root,'tokenizer_root':manifest.tokenizer_root,'adapter_values_root':manifest.adapter_values_root,'model_family':manifest.family,'trainer_class':manifest.trainer_class,'key_id':verifier.active_key_id,'verifier_generation':verifier.generation,'observed_at':observed_at,'authority':'D0_NONPROMOTING','gate10':False}
    return Admission(action,reason,source_root,manifest.identity_root,manifest.runtime_root,target_root,manifest.base_checkpoint_root,manifest.base_config_root,manifest.tokenizer_root,manifest.adapter_values_root,manifest.family,manifest.trainer_class,verifier.active_key_id,verifier.generation,observed_at,verifier._mac(verifier._keys[verifier.active_key_id],p))

def _class_bases(tree): return {n.name:tuple(ast.unparse(b) for b in n.bases) for n in tree.body if isinstance(n,ast.ClassDef)}
def _function_text(source,name):
    tree=ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name: return ast.get_source_segment(source,node) or ast.unparse(node)
    return ''
def audit_source(repo:Path,commit:str,verifier:SourceAuditVerifier,*,observed_at:int):
    if commit!=AIRLLM_COMMIT: raise ValueError('unbound AirLLM commit')
    for rel,expected in REQ_FILES.items():
        got=h_bytes((repo/rel).read_bytes())
        if got!=expected: raise ValueError(f'source drift {rel}: {got}')
    lora=(repo/'air_llm/airllm/airllm_lora.py').read_text(); linear=(repo/'air_llm/airllm/lora_linear.py').read_text(); bases=_class_bases(ast.parse(lora))
    if bases.get('AirLLMLoRA')!=('AirLLMQwen3_5',) or bases.get('AirLLMLoRAQwen4Exp')!=('AirLLMQwen4Exp',): raise ValueError('trainer ancestry drift')
    load=_function_text(linear,'load_lora_state_dict')
    if 'owned = dict(module.named_parameters())' not in load or 'for name, value in state.items()' not in load: raise ValueError('loader structure changed')
    if not ('set(state)' not in load and 'state.keys()' not in load) or not ('base_checkpoint_root' not in linear and 'tokenizer_root' not in linear and 'runtime_root' not in linear): raise ValueError('upstream contract changed; re-audit required')
    return verifier._issue_exact(observed_at=observed_at)

def admit(*,source_verifier:SourceAuditVerifier,source:SourceReceipt,manifest:AdapterManifest,observed_base_checkpoint_root:str,observed_config_root:str,observed_tokenizer_root:str,observed_runtime_root:str,observed_target_paths:set[str],provided_adapter_values:dict[str,bytes],observed_at:int):
    if not valid_int(observed_at) or observed_at<0: raise ValueError('observed_at')
    target_root=target_topology_root(observed_target_paths)
    def out(action,reason): return _issue_validated_admission(source_verifier,action=action,reason=reason,source_root=source.receipt_root,manifest=manifest,target_root=target_root,observed_at=observed_at)
    if not source_verifier.verify(source): return out('HOLD_SOURCE_RECEIPT_INVALID','SOURCE_AUDIT_NOT_AUTHENTICATED')
    if source.route(manifest.family)=='HOLD_PORT_REQUIRED': return out('HOLD_PORT_REQUIRED','CURRENT_AIRLLM_STREAMED_TRAINER_IS_QWEN_SPECIFIC')
    want=expected_family_trainer(manifest.family)
    if want is None or manifest.trainer_class!=want: return out('HOLD_FAMILY_MISMATCH','TRAINER_FAMILY_MISMATCH')
    if (observed_base_checkpoint_root,observed_config_root,observed_tokenizer_root,observed_runtime_root)!=(manifest.base_checkpoint_root,manifest.base_config_root,manifest.tokenizer_root,manifest.runtime_root): return out('HOLD_REBIND_REQUIRED','BASE_CONFIG_TOKENIZER_OR_RUNTIME_DRIFT')
    observed_targets=set(observed_target_paths)
    if tuple(sorted(observed_targets))!=manifest.target_paths: return out('HOLD_TARGET_TOPOLOGY_MISMATCH','TARGET_MODULE_TOPOLOGY_DRIFT')
    expected_keys=tuple(sorted(derived_expected_adapter_keys(observed_targets)))
    if manifest.adapter_keys!=expected_keys: return out('HOLD_MANIFEST_KEY_TOPOLOGY','MANIFEST_KEYS_NOT_DERIVED_FROM_OBSERVED_TARGETS')
    if not isinstance(provided_adapter_values,dict) or tuple(sorted(provided_adapter_values))!=expected_keys: return out('HOLD_ADAPTER_KEY_COVERAGE','PROVIDED_ADAPTER_KEY_SET_NOT_EXACT')
    try: observed_roots=tuple(h_bytes(provided_adapter_values[k]) for k in manifest.adapter_keys)
    except TypeError: return out('HOLD_ADAPTER_VALUE_EVIDENCE','ADAPTER_VALUES_NOT_OBSERVED_BYTES')
    if observed_roots!=manifest.adapter_value_roots: return out('HOLD_ADAPTER_VALUE_MISMATCH','OBSERVED_ADAPTER_VALUES_DIFFER_FROM_MANIFEST')
    return out('ADMIT_D0_ADAPTER_LOAD','EXACT_AUTHENTICATED_SOURCE_BASE_RUNTIME_TARGET_KEY_AND_VALUE_EVIDENCE')

def omega8(bits): return len(bits)==8 and all(v==1 for v in bits)
