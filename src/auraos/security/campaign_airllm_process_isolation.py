from __future__ import annotations

from hashlib import sha256
import json
import os

from airllm_process_isolation import IsolatedObjectProxy, RemoteInvocationError
from test_airllm_process_isolation import FakeBoundary


def canonical_root(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return sha256(raw).hexdigest()


def run_campaign():
    parent_cases = 100_000
    child_reject_cases = 1_000
    child_keep_cases = 1_000
    parent_mismatches = 0
    child_false_admissions = 0
    child_false_rejects = 0
    trust_values = (True, None, "yes", 1, False)

    with IsolatedObjectProxy(
        "test_airllm_process_isolation",
        "IsolatedPatchedTarget",
        timeout_seconds=10.0,
    ) as proxy:
        if proxy.receipt.parent_pid != os.getpid() or proxy.receipt.child_pid == os.getpid():
            raise AssertionError("process identity isolation failed")

        for i in range(parent_cases):
            requested = trust_values[i % len(trust_values)]
            result = FakeBoundary.from_pretrained("unrelated", trust_remote_code=requested)
            if result["pid"] != os.getpid() or result["trust_remote_code"] != requested:
                parent_mismatches += 1

        for _ in range(child_reject_cases):
            try:
                proxy.call("probe", True)
            except RemoteInvocationError:
                pass
            else:
                child_false_admissions += 1

        for _ in range(child_keep_cases):
            try:
                result = proxy.call("probe", False)
            except RemoteInvocationError:
                child_false_rejects += 1
            else:
                if (
                    result["trust_remote_code"] is not False
                    or result["pid"] != proxy.receipt.child_pid
                ):
                    child_false_rejects += 1

        semantic = {
            "schema": "AURA-AIRLLM-PROCESS-ISOLATION-CAMPAIGN-v1",
            "start_method": proxy.receipt.start_method,
            "parent_cases": parent_cases,
            "parent_mismatches": parent_mismatches,
            "child_reject_cases": child_reject_cases,
            "child_false_admissions": child_false_admissions,
            "child_keep_cases": child_keep_cases,
            "child_false_rejects": child_false_rejects,
        }

    semantic["campaign_root"] = canonical_root(semantic)
    return semantic


if __name__ == "__main__":
    print(json.dumps(run_campaign(), sort_keys=True, separators=(",", ":")))
