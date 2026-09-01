from __future__ import annotations

from dataclasses import replace
import unittest

import tools.aura_generation_bound_admission_reuse as r769
import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as m

D0, D1, D2, D3, D4, D5 = (c * 64 for c in "012345")


def parent_receipt():
    family = r769.AdmissionFamily.GLM53_BOUNDED_C2_PROPOSAL
    admission = r769.AdmissionReceiptProjectionV1(
        family=family,
        producer_head=r769.EXPECTED_HEAD[family],
        receipt_digest=m.Q18_RECEIPT_DIGEST,
        admission_disposition=r769.EXPECTED_POSITIVE_DISPOSITION[family],
        subject_identity="subject:q18",
        source_generation_key="source-generation:q18:1",
        evidence_generation_key="evidence-generation:q18:1",
        owner_context_key="owner-context:q18:1",
        decision_context_key="decision-context:q18:1",
        bounded_admission_positive=True,
    )
    current = r769.CurrentAdmissionUseContextV1(
        producer_head=admission.producer_head,
        subject_identity=admission.subject_identity,
        source_generation_key=admission.source_generation_key,
        evidence_generation_key=admission.evidence_generation_key,
        owner_context_key=admission.owner_context_key,
        decision_context_key=admission.decision_context_key,
    )
    return r769.revalidate_admission_reuse(admission=admission, current=current)


def reuse(**changes):
    p = parent_receipt()
    candidate = m.AdmissionReuseProjection(
        m.REUSE_HEAD, m.REUSE_RUN, m.REUSE_JOB, m.REUSE_SOURCE_BLOB, m.REUSE_TEST_BLOB,
        p.family.value, p.disposition.value, p.admission_receipt_digest, D5,
        p.subject_identity or "", p.source_generation_key or "", p.evidence_generation_key or "",
        p.owner_context_key or "", p.decision_context_key or "", True,
    )
    candidate = replace(candidate, **changes)
    return replace(candidate, reuse_digest=m.expected_pr769_reuse_digest(candidate))


def provenance():
    return m.ObservationProvenanceContractProjection(
        m.PROV_HEAD, m.PROV_RUN, m.PROV_JOB, m.PROV_SOURCE_BLOB, True, True, True
    )


def source():
    return m.SourceIdentityProjection(
        m.OFFICIAL_REPOSITORY, m.PINNED_OFFICIAL_REVISION, m.SOURCE_SET_DIGEST, True
    )


def owner():
    return m.OwnerHostTargetProjection(
        "owner-host:local:glm53-c2", "principal:g1", "host:g1", "runtime:g1",
        "cache:g1", "storage:g1", D0, "artifact:awj032:g6:owner-host-evidence"
    )


def evidence():
    return m.EvidenceContractProjection(
        D1, D2, D3, D4, m.REQUIRED_EVIDENCE_AXES, m.OPEN_GATE10_DEBT, True
    )


def compile_(**changes):
    args = dict(reuse=reuse(), provenance=provenance(), source=source(), owner=owner(), evidence=evidence())
    args.update(changes)
    return m.compile_gate10_owner_host_evidence_request(**args)


