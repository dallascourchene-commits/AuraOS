from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.project006.tecc_effect_admission_bridge import *


def r(x: str) -> str: return sha256(x.encode()).hexdigest()

@dataclass(frozen=True)
class Ident:
    command_id: str = "cmd-1"
    idempotency_key: str = "idem-1"
    source_digest: str = r("source")

@dataclass(frozen=True)
class Intent:
    identity_root: str = r("intent")
    effect_payload_root: str = r("payload")

@dataclass(frozen=True)
class Contract:
    contract_root: str = r("contract")

@dataclass(frozen=True)
class ParentPermit:
    action: str = "CALL_PROVIDER_FIRST_TIME"
    effect_authority: bool = False
    gate10: bool = False

class FakeJournal:
    def __init__(self, path: str):
        self.path = path; self.rows = {}; self.results = {}
    def bind_admitted(self, ident, intent, contract):
        old=self.rows.get(ident.command_id)
        if old is None:
            self.rows[ident.command_id] = {"idempotency_key":ident.idempotency_key,"source_digest":ident.source_digest,"intent_root":intent.identity_root,"contract_root":contract.contract_root,"effect_payload_root":intent.effect_payload_root,"phase":"DECIDED_ADMITTED","provider_request_count":0,"effect_attempt_root":None}
    def status(self, command_id):
        if command_id not in self.rows: raise ValueError("EFFECT_COMMAND_NOT_BOUND")
        return dict(self.rows[command_id])
    def prepare_ack(self, ident, intent, contract):
        if ident.command_id not in self.rows: raise ValueError("EFFECT_COMMAND_NOT_BOUND")
        return {"kind":"ACK"}, r("ack")
    def decide_and_persist(self, ident, intent, contract, recovery_context):
        if ident.command_id not in self.rows: raise ValueError("EFFECT_COMMAND_NOT_BOUND")
        self.rows[ident.command_id]["phase"]="EFFECT_ATTEMPT_DURABLE"; self.rows[ident.command_id]["provider_request_count"]+=1; self.rows[ident.command_id]["effect_attempt_root"]=r("attempt")
        return ParentPermit()
    def record_result(self, command_id, result_root): self.results[command_id]=result_root
    def record_ambiguous(self, *a, **k): return None
    def stage_final_terminal(self, *a, **k): return "terminal"
    def mark_return_written(self, *a, **k): return "return"


def producer(intent=Intent(), *, schema="OWNER-O14-v1", lineage="producer-A"):
    x = ProducerTeccEvidence(schema,"semantic-head",r("tecc"),r("handoff"),r("refine"),r("escalate"),
        intent.identity_root,intent.effect_payload_root,r("proofgen"),"reproof-v3",lineage,TECC_SCHEMA,r("zero"))
    return replace(x, receipt_root=digest(x.payload()))

def consumer(p, *, gen=7, current=r("current"), verifier="tecc-1", observer="observer-B", disposition="BIND_TECC_CONSUMER_D0"):
    x=ConsumerAdmissionEvidence(CONSUMER_SCHEMA,disposition,p.receipt_root,p.tecc_input_root,gen,current,verifier,observer,r("observer-receipt"),r("zero"))
    return replace(x, admission_root=digest(x.payload()))

def fixtures(tmp):
    ident=Ident(); intent=Intent(); contract=Contract(); p=producer(intent); c=consumer(p)
    reg=TeccVerifierRegistry(b"reference-test-key-32-bytes!!!!",r("registry"))
    ctx=AdmissionAtUseContext(p.producer_schema,p.producer_semantic_head,p.receipt_root,p.proof_generation_root,p.proof_semantics_id,p.producer_lineage,p.tecc_input_root,p.effect_escalation_root,CONSUMER_SCHEMA,7,r("current"),"tecc-1",r("scope"),3,50)
    a=issue_authorization_receipt(producer=p,consumer=c,ident=ident,intent=intent,contract=contract,
        authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=reg.authorization_key)
    j=FakeJournal(tmp); b=ProofBoundEffectAttemptJournal(j)
    return ident,intent,contract,p,c,a,ctx,reg,j,b

