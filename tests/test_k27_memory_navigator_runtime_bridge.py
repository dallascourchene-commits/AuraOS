import unittest
from dataclasses import dataclass

from tools.arena.k27_memory_navigator.runtime_bridge import RuntimeBridgeError, route_identity_from_runtime

H = "0" * 64
A = "1" * 64
B = "2" * 64


@dataclass
class Seal:
    semantic_registry_root: str = A


@dataclass
class Binding:
    revision_id: str = "rev1"
    epoch: int = 9
    frame_generation: str = "20260906-v1"
    path: tuple = (1, 2, 0)
    truth_authority: bool = False
    planning_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False


class Runtime:
    seal = Seal()
    _state_root = H

    def __init__(self, binding=None):
        self.binding = binding or Binding()

    def read(self, object_id):
        return self.binding, {"object_id": object_id}


class RuntimeBridgeTests(unittest.TestCase):
    def test_bridge(self):
        route, receipt = route_identity_from_runtime(
            Runtime(), "MCXR-1", objective_root=H, dependency_root=B,
            owner_incarnation="boot-x", currentness_generation=4,
        )
        self.assertEqual(route.source_root, A)
        self.assertEqual(route.lifecycle_epoch, 9)
        self.assertEqual(route.k27, (1, 2, 0))
        self.assertFalse(receipt.gate10)

    def test_k27_not_source(self):
        route, _ = route_identity_from_runtime(
            Runtime(), "MCXR-1", objective_root=H, dependency_root=B,
            owner_incarnation="boot-x", currentness_generation=4,
        )
        self.assertNotEqual(route.source_root, "".join(map(str, route.k27)))

    def test_authority_widening_rejected(self):
        with self.assertRaises(RuntimeBridgeError):
            route_identity_from_runtime(
                Runtime(Binding(effect_authority=True)), "MCXR-1",
                objective_root=H, dependency_root=B,
                owner_incarnation="boot-x", currentness_generation=4,
            )

    def test_missing_incarnation_rejected(self):
        with self.assertRaises(RuntimeBridgeError):
            route_identity_from_runtime(
                Runtime(), "MCXR-1", objective_root=H, dependency_root=B,
                owner_incarnation="", currentness_generation=4,
            )

    def test_bool_generation_rejected(self):
        with self.assertRaises(RuntimeBridgeError):
            route_identity_from_runtime(
                Runtime(), "MCXR-1", objective_root=H, dependency_root=B,
                owner_incarnation="x", currentness_generation=True,
            )

    def test_bad_state_root_rejected(self):
        runtime = Runtime()
        runtime._state_root = "bad"
        with self.assertRaises(RuntimeBridgeError):
            route_identity_from_runtime(
                runtime, "MCXR-1", objective_root=H, dependency_root=B,
                owner_incarnation="x", currentness_generation=1,
            )


if __name__ == "__main__":
    unittest.main()
