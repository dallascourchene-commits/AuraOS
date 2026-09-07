from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import replace

from tools.project006.o4_owner_row_convergence import (
    ProofAdmission, SemanticEffectIdentity, digest, persist_owner_bound_provider_attempt,
    proof_action_currentness_root, proof_crossbind_root, provider_candidate_ready,
    stable_provider_operation_root,
)


def r(x: str) -> str:
    return digest([x])


def semantic(**kw) -> SemanticEffectIdentity:
    d = dict(command_id="C1", idempotency_key="K1", source_file_id="F1", source_revision="R1",
             source_digest=r("source"), intent_root=r("intent"), contract_root=r("contract"),
             effect_payload_root=r("payload"), recovery_mode="IDEMPOTENT_RETRY")
    d.update(kw)
    return SemanticEffectIdentity(**d)


def admission(s: SemanticEffectIdentity, **kw) -> ProofAdmission:
    d = dict(proof_bound_admission_root="0"*64, tecc_input_root=r("tecc"),
             consumer_admission_root=r("consumer"), authorization_receipt_root=r("auth"),
             producer_proof_generation_root=r("generation"), producer_proof_semantics_id="PSEM1",
             consumer_generation=7, consumer_currentness_root=r("consumer-current"),
             verifier_instance="VERIFIER1", authority_scope_root=r("scope"), authority_epoch=3,
             authorization_expires_at=2000, recovery_mode=s.recovery_mode)
    d.update(kw)
    a = ProofAdmission(**d)
    return replace(a, proof_bound_admission_root=proof_crossbind_root(s, a))


