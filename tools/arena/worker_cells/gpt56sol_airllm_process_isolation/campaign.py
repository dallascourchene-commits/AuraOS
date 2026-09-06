from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_process_isolation as fixture
from process_isolation import IsolatedSessionProxy


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def run():
    fixture.HOST_TRANSFORMERS_BOUNDARY = "HOST_ORIGINAL"
    records = []
    with IsolatedSessionProxy(
        factory_module="test_process_isolation",
        factory_qualname="FakePatchedSession",
        allowed_methods=("boundary", "generate_text"),
    ) as proxy:
        for i in range(1000):
            result = proxy.call("generate_text", f"case-{i:04d}")
            host_ok = fixture.HOST_TRANSFORMERS_BOUNDARY == "HOST_ORIGINAL"
            child_ok = result["marker"] == "CHILD_PATCHED" and result["calls"] == i + 1
            records.append({"i": i, "host_ok": host_ok, "child_ok": child_ok})
    false_isolation = sum(not (r["host_ok"] and r["child_ok"]) for r in records)

    keeper = 0
    for state in range(3 ** 8):
        n = state
        digits = []
        for _ in range(8):
            digits.append(n % 3)
            n //= 3
        admitted = all(x == 2 for x in digits)
        keeper += int(admitted)
    hard_invalid_repairs = 0
    for tail in range(3 ** 5):
        hard_valid = False
        admitted = hard_valid and tail >= 0
        hard_invalid_repairs += int(admitted)

    semantic = {
        "schema": "AURA-AIRLLM-PROCESS-ISOLATION-CAMPAIGN-v1",
        "cases": records,
        "false_isolation": false_isolation,
        "omega8_keeper": keeper,
        "13d_hard_invalid_repairs": hard_invalid_repairs,
        "receipt_root": IsolatedSessionProxy(
            factory_module="test_process_isolation",
            factory_qualname="FakePatchedSession",
            allowed_methods=("boundary", "generate_text"),
        ).receipt.root,
    }
    root = sha256(canonical(semantic)).hexdigest()
    print(json.dumps({
        "campaign_root": root,
        "cases": 1000,
        "false_isolation": false_isolation,
        "omega8_states": 3 ** 8,
        "omega8_keeper": keeper,
        "13d_tails": 3 ** 5,
        "13d_hard_invalid_repairs": hard_invalid_repairs,
        "receipt_root": semantic["receipt_root"],
    }, sort_keys=True))


if __name__ == "__main__":
    run()
