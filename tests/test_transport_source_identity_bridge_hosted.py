from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import unittest
from tools.project006.transport_source_identity_bridge import *

ROOT=Path(__file__).resolve().parents[1]
E=json.loads((ROOT/"artifacts/arena/project006_o17_transport_source_identity/PHYSICAL_R3_SOURCE_PREIMAGE_EVIDENCE.json").read_text())
def r(x): return sha256(x.encode()).hexdigest()
def fixture():
    s=DriveSourceIncarnation("file","rev","text/plain",b"source")
    a=TransportCallback("ACK","cmd","idem",r("attempt"),s.export_root,"ACK-v1","ACK_ACCEPTED",r("ab"),r("ao"))
    z=TransportCallback("RESULT","cmd","idem",r("attempt"),s.export_root,"RESULT-v1","TERMINAL_SUCCESS",r("rb"),r("ro"),r("res"),r("response"))
    c=AdmissionContext("cmd","idem",s.file_id,s.revision_id,s.incarnation_root,r("proof"),r("training"),r("workcell"),True,True,True)
    k=DigestPreimageContract("exact-v1","UTF8_EXACT")
    return s,a,z,c,k
class T(unittest.TestCase):
    def test_physical_evidence_is_fail_closed(self): self.assertEqual(E["disposition"],"HOLD_UNRESOLVED_PREIMAGE_CONTRACT"); self.assertIsNone(E["declared_preimage_contract"])
    def test_physical_declared_text_roots_do_not_match_reported_digest(self): self.assertNotEqual(E["exact_revision_export_root"],E["transport_reported_source_envelope_digest"]); self.assertNotEqual(E["normalized_no_bom_lf_root"],E["transport_reported_source_envelope_digest"])
    def test_physical_authority_remains_false(self): self.assertFalse(E["transport_digest_authority"] or E["effect_authority"] or E["training_authority"] or E["gate10"])
    def test_synthetic_exact_preimage_binds_d0(self): s,a,z,c,k=fixture(); d=validate_source_admission(source=s,ack=a,result=z,ctx=c,digest_contract=k); self.assertEqual(d.disposition,Disposition.BIND_OBSERVATION_D0); self.assertFalse(d.effect_authority)
    def test_missing_preimage_contract_holds(self): s,a,z,c,k=fixture(); self.assertEqual(validate_source_admission(source=s,ack=a,result=z,ctx=c,digest_contract=None).reason,"UNRESOLVED_PREIMAGE_CONTRACT")
    def test_digest_claim_alone_does_not_bind(self): s,a,z,c,k=fixture(); a=replace(a,source_envelope_digest=r("claim")); z=replace(z,source_envelope_digest=r("claim")); self.assertEqual(validate_source_admission(source=s,ack=a,result=z,ctx=c,digest_contract=k).reason,"TRANSPORT_DIGEST_PREIMAGE_MISMATCH")
    def test_same_bytes_new_revision_changes_source_identity(self): s,*_=fixture(); self.assertNotEqual(s.incarnation_root,replace(s,revision_id="rev2").incarnation_root)
    def test_same_bytes_new_file_changes_source_identity(self): s,*_=fixture(); self.assertNotEqual(s.incarnation_root,replace(s,file_id="file2").incarnation_root)
    def test_forged_proof_shape_holds(self): s,a,z,c,k=fixture(); self.assertEqual(validate_source_admission(source=s,ack=a,result=z,ctx=replace(c,proof_authenticated=False),digest_contract=k).reason,"PROOF_BOUND_ADMISSION_UNAUTHENTICATED")
    def test_forged_training_shape_holds(self): s,a,z,c,k=fixture(); self.assertEqual(validate_source_admission(source=s,ack=a,result=z,ctx=replace(c,training_authenticated=False),digest_contract=k).reason,"TRAINING_ADMISSION_UNAUTHENTICATED")
    def test_stale_workcell_rebinds(self): s,a,z,c,k=fixture(); self.assertEqual(validate_source_admission(source=s,ack=a,result=z,ctx=replace(c,workcell_current=False),digest_contract=k).reason,"WORKCELL_EXECUTION_NOT_CURRENT")
    def test_k27_context_cannot_compensate(self): self.assertTrue(set(AdmissionContext.__dataclass_fields__).isdisjoint({"k27_locality","cache_heat","route_similarity","provider_availability","presentation_priority"}))
if __name__=="__main__": unittest.main()
