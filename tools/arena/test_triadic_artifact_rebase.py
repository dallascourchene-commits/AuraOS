import unittest

from triadic_artifact_rebase import (
    ArtifactAnchor,
    TriadicRebaseError,
    compile_triadic_rebase,
    select_two_sibling_anchors,
)


def anchor(
    ref,
    agent,
    role,
    *,
    currentness="CURRENT",
    superseded=False,
    relevance=5,
    evidence="SOURCE_EVIDENCE",
):
    return ArtifactAnchor(
        artifact_ref=ref,
        agent_id=agent,
        role=role,
        evidence_class=evidence,
        currentness=currentness,
        content_digest=("a" if agent == "A" else "b" if agent == "B" else "c") * 64,
        evidence_ref=f"receipt:{ref}",
        dependency_relevance=relevance,
        superseded=superseded,
    )


def compile_ok(**overrides):
    params = dict(
        mission_ref="mission:arena",
        purpose_ref="purpose:reuse",
        currentness_basis="head:123",
        synthesizing_agent_id="SYNTH",
        anchors=(
            anchor("drive:A", "A", "construct"),
            anchor("drive:B", "B", "challenge"),
        ),
        agreements=("both demand source/currentness binding",),
        tensions=("dynamic objective generation must not become runaway recursion",),
        unknowns=("live host wake remains unproven",),
        derived_objective="implement the smallest fail-closed triadic packet validator",
        why_material="turns sibling synthesis into reusable Arena coordination",
        dependencies=("U5", "H-E"),
        required_capabilities=("python", "review"),
        inherited_effect_ceiling="D0",
        required_effect_ceiling="D0",
        cost_ceiling=0.0,
        expected_output="module + tests + receipt",
        acceptance=("all TAR vectors pass",),
        reopen_conditions=("anchor currentness changes",),
    )
    params.update(overrides)
    return compile_triadic_rebase(**params)


class TriadicArtifactRebaseTests(unittest.TestCase):
    # TAR-01
    def test_self_authored_anchor_rejected(self):
        with self.assertRaisesRegex(TriadicRebaseError, "TRIAD_SELF_AUTHORED"):
            compile_ok(
                anchors=(
                    anchor("x", "SYNTH", "construct"),
                    anchor("y", "B", "verify"),
                )
            )

    # TAR-02
    def test_superseded_anchor_requires_explicit_provisional(self):
        stale = anchor("x", "A", "construct", currentness="STALE", superseded=True)
        with self.assertRaisesRegex(TriadicRebaseError, "TRIAD_ANCHOR_REBASE_REQUIRED"):
            compile_ok(anchors=(stale, anchor("y", "B", "verify")))
        packet = compile_ok(
            anchors=(stale, anchor("y", "B", "verify")),
            allow_provisional=True,
        )
        self.assertEqual(packet.disposition, "PROVISIONAL_REBASE_REQUIRED")

    # TAR-03
    def test_distinct_agents_preferred_and_same_agent_requires_exception(self):
        with self.assertRaisesRegex(TriadicRebaseError, "TRIAD_DISTINCT_AGENT"):
            compile_ok(
                anchors=(
                    anchor("x", "A", "construct"),
                    anchor("y", "A", "verify"),
                )
            )
        packet = compile_ok(
            anchors=(
                anchor("x", "A", "construct"),
                anchor("y", "A", "verify"),
            ),
            same_agent_exception_ref="exception:no-distinct-current-candidate",
        )
        self.assertEqual(len(packet.anchors), 2)

    # TAR-04
    def test_dissent_tension_is_required_and_preserved(self):
        with self.assertRaisesRegex(TriadicRebaseError, "TENSION_REQUIRED"):
            compile_ok(tensions=())
        packet = compile_ok(tensions=("challenge remains unresolved",))
        self.assertIn("challenge remains unresolved", packet.tensions)

    # TAR-05
    def test_same_basis_has_stable_triad_identity(self):
        self.assertEqual(compile_ok().triad_id, compile_ok().triad_id)

    # TAR-06
    def test_observation_timestamp_does_not_churn_identity_or_packet_digest(self):
        a = compile_ok(observed_at="2026-08-30T10:00:00Z")
        b = compile_ok(observed_at="2026-08-30T10:00:30Z")
        self.assertEqual(a.triad_id, b.triad_id)
        self.assertEqual(a.packet_digest, b.packet_digest)

    # TAR-07
    def test_anchor_content_change_creates_new_lineage(self):
        a = compile_ok()
        changed = ArtifactAnchor(
            artifact_ref="drive:A",
            agent_id="A",
            role="construct",
            evidence_class="SOURCE_EVIDENCE",
            currentness="CURRENT",
            content_digest="d" * 64,
            evidence_ref="receipt:drive:A",
            dependency_relevance=5,
        )
        b = compile_ok(
            anchors=(changed, anchor("drive:B", "B", "challenge"))
        )
        self.assertNotEqual(a.triad_id, b.triad_id)

    # TAR-08
    def test_effect_authority_cannot_be_widened(self):
        with self.assertRaisesRegex(TriadicRebaseError, "CANNOT_WIDEN_EFFECT"):
            compile_ok(
                inherited_effect_ceiling="D0",
                required_effect_ceiling="D1",
            )

    # TAR-09
    def test_packet_never_claims_synthesis_runtime_or_effect_execution(self):
        packet = compile_ok()
        self.assertFalse(packet.synthesis_execution_proven)
        self.assertFalse(packet.runtime_execution_proven)
        self.assertFalse(packet.effect_authorized)

    # TAR-10
    def test_exactly_two_sibling_anchors_plus_synthesizer(self):
        with self.assertRaisesRegex(TriadicRebaseError, "EXACTLY_TWO"):
            compile_ok(anchors=(anchor("x", "A", "construct"),))
        packet = compile_ok()
        self.assertEqual(len(packet.anchors), 2)
        self.assertNotIn(
            packet.synthesizing_agent_id,
            {x.agent_id for x in packet.anchors},
        )

    def test_nomination_fails_when_two_current_siblings_do_not_exist(self):
        with self.assertRaisesRegex(TriadicRebaseError, "TRIAD_ANCHOR_INSUFFICIENT"):
            select_two_sibling_anchors(
                [
                    anchor("a", "SYNTH", "construct"),
                    anchor("b", "A", "challenge", currentness="STALE"),
                ],
                synthesizing_agent_id="SYNTH",
            )

    def test_nomination_prefers_distinct_agent_and_complementary_role(self):
        selected = select_two_sibling_anchors(
            [
                anchor("a1", "A", "construct", relevance=10),
                anchor("a2", "A", "construct", relevance=9),
                anchor(
                    "b1",
                    "B",
                    "challenge",
                    relevance=8,
                    evidence="ADVERSARIAL_ORACLE",
                ),
            ],
            synthesizing_agent_id="SYNTH",
        )
        self.assertEqual(selected[0].artifact_ref, "a1")
        self.assertEqual(selected[1].artifact_ref, "b1")

    def test_invalid_nonfinite_cost_fails_closed(self):
        with self.assertRaisesRegex(TriadicRebaseError, "COST_CEILING_INVALID"):
            compile_ok(cost_ceiling=float("nan"))


if __name__ == "__main__":
    unittest.main()
