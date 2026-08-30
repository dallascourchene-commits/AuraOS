import unittest

from tools.awj032 import glm53_w3_admission_gate as g


def plan(**overrides):
    value = {
        "source_plan_digest": "a" * 64,
        "header_evidence_digest": "b" * 64,
        "header_receipt_digest": "c" * 40,
        "representative_header_bound": True,
        "representative_layer": 3,
        "representative_expert": 0,
        "all_experts_header_uniformity_proven": False,
        "g2_admitted": False,
        "runtime_execution_proven": False,
        "large_checkpoint_admitted": False,
    }
    value.update(overrides)
    return value


def security(**overrides):
    value = {
        "semantic_head": g.CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD,
        "hosted_contract_pass": True,
        "static_source_security_only": True,
        "hard_false_remote_code_proven": True,
    }
    value.update(overrides)
    return value


def metadata(**overrides):
    value = {
        "semantic_head": g.CURRENT_GLM53_METADATA_SEMANTIC_HEAD,
        "hosted_contract_pass": True,
        "resolver_provenance_proven": False,
        "source_binding_proven": True,
    }
    value.update(overrides)
    return value


class W3AdmissionGateTests(unittest.TestCase):
    def evaluate(self, *, p=None, s=None, m=None):
        return g.evaluate_w3_admission(
            pager_plan=plan() if p is None else p,
            airllm_security_evidence=security() if s is None else s,
            glm53_metadata_evidence=metadata() if m is None else m,
        )

    def test_current_real_frontier_is_blocked_only_by_resolver_provenance(self):
        out = self.evaluate()
        self.assertEqual("BLOCKED", out.status)
        self.assertEqual(("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED",), out.blockers)
        self.assertFalse(out.synthetic_tiny_fixture_admitted)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.runtime_execution_admitted)
        self.assertFalse(out.checkpoint_payload_admitted)
        self.assertFalse(out.provider_effect_admitted)

    def test_old_positive_metadata_generation_cannot_bypass_new_trust_root_blocker(self):
        old = metadata(
            semantic_head="b5e13997e2acaec02249994160460353bea9720e",
            resolver_provenance_proven=True,
        )
        out = self.evaluate(m=old)
        self.assertIn("GLM53_METADATA_GENERATION_STALE", out.blockers)
        self.assertFalse(out.synthetic_tiny_fixture_admitted)

    def test_old_airllm_scanner_generation_cannot_mint_current_security(self):
        old = security(semantic_head="6f572d96db12b9ada7d782d62f8d992241f70f35")
        out = self.evaluate(s=old)
        self.assertIn("AIRLLM_SECURITY_GENERATION_STALE", out.blockers)

    def test_missing_current_contract_passes_and_source_binding_fail_closed(self):
        out = self.evaluate(
            s=security(hosted_contract_pass=False, hard_false_remote_code_proven=False),
            m=metadata(hosted_contract_pass=False, source_binding_proven=False),
        )
        self.assertIn("AIRLLM_SECURITY_HOSTED_CONTRACT_REQUIRED", out.blockers)
        self.assertIn("AIRLLM_HARD_FALSE_REMOTE_CODE_REQUIRED", out.blockers)
        self.assertIn("GLM53_METADATA_HOSTED_CONTRACT_REQUIRED", out.blockers)
        self.assertIn("GLM53_SOURCE_BINDING_REQUIRED", out.blockers)

    def test_header_plan_is_required_but_representative_is_not_universal(self):
        out = self.evaluate(p=plan(representative_header_bound=False))
        self.assertIn("PAGER_REPRESENTATIVE_HEADER_BINDING_REQUIRED", out.blockers)
        out = self.evaluate(p=plan(all_experts_header_uniformity_proven=True))
        self.assertIn("REPRESENTATIVE_HEADER_UNIVERSALIZATION_FORBIDDEN", out.blockers)

    def test_effect_ceiling_widening_is_blocked(self):
        for field in ("g2_admitted", "runtime_execution_proven", "large_checkpoint_admitted"):
            with self.subTest(field=field):
                out = self.evaluate(p=plan(**{field: True}))
                self.assertIn("PAGER_EFFECT_CEILING_WIDENED", out.blockers)

    def test_only_hypothetical_current_independently_proven_resolver_opens_synthetic_fixture(self):
        out = self.evaluate(m=metadata(resolver_provenance_proven=True))
        self.assertEqual("ELIGIBLE_FOR_SYNTHETIC_TINY_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertTrue(out.synthetic_tiny_fixture_admitted)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.runtime_execution_admitted)
        self.assertFalse(out.checkpoint_payload_admitted)
        self.assertFalse(out.provider_effect_admitted)

    def test_evidence_booleans_are_exact_and_header_receipt_is_typed(self):
        with self.assertRaises(g.W3AdmissionError):
            self.evaluate(m=metadata(resolver_provenance_proven=1))
        with self.assertRaises(g.W3AdmissionError):
            self.evaluate(s=security(hosted_contract_pass="true"))
        with self.assertRaises(g.W3AdmissionError):
            self.evaluate(p=plan(header_receipt_digest="not-a-digest"))

    def test_logical_identity_changes_with_admission_evidence(self):
        blocked = self.evaluate()
        eligible = self.evaluate(m=metadata(resolver_provenance_proven=True))
        self.assertNotEqual(blocked.logical_id, eligible.logical_id)


if __name__ == "__main__":
    unittest.main()
