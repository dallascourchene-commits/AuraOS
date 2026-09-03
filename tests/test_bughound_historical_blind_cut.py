import json
import random
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from tools.bughound.historical_blind_cut import (
    HistoricalBlindError,
    HistoricalCaseV1,
    SplitMemberV1,
    TimedEvidenceV1,
    MODE_HISTORICAL_BLIND,
    MODE_POST_DISCLOSURE,
    MODE_HOLD,
    compile_historical_cut,
    historical_blind_eligible,
    hyper1000,
    validate_group_disjoint_split,
    validate_solver_packet,
)

SALT = "historical-evaluator-salt-20260903"


def real_case():
    return HistoricalCaseV1(
        corpus_id="VULNGYM_V0_1_4",
        case_id="entry-00057",
        repo_url="https://github.com/open-webui/open-webui",
        vulnerable_commit="9942de8011d4b5a141ac507c974c061c0cdad59a",
        source_commit_at="2025-10-21T21:03:04Z",
        source_tree_digest="tree-openwebui-9942de8",
        source_generation="VULNGYM_SOURCE_V0_1_4",
        advisory_published_at="2025-11-07T15:25:23Z",
        evaluator_generation="VULNGYM_EVAL_V0_1_4",
        evidence=(
            TimedEvidenceV1(
                "SOURCE_TREE",
                "github:open-webui@9942de8",
                "2025-10-21T21:03:04Z",
                "src-tree-digest",
                "github-v1",
                "sem-src",
            ),
            TimedEvidenceV1(
                "ADVISORY",
                "GHSA-W7XJ-8FX7-WFCH",
                "2025-11-07T15:25:23Z",
                "advisory-digest",
                "ghsa-v1",
                "sem-advisory",
                evaluator_only=True,
            ),
            TimedEvidenceV1(
                "TRACE_GOLD",
                "vulngym:entry-00057",
                "2026-06-26T09:20:57Z",
                "trace-digest",
                "vulngym-0.1.4",
                "sem-trace",
                evaluator_only=True,
            ),
        ),
        advisory_id="GHSA-W7XJ-8FX7-WFCH",
        cve_ids=("CVE-2025-64495",),
        vuln_title="Stored DOM XSS via Prompt Insertion Rich Text Feature",
        vuln_category="XSS / Stored XSS",
        entry_point_gold="src/lib/components/chat/MessageInput/CommandSuggestionList.svelte:97",
        critical_operation_gold="src/lib/components/common/RichTextInput.svelte:348",
        trace_gold=("entry", "propagation", "critical-operation"),
        fix_commit="eb9c4c0e00000000000000000000000000000000",
        patch_digest="patch-gold",
        poc_digest="poc-sealed",
        oracle_digest="oracle-sealed",
    )


