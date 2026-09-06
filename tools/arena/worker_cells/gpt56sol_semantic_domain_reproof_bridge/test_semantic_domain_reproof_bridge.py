import unittest
from dataclasses import replace
from hashlib import sha256
import json

from semantic_domain_reproof_bridge import *


def D(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


R = lambda c: c * 64


def graph_fixture():
    return CanonicalGraph.build(
        [
            Node("NUMERIC_SOURCE", (), "V_NUM", ("numeric-domain",)),
            Node("WORKLOAD_COST", (), "V_COST", ("workload",)),
            Node("SECURITY_SOURCE", (), "V_SEC", ("security-source",)),
            Node("TRACE", (), "V_TRACE", ("trace",)),
            Node("COST_RECEIPT", ("WORKLOAD_COST", "NUMERIC_SOURCE"), "V_COST", ("cost",)),
            Node("SECURITY_RECEIPT", ("SECURITY_SOURCE",), "V_SEC", ("security",)),
            Node("EFFICIENCY_REUSE", ("COST_RECEIPT", "TRACE"), "V_EFF", ("efficiency",)),
            Node("FINAL_REUSE", ("EFFICIENCY_REUSE", "SECURITY_RECEIPT"), "V_FINAL", ("final",)),
        ]
    )


def surfaces(g):
    gens = tuple((v, f"g-{i}") for i, v in enumerate(sorted({n.verifier_id for n in g.nodes})))
    witness = tuple((n.node_id, D(("w", n.node_id))) for n in g.nodes)
    projections = tuple((n.node_id, D(("p", n.node_id))) for n in g.nodes)
    domains = tuple((n.node_id, D(("d", n.node_id))) for n in g.nodes)
    a = AdmissionSurface.mint_identity_surface(
        graph_root=g.graph_root,
        verifier_generations=gens,
        accepted_witness_roots=witness,
        proof_projection_roots=projections,
        semantic_domain_roots=domains,
        observation_generation="obs-1",
        external_receipt_root=R("a"),
    )
    o = CurrentOwnerSurface.mint_identity_surface(
        graph_root=g.graph_root,
        verifier_generations=gens,
        projection_roots=projections,
        semantic_domain_roots=domains,
        owner_replay_receipt_root=R("b"),
    )
    return a, o


def evidence_fixture(g, a, o):
    aw = dict(a.accepted_witness_roots)
    pp = dict(a.proof_projection_roots)
    sd = dict(a.semantic_domain_roots)
    vg = dict(a.verifier_generations)
    evidence = {}
    for node_id in g.topo_order:
        n = g.by_id[node_id]
        provisional = EvidenceWitness(
            node_id=node_id,
            graph_root=g.graph_root,
            witness_root=aw[node_id],
            output_root=D(("out", node_id)),
            verifier_generation=vg[n.verifier_id],
            dependency_input_root=R("0"),
            projection_root=pp[node_id],
            semantic_domain_root=sd[node_id],
        )
        evidence[node_id] = provisional
        evidence[node_id] = replace(
            provisional,
            dependency_input_root=dependency_input_root(g, node_id, evidence),
        )
    return evidence


def remint_owner(o, **updates):
    return CurrentOwnerSurface.mint_identity_surface(
        graph_root=updates.get("graph_root", o.graph_root),
        verifier_generations=updates.get("verifier_generations", o.verifier_generations),
        projection_roots=updates.get("projection_roots", o.projection_roots),
        semantic_domain_roots=updates.get("semantic_domain_roots", o.semantic_domain_roots),
        owner_replay_receipt_root=updates.get(
            "owner_replay_receipt_root", o.owner_replay_receipt_root
        ),
    )


class T(unittest.TestCase):
    def setUp(self):
        self.g = graph_fixture()
        self.a, self.o = surfaces(self.g)
        self.e = evidence_fixture(self.g, self.a, self.o)

    def test_canonical_presentation_order(self):
        g2 = CanonicalGraph.build(reversed(self.g.nodes))
        self.assertEqual(self.g.graph_root, g2.graph_root)
        self.assertEqual(self.g.topo_order, g2.topo_order)

    def test_clean_surface_reuses_everything(self):
        p = compile_reproof_plan(
            self.g,
            explicit_changed_roots=(),
            evidence=self.e,
            admission=self.a,
            current_owner=self.o,
        )
        self.assertEqual(p.recompute_order, ())
        self.assertEqual(p.rebind_nodes, ())
        self.assertEqual(set(p.reuse_nodes), set(self.g.by_id))
        self.assertTrue(all(state == EXACT for _, state in p.transition_classes))

    def test_generation_only_movement_is_explicit_rebind_not_reproof(self):
        vg = dict(self.o.verifier_generations)
        vg["V_COST"] = "g-new"
        o = remint_owner(self.o, verifier_generations=vg.items())
        p = compile_reproof_plan(
            self.g,
            explicit_changed_roots=(),
            evidence=self.e,
            admission=self.a,
            current_owner=o,
        )
        self.assertEqual(p.recompute_order, ())
        self.assertEqual(set(p.rebind_nodes), {"WORKLOAD_COST", "COST_RECEIPT"})
        self.assertIn("EFFICIENCY_REUSE", p.reuse_nodes)
        states = dict(p.transition_classes)
        self.assertEqual(states["WORKLOAD_COST"], REBIND)
        self.assertEqual(states["COST_RECEIPT"], REBIND)

    def test_rebind_still_binds_old_proof_generation(self):
        vg = dict(self.o.verifier_generations)
        vg["V_COST"] = "g-new"
        o = remint_owner(self.o, verifier_generations=vg.items())
        e = dict(self.e)
        e["WORKLOAD_COST"] = replace(e["WORKLOAD_COST"], verifier_generation="wrong-old")
        with self.assertRaisesRegex(ReproofContractError, "REBIND_PROOF_GENERATION_MISMATCH"):
            compile_reproof_plan(
                self.g,
                explicit_changed_roots=(),
                evidence=e,
                admission=self.a,
                current_owner=o,
            )

    def test_numeric_domain_drift_seeds_exact_descendant_cone(self):
        sd = dict(self.o.semantic_domain_roots)
        sd["NUMERIC_SOURCE"] = R("c")
        o = remint_owner(self.o, semantic_domain_roots=sd.items())
        p = compile_reproof_plan(
            self.g,
            explicit_changed_roots=(),
            evidence=self.e,
            admission=self.a,
            current_owner=o,
        )
        self.assertEqual(p.drift_seeds, ("NUMERIC_SOURCE",))
        self.assertEqual(
            set(p.recompute_order),
            {"NUMERIC_SOURCE", "COST_RECEIPT", "EFFICIENCY_REUSE", "FINAL_REUSE"},
        )
        self.assertIn("SECURITY_RECEIPT", p.reuse_nodes)

    def test_projection_drift_is_reproof(self):
        pp = dict(self.o.projection_roots)
        pp["COST_RECEIPT"] = R("d")
        o = remint_owner(self.o, projection_roots=pp.items())
        p = compile_reproof_plan(
            self.g,
            explicit_changed_roots=(),
            evidence=self.e,
            admission=self.a,
            current_owner=o,
        )
        self.assertEqual(
            set(p.recompute_order),
            {"COST_RECEIPT", "EFFICIENCY_REUSE", "FINAL_REUSE"},
        )
        self.assertEqual(dict(p.transition_classes)["COST_RECEIPT"], REPROVE)

    def test_generation_plus_domain_drift_is_reproof_not_rebind(self):
        vg = dict(self.o.verifier_generations)
        vg["V_COST"] = "g-new"
        sd = dict(self.o.semantic_domain_roots)
        sd["WORKLOAD_COST"] = R("e")
        o = remint_owner(
            self.o,
            verifier_generations=vg.items(),
            semantic_domain_roots=sd.items(),
        )
        p = compile_reproof_plan(
            self.g,
            explicit_changed_roots=(),
            evidence=self.e,
            admission=self.a,
            current_owner=o,
        )
        states = dict(p.transition_classes)
        self.assertEqual(states["WORKLOAD_COST"], REPROVE)
        self.assertEqual(states["COST_RECEIPT"], REBIND)
        self.assertIn("WORKLOAD_COST", p.recompute_order)
        self.assertIn("COST_RECEIPT", p.recompute_order)
        self.assertNotIn("COST_RECEIPT", p.rebind_nodes)

    def test_classifier_hold_on_malformed_unknown_surface(self):
        self.assertEqual(
            classify_owner_transition(
                proof_generation="g1",
                current_generation="g2",
                proof_projection_root=R("1"),
                current_projection_root="not-a-root",
                proof_semantic_domain_root=R("2"),
                current_semantic_domain_root=R("2"),
            ),
            HOLD,
        )

    def test_classifier_precedence_reprove_over_rebind(self):
        self.assertEqual(
            classify_owner_transition(
                proof_generation="g1",
                current_generation="g2",
                proof_projection_root=R("1"),
                current_projection_root=R("3"),
                proof_semantic_domain_root=R("2"),
                current_semantic_domain_root=R("2"),
            ),
            REPROVE,
        )

    def test_trace_change_reopens_only_reuse_lane(self):
        p = compile_reproof_plan(
            self.g,
            explicit_changed_roots=("TRACE",),
            evidence=self.e,
            admission=self.a,
            current_owner=self.o,
        )
        self.assertEqual(set(p.recompute_order), {"TRACE", "EFFICIENCY_REUSE", "FINAL_REUSE"})
        self.assertIn("SECURITY_RECEIPT", p.reuse_nodes)

    def test_security_change_does_not_reopen_cost_branch(self):
        p = compile_reproof_plan(
            self.g,
            explicit_changed_roots=("SECURITY_SOURCE",),
            evidence=self.e,
            admission=self.a,
            current_owner=self.o,
        )
        self.assertEqual(
            set(p.recompute_order),
            {"SECURITY_SOURCE", "SECURITY_RECEIPT", "FINAL_REUSE"},
        )
        self.assertIn("COST_RECEIPT", p.reuse_nodes)

    def test_unadmitted_survivor_witness_fails(self):
        e = dict(self.e)
        e["SECURITY_RECEIPT"] = replace(e["SECURITY_RECEIPT"], witness_root=R("f"))
        with self.assertRaisesRegex(ReproofContractError, "UNADMITTED_WITNESS"):
            compile_reproof_plan(
                self.g,
                explicit_changed_roots=("NUMERIC_SOURCE",),
                evidence=e,
                admission=self.a,
                current_owner=self.o,
            )

    def test_dependency_detachment_fails(self):
        e = dict(self.e)
        e["SECURITY_RECEIPT"] = replace(
            e["SECURITY_RECEIPT"], dependency_input_root=R("9")
        )
        with self.assertRaisesRegex(ReproofContractError, "DEPENDENCY_DETACHMENT"):
            compile_reproof_plan(
                self.g,
                explicit_changed_roots=("NUMERIC_SOURCE",),
                evidence=e,
                admission=self.a,
                current_owner=self.o,
            )

    def test_authority_widening_fails(self):
        e = dict(self.e)
        e["SECURITY_RECEIPT"] = replace(e["SECURITY_RECEIPT"], effect_authority=True)
        with self.assertRaisesRegex(ReproofContractError, "AUTHORITY_WIDENING"):
            compile_reproof_plan(
                self.g,
                explicit_changed_roots=("NUMERIC_SOURCE",),
                evidence=e,
                admission=self.a,
                current_owner=self.o,
            )

    def test_cross_graph_surface_fails(self):
        o = replace(self.o, graph_root=R("1"))
        with self.assertRaisesRegex(ReproofContractError, "CROSS_GRAPH_SURFACE"):
            compile_reproof_plan(
                self.g,
                explicit_changed_roots=(),
                evidence=self.e,
                admission=self.a,
                current_owner=o,
            )

    def test_incomplete_owner_surface_fails_closed(self):
        o = replace(self.o, projection_roots=self.o.projection_roots[:-1])
        with self.assertRaisesRegex(ReproofContractError, "INCOMPLETE_NODE_SURFACE"):
            compile_reproof_plan(
                self.g,
                explicit_changed_roots=(),
                evidence=self.e,
                admission=self.a,
                current_owner=o,
            )

    def test_unknown_changed_root_fails(self):
        with self.assertRaisesRegex(ReproofContractError, "UNKNOWN_CHANGED_ROOT"):
            compile_reproof_plan(
                self.g,
                explicit_changed_roots=("NOPE",),
                evidence=self.e,
                admission=self.a,
                current_owner=self.o,
            )

    def test_malformed_identity_fails(self):
        with self.assertRaises(ReproofContractError):
            CanonicalGraph.build([Node("X", (True,), "V", ())])

    def test_cycle_fails(self):
        with self.assertRaisesRegex(ReproofContractError, "CYCLE"):
            CanonicalGraph.build([Node("A", ("B",), "V"), Node("B", ("A",), "V")])

    def test_omega8_and_13d_noncompensatory(self):
        self.assertTrue(omega8_admit((2, 2, 2, 2, 2, 2, 2, 1)))
        self.assertFalse(omega8_admit((2, 2, 2, 2, 2, 2, 1, 2)))
        self.assertTrue(admit13((2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2)))
        self.assertFalse(admit13((2, 2, 2, 2, 2, 2, 2, 2, 0, 2, 2, 2, 2)))


if __name__ == "__main__":
    unittest.main()
