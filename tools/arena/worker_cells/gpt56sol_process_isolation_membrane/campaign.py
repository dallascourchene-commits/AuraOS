from itertools import product
import json
import os
import random
from hashlib import sha256
from types import ModuleType, SimpleNamespace
import sys

from process_isolation_membrane import *


def main():
    rng = random.Random(20260905_844)
    false_parent_admit = 0
    for i in range(1000):
        module = ModuleType(f"_aura_attack_{i}")
        sys.modules[module.__name__] = module
        try:
            try:
                require_patch_isolation(module)
                false_parent_admit += 1
            except ProcessIsolationRequiredError:
                pass
        finally:
            sys.modules.pop(module.__name__, None)

    private_mismatch = 0
    for _ in range(100000):
        obj = SimpleNamespace()
        got = patch_isolation_state(obj)
        private_mismatch += int(got != "PRIVATE_MODULE")

    rpc_mismatch = 0
    worker_pid = None
    worker_receipt_valid = False
    with DedicatedProcessService.start("process_isolation_membrane:IsolationProbe") as service:
        worker_pid = service.worker_pid
        worker_receipt_valid = (
            service.receipt.worker_pid == worker_pid
            and service.receipt.parent_pid == os.getpid()
            and service.receipt.authority_ceiling == "D0_PROCESS_ISOLATION_ONLY"
            and len(service.receipt.worker_nonce_root) == 64
            and len(service.receipt.factory_identity_root) == 64
            and len(service.receipt.factory_module_bytes_root) == 64
            and service.receipt.verify()
            and len(service.receipt.receipt_root) == 64
        )
        state, pid, aliases = service.call("isolation_state")
        rpc_mismatch += int(state != "DEDICATED_PROCESS")
        rpc_mismatch += int(pid == os.getpid())
        rpc_mismatch += int(not aliases)
        expected = 0
        for _ in range(1000):
            step = rng.randrange(-3, 4)
            expected += step
            value, pid = service.call("increment", step)
            rpc_mismatch += int(value != expected or pid != worker_pid)


    # Implementation-currentness oracle: same textual factory name is not enough.
    baseline_identity = factory_identity_for_spec("process_isolation_membrane:IsolationProbe")
    factory_currentness_cases = 100000
    factory_currentness_mismatches = 0
    for i in range(factory_currentness_cases):
        exact = (i % 4 == 0)
        if exact:
            candidate = baseline_identity
            expected = "EXACT"
        else:
            root = sha256(f"factory-generation-{i}".encode()).hexdigest()
            if root == baseline_identity.module_bytes_root:
                root = sha256(f"factory-generation-alt-{i}".encode()).hexdigest()
            candidate = FactoryIdentity.mint(
                factory_spec=baseline_identity.factory_spec,
                module_bytes_root=root,
            )
            expected = "HOLD"
        got = factory_identity_currentness(baseline_identity, candidate)
        factory_currentness_mismatches += int(got != expected)

    factory_hs1000_false_exact = 0
    for i in range(1000):
        root = sha256(f"hs1000-stale-factory-{i}".encode()).hexdigest()
        if root == baseline_identity.module_bytes_root:
            root = sha256(f"hs1000-stale-factory-alt-{i}".encode()).hexdigest()
        stale = FactoryIdentity.mint(
            factory_spec=baseline_identity.factory_spec,
            module_bytes_root=root,
        )
        factory_hs1000_false_exact += int(
            factory_identity_currentness(baseline_identity, stale) == "EXACT"
        )

    omega_admits = sum(omega8_admit(s) for s in product(range(3), repeat=8))
    hard_invalid_repairs = 0
    seen_context5 = set()
    keeper = (2,2,2,2,2,2,2,2,1,2,2,2,2)
    for _ in range(100000):
        state = tuple(rng.randrange(3) for _ in range(13))
        seen_context5.add(state[-5:])
        if state != keeper and admit13(state):
            hard_invalid_repairs += 1

    result = {
        "parent_registered_module_attacks": 1000,
        "false_parent_patch_admissions": false_parent_admit,
        "private_policy_cases": 100000,
        "private_policy_mismatches": private_mismatch,
        "worker_rpc_cases": 1000,
        "worker_rpc_mismatches": rpc_mismatch,
        "worker_pid_distinct": worker_pid != os.getpid(),
        "worker_receipt_valid": worker_receipt_valid,
        "factory_currentness_cases": factory_currentness_cases,
        "factory_currentness_mismatches": factory_currentness_mismatches,
        "factory_hs1000_cases": 1000,
        "factory_hs1000_false_exact": factory_hs1000_false_exact,
        "factory_identity_root": baseline_identity.identity_root,
        "factory_module_bytes_root": baseline_identity.module_bytes_root,
        "omega8_states": 3**8,
        "omega8_admits": omega_admits,
        "states13_sampled": 100000,
        "context5_roots_seen": len(seen_context5),
        "hard_invalid_13d_repairs": hard_invalid_repairs,
        "claim_ceiling": "D0_PROCESS_ISOLATION_ONLY",
    }
    result["campaign_root"] = sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
