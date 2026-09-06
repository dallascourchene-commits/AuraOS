import random
import unittest
from dataclasses import replace

from provider_observation_slice_bridge import *

PARENT = "a" * 40
CHILD = "b" * 40
PROVIDER = "github"
REPO = "dallascourchene-commits/AuraOS"
CR = "PR-999"
GEN = "AuraOS CODEMAP Bot"
VERIFIER = "auraos-provider-proof-bridge"
PATHS = (".aura/CODEMAP.json", ".aura/CODEMAP.md")
GRAPH = "1" * 64
PAYLOAD = "3" * 64
SEMANTIC_RECEIPT = "4" * 64
BINDINGS = (
    PathBinding(PATHS[0], ("provider_binding",)),
    PathBinding(PATHS[1], ("provider_binding",)),
)


def obs(status=EvidenceStatus.ATTESTED, **changes):
    data = dict(
        provider=PROVIDER, repository=REPO, change_request_id=CR, parent_head=PARENT, child_head=CHILD,
        actor_identity="provider-bot", generator_identity=GEN, changed_paths=PATHS,
        evidence_uri="https://api.github.com/repos/dallascourchene-commits/AuraOS/pulls/999",
        captured_at="2026-09-05T23:40:00Z", verifier_id=VERIFIER, verifier_generation="v1",
        status=status, payload_sha256=PAYLOAD,
    )
    data.update(changes)
    return observation_for(**data)


def expectation(**changes):
    data = dict(
        provider=PROVIDER, repository=REPO, change_request_id=CR, proved_parent_head=PARENT,
        current_child_head=CHILD, expected_generator_identity=GEN,
        allowed_proof_neutral_paths=PATHS, accepted_verifier_ids=(VERIFIER,),
    )
    data.update(changes)
    return MovementExpectation(**data)


def admission(**changes):
    data = dict(
        graph_root=GRAPH,
        verifier_generations=(("AGENT09", "agent09-e68b9188"),),
        accepted_witness_roots=(("cost_receipt", "5"*64), ("trace_receipt", "6"*64)),
        observation_generation="obs-g1",
        external_receipt_root=SEMANTIC_RECEIPT,
    )
    data.update(changes)
    if "surface_root" in data:
        root = data.pop("surface_root")
        return replace(semantic_admission_for(**data), surface_root=root)
    return semantic_admission_for(**data)


def plan(a=None, **changes):
    a = a or admission()
    data = dict(
        graph_root=GRAPH, changed_roots=("provider_binding",),
        invalidated=("combined_reuse", "provider_binding"), reusable=("cost_receipt", "trace_receipt"),
        recompute_order=("provider_binding", "combined_reuse"),
        affected_consequence_keys=("provider_binding", "proof_reuse"),
        admission_surface_root=a.surface_root, decision="RECOMPUTE_MINIMUM_SLICE", plan_root="2"*64,
    )
    data.update(changes)
    return SlicePlanAttestation(**data)


def evidence(o=None, x=None, b=None, a=None, p=None, **changes):
    a = a or admission()
    data = dict(
        observation=o or obs(), expectation=x or expectation(), bindings=b or BINDINGS,
        semantic_admission=a, slice_plan=p or plan(a), expected_graph_root=GRAPH, authority_requested=False,
    )
    data.update(changes)
    return BridgeEvidence(**data)


