from __future__ import annotations

import unittest

from tools.aura_dual_key_evidence_generation import (
    GLM53_REVISION,
    ProcessIdentity,
    classify_commit,
    historical_glm53_fixture,
    make_evidence_generation,
    semantic_consequence_key,
)


class DualKeyEvidenceGenerationTests(unittest.TestCase):
    def test_sck_is_stable_across_evidence_refresh(self) -> None:
        consequence = {"type": "X", "scope": "same", "result": "HOLD"}
        sck = semantic_consequence_key(consequence)
        old = make_evidence_generation(
            sck=sck,
            source_generations=("source@1",),
            evidence_digests=("a" * 64,),
            verifier_generation="verifier@1",
            currentness_generation="currentness@1",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
        )
        new = make_evidence_generation(
            sck=sck,
            source_generations=("source@2",),
            evidence_digests=("b" * 64,),
            verifier_generation="verifier@2",
            currentness_generation="currentness@2",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
        )
        self.assertEqual(old.sck, new.sck)
        self.assertNotEqual(old.egk, new.egk)

    def test_independent_support_is_support_merge_not_new_semantic(self) -> None:
        sck = semantic_consequence_key({"type": "X", "result": "HOLD"})
        first = make_evidence_generation(
            sck=sck,
            source_generations=("source@1",),
            evidence_digests=("a" * 64,),
            verifier_generation="v1",
            currentness_generation="c1",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
        )
        second = make_evidence_generation(
            sck=sck,
            source_generations=("source@1", "source@2"),
            evidence_digests=("a" * 64, "b" * 64),
            verifier_generation="v2",
            currentness_generation="c1",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
            independence_keys=("agent-a", "agent-b"),
        )
        self.assertEqual(
            classify_commit(
                sck=sck,
                egk=second.egk,
                committed_scks={sck},
                evidence_by_sck={sck: {first.egk}},
            ),
            "SUPPORT_MERGE",
        )

    def test_process_retry_is_not_new_evidence(self) -> None:
        p1 = ProcessIdentity("o", "w", "t", "h", 1)
        p2 = ProcessIdentity("o", "w", "t", "h", 2)
        self.assertNotEqual(p1.rik, p2.rik)
        sck = semantic_consequence_key({"type": "X", "result": "HOLD"})
        evidence = make_evidence_generation(
            sck=sck,
            source_generations=("source@1",),
            evidence_digests=("a" * 64,),
            verifier_generation="v1",
            currentness_generation="c1",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
        )
        self.assertEqual(
            classify_commit(
                sck=sck,
                egk=evidence.egk,
                committed_scks={sck},
                evidence_by_sck={sck: {evidence.egk}},
            ),
            "PROCESS_DUPLICATE",
        )

    def test_coordinate_growth_does_not_change_sck(self) -> None:
        consequence = {"type": "X", "result": "HOLD"}
        sck = semantic_consequence_key(consequence)
        e1 = make_evidence_generation(
            sck=sck,
            source_generations=("source@1",),
            evidence_digests=("a" * 64,),
            verifier_generation="v1",
            currentness_generation="c1",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
            coordinate_keys=("k27:1,2,3",),
        )
        e2 = make_evidence_generation(
            sck=sck,
            source_generations=("source@1",),
            evidence_digests=("a" * 64,),
            verifier_generation="v1",
            currentness_generation="c1",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
            coordinate_keys=("k27:1,2,3", "k27:4,5,6"),
        )
        self.assertEqual(e1.sck, e2.sck)
        self.assertNotEqual(e1.egk, e2.egk)

    def test_changed_consequence_changes_sck(self) -> None:
        hold = semantic_consequence_key({"type": "X", "result": "HOLD"})
        passed = semantic_consequence_key({"type": "X", "result": "PASS"})
        self.assertNotEqual(hold, passed)

    def test_pr646_historical_evidence_is_one_egk_not_current_bytes(self) -> None:
        fixture = historical_glm53_fixture()
        self.assertEqual(fixture["consequence"]["model_revision"], GLM53_REVISION)
        sck = fixture["sck"]
        current = make_evidence_generation(
            sck=sck,
            source_generations=("future-current-consumer@1",),
            evidence_digests=("c" * 64,),
            verifier_generation="future-verifier@1",
            currentness_generation="CURRENT_CONSUMER_REMATERIALIZED",
            authority_scope="SOURCE_GEOMETRY_EVIDENCE_ONLY",
            effect_ceiling="NO_TENSOR_PAYLOAD_NO_GATE10",
        )
        self.assertEqual(current.sck, sck)
        self.assertNotEqual(current.egk, fixture["historical_egk"])

    def test_authority_change_changes_egk(self) -> None:
        sck = semantic_consequence_key({"type": "X", "result": "HOLD"})
        common = dict(
            sck=sck,
            source_generations=("source@1",),
            evidence_digests=("a" * 64,),
            verifier_generation="v1",
            currentness_generation="c1",
        )
        low = make_evidence_generation(
            **common, authority_scope="D0", effect_ceiling="NO_EFFECT"
        )
        other = make_evidence_generation(
            **common, authority_scope="D1", effect_ceiling="NO_EFFECT"
        )
        self.assertNotEqual(low.egk, other.egk)

    def test_order_does_not_change_generation_identity(self) -> None:
        sck = semantic_consequence_key({"type": "X", "result": "HOLD"})
        a = make_evidence_generation(
            sck=sck,
            source_generations=("s2", "s1"),
            evidence_digests=("b", "a"),
            verifier_generation="v",
            currentness_generation="c",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
            coordinate_keys=("z", "a"),
            independence_keys=("j2", "j1"),
        )
        b = make_evidence_generation(
            sck=sck,
            source_generations=("s1", "s2"),
            evidence_digests=("a", "b"),
            verifier_generation="v",
            currentness_generation="c",
            authority_scope="D0",
            effect_ceiling="NO_EFFECT",
            coordinate_keys=("a", "z"),
            independence_keys=("j1", "j2"),
        )
        self.assertEqual(a.egk, b.egk)


if __name__ == "__main__":
    unittest.main()
