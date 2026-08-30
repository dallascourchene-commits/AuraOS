import importlib.util
from dataclasses import dataclass
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).with_name("glm53_source_bound_layout_bridge.py")
SPEC = importlib.util.spec_from_file_location("glm53_source_bound_layout_bridge", PATH)
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
assert SPEC.loader is not None
SPEC.loader.exec_module(m)


@dataclass
class FakePlan:
    weight_map_digest: str
    source_plan_digest: str = "b" * 64
    binding: object = None

    def to_dict(self):
        return {
            "weight_map_digest": self.weight_map_digest,
            "source_plan_digest": self.source_plan_digest,
        }


class SourceBoundLayoutBridgeTests(unittest.TestCase):
    def wm(self):
        return {"a": "s1", "b": "s2"}

    def report(self):
        return {
            "source_binding_proven": True,
            "source_bundle_id": "a" * 64,
            "weight_map_digest": m.weight_map_digest(self.wm()),
        }

    def compile(self, report, **kwargs):
        return FakePlan(m.weight_map_digest(kwargs["weight_map"]))

    def test_success_binds_source_bundle_and_map(self):
        plan = m.compile_source_bound_pager_source_plan(
            self.report(),
            weight_map=self.wm(),
            headers=None,
            expected_model_revision="r",
            expected_index_digest="i",
            compile_fn=self.compile,
        )
        self.assertEqual("a" * 64, plan.source_bundle_id)
        self.assertEqual(m.weight_map_digest(self.wm()), plan.weight_map_digest)
        self.assertFalse(plan.g2_admitted)
        self.assertEqual(64, len(plan.source_bound_plan_digest))

    def test_unproven_report_rejected(self):
        report = self.report()
        report["source_binding_proven"] = False
        with self.assertRaises(m.SourceBoundLayoutError) as ctx:
            m.compile_source_bound_pager_source_plan(
                report,
                weight_map=self.wm(),
                headers=None,
                expected_model_revision="r",
                expected_index_digest="i",
                compile_fn=self.compile,
            )
        self.assertEqual("SOURCE_BINDING_REQUIRED", ctx.exception.code)

    def test_substituted_weight_map_rejected_before_compile(self):
        called = []

        def compile_fn(*args, **kwargs):
            called.append(1)

        with self.assertRaises(m.SourceBoundLayoutError) as ctx:
            m.compile_source_bound_pager_source_plan(
                self.report(),
                weight_map={"a": "DIFFERENT"},
                headers=None,
                expected_model_revision="r",
                expected_index_digest="i",
                compile_fn=compile_fn,
            )
        self.assertEqual("SOURCE_WEIGHT_MAP_DIGEST_MISMATCH", ctx.exception.code)
        self.assertEqual([], called)

    def test_missing_source_bundle_rejected(self):
        report = self.report()
        report.pop("source_bundle_id")
        with self.assertRaises(m.SourceBoundLayoutError):
            m.compile_source_bound_pager_source_plan(
                report,
                weight_map=self.wm(),
                headers=None,
                expected_model_revision="r",
                expected_index_digest="i",
                compile_fn=self.compile,
            )

    def test_inner_digest_mismatch_rejected(self):
        def bad(report, **kwargs):
            return FakePlan("c" * 64)

        with self.assertRaises(m.SourceBoundLayoutError) as ctx:
            m.compile_source_bound_pager_source_plan(
                self.report(),
                weight_map=self.wm(),
                headers=None,
                expected_model_revision="r",
                expected_index_digest="i",
                compile_fn=bad,
            )
        self.assertEqual("INNER_WEIGHT_MAP_DIGEST_MISMATCH", ctx.exception.code)

    def test_source_bundle_changes_final_identity(self):
        first = self.report()
        second = self.report()
        second["source_bundle_id"] = "c" * 64
        p1 = m.compile_source_bound_pager_source_plan(
            first,
            weight_map=self.wm(),
            headers=None,
            expected_model_revision="r",
            expected_index_digest="i",
            compile_fn=self.compile,
        )
        p2 = m.compile_source_bound_pager_source_plan(
            second,
            weight_map=self.wm(),
            headers=None,
            expected_model_revision="r",
            expected_index_digest="i",
            compile_fn=self.compile,
        )
        self.assertNotEqual(p1.source_bound_plan_digest, p2.source_bound_plan_digest)


if __name__ == "__main__":
    unittest.main()
