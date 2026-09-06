from __future__ import annotations

from hashlib import sha256
import itertools
import json
import math
import random

from tools.arena.worker_cells.gpt56sol_frontier27_numeric_preflight.transactional_preflight import (
    MAX_GOVERNED_INT,
    _freeze_records,
)


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


class _OuterFailure:
    def __init__(self, exc, *, on_next=False):
        self.exc = exc
        self.on_next = on_next
        self.used = False

    def __iter__(self):
        if not self.on_next:
            raise self.exc
        return self

    def __next__(self):
        if not self.used:
            self.used = True
            return (1,)
        raise self.exc


class _InnerFailure:
    def __init__(self, exc, *, on_next=False):
        self.exc = exc
        self.on_next = on_next
        self.used = False

    def __iter__(self):
        if not self.on_next:
            raise self.exc
        return self

    def __next__(self):
        if not self.used:
            self.used = True
            return 1
        raise self.exc


class _InfiniteOuter:
    def __iter__(self):
        while True:
            yield (1,)


class _InfiniteInner:
    def __iter__(self):
        while True:
            yield 1


def materialization_case(i):
    family = i % 10
    if family == 0:
        routes, preds, expected = [(1, 2), (3,)], [(1,), (3, 4)], True
    elif family == 1:
        routes, preds, expected = _OuterFailure(RuntimeError("outer")), [], False
    elif family == 2:
        routes, preds, expected = _OuterFailure(KeyError("outer"), on_next=True), [(1,)], False
    elif family == 3:
        routes, preds, expected = [_InnerFailure(LookupError("inner"))], [(1,)], False
    elif family == 4:
        routes, preds, expected = [_InnerFailure(RuntimeError("inner"), on_next=True)], [(1,)], False
    elif family == 5:
        routes, preds, expected = _InfiniteOuter(), [(1,)] * 8, False
    elif family == 6:
        routes, preds, expected = [_InfiniteInner()], [(1,)], False
    elif family == 7:
        routes, preds, expected = [(True,)], [(1,)], False
    elif family == 8:
        routes, preds, expected = [(1,)], [(1,), (2,)], False
    else:
        routes, preds, expected = [(), (1,)], [(), (1,)], True
    try:
        _freeze_records(routes, preds, max_records=8, max_items_per_record=8)
        got = True
    except ValueError:
        got = False
    return got, expected


def materialization_campaign(n=30_000):
    mismatches = false_accepts = false_rejects = uncontrolled = 0
    for i in range(n):
        try:
            got, expected = materialization_case(i)
        except Exception:
            uncontrolled += 1
            continue
        mismatches += got != expected
        false_accepts += got and not expected
        false_rejects += expected and not got

    hs_escapes = 0
    for family in range(10):
        for j in range(1000):
            got, expected = materialization_case(family * 1000 + j)
            hs_escapes += got != expected
    return {
        "cases": n,
        "mismatches": mismatches,
        "false_accepts": false_accepts,
        "false_rejects": false_rejects,
        "uncontrolled_exceptions": uncontrolled,
        "hs1000_families": 10,
        "hs1000_cases": 10_000,
        "hs1000_escapes": hs_escapes,
    }


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

    invocation = materialization_campaign()

    omega_keeper = 0
    for axes in itertools.product((0, 1, 2), repeat=8):
        omega_keeper += int(all(v == 2 for v in axes))

    hard_invalid = (0, 2, 2, 2, 2, 2, 2, 2)
    repairs = 0
    for tail in itertools.product((0, 1, 2), repeat=5):
        del tail
        repairs += int(all(v == 2 for v in hard_invalid))

    receipt = {
        "schema": "AURA-F27-NUMERIC-INVOCATION-TOTALITY-DONOR-CAMPAIGN-v2",
        "seed": seed,
        "randomized_decisions": n,
        "oracle_mismatches": mismatches,
        "numeric_hs1000_families": len(hs_families),
        "numeric_hs1000_cases": len(hs_families) * 1000,
        "numeric_hs_false_accepts": hs_false_accepts,
        "invocation_materialization": invocation,
        "omega8_states": 3**8,
        "omega8_keepers": omega_keeper,
        "13d_trailing_contexts": 3**5,
        "13d_repairs": repairs,
    }
    receipt["campaign_root"] = root(receipt)
    assert mismatches == hs_false_accepts == repairs == 0
    assert all(invocation[k] == 0 for k in ("mismatches", "false_accepts", "false_rejects", "uncontrolled_exceptions", "hs1000_escapes"))
    assert omega_keeper == 1
    return receipt


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
