from __future__ import annotations

import hashlib
import json
import random

from .reflexive_topology import ProbeStep, components, execute_probe_program
from .route_evidence_transaction import TransactionDisposition, certify
from .temporal_zone import DifferenceConstraint, ZoneDisposition, compile_zone


def run(seed=9099, cases=20000):
    rng = random.Random(seed)
    oracle_mismatches = 0
    naive_pre_partition_wrong = 0
    inconsistent_zones = 0
    ready = 0
    rows = []
    for _ in range(cases):
        count = rng.randint(2, 10)
        nodes = {str(i) for i in range(count)}
        possible = [(str(i), str(j)) for i in range(count) for j in range(i + 1, count)]
        edges = {edge for edge in possible if rng.random() < .2}
        pre_partition = components(nodes, edges)
        program = []
        for _ in range(rng.randint(0, 5)):
            observed = rng.choice(possible)
            adds = (rng.choice(possible),) if rng.random() < .25 else ()
            removes = (rng.choice(possible),) if rng.random() < .25 else ()
            program.append(ProbeStep(observed, adds, removes, rng.random() < .1))
        topology = execute_probe_program(nodes, edges, program)
        naive_pre_partition_wrong += pre_partition != topology.post_partition

        names = ("event", "valid", "phase", "sim", "commit", "external")
        constraints = [DifferenceConstraint(
            rng.choice(names), rng.choice(names), rng.randint(-5, 12))
            for _ in range(rng.randint(1, 10))]
        zone = compile_zone(names, constraints)
        inconsistent_zones += zone.disposition is ZoneDisposition.HOLD_INCONSISTENT
        transaction = certify(topology, zone)
        ready += transaction.disposition is TransactionDisposition.READY_D0
        if ((transaction.disposition is TransactionDisposition.READY_D0)
                != (zone.disposition is ZoneDisposition.READY_D0)):
            oracle_mismatches += 1
        rows.append((
            topology.pre_root, topology.program_root, topology.post_root,
            zone.disposition.value, transaction.disposition.value,
        ))

    root = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    result = {
        "cases": cases,
        "oracle_mismatches": oracle_mismatches,
        "naive_pre_partition_wrong": naive_pre_partition_wrong,
        "inconsistent_zones": inconsistent_zones,
        "ready": ready,
        "campaign_root": root,
        "authority_minted": False,
        "effect_authority": False,
        "gate10": False,
    }
    if oracle_mismatches:
        raise AssertionError(result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