class Tests(unittest.TestCase):
    def test_attested_provider_plus_external_semantic_admission_maps_to_minimum_slice(self):
        e = evidence(); receipt = make_receipt(e)
        self.assertEqual(receipt.decision, Decision.REPROVE_MINIMUM_SLICE)
        self.assertEqual(receipt.semantic_admission_surface_root, e.semantic_admission.surface_root)
        self.assertTrue(verify_receipt(e, receipt))

    def test_observed_is_not_attested(self):
        e = evidence(o=obs(EvidenceStatus.OBSERVED))
        self.assertEqual(decide(e), Decision.HOLD_PROVIDER_EVIDENCE)
        self.assertEqual(reasons(e), ("PROVIDER_EVIDENCE_OBSERVED",))

    def test_provider_attestation_does_not_substitute_for_semantic_admission(self):
        a = admission(surface_root="f"*64)
        self.assertEqual(decide(evidence(a=a, p=plan(a))), Decision.HOLD_SEMANTIC_ADMISSION)

    def test_semantic_admission_does_not_substitute_for_provider_attestation(self):
        self.assertEqual(decide(evidence(o=obs(EvidenceStatus.OBSERVED))), Decision.HOLD_PROVIDER_EVIDENCE)

    def test_admission_surface_is_parent_schema_exact(self):
        a = admission()
        independent = digest({
            "schema": "AURA-EXTERNAL-WITNESS-ADMISSION-v1",
            "graph_root": GRAPH,
            "verifier_generations": (("AGENT09", "agent09-e68b9188"),),
            "accepted_witness_roots": (("cost_receipt", "5"*64), ("trace_receipt", "6"*64)),
            "observation_generation": "obs-g1",
            "external_receipt_root": SEMANTIC_RECEIPT,
        })
        self.assertEqual(a.surface_root, independent)

    def test_plan_must_bind_current_admission_surface(self):
        self.assertEqual(decide(evidence(p=plan(admission_surface_root="f"*64))), Decision.HOLD_DAG_PLAN)

    def test_current_dag_generation_is_pinned(self):
        self.assertEqual(EVIDENCE_DAG_PARENT_COMMIT, "8d97a5f0fb0efefedf3daa2e36161c5eecc93fb1")
        self.assertEqual(EVIDENCE_DAG_SCHEMA, "AURA-EVIDENCE-SLICE-DAG-v2")

    def test_old_dag_generation_fails_closed(self):
        self.assertEqual(decide(evidence(p=plan(dag_semantic_commit="88aa998ae80677375ebc8fcda3ea08c7cb894a6e"))), Decision.HOLD_DAG_PLAN)

    def test_old_dag_schema_fails_closed(self):
        self.assertEqual(decide(evidence(p=plan(dag_schema="AURA-EVIDENCE-SLICE-DAG-v1"))), Decision.HOLD_DAG_PLAN)

    def test_semantic_admission_graph_mismatch(self):
        a = admission(graph_root="f"*64)
        self.assertEqual(decide(evidence(a=a, p=plan(a, graph_root="f"*64))), Decision.HOLD_SEMANTIC_ADMISSION)

    def test_plan_admission_graph_mismatch(self):
        a = admission()
        self.assertEqual(decide(evidence(p=plan(a, graph_root="f"*64))), Decision.HOLD_DAG_PLAN)

    def test_duplicate_admission_node_rejected(self):
        with self.assertRaisesRegex(BridgeError, "DUPLICATE_PAIR_KEY"):
            semantic_admission_for(graph_root=GRAPH, verifier_generations=(("AGENT09","g1"),), accepted_witness_roots=(("x","5"*64),("x","6"*64)), observation_generation="o", external_receipt_root="4"*64)

    def test_bool_identity_rejected(self):
        with self.assertRaisesRegex(BridgeError, "INVALID_STRING"):
            semantic_admission_for(graph_root=GRAPH, verifier_generations=((True,"g1"),), accepted_witness_roots=(), observation_generation="o", external_receipt_root="4"*64)

    def test_indeterminate_holds(self): self.assertEqual(decide(evidence(o=obs(EvidenceStatus.INDETERMINATE))), Decision.HOLD_PROVIDER_EVIDENCE)
    def test_contested_holds(self): self.assertEqual(decide(evidence(o=obs(EvidenceStatus.CONTESTED))), Decision.HOLD_PROVIDER_EVIDENCE)
    def test_expired_holds(self): self.assertEqual(decide(evidence(o=obs(EvidenceStatus.EXPIRED))), Decision.HOLD_PROVIDER_EVIDENCE)

    def test_bare_boolean_status_rejected(self):
        self.assertEqual(decide(evidence(o=replace(obs(), status=True))), Decision.HOLD_MOVEMENT_BINDING)

    def test_observation_root_tamper(self): self.assertEqual(decide(evidence(o=replace(obs(), observation_root="f"*64))), Decision.HOLD_MOVEMENT_BINDING)
    def test_provider_mismatch(self): self.assertIn("PROVIDER_MISMATCH", reasons(evidence(o=obs(provider="gitlab"))))
    def test_repo_mismatch(self): self.assertIn("REPOSITORY_MISMATCH", reasons(evidence(o=obs(repository="other/repo"))))
    def test_change_request_mismatch(self): self.assertIn("CHANGE_REQUEST_MISMATCH", reasons(evidence(o=obs(change_request_id="PR-1"))))
    def test_parent_mismatch(self): self.assertIn("PARENT_HEAD_MISMATCH", reasons(evidence(o=obs(parent_head="c"*40))))
    def test_child_mismatch(self): self.assertIn("CHILD_HEAD_MISMATCH", reasons(evidence(o=obs(child_head="c"*40))))
    def test_generator_mismatch(self): self.assertIn("GENERATOR_IDENTITY_MISMATCH", reasons(evidence(o=obs(generator_identity="Other Bot"))))
    def test_unaccepted_verifier(self): self.assertIn("UNACCEPTED_VERIFIER", reasons(evidence(o=obs(verifier_id="unknown"))))

    def test_non_neutral_path(self):
        o = obs(changed_paths=PATHS+("tools/arena/frontier27_runtime.py",))
        self.assertIn("NON_NEUTRAL_CHANGED_PATH", reasons(evidence(o=o)))

    def test_unbound_changed_path(self):
        extra = ".aura/CODEMAP.txt"
        o = obs(changed_paths=PATHS+(extra,))
        x = expectation(allowed_proof_neutral_paths=PATHS+(extra,))
        self.assertIn("UNBOUND_CHANGED_PATH", reasons(evidence(o=o, x=x)))

    def test_duplicate_binding_rejected(self):
        self.assertEqual(decide(evidence(b=BINDINGS+(PathBinding(PATHS[0],("provider_binding",)),))), Decision.HOLD_MOVEMENT_BINDING)

    def test_changed_root_binding_mismatch(self):
        p = plan(changed_roots=("other",), invalidated=("combined_reuse","other"), recompute_order=("other","combined_reuse"))
        self.assertEqual(decide(evidence(p=p)), Decision.HOLD_DAG_PLAN)

    def test_wrong_agent10_generation(self): self.assertEqual(decide(evidence(x=expectation(agent10_semantic_commit="c"*40))), Decision.HOLD_MOVEMENT_BINDING)
    def test_invalidated_reusable_overlap(self): self.assertEqual(decide(evidence(p=plan(reusable=("combined_reuse",)))), Decision.HOLD_DAG_PLAN)
    def test_recompute_order_must_cover_invalidated(self): self.assertEqual(decide(evidence(p=plan(recompute_order=("provider_binding",)))), Decision.HOLD_DAG_PLAN)
    def test_authority_request_holds(self): self.assertEqual(decide(evidence(authority_requested=True)), Decision.HOLD_MOVEMENT_BINDING)

    def test_receipt_tamper(self):
        e = evidence(); receipt = make_receipt(e)
        self.assertFalse(verify_receipt(e, replace(receipt, child_head="c"*40)))

    def test_receipt_authority_hard_false(self):
        receipt = make_receipt(evidence())
        self.assertFalse(receipt.fresh_hosted_pass); self.assertFalse(receipt.effect_authority); self.assertFalse(receipt.gate10)

    def test_path_order_is_canonical(self): self.assertEqual(obs().observation_root, obs(changed_paths=tuple(reversed(PATHS))).observation_root)

    def test_omega8_single_keeper(self):
        counts = exhaustive8(); self.assertEqual(sum(counts.values()), 3**8); self.assertEqual(counts.get(Decision.REPROVE_MINIMUM_SLICE.value), 1)

    def test_13d_tail_cannot_repair_invalid_core(self):
        rng = random.Random(6)
        for _ in range(10000):
            core = [2,2,2,2,2,2,2,1]; core[rng.randrange(7)] = 0
            tail = tuple(rng.randrange(3) for _ in range(5))
            self.assertNotEqual(classify13(tuple(core)+tail), Decision.REPROVE_MINIMUM_SLICE.value)

    def test_13d_tail_is_applied(self):
        core = (2,2,2,2,2,2,2,1)
        self.assertEqual(classify13(core+(2,2,2,2,2)), Decision.REPROVE_MINIMUM_SLICE.value)
        self.assertNotEqual(classify13(core+(0,2,2,2,2)), Decision.REPROVE_MINIMUM_SLICE.value)


if __name__ == "__main__":
    unittest.main()
