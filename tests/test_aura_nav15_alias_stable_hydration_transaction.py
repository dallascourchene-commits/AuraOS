from __future__ import annotations

from dataclasses import replace
import hashlib
import unittest

from tools.aura_retrieval_progress_guard import RetrievalFingerprint, RetrievalObservation
from tools.aura_retrieval_progress_k27_alias_guard import (
    ALIAS_SCHEMA,
    VIEW_SCHEMA,
    ProjectionAliasOwnerProjection,
    SchemeBoundCoordinateViewProjection,
)
import tools.aura_nav15_alias_stable_hydration_transaction as m


def d(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def view(
    *,
    scheme: str = "URL-SHA256-MOD27-v1",
    canonical_key: str = "https://arxiv.org/abs/2608.02764",
    xyz: tuple[int, int, int] = (3, 4, 6),
    sid: str = "sid:arxiv:2608.02764",
):
    return SchemeBoundCoordinateViewProjection(
        schema=VIEW_SCHEMA,
        scheme_id=scheme,
        normalization_version="v1",
        canonical_key=canonical_key,
        full_digest=hashlib.sha256(canonical_key.encode("utf-8")).hexdigest(),
        xyz=xyz,
        source_sid=sid,
        source_binding_generation="registry:g1",
        source_binding_receipt_digest=d(f"binding:{sid}"),
    )


def session_view(*, sid: str = "sid:arxiv:2608.02764"):
    return view(
        scheme="SESSION-ID-SHA256-MOD27-v1",
        canonical_key="arxiv:2608.02764",
        xyz=(21, 22, 26),
        sid=sid,
    )


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
    evidence: str = d("evidence:e0"),
    tool: str = "search",
    query: str = "same question",
):
    return RetrievalObservation(
        fingerprint=fp(v, tool=tool, query=query),
        provider_state_generation=state,
        evidence_digest=evidence,
    )


def alias(a: SchemeBoundCoordinateViewProjection, b: SchemeBoundCoordinateViewProjection):
    return ProjectionAliasOwnerProjection(
        schema=ALIAS_SCHEMA,
        view_digests=tuple(sorted((a.view_digest, b.view_digest))),
        source_sid=a.source_sid,
        owner_ref="registry:external-source",
        owner_generation="registry:g1",
        owner_receipt_digest=d("registry-alias-receipt"),
        relation_type="ALIASABLE_PROJECTIONS",
    )


def transaction(
    current: RetrievalObservation,
    current_view: SchemeBoundCoordinateViewProjection,
    *,
    raw_decision: str,
    admitted: bool = True,
    parent_head: str = m.TRANSACTION_HEAD,
    evidence_digest: str | None = None,
    fingerprint_digest: str | None = None,
    source_identity: str | None = None,
):
    disposition = "ADMIT_BOUNDED_TRANSACTION" if admitted else "HOLD_ROUTE_RECOMPUTE"
    reason = (
        "ROUTE_EPOCH_AND_RETRIEVAL_NOVELTY_GATES_COMMUTE"
        if admitted
        else "SCHEME_OR_ROUTE_PROJECTION_CHANGED_RECOMPUTE_REQUIRED"
    )
    t = m.SchemeSerializableTransactionProjectionV1(
        parent_head=parent_head,
        schema=m.TRANSACTION_SCHEMA,
        disposition=disposition,
        reason=reason,
        source_identity=source_identity or current_view.source_sid,
        pre_route_projection_digest=d("pre-route"),
        post_route_projection_digest=d("post-route"),
        owner_epoch="owner:e1",
        semantic_plan_digest=d("plan"),
        evidence_generation_key="eg:g1",
        target_level=4,
        retrieval_fingerprint_digest=fingerprint_digest or current.fingerprint.digest,
        retrieval_evidence_digest=evidence_digest or current.evidence_digest,
        retrieval_disposition=raw_decision,
        exact_reopen_handle_digest=d("reopen"),
        transaction_digest="0" * 64,
        bounded_transaction_admitted=admitted,
    )
    return replace(t, transaction_digest=m._transaction_digest(t))


