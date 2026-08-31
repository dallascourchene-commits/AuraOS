import unittest

from tools.aura_review.aura_review_context_compiler import (
    ContextCompileRefusal,
    CoordinateLocatorV1,
    GraphEdgeV1,
    compile_affected_cone,
    project_review_capsule_inputs,
)

CGEN = "codemap-gen-1"
WGEN = "workgraph-gen-1"


def ce(a, b, r="CALLS", gen=CGEN, ref="codemap:1"):
    return GraphEdgeV1(a, b, r, gen, ref)


def we(a, b, r="DEPENDS_ON", gen=WGEN, ref="workgraph:1"):
    return GraphEdgeV1(a, b, r, gen, ref)


def compile(**kw):
    args = dict(
        repository="dallascourchene-commits/AuraOS",
        base_sha="a" * 40,
        head_sha="b" * 40,
        diff_digest="d" * 64,
        currentness_ref="cur-1",
        source_generation_ref="src-1",
        codemap_generation_ref=CGEN,
        workgraph_generation_ref=WGEN,
        route_policy_ref="route-v1",
        changed_paths=("tools/a.py",),
        code_graph_edges=(),
        workgraph_edges=(),
        max_nodes=64,
        optional_depth=0,
    )
    args.update(kw)
    return compile_affected_cone(**args)


class T(unittest.TestCase):
    def test_changed_path_is_required(self):
        c = compile()
        self.assertEqual(c["changed_paths"], ["tools/a.py"])
        self.assertTrue(c["nodes"][0]["required"])

    def test_direct_outbound_dependency_is_required(self):
        c = compile(code_graph_edges=(ce("tools/a.py", "tools/b.py", "CALLS"),))
        self.assertEqual({n["path"] for n in c["nodes"]}, {"tools/a.py", "tools/b.py"})

    def test_direct_inbound_dependent_is_required(self):
        c = compile(code_graph_edges=(ce("tools/c.py", "tools/a.py", "CALLS"),))
        self.assertIn("tools/c.py", {n["path"] for n in c["nodes"]})

    def test_workgraph_dependency_is_required(self):
        c = compile(workgraph_edges=(we("tools/a.py", "tools/d.py"),))
        self.assertIn("tools/d.py", {n["path"] for n in c["nodes"]})

    def test_must_not_affect_is_required(self):
        c = compile(workgraph_edges=(we("tools/a.py", "security/invariant.py", "MUST_NOT_AFFECT"),))
        n = next(n for n in c["nodes"] if n["path"] == "security/invariant.py")
        self.assertTrue(n["required"])
        self.assertIn("MUST_NOT_AFFECT", n["reasons"])

    def test_negative_space_is_required(self):
        c = compile(workgraph_edges=(we("tools/a.py", "legacy/compat.py", "NEGATIVE_SPACE"),))
        self.assertIn("legacy/compat.py", {n["path"] for n in c["nodes"]})

    def test_disconnected_node_is_excluded(self):
        c = compile(code_graph_edges=(ce("x.py", "y.py"),))
        self.assertEqual({n["path"] for n in c["nodes"]}, {"tools/a.py"})

    def test_budget_never_drops_required_nodes(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "CONTEXT_BUDGET_INSUFFICIENT"):
            compile(code_graph_edges=(ce("tools/a.py", "b.py"), ce("tools/a.py", "c.py")), max_nodes=2)

    def test_optional_nodes_are_truncated_after_required(self):
        c = compile(
            code_graph_edges=(
                ce("tools/a.py", "b.py"),
                ce("b.py", "c.py"),
                ce("b.py", "d.py"),
            ),
            optional_depth=1,
            max_nodes=3,
        )
        paths = [n["path"] for n in c["nodes"]]
        self.assertIn("tools/a.py", paths)
        self.assertIn("b.py", paths)
        self.assertTrue(c["context_budget_exhausted"])
        self.assertEqual(len(paths), 3)

    def test_coordinate_is_locator_only(self):
        c = compile(coordinate_locators=(CoordinateLocatorV1("tools/a.py", "WS1/L2/abc", "coord-gen"),))
        self.assertFalse(c["coordinate_is_authority"])
        self.assertEqual(c["nodes"][0]["coordinates"], ("WS1/L2/abc",))

    def test_coordinate_authority_widening_refused(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "COORDINATE_AUTHORITY_WIDENING"):
            CoordinateLocatorV1("tools/a.py", "x", "g", authority=True)

    def test_codemap_edge_generation_mismatch_refused(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "CODEMAP_EDGE_GENERATION_MISMATCH"):
            compile(code_graph_edges=(ce("tools/a.py", "b.py", gen="old"),))

    def test_workgraph_edge_generation_mismatch_refused(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "WORKGRAPH_EDGE_GENERATION_MISMATCH"):
            compile(workgraph_edges=(we("tools/a.py", "b.py", gen="old"),))

    def test_expected_current_graph_generation_refused(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "CODEMAP_GENERATION_STALE"):
            compile(expected_codemap_generation_ref="new")

    def test_unknown_edge_relation_refused(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "UNKNOWN_EDGE_RELATION"):
            ce("a.py", "b.py", "HANDWAVE")

    def test_path_escape_refused(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "PATH_OUTSIDE_REPOSITORY"):
            compile(changed_paths=("../secret",))

    def test_input_order_does_not_change_digest(self):
        e1 = ce("tools/a.py", "b.py", "CALLS", ref="c:1")
        e2 = ce("c.py", "tools/a.py", "READS", ref="c:2")
        a = compile(code_graph_edges=(e1, e2))
        b = compile(code_graph_edges=(e2, e1))
        self.assertEqual(a["context_digest"], b["context_digest"])

    def test_projection_matches_ghr001_interface(self):
        c = compile(code_graph_edges=(ce("tools/a.py", "b.py"),))
        p = project_review_capsule_inputs(c)
        self.assertEqual(p["changed_paths"], ["tools/a.py"])
        self.assertTrue(p["code_graph_refs"])
        self.assertEqual(len(p["deterministic_receipt_refs"]), 1)

    def test_missing_binding_refused(self):
        with self.assertRaisesRegex(ContextCompileRefusal, "INVALID_CURRENTNESS_REF"):
            compile(currentness_ref=" ")


if __name__ == "__main__":
    unittest.main()
