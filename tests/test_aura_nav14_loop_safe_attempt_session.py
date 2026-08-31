from __future__ import annotations

from dataclasses import replace
import unittest

import tools.aura_nav14_loop_safe_attempt_session as m


class Nav14LoopSafeAttemptSessionTests(unittest.TestCase):
    def test_clean_exact_session_is_candidate_only(self) -> None:
        h, l, g, i = m._fixture()
        r = m.bind_loop_safe_attempt_session(handoff=h, ledger=l, guard=g, intent=i)
        self.assertEqual(r.disposition, m.AttemptDisposition.ATTEMPT_SESSION_CANDIDATE)
        self.assertTrue(r.attempt_session_candidate)
        self.assertTrue(r.candidate_only)
        self.assertFalse(r.ledger_producer_authenticated)
        self.assertFalse(r.ledger_persistence_proven)
        self.assertFalse(r.currentness_resolved)
        self.assertFalse(r.evidence_admitted)
        self.assertFalse(r.tool_execution_authorized)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.semantic_k27_authority)
        self.assertFalse(r.native_private_transformer_kv_accessed)

    def test_parent_generation_forgery_holds(self) -> None:
        h, l, g, i = m._fixture()
        for forged_h, forged_g in (
            (replace(h, parent_head="0" * 40), g),
            (h, replace(g, parent_head="0" * 40)),
        ):
            r = m.bind_loop_safe_attempt_session(
                handoff=forged_h, ledger=l, guard=forged_g, intent=i
            )
            self.assertEqual(r.disposition, m.AttemptDisposition.HOLD_PARENT_GENERATION)

    def test_candidate_identity_must_commute(self) -> None:
        h, l, g, i = m._fixture()
        for forged_l, forged_i in (
            (replace(l, candidate_digest="5" * 64), i),
            (l, replace(i, candidate_digest="6" * 64)),
        ):
            r = m.bind_loop_safe_attempt_session(
                handoff=h, ledger=forged_l, guard=g, intent=forged_i
            )
            self.assertEqual(
                r.disposition, m.AttemptDisposition.HOLD_CANDIDATE_BINDING_MISMATCH
            )

    def test_session_identity_must_commute(self) -> None:
        h, l, g, i = m._fixture()
        for forged_l, forged_g, forged_i in (
            (replace(l, session_id="session-x"), g, i),
            (l, replace(g, objective_id="session-x"), i),
            (l, g, replace(i, session_id="session-x")),
        ):
            r = m.bind_loop_safe_attempt_session(
                handoff=h, ledger=forged_l, guard=forged_g, intent=forged_i
            )
            self.assertEqual(
                r.disposition, m.AttemptDisposition.HOLD_SESSION_BINDING_MISMATCH
            )

    def test_terminal_or_no_progress_ledger_debt_requires_reopen(self) -> None:
        h, l, g, i = m._fixture()
        for forged in (
            replace(l, prior_terminalized=True),
            replace(l, prior_no_progress_debt=1),
            replace(l, durable_identity_bound=False),
        ):
            r = m.bind_loop_safe_attempt_session(
                handoff=h, ledger=forged, guard=g, intent=i
            )
            self.assertEqual(
                r.disposition, m.AttemptDisposition.HOLD_ATTEMPT_LEDGER_REOPEN_REQUIRED
            )

    def test_every_loop_guard_debt_taints_session(self) -> None:
        h, l, g, i = m._fixture()
        variants = (
            replace(g, incident_count=1),
            replace(g, mutation_stop=True),
            replace(g, frozen_primitives=("write",)),
            replace(g, blocked_write_keys=(("update", "resource"),)),
        )
        for forged in variants:
            r = m.bind_loop_safe_attempt_session(
                handoff=h, ledger=l, guard=forged, intent=i
            )
            self.assertEqual(r.disposition, m.AttemptDisposition.HOLD_LOOP_GUARD_TAINTED)

    def test_handoff_readiness_and_ceiling_fail_closed(self) -> None:
        h, l, g, i = m._fixture()
        not_ready = replace(h, disposition="HOLD_RETRIEVAL_CONE_COLLAPSED")
        r = m.bind_loop_safe_attempt_session(
            handoff=not_ready, ledger=l, guard=g, intent=i
        )
        self.assertEqual(r.disposition, m.AttemptDisposition.HOLD_HANDOFF_NOT_READY)
        for forged in (
            replace(h, candidate_only=False),
            replace(h, persistent_write_authorized=True),
            replace(h, evidence_admitted=True),
            replace(h, source_truth_proven=True),
            replace(h, read_currentness_proven=True),
            replace(h, effect_authorized=True),
            replace(h, semantic_k27_authority=True),
            replace(h, native_private_transformer_kv_accessed=True),
        ):
            r = m.bind_loop_safe_attempt_session(
                handoff=forged, ledger=l, guard=g, intent=i
            )
            self.assertEqual(r.disposition, m.AttemptDisposition.HOLD_CLAIM_CEILING)
        for forged_guard in (
            replace(g, effect_authority=True),
            replace(g, semantic_authority=True),
            replace(g, provider_authority=True),
            replace(g, native_private_transformer_kv=True),
        ):
            with self.assertRaises(ValueError):
                m.bind_loop_safe_attempt_session(
                    handoff=h, ledger=l, guard=forged_guard, intent=i
                )

    def test_ledger_cannot_self_mint_authentication_or_persistence(self) -> None:
        h, l, g, i = m._fixture()
        with self.assertRaises(ValueError):
            m.bind_loop_safe_attempt_session(
                handoff=h,
                ledger=replace(l, producer_authenticated_by_this_contract=True),
                guard=g,
                intent=i,
            )
        r = m.bind_loop_safe_attempt_session(handoff=h, ledger=l, guard=g, intent=i)
        self.assertFalse(r.ledger_producer_authenticated)
        self.assertFalse(r.ledger_persistence_proven)

    def test_projection_shape_types_fail_closed(self) -> None:
        h, l, g, i = m._fixture()
        for bad_ledger in (
            replace(l, prior_terminalized=1),
            replace(l, durable_identity_bound=1),
        ):
            with self.assertRaises(ValueError):
                m.bind_loop_safe_attempt_session(
                    handoff=h, ledger=bad_ledger, guard=g, intent=i
                )
        with self.assertRaises(ValueError):
            m.bind_loop_safe_attempt_session(
                handoff=h, ledger=l, guard=replace(g, mutation_stop=1), intent=i
            )
        with self.assertRaises(ValueError):
            m.bind_loop_safe_attempt_session(
                handoff=replace(h, candidate_only=1), ledger=l, guard=g, intent=i
            )

    def test_hold_receipt_suppresses_candidate_and_session_identity(self) -> None:
        h, l, g, i = m._fixture()
        r = m.bind_loop_safe_attempt_session(
            handoff=h, ledger=replace(l, prior_no_progress_debt=1), guard=g, intent=i
        )
        self.assertIsNone(r.candidate_digest)
        self.assertIsNone(r.session_id)
        self.assertIsNone(r.ledger_generation)
        self.assertIsNone(r.attempt_ordinal)
        self.assertIsNone(r.operation_fingerprint_digest)
        self.assertFalse(r.attempt_session_candidate)

    def test_receipt_is_deterministic(self) -> None:
        h, l, g, i = m._fixture()
        a = m.bind_loop_safe_attempt_session(handoff=h, ledger=l, guard=g, intent=i)
        b = m.bind_loop_safe_attempt_session(handoff=h, ledger=l, guard=g, intent=i)
        self.assertEqual(a, b)
        self.assertEqual(len(a.attempt_receipt_digest), 64)

    def test_complete_64_state_different_j_lattice(self) -> None:
        self.assertEqual(m.prove_different_j(), 64)

    def test_parent_coordinates_are_exact(self) -> None:
        self.assertEqual(m.NAV14_HEAD, "6cdd1be40428250bffba20e924f664c7be585469")
        self.assertEqual(m.NAV14_RUN, 33437542974)
        self.assertEqual(m.NAV14_JOB, 99637538062)
        self.assertEqual(m.LOOP_HEAD, "6406e2f302335f940a7e780d818966a539c88845")
        self.assertEqual(m.LOOP_RUN, 33437846633)
        self.assertEqual(m.LOOP_JOB, 99638534069)


if __name__ == "__main__":
    unittest.main()
