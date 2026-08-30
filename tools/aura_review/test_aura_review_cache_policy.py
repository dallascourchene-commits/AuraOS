import unittest

from tools.aura_review.aura_review_cache_policy import (
    CacheResponsibility,
    CacheTier,
    ReviewCacheRefusal,
    ReviewContextCacheRecordV1,
    admit_cache_candidate,
    compile_cache_key,
    compile_qdkt_review_plan,
    observe_cache_use,
)


def context():
    return {
        "schema": "AffectedConeContextV1",
        "repository": "dallascourchene-commits/AuraOS",
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "diff_digest": "d" * 64,
        "context_digest": "c" * 64,
        "currentness_ref": "cur-1",
        "source_generation_ref": "src-1",
        "codemap_generation_ref": "code-1",
        "workgraph_generation_ref": "work-1",
        "route_policy_ref": "route-1",
        "required_node_count": 2,
        "nodes": [
            {"path": "a.py", "required": True},
            {"path": "must_not.py", "required": True},
            {"path": "optional.py", "required": False},
        ],
    }


def key(ctx=None, **kw):
    args = dict(
        responsibility=CacheResponsibility.REVIEW_CONTEXT,
        reviewer="CODEX",
        reviewer_version="codex-v1",
        model_signature="model-v1",
        tokenizer_identity="tok-v1",
        system_tool_prefix_digest="p" * 64,
        context_strategy="MINIMUM_CONSEQUENCE_COMPLETE",
        principal_id="principal-1",
        arena_id="arena-1",
    )
    args.update(kw)
    return compile_cache_key(ctx or context(), **args)


def record(k=None, **kw):
    k = k or key()
    args = dict(
        key_digest=k.key_digest,
        responsibility=k.responsibility,
        context_digest=k.context_digest,
        currentness_ref=k.currentness_ref,
        materialized_context_digest=k.context_digest,
        cache_ref="cache://1",
        source_ref="host://cache/1",
        tier=CacheTier.WARM_PAGED,
        byte_size=1024,
    )
    args.update(kw)
    return ReviewContextCacheRecordV1(**args)


