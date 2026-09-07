from __future__ import annotations
import random, unittest
from aura_interaction_contract import *

SRC=SourceIdentity('1mFHhvGUvH2HGJgPzk7s6SKLwjpcG8MUBtOO_2yntNFY','rev-20260907-1','a'*64)
LIVE=LiveCurrentness(25,'d91e0a39358901c5')
INTENT=AgentIntent('SESSION-WORKER:TEST','Return exactly Hello World',1)
DRAFT=draft_agent_command(INTENT,SRC)

def admission(**kw):
    base=dict(command_id='TEST-CMD-1',idempotency_key='TEST-CMD-1',source=SRC,objective_digest=DRAFT.objective_digest,authority_ref='Drive 1DbZyzpdBIuZUt9jvWogWIesJTHbEqVKGEnmaXO_deO8',currentness=LIVE,provider_policy='DEEPSEEK_STANDARD_ONLY',proof_root='b'*64,execution_authorized=True)
    base.update(kw); return OwnerAdmissionBinding(**base)

class InteractionTests(unittest.TestCase):
    def test_draft_is_inert(self): self.assertFalse(DRAFT.execution_authorized)
    def test_authenticated_owner_binding_compiles(self):
        e=compile_authorized_envelope(DRAFT,admission(),LIVE,lambda _:True)
        self.assertTrue(e['execution_authorized']); self.assertEqual(e['requested_effect'],'D0')
        self.assertEqual(e['source_file_id'],SRC.file_id); self.assertEqual(e['source_revision'],SRC.revision); self.assertEqual(e['source_digest'],SRC.digest)
        self.assertEqual(e['bound_revision']['digest'],LIVE.head_digest); self.assertTrue(e['no_implicit_fallback'])
    def test_shape_without_authentication_fails(self):
        with self.assertRaisesRegex(InteractionError,'ADMISSION_PROOF_NOT_AUTHENTICATED'): compile_authorized_envelope(DRAFT,admission(),LIVE,lambda _:False)
    def test_same_digest_different_file_fails(self):
        moved=SourceIdentity('1ltH85yuYb-DUBL2GbGqIsg7lfinV0iMFMhBd2AkxJY4','rev-20260907-1',SRC.digest)
        with self.assertRaisesRegex(InteractionError,'FULL_SOURCE_IDENTITY_MISMATCH'): compile_authorized_envelope(DRAFT,admission(source=moved),LIVE,lambda _:True)
    def test_same_file_digest_different_revision_fails(self):
        moved=SourceIdentity(SRC.file_id,'rev-20260907-2',SRC.digest)
        with self.assertRaisesRegex(InteractionError,'FULL_SOURCE_IDENTITY_MISMATCH'): compile_authorized_envelope(DRAFT,admission(source=moved),LIVE,lambda _:True)
    def test_currentness_move_requires_reproof(self):
        with self.assertRaisesRegex(InteractionError,'CURRENTNESS_MOVED_REPROVE'): compile_authorized_envelope(DRAFT,admission(),LiveCurrentness(26,'e'*16),lambda _:True)
    def test_provider_policy_is_not_agent_selected(self):
        with self.assertRaisesRegex(InteractionError,'PROVIDER_POLICY_NOT_OWNER_FIXED'): compile_authorized_envelope(DRAFT,admission(provider_policy='ARBITRARY_PROVIDER'),LIVE,lambda _:True)
    def test_non_d0_draft_rejected(self):
        with self.assertRaisesRegex(InteractionError,'ONLY_D0'): draft_agent_command(AgentIntent('a','x',1,'D1'),SRC)
    def test_target_bounds(self):
        for n in [0,82]:
            with self.assertRaisesRegex(InteractionError,'TARGET_SIZE_INVALID'): draft_agent_command(AgentIntent('a','x',n),SRC)
    def test_fuzz_hard_axes(self):
        rng=random.Random(18018)
        for _ in range(20000):
            src_ok=rng.choice([True,False]); rev_ok=rng.choice([True,False]); current_ok=rng.choice([True,False]); proof_ok=rng.choice([True,False]); policy_ok=rng.choice([True,False])
            s=SRC if src_ok and rev_ok else SourceIdentity(SRC.file_id if src_ok else '1ltH85yuYb-DUBL2GbGqIsg7lfinV0iMFMhBd2AkxJY4', SRC.revision if rev_ok else 'moved', SRC.digest)
            a=admission(source=s,currentness=LIVE if current_ok else LiveCurrentness(26,'e'*16),provider_policy='DEEPSEEK_STANDARD_ONLY' if policy_ok else 'X')
            should=src_ok and rev_ok and current_ok and proof_ok and policy_ok
            try: compile_authorized_envelope(DRAFT,a,LIVE,lambda _a:proof_ok); got=True
            except InteractionError: got=False
            self.assertEqual(should,got)

if __name__=='__main__': unittest.main()
