import unittest
from dataclasses import dataclass

from tools.arena.k27_memory_navigator.minimal_evidence import (
    EvidenceMode, EvidenceWorld, compile_minimal_evidence,
)
from tools.arena.k27_memory_navigator.route_card_admission import (
    CapacityEnvelope, Disposition, Polarity, ProofReceipt, RouteIdentity,
    TemporalRequirement, UseContext, admit, canonical_receipt_root,
)
from tools.arena.k27_memory_navigator.runtime_bridge import route_identity_from_runtime

H = "0" * 64
A = "1" * 64
B = "2" * 64


def identity(**kw):
    base = dict(
        objective_root=H, target_id="target", source_root=A,
        dependency_root=B, map_generation="g", lifecycle_epoch=1,
        owner_incarnation="boot", currentness_generation=1, k27=(1,),
    )
    base.update(kw)
    return RouteIdentity(**base)


def envelope():
    return CapacityEnvelope(1, 1, 1, 1)


def temporal():
    return TemporalRequirement(1)


def receipt(route=None):
    t = temporal()
    return ProofReceipt(Polarity.POSITIVE, route or identity(), envelope(), t.mode, t.event_time)


@dataclass
class Seal:
    semantic_registry_root: str = A


@dataclass
class Binding:
    revision_id: str = "rev1"
    epoch: int = 1
    frame_generation: str = "g"
    path: tuple = (1,)
    truth_authority: bool = False
    planning_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False


class Runtime:
    seal = Seal()
    _state_root = H

    def __init__(self, binding=None):
        self.binding = binding or Binding()

    def read(self, _object_id):
        return self.binding, {}


class NavigatorReviewRegressionTests(unittest.TestCase):
    def test_runtime_bridge_binds_state_and_revision(self):
        route, bridge_receipt = route_identity_from_runtime(
            Runtime(), "target", objective_root=H, dependency_root=B,
            owner_incarnation="boot", currentness_generation=1,
        )
        self.assertEqual(route.runtime_state_root, H)
        self.assertEqual(route.revision_id, "rev1")
        self.assertEqual(bridge_receipt.runtime_state_root, H)
        self.assertEqual(bridge_receipt.revision_id, "rev1")

    def test_runtime_state_root_drift_reproves(self):
        before = identity(runtime_state_root=H, revision_id="rev1")
        after = identity(runtime_state_root="3" * 64, revision_id="rev1")
        use = UseContext(after, envelope(), temporal())
        self.assertIs(admit(receipt(before), use).disposition, Disposition.REPROVE)

    def test_runtime_revision_drift_reproves(self):
        before = identity(runtime_state_root=H, revision_id="rev1")
        after = identity(runtime_state_root=H, revision_id="rev2")
        use = UseContext(after, envelope(), temporal())
        self.assertIs(admit(receipt(before), use).disposition, Disposition.REPROVE)

    def test_partial_runtime_identity_rejected(self):
        with self.assertRaises(ValueError):
            identity(runtime_state_root=H)

    def test_raw_polarity_rejected(self):
        t = temporal()
        with self.assertRaises(ValueError):
            ProofReceipt("NEGATIVE", identity(), envelope(), t.mode, t.event_time)

    def test_raw_timing_mode_rejected(self):
        with self.assertRaises(ValueError):
            ProofReceipt(Polarity.POSITIVE, identity(), envelope(), "CAUSAL", 1)

    def test_duplicate_uniform_world_ids_rejected(self):
        worlds = [
            EvidenceWorld("a", "HOLD", (0,)),
            EvidenceWorld("a", "HOLD", (1,)),
        ]
        with self.assertRaisesRegex(ValueError, "duplicate world_id"):
            compile_minimal_evidence(worlds, [1], hard_premises_valid=True)

    def test_duplicate_world_ids_rejected_even_on_hard_hold(self):
        worlds = [
            EvidenceWorld("a", "READY", (0,)),
            EvidenceWorld("a", "HOLD", (1,)),
        ]
        with self.assertRaisesRegex(ValueError, "duplicate world_id"):
            compile_minimal_evidence(worlds, [1], hard_premises_valid=False)

    def test_valid_uniform_family_still_zero_disclosure(self):
        worlds = [
            EvidenceWorld("a", "HOLD", (0,)),
            EvidenceWorld("b", "HOLD", (1,)),
        ]
        plan = compile_minimal_evidence(worlds, [1], hard_premises_valid=True)
        self.assertIs(plan.mode, EvidenceMode.ZERO_DISCLOSURE)

    def test_receipt_root_binds_runtime_revision(self):
        a = receipt(identity(runtime_state_root=H, revision_id="rev1"))
        b = receipt(identity(runtime_state_root=H, revision_id="rev2"))
        self.assertNotEqual(canonical_receipt_root(a), canonical_receipt_root(b))


if __name__ == "__main__":
    unittest.main()