class Nav15AliasStableHydrationTransactionTests(unittest.TestCase):
    def test_initial_transaction_remains_candidate_only(self):
        a = view()
        current = obs(a)
        t = transaction(current, a, raw_decision="ALLOW_INITIAL")
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=None,
            current=current,
            previous_view=None,
            current_view=a,
        )
        self.assertTrue(r.ready)
        self.assertEqual(
            r.disposition,
            m.Nav15Disposition.ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE,
        )
        self.assertFalse(r.source_currentness_proven)
        self.assertFalse(r.semantic_truth_proven)
        self.assertFalse(r.evidence_admitted)
        self.assertFalse(r.materialization_executed)
        self.assertFalse(r.authorization_issued)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.semantic_k27_authority)
        self.assertFalse(r.native_private_transformer_kv_accessed)

    def test_same_sid_scheme_change_without_alias_downgrades_transaction(self):
        a, b = view(), session_view()
        current = obs(b)
        t = transaction(current, b, raw_decision="ALLOW_CHANGED_AXIS")
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=obs(a),
            current=current,
            previous_view=a,
            current_view=b,
        )
        self.assertEqual(r.disposition, m.Nav15Disposition.HOLD_ALIAS_RESOLUTION_REQUIRED)
        self.assertFalse(r.ready)

    def test_scheme_rotation_with_alias_cannot_reset_first_no_progress_debt(self):
        a, b = view(), session_view()
        current = obs(b)
        t = transaction(current, b, raw_decision="ALLOW_CHANGED_AXIS")
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=obs(a),
            current=current,
            previous_view=a,
            current_view=b,
            alias_projection=alias(a, b),
            prior_no_progress_count=0,
        )
        self.assertEqual(
            r.disposition,
            m.Nav15Disposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
        )

    def test_scheme_ping_pong_with_alias_collapses_transaction_cone(self):
        a, b = view(), session_view()
        current = obs(b)
        t = transaction(current, b, raw_decision="ALLOW_CHANGED_AXIS")
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=obs(a),
            current=current,
            previous_view=a,
            current_view=b,
            alias_projection=alias(a, b),
            prior_no_progress_count=1,
        )
        self.assertEqual(r.disposition, m.Nav15Disposition.COLLAPSE_RETRIEVAL_CONE)

    def test_real_provider_transition_across_alias_preserves_candidate(self):
        a, b = view(), session_view()
        current = obs(b, state="provider:g1")
        # Raw #754 sees the resource token change first; #759 then proves a semantic state transition.
        t = transaction(current, b, raw_decision="ALLOW_CHANGED_AXIS")
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=obs(a),
            current=current,
            previous_view=a,
            current_view=b,
            alias_projection=alias(a, b),
            prior_no_progress_count=2,
        )
        self.assertTrue(r.ready)
        self.assertEqual(r.alias_aware_decision, "ALLOW_STATE_TRANSITION")
        self.assertEqual(r.raw_retrieval_decision, "ALLOW_CHANGED_AXIS")

    def test_real_evidence_transition_across_alias_preserves_candidate(self):
        a, b = view(), session_view()
        current = obs(b, evidence=d("evidence:e1"))
        t = transaction(current, b, raw_decision="ALLOW_CHANGED_AXIS")
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=obs(a),
            current=current,
            previous_view=a,
            current_view=b,
            alias_projection=alias(a, b),
        )
        self.assertTrue(r.ready)
        self.assertEqual(r.alias_aware_decision, "ALLOW_STATE_TRANSITION")

    def test_same_observation_binding_is_mandatory(self):
        a = view()
        current = obs(a)
        cases = (
            transaction(current, a, raw_decision="ALLOW_INITIAL", evidence_digest=d("other-evidence")),
            transaction(current, a, raw_decision="ALLOW_INITIAL", fingerprint_digest=d("other-fingerprint")),
            transaction(current, a, raw_decision="ALLOW_INITIAL", source_identity="sid:other"),
        )
        for t in cases:
            with self.subTest(transaction=t):
                r = m.bind_alias_stable_hydration_transaction(
                    transaction=t,
                    previous=None,
                    current=current,
                    previous_view=None,
                    current_view=a,
                )
                self.assertEqual(
                    r.disposition,
                    m.Nav15Disposition.HOLD_OBSERVATION_BINDING_MISMATCH,
                )

    def test_raw_parent_decision_must_match_transaction(self):
        a = view()
        current = obs(a)
        t = transaction(current, a, raw_decision="ALLOW_STATE_TRANSITION")
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=None,
            current=current,
            previous_view=None,
            current_view=a,
        )
        self.assertEqual(r.disposition, m.Nav15Disposition.HOLD_RAW_DECISION_MISMATCH)

    def test_nonadmitted_parent_transaction_stays_hold(self):
        a = view()
        current = obs(a)
        t = transaction(current, a, raw_decision="ALLOW_INITIAL", admitted=False)
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=None,
            current=current,
            previous_view=None,
            current_view=a,
        )
        self.assertEqual(r.disposition, m.Nav15Disposition.HOLD_TRANSACTION_NOT_ADMITTED)

    def test_parent_generation_mismatch_holds(self):
        a = view()
        current = obs(a)
        t = transaction(current, a, raw_decision="ALLOW_INITIAL", parent_head="f" * 40)
        r = m.bind_alias_stable_hydration_transaction(
            transaction=t,
            previous=None,
            current=current,
            previous_view=None,
            current_view=a,
        )
        self.assertEqual(r.disposition, m.Nav15Disposition.HOLD_PARENT_GENERATION)

    def test_parent_transaction_digest_is_recomputed(self):
        a = view()
        current = obs(a)
        t = transaction(current, a, raw_decision="ALLOW_INITIAL")
        with self.assertRaisesRegex(ValueError, "TRANSACTION_DIGEST_MISMATCH"):
            m.bind_alias_stable_hydration_transaction(
                transaction=replace(t, transaction_digest=d("forged")),
                previous=None,
                current=current,
                previous_view=None,
                current_view=a,
            )

    def test_transaction_claim_ceiling_widening_fails_closed(self):
        a = view()
        current = obs(a)
        t = transaction(current, a, raw_decision="ALLOW_INITIAL")
        with self.assertRaisesRegex(ValueError, "TRANSACTION_EXCEEDED_NONPROMOTION_CEILING"):
            m.bind_alias_stable_hydration_transaction(
                transaction=replace(t, evidence_admitted=True),
                previous=None,
                current=current,
                previous_view=None,
                current_view=a,
            )

    def test_deterministic_receipt(self):
        a = view()
        current = obs(a)
        t = transaction(current, a, raw_decision="ALLOW_INITIAL")
        kwargs = dict(
            transaction=t,
            previous=None,
            current=current,
            previous_view=None,
            current_view=a,
        )
        self.assertEqual(
            m.bind_alias_stable_hydration_transaction(**kwargs),
            m.bind_alias_stable_hydration_transaction(**kwargs),
        )

    def test_complete_different_j_matrix(self):
        self.assertEqual(m.prove_different_j(), 192)


if __name__ == "__main__":
    unittest.main()
