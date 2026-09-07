from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.project006.tecc_effect_admission_bridge import *


def r(x: str) -> str:
    return sha256(x.encode()).hexdigest()


@dataclass(frozen=True)
class Ident:
    command_id: str = "cmd-1"
    idempotency_key: str = "idem-1"
    source_file_id: str = "drive-file-1"
    source_revision: str = "rev-1"
    source_digest: str = r("source")


@dataclass(frozen=True)
class Intent:
    identity_root: str = r("intent")
    effect_payload_root: str = r("payload")


@dataclass(frozen=True)
class Contract:
    contract_root: str = r("contract")


class FakeJournal:
    schema = OWNER_JOURNAL_SCHEMA
    def __init__(self, path: str):
        self.path=path; self.rows={}
    def bind_admitted(self, ident, intent, contract):
        if ident.command_id not in self.rows:
            self.rows[ident.command_id]={"idempotency_key":ident.idempotency_key,"source_file_id":ident.source_file_id,"source_revision":ident.source_revision,"source_digest":ident.source_digest,"intent_root":intent.identity_root,"contract_root":contract.contract_root,"effect_payload_root":intent.effect_payload_root,"phase":"DECIDED_ADMITTED","provider_request_count":0,"effect_attempt_root":None}
    def status(self, command_id):
        if command_id not in self.rows: raise ValueError("EFFECT_COMMAND_NOT_BOUND")
        return dict(self.rows[command_id])
    def prepare_ack(self,*a,**k): return {"kind":"ACK"},r("ack")
    def decide_and_persist(self,*a,**k):
        class P: effect_authority=False; gate10=False
        return P()
    def record_result(self,*a,**k): return None
    def record_ambiguous(self,*a,**k): return None
    def stage_final_terminal(self,*a,**k): return "terminal"
    def mark_return_written(self,*a,**k): return "return"


def producer(intent=Intent()):
    x=ProducerTeccEvidence("OWNER-O14-v1","semantic-head",r("tecc"),r("handoff"),r("refine"),r("escalate"),intent.identity_root,intent.effect_payload_root,r("proofgen"),"reproof-v3","producer-A",TECC_SCHEMA,r("zero"))
    return replace(x,receipt_root=digest(x.payload()))


def consumer(p, *, observer="observer-B", gen=7):
    x=ConsumerAdmissionEvidence(CONSUMER_SCHEMA,"BIND_TECC_CONSUMER_D0",p.receipt_root,p.tecc_input_root,gen,r("current"),"tecc-1",observer,r("observer-receipt"),r("zero"))
    return replace(x,admission_root=digest(x.payload()))


