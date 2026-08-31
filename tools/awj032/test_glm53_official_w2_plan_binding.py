import types
import unittest

from tools.awj032 import glm53_official_w2_observation as o
from tools.awj032 import glm53_official_w2_plan_binding as p


def plan(**overrides):
    body = {
        "source_plan_digest": "a" * 64,
        "header_receipt_digest": o.OFFICIAL_RECEIPT_DIGEST,
        "header_observation_repo_id": o.OFFICIAL_REPO_ID,
        "representative_header_bound": True,
        "representative_layer": o.OFFICIAL_LAYER,
        "representative_expert": o.OFFICIAL_EXPERT,
        "all_experts_header_uniformity_proven": False,
        "g2_admitted": False,
        "runtime_execution_proven": False,
        "large_checkpoint_admitted": False,
        # Legacy/caller-plane flag is deliberately ignored by the producer binder.
        "official_w2_observation_bound": True,
    }
    body.update(overrides)
    binding = types.SimpleNamespace(
        model_revision=body.pop("binding_model_revision", o.OFFICIAL_MODEL_REVISION),
        index_digest=body.pop("binding_index_digest", o.OFFICIAL_INDEX_SHA256),
    )

    class FakePlan:
        def __init__(self, payload, source_binding):
            self._payload = payload
            self.binding = source_binding

        def to_dict(self):
            return dict(self._payload)

    return FakePlan(body, binding)


class OfficialW2PlanBindingTests(unittest.TestCase):
    def code(self, expected, value):
        with self.assertRaises(p.OfficialW2PlanBindingError) as ctx:
            p.bind_official_w2_pager_plan(value)
        self.assertEqual(expected, ctx.exception.code)

    def test_exact_pr398_observation_binds_producer_identity(self):
        out = p.bind_official_w2_pager_plan(plan())
        self.assertTrue(out.official_w2_producer_observation_proven)
        self.assertEqual(o.OFFICIAL_W2_OBSERVATION.observation_digest, out.official_w2_observation_digest)
        self.assertEqual(o.OFFICIAL_PRODUCER_SEMANTIC_HEAD, out.official_w2_producer_semantic_head)
        self.assertEqual(o.OFFICIAL_PRODUCER_RUN_REF, out.official_w2_producer_run_ref)
        self.assertEqual(o.OFFICIAL_DRIVE_OBSERVATION_REF, out.official_w2_drive_observation_ref)
        self.assertFalse(out.all_experts_header_uniformity_proven)
        self.assertFalse(out.g2_admitted)

    def test_caller_claimed_official_flag_cannot_override_forged_receipt(self):
        self.code(
            "OFFICIAL_W2_OBSERVATION_RECEIPT_MISMATCH",
            plan(header_receipt_digest="0" * 40, official_w2_observation_bound=True),
        )

    def test_repo_or_coordinate_substitution_cannot_bind(self):
        self.code(
            "OFFICIAL_W2_SOURCE_COORDINATE_MISMATCH",
            plan(header_observation_repo_id="attacker/GLM-5.3"),
        )
        self.code(
            "OFFICIAL_W2_SOURCE_COORDINATE_MISMATCH",
            plan(representative_expert=1),
        )

    def test_model_or_index_generation_substitution_cannot_bind(self):
        self.code(
            "OFFICIAL_W2_SOURCE_COORDINATE_MISMATCH",
            plan(binding_model_revision="f" * 40),
        )
        self.code(
            "OFFICIAL_W2_SOURCE_COORDINATE_MISMATCH",
            plan(binding_index_digest="e" * 64),
        )

    def test_missing_representative_header_binding_fails(self):
        self.code("REPRESENTATIVE_HEADER_BINDING_REQUIRED", plan(representative_header_bound=False))

    def test_representative_to_universal_cast_fails(self):
        self.code(
            "REPRESENTATIVE_TO_UNIVERSAL_CAST_FORBIDDEN",
            plan(all_experts_header_uniformity_proven=True),
        )

    def test_effect_ceiling_widening_fails(self):
        self.code("PAGER_G2_WIDENING_FORBIDDEN", plan(g2_admitted=True))
        self.code("PAGER_RUNTIME_WIDENING_FORBIDDEN", plan(runtime_execution_proven=True))
        self.code("PAGER_CHECKPOINT_WIDENING_FORBIDDEN", plan(large_checkpoint_admitted=True))

    def test_producer_bound_plan_identity_includes_inner_plan_identity(self):
        a = p.bind_official_w2_pager_plan(plan(source_plan_digest="a" * 64))
        b = p.bind_official_w2_pager_plan(plan(source_plan_digest="b" * 64))
        self.assertNotEqual(a.source_plan_digest, b.source_plan_digest)
        self.assertEqual(a.official_w2_observation_digest, b.official_w2_observation_digest)


if __name__ == "__main__":
    unittest.main()