class T(unittest.TestCase):
    def test_exact_record_is_eligible_but_not_hit_proof(self):
        k = key()
        a = admit_cache_candidate(k, record(k))
        self.assertEqual(a["disposition"], "CACHE_REUSE_ELIGIBLE")
        self.assertFalse(a["cache_hit_proven"])

    def test_pointer_absence_rehydrates(self):
        self.assertEqual(admit_cache_candidate(key(), None)["reason"], "CACHE_MISS")

    def test_head_change_invalidates_key(self):
        old_key = key()
        old = record(old_key)
        ctx = context()
        ctx["head_sha"] = "e" * 40
        self.assertEqual(admit_cache_candidate(key(ctx), old)["reason"], "CACHE_KEY_MISMATCH")

    def test_currentness_change_invalidates_key(self):
        old_key = key()
        old = record(old_key)
        ctx = context()
        ctx["currentness_ref"] = "cur-2"
        self.assertEqual(admit_cache_candidate(key(ctx), old)["reason"], "CACHE_KEY_MISMATCH")

    def test_reviewer_version_invalidates(self):
        k = key()
        self.assertEqual(admit_cache_candidate(key(reviewer_version="codex-v2"), record(k))["reason"], "CACHE_KEY_MISMATCH")

    def test_model_signature_invalidates(self):
        k = key()
        self.assertEqual(admit_cache_candidate(key(model_signature="model-v2"), record(k))["reason"], "CACHE_KEY_MISMATCH")

    def test_tokenizer_invalidates(self):
        k = key()
        self.assertEqual(admit_cache_candidate(key(tokenizer_identity="tok-v2"), record(k))["reason"], "CACHE_KEY_MISMATCH")

    def test_system_tool_prefix_invalidates(self):
        k = key()
        self.assertEqual(admit_cache_candidate(key(system_tool_prefix_digest="q" * 64), record(k))["reason"], "CACHE_KEY_MISMATCH")

    def test_context_strategy_invalidates(self):
        k = key()
        self.assertEqual(admit_cache_candidate(key(context_strategy="DEEP"), record(k))["reason"], "CACHE_KEY_MISMATCH")

    def test_principal_isolation(self):
        k = key()
        self.assertEqual(admit_cache_candidate(key(principal_id="principal-2"), record(k))["reason"], "CACHE_KEY_MISMATCH")

    def test_arena_isolation(self):
        k = key()
        self.assertEqual(admit_cache_candidate(key(arena_id="arena-2"), record(k))["reason"], "CACHE_KEY_MISMATCH")

    def test_responsibility_cross_credit_refused(self):
        k = key()
        r = record(k, responsibility=CacheResponsibility.MODEL_PREFIX_KV)
        self.assertEqual(admit_cache_candidate(k, r)["reason"], "RESPONSIBILITY_MISMATCH")

    def test_materialized_context_mismatch_rehydrates(self):
        k = key()
        r = record(k, materialized_context_digest="x" * 64)
        self.assertEqual(admit_cache_candidate(k, r)["reason"], "CONTEXT_DIGEST_MISMATCH")

    def test_record_currentness_stale_rehydrates(self):
        k = key()
        r = record(k, currentness_ref="cur-old")
        self.assertEqual(admit_cache_candidate(k, r)["reason"], "CACHE_CURRENTNESS_STALE")

    def test_unobserved_read_cannot_be_claimed(self):
        k = key()
        r = record(k)
        with self.assertRaisesRegex(ReviewCacheRefusal, "CACHE_READ_NOT_OBSERVED"):
            observe_cache_use(k, r, read_attempt_id="read-1", observer_ref="host://cache", observed_materialized_digest=k.context_digest, cache_read_observed=False, source_currentness_ref=k.currentness_ref)

    def test_observed_wrong_content_refused(self):
        k = key()
        r = record(k)
        with self.assertRaisesRegex(ReviewCacheRefusal, "OBSERVED_CACHE_CONTENT_MISMATCH"):
            observe_cache_use(k, r, read_attempt_id="read-1", observer_ref="host://cache", observed_materialized_digest="x" * 64, cache_read_observed=True, source_currentness_ref=k.currentness_ref)

    def test_observed_stale_currentness_refused(self):
        k = key()
        r = record(k)
        with self.assertRaisesRegex(ReviewCacheRefusal, "OBSERVED_CACHE_CURRENTNESS_STALE"):
            observe_cache_use(k, r, read_attempt_id="read-1", observer_ref="host://cache", observed_materialized_digest=k.context_digest, cache_read_observed=True, source_currentness_ref="old")

    def test_observed_exact_read_yields_non_authoritative_evidence(self):
        k = key()
        r = record(k)
        e = observe_cache_use(k, r, read_attempt_id="read-1", observer_ref="host://cache", observed_materialized_digest=k.context_digest, cache_read_observed=True, source_currentness_ref=k.currentness_ref)
        self.assertTrue(e.cache_read_observed)
        self.assertFalse(e.review_pass_proven)
        self.assertFalse(e.execution_authorized)

    def test_qdkt_never_drops_mandatory_paths(self):
        plan = compile_qdkt_review_plan(context(), phase="PRE_GITHUB", risk_score=0.0, deterministic_tools=("CODEMAP",), reviewer_availability={"CODEX": True})
        self.assertEqual(plan["mandatory_paths"], ["a.py", "must_not.py"])
        self.assertEqual(plan["optional_depth_rank"], 0)

    def test_qdkt_high_risk_expands_only_optional_rank(self):
        plan = compile_qdkt_review_plan(context(), phase="PRE_GITHUB", risk_score=0.9, deterministic_tools=("UNIT_TESTS", "CODEMAP"), reviewer_availability={"CODEX": True})
        self.assertEqual(plan["mandatory_paths"], ["a.py", "must_not.py"])
        self.assertEqual(plan["optional_depth_rank"], 2)
        self.assertFalse(plan["qdkt_is_authority"])

    def test_github_lane_requires_both_reviewers_available(self):
        plan = compile_qdkt_review_plan(context(), phase="GITHUB_REVIEW_LANE", risk_score=0.5, deterministic_tools=("CODEMAP",), reviewer_availability={"CODEX": True, "CODERABBIT": False})
        self.assertEqual(plan["review_disposition"], "REVIEW_INCOMPLETE")
        self.assertEqual(plan["unavailable_reviewers"], ("CODERABBIT",))

    def test_qdkt_plan_is_deterministic(self):
        a = compile_qdkt_review_plan(context(), phase="PRE_GITHUB", risk_score=0.5, deterministic_tools=("B", "A"), reviewer_availability={"CODEX": True})
        b = compile_qdkt_review_plan(context(), phase="PRE_GITHUB", risk_score=0.5, deterministic_tools=("A", "B"), reviewer_availability={"CODEX": True})
        self.assertEqual(a["plan_digest"], b["plan_digest"])

    def test_qdkt_mandatory_count_mismatch_fails_closed(self):
        ctx = context()
        ctx["required_node_count"] = 3
        with self.assertRaisesRegex(ReviewCacheRefusal, "MANDATORY_CONTEXT_COUNT_MISMATCH"):
            compile_qdkt_review_plan(ctx, phase="PRE_GITHUB", risk_score=0.5, deterministic_tools=("A",), reviewer_availability={"CODEX": True})

    def test_invalid_risk_score_refused(self):
        with self.assertRaisesRegex(ReviewCacheRefusal, "INVALID_RISK_SCORE"):
            compile_qdkt_review_plan(context(), phase="PRE_GITHUB", risk_score=1.1, deterministic_tools=("A",), reviewer_availability={"CODEX": True})


if __name__ == "__main__":
    unittest.main()