def fixtures(path):
    i,n,k=Ident(),Intent(),Contract(); p=producer(n); c=consumer(p)
    g=TeccVerifierRegistry(b"reference-test-key-32-bytes!!!!",r("registry"))
    x=AdmissionAtUseContext(p.producer_schema,p.producer_semantic_head,p.receipt_root,p.proof_generation_root,p.proof_semantics_id,p.producer_lineage,p.tecc_input_root,p.effect_escalation_root,CONSUMER_SCHEMA,7,r("current"),"tecc-1",r("scope"),3,50)
    a=issue_authorization_receipt(producer=p,consumer=c,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
    j=FakeJournal(path); b=ProofBoundEffectAttemptJournal(j)
    return i,n,k,p,c,a,x,g,j,b


class T(unittest.TestCase):
    def setUp(self): self.t=tempfile.TemporaryDirectory(); self.db=str(Path(self.t.name)/"x.sqlite")
    def tearDown(self): self.t.cleanup()

    def test_valid_binding(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db)
        d=b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        self.assertIs(d.disposition,AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0)
        self.assertEqual(b._sidecar(i.command_id)["owner_journal_schema"],OWNER_JOURNAL_SCHEMA)

    def test_same_digest_revision_moves_operation_root(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); i2=replace(i,source_revision="rev-2")
        self.assertEqual(i.source_digest,i2.source_digest)
        self.assertNotEqual(operation_identity_root(i,n,k),operation_identity_root(i2,n,k))
        self.assertEqual(validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i2,intent=n,contract=k,ctx=x,registry=g).reason,"OPERATION_IDENTITY_MOVED")

    def test_same_digest_file_moves_operation_root(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); i2=replace(i,source_file_id="drive-file-2")
        self.assertEqual(i.source_digest,i2.source_digest)
        self.assertNotEqual(operation_identity_root(i,n,k),operation_identity_root(i2,n,k))

    def test_parent_schema_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); j.schema="AURA-PROJECT006-EFFECT-ATTEMPT-JOURNAL-v4"; b.owner_journal_schema=j.schema
        d=b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g)
        self.assertEqual(d.reason,"PARENT_JOURNAL_SCHEMA_MOVED")

    def test_legacy_parent_without_sidecar_cannot_progress(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); j.bind_admitted(i,n,k)
        with self.assertRaisesRegex(ValueError,"TECC_ADMISSION_REQUIRED"):
            b.decide_and_persist(i,n,k,None,producer=p,consumer=c,authorization=a,ctx=x,registry=g)

    def test_retroactive_bind_after_attempt_forbidden(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); j.bind_admitted(i,n,k); j.rows[i.command_id]["phase"]="EFFECT_ATTEMPT_DURABLE"; j.rows[i.command_id]["provider_request_count"]=1; j.rows[i.command_id]["effect_attempt_root"]=r("attempt")
        self.assertEqual(b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g).reason,"RETROACTIVE_TECC_BIND_FORBIDDEN")

    def test_forged_authorization_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); a=replace(a,signature=r("bad"))
        self.assertEqual(validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g).reason,"TECC_AUTH_FORGED")

    def test_same_lineage_observer_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); c2=consumer(p,observer=p.producer_lineage); a2=issue_authorization_receipt(producer=p,consumer=c2,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
        self.assertEqual(validate_effect_admission(producer=p,consumer=c2,authorization=a2,ident=i,intent=n,contract=k,ctx=x,registry=g).reason,"NONINDEPENDENT_CONSUMER_OBSERVER")

    def test_expired_authorization_holds(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,now=100)
        self.assertEqual(validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g).reason,"TECC_AUTHORIZATION_EXPIRED")

    def test_proof_semantics_move_reproves(self):
        i,n,k,p,c,a,x,g,j,b=fixtures(self.db); x=replace(x,proof_semantics_id="reproof-v4")
        self.assertEqual(validate_effect_admission(producer=p,consumer=c,authorization=a,ident=i,intent=n,contract=k,ctx=x,registry=g).reason,"PRODUCER_SEMANTIC_OR_PROOF_IDENTITY_MOVED")

    def test_context_axes_not_in_contract(self):
        names=set(AdmissionAtUseContext.__dataclass_fields__)
        self.assertTrue(names.isdisjoint({"k27_locality","cache_heat","route_similarity","provider_availability","presentation_priority"}))

    def test_real_pr899_v3_owner(self):
        from tools.project006.terminal_outbox import CommandIdentity
        from tools.arena.effect_return_atomicity import EffectIntent,EffectContract,RecoveryMode
        from tools.project006.effect_attempt_recovery import EffectAttemptJournal,SCHEMA
        i=CommandIdentity("cmd-real","idem-real","drive-real","rev-real",r("source-real")); n=EffectIntent(i.command_id,i.idempotency_key,i.source_digest,r("tecc-auth"),r("payload-real"),"WRITE"); k=EffectContract(RecoveryMode.NON_RETRYABLE,r("cap"),"WRITE")
        p=producer(n); c=consumer(p); g=TeccVerifierRegistry(b"reference-test-key-32-bytes!!!!",r("registry-real")); x=AdmissionAtUseContext(p.producer_schema,p.producer_semantic_head,p.receipt_root,p.proof_generation_root,p.proof_semantics_id,p.producer_lineage,p.tecc_input_root,p.effect_escalation_root,CONSUMER_SCHEMA,7,r("current"),"tecc-1",r("scope"),3,50); a=issue_authorization_receipt(producer=p,consumer=c,ident=i,intent=n,contract=k,authority_scope_root=r("scope"),authority_epoch=3,expires_at=100,verifier_instance="tecc-1",key=g.authorization_key)
        owner=EffectAttemptJournal(self.db); b=ProofBoundEffectAttemptJournal(owner); self.assertEqual(b.owner_journal_schema,SCHEMA); self.assertIs(b.bind_verified(i,n,k,producer=p,consumer=c,authorization=a,ctx=x,registry=g).disposition,AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0); row=owner.status(i.command_id); self.assertEqual((row["source_file_id"],row["source_revision"],row["source_digest"]),(i.source_file_id,i.source_revision,i.source_digest))


if __name__=="__main__": unittest.main()
