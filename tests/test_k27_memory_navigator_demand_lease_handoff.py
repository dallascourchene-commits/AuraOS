from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys
import unittest

from tools.arena.k27_memory_navigator.demand_lease_handoff import (
    ConfigurationTransition,
    DemandCellLease,
    DemandCellState,
    LeaseDisposition,
    ResourceFenceReceipt,
    TransitionAuthorityEvidence,
    TransitionVerificationContext,
    apply_configuration_transition,
    canonical_lease_root,
    commit_new_immutable_revision,
    compile_write,
    dependency_closed_invalidation,
    grant_current_lease,
)


def root(label: str) -> str:
    return sha256(label.encode()).hexdigest()


class DemandLeaseHandoffTests(unittest.TestCase):
    def cell(self) -> DemandCellState:
        return DemandCellState("cell-7", 4, root("cfg-a"), 10, 21, 21)

    def lease(self) -> DemandCellLease:
        return DemandCellLease("cell-7", 4, root("cfg-a"), 10, 21, "worker-a", 100)

    def transition(self, **changes) -> ConfigurationTransition:
        values = dict(
            cell_id="cell-7",
            old_configuration_root=root("cfg-a"),
            new_configuration_root=root("cfg-b"),
            old_support_epoch=10,
            new_support_epoch=11,
            new_fence_generation=22,
        )
        values.update(changes)
        return ConfigurationTransition(**values)

    def receipts(self, transition=None, *, claim_root=None, resource_fence=None, verifier_root=None):
        transition = transition or self.transition()
        authority_source = root("authority-source")
        verifier = verifier_root or root("verifier")
        observer = root("resource-observer")
        proto = ResourceFenceReceipt(
            transition.cell_id,
            transition.new_configuration_root,
            transition.new_support_epoch,
            transition.new_fence_generation if resource_fence is None else resource_fence,
            "0" * 64,
            observer,
        )
        resource = ResourceFenceReceipt(
            proto.cell_id,
            proto.configuration_root,
            proto.support_epoch,
            proto.installed_fence_generation,
            proto.canonical_state_root(),
            observer,
        )
        evidence = TransitionAuthorityEvidence(
            claim_root or transition.canonical_claim_root(),
            authority_source,
            verifier,
        )
        verification = TransitionVerificationContext(
            authority_source,
            root("verifier"),
            resource.resource_state_root,
            observer,
        )
        return evidence, resource, verification

    def apply(self, transition=None, **receipt_changes):
        transition = transition or self.transition()
        evidence, resource, verification = self.receipts(transition, **receipt_changes)
        return apply_configuration_transition(self.cell(), transition, evidence, resource, verification)

    def test_exact_current_lease_is_d0_ready(self):
        self.assertIs(compile_write(self.lease(), self.cell(), 50).disposition, LeaseDisposition.READY_D0)

    def test_support_move_invalidates_unexpired_old_writer(self):
        _, moved = self.apply()
        self.assertIs(compile_write(self.lease(), moved, 50).disposition, LeaseDisposition.REBIND_REQUIRED)

    def test_successor_fences_old_writer(self):
        _, moved = self.apply()
        successor = grant_current_lease(moved, holder="worker-b", expires_at=120)
        self.assertIs(compile_write(self.lease(), moved, 60).disposition, LeaseDisposition.REBIND_REQUIRED)
        self.assertIs(compile_write(successor, moved, 60).disposition, LeaseDisposition.READY_D0)

    def test_expiry_is_necessary_but_not_sufficient(self):
        self.assertIs(compile_write(self.lease(), self.cell(), 100).disposition, LeaseDisposition.HOLD)
        stale = DemandCellState("cell-7", 4, root("cfg-b"), 11, 22, 22)
        self.assertIsNot(compile_write(self.lease(), stale, 50).disposition, LeaseDisposition.READY_D0)

    def test_direct_state_with_uninstalled_current_fence_cannot_write(self):
        state = DemandCellState("cell-7", 4, root("cfg-a"), 10, 22, 21)
        lease = DemandCellLease("cell-7", 4, root("cfg-a"), 10, 22, "worker-b", 100)
        decision = compile_write(lease, state, 50)
        self.assertIs(decision.disposition, LeaseDisposition.HOLD)
        self.assertEqual(decision.reason, "FENCE_NOT_INSTALLED_CURRENT")

    def test_configuration_transition_requires_exact_proof_binding(self):
        decision, same = self.apply(claim_root=root("unsupported-transition"))
        self.assertEqual(decision.reason, "TRANSITION_EVIDENCE_CLAIM_MISMATCH")
        self.assertEqual(same, self.cell())

    def test_configuration_transition_requires_current_verifier_receipt(self):
        decision, same = self.apply(verifier_root=root("stale-verifier"))
        self.assertEqual(decision.reason, "VERIFIER_RECEIPT_ROOT_STALE")
        self.assertEqual(same, self.cell())

    def test_configuration_transition_requires_new_configuration_root(self):
        transition = self.transition(new_configuration_root=root("cfg-a"))
        evidence, resource, verification = self.receipts(transition)
        decision, _ = apply_configuration_transition(self.cell(), transition, evidence, resource, verification)
        self.assertEqual(decision.reason, "CONFIGURATION_ROOT_NOT_ADVANCED")

    def test_configuration_transition_requires_monotone_support_and_fence(self):
        t1 = self.transition(new_support_epoch=10)
        e1, r1, v1 = self.receipts(t1)
        self.assertEqual(apply_configuration_transition(self.cell(), t1, e1, r1, v1)[0].reason, "SUPPORT_EPOCH_NOT_ADVANCED")
        t2 = self.transition(new_fence_generation=21)
        e2, r2, v2 = self.receipts(t2)
        self.assertEqual(apply_configuration_transition(self.cell(), t2, e2, r2, v2)[0].reason, "FENCE_NOT_MONOTONIC")

    def test_fence_must_be_verified_at_mutation_boundary(self):
        decision, same = self.apply(resource_fence=21)
        self.assertEqual(decision.reason, "FENCE_NOT_VERIFIED_AT_RESOURCE")
        self.assertEqual(same, self.cell())

    def test_commit_creates_new_immutable_revision_and_invalidates_old_lease(self):
        decision, moved = commit_new_immutable_revision(self.lease(), self.cell(), 50)
        self.assertIs(decision.disposition, LeaseDisposition.READY_D0)
        self.assertEqual(moved.revision, 5)
        self.assertIs(compile_write(self.lease(), moved, 51).disposition, LeaseDisposition.REBIND_REQUIRED)

    def test_dependency_closed_invalidation_preserves_unrelated_cells(self):
        edges = {"a": frozenset({"b"}), "b": frozenset({"c"}), "x": frozenset({"y"})}
        self.assertEqual(dependency_closed_invalidation(frozenset({"a"}), edges), frozenset({"a", "b", "c"}))

    def test_k27_or_cache_locality_is_not_part_of_lease_authority(self):
        first = canonical_lease_root(self.lease())
        second = canonical_lease_root(self.lease())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_malformed_roots_fail_closed(self):
        with self.assertRaises(ValueError):
            DemandCellState("cell-7", 4, "not-a-root", 10, 21, 21)
        with self.assertRaises(ValueError):
            TransitionAuthorityEvidence("bad", root("authority"), root("verifier"))

    def test_decision_never_mints_effect_or_gate10_authority(self):
        decision = compile_write(self.lease(), self.cell(), 50)
        self.assertFalse(decision.authority_minted)
        self.assertFalse(decision.effect_authority)
        self.assertFalse(decision.gate10)

    def test_campaign_direct_script_entrypoint_runs(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "tools" / "arena" / "k27_memory_navigator" / "campaign_demand_lease_handoff.py"
        completed = subprocess.run([sys.executable, str(script)], cwd=repo, capture_output=True, text=True, check=True)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["compiler_false_ready"], 0)
        self.assertEqual(payload["compiler_false_hold"], 0)
        self.assertEqual(payload["unsupported_transition_false_ready"], 0)


if __name__ == "__main__":
    unittest.main()
