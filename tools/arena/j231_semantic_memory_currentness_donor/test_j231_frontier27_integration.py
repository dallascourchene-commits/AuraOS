from __future__ import annotations
import unittest
from tools.arena.frontier27_runtime import HybridIndexBridge, NativeRouterAuthority
from j231_semantic_memory_donor import GovernedSemanticMemory

class Frontier27IntegrationTests(unittest.TestCase):
    def test_semantic_plane_appends_without_reordering_native(self):
        b=HybridIndexBridge(prefix_bits=10)
        b.add("s1","semantic memory lifecycle epoch",(4,13,0))
        sem=tuple(x[0] for x in b.candidates("semantic memory"))
        combined=GovernedSemanticMemory.stable_union(("native-2","native-1"),sem)
        self.assertEqual(combined[:2],("native-2","native-1"))
        self.assertEqual(len(combined),len(set(combined)))

    def test_native_router_authority_ignores_prefetch_or_semantic_hint(self):
        self.assertEqual(NativeRouterAuthority.execute((7,3,9),(99,7,42)),(7,3,9))

if __name__ == "__main__": unittest.main()
