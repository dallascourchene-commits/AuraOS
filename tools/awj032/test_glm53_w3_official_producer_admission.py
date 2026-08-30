import unittest
from types import SimpleNamespace

from tools.awj032 import glm53_w3_official_producer_admission as g
from tools.awj032.glm53_official_w2_observation import OFFICIAL_W2_OBSERVATION as O
from tools.awj032.glm53_official_w2_plan_binding import bind_official_w2_pager_plan


class LowerPlan:
    def __init__(self, **overrides):
        self.binding = SimpleNamespace(
            model_revision=overrides.pop("model_revision", O.model_revision),
            index_digest=overrides.pop("index_digest", O.index_sha256),
        )
        self.value = {
            "source_plan_digest": "a" * 64,
            "header_receipt_digest": O.receipt_digest,
            "header_observation_repo_id": O.repo_id,
            "representative_header_bound": True,
            "representative_layer": O.layer,
            "representative_expert": O.expert,
            "all_experts_header_uniformity_proven": False,
            "g2_admitted": False,
            "runtime_execution_proven": False,
            "large_checkpoint_admitted": False,
        }
        self.value.update(overrides)

    def to_dict(self):
        return dict(self.value)


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


class W3OfficialProducerAdmissionTests(unittest.TestCase):
    def evaluate(self, *, plan=None, sec=None, meta=None):
        return g.evaluate_w3_official_producer_admission(
            pager_plan=LowerPlan() if plan is None else plan,
            airllm_security_evidence=security() if sec is None else sec,
            glm53_metadata_evidence=metadata() if meta is None else meta,
        )

    def test_current_exact_official_w2_plan_is_consumed_but_mtp_remains_blocked(self):
        out = self.evaluate()
        self.assertEqual("BLOCKED", out.status)
        self.assertEqual(("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED",), out.blockers)
        self.assertTrue(out.official_w2_producer_proof_consumed)
        self.assertEqual(O.observation_digest, out.official_w2_observation_digest)
        self.assertEqual(O.receipt_digest, out.official_w2_receipt_digest)
        self.assertFalse(out.synthetic_tiny_fixture_admitted)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.authority)

    def test_serialized_official_wrapper_cannot_bypass_consumer_binder(self):
        forged_or_replayed = bind_official_w2_pager_plan(LowerPlan()).to_dict()
        with self.assertRaises(g.W3OfficialProducerAdmissionError) as ctx:
            self.evaluate(plan=forged_or_replayed)
        self.assertEqual("OFFICIAL_W2_PRODUCER_BINDING_REQUIRED", ctx.exception.code)

    def test_lower_plan_with_old_pr404_shape_but_no_official_source_is_rejected(self):
        with self.assertRaises(g.W3OfficialProducerAdmissionError) as ctx:
            self.evaluate(plan=LowerPlan(header_observation_repo_id="synthetic/local"))
        self.assertEqual("OFFICIAL_W2_PRODUCER_BINDING_REQUIRED", ctx.exception.code)

    def test_wrong_official_receipt_is_a_hard_failure(self):
        with self.assertRaises(g.W3OfficialProducerAdmissionError) as ctx:
            self.evaluate(plan=LowerPlan(header_receipt_digest="f" * 40))
        self.assertEqual("OFFICIAL_W2_PRODUCER_BINDING_REQUIRED", ctx.exception.code)
        self.assertIn("OFFICIAL_W2_OBSERVATION_RECEIPT_MISMATCH", ctx.exception.detail)

    def test_model_index_and_coordinate_substitutions_fail(self):
        bad = (
            LowerPlan(model_revision="0" * 40),
            LowerPlan(index_digest="1" * 64),
            LowerPlan(representative_layer=4),
            LowerPlan(representative_expert=1),
        )
        for plan in bad:
            with self.subTest(plan=plan.to_dict()):
                with self.assertRaises(g.W3OfficialProducerAdmissionError):
                    self.evaluate(plan=plan)

    def test_representative_to_universal_and_effect_widening_fail_inside_binder(self):
        for field in (
            "all_experts_header_uniformity_proven",
            "g2_admitted",
            "runtime_execution_proven",
            "large_checkpoint_admitted",
        ):
            with self.subTest(field=field):
                with self.assertRaises(g.W3OfficialProducerAdmissionError):
                    self.evaluate(plan=LowerPlan(**{field: True}))

    def test_stale_airllm_and_metadata_generations_remain_blockers(self):
        out = self.evaluate(
            sec=security(semantic_head="1" * 40),
            meta=metadata(semantic_head="2" * 40),
        )
        self.assertIn("AIRLLM_SECURITY_GENERATION_STALE", out.blockers)
        self.assertIn("GLM53_METADATA_GENERATION_STALE", out.blockers)
        self.assertIn("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED", out.blockers)

    def test_missing_contract_or_source_binding_remains_blocked(self):
        out = self.evaluate(
            sec=security(hosted_contract_pass=False, hard_false_remote_code_proven=False),
            meta=metadata(hosted_contract_pass=False, source_binding_proven=False),
        )
        self.assertIn("AIRLLM_SECURITY_HOSTED_CONTRACT_REQUIRED", out.blockers)
        self.assertIn("AIRLLM_HARD_FALSE_REMOTE_CODE_REQUIRED", out.blockers)
        self.assertIn("GLM53_METADATA_HOSTED_CONTRACT_REQUIRED", out.blockers)
        self.assertIn("GLM53_SOURCE_BINDING_REQUIRED", out.blockers)

    def test_caller_cannot_flip_mtp_provenance_boolean_to_open_w3(self):
        out = self.evaluate(meta=metadata(resolver_provenance_proven=True))
        self.assertIn("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED", out.blockers)
        self.assertIn("GLM53_MTP_CALLER_PROVENANCE_WIDENING_FORBIDDEN", out.blockers)
        self.assertFalse(out.synthetic_tiny_fixture_admitted)

    def test_evidence_booleans_are_exact(self):
        with self.assertRaises(g.W3OfficialProducerAdmissionError):
            self.evaluate(sec=security(hosted_contract_pass=1))
        with self.assertRaises(g.W3OfficialProducerAdmissionError):
            self.evaluate(meta=metadata(resolver_provenance_proven="true"))


if __name__ == "__main__":
    unittest.main()
