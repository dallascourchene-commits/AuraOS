import unittest

from tools.aura_review.aura_review_context_compiler import CoordinateLocatorV1, GraphEdgeV1, compile_affected_cone
import tools.aura_review.aura_review_cache_policy as m

CGEN = "codemap-gen-1"
WGEN = "workgraph-gen-1"


def context(**kw):
    args = dict(repository="dallascourchene-commits/AuraOS", base_sha="a"*40, head_sha="b"*40,
        diff_digest="d"*64, currentness_ref="cur-1", source_generation_ref="src-1",
        codemap_generation_ref=CGEN, workgraph_generation_ref=WGEN, route_policy_ref="route-v1",
        changed_paths=("tools/a.py",), code_graph_edges=(), workgraph_edges=(),
        coordinate_locators=(CoordinateLocatorV1("tools/a.py", "WS1/L2/abc", "cg1"),),
        expected_codemap_generation_ref=CGEN, expected_workgraph_generation_ref=WGEN,
        max_nodes=64, optional_depth=0)
    args.update(kw)
    return compile_affected_cone(**args)


def key(ctx=None, **kw):
    args = dict(responsibility=m.CacheResponsibility.REVIEW_CONTEXT, reviewer="CODEX",
        reviewer_version="v1", model_signature="model:v1", tokenizer_identity="tok:v1",
        system_tool_prefix_digest="prefix:v1", context_strategy="MINIMUM",
        principal_id="principal:A", arena_id="arena:A")
    args.update(kw)
    return m.compile_cache_key(ctx or context(), **args)


def owner_expectation(**kw):
    args = dict(owner_ref="cache-owner", owner_generation="owner-g1",
        owner_currentness_ref="owner-current-1", expected_signature_ref="sig:record",
        expected_principal_id="principal:A", expected_arena_id="arena:A",
        resolver_ref="resolver:cache", resolver_generation="resolver-g1",
        resolver_currentness_ref="resolver-current-1")
    args.update(kw)
    return m.ResolvedCacheOwnerExpectationV2(**args)


def record(k=None, **kw):
    k = k or key()
    args = dict(key_digest=k.key_digest, context_digest=k.context_digest,
        currentness_ref=k.currentness_ref, materialized_context_digest="materialized:"+k.context_digest,
        cache_ref="cache:1", source_ref="source:context", tier=m.CacheTier.HOT_PREFIX,
        byte_size=123, owner_ref="cache-owner", owner_generation="owner-g1",
        owner_currentness_ref="owner-current-1", compiler_version="compiler:v2",
        evidence_set_digest="evidence:set:1", principal_id=k.principal_id, arena_id=k.arena_id,
        payload_receipt_ref="payload:receipt:1", owner_signature_ref="sig:record", revoked=False)
    args.update(kw)
    return m.ReviewContextCacheRecordV2(**args)


def observer_expectation(**kw):
    args = dict(observer_ref="read-observer", observer_generation="observer-g1",
        observer_currentness_ref="observer-current-1", expected_signature_ref="sig:read",
        resolver_ref="resolver:read", resolver_generation="resolver-read-g1",
        resolver_currentness_ref="resolver-read-current-1")
    args.update(kw)
    return m.ResolvedReadObserverExpectationV2(**args)


def observation(k=None, r=None, **kw):
    k = k or key(); r = r or record(k)
    args = dict(key_digest=k.key_digest, record_digest=r.record_digest, context_digest=k.context_digest,
        materialized_context_digest=r.materialized_context_digest, cache_ref=r.cache_ref,
        read_attempt_id="read:1", observer_ref="read-observer", observer_generation="observer-g1",
        observer_currentness_ref="observer-current-1", observer_signature_ref="sig:read",
        source_currentness_ref=k.currentness_ref, cache_read_observed=True)
    args.update(kw)
    return m.TrustedCacheReadObservationV2(**args)


