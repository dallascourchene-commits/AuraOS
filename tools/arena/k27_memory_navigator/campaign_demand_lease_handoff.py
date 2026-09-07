from __future__ import annotations

"""Deterministic D0 campaign for configuration-bound demand-cell lease handoff."""

from hashlib import sha256
import json
import random

try:
    from .demand_lease_handoff import (
        ConfigurationTransition,
        DemandCellLease,
        DemandCellState,
        LeaseDisposition,
        ResourceFenceReceipt,
        TransitionAuthorityEvidence,
        TransitionVerificationContext,
        apply_configuration_transition,
        compile_write,
        dependency_closed_invalidation,
    )
except ImportError:  # direct-script execution from this directory
    from demand_lease_handoff import (
        ConfigurationTransition,
        DemandCellLease,
        DemandCellState,
        LeaseDisposition,
        ResourceFenceReceipt,
        TransitionAuthorityEvidence,
        TransitionVerificationContext,
        apply_configuration_transition,
        compile_write,
        dependency_closed_invalidation,
    )


def _root(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def _oracle(lease: DemandCellLease, cell: DemandCellState, now: int) -> bool:
    return (
        lease.cell_id == cell.cell_id
        and now < lease.expires_at
        and lease.revision == cell.revision
        and lease.configuration_root == cell.configuration_root
        and lease.support_epoch == cell.support_epoch
        and lease.fence_generation == cell.fence_generation
        and lease.fence_generation == cell.highest_accepted_fence
    )


def _naive_expiry_only(lease: DemandCellLease, cell: DemandCellState, now: int) -> bool:
    return lease.cell_id == cell.cell_id and now < lease.expires_at


def _transition_receipts(transition: ConfigurationTransition, valid: bool):
    authority_source = _root("authority-source")
    verifier = _root("verifier")
    observer = _root("resource-observer")
    good_resource = ResourceFenceReceipt(
        transition.cell_id,
        transition.new_configuration_root,
        transition.new_support_epoch,
        transition.new_fence_generation,
        "0" * 64,
        observer,
    )
    resource = ResourceFenceReceipt(
        good_resource.cell_id,
        good_resource.configuration_root,
        good_resource.support_epoch,
        good_resource.installed_fence_generation,
        good_resource.canonical_state_root(),
        observer,
    )
    evidence = TransitionAuthorityEvidence(
        transition.canonical_claim_root() if valid else _root("wrong-claim"),
        authority_source,
        verifier,
    )
    verification = TransitionVerificationContext(
        authority_source,
        verifier,
        resource.resource_state_root,
        observer,
    )
    return evidence, resource, verification


def run(seed: int = 541002, cases: int = 12000) -> dict[str, object]:
    rng = random.Random(seed)
    counters = {
        "cases": cases,
        "oracle_ready": 0,
        "oracle_hold": 0,
        "naive_false_ready": 0,
        "compiler_false_ready": 0,
        "compiler_false_hold": 0,
        "transition_ready": 0,
        "transition_hold": 0,
        "unsupported_transition_false_ready": 0,
        "invalidation_oracle_mismatches": 0,
        "selective_invalidation_units": 0,
        "global_invalidation_units": 0,
    }

    for i in range(cases):
        cfg_a = _root(f"cfg-a-{i % 31}")
        cfg_b = _root(f"cfg-b-{i % 37}")
        base = DemandCellState("cell", 4, cfg_a, 10, 21, 21)
        lease = DemandCellLease("cell", 4, cfg_a, 10, 21, "old", 100)
        mode = i % 9
        if mode == 0:
            current, now = base, 50
        elif mode == 1:
            current, now = DemandCellState("cell", 5, cfg_a, 10, 21, 21), 50
        elif mode == 2:
            current, now = DemandCellState("cell", 4, cfg_b, 11, 22, 22), 50
        elif mode == 3:
            current, now = DemandCellState("cell", 4, cfg_a, 11, 22, 22), 50
        elif mode == 4:
            current, now = DemandCellState("cell", 4, cfg_a, 10, 22, 22), 50
        elif mode == 5:
            current, now = base, 100
        elif mode == 6:
            current, now = DemandCellState("cell", 4, cfg_b, 11, 22, 22), 99
        elif mode == 7:
            current, now = base, 99
        else:
            current = DemandCellState("cell", 4, cfg_a, 10, 22, 21)
            lease = DemandCellLease("cell", 4, cfg_a, 10, 22, "new", 100)
            now = 50

        expected = _oracle(lease, current, now)
        actual = compile_write(lease, current, now).disposition is LeaseDisposition.READY_D0
        naive = _naive_expiry_only(lease, current, now)
        counters["oracle_ready" if expected else "oracle_hold"] += 1
        counters["naive_false_ready"] += int(naive and not expected)
        counters["compiler_false_ready"] += int(actual and not expected)
        counters["compiler_false_hold"] += int(expected and not actual)

        transition = ConfigurationTransition("cell", cfg_a, cfg_b, 10, 11, 22)
        valid = i % 5 != 0
        evidence, resource, verification = _transition_receipts(transition, valid)
        decision, _ = apply_configuration_transition(base, transition, evidence, resource, verification)
        transition_ready = decision.disposition is LeaseDisposition.READY_D0
        counters["transition_ready" if transition_ready else "transition_hold"] += 1
        counters["unsupported_transition_false_ready"] += int((not valid) and transition_ready)

        width = 128
        source = f"c-{rng.randrange(width)}"
        mutable_edges: dict[str, set[str]] = {}
        for n in range(width):
            dependency = f"c-{n}"
            if n + 1 < width and rng.random() < 0.12:
                mutable_edges.setdefault(f"c-{n + 1}", set()).add(dependency)
            if n + 7 < width and rng.random() < 0.025:
                mutable_edges.setdefault(f"c-{n + 7}", set()).add(dependency)
        edges = {dependent: frozenset(dependencies) for dependent, dependencies in mutable_edges.items()}
        actual_cone = dependency_closed_invalidation(frozenset({source}), edges)

        # Independent fixed-point oracle over dependent -> dependencies.
        expected_cone = {source}
        changed = True
        while changed:
            changed = False
            for dependent, dependencies in edges.items():
                if dependent not in expected_cone and dependencies & expected_cone:
                    expected_cone.add(dependent)
                    changed = True
        counters["invalidation_oracle_mismatches"] += int(actual_cone != frozenset(expected_cone))
        counters["selective_invalidation_units"] += len(actual_cone)
        counters["global_invalidation_units"] += width

    encoded = json.dumps(counters, sort_keys=True, separators=(",", ":")).encode()
    result = {
        "schema": "aura.astra.o10.demand_lease_handoff.campaign.v2",
        "seed": seed,
        **counters,
        "campaign_root": sha256(encoded).hexdigest(),
        "authority": "D0_NONPROMOTING_GATE10_FALSE",
    }
    if (counters["compiler_false_ready"] or counters["compiler_false_hold"]
            or counters["unsupported_transition_false_ready"] or counters["invalidation_oracle_mismatches"]):
        raise AssertionError(result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))
