import unittest

from tools.aura_review import review_context_invocation_membrane as m


def context_v1(**changes):
    value = {
        "schema": "AffectedConeContextV1",
        "repository": "owner/repo",
        "base_sha": "base1",
        "head_sha": "head1",
        "diff_digest": "diff1",
        "currentness_ref": "current1",
        "source_generation_ref": "source1",
        "codemap_generation_ref": "codemap1",
        "workgraph_generation_ref": "workgraph1",
        "route_policy_ref": "route1",
        "changed_paths": ["a.py"],
        "nodes": [{"path": "a.py", "required": True}],
    }
    value.update(changes)
    body = dict(value)
    body.pop("context_digest", None)
    value["context_digest"] = __import__("hashlib").sha256(
        __import__("json").dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
    ).hexdigest()
    return value


def expectation(ctx=None, **changes):
    ctx = ctx or context_v1()
    values = dict(
        issuer_ref="workgraph-owner://review-currentness",
        issuer_generation="owner-gen1",
        repository=ctx["repository"],
        base_sha=ctx["base_sha"],
        head_sha=ctx["head_sha"],
        diff_digest=ctx["diff_digest"],
        currentness_ref=ctx["currentness_ref"],
        source_generation_ref=ctx["source_generation_ref"],
        codemap_generation_ref=ctx["codemap_generation_ref"],
        workgraph_generation_ref=ctx["workgraph_generation_ref"],
        route_policy_ref=ctx["route_policy_ref"],
        context_digest=ctx["context_digest"],
    )
    values.update(changes)
    return m.CurrentReviewContextExpectationV1(**values)


def bind(ctx=None, exp=None, **changes):
    ctx = ctx or context_v1()
    exp = exp or expectation(ctx)
    values = dict(
        context=ctx,
        expectation=exp,
        reviewer="CODEX",
        adapter_ref="review-adapter://codex",
        adapter_version="v1",
        attempt_id="attempt-1",
        review_capsule_digest="capsule1",
    )
    values.update(changes)
    return m.bind_current_context_to_review_invocation(**values)


class ReviewContextInvocationMembraneTests(unittest.TestCase):
    def test_exact_current_context_binds_zero_authority(self):
        b = bind()
        self.assertEqual("CODEX", b.reviewer)
        self.assertFalse(b.reviewer_executed)
        self.assertFalse(b.review_pass_proven)
        self.assertFalse(b.github_mutation_authorized)
        self.assertFalse(b.execution_authorized)
        self.assertFalse(b.promotion_authorized)

    def test_mutated_context_with_stale_stored_digest_refused(self):
        ctx = context_v1()
        ctx["nodes"].append({"path": "b.py", "required": True})
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=ctx, exp=expectation(context_v1()))
        self.assertEqual("AFFECTED_CONE_DIGEST_MISMATCH", cm.exception.code)

    def test_internally_consistent_stale_head_refused_by_expectation(self):
        old = context_v1()
        current = context_v1(head_sha="head2")
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=old, exp=expectation(current))
        self.assertEqual("AFFECTED_CONE_HEAD_SHA_STALE", cm.exception.code)

    def test_stale_codemap_generation_refused(self):
        old = context_v1()
        current = context_v1(codemap_generation_ref="codemap2")
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=old, exp=expectation(current))
        self.assertEqual("AFFECTED_CONE_CODEMAP_GENERATION_REF_STALE", cm.exception.code)

    def test_stale_workgraph_generation_refused(self):
        old = context_v1()
        current = context_v1(workgraph_generation_ref="workgraph2")
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=old, exp=expectation(current))
        self.assertEqual("AFFECTED_CONE_WORKGRAPH_GENERATION_REF_STALE", cm.exception.code)

    def test_route_policy_drift_refused(self):
        old = context_v1()
        current = context_v1(route_policy_ref="route2")
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=old, exp=expectation(current))
        self.assertEqual("AFFECTED_CONE_ROUTE_POLICY_REF_STALE", cm.exception.code)

    def test_currentness_drift_refused(self):
        old = context_v1()
        current = context_v1(currentness_ref="current2")
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=old, exp=expectation(current))
        self.assertEqual("AFFECTED_CONE_CURRENTNESS_REF_STALE", cm.exception.code)

    def test_expectation_digest_mismatch_refused(self):
        ctx = context_v1()
        exp = expectation(ctx, context_digest="other")
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=ctx, exp=exp)
        self.assertEqual("AFFECTED_CONE_EXPECTATION_DIGEST_MISMATCH", cm.exception.code)

    def test_v2_fixture_refused(self):
        ctx = context_v1(schema="AffectedConeContextV2", mode="NONAUTHORITATIVE_FIXTURE")
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(ctx=ctx, exp=expectation(ctx))
        self.assertEqual("NONPRODUCTION_AFFECTED_CONE_REFUSED", cm.exception.code)

    def test_v2_production_allowed(self):
        ctx = context_v1(schema="AffectedConeContextV2", mode="PRODUCTION")
        b = bind(ctx=ctx, exp=expectation(ctx))
        self.assertEqual("AffectedConeContextV2", b.affected_cone_schema)

    def test_binding_identity_changes_with_attempt(self):
        self.assertNotEqual(bind().invocation_binding_digest, bind(attempt_id="attempt-2").invocation_binding_digest)

    def test_binding_identity_changes_with_capsule(self):
        self.assertNotEqual(bind().invocation_binding_digest, bind(review_capsule_digest="capsule2").invocation_binding_digest)

    def test_binding_identity_changes_with_expectation_issuer_generation(self):
        ctx = context_v1()
        a = bind(ctx=ctx, exp=expectation(ctx, issuer_generation="owner-gen1"))
        b = bind(ctx=ctx, exp=expectation(ctx, issuer_generation="owner-gen2"))
        self.assertNotEqual(a.invocation_binding_digest, b.invocation_binding_digest)

    def test_revalidation_accepts_unchanged(self):
        ctx = context_v1()
        exp = expectation(ctx)
        m.revalidate_invocation_binding(binding=bind(ctx=ctx, exp=exp), context=ctx, expectation=exp)

    def test_revalidation_rejects_context_change(self):
        ctx = context_v1()
        exp = expectation(ctx)
        binding = bind(ctx=ctx, exp=exp)
        changed = context_v1(head_sha="head2")
        with self.assertRaises(m.ReviewContextBindingRefusal):
            m.revalidate_invocation_binding(
                binding=binding, context=changed, expectation=expectation(changed)
            )

    def test_unsupported_reviewer_refused(self):
        with self.assertRaises(m.ReviewContextBindingRefusal) as cm:
            bind(reviewer="OTHER")
        self.assertEqual("REVIEWER_UNSUPPORTED", cm.exception.code)


if __name__ == "__main__":
    unittest.main()
