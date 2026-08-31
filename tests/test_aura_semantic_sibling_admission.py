from __future__ import annotations

import unittest

from tools.aura_dual_key_evidence_generation import semantic_consequence_key
from tools.aura_semantic_sibling_admission import (
    OBJECTIVE_2_CUT,
    admit_successor,
    build_candidate,
    post_cut_pr648_pr649_fixture,
)


class SemanticSiblingAdmissionTests(unittest.TestCase):
    def _candidate(
        self,
        *,
        artifact_id: str,
        consequence: dict[str, object],
        terminal_at: str = "2026-08-31T09:00:00Z",
        agent_id: str = "OTHER",
        terminal_green: bool = True,
        source: str = "source@1",
        verifier: str = "verifier@1",
        currentness: str = "currentness@1",
        coordinate: str = "k27:1,2,3",
        run: int = 1,
    ):
        return build_candidate(
            artifact_id=artifact_id,
            agent_id=agent_id,
            terminal_at=terminal_at,
            exact_head=(artifact_id.replace(":", "") + "0" * 40)[:40],
            exact_run=run,
            terminal_green=terminal_green,
            semantic_consequence=consequence,
            source_generations=(source,),
            evidence_digests=(f"evidence:{source}",),
            verifier_generation=verifier,
            currentness_generation=currentness,
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
            coordinate_keys=(coordinate,),
            independence_keys=(f"proof:{artifact_id}",),
        )

    def test_exact_pr648_pr649_fixture_admits_successor(self) -> None:
        receipt = admit_successor(
            candidates=post_cut_pr648_pr649_fixture(),
            cut=OBJECTIVE_2_CUT,
            current_agent_id="GPT56SOL_A3",
        )
        self.assertTrue(receipt.successor_admissible)
        self.assertEqual(receipt.selected_artifact_ids, ("github:pr/648", "github:pr/649"))
        self.assertEqual(len(set(receipt.selected_scks)), 2)
        self.assertTrue(all(c.disposition == "SEMANTIC_SIBLING" for c in receipt.classifications))

    def test_evidence_refresh_is_support_merge_not_second_sibling(self) -> None:
        consequence = {"type": "X", "result": "HOLD"}
        first = self._candidate(artifact_id="a", consequence=consequence, source="source@1")
        refresh = self._candidate(
            artifact_id="b",
            consequence=consequence,
            terminal_at="2026-08-31T09:01:00Z",
            source="source@2",
            verifier="verifier@2",
            currentness="currentness@2",
            coordinate="k27:4,5,6",
            run=2,
        )
        receipt = admit_successor(
            candidates=(first, refresh), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertFalse(receipt.successor_admissible)
        self.assertEqual(
            tuple(c.disposition for c in receipt.classifications),
            ("SEMANTIC_SIBLING", "SUPPORT_MERGE"),
        )

    def test_process_duplicate_is_not_second_sibling(self) -> None:
        consequence = {"type": "X", "result": "HOLD"}
        first = self._candidate(artifact_id="a", consequence=consequence)
        duplicate = build_candidate(
            artifact_id="b",
            agent_id="OTHER2",
            terminal_at="2026-08-31T09:01:00Z",
            exact_head="b" * 40,
            exact_run=2,
            terminal_green=True,
            semantic_consequence=consequence,
            source_generations=("source@1",),
            evidence_digests=("evidence:source@1",),
            verifier_generation="verifier@1",
            currentness_generation="currentness@1",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
            coordinate_keys=("k27:1,2,3",),
            independence_keys=("proof:a",),
        )
        receipt = admit_successor(
            candidates=(first, duplicate), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertFalse(receipt.successor_admissible)
        self.assertEqual(receipt.classifications[1].disposition, "PROCESS_DUPLICATE")

    def test_stale_pre_cut_artifact_does_not_count(self) -> None:
        stale = self._candidate(
            artifact_id="stale",
            consequence={"type": "OLD", "result": "PASS"},
            terminal_at="2026-08-31T08:28:12Z",
        )
        fresh = self._candidate(
            artifact_id="fresh",
            consequence={"type": "NEW", "result": "PASS"},
        )
        receipt = admit_successor(
            candidates=(stale, fresh), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertFalse(receipt.successor_admissible)
        self.assertEqual(receipt.classifications[0].disposition, "STALE_PRE_CUT")

    def test_self_artifact_does_not_count(self) -> None:
        self_artifact = self._candidate(
            artifact_id="self", consequence={"type": "A", "result": "PASS"}, agent_id="SELF"
        )
        other = self._candidate(
            artifact_id="other", consequence={"type": "B", "result": "PASS"}, run=2
        )
        receipt = admit_successor(
            candidates=(self_artifact, other), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertFalse(receipt.successor_admissible)
        dispositions = {c.artifact_id: c.disposition for c in receipt.classifications}
        self.assertEqual(dispositions["self"], "SELF_ARTIFACT")

    def test_nonterminal_artifact_does_not_count(self) -> None:
        pending = self._candidate(
            artifact_id="pending",
            consequence={"type": "A", "result": "PASS"},
            terminal_green=False,
        )
        other = self._candidate(
            artifact_id="other", consequence={"type": "B", "result": "PASS"}, run=2
        )
        receipt = admit_successor(
            candidates=(pending, other), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertFalse(receipt.successor_admissible)
        self.assertEqual(receipt.classifications[0].disposition, "NOT_TERMINAL_GREEN")

    def test_semantic_state_change_can_be_second_sibling(self) -> None:
        hold = self._candidate(
            artifact_id="hold", consequence={"type": "X", "result": "HOLD"}
        )
        passed = self._candidate(
            artifact_id="pass",
            consequence={"type": "X", "result": "PASS"},
            terminal_at="2026-08-31T09:01:00Z",
            run=2,
        )
        self.assertNotEqual(hold.sck, passed.sck)
        receipt = admit_successor(
            candidates=(hold, passed), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertTrue(receipt.successor_admissible)

    def test_coordinate_growth_is_support_merge_not_semantic_growth(self) -> None:
        consequence = {"type": "X", "result": "HOLD"}
        first = self._candidate(
            artifact_id="a", consequence=consequence, coordinate="k27:1,2,3"
        )
        expanded = self._candidate(
            artifact_id="b",
            consequence=consequence,
            terminal_at="2026-08-31T09:01:00Z",
            coordinate="k27:4,5,6",
            run=2,
        )
        self.assertEqual(first.sck, expanded.sck)
        self.assertNotEqual(first.egk, expanded.egk)
        receipt = admit_successor(
            candidates=(first, expanded), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertEqual(receipt.classifications[1].disposition, "SUPPORT_MERGE")
        self.assertFalse(receipt.k27_coordinate_growth_counts_as_semantic_sibling)

    def test_preexisting_sck_with_fresh_egk_is_support_merge(self) -> None:
        candidate = self._candidate(
            artifact_id="refresh", consequence={"type": "X", "result": "HOLD"}
        )
        old_sck = semantic_consequence_key({"type": "X", "result": "HOLD"})
        receipt = admit_successor(
            candidates=(candidate,),
            cut=OBJECTIVE_2_CUT,
            current_agent_id="SELF",
            committed_scks={old_sck},
            evidence_by_sck={old_sck: set()},
        )
        self.assertEqual(receipt.classifications[0].disposition, "SUPPORT_MERGE")

    def test_input_order_does_not_change_selected_pair(self) -> None:
        pr648, pr649 = post_cut_pr648_pr649_fixture()
        forward = admit_successor(
            candidates=(pr648, pr649), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        reverse = admit_successor(
            candidates=(pr649, pr648), cut=OBJECTIVE_2_CUT, current_agent_id="SELF"
        )
        self.assertEqual(forward.selected_artifact_ids, reverse.selected_artifact_ids)
        self.assertEqual(forward.receipt_digest, reverse.receipt_digest)


if __name__ == "__main__":
    unittest.main()