def router_input(**kw):
    args = dict(risk_score=0.2, reviewer_availability=(("CODEX", True), ("CODERABBIT", True)),
        issuer_ref="qdkt-owner", issuer_generation="qdkt-g1", issuer_currentness_ref="qdkt-current-1",
        source_currentness_ref="cur-1", signature_ref="sig:qdkt", revoked=False)
    args.update(kw)
    return m.TrustedQDKTRouterInputV2(**args)


def router_expectation(**kw):
    args = dict(issuer_ref="qdkt-owner", issuer_generation="qdkt-g1",
        issuer_currentness_ref="qdkt-current-1", expected_signature_ref="sig:qdkt",
        source_currentness_ref="cur-1", resolver_ref="resolver:qdkt",
        resolver_generation="resolver-qdkt-g1", resolver_currentness_ref="resolver-qdkt-current-1")
    args.update(kw)
    return m.ResolvedQDKTInputExpectationV2(**args)


class CachePolicyV2Tests(unittest.TestCase):
    def test_01_valid_context_key(self):
        self.assertEqual(64, len(key().key_digest))

    def test_02_fixture_context_refused(self):
        c = context(fixture_mode=True, expected_codemap_generation_ref=None, expected_workgraph_generation_ref=None)
        with self.assertRaisesRegex(m.ReviewCacheRefusal, "NONAUTHORITATIVE_AFFECTED_CONE_CONTEXT"): key(c)

    def test_03_mutated_context_refused(self):
        c = context(); c["changed_paths"].append("mutated.py")
        with self.assertRaisesRegex(m.ReviewCacheRefusal, "AFFECTED_CONE_REVALIDATION_FAILED"): key(c)

    def test_04_model_prefix_owner_rejected(self):
        with self.assertRaisesRegex(m.ReviewCacheRefusal, "CACHE_RESPONSIBILITY_OWNER_MISMATCH"):
            key(responsibility=m.CacheResponsibility.MODEL_PREFIX_KV)

    def test_05_review_receipt_owner_rejected(self):
        with self.assertRaisesRegex(m.ReviewCacheRefusal, "CACHE_RESPONSIBILITY_OWNER_MISMATCH"):
            key(responsibility=m.CacheResponsibility.REVIEW_RECEIPT)

    def test_06_coordinate_generation_changes_key(self):
        a = key(context(coordinate_locators=(CoordinateLocatorV1("tools/a.py", "WS1/L2/abc", "cg1"),)))
        b = key(context(coordinate_locators=(CoordinateLocatorV1("tools/a.py", "WS1/L2/abc", "cg2"),)))
        d = m.cache_key_delta(a,b)
        self.assertNotEqual(a.key_digest,b.key_digest); self.assertEqual(("PLACEMENT",),d["changed_axes"])
        self.assertEqual("RELOCALIZE_REVIEW_CONTEXT",d["disposition"]); self.assertFalse(d["semantic_source_refetch_required"])

    def test_07_source_generation_delta(self):
        d=m.cache_key_delta(key(context(source_generation_ref="src-1")), key(context(source_generation_ref="src-2")))
        self.assertIn("SOURCE",d["changed_axes"]); self.assertTrue(d["semantic_source_refetch_required"])

    def test_08_target_head_delta(self):
        self.assertIn("TARGET",m.cache_key_delta(key(context(head_sha="b"*40)),key(context(head_sha="c"*40)))["changed_axes"])

    def test_09_principal_delta_blocks_cross_principal(self):
        d=m.cache_key_delta(key(principal_id="principal:A"),key(principal_id="principal:B"))
        self.assertIn("PRINCIPAL_CONTEXT",d["changed_axes"]); self.assertEqual("REHYDRATE_NO_CROSS_PRINCIPAL_REUSE",d["disposition"])

    def test_10_review_runtime_delta(self):
        self.assertIn("REVIEW_RUNTIME",m.cache_key_delta(key(reviewer_version="v1"),key(reviewer_version="v2"))["changed_axes"])

    def test_11_exact_key_delta_reuses(self):
        a=key(); d=m.cache_key_delta(a,a); self.assertEqual((),d["changed_axes"]); self.assertEqual("REUSE_KEY_EXACT",d["disposition"])

    def test_12_multiple_axes_union(self):
        d=m.cache_key_delta(key(),key(context(head_sha="c"*40),principal_id="principal:B",reviewer_version="v2"))
        self.assertEqual({"TARGET","PRINCIPAL_CONTEXT","REVIEW_RUNTIME"},set(d["changed_axes"]))

    def test_13_cache_miss_rehydrates(self):
        self.assertEqual("CACHE_MISS",m.admit_cache_candidate(key(),None,owner_expectation=owner_expectation())["reason"])

    def test_14_missing_owner_trust_rehydrates(self):
        k=key(); self.assertEqual("CACHE_OWNER_TRUST_UNRESOLVED",m.admit_cache_candidate(k,record(k),owner_expectation=None)["reason"])

    def test_15_wrong_key_rehydrates(self):
        k=key(); self.assertEqual("CACHE_KEY_MISMATCH",m.admit_cache_candidate(k,record(k,key_digest="wrong"),owner_expectation=owner_expectation())["reason"])

    def test_16_revoked_record_rehydrates(self):
        k=key(); self.assertEqual("CACHE_RECORD_REVOKED",m.admit_cache_candidate(k,record(k,revoked=True),owner_expectation=owner_expectation())["reason"])

    def test_17_wrong_owner_signature_rehydrates(self):
        k=key(); self.assertEqual("CACHE_OWNER_TRUST_MISMATCH",m.admit_cache_candidate(k,record(k,owner_signature_ref="sig:wrong"),owner_expectation=owner_expectation())["reason"])

    def test_18_principal_mismatch_rehydrates(self):
        k=key(); self.assertEqual("CACHE_PRINCIPAL_ARENA_MISMATCH",m.admit_cache_candidate(k,record(k,principal_id="principal:B"),owner_expectation=owner_expectation())["reason"])

    def test_19_materialized_digest_may_differ_from_logical(self):
        k=key(); a=m.admit_cache_candidate(k,record(k,materialized_context_digest="materialized:independent"),owner_expectation=owner_expectation())
        self.assertEqual("CACHE_REUSE_ELIGIBLE",a["disposition"]); self.assertEqual("materialized:independent",a["materialized_context_digest"])

    def test_20_exact_trusted_record_is_only_eligible_not_hit(self):
        k=key(); a=m.admit_cache_candidate(k,record(k),owner_expectation=owner_expectation()); self.assertFalse(a["cache_hit_proven"])

    def test_21_unobserved_read_refused(self):
        k=key(); r=record(k); o=observation(k,r,cache_read_observed=False)
        with self.assertRaisesRegex(m.ReviewCacheRefusal,"CACHE_READ_NOT_OBSERVED"):
            m.observe_cache_use(k,r,owner_expectation=owner_expectation(),read_observation=o,observer_expectation=observer_expectation())

    def test_22_wrong_observer_signature_refused(self):
        k=key(); r=record(k); o=observation(k,r,observer_signature_ref="sig:wrong")
        with self.assertRaisesRegex(m.ReviewCacheRefusal,"CACHE_READ_OBSERVER_TRUST_MISMATCH"):
            m.observe_cache_use(k,r,owner_expectation=owner_expectation(),read_observation=o,observer_expectation=observer_expectation())

    def test_23_wrong_materialized_content_refused(self):
        k=key(); r=record(k); o=observation(k,r,materialized_context_digest="wrong")
        with self.assertRaisesRegex(m.ReviewCacheRefusal,"CACHE_READ_BINDING_MISMATCH"):
            m.observe_cache_use(k,r,owner_expectation=owner_expectation(),read_observation=o,observer_expectation=observer_expectation())

    def test_24_exact_observed_read_has_zero_review_authority(self):
        k=key(); r=record(k); out=m.observe_cache_use(k,r,owner_expectation=owner_expectation(),read_observation=observation(k,r),observer_expectation=observer_expectation())
        self.assertFalse(out.review_pass_proven); self.assertFalse(out.execution_authorized); self.assertFalse(out.promotion_authorized); self.assertEqual(64,len(out.observation_digest))

    def test_25_missing_qdkt_input_is_conservative(self):
        p=m.compile_qdkt_review_plan(context(),phase="PRE_GITHUB",deterministic_tools=("PYTEST",))
        self.assertFalse(p["router_input_trusted"]); self.assertEqual(1.0,p["risk_score"]); self.assertEqual(2,p["optional_depth_rank"]); self.assertEqual("REVIEW_INCOMPLETE",p["review_disposition"])

    def test_26_untrusted_qdkt_signature_is_conservative(self):
        p=m.compile_qdkt_review_plan(context(),phase="PRE_GITHUB",deterministic_tools=(),router_input=router_input(signature_ref="sig:wrong"),router_expectation=router_expectation())
        self.assertFalse(p["router_input_trusted"]); self.assertEqual("REVIEW_INCOMPLETE",p["review_disposition"])

    def test_27_stale_qdkt_currentness_is_conservative(self):
        p=m.compile_qdkt_review_plan(context(),phase="PRE_GITHUB",deterministic_tools=(),router_input=router_input(source_currentness_ref="old"),router_expectation=router_expectation())
        self.assertFalse(p["router_input_trusted"]); self.assertEqual(1.0,p["risk_score"])

    def test_28_trusted_low_risk_pre_github_ready(self):
        p=m.compile_qdkt_review_plan(context(),phase="PRE_GITHUB",deterministic_tools=("PYTEST","PYTEST"),router_input=router_input(risk_score=0.2),router_expectation=router_expectation())
        self.assertTrue(p["router_input_trusted"]); self.assertEqual(0,p["optional_depth_rank"]); self.assertEqual("REVIEW_ROUTE_READY",p["review_disposition"]); self.assertFalse(p["review_pass_proven"])

    def test_29_github_lane_requires_both_reviewers(self):
        p=m.compile_qdkt_review_plan(context(),phase="GITHUB_REVIEW_LANE",deterministic_tools=(),router_input=router_input(reviewer_availability=(("CODEX",True),("CODERABBIT",False))),router_expectation=router_expectation())
        self.assertEqual(("CODERABBIT",),p["unavailable_reviewers"]); self.assertEqual("REVIEW_INCOMPLETE",p["review_disposition"])

    def test_30_mandatory_paths_preserved_under_low_risk(self):
        c=context(code_graph_edges=(GraphEdgeV1("tools/a.py","tools/b.py","CALLS",CGEN,"cg:1"),))
        p=m.compile_qdkt_review_plan(c,phase="PRE_GITHUB",deterministic_tools=(),router_input=router_input(risk_score=0.0),router_expectation=router_expectation())
        self.assertEqual(["tools/a.py","tools/b.py"],p["mandatory_paths"])

    def test_31_mandatory_count_tamper_refused(self):
        c=context(); c["required_node_count"]=99
        import hashlib,json
        body=dict(c); body.pop("context_digest"); c["context_digest"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
        with self.assertRaisesRegex(m.ReviewCacheRefusal,"AFFECTED_CONE_REVALIDATION_FAILED|MANDATORY_CONTEXT_COUNT_MISMATCH"):
            m.compile_qdkt_review_plan(c,phase="PRE_GITHUB",deterministic_tools=())

    def test_32_qdkt_and_cache_never_grant_effect_or_promotion(self):
        p=m.compile_qdkt_review_plan(context(),phase="PRE_GITHUB",deterministic_tools=(),router_input=router_input(),router_expectation=router_expectation())
        self.assertFalse(p["qdkt_is_authority"]); self.assertFalse(p["cache_is_truth"]); self.assertFalse(p["execution_authorized"]); self.assertFalse(p["promotion_authorized"])


if __name__ == "__main__": unittest.main()