def owner_db(s: SemanticEffectIdentity):
    td = tempfile.TemporaryDirectory()
    con = sqlite3.connect(td.name + "/effect.db")
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE effect_tx(command_id TEXT PRIMARY KEY,idempotency_key TEXT,source_file_id TEXT,
        source_revision TEXT,source_digest TEXT,intent_root TEXT,contract_root TEXT,effect_payload_root TEXT,
        recovery_mode TEXT,phase TEXT,provider_request_count INTEGER,effect_attempt_root TEXT,
        provider_action_currentness_root TEXT,provider_operation_root TEXT)""")
    con.execute("INSERT INTO effect_tx VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (s.command_id,s.idempotency_key,s.source_file_id,s.source_revision,s.source_digest,s.intent_root,
         s.contract_root,s.effect_payload_root,s.recovery_mode,"ACK_WRITTEN_PRE_EFFECT",0,None,None,None))
    con.commit()
    return td, con


class O4OwnerRowConvergenceTests(unittest.TestCase):
    def test_atomic_owner_row_binds_candidate(self):
        s=semantic(); a=admission(s); td,con=owner_db(s)
        try:
            con.execute("BEGIN IMMEDIATE")
            attempt=persist_owner_bound_provider_attempt(con,semantic=s,admission=a,now=1000,
                parent_attempt_root=r("parent"),provider_action_currentness_root=r("provider-current"),provider_request_count=1)
            con.commit(); row=con.execute("SELECT * FROM effect_tx").fetchone()
            self.assertEqual(row["effect_attempt_root"],attempt); self.assertTrue(provider_candidate_ready(row,now=1000))
            self.assertIsNone(row["provider_operation_root"])
        finally: con.close(); td.cleanup()

    def test_recovery_mode_crosscast_fails_before_update(self):
        s=semantic(); a=replace(admission(s),recovery_mode="QUERY_RECONCILE"); td,con=owner_db(s)
        try:
            con.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(ValueError,"RECOVERY_MODE_NOT_BOUND"):
                persist_owner_bound_provider_attempt(con,semantic=s,admission=a,now=1000,parent_attempt_root=r("p"),
                    provider_action_currentness_root=r("c"),provider_request_count=1)
            con.rollback(); self.assertEqual(con.execute("SELECT phase FROM effect_tx").fetchone()[0],"ACK_WRITTEN_PRE_EFFECT")
        finally: con.close(); td.cleanup()

    def test_forged_proof_crossbind_holds(self):
        s=semantic(); a=replace(admission(s),proof_bound_admission_root=r("forged")); td,con=owner_db(s)
        try:
            con.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(ValueError,"PROOF_ADMISSION_CROSSBIND_DIVERGED"):
                persist_owner_bound_provider_attempt(con,semantic=s,admission=a,now=1000,parent_attempt_root=r("p"),
                    provider_action_currentness_root=r("c"),provider_request_count=1)
            con.rollback()
        finally: con.close(); td.cleanup()

    def test_expired_authorization_holds(self):
        s=semantic(); a=admission(s,authorization_expires_at=1000); td,con=owner_db(s)
        try:
            con.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(ValueError,"PROOF_AUTHORIZATION_EXPIRED"):
                persist_owner_bound_provider_attempt(con,semantic=s,admission=a,now=1000,parent_attempt_root=r("p"),
                    provider_action_currentness_root=r("c"),provider_request_count=1)
            con.rollback()
        finally: con.close(); td.cleanup()

    def test_consumer_rebind_keeps_stable_operation_changes_attempt(self):
        s=semantic(); a1=admission(s); a2=admission(s,consumer_generation=8,consumer_currentness_root=r("cc2"),
            consumer_admission_root=r("ca2"),authorization_receipt_root=r("ar2"))
        self.assertEqual(stable_provider_operation_root(s),stable_provider_operation_root(s))
        self.assertNotEqual(proof_action_currentness_root(a1),proof_action_currentness_root(a2))
        td,con=owner_db(s)
        try:
            con.execute("BEGIN IMMEDIATE")
            x1=persist_owner_bound_provider_attempt(con,semantic=s,admission=a1,now=1000,parent_attempt_root=r("p1"),
                provider_action_currentness_root=r("c1"),provider_request_count=1); con.commit()
            con.execute("UPDATE effect_tx SET phase='COMPLETION_AMBIGUOUS'"); con.commit(); con.execute("BEGIN IMMEDIATE")
            x2=persist_owner_bound_provider_attempt(con,semantic=s,admission=a2,now=1001,parent_attempt_root=r("p2"),
                provider_action_currentness_root=r("c2"),provider_request_count=2); con.commit()
            self.assertNotEqual(x1,x2)
        finally: con.close(); td.cleanup()

    def test_semantic_movements_change_stable_operation(self):
        s=semantic()
        for m in (replace(s,source_revision="R2"),replace(s,intent_root=r("i2")),replace(s,contract_root=r("k2")),replace(s,effect_payload_root=r("p2"))):
            self.assertNotEqual(stable_provider_operation_root(s),stable_provider_operation_root(m))

    def test_provider_observed_locator_remains_separate(self):
        s=semantic(); a=admission(s); td,con=owner_db(s); locator=r("remote-op")
        try:
            con.execute("UPDATE effect_tx SET provider_operation_root=?",(locator,)); con.commit(); con.execute("BEGIN IMMEDIATE")
            persist_owner_bound_provider_attempt(con,semantic=s,admission=a,now=1000,parent_attempt_root=r("p"),
                provider_action_currentness_root=r("c"),provider_request_count=1); con.commit()
            row=con.execute("SELECT * FROM effect_tx").fetchone()
            self.assertEqual(row["provider_operation_root"],locator)
            self.assertNotEqual(row["provider_operation_root"],row["stable_provider_operation_root"])
        finally: con.close(); td.cleanup()

    def test_legacy_unproofed_attempt_not_ready(self):
        s=semantic(); td,con=owner_db(s)
        try:
            con.execute("UPDATE effect_tx SET phase='EFFECT_ATTEMPT_DURABLE',effect_attempt_root=?,provider_action_currentness_root=?",
                (r("old-attempt"),r("old-current"))); con.commit()
            self.assertFalse(provider_candidate_ready(con.execute("SELECT * FROM effect_tx").fetchone(),now=1000))
        finally: con.close(); td.cleanup()

    def test_authority_cannot_be_minted(self):
        s=semantic(); a=admission(s)
        with self.assertRaisesRegex(ValueError,"cannot mint authority"):
            replace(a,effect_authority=True)

    def test_bool_epoch_rejected(self):
        s=semantic(); a=admission(s)
        with self.assertRaisesRegex(ValueError,"invalid"):
            replace(a,authority_epoch=True)


if __name__ == "__main__":
    unittest.main()