class HistoricalCutTests(unittest.TestCase):
    def test_real_vulngym_example_is_historical_blind_before_disclosure(self):
        p, s = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        self.assertEqual(MODE_HISTORICAL_BLIND, p.mode)
        self.assertTrue(historical_blind_eligible(p))
        self.assertIn("advisory_id", s.sealed_classes)

    def test_same_case_is_post_disclosure_after_publication(self):
        p, _ = compile_historical_cut(
            real_case(), as_of="2025-11-08T00:00:00Z", evaluator_salt=SALT
        )
        self.assertEqual(MODE_POST_DISCLOSURE, p.mode)
        self.assertFalse(historical_blind_eligible(p))

    def test_equal_publication_time_is_not_blind(self):
        p, _ = compile_historical_cut(
            real_case(), as_of="2025-11-07T15:25:23Z", evaluator_salt=SALT
        )
        self.assertEqual(MODE_POST_DISCLOSURE, p.mode)

    def test_unknown_publication_holds(self):
        p, _ = compile_historical_cut(
            replace(real_case(), advisory_published_at=None),
            as_of="2025-11-01T00:00:00Z",
            evaluator_salt=SALT,
        )
        self.assertEqual(MODE_HOLD, p.mode)

    def test_source_after_cut_fails(self):
        with self.assertRaises(HistoricalBlindError) as ctx:
            compile_historical_cut(
                real_case(), as_of="2025-10-01T00:00:00Z", evaluator_salt=SALT
            )
        self.assertEqual("SOURCE_NOT_YET_AVAILABLE_AT_CUT", ctx.exception.code)

    def test_solver_packet_contains_no_gold_fields_or_ids(self):
        p, _ = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        validate_solver_packet(p)
        body = json.dumps(p.to_solver_dict(), sort_keys=True)
        for forbidden in (
            "GHSA-",
            "CVE-",
            "entry_point_gold",
            "critical_operation_gold",
            "trace_gold",
            "poc",
            "oracle",
            "patch_digest",
        ):
            self.assertNotIn(forbidden, body)

    def test_evaluator_seal_retains_gold_without_exposing_payload(self):
        _, s = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        self.assertIn("critical_operation_gold", s.sealed_classes)
        self.assertNotIn("RichTextInput", json.dumps(s.__dict__, sort_keys=True))

    def test_evaluator_only_evidence_never_visible_even_after_cut(self):
        p, _ = compile_historical_cut(
            real_case(), as_of="2026-08-01T00:00:00Z", evaluator_salt=SALT
        )
        self.assertEqual(
            ("SOURCE_TREE", "github:open-webui@9942de8", "src-tree-digest"),
            p.visible_evidence[0],
        )
        self.assertEqual(1, len(p.visible_evidence))

    def test_future_public_nongold_evidence_not_visible(self):
        c = real_case()
        future = TimedEvidenceV1(
            "BUILD_METADATA",
            "public:build",
            "2025-11-03T00:00:00Z",
            "build-d",
            "build-v1",
            "sem-build",
        )
        p, _ = compile_historical_cut(
            replace(c, evidence=c.evidence + (future,)),
            as_of="2025-11-01T00:00:00Z",
            evaluator_salt=SALT,
        )
        self.assertEqual(1, len(p.visible_evidence))

    def test_past_public_nongold_evidence_visible(self):
        c = real_case()
        past = TimedEvidenceV1(
            "BUILD_METADATA",
            "public:build",
            "2025-10-25T00:00:00Z",
            "build-d",
            "build-v1",
            "sem-build",
        )
        p, _ = compile_historical_cut(
            replace(c, evidence=c.evidence + (past,)),
            as_of="2025-11-01T00:00:00Z",
            evaluator_salt=SALT,
        )
        self.assertEqual(2, len(p.visible_evidence))

    def test_later_recording_cannot_retroactively_change_old_cut(self):
        c = real_case()
        p1, _ = compile_historical_cut(
            c, as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        later = TimedEvidenceV1(
            "PUBLIC_DISCUSSION",
            "public:later",
            "2026-01-01T00:00:00Z",
            "later-d",
            "pub-v1",
            "sem-pub",
        )
        p2, _ = compile_historical_cut(
            replace(c, evidence=c.evidence + (later,)),
            as_of="2025-11-01T00:00:00Z",
            evaluator_salt=SALT,
        )
        self.assertEqual(p1.visible_evidence, p2.visible_evidence)

    def test_cut_is_part_of_target_identity(self):
        p1, _ = compile_historical_cut(
            real_case(), as_of="2025-10-30T00:00:00Z", evaluator_salt=SALT
        )
        p2, _ = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        self.assertNotEqual(p1.target_id, p2.target_id)

    def test_same_cut_is_deterministic(self):
        p1, s1 = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        p2, s2 = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        self.assertEqual(p1.packet_digest, p2.packet_digest)
        self.assertEqual(s1.seal_digest, s2.seal_digest)

    def test_source_generation_changes_target_identity(self):
        p1, _ = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        p2, _ = compile_historical_cut(
            replace(real_case(), source_generation="VULNGYM_SOURCE_V0_1_5"),
            as_of="2025-11-01T00:00:00Z",
            evaluator_salt=SALT,
        )
        self.assertNotEqual(p1.target_id, p2.target_id)

    def test_group_key_same_for_same_repo(self):
        p1, _ = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        c2 = replace(real_case(), case_id="entry-other", vulnerable_commit="0" * 40)
        p2, _ = compile_historical_cut(
            c2, as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        self.assertEqual(p1.group_key, p2.group_key)

    def test_repo_group_cannot_cross_train_and_test(self):
        p, _ = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        members = [
            SplitMemberV1("train-x", p.repo_url, p.group_key, "TRAIN"),
            SplitMemberV1(p.target_id, p.repo_url, p.group_key, "TEST"),
        ]
        with self.assertRaises(HistoricalBlindError) as ctx:
            validate_group_disjoint_split(members)
        self.assertEqual("REPO_GROUP_CROSS_PARTITION", ctx.exception.code)

    def test_different_repo_groups_may_train_test(self):
        p, _ = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        validate_group_disjoint_split(
            [
                SplitMemberV1(
                    "train-x",
                    "https://github.com/example/other",
                    "other-group",
                    "TRAIN",
                ),
                SplitMemberV1(p.target_id, p.repo_url, p.group_key, "TEST"),
            ]
        )

    def test_target_cannot_cross_partitions(self):
        with self.assertRaises(HistoricalBlindError) as ctx:
            validate_group_disjoint_split(
                [
                    SplitMemberV1("t", "r1", "g1", "TRAIN"),
                    SplitMemberV1("t", "r2", "g2", "TEST"),
                ]
            )
        self.assertEqual("TARGET_CROSS_PARTITION", ctx.exception.code)

    def test_no_packet_mints_authority(self):
        p, _ = compile_historical_cut(
            real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt=SALT
        )
        self.assertFalse(p.authority)
        self.assertFalse(p.external_effect)

    def test_authority_in_case_fails(self):
        with self.assertRaises(HistoricalBlindError):
            compile_historical_cut(
                replace(real_case(), authority=True),
                as_of="2025-11-01T00:00:00Z",
                evaluator_salt=SALT,
            )

    def test_authority_in_evidence_fails(self):
        c = real_case()
        bad = replace(c.evidence[0], authority=True)
        with self.assertRaises(HistoricalBlindError):
            compile_historical_cut(
                replace(c, evidence=(bad,) + c.evidence[1:]),
                as_of="2025-11-01T00:00:00Z",
                evaluator_salt=SALT,
            )

    def test_hyper1000_exact(self):
        cells = hyper1000()
        self.assertEqual(1000, len(cells))
        self.assertEqual(1000, len(set(cells)))

    def test_short_salt_fails(self):
        with self.assertRaises(HistoricalBlindError):
            compile_historical_cut(
                real_case(), as_of="2025-11-01T00:00:00Z", evaluator_salt="short"
            )

    def test_bad_commit_fails(self):
        with self.assertRaises(HistoricalBlindError):
            compile_historical_cut(
                replace(real_case(), vulnerable_commit="abc"),
                as_of="2025-11-01T00:00:00Z",
                evaluator_salt=SALT,
            )

    def test_randomized_bitemporal_reference_equivalence(self):
        rng = random.Random(20260903)
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        for i in range(100_000):
            source_delta = rng.randint(0, 1000)
            advisory_delta = rng.choice([None, rng.randint(0, 1000)])
            cut_delta = rng.randint(0, 1000)
            source = base + timedelta(hours=source_delta)
            cut = base + timedelta(hours=cut_delta)
            advisory = (
                None
                if advisory_delta is None
                else base + timedelta(hours=advisory_delta)
            )
            c = replace(
                real_case(),
                source_commit_at=source.isoformat(),
                advisory_published_at=(
                    None if advisory is None else advisory.isoformat()
                ),
                vulnerable_commit=f"{i % 16:x}" * 40,
            )
            if source > cut:
                with self.assertRaises(HistoricalBlindError) as ctx:
                    compile_historical_cut(c, as_of=cut.isoformat(), evaluator_salt=SALT)
                self.assertEqual(
                    "SOURCE_NOT_YET_AVAILABLE_AT_CUT", ctx.exception.code
                )
                continue
            p, _ = compile_historical_cut(c, as_of=cut.isoformat(), evaluator_salt=SALT)
            expected = (
                MODE_HOLD
                if advisory is None
                else (
                    MODE_HISTORICAL_BLIND
                    if cut < advisory
                    else MODE_POST_DISCLOSURE
                )
            )
            self.assertEqual(expected, p.mode)


if __name__ == "__main__":
    unittest.main()
