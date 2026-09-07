import dataclasses
import unittest
from types import SimpleNamespace

from consumer_admitted_currentness import *


def r(s): return digest(s)
SECRET=b"o12r2-test-secret"
NOW=1000

def intent(**changes):
    d=dict(command_id="cmd-1", source_root=r("source"), tecc_authorization_root=r("auth"), identity_root=r("intent"))
    d.update(changes); return SimpleNamespace(**d)

def contract(**changes):
    d=dict(contract_root=r("contract")); d.update(changes); return SimpleNamespace(**d)

def make(**changes):
    d=dict(
        secret=SECRET, command_id="cmd-1", intent_root=r("intent"), contract_root=r("contract"),
        source_root=r("source"), authorization_root=r("auth"), consumer_generation=7,
        currentness_root=r("currentness"), verifier_instance="tecc-consumer-v7",
        producer_lineage_root=r("producer-lineage"), observer_lineage_root=r("observer-lineage"),
        observer_receipt_root=r("observer-receipt"), proof_semantics_id=EXPECTED_REPROOF_SEMANTICS,
        source_owner_id="source-owner", authorization_owner_id="auth-owner", observer_id="observer-1",
        issued_at=900, expires_at=1100,
    ); d.update(changes); return sign_consumer_admission(**d)

def resolver(adm, **cut_changes):
    cut=dict(consumer_generation=7,currentness_root=r("currentness"),verifier_instance="tecc-consumer-v7",
             source_owner_id="source-owner",authorization_owner_id="auth-owner")
    cut.update(cut_changes)
    return CanonicalConsumerAdmissionResolver(secret=SECRET, cut=CanonicalConsumerCut(**cut),
        admission_provider=lambda _i,_c: adm, now_provider=lambda: NOW)

class T(unittest.TestCase):
    def test_valid(self):
        cur=resolver(make())(intent(),contract()); self.assertIsNotNone(cur)
        self.assertEqual(cur.consumer_admission_root,make().receipt_root)
    def test_bad_mac(self):
        a=make(); a=dataclasses.replace(a,mac=r("forged")); self.assertIsNone(resolver(a)(intent(),contract()))
    def test_generation_moved(self): self.assertIsNone(resolver(make(consumer_generation=8))(intent(),contract()))
    def test_cut_generation_moved(self): self.assertIsNone(resolver(make(),consumer_generation=8)(intent(),contract()))
    def test_currentness_moved(self): self.assertIsNone(resolver(make(currentness_root=r("new")))(intent(),contract()))
    def test_verifier_moved(self): self.assertIsNone(resolver(make(verifier_instance="other"))(intent(),contract()))
    def test_proof_semantics_moved(self): self.assertIsNone(resolver(make(proof_semantics_id="legacy"))(intent(),contract()))
    def test_source_moved(self): self.assertIsNone(resolver(make(source_root=r("other")))(intent(),contract()))
    def test_auth_moved(self): self.assertIsNone(resolver(make(authorization_root=r("other")))(intent(),contract()))
    def test_command_moved(self): self.assertIsNone(resolver(make(command_id="other"))(intent(),contract()))
    def test_intent_moved(self): self.assertIsNone(resolver(make(intent_root=r("other")))(intent(),contract()))
    def test_contract_moved(self): self.assertIsNone(resolver(make(contract_root=r("other")))(intent(),contract()))
    def test_expired(self): self.assertIsNone(resolver(make(expires_at=999))(intent(),contract()))
    def test_future(self): self.assertIsNone(resolver(make(issued_at=1001,expires_at=1100))(intent(),contract()))
    def test_owner_moved(self): self.assertIsNone(resolver(make(source_owner_id="other"))(intent(),contract()))
    def test_wrong_type(self):
        x=CanonicalConsumerAdmissionResolver(secret=SECRET,cut=resolver(make()).cut,admission_provider=lambda *_: False,now_provider=lambda:NOW)
        self.assertIsNone(x(intent(),contract()))
    def test_provider_raises(self):
        def boom(*_): raise RuntimeError
        x=CanonicalConsumerAdmissionResolver(secret=SECRET,cut=resolver(make()).cut,admission_provider=boom,now_provider=lambda:NOW)
        self.assertIsNone(x(intent(),contract()))
    def test_receipt_root_changes_generation(self): self.assertNotEqual(make().receipt_root,make(consumer_generation=8).receipt_root)
    def test_receipt_root_changes_observer_receipt(self): self.assertNotEqual(make().receipt_root,make(observer_receipt_root=r("newobs")).receipt_root)
    def test_currentness_identity_binds_receipt(self):
        a=make(); b=make(observer_receipt_root=r("newobs")); ca=resolver(a)(intent(),contract()); cb=resolver(b)(intent(),contract())
        self.assertIsNotNone(ca); self.assertIsNotNone(cb); self.assertNotEqual(ca.identity_root,cb.identity_root)
    def test_k27_is_only_projection(self):
        a=make(); self.assertEqual(len(k27_reopen_coordinate(a.receipt_root)),3); self.assertIsNotNone(resolver(a)(intent(),contract()))
    def test_authority_rejected(self):
        with self.assertRaises(ValueError): dataclasses.replace(make(),effect_authority=True)
    def test_same_observer_owner_rejected(self):
        with self.assertRaises(ValueError): make(observer_id="source-owner")
    def test_same_lineage_rejected(self):
        with self.assertRaises(ValueError): make(observer_lineage_root=r("producer-lineage"))

if __name__=='__main__': unittest.main()