class T(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.db=str(Path(self.t.name)/"x.sqlite")
    def tearDown(self): self.t.cleanup()
    def test_valid_binding_and_provider_candidate(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db)
        d=b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        self.assertIs(d.disposition,AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0)
        q=b.decide_and_persist(i,n,k,None,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        self.assertEqual(q.tecc_input_root,p.tecc_input_root); self.assertFalse(q.effect_authority)
    def test_legacy_parent_bind_cannot_pass_bridge(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); j.bind_admitted(i,n,k)
        with self.assertRaisesRegex(ValueError,"TECC_ADMISSION_REQUIRED"):
            b.decide_and_persist(i,n,k,None,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
    def test_producer_receipt_forgery_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); p=replace(p,receipt_root=r("forged"))
        d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g)
        self.assertEqual(d.reason,"PRODUCER_RECEIPT_FORGED")
    def test_schema_shape_not_owner_schema_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); p2=producer(n,schema="LOOKALIKE")
        c2=consumer(p2); a2=issue_authorization_receipt(producer=p2,consumer=c2,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
        d=validate_effect_admission(producer=p2,consumer=c2,authorization=a2,ident=i,intent=n,contract=k,ctx=x,registry=g)
        self.assertEqual(d.reason,"PRODUCER_SCHEMA_MOVED")
    def test_nonindependent_consumer_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); c2=consumer(p,observer=p.producer_lineage); a2=issue_authorization_receipt(producer=p,consumer=c2,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
        d=validate_effect_admission(producer=p,consumer=c2,authorization=a2,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"NONINDEPENDENT_CONSUMER_OBSERVER")
    def test_consumer_generation_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); c2=consumer(p,gen=8); a2=issue_authorization_receipt(producer=p,consumer=c2,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
        d=validate_effect_admission(producer=p,consumer=c2,authorization=a2,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"CONSUMER_GENERATION_MOVED")
    def test_currentness_move_rebinds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,currentness_root=r("moved")); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"CONSUMER_CURRENTNESS_MOVED")
    def test_verifier_signature_forgery_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); a=replace(a,signature=r("bad")); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"TECC_AUTH_FORGED")
    def test_unauthorized_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); a=issue_authorization_receipt(producer=p,consumer=c,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key,authorized=False); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"TECC_NOT_AUTHORIZED")
    def test_expired_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,now=100); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"TECC_AUTHORIZATION_EXPIRED")
    def test_authority_epoch_move_rebinds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,authority_epoch=4); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"TECC_AUTHORITY_CURRENTNESS_MOVED")
    def test_intent_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); n2=replace(n,identity_root=r("intent2")); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n2,contract=k,ctx=x,registry=g); self.assertIn(d.reason,("OPERATION_IDENTITY_MOVED","INTENT_ROOT_MOVED","PRODUCER_INTENT_ROOT_MOVED"))
    def test_contract_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); k2=replace(k,contract_root=r("contract2")); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k2,ctx=x,registry=g); self.assertIn(d.reason,("OPERATION_IDENTITY_MOVED","EFFECT_CONTRACT_ROOT_MOVED"))
    def test_idempotency_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); i2=replace(i,idempotency_key="idem-2"); d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i2,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"OPERATION_IDENTITY_MOVED")
    def test_sidecar_equivocation_rejected(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        x2=replace(x,authority_epoch=4); a2=issue_authorization_receipt(producer=p,consumer=c,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=4,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
        with self.assertRaisesRegex(ValueError,"TECC_ADMISSION_EQUIVOCATION"):
            b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a2,ctx=x2,registry=g)
    def test_auth_movement_before_provider_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        x2=replace(x,authority_epoch=4); a2=issue_authorization_receipt(producer=p,consumer=c,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=4,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
        with self.assertRaisesRegex(ValueError,"DURABLE_TECC_ADMISSION_MOVED"):
            b.decide_and_persist(i,n,k,None,producer=p,consumer=c,authorization=a2,ctx=x2,registry=g)
    def test_result_remains_publishable_after_auth_expiry(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        j.record_result(i.command_id,r("result")); self.assertEqual(b.stage_final_terminal(None,i),"terminal")
    def test_retroactive_bind_after_unproofed_provider_attempt_forbidden(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); j.bind_admitted(i,n,k); j.rows[i.command_id]["phase"]="EFFECT_ATTEMPT_DURABLE"; j.rows[i.command_id]["provider_request_count"]=1; j.rows[i.command_id]["effect_attempt_root"]=r("legacy-attempt")
        d=b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        self.assertEqual(d.reason,"RETROACTIVE_TECC_BIND_FORBIDDEN")
    def test_parent_lineage_move_after_bind_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g); j.rows[i.command_id]["contract_root"]=r("moved-parent-contract")
        with self.assertRaisesRegex(ValueError,"PARENT_EFFECT_LINEAGE_MOVED"):
            b.decide_and_persist(i,n,k,None,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
    def test_context_fields_do_not_exist_in_admission_contract(self):
        names=set(AdmissionAtUseContext.__dataclass_fields__)
        self.assertTrue(names.isdisjoint({"k27_locality","cache_heat","provider_availability","presentation_priority","route_similarity"}))
    def test_producer_semantic_head_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,producer_semantic_head="new-head")
        d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"PRODUCER_SEMANTIC_OR_PROOF_IDENTITY_MOVED")
    def test_producer_proof_generation_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,proof_generation_root=r("new-proofgen"))
        d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"PRODUCER_SEMANTIC_OR_PROOF_IDENTITY_MOVED")
    def test_producer_proof_semantics_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,proof_semantics_id="reproof-v4")
        d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"PRODUCER_SEMANTIC_OR_PROOF_IDENTITY_MOVED")
    def test_tecc_input_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,tecc_input_root=r("new-tecc"))
        d=validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g); self.assertEqual(d.reason,"PRODUCER_SEMANTIC_OR_PROOF_IDENTITY_MOVED")
    def test_decision_cannot_mint_authority(self):
        with self.assertRaises(ValueError): AdmissionDecision(AdmissionDisposition.HOLD,"x",authority_minted=True)

if __name__ == "__main__": unittest.main()
