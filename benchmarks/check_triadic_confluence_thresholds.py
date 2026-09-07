"""Fail-closed structural thresholds for the D0 Triadic Confluence benchmark."""
import json
import math
import sys


def main(path: str) -> int:
    with open(path, "r", encoding="utf-8") as f:
        r = json.load(f)
    required = {
        "cases", "surface_only_cases", "collapsed_noop_attempts",
        "naive_durable_generations", "confluence_durable_generations",
        "generation_ratio", "serialized_byte_ratio", "holds",
    }
    if set(r) < required:
        raise SystemExit("missing benchmark fields")
    for name in ("generation_ratio", "serialized_byte_ratio"):
        v = r[name]
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            raise SystemExit(f"non-finite/invalid {name}")
    if r["cases"] < 10_000:
        raise SystemExit("campaign too small")
    if r["holds"] != 0:
        raise SystemExit("unexpected HOLD in compatible/no-op benchmark")
    if r["collapsed_noop_attempts"] != r["surface_only_cases"]:
        raise SystemExit("surface-only refinement escaped collapse")
    if r["generation_ratio"] > 0.002:
        raise SystemExit("durable-generation structural reduction floor missed")
    if r["serialized_byte_ratio"] > 0.002:
        raise SystemExit("serialized semantic-state structural reduction floor missed")
    print("triadic-confluence structural thresholds: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
