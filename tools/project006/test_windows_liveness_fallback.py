from __future__ import annotations
import pathlib, random, unittest
from windows_liveness_contract import LivenessEvidence, PersistenceMode, classify

ROOT = pathlib.Path(__file__).resolve().parent
GUARDIAN = (ROOT/'windows_reconcile_guardian.ps1').read_text(encoding='utf-8')
INSTALLER = (ROOT/'Install-AuraProject006Wake.ps1').read_text(encoding='utf-8')

class ContractTests(unittest.TestCase):
    def test_only_complete_physical_evidence_accepts(self):
        ev=LivenessEvidence(PersistenceMode.WINDOWS_USER_SESSION_GUARDIAN,True,True,True,True,0,True,True)
        d=classify(ev)
        self.assertTrue(d.physical_acceptance)
        self.assertTrue(d.owner_session_liveness)
        self.assertFalse(d.boot_level_liveness)

    def test_immediate_canary_cannot_fake_wake_from_stopped(self):
        ev=LivenessEvidence(PersistenceMode.WINDOWS_USER_SESSION_GUARDIAN,True,None,True,True,0,True,True)
        d=classify(ev)
        self.assertFalse(d.physical_acceptance)
        self.assertIn('WAKE_FROM_STOPPED_NOT_OBSERVED', d.reasons)

    def test_provider_count_nonzero_holds(self):
        ev=LivenessEvidence(PersistenceMode.WINDOWS_SCHEDULED_RECONCILE,True,True,True,True,1,True,True)
        self.assertFalse(classify(ev).physical_acceptance)

    def test_no_persistence_owner_holds(self):
        ev=LivenessEvidence(PersistenceMode.NONE,True,True,True,True,0,True,True)
        self.assertFalse(classify(ev).physical_acceptance)

    def test_randomized_oracle(self):
        rng=random.Random(17017)
        modes=list(PersistenceMode)
        vals=[True,False,None]
        for _ in range(10000):
            ev=LivenessEvidence(rng.choice(modes),*(rng.choice(vals) for _ in range(4)),rng.choice([0,1,None]),rng.choice(vals),rng.choice(vals))
            d=classify(ev)
            expected=(ev.persistence_mode != PersistenceMode.NONE and ev.guardian_alive is True and ev.wsl_wake_observed is True and ev.consumer_progress is True and ev.outbound_return_observed is True and ev.provider_request_count == 0 and ev.currentness_exact is True and ev.authority_bounded_d0 is True)
            self.assertEqual(expected,d.physical_acceptance)

class SourceTests(unittest.TestCase):
    def test_guardian_is_windows_resident_and_bounded(self):
        for token in ['Local\\AuraOSProject006GuardianV2','wsl.exe',"$Wrapper, 'once'",'guardian_heartbeat.json','CycleTimeoutSeconds','boot_level_liveness = $false']:
            self.assertIn(token, GUARDIAN)
        self.assertNotIn('deepseek', GUARDIAN.lower())
        self.assertNotIn('api_key', GUARDIAN.lower())

    def test_installer_has_nonadmin_fallback_and_truthful_claims(self):
        for token in ['Install-UserSessionGuardian','WINDOWS_USER_SESSION_GUARDIAN','boot_level_liveness','wake_from_stopped_proven','Register-ScheduledTask']:
            self.assertIn(token, INSTALLER)
        self.assertIn('Access is denied', INSTALLER)
        self.assertIn('0x80070005', INSTALLER)
        self.assertNotIn('physical_acceptance = $canaryVerified', INSTALLER)

    def test_startup_fallback_is_per_user_not_admin(self):
        self.assertIn("[Environment]::GetFolderPath('Startup')", INSTALLER)
        self.assertIn('AuraOS-Project006-Guardian.cmd', INSTALLER)

if __name__ == '__main__': unittest.main()
