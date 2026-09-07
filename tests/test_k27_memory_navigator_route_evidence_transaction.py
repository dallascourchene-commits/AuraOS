import random
import unittest

from tools.arena.k27_memory_navigator.reflexive_topology import (
    ProbeStep, components, edge_set, execute_probe_program, norm_edge, program_root,
)
from tools.arena.k27_memory_navigator.temporal_zone import (
    DifferenceConstraint, ZoneDisposition, compile_zone,
)
from tools.arena.k27_memory_navigator.route_evidence_transaction import (
    TransactionDisposition, certify,
)


class RouteEvidenceTransactionTests(unittest.TestCase):
    def test_probe_can_merge_pre_components(self):
        nodes = {"a", "b", "c", "d"}
        edges = {("a", "b"), ("c", "d")}
        pre = components(nodes, edges)
        certificate = execute_probe_program(
            nodes, edges, [ProbeStep(("a", "b"), add_edges=(("b", "c"),))])
        self.assertNotEqual(pre, certificate.post_partition)
        self.assertEqual(certificate.post_partition, (("a", "b", "c", "d"),))

    def test_probe_can_split_component(self):
        certificate = execute_probe_program(
            {"a", "b", "c"}, {("a", "b"), ("b", "c")},
            [ProbeStep(("a", "b"), remove_edges=(("b", "c"),))])
        self.assertEqual(certificate.post_partition, (("a", "b"), ("c",)))

    def test_consume_observed_edge(self):
        certificate = execute_probe_program(
            {"a", "b"}, {("a", "b")}, [ProbeStep(("a", "b"), consume_observed_edge=True)])
        self.assertEqual(certificate.post_partition, (("a",), ("b",)))

    def test_topology_certificate_is_nonauthorizing(self):
        certificate = execute_probe_program({"a", "b"}, set(), [])
        self.assertFalse(certificate.authority_minted)
        self.assertFalse(certificate.effect_authority)
        self.assertFalse(certificate.gate10)

    def test_consistent_relational_zone(self):
        zone = compile_zone(("zero", "event", "commit"), [
            DifferenceConstraint("event", "zero", 10),
            DifferenceConstraint("zero", "event", 0),
            DifferenceConstraint("commit", "event", 5),
        ])
        self.assertEqual(zone.disposition, ZoneDisposition.READY_D0)

    def test_nonempty_marginals_can_be_jointly_inconsistent(self):
        zone = compile_zone(("zero", "a", "b"), [
            DifferenceConstraint("a", "zero", 10), DifferenceConstraint("zero", "a", 0),
            DifferenceConstraint("b", "zero", 10), DifferenceConstraint("zero", "b", 0),
            DifferenceConstraint("a", "b", -8), DifferenceConstraint("b", "a", -8),
        ])
        self.assertEqual(zone.disposition, ZoneDisposition.HOLD_INCONSISTENT)
        self.assertTrue(zone.contradiction_variables)

    def test_transaction_holds_inconsistent_zone(self):
        topology = execute_probe_program({"a"}, set(), [])
        zone = compile_zone(("a", "b"), [
            DifferenceConstraint("a", "b", -1), DifferenceConstraint("b", "a", -1)])
        self.assertEqual(certify(topology, zone).disposition, TransactionDisposition.HOLD_TEMPORAL_ZONE)

    def test_transaction_ready(self):
        topology = execute_probe_program({"a", "b"}, set(), [])
        zone = compile_zone(("a", "b"), [DifferenceConstraint("a", "b", 1)])
        result = certify(topology, zone)
        self.assertEqual(result.disposition, TransactionDisposition.READY_D0)
        self.assertFalse(result.gate10)

    def test_unknown_added_node_rejected(self):
        with self.assertRaises(ValueError):
            execute_probe_program(
                {"a", "b"}, set(), [ProbeStep(("a", "b"), add_edges=(("a", "x"),))])

    def test_program_root_stable(self):
        program = [ProbeStep(("a", "b"), add_edges=(("b", "c"),))]
        self.assertEqual(program_root(program), program_root(program))

    def test_random_topology_matches_independent_bfs(self):
        rng = random.Random(909)
        for _ in range(500):
            count = rng.randint(2, 9)
            nodes = {str(i) for i in range(count)}
            possible = [(str(i), str(j)) for i in range(count) for j in range(i + 1, count)]
            edges = {edge for edge in possible if rng.random() < .25}
            expected = set(edge_set(edges))
            program = []
            for _ in range(rng.randint(0, 6)):
                observed = rng.choice(possible)
                adds = tuple(edge for edge in rng.sample(possible, k=min(len(possible), rng.randint(0, 2)))
                             if rng.random() < .5)
                removes = tuple(edge for edge in rng.sample(possible, k=min(len(possible), rng.randint(0, 2)))
                                if rng.random() < .5)
                consume = rng.random() < .2
                program.append(ProbeStep(observed, adds, removes, consume))
                for edge in removes:
                    expected.discard(norm_edge(edge))
                if consume:
                    expected.discard(norm_edge(observed))
                for edge in adds:
                    expected.add(norm_edge(edge))
            actual = execute_probe_program(nodes, edges, program).post_partition
            adjacency = {node: set() for node in nodes}
            for a, b in expected:
                adjacency[a].add(b); adjacency[b].add(a)
            seen, parts = set(), []
            for root in sorted(nodes):
                if root in seen:
                    continue
                stack, component = [root], []
                seen.add(root)
                while stack:
                    node = stack.pop(); component.append(node)
                    for neighbor in adjacency[node]:
                        if neighbor not in seen:
                            seen.add(neighbor); stack.append(neighbor)
                parts.append(tuple(sorted(component)))
            self.assertEqual(actual, tuple(sorted(parts)))

    def test_random_zone_matches_bellman_ford(self):
        rng = random.Random(910)
        for _ in range(1000):
            count = rng.randint(2, 7)
            names = tuple(str(i) for i in range(count))
            constraints, edges = [], []
            for _ in range(rng.randint(0, 15)):
                left, right, bound = rng.choice(names), rng.choice(names), rng.randint(-9, 12)
                constraints.append(DifferenceConstraint(left, right, bound))
                edges.append((names.index(right), names.index(left), bound))
            zone = compile_zone(names, constraints)
            distance = [0] * count
            for _ in range(count - 1):
                changed = False
                for a, b, weight in edges:
                    if distance[b] > distance[a] + weight:
                        distance[b] = distance[a] + weight; changed = True
                if not changed:
                    break
            negative_cycle = any(distance[b] > distance[a] + weight for a, b, weight in edges)
            self.assertEqual(zone.disposition is ZoneDisposition.HOLD_INCONSISTENT, negative_cycle)


if __name__ == "__main__":
    unittest.main()
