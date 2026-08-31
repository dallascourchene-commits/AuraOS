from __future__ import annotations

from dataclasses import replace
import hashlib
import unittest

from tools.aura_retrieval_progress_guard import (
    RetrievalFingerprint,
    RetrievalObservation,
)
from tools.aura_retrieval_progress_k27_alias_guard import (
    ALIAS_SCHEMA,
    VIEW_SCHEMA,
    AliasAwareDecision,
    ProjectionAliasOwnerProjection,
    SchemeBoundCoordinateViewProjection,
    assess_k27_alias_aware_retrieval_progress,
)


def d(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def view(
    *,
    scheme: str = "URL-SHA256-MOD27-v1",
    norm: str = "v1",
    canonical_key: str = "https://arxiv.org/abs/2608.02764",
    xyz: tuple[int, int, int] = (3, 4, 6),
    sid: str = "sid:arxiv:2608.02764",
    binding_generation: str = "registry:g1",
    **updates,
):
    base = dict(
        schema=VIEW_SCHEMA,
        scheme_id=scheme,
        normalization_version=norm,
        canonical_key=canonical_key,
        full_digest=hashlib.sha256(canonical_key.encode("utf-8")).hexdigest(),
        xyz=xyz,
        source_sid=sid,
        source_binding_generation=binding_generation,
        source_binding_receipt_digest=d(f"binding:{sid}:{binding_generation}"),
    )
    base.update(updates)
    return SchemeBoundCoordinateViewProjection(**base)


def session_view(**updates):
    base = dict(
        scheme="SESSION-ID-SHA256-MOD27-v1",
        canonical_key="arxiv:2608.02764",
        xyz=(21, 22, 26),
    )
    base.update(updates)
    return view(**base)


def fp(v: SchemeBoundCoordinateViewProjection, *, tool: str = "search", query: str = "same question"):
    return RetrievalFingerprint(
        provider="external",
        tool=tool,
        resource=v.resource_token,
        query_or_pattern=query,
        page_or_range="0:20",
        semantic_purpose="hydrate-source",
    )


def obs(
    v: SchemeBoundCoordinateViewProjection,
    *,
    state: str = "provider:g0",
    evidence: str = "evidence:e0",
    tool: str = "search",
    query: str = "same question",
):
    return RetrievalObservation(
        fingerprint=fp(v, tool=tool, query=query),
        provider_state_generation=state,
        evidence_digest=evidence,
    )


def alias(a: SchemeBoundCoordinateViewProjection, b: SchemeBoundCoordinateViewProjection, **updates):
    base = dict(
        schema=ALIAS_SCHEMA,
        view_digests=tuple(sorted((a.view_digest, b.view_digest))),
        source_sid=a.source_sid,
        owner_ref="registry:external-source",
        owner_generation="registry:g1",
        owner_receipt_digest=d("registry-alias-receipt"),
        relation_type="ALIASABLE_PROJECTIONS",
    )
    base.update(updates)
    return ProjectionAliasOwnerProjection(**base)


class RetrievalProgressK27AliasGuardTests(unittest.TestCase):
    def test_initial_semantic_source_retrieval_allowed_nonpromoting(self):
        a = view()
        receipt = assess_k27_alias_aware_retrieval_progress(
            previous=None,
            current=obs(a),
            previous_view=None,
            current_view=a,
        )
        self.assertEqual(AliasAwareDecision.ALLOW_INITIAL, receipt.decision)
        self.assertFalse(receipt.source_identity_authenticated_by_this_contract)
        self.assertFalse(receipt.source_currentness_proven)
        self.assertFalse(receipt.semantic_truth_proven)
        self.assertFalse(receipt.authority_granted)
        self.assertFalse(receipt.effect_authority_granted)
        self.assertFalse(receipt.semantic_k27_authority_minted)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)

    def test_identical_view_preserves_base_no_progress_law(self):
        a = view()
        first = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(a), previous_view=a, current_view=a,
            prior_no_progress_count=0,
        )
        self.assertEqual(AliasAwareDecision.CHANGE_AXIS_REQUIRED, first.decision)
        self.assertEqual(1, first.next_no_progress_count)
        second = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(a), previous_view=a, current_view=a,
            prior_no_progress_count=1,
        )
        self.assertEqual(AliasAwareDecision.COLLAPSE_CONE, second.decision)
        self.assertEqual(2, second.next_no_progress_count)

    def test_scheme_change_same_sid_without_owner_alias_holds(self):
        a, b = view(), session_view()
        receipt = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(b), previous_view=a, current_view=b,
            prior_no_progress_count=1,
        )
        self.assertEqual(AliasAwareDecision.HOLD_ALIAS_RESOLUTION_REQUIRED, receipt.decision)
        self.assertEqual("ALLOW_CHANGED_AXIS", receipt.raw_decision)
        self.assertIsNone(receipt.semantic_decision)
        self.assertTrue(receipt.alias_projection_required)
        self.assertFalse(receipt.alias_projection_consumed)
        self.assertEqual(1, receipt.next_no_progress_count)

    def test_verified_alias_quotients_false_changed_axis(self):
        a, b = view(), session_view()
        receipt = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(b), previous_view=a, current_view=b,
            alias_projection=alias(a, b), prior_no_progress_count=0,
        )
        self.assertEqual("ALLOW_CHANGED_AXIS", receipt.raw_decision)
        self.assertEqual("CHANGE_AXIS_REQUIRED", receipt.semantic_decision)
        self.assertEqual(AliasAwareDecision.CHANGE_AXIS_REQUIRED, receipt.decision)
        self.assertEqual(1, receipt.next_no_progress_count)
        self.assertFalse(receipt.alias_owner_authenticated_by_this_contract)

    def test_two_scheme_ping_pong_cannot_reset_no_progress_debt(self):
        a, b = view(), session_view()
        first = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(b), previous_view=a, current_view=b,
            alias_projection=alias(a, b), prior_no_progress_count=0,
        )
        self.assertEqual(AliasAwareDecision.CHANGE_AXIS_REQUIRED, first.decision)
        second = assess_k27_alias_aware_retrieval_progress(
            previous=obs(b), current=obs(a), previous_view=b, current_view=a,
            alias_projection=alias(b, a), prior_no_progress_count=first.next_no_progress_count,
        )
        self.assertEqual(AliasAwareDecision.COLLAPSE_CONE, second.decision)
        self.assertEqual(2, second.next_no_progress_count)

    def test_provider_or_evidence_change_is_real_state_transition_across_alias(self):
        a, b = view(), session_view()
        for field in ("state", "evidence"):
            with self.subTest(field=field):
                kwargs = {field: "changed"}
                receipt = assess_k27_alias_aware_retrieval_progress(
                    previous=obs(a), current=obs(b, **kwargs), previous_view=a, current_view=b,
                    alias_projection=alias(a, b), prior_no_progress_count=2,
                )
                self.assertEqual(AliasAwareDecision.ALLOW_STATE_TRANSITION, receipt.decision)
                self.assertEqual(0, receipt.next_no_progress_count)

    def test_real_tool_or_query_change_remains_changed_axis_across_alias(self):
        a, b = view(), session_view()
        for kwargs in ({"tool": "fetch"}, {"query": "different question"}):
            with self.subTest(kwargs=kwargs):
                receipt = assess_k27_alias_aware_retrieval_progress(
                    previous=obs(a), current=obs(b, **kwargs), previous_view=a, current_view=b,
                    alias_projection=alias(a, b), prior_no_progress_count=2,
                )
                self.assertEqual(AliasAwareDecision.ALLOW_CHANGED_AXIS, receipt.decision)
                self.assertEqual(0, receipt.next_no_progress_count)

    def test_different_sid_is_semantic_resource_change_without_alias(self):
        a = view()
        b = view(
            scheme="URL-SHA256-MOD27-v1",
            canonical_key="https://arxiv.org/abs/2607.10487",
            xyz=(5, 3, 9),
            sid="sid:arxiv:2607.10487",
        )
        receipt = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(b), previous_view=a, current_view=b,
            prior_no_progress_count=1,
        )
        self.assertEqual(AliasAwareDecision.ALLOW_CHANGED_AXIS, receipt.decision)
        self.assertFalse(receipt.alias_projection_required)

    def test_normalization_change_same_sid_is_route_recompute_not_progress(self):
        a = view(norm="v1")
        b = view(norm="v2", binding_generation="registry:g2")
        receipt = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(b), previous_view=a, current_view=b,
            alias_projection=alias(a, b, relation_type="SUPERSEDED_FOR_ROUTING_BY"),
            prior_no_progress_count=1,
        )
        self.assertEqual(AliasAwareDecision.COLLAPSE_CONE, receipt.decision)

    def test_same_xyz_different_full_digest_never_merges_sources(self):
        a = view(xyz=(3, 4, 6))
        b = view(
            canonical_key="https://example.org/different-source",
            xyz=(3, 4, 6),
            sid="sid:example:different",
        )
        self.assertEqual(a.xyz, b.xyz)
        self.assertNotEqual(a.full_digest, b.full_digest)
        receipt = assess_k27_alias_aware_retrieval_progress(
            previous=obs(a), current=obs(b), previous_view=a, current_view=b,
            prior_no_progress_count=1,
        )
        self.assertEqual(AliasAwareDecision.ALLOW_CHANGED_AXIS, receipt.decision)
        self.assertFalse(receipt.source_sid_same)

    def test_alias_view_or_sid_forgery_rejected(self):
        a, b = view(), session_view()
        wrong = view(canonical_key="https://example.org/wrong", sid=a.source_sid, xyz=(1, 1, 1))
        with self.assertRaisesRegex(ValueError, "K27_ALIAS_VIEW_SET_MISMATCH"):
            assess_k27_alias_aware_retrieval_progress(
                previous=obs(a), current=obs(b), previous_view=a, current_view=b,
                alias_projection=alias(a, wrong), prior_no_progress_count=0,
            )
        with self.assertRaisesRegex(ValueError, "K27_ALIAS_SOURCE_SID_MISMATCH"):
            alias(a, b, source_sid="sid:forged").validate()
            assess_k27_alias_aware_retrieval_progress(
                previous=obs(a), current=obs(b), previous_view=a, current_view=b,
                alias_projection=alias(a, b, source_sid="sid:forged"), prior_no_progress_count=0,
            )

    def test_stale_alias_projection_rejected(self):
        a, b = view(), session_view()
        with self.assertRaisesRegex(ValueError, "K27_ALIAS_OWNER_PROJECTION_NOT_CURRENT"):
            assess_k27_alias_aware_retrieval_progress(
                previous=obs(a), current=obs(b), previous_view=a, current_view=b,
                alias_projection=alias(a, b, owner_state="STALE"), prior_no_progress_count=0,
            )

    def test_route_resource_must_bind_exact_view_digest(self):
        a = view()
        bad = RetrievalObservation(
            RetrievalFingerprint("external", "search", "k27view:" + "0" * 64, "q", "0:20", "hydrate-source"),
            "g0",
            "e0",
        )
        with self.assertRaisesRegex(ValueError, "CURRENT_RETRIEVAL_RESOURCE_NOT_BOUND_TO_K27_VIEW"):
            assess_k27_alias_aware_retrieval_progress(
                previous=None, current=bad, previous_view=None, current_view=a,
            )

    def test_view_and_alias_authority_widening_rejected(self):
        for field in (
            "source_identity_authenticated_by_this_contract",
            "source_currentness_proven",
            "semantic_truth_proven",
            "routing_authority_granted",
            "effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
        ):
            with self.subTest(view_field=field):
                with self.assertRaisesRegex(ValueError, "K27_VIEW_EXCEEDED_NONPROMOTION_CEILING"):
                    replace(view(), **{field: True}).validate()
        a, b = view(), session_view()
        for field in (
            "owner_authenticated_by_this_contract",
            "source_truth_proven",
            "source_currentness_proven_by_this_contract",
            "effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
        ):
            with self.subTest(alias_field=field):
                with self.assertRaisesRegex(ValueError, "K27_ALIAS_EXCEEDED_NONPROMOTION_CEILING"):
                    replace(alias(a, b), **{field: True}).validate()

    def test_receipt_identity_deterministic_and_alias_bearing(self):
        a, b = view(), session_view()
        kwargs = dict(
            previous=obs(a), current=obs(b), previous_view=a, current_view=b,
            alias_projection=alias(a, b), prior_no_progress_count=1,
        )
        x = assess_k27_alias_aware_retrieval_progress(**kwargs)
        y = assess_k27_alias_aware_retrieval_progress(**kwargs)
        self.assertEqual(x.receipt_digest, y.receipt_digest)
        self.assertIsNotNone(x.alias_projection_digest)
        self.assertEqual(AliasAwareDecision.COLLAPSE_CONE, x.decision)


if __name__ == "__main__":
    unittest.main()
