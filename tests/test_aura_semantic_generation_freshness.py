from dataclasses import replace
import unittest

from tools import aura_semantic_generation_freshness as g


class SemanticGenerationFreshnessTests(unittest.TestCase):
    def test_cross_plane_false_freshness_is_rejected(self):
        receipt = g.admit_generation_aware_successor(
            candidates=g.cross_plane_false_freshness_fixture(),
            cut=g.A4_CUT,
            current_agent_id="GPT56SOL_A5",
        )
        self.assertFalse(receipt.successor_admissible)
        self.assertEqual(
            [c.disposition for c in receipt.classifications],
            ["PRE_CUT_SEMANTIC_GENERATION", "PRE_CUT_SEMANTIC_GENERATION"],
        )

    def test_post_cut_semantic_generation_delegates_to_a3(self):
        a = g.build_demo_candidate(
            artifact_id="fresh:a", semantic_generated_at="2026-08-31T09:02:00Z",
            artifact_observed_at="2026-08-31T09:03:00Z", source_generation_id="src:a",
            derivation_kind="SEMANTIC_SOURCE", semantic_type="NEW_A",
            terminal_at="2026-08-31T09:04:00Z",
        )
        b = g.build_demo_candidate(
            artifact_id="fresh:b", semantic_generated_at="2026-08-31T09:02:01Z",
            artifact_observed_at="2026-08-31T09:03:01Z", source_generation_id="src:b",
            derivation_kind="SEMANTIC_SOURCE", semantic_type="NEW_B",
            terminal_at="2026-08-31T09:04:01Z",
        )
        receipt = g.admit_generation_aware_successor(
            candidates=(a, b), cut=g.A4_CUT, current_agent_id="GPT56SOL_A5"
        )
        self.assertTrue(receipt.successor_admissible)
        self.assertEqual(set(receipt.selected_artifact_ids), {"fresh:a", "fresh:b"})
        self.assertTrue(all(c.disposition == "SEMANTIC_SIBLING" for c in receipt.classifications))

    def test_new_replica_of_old_unseen_sck_still_fails(self):
        candidate = g.build_demo_candidate(
            artifact_id="replica:unseen", semantic_generated_at="2026-08-01T00:00:00Z",
            artifact_observed_at="2026-08-31T12:00:00Z", source_generation_id="old:unseen",
            derivation_kind="NEW_COORDINATE_REPLICA", semantic_type="UNSEEN_LOCALLY_OLD_SEMANTIC",
            terminal_at="2026-08-31T12:00:01Z",
        )
        receipt = g.admit_generation_aware_successor(
            candidates=(candidate,), cut=g.A4_CUT, current_agent_id="GPT56SOL_A5",
            committed_scks=set(),
        )
        self.assertEqual(receipt.classifications[0].disposition, "PRE_CUT_SEMANTIC_GENERATION")
        self.assertFalse(receipt.successor_admissible)

    def test_post_cut_observation_is_not_enough(self):
        candidate = g.cross_plane_false_freshness_fixture()[1]
        self.assertGreater(g._parse_utc(candidate.artifact_observed_at), g._parse_utc(g.A4_CUT))
        self.assertLessEqual(g._parse_utc(candidate.semantic_generated_at), g._parse_utc(g.A4_CUT))

    def test_semantic_generation_after_observation_fails_closed(self):
        candidate = g.build_demo_candidate(
            artifact_id="bad:time", semantic_generated_at="2026-08-31T09:05:00Z",
            artifact_observed_at="2026-08-31T09:04:00Z", source_generation_id="src:bad",
            derivation_kind="SEMANTIC_SOURCE", semantic_type="BAD_TIME",
            terminal_at="2026-08-31T09:06:00Z",
        )
        with self.assertRaisesRegex(ValueError, "SEMANTIC_GENERATION_AFTER_OBSERVATION"):
            g.admit_generation_aware_successor(
                candidates=(candidate,), cut=g.A4_CUT, current_agent_id="GPT56SOL_A5"
            )

    def test_observation_after_terminal_fails_closed(self):
        candidate = g.build_demo_candidate(
            artifact_id="bad:terminal", semantic_generated_at="2026-08-31T09:02:00Z",
            artifact_observed_at="2026-08-31T09:05:00Z", source_generation_id="src:bad-terminal",
            derivation_kind="SEMANTIC_SOURCE", semantic_type="BAD_TERMINAL_TIME",
            terminal_at="2026-08-31T09:04:00Z",
        )
        with self.assertRaisesRegex(ValueError, "OBSERVATION_AFTER_TERMINAL"):
            g.admit_generation_aware_successor(
                candidates=(candidate,), cut=g.A4_CUT, current_agent_id="GPT56SOL_A5"
            )

    def test_self_artifact_is_rejected_even_if_generation_fresh(self):
        candidate = g.build_demo_candidate(
            artifact_id="self:fresh", semantic_generated_at="2026-08-31T09:02:00Z",
            artifact_observed_at="2026-08-31T09:03:00Z", source_generation_id="src:self",
            derivation_kind="SEMANTIC_SOURCE", semantic_type="SELF_FRESH",
            terminal_at="2026-08-31T09:04:00Z", agent_id="GPT56SOL_A5",
        )
        receipt = g.admit_generation_aware_successor(
            candidates=(candidate,), cut=g.A4_CUT, current_agent_id="GPT56SOL_A5"
        )
        self.assertEqual(receipt.classifications[0].disposition, "SELF_ARTIFACT")

    def test_nonterminal_is_rejected_before_freshness_credit(self):
        candidate = g.build_demo_candidate(
            artifact_id="nonterminal", semantic_generated_at="2026-08-31T09:02:00Z",
            artifact_observed_at="2026-08-31T09:03:00Z", source_generation_id="src:nonterminal",
            derivation_kind="SEMANTIC_SOURCE", semantic_type="NONTERMINAL",
            terminal_at="2026-08-31T09:04:00Z",
        )
        candidate = replace(candidate, sibling=replace(candidate.sibling, terminal_green=False))
        receipt = g.admit_generation_aware_successor(
            candidates=(candidate,), cut=g.A4_CUT, current_agent_id="GPT56SOL_A5"
        )
        self.assertEqual(receipt.classifications[0].disposition, "NOT_TERMINAL_GREEN")

    def test_permutation_is_deterministic(self):
        pair = g.cross_plane_false_freshness_fixture()
        a = g.admit_generation_aware_successor(candidates=pair, cut=g.A4_CUT, current_agent_id="X")
        b = g.admit_generation_aware_successor(candidates=tuple(reversed(pair)), cut=g.A4_CUT, current_agent_id="X")
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_claim_ceiling(self):
        r = g.admit_generation_aware_successor(
            candidates=g.cross_plane_false_freshness_fixture(), cut=g.A4_CUT, current_agent_id="X"
        )
        self.assertFalse(r.artifact_time_counts_as_semantic_generation)
        self.assertFalse(r.head_advance_counts_as_semantic_generation)
        self.assertFalse(r.replica_creation_counts_as_semantic_generation)
        self.assertFalse(r.coordinate_growth_counts_as_semantic_generation)
        self.assertFalse(r.semantic_truth_minted)
        self.assertFalse(r.effect_authority_granted)
        self.assertFalse(r.native_private_transformer_kv_accessed)
        self.assertFalse(r.gate10_promoted)
        self.assertFalse(r.merge_or_deployment_authorized)


if __name__ == "__main__":
    unittest.main()
