from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from atomic_runtime_update import *

PAY={'consumer.py':b'new-consumer','terminal_outbox.py':b'new-outbox','guardian.ps1':b'new-guardian'}
MAN=ReleaseManifest('R21','dallascourchene-commits/AuraOS','head21','a'*64,{k:sha256_bytes(v) for k,v in PAY.items()})
SRC='b'*64
class Tests(unittest.TestCase):
    def journal(self):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);return UpdateJournal(td.name+'/j.db')
    def ready(self,j,tx='T'):
        j.prepare(tx,SRC,MAN.release_root);j.record_backup(tx,SRC);j.record_staged(tx,MAN.release_root);return tx
    def test_materialize_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:self.assertEqual(materialize_release(Path(td),PAY,MAN),MAN.release_root)
    def test_hash_mismatch_rejected(self):
        bad=dict(PAY);bad['consumer.py']=b'bad'
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(UpdateError,'PAYLOAD_HASH_MISMATCH'):materialize_release(Path(td),bad,MAN)
    def test_extra_payload_rejected(self):
        bad=dict(PAY);bad['extra']=b'x'
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(UpdateError,'PAYLOAD_SET_MISMATCH'):materialize_release(Path(td),bad,MAN)
    def test_unsafe_path_rejected(self):
        with self.assertRaisesRegex(UpdateError,'UNSAFE_COMPONENT_PATH'):ReleaseManifest('x','r','h','a'*64,{'../x':'1'*64}).validate()
    def test_backup_required_before_stage(self):
        j=self.journal();j.prepare('T',SRC,MAN.release_root)
        with self.assertRaisesRegex(UpdateError,'STAGE_STATE_INVALID'):j.record_staged('T',MAN.release_root)
    def test_staged_bytes_must_match_target(self):
        j=self.journal();j.prepare('T',SRC,MAN.release_root);j.record_backup('T',SRC)
        with self.assertRaisesRegex(UpdateError,'STAGED_BYTES_DO_NOT_MATCH_TARGET'):j.record_staged('T','c'*64)
    def test_commit_is_idempotent_never_reapply(self):
        j=self.journal();tx=self.ready(j);a=j.commit(tx,MAN.release_root);b=j.commit(tx,MAN.release_root);self.assertEqual(a.receipt_root,b.receipt_root)
    def test_commit_equivocation_rejected(self):
        j=self.journal();tx=self.ready(j);j.commit(tx,MAN.release_root)
        with self.assertRaisesRegex(UpdateError,'COMMIT_EQUIVOCATION'):j.commit(tx,'d'*64)
    def test_post_install_requires_o20_and_o19(self):
        j=self.journal();tx=self.ready(j);j.commit(tx,MAN.release_root);r=j.post_install_attest(tx,o20_current_exact=True,o19_physical_wake_accepted=False);self.assertEqual(r.state,UpdateState.ROLLBACK_REQUIRED)
    def test_accept_only_after_both_witnesses(self):
        j=self.journal();tx=self.ready(j);j.commit(tx,MAN.release_root);r=j.post_install_attest(tx,o20_current_exact=True,o19_physical_wake_accepted=True);self.assertEqual(r.state,UpdateState.ACCEPTED)
    def test_rollback_restores_exact_backup(self):
        j=self.journal();tx=self.ready(j);j.commit(tx,MAN.release_root);j.post_install_attest(tx,o20_current_exact=False,o19_physical_wake_accepted=False);r=j.rollback(tx,SRC);self.assertEqual(r.state,UpdateState.ROLLED_BACK);self.assertEqual(r.installed_root,SRC)
    def test_wrong_rollback_bytes_rejected(self):
        j=self.journal();tx=self.ready(j);j.commit(tx,MAN.release_root);j.post_install_attest(tx,o20_current_exact=False,o19_physical_wake_accepted=False)
        with self.assertRaisesRegex(UpdateError,'ROLLBACK_BYTES_NOT_SOURCE_BACKUP'):j.rollback(tx,'e'*64)
    def test_crash_reopen_after_commit_never_reapplies(self):
        with tempfile.TemporaryDirectory() as td:
            p=td+'/j.db';j=UpdateJournal(p);tx=self.ready(j);a=j.commit(tx,MAN.release_root);del j;j=UpdateJournal(p);b=j.commit(tx,MAN.release_root);self.assertEqual(a.receipt_root,b.receipt_root)
    def test_tx_identity_conflict_rejected(self):
        j=self.journal();j.prepare('T',SRC,MAN.release_root)
        with self.assertRaisesRegex(UpdateError,'TX_IDENTITY_CONFLICT'):j.prepare('T','c'*64,MAN.release_root)
    def test_published_release_not_accepted_without_host_witnesses(self):
        j=self.journal();tx=self.ready(j);j.commit(tx,MAN.release_root);self.assertEqual(j._read(tx)[0],UpdateState.COMMITTED.value)
if __name__=='__main__':unittest.main()
