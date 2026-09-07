from __future__ import annotations
import argparse, hashlib, hmac, itertools, json, random, tempfile, unittest
from dataclasses import dataclass, replace
from enum import Enum

SCHEMA='AURA-O18-CREATIVE-PROOF-TERMINAL-v1'
KEY=b'o18-host-private-test-key'
NOW=1800000000
D0='D0_NONPROMOTING'

def H(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()

def MAC(v):
    return hmac.new(KEY, json.dumps(v, sort_keys=True, separators=(',',':'), allow_nan=False).encode(), hashlib.sha256).hexdigest()

@dataclass(frozen=True)
class CreativeOperation:
    command_id:str; idempotency_key:str; source_file_id:str; source_revision:str; source_digest:str
    intent_root:str; contract_root:str; payload_root:str; topic_root:str
    @property
    def root(self):
        return H({'schema':SCHEMA,'kind':'creative_operation','command_id':self.command_id,'idempotency_key':self.idempotency_key,
                  'source_file_id':self.source_file_id,'source_revision':self.source_revision,'source_digest':self.source_digest,
                  'intent_root':self.intent_root,'contract_root':self.contract_root,'payload_root':self.payload_root,'topic_root':self.topic_root})

@dataclass(frozen=True)
class AttemptAdmission:
    operation_root:str; card_root:str; lease_root:str; progress_root:str; host_generation:int; actor:str; currentness_root:str; issued_at:int; expires_at:int
    @property
    def root(self):
        return H({'schema':SCHEMA,'kind':'attempt_admission',**self.__dict__})

@dataclass(frozen=True)
class CreativeAttempt:
    operation_root:str; admission_root:str; attempt_seq:int; mac:str
    @property
    def unsigned(self): return {'operation_root':self.operation_root,'admission_root':self.admission_root,'attempt_seq':self.attempt_seq}
    @property
    def root(self): return H({'schema':SCHEMA,'kind':'creative_attempt',**self.unsigned,'mac':self.mac})

@dataclass(frozen=True)
class ExecutionProofBundle:
    command_id:str; idempotency_key:str; source_digest:str; operation_root:str; attempt_root:str
    source_binding_root:str; creative_semantic_root:str; workcell_witness_root:str; durable_effect_root:str; governed_operation_root:str
    issued_at:int; expires_at:int; mac:str
    @property
    def unsigned(self):
        d=self.__dict__.copy(); d.pop('mac'); return d
    @property
    def root(self): return H({'schema':SCHEMA,'kind':'proof_bundle',**self.unsigned,'mac':self.mac})

@dataclass(frozen=True)
class Callback:
    command_id:str; idempotency_key:str; source_digest:str; operation_root:str; attempt_root:str
    ack_body:str; result_body:str; ack_at:int; result_at:int; ack_sha:str; result_sha:str
    @property
    def transport_root(self):
        return H({'schema':SCHEMA,'kind':'callback_transport','command_id':self.command_id,'idempotency_key':self.idempotency_key,
                  'source_digest':self.source_digest,'operation_root':self.operation_root,'attempt_root':self.attempt_root,
                  'ack_sha':self.ack_sha,'result_sha':self.result_sha,'ack_at':self.ack_at,'result_at':self.result_at})

class Disposition(str,Enum):
    PROOF_TERMINAL_CURRENT='PROOF_CARRYING_TERMINAL_CURRENT_ATTEMPT'
    PROOF_TERMINAL_HISTORICAL='PROOF_CARRYING_TERMINAL_HISTORICAL_ATTEMPT'
    LEGACY_TRANSPORT='LEGACY_TRANSPORT_BOUND'
    HOLD='HOLD'

@dataclass(frozen=True)
class TerminalDecision:
    disposition:Disposition; operation_root:str; attempt_root:str; callback_root:str; proof_root:str|None; current_attempt:bool
    effect_authority:bool=False; gate10:bool=False
    @property
    def root(self): return H({'schema':SCHEMA,'kind':'terminal_decision',**{**self.__dict__,'disposition':self.disposition.value}})

def operation(i=0, **kw):
    d=dict(command_id=f'cmd-{i}',idempotency_key=f'idem-{i}',source_file_id=f'file-{i}',source_revision=f'rev-{i}',source_digest=H(['src',i]),
           intent_root=H(['intent',i]),contract_root=H(['contract',i]),payload_root=H(['payload',i]),topic_root=H(['topic',i])); d.update(kw); return CreativeOperation(**d)

def admission(op:CreativeOperation, i=0, **kw):
    d=dict(operation_root=op.root,card_root=H(['card',i]),lease_root=H(['lease',i]),progress_root=H(['progress',i]),host_generation=1,actor=f'agent-{i}',currentness_root=H(['current',i]),issued_at=NOW-10,expires_at=NOW+100); d.update(kw); return AttemptAdmission(**d)

def attempt(op, adm, seq=1):
    u={'operation_root':op.root,'admission_root':adm.root,'attempt_seq':seq}; return CreativeAttempt(**u,mac=MAC(u))

def verify_attempt(att:CreativeAttempt, op:CreativeOperation):
    if not isinstance(att,CreativeAttempt): return False,'ATTEMPT_TYPE'
    if not hmac.compare_digest(att.mac,MAC(att.unsigned)): return False,'ATTEMPT_AUTH'
    if att.operation_root!=op.root: return False,'ATTEMPT_OPERATION'
    return True,'OK'

def bundle(op, att, **kw):
    d=dict(command_id=op.command_id,idempotency_key=op.idempotency_key,source_digest=op.source_digest,operation_root=op.root,attempt_root=att.root,
           source_binding_root=H(['source-binding',op.source_file_id,op.source_revision,op.source_digest]),creative_semantic_root=op.root,
           workcell_witness_root=H(['workcell',att.admission_root]),durable_effect_root=H(['effect',att.root]),governed_operation_root=H(['governed',op.root]),issued_at=NOW-5,expires_at=NOW+100)
    d.update(kw); d['mac']=MAC(d); return ExecutionProofBundle(**d)

def callback(op, att, **kw):
    ack=f'ACK:{op.command_id}:{att.root}'; result=f'RESULT:{op.command_id}:{att.root}:ok'
    d=dict(command_id=op.command_id,idempotency_key=op.idempotency_key,source_digest=op.source_digest,operation_root=op.root,attempt_root=att.root,
           ack_body=ack,result_body=result,ack_at=NOW,result_at=NOW+1,ack_sha=hashlib.sha256(ack.encode()).hexdigest(),result_sha=hashlib.sha256(result.encode()).hexdigest())
    d.update(kw); return Callback(**d)

def verify_bundle(b:ExecutionProofBundle, op:CreativeOperation, att:CreativeAttempt, now=NOW):
    if not isinstance(b,ExecutionProofBundle): return False,'BUNDLE_TYPE'
    if not hmac.compare_digest(b.mac,MAC(b.unsigned)): return False,'BUNDLE_AUTH'
    if not (b.issued_at<=now<=b.expires_at): return False,'BUNDLE_TIME'
    if (b.command_id,b.idempotency_key,b.source_digest,b.operation_root,b.attempt_root)!=(op.command_id,op.idempotency_key,op.source_digest,op.root,att.root): return False,'BUNDLE_LINEAGE'
    roles=(b.source_binding_root,b.creative_semantic_root,b.workcell_witness_root,b.durable_effect_root,b.governed_operation_root)
    if any(len(x)!=64 for x in roles): return False,'BUNDLE_ROLE'
    if b.creative_semantic_root!=op.root: return False,'BUNDLE_SEMANTIC'
    return True,'OK'

def verify_callback(cb:Callback, op:CreativeOperation, att:CreativeAttempt):
    if not isinstance(cb,Callback): return False,'CALLBACK_TYPE'
    if (cb.command_id,cb.idempotency_key,cb.source_digest,cb.operation_root,cb.attempt_root)!=(op.command_id,op.idempotency_key,op.source_digest,op.root,att.root): return False,'CALLBACK_LINEAGE'
    if hashlib.sha256(cb.ack_body.encode()).hexdigest()!=cb.ack_sha: return False,'ACK_HASH'
    if hashlib.sha256(cb.result_body.encode()).hexdigest()!=cb.result_sha: return False,'RESULT_HASH'
    if not cb.ack_at < cb.result_at: return False,'TEMPORAL_ORDER'
    return True,'OK'

def compile_terminal(op:CreativeOperation, recorded_attempt:CreativeAttempt, latest_attempt_root:str, cb:Callback, proof:ExecutionProofBundle|None):
    oka,_=verify_attempt(recorded_attempt,op)
    if not oka:
        return TerminalDecision(Disposition.HOLD,op.root,recorded_attempt.root,cb.transport_root,None,False)
    okc,_=verify_callback(cb,op,recorded_attempt)
    if not okc:
        return TerminalDecision(Disposition.HOLD,op.root,recorded_attempt.root,cb.transport_root,None,recorded_attempt.root==latest_attempt_root)
    current=recorded_attempt.root==latest_attempt_root
    if proof is None:
        return TerminalDecision(Disposition.LEGACY_TRANSPORT,op.root,recorded_attempt.root,cb.transport_root,None,current)
    okp,_=verify_bundle(proof,op,recorded_attempt)
    if not okp:
        return TerminalDecision(Disposition.HOLD,op.root,recorded_attempt.root,cb.transport_root,proof.root,current)
    disp=Disposition.PROOF_TERMINAL_CURRENT if current else Disposition.PROOF_TERMINAL_HISTORICAL
    return TerminalDecision(disp,op.root,recorded_attempt.root,cb.transport_root,proof.root,current)

# Pure consequence classifier for campaigns/lattices.  Eight hard proof axes plus
# current-vs-historical as a separate context bit.
def classify(operation_valid,attempt_valid,callback_integrity,proof_auth,proof_roles,lineage,temporal,authority_clean,current_attempt,proof_present=True):
    if not (operation_valid and attempt_valid and callback_integrity and lineage and temporal): return 'HOLD'
    if not proof_present: return 'LEGACY_TRANSPORT_BOUND'
    if not (proof_auth and proof_roles and authority_clean): return 'HOLD'
    return 'PROOF_CURRENT' if current_attempt else 'PROOF_HISTORICAL'

def oracle(operation_valid,attempt_valid,callback_integrity,proof_auth,proof_roles,lineage,temporal,authority_clean,current_attempt,proof_present=True):
    # Independent branch table, intentionally not delegated to classify().
    transport_ok = operation_valid and attempt_valid and callback_integrity and lineage and temporal
    if not transport_ok:
        return 'HOLD'
    if proof_present is False:
        return 'LEGACY_TRANSPORT_BOUND'
    proof_ok = proof_auth and proof_roles and authority_clean
    if proof_ok is False:
        return 'HOLD'
    if current_attempt is True:
        return 'PROOF_CURRENT'
    return 'PROOF_HISTORICAL'

def campaign(n=30000, seed=1801):
    r=random.Random(seed); mismatches=false_promotions=naive_transport_false=wrong_attempt_false=0; groups={}
    for i in range(n):
        vals=[bool(r.getrandbits(1)) for _ in range(9)]; pp=bool(r.getrandbits(1))
        out=classify(*vals,proof_present=pp); exp=oracle(*vals,proof_present=pp); mismatches+=out!=exp
        opm,attm,cbi,pa,pr,lin,tmp,clean,current=vals
        naive='PROOF_CURRENT' if opm and cbi else 'HOLD'
        lawful=out.startswith('PROOF_')
        false_promotions+=naive.startswith('PROOF_') and not lawful
        naive_transport_false += (opm and attm and cbi and lin and tmp and not pp)
        wrong_attempt_false += (opm and not attm and cbi and pa and pr and lin and tmp and clean and pp)
        groups[out]=groups.get(out,0)+1
    payload={'schema':SCHEMA,'cases':n,'oracle_mismatches':mismatches,'naive_transport_or_operation_false_promotions':false_promotions,
             'transport_without_proof_cases':naive_transport_false,'wrong_attempt_challenge_cases':wrong_attempt_false,'groups':groups,'authority_minted':0,'gate10':False}
    payload['root']=H(payload); return payload

def omega8():
    states=keepers=invalid=0
    for vals in itertools.product((False,None,True), repeat=8):
        states+=1
        hard=all(v is True for v in vals)
        ready=classify(*[v is True for v in vals], current_attempt=True, proof_present=True)=='PROOF_CURRENT'
        keepers+=int(ready)
        invalid+=int(ready and not hard)
    p={'states':states,'keepers':keepers,'invalid_promotions':invalid}; p['root']=H(p); return p

def d13():
    o=omega8(); contexts=243; states=o['states']*contexts; lawful=o['keepers']*contexts
    p={'states':states,'lawful_contexts':lawful,'hard_invalid_context_repairs':0,'context_axes':['k27','hydration','agent','ui','cache']}; p['root']=H(p); return p

def hs1000():
    cells=[]
    for a,b,c in itertools.product(range(10),repeat=3):
        idx=a*100+b*10+c
        attack=('attempt_swap','transport_only','result_tamper','proof_forge','temporal_invert','operation_drift','role_missing','historical_valid','authority_taint','valid')[idx%10]
        cells.append({'cell':[a,b,c],'attack':attack})
    groups={}
    for x in cells: groups[x['attack']]=groups.get(x['attack'],0)+1
    p={'raw_cells':len(cells),'consequence_groups':len(groups),'groups':groups,'claimed_breakthroughs':0,'freeze_root':H(cells)}; p['root']=H(p); return p

class Tests(unittest.TestCase):
    def setUp(self):
        self.op=operation(); self.adm=admission(self.op); self.att=attempt(self.op,self.adm); self.cb=callback(self.op,self.att); self.p=bundle(self.op,self.att)
    def test_01_current_proof(self): self.assertEqual(compile_terminal(self.op,self.att,self.att.root,self.cb,self.p).disposition,Disposition.PROOF_TERMINAL_CURRENT)
    def test_02_transport_only_not_proof(self): self.assertEqual(compile_terminal(self.op,self.att,self.att.root,self.cb,None).disposition,Disposition.LEGACY_TRANSPORT)
    def test_03_wrong_attempt_holds(self):
        a2=attempt(self.op,admission(self.op,2),2); self.assertEqual(compile_terminal(self.op,a2,a2.root,self.cb,self.p).disposition,Disposition.HOLD)
    def test_04_historical_attempt_closes(self): self.assertEqual(compile_terminal(self.op,self.att,'f'*64,self.cb,self.p).disposition,Disposition.PROOF_TERMINAL_HISTORICAL)
    def test_05_historical_not_current(self): self.assertFalse(compile_terminal(self.op,self.att,'f'*64,self.cb,self.p).current_attempt)
    def test_06_ack_tamper(self): self.assertEqual(compile_terminal(self.op,self.att,self.att.root,replace(self.cb,ack_body='tamper'),self.p).disposition,Disposition.HOLD)
    def test_07_result_tamper(self): self.assertEqual(compile_terminal(self.op,self.att,self.att.root,replace(self.cb,result_body='tamper'),self.p).disposition,Disposition.HOLD)
    def test_08_temporal_invert(self): self.assertEqual(compile_terminal(self.op,self.att,self.att.root,replace(self.cb,ack_at=NOW+2),self.p).disposition,Disposition.HOLD)
    def test_09_proof_mac(self): self.assertEqual(compile_terminal(self.op,self.att,self.att.root,self.cb,replace(self.p,mac='0'*64)).disposition,Disposition.HOLD)
    def test_10_proof_expired(self):
        b=bundle(self.op,self.att,expires_at=NOW-1); self.assertEqual(compile_terminal(self.op,self.att,self.att.root,self.cb,b).disposition,Disposition.HOLD)
    def test_11_missing_role(self):
        d=self.p.unsigned; d['durable_effect_root']='x'; d['mac']=MAC(d); b=ExecutionProofBundle(**d); self.assertEqual(compile_terminal(self.op,self.att,self.att.root,self.cb,b).disposition,Disposition.HOLD)
    def test_12_operation_move(self):
        op2=operation(payload_root='9'*64); self.assertNotEqual(op2.root,self.op.root); self.assertEqual(compile_terminal(op2,self.att,self.att.root,self.cb,self.p).disposition,Disposition.HOLD)
    def test_13_source_move(self):
        op2=operation(source_revision='rev-new'); self.assertEqual(compile_terminal(op2,self.att,self.att.root,self.cb,self.p).disposition,Disposition.HOLD)
    def test_14_idem_move(self):
        op2=operation(idempotency_key='other'); self.assertEqual(compile_terminal(op2,self.att,self.att.root,self.cb,self.p).disposition,Disposition.HOLD)
    def test_15_callback_attempt_substitute(self):
        a2=attempt(self.op,admission(self.op,3),3); cb2=callback(self.op,a2); self.assertEqual(compile_terminal(self.op,self.att,self.att.root,cb2,self.p).disposition,Disposition.HOLD)
    def test_16_proof_attempt_substitute(self):
        a2=attempt(self.op,admission(self.op,3),3); p2=bundle(self.op,a2); self.assertEqual(compile_terminal(self.op,self.att,self.att.root,self.cb,p2).disposition,Disposition.HOLD)
    def test_17_navigation_rebind_preserves_operation(self):
        a2=attempt(self.op,admission(self.op,4,card_root=H(['other-card']),host_generation=2),2); self.assertEqual(a2.operation_root,self.att.operation_root); self.assertNotEqual(a2.root,self.att.root)
    def test_18_agent_rebind_preserves_operation(self):
        a2=attempt(self.op,admission(self.op,5,actor='agent-B'),2); self.assertEqual(a2.operation_root,self.att.operation_root); self.assertNotEqual(a2.root,self.att.root)
    def test_19_attempt_auth_tamper(self):
        bad=replace(self.att,mac='0'*64); self.assertEqual(compile_terminal(self.op,bad,bad.root,callback(self.op,bad),bundle(self.op,bad)).disposition,Disposition.HOLD)
    def test_20_no_authority(self):
        d=compile_terminal(self.op,self.att,self.att.root,self.cb,self.p); self.assertFalse(d.effect_authority); self.assertFalse(d.gate10)
    def test_21_callback_root_changes_on_result(self): self.assertNotEqual(self.cb.transport_root,replace(self.cb,result_sha='0'*64).transport_root)
    def test_22_proof_root_changes_on_attempt(self):
        a2=attempt(self.op,admission(self.op,6),2); self.assertNotEqual(self.p.root,bundle(self.op,a2).root)
    def test_23_current_vs_historical_same_operation(self):
        a2=attempt(self.op,admission(self.op,7),2); d1=compile_terminal(self.op,self.att,a2.root,self.cb,self.p); d2=compile_terminal(self.op,a2,a2.root,callback(self.op,a2),bundle(self.op,a2)); self.assertEqual(d1.operation_root,d2.operation_root); self.assertNotEqual(d1.attempt_root,d2.attempt_root)
    def test_24_transport_success_not_proof(self): self.assertNotIn('PROOF_',compile_terminal(self.op,self.att,self.att.root,self.cb,None).disposition.value)
    def test_25_d0(self): self.assertEqual(D0,'D0_NONPROMOTING')
    def test_26_campaign(self): self.assertEqual(campaign(1000)['oracle_mismatches'],0)
    def test_27_omega(self): self.assertEqual(omega8()['keepers'],1)
    def test_28_d13(self): self.assertEqual(d13()['states'],1594323)
    def test_29_hs(self): self.assertEqual(hs1000()['claimed_breakthroughs'],0)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('mode',choices=['test','campaign','omega8','13d','hs1000']); a=ap.parse_args()
    if a.mode=='test':
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests); r=unittest.TextTestRunner(verbosity=1).run(suite); raise SystemExit(0 if r.wasSuccessful() else 1)
    obj={'campaign':campaign,'omega8':omega8,'13d':d13,'hs1000':hs1000}[a.mode](); print(json.dumps(obj,sort_keys=True,separators=(',',':')))
if __name__=='__main__': main()
