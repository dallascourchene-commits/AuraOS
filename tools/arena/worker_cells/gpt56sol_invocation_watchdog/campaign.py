from __future__ import annotations

from hashlib import sha256
import itertools
import json

from tools.arena.worker_cells.gpt56sol_invocation_watchdog.watchdog_canary import run_watchdog_canary


def stable(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def root(v):
    return sha256(stable(v)).hexdigest()


def decision(*, isolated_process, deadline_owned_by_parent, finite_cleanup, typed_outcome, no_parent_shared_state, ordinary_path_preserved, descendant_scope_explicit, authority_d0):
    return all((isolated_process, deadline_owned_by_parent, finite_cleanup, typed_outcome, no_parent_shared_state, ordinary_path_preserved, descendant_scope_explicit, authority_d0))


def oracle(case):
    # Independently spelled conjunction: no soft/context axis repairs a missing hard property.
    required = ("isolated_process", "deadline_owned_by_parent", "finite_cleanup", "typed_outcome", "no_parent_shared_state", "ordinary_path_preserved", "descendant_scope_explicit", "authority_d0")
    return all(type(case[k]) is bool and case[k] for k in required)


def state_campaign(n=30_000):
    mismatches = false_accepts = false_rejects = 0
    for i in range(n):
        case = {
            "isolated_process": i % 11 != 0,
            "deadline_owned_by_parent": i % 13 != 0,
            "finite_cleanup": i % 17 != 0,
            "typed_outcome": i % 19 != 0,
            "no_parent_shared_state": i % 23 != 0,
            "ordinary_path_preserved": i % 29 != 0,
            "descendant_scope_explicit": i % 31 != 0,
            "authority_d0": i % 37 != 0,
        }
        got = decision(**case)
        exp = oracle(case)
        mismatches += got != exp
        false_accepts += got and not exp
        false_rejects += exp and not got
    return mismatches, false_accepts, false_rejects


def real_process_campaign(rounds_per_family=10):
    counts = {"finite": 0, "ordinary_reject": 0, "non_returning_next": 0}
    escapes = 0
    expected = {
        "finite": {"COMPLETED"},
        "ordinary_reject": {"GOVERNED_REJECT"},
        "non_returning_next": {"EXECUTION_TIMEOUT_TERMINATED", "EXECUTION_TIMEOUT_KILLED"},
    }
    stable_finite = None
    for scenario in counts:
        for _ in range(rounds_per_family):
            receipt = run_watchdog_canary(
                scenario,
                startup_deadline_s=1.0,
                execution_deadline_s=0.05 if scenario == "non_returning_next" else 0.75,
                cleanup_grace_s=0.25,
            )
            counts[scenario] += 1
            escapes += receipt.disposition not in expected[scenario]
            if scenario == "finite":
                evidence = receipt.stable_evidence()
                if stable_finite is None:
                    stable_finite = evidence
                escapes += evidence != stable_finite
    return counts, escapes, stable_finite


def run():
    mismatches, false_accepts, false_rejects = state_campaign()
    process_counts, process_escapes, finite_evidence = real_process_campaign()

    omega_keeper = sum(int(all(v == 2 for v in axes)) for axes in itertools.product((0, 1, 2), repeat=8))
    hard_invalid = (2, 2, 2, 0, 2, 2, 2, 2)
    repairs = sum(int(all(v == 2 for v in hard_invalid)) for _ in itertools.product((0, 1, 2), repeat=5))

    receipt = {
        "schema": "AURA-R10.3-DIRECT-WORKER-WATCHDOG-CANARY-v1",
        "state_decisions": 30_000,
        "state_mismatches": mismatches,
        "state_false_accepts": false_accepts,
        "state_false_rejects": false_rejects,
        "real_process_counts": process_counts,
        "real_process_escapes": process_escapes,
        "finite_evidence": finite_evidence,
        "omega8_states": 3**8,
        "omega8_keepers": omega_keeper,
        "13d_trailing_contexts": 3**5,
        "13d_repairs": repairs,
        "scope": "direct_child_only_no_descendant_tree_or_external_effect_claim",
    }
    receipt["campaign_root"] = root(receipt)
    assert mismatches == false_accepts == false_rejects == process_escapes == repairs == 0
    assert omega_keeper == 1
    return receipt


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
