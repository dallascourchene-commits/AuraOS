import unittest
from dataclasses import replace
import random

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
PLANROOT = "2" * 64
PAYLOAD = "3" * 64
BINDINGS = (
    PathBinding(PATHS[0], ("provider_binding",)),
    PathBinding(PATHS[1], ("provider_binding",)),
)


def obs(status=EvidenceStatus.ATTESTED, **changes):
    d = dict(
        provider=PROVIDER, repository=REPO, change_request_id=CR, parent_head=PARENT, child_head=CHILD,
        actor_identity="provider-bot", generator_identity=GEN, changed_paths=PATHS,
        evidence_uri="https://api.github.com/repos/dallascourchene-commits/AuraOS/pulls/999",
        captured_at="2026-09-05T23:30:00Z", verifier_id=VERIFIER, verifier_generation="v1",
        status=status, payload_sha256=PAYLOAD,
    )
    d.update(changes)
    return observation_for(**d)


def expectation(**changes):
    d = dict(
        provider=PROVIDER, repository=REPO, change_request_id=CR, proved_parent_head=PARENT,
        current_child_head=CHILD, expected_generator_identity=GEN,
        allowed_proof_neutral_paths=PATHS, accepted_verifier_ids=(VERIFIER,),
    )
    d.update(changes)
    return MovementExpectation(**d)


def plan(**changes):
    d = dict(
        graph_root=GRAPH, changed_roots=("provider_binding",),
        invalidated=("combined_reuse", "provider_binding"), reusable=("cost_receipt", "trace_receipt"),
        recompute_order=("provider_binding", "combined_reuse"), affected_consequence_keys=("provider_binding", "proof_reuse"),
        decision="RECOMPUTE_MINIMUM_SLICE", plan_root=PLANROOT,
    )
    d.update(changes)
    return SlicePlanAttestation(**d)


def evidence(o=None, x=None, b=None, p=None, **changes):
    d = dict(observation=o or obs(), expectation=x or expectation(), bindings=b or BINDINGS,
             slice_plan=p or plan(), expected_graph_root=GRAPH, authority_requested=False)
    d.update(changes)
    return BridgeEvidence(**d)


class Tests(unittest.TestCase):
    def test_attested_provider_maps_to_minimum_slice(self):
        e = evidence(); r = make_receipt(e)
        self.assertEqual(r.decision, Decision.REPROVE_MINIMUM_SLICE)
        self.assertEqual(r.changed_evidence_nodes, ("provider_binding",))
        self.assertTrue(verify_receipt(e, r))

    def test_observed_is_not_attested(self):
        e = evidence(o=obs(EvidenceStatus.OBSERVED))
        self.assertEqual(decide(e), Decision.HOLD_PROVIDER_EVIDENCE)
        self.assertEqual(reasons(e), ("PROVIDER_EVIDENCE_OBSERVED",))

    def test_indeterminate_holds(self): self.assertEqual(decide(evidence(o=obs(EvidenceStatus.INDETERMINATE))), Decision.HOLD_PROVIDER_EVIDENCE)
    def test_contested_holds(self): self.assertEqual(decide(evidence(o=obs(EvidenceStatus.CONTESTED))), Decision.HOLD_PROVIDER_EVIDENCE)
    def test_expired_holds(self): self.assertEqual(decide(evidence(o=obs(EvidenceStatus.EXPIRED))), Decision.HOLD_PROVIDER_EVIDENCE)

    def test_bare_boolean_status_rejected(self):
        o = replace(obs(), status=True)
        self.assertIn("INVALID_EVIDENCE_STATUS", reasons(evidence(o=o))[0])

    def test_observation_root_tamper(self):
        o = replace(obs(), observation_root="f"*64)
        self.assertEqual(decide(evidence(o=o)), Decision.HOLD_MOVEMENT_BINDING)

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
        extra=".aura/CODEMAP.txt"
        o=obs(changed_paths=PATHS+(extra,))
        x=expectation(allowed_proof_neutral_paths=PATHS+(extra,))
        self.assertIn("UNBOUND_CHANGED_PATH", reasons(evidence(o=o,x=x)))

    def test_duplicate_binding_rejected(self):
        b=BINDINGS+(PathBinding(PATHS[0],("provider_binding",)),)
        self.assertEqual(decide(evidence(b=b)), Decision.HOLD_MOVEMENT_BINDING)

    def test_dag_graph_root_mismatch(self):
        self.assertIn("GRAPH_ROOT_MISMATCH", reasons(evidence(expected_graph_root="f"*64)))

    def test_changed_root_binding_mismatch(self):
        p=plan(changed_roots=("other",), invalidated=("combined_reuse","other"), recompute_order=("other","combined_reuse"))
        self.assertEqual(decide(evidence(p=p)), Decision.HOLD_DAG_PLAN)

    def test_wrong_dag_parent_generation(self):
        p=plan(dag_semantic_commit="c"*40)
        self.assertEqual(decide(evidence(p=p)), Decision.HOLD_DAG_PLAN)

    def test_wrong_agent10_generation(self):
        x=expectation(agent10_semantic_commit="c"*40)
        self.assertEqual(decide(evidence(x=x)), Decision.HOLD_MOVEMENT_BINDING)

    def test_invalidated_reusable_overlap(self):
        p=plan(reusable=("combined_reuse",))
        self.assertEqual(decide(evidence(p=p)), Decision.HOLD_DAG_PLAN)

    def test_recompute_order_must_cover_invalidated(self):
        p=plan(recompute_order=("provider_binding",))
        self.assertEqual(decide(evidence(p=p)), Decision.HOLD_DAG_PLAN)

    def test_authority_request_holds(self):
        self.assertEqual(decide(evidence(authority_requested=True)), Decision.HOLD_MOVEMENT_BINDING)

    def test_receipt_tamper(self):
        e=evidence(); r=make_receipt(e)
        self.assertFalse(verify_receipt(e, replace(r, child_head="c"*40)))

    def test_receipt_authority_hard_false(self):
        r=make_receipt(evidence())
        self.assertFalse(r.fresh_hosted_pass); self.assertFalse(r.effect_authority); self.assertFalse(r.gate10)

    def test_path_order_is_canonical(self):
        a=obs(); b=obs(changed_paths=tuple(reversed(PATHS)))
        self.assertEqual(a.observation_root,b.observation_root)

    def test_omega8_single_keeper(self):
        c=exhaustive8(); self.assertEqual(sum(c.values()),3**8); self.assertEqual(c.get(Decision.REPROVE_MINIMUM_SLICE.value),1)

    def test_13d_tail_cannot_repair_invalid_core(self):
        rng=random.Random(6)
        for _ in range(10000):
            core=[2,2,2,2,2,2,2,1]; core[rng.randrange(7)]=0
            tail=tuple(rng.randrange(3) for _ in range(5))
            self.assertNotEqual(classify13(tuple(core)+tail),Decision.REPROVE_MINIMUM_SLICE.value)

    def test_13d_tail_is_applied(self):
        core=(2,2,2,2,2,2,2,1)
        self.assertEqual(classify13(core+(2,2,2,2,2)),Decision.REPROVE_MINIMUM_SLICE.value)
        self.assertNotEqual(classify13(core+(0,2,2,2,2)),Decision.REPROVE_MINIMUM_SLICE.value)


if __name__ == "__main__": unittest.main()
