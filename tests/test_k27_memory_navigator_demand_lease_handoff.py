from __future__ import annotations

from hashlib import sha256
import unittest

from tools.arena.k27_memory_navigator.demand_lease_handoff import (
    ConfigurationTransition,
    DemandCellLease,
    DemandCellState,
    LeaseDisposition,
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
            authenticated=True,
            installed_at_resource=True,
        )
        values.update(changes)
        return ConfigurationTransition(**values)

    def test_exact_current_lease_is_d0_ready(self):
        self.assertIs(compile_write(self.lease(), self.cell(), 50).disposition, LeaseDisposition.READY_D0)

    def test_support_move_invalidates_unexpired_old_writer(self):
        _, moved = apply_configuration_transition(self.cell(), self.transition())
        self.assertIs(compile_write(self.lease(), moved, 50).disposition, LeaseDisposition.REBIND_REQUIRED)

    def test_successor_fences_old_writer(self):
        _, moved = apply_configuration_transition(self.cell(), self.transition())
        successor = grant_current_lease(moved, holder="worker-b", expires_at=120)
        self.assertIs(compile_write(self.lease(), moved, 60).disposition, LeaseDisposition.REBIND_REQUIRED)
        self.assertIs(compile_write(successor, moved, 60).disposition, LeaseDisposition.READY_D0)

    def test_expiry_is_necessary_but_not_sufficient(self):
        self.assertIs(compile_write(self.lease(), self.cell(), 100).disposition, LeaseDisposition.HOLD)
        stale = DemandCellState("cell-7", 4, root("cfg-b"), 11, 22, 22)
        self.assertIsNot(compile_write(self.lease(), stale, 50).disposition, LeaseDisposition.READY_D0)

    def test_configuration_transition_requires_authentication(self):
        decision, same = apply_configuration_transition(self.cell(), self.transition(authenticated=False))
        self.assertIs(decision.disposition, LeaseDisposition.HOLD)
        self.assertEqual(same, self.cell())

    def test_configuration_transition_requires_new_configuration_root(self):
        decision, _ = apply_configuration_transition(
            self.cell(), self.transition(new_configuration_root=root("cfg-a"))
        )
        self.assertEqual(decision.reason, "CONFIGURATION_ROOT_NOT_ADVANCED")

    def test_configuration_transition_requires_monotone_support_and_fence(self):
        self.assertEqual(
            apply_configuration_transition(self.cell(), self.transition(new_support_epoch=10))[0].reason,
            "SUPPORT_EPOCH_NOT_ADVANCED",
        )
        self.assertEqual(
            apply_configuration_transition(self.cell(), self.transition(new_fence_generation=21))[0].reason,
            "FENCE_NOT_MONOTONIC",
        )

    def test_fence_must_be_installed_at_mutation_boundary(self):
        decision, _ = apply_configuration_transition(
            self.cell(), self.transition(installed_at_resource=False)
        )
        self.assertEqual(decision.reason, "FENCE_NOT_INSTALLED_AT_RESOURCE")

    def test_commit_creates_new_immutable_revision_and_invalidates_old_lease(self):
        decision, moved = commit_new_immutable_revision(self.lease(), self.cell(), 50)
        self.assertIs(decision.disposition, LeaseDisposition.READY_D0)
        self.assertEqual(moved.revision, 5)
        self.assertIs(compile_write(self.lease(), moved, 51).disposition, LeaseDisposition.REBIND_REQUIRED)

    def test_dependency_closed_invalidation_preserves_unrelated_cells(self):
        edges = {
            "a": frozenset({"b"}),
            "b": frozenset({"c"}),
            "x": frozenset({"y"}),
        }
        self.assertEqual(
            dependency_closed_invalidation(frozenset({"a"}), edges),
            frozenset({"a", "b", "c"}),
        )

    def test_k27_or_cache_locality_is_not_part_of_lease_authority(self):
        first = canonical_lease_root(self.lease())
        second = canonical_lease_root(self.lease())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_malformed_roots_and_boolean_like_values_fail_closed(self):
        with self.assertRaises(ValueError):
            DemandCellState("cell-7", 4, "not-a-root", 10, 21, 21)
        with self.assertRaises(ValueError):
            ConfigurationTransition(
                "cell-7", root("a"), root("b"), 10, 11, 22, 1, True
            )

    def test_decision_never_mints_effect_or_gate10_authority(self):
        decision = compile_write(self.lease(), self.cell(), 50)
        self.assertFalse(decision.authority_minted)
        self.assertFalse(decision.effect_authority)
        self.assertFalse(decision.gate10)


if __name__ == "__main__":
    unittest.main()
