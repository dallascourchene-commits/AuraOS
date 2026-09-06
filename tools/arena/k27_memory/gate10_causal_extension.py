from __future__ import annotations

from itertools import product
from pathlib import Path
import json
import tempfile
import sys

ARENA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ARENA))

from k27_memory import FrameAddress, MemoryConflict, MemoryStore, StaleMemory
from consequence_admission_kernel import (
    AdmissionInput, AdmissionPolicy, AxisState, ConsequenceAdmissionKernel,
    ConsequenceVector, Decision, SourceExit,
)

SCHEMA = "AURA-K27-GATE10-CAUSAL-EXTENSION-v1"


def store_root_guard_probe(rounds: int = 750) -> dict:
    if type(rounds) is not int or rounds <= 0:
        raise ValueError("rounds must be a positive exact int")
    holds = violations = wrong_holds = 0
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "causal.sqlite"
        with MemoryStore(path) as store:
            store.register_frame("f", "g", expected_generation=None)
            store.publish("guard", {"v": 1}, FrameAddress("f", "g", (1,), "guard"), source_url="u", source_version="1")
            store.publish("tick", {"v": 1}, FrameAddress("f", "g", (2,), "tick"), source_url="u", source_version="1")
        for _ in range(rounds):
            with MemoryStore(path) as store:
                guard_now = store.get("guard")
                tick_now = store.get("tick")
                stale_root = store.state_root()
                store.publish(
                    "tick", {"v": 1}, FrameAddress("f", "g", (2,), "tick"), source_url="u", source_version="1",
                    expected_revision=tick_now["revision_id"], expected_epoch=tick_now["epoch"], expected_store_root=stale_root,
                )
                # guard revision+epoch remain current. The only deliberately stale input is whole-store root.
                try:
                    store.publish(
                        "guard", {"v": 1}, FrameAddress("f", "g", (1,), "guard"), source_url="u", source_version="1",
                        expected_revision=guard_now["revision_id"], expected_epoch=guard_now["epoch"], expected_store_root=stale_root,
                    )
                    violations += 1
                except MemoryConflict:
                    holds += 1
                except StaleMemory:
                    wrong_holds += 1
    return {
        "rounds": rounds,
        "store_root_guard_probes": rounds,
        "store_root_guard_holds": holds,
        "store_root_guard_violations": violations,
        "store_root_guard_wrong_holds": wrong_holds,
    }


def routing_nonhard_sweep() -> dict:
    kernel = ConsequenceAdmissionKernel()
    policy = AdmissionPolicy("gate10-causal-routing-v1", tuple(range(8)), ())
    source = SourceExit("campaign", "arena-gate10", "causal-v1", "semantic-root", True)
    vectors = decision_variations = unknown_repairs = ready_tail_keepers = 0
    tails = tuple(product((0, 1, 2), repeat=5))
    for axes in product((1, 2), repeat=8):
        omega = tuple(AxisState(v) for v in axes)
        baseline = None
        ready_state = all(v == 2 for v in axes)
        for tail in tails:
            decision = kernel.assess(
                AdmissionInput("GATE10_CAUSAL", ConsequenceVector(omega, tail), policy, source)
            ).decision
            vectors += 1
            if baseline is None:
                baseline = decision
            elif decision != baseline:
                decision_variations += 1
            if ready_state:
                if decision == Decision.READY_NONAUTHORIZING:
                    ready_tail_keepers += 1
                else:
                    decision_variations += 1
            elif decision == Decision.READY_NONAUTHORIZING:
                unknown_repairs += 1
    return {
        "routing_nonhard_vectors_checked": vectors,
        "routing_decision_variations": decision_variations,
        "routing_unknown_repairs": unknown_repairs,
        "routing_ready_tail_keepers": ready_tail_keepers,
    }


def run() -> dict:
    guard = store_root_guard_probe()
    routing = routing_nonhard_sweep()
    return {
        "schema": SCHEMA,
        **guard,
        **routing,
        "truth_authority": False,
        "currentness_authority": False,
        "effect_authority": False,
        "gate10": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
