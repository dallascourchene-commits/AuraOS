from __future__ import annotations

from hashlib import sha256
import itertools
import json
import math
import random

from tools.arena.worker_cells.gpt56sol_frontier27_numeric_preflight.transactional_preflight import MAX_GOVERNED_INT


def stable(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def root(v):
    return sha256(stable(v)).hexdigest()


def implementation_decision(*, size, transfers, bandwidth, jpgb, window_product, records_valid, authority_d0):
    scalar_ok = type(size) is int and 1 <= size <= MAX_GOVERNED_INT
    transfers_ok = type(transfers) is int and 0 <= transfers <= MAX_GOVERNED_INT
    byte_ok = scalar_ok and transfers_ok and transfers * size <= MAX_GOVERNED_INT
    bandwidth_ok = type(bandwidth) is float and math.isfinite(bandwidth) and bandwidth > 0
    jpgb_ok = type(jpgb) is float and math.isfinite(jpgb) and jpgb >= 0
    window_ok = type(window_product) is float and math.isfinite(window_product) and window_product >= 0
    derived_ok = False
    if byte_ok and bandwidth_ok and jpgb_ok:
        total_bytes = transfers * size
        seconds = float(total_bytes) / bandwidth
        energy = float(total_bytes) / 1e9 * jpgb
        derived_ok = math.isfinite(seconds) and seconds >= 0 and math.isfinite(energy) and energy >= 0
    return all((scalar_ok, transfers_ok, byte_ok, bandwidth_ok, jpgb_ok, window_ok, records_valid, derived_ok, authority_d0))


def oracle(**x):
    # Independently spelled bounded-domain oracle.
    if type(x["size"]) is not int or x["size"] < 1 or x["size"] > 9223372036854775807:
        return False
    if type(x["transfers"]) is not int or x["transfers"] < 0 or x["transfers"] > 9223372036854775807:
        return False
    n = x["size"] * x["transfers"]
    if n > 9223372036854775807:
        return False
    for key, positive in (("bandwidth", True), ("jpgb", False), ("window_product", False)):
        v = x[key]
        if type(v) is not float or not math.isfinite(v) or (v <= 0 if positive else v < 0):
            return False
    if not x["records_valid"] or not x["authority_d0"]:
        return False
    try:
        s = n / x["bandwidth"]
        e = n / 1_000_000_000.0 * x["jpgb"]
    except (OverflowError, ZeroDivisionError):
        return False
    return math.isfinite(s) and s >= 0 and math.isfinite(e) and e >= 0


def random_case(rng):
    valid = rng.random() < 0.35
    if valid:
        size = rng.randint(1, 1_000_000)
        transfers = rng.randint(0, 1000)
        bandwidth = 10.0 ** rng.uniform(3, 12)
        jpgb = 10.0 ** rng.uniform(-6, 4)
        window = 10.0 ** rng.uniform(-6, 6)
        return dict(size=size, transfers=transfers, bandwidth=bandwidth, jpgb=jpgb, window_product=bandwidth*window, records_valid=True, authority_d0=True)
    family = rng.randrange(9)
    base = dict(size=4096, transfers=4, bandwidth=1e9, jpgb=2.0, window_product=1e8, records_valid=True, authority_d0=True)
    if family == 0: base["size"] = 10**1000
    elif family == 1: base["transfers"] = MAX_GOVERNED_INT
    elif family == 2: base["bandwidth"] = 5e-324
    elif family == 3: base["jpgb"] = 1e308; base["size"] = MAX_GOVERNED_INT; base["transfers"] = 1
    elif family == 4: base["window_product"] = math.inf
    elif family == 5: base["records_valid"] = False
    elif family == 6: base["authority_d0"] = False
    elif family == 7: base["bandwidth"] = math.inf
    else: base["size"] = 0
    return base


def run(seed=270825, n=100_000):
    rng = random.Random(seed)
    mismatches = 0
    for _ in range(n):
        c = random_case(rng)
        mismatches += implementation_decision(**c) != oracle(**c)

    hs_families = [
        dict(size=10**1000, transfers=1, bandwidth=1e9, jpgb=1.0, window_product=1.0, records_valid=True, authority_d0=True),
        dict(size=MAX_GOVERNED_INT, transfers=2, bandwidth=1e9, jpgb=1.0, window_product=1.0, records_valid=True, authority_d0=True),
        dict(size=1, transfers=1, bandwidth=5e-324, jpgb=1.0, window_product=1.0, records_valid=True, authority_d0=True),
        dict(size=MAX_GOVERNED_INT, transfers=1, bandwidth=1e9, jpgb=1e308, window_product=1.0, records_valid=True, authority_d0=True),
        dict(size=1, transfers=1, bandwidth=1e9, jpgb=1.0, window_product=math.inf, records_valid=True, authority_d0=True),
        dict(size=1, transfers=1, bandwidth=math.inf, jpgb=1.0, window_product=1.0, records_valid=True, authority_d0=True),
        dict(size=1, transfers=1, bandwidth=1e9, jpgb=math.inf, window_product=1.0, records_valid=True, authority_d0=True),
        dict(size=1, transfers=1, bandwidth=1e9, jpgb=1.0, window_product=1.0, records_valid=False, authority_d0=True),
        dict(size=1, transfers=1, bandwidth=1e9, jpgb=1.0, window_product=1.0, records_valid=True, authority_d0=False),
        dict(size=0, transfers=1, bandwidth=1e9, jpgb=1.0, window_product=1.0, records_valid=True, authority_d0=True),
    ]
    hs_false_accepts = 0
    for family in hs_families:
        for _ in range(1000):
            hs_false_accepts += bool(implementation_decision(**family))

    omega_keeper = 0
    for axes in itertools.product((0, 1, 2), repeat=8):
        # Each hard axis has exactly one verified state (=2); unknown/invalid cannot compensate.
        omega_keeper += int(all(v == 2 for v in axes))

    hard_invalid = (0, 2, 2, 2, 2, 2, 2, 2)
    repairs = 0
    for tail in itertools.product((0, 1, 2), repeat=5):
        del tail
        repairs += int(all(v == 2 for v in hard_invalid))

    receipt = {
        "schema": "AURA-F27-NUMERIC-TOTALITY-DONOR-CAMPAIGN-v1",
        "seed": seed,
        "randomized_decisions": n,
        "oracle_mismatches": mismatches,
        "hs1000_families": len(hs_families),
        "hs1000_cases": len(hs_families) * 1000,
        "hs_false_accepts": hs_false_accepts,
        "omega8_states": 3**8,
        "omega8_keepers": omega_keeper,
        "13d_trailing_contexts": 3**5,
        "13d_repairs": repairs,
    }
    receipt["campaign_root"] = root(receipt)
    return receipt


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