class G6Tests(unittest.TestCase):
    def test_parent769_q18_digest_relation(self):
        p = parent_receipt()
        r = reuse()
        self.assertEqual(p.admission_receipt_digest, m.Q18_RECEIPT_DIGEST)
        self.assertEqual(p.reuse_digest, r.reuse_digest)
        self.assertEqual(r.reuse_digest, m.expected_pr769_reuse_digest(r))

    def test_exact_inputs_compile_single_owner_request(self):
        r = compile_()
        self.assertEqual(r.disposition, m.COMPILED)
        self.assertEqual(r.reuse_identity_reason_code, m.REUSE_IDENTITY_OK)
        self.assertTrue(r.exact_q18_admission_receipt_bound)
        self.assertTrue(r.pr769_reuse_digest_structurally_verified)
        self.assertTrue(r.single_owner_request_constructed_by_this_contract)
        self.assertFalse(r.caller_supplied_precompiled_request_accepted)
        self.assertFalse(r.reuse_receipt_authenticated_by_this_contract)
        self.assertFalse(r.gate10_promoted)

    def test_public_api_has_no_precompiled_request_join(self):
        self.assertEqual(m.public_api_parameters(), ("reuse", "provenance", "source", "owner", "evidence"))
        self.assertFalse(hasattr(m, "bind_g6_request_to_admission_identity"))

    def test_family_disposition_and_currentness_cross_casts_hold(self):
        cases = (
            (reuse(admission_family="OTHER"), m.REUSE_HOLD_FAMILY),
            (reuse(disposition="HOLD_SUBJECT_CHANGED"), m.REUSE_HOLD_DISPOSITION),
            (reuse(current_context_exact=False), m.REUSE_HOLD_CURRENT),
        )
        for candidate, code in cases:
            with self.subTest(code=code):
                r = compile_(reuse=candidate)
                self.assertEqual(r.disposition, m.HOLD_REUSE)
                self.assertEqual(r.reuse_identity_reason_code, code)
                self.assertEqual(r.admission_receipt_digest, "")

    def test_same_family_different_q18_receipt_holds(self):
        r = compile_(reuse=reuse(admission_receipt_digest="a" * 64))
        self.assertEqual(r.disposition, m.HOLD_REUSE)
        self.assertEqual(r.reuse_identity_reason_code, m.REUSE_HOLD_Q18_RECEIPT)

    def test_stale_or_forged_reuse_digest_holds(self):
        forged = replace(reuse(), reuse_digest="b" * 64)
        stale = replace(reuse(), subject_identity="subject:q18:drift")
        for candidate in (forged, stale):
            r = compile_(reuse=candidate)
            self.assertEqual(r.disposition, m.HOLD_REUSE)
            self.assertEqual(r.reuse_identity_reason_code, m.REUSE_HOLD_DIGEST_RELATION)

    def test_coherent_current_identity_changes_request_digest(self):
        base = compile_()
        changed = compile_(reuse=reuse(subject_identity="subject:q18:other"))
        self.assertEqual(changed.disposition, m.COMPILED)
        self.assertNotEqual(changed.reuse_digest, base.reuse_digest)
        self.assertNotEqual(changed.request_digest, base.request_digest)
        self.assertFalse(changed.reuse_receipt_authenticated_by_this_contract)

    def test_parent_proof_coordinate_substitution_rejected(self):
        with self.assertRaises(ValueError):
            compile_(reuse=replace(reuse(), proof_job=m.REUSE_JOB + 1))
        with self.assertRaises(ValueError):
            compile_(provenance=replace(provenance(), proof_run=m.PROV_RUN + 1))

    def test_source_mismatch_holds_without_echoing_identity(self):
        r = compile_(source=replace(source(), repository="example/not-glm"))
        self.assertEqual(r.disposition, m.HOLD_SOURCE)
        self.assertEqual(r.official_repository, "")
        self.assertFalse(r.exact_source_request_identity_bound)

    def test_missing_provenance_holds(self):
        r = compile_(provenance=replace(provenance(), producer_authentication_required=False))
        self.assertEqual(r.disposition, m.HOLD_PROVENANCE)

    def test_request_digest_is_deterministic_and_runtime_sensitive(self):
        self.assertEqual(compile_(), compile_())
        changed = compile_(owner=replace(owner(), runtime_generation="runtime:g2"))
        self.assertNotEqual(changed.request_digest, compile_().request_digest)

    def test_different_j_surfaces(self):
        self.assertEqual(m.prove_different_j(), 512)
        self.assertEqual(m.prove_reuse_identity_different_j(), 32)

    def test_core_laws(self):
        for law in (
            "ExactQ18AdmissionReceiptMustRemainBound",
            "PR769ReuseDigestMustCommitExactIdentityVector",
            "DigestShape!=DigestRelationProof",
            "SingleOwnerCompilerEliminatesPostHocIdentityJoin",
            "IdentityBinding!=ReceiptProducerAuthentication",
            "CanonicalC2ReturnPath!=ProducerAuthentication",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ):
            self.assertIn(law, m.LAWS)


if __name__ == "__main__":
    unittest.main()
