from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import itertools
import json

from tools.arena.kinetic_audio_multirate_donor import (
    GestureIntentCompiler,
    GestureObservation,
    K27ConstraintProjector,
    K27Coordinate,
    KineticAudioOwner,
    ProjectedMusicalIntent,
    RawGestureIntent,
    classify_currentness_lattice,
    digest,
    replay_root,
    stable,
    synthetic_callback_benchmark,
)

RECIPE = digest("campaign-recipe-v1")
ENGINE = digest("campaign-engine-v1")

FAMILIES = (
    "valid_soft",
    "valid_hard",
    "stale_graph_epoch",
    "stale_timeline_epoch",
    "queue_overflow",
    "low_confidence",
    "control_bounds",
    "control_schema",
    "invalid_k27",
    "stale_projection_basis",
)
DOMAINS = (
    "gesture_gate", "k27_projection", "soft_control", "hard_transition", "audio_clock",
    "queue_recovery", "graph_currentness", "timeline_currentness", "replay_provenance", "authority_boundary",
)
MECHANISMS = (
    "confidence_hysteresis", "constraint_projection", "block_alignment", "phrase_quantization", "fixed_queue",
    "epoch_permit", "immediate_invalidation", "timeline_fence", "deterministic_digest", "fail_closed_schema",
)


def make_owner(*, queue_capacity: int = 16, bpm_milli: int = 180_000, lookahead_blocks: int = 1) -> KineticAudioOwner:
    return KineticAudioOwner(
        recipe_root=RECIPE, engine_root=ENGINE, sample_rate=8_000, block_size=256,
        bpm_milli=bpm_milli, beats_per_bar=1, bars_per_phrase=1,
        queue_capacity=queue_capacity, lookahead_blocks=lookahead_blocks, smoothing_ms=20,
    )


def mk_intent(o: KineticAudioOwner, kind: str, controls, *, gesture: str = "campaign", coord: K27Coordinate | None = None, frame: int = 0, magnitude: int = 500):
    coord = K27Coordinate(1, 1, 1) if coord is None else coord
    controls = tuple(sorted(controls))
    snap = o.snapshot()
    source_digest = digest([gesture, magnitude, coord.code, frame])
    return ProjectedMusicalIntent(
        kind, controls, coord, gesture, magnitude, frame, source_digest,
        snap.graph_generation, snap.mutation_epoch, snap.timeline_epoch, snap.projection_root,
    )


def run_family(family: str, variant: int, severity: int) -> dict:
    coord = K27Coordinate(variant % 3, (variant // 3) % 3, severity % 3)
    frame = variant * 10 + severity
    if family == "valid_soft":
        o = make_owner(); value = min(1000, 50 + variant * 80 + severity * 5)
        r = o.schedule(mk_intent(o, "soft", (("brightness_milli", value),), coord=coord, frame=frame))
        receipts = o.process_until((r.target_sample or 0) + o.block_size) if r.admitted else ()
        applied = sum(len(x.applied) for x in receipts)
        ok = r.admitted and applied == 1 and dict(o.snapshot().soft_controls)["brightness_milli"] == value
        detail = [r.reason, applied, o.snapshot().timeline_epoch]
    elif family == "valid_hard":
        o = make_owner(); value = (variant + severity) % 12
        r = o.schedule(mk_intent(o, "hard", (("scale_index", value),), gesture="rotate", coord=coord, frame=frame))
        receipts = o.process_until((r.target_sample or 0) + o.block_size) if r.admitted else ()
        applied = sum(len(x.applied) for x in receipts)
        ok = r.admitted and applied == 1 and o.snapshot().scale_index == value and o.snapshot().timeline_epoch == 2
        detail = [r.reason, applied, o.snapshot().scale_index]
    elif family == "stale_graph_epoch":
        o = make_owner(queue_capacity=2)
        r = o.schedule(mk_intent(o, "soft", (("density_milli", 600 + variant * 10),), coord=coord, frame=frame))
        wr = o.governed_graph_write(recipe_root=RECIPE)
        fresh = o.schedule(mk_intent(o, "soft", (("width_milli", 500 + severity * 10),), coord=coord, frame=frame + 1))
        ok = r.admitted and wr.invalidated_events == (r.event_id,) and o.queue_depth == 1 and fresh.admitted
        detail = [len(wr.invalidated_events), fresh.reason, wr.snapshot.mutation_epoch]
    elif family == "stale_timeline_epoch":
        o = make_owner(queue_capacity=4)
        a = o.schedule(mk_intent(o, "hard", (("drop_state", (variant + severity) % 2),), gesture="fist", coord=coord, frame=frame))
        b = o.schedule(mk_intent(o, "hard", (("scale_index", (variant + severity) % 12),), gesture="rotate", coord=coord, frame=frame + 1))
        target = max(a.target_sample or 0, b.target_sample or 0)
        receipts = o.process_until(target + o.block_size)
        applied = [x.event_id for br in receipts for x in br.applied]; stale = [x for br in receipts for x in br.held_stale]
        ok = a.admitted and b.admitted and applied == [a.event_id] and stale == [b.event_id] and o.queue_depth == 0
        detail = [len(applied), len(stale), o.snapshot().timeline_epoch]
    elif family == "queue_overflow":
        o = make_owner(queue_capacity=1)
        a = o.schedule(mk_intent(o, "soft", (("width_milli", 300 + variant * 10),), coord=coord, frame=frame))
        b = o.schedule(mk_intent(o, "soft", (("density_milli", 300 + severity * 10),), coord=coord, frame=frame + 1))
        ok = a.admitted and not b.admitted and b.reason == "HOLD_QUEUE_FULL" and o.queue_depth == 1
        detail = [a.reason, b.reason, o.queue_depth]
    elif family == "low_confidence":
        c = GestureIntentCompiler(activation_milli=750, release_milli=550, hold_frames=2); conf = min(749, 500 + variant * 20 + severity)
        a = c.observe(GestureObservation(variant * 2, "open", conf, 500, coord)); b = c.observe(GestureObservation(variant * 2 + 1, "open", conf, 500, coord))
        ok = a is None and b is None; detail = [conf, a is None, b is None]
    elif family == "control_bounds":
        o = make_owner(); bad = 1001 + variant * 10 + severity
        r = o.schedule(mk_intent(o, "soft", (("brightness_milli", bad),), coord=coord, frame=frame))
        ok = not r.admitted and r.reason == "HOLD_CONTROL_BOUNDS" and o.queue_depth == 0; detail = [bad, r.reason]
    elif family == "control_schema":
        o = make_owner(); r = o.schedule(mk_intent(o, "soft", ((f"raw_sample_{variant}_{severity}", 1),), coord=coord, frame=frame))
        ok = not r.admitted and r.reason == "HOLD_CONTROL_SCHEMA" and o.queue_depth == 0; detail = [r.reason, o.queue_depth]
    elif family == "invalid_k27":
        bad = -1 - severity if variant % 2 == 0 else 3 + severity
        try: K27Coordinate(bad, 1, 1)
        except ValueError: ok = True; detail = [bad, "ValueError"]
        else: ok = False; detail = [bad, "accepted"]
    elif family == "stale_projection_basis":
        o = make_owner(); p = K27ConstraintProjector(); snap = o.snapshot()
        raw = RawGestureIntent.build(GestureObservation(variant * 2, "swipe_up", 900, 650 + severity * 10, coord)); projected = p.project(raw, snap)
        o.governed_graph_write(recipe_root=RECIPE); r = o.schedule(projected)
        ok = not r.admitted and r.reason == "HOLD_STALE_PROJECTION" and o.queue_depth == 0; detail = [r.reason, snap.projection_root, o.snapshot().projection_root]
    else:
        raise AssertionError(family)
    return {"family": family, "variant": variant, "severity": severity, "ok": ok, "detail": detail}


def hs1000() -> dict:
    cases = []; mismatches = 0; chain = "0" * 64
    for family in FAMILIES:
        for variant in range(10):
            for severity in range(10):
                row = run_family(family, variant, severity); mismatches += int(not row["ok"])
                capsule = {"domain": DOMAINS[(variant + severity) % 10], "mechanism": MECHANISMS[(variant * 3 + severity) % 10], "falsifier": family, **row}
                chain = digest([chain, capsule]); cases.append(capsule)
    return {"cases": len(cases), "oracle_mismatches": mismatches, "compound_root": chain, "stream_sha256": sha256(b"\n".join(stable(x) for x in cases)).hexdigest()}


def oracle_route(axes: tuple[int, ...]) -> str:
    if 0 in axes: return "HOLD_HARD_INVALID"
    if 1 in axes: return "HOLD_UNKNOWN"
    return "READY"


def omega8_13d() -> dict:
    omega = {"READY": 0, "HOLD_UNKNOWN": 0, "HOLD_HARD_INVALID": 0}; omega_chain = "0" * 64; omega_variations = 0
    for axes in itertools.product(range(3), repeat=8):
        expected = oracle_route(axes); observed = classify_currentness_lattice(axes)
        omega_variations += int(observed != expected); omega[observed] += 1; omega_chain = digest([omega_chain, list(axes), observed])

    hard_repairs = 0; decision_variations = 0; counts = {"READY": 0, "HOLD_UNKNOWN": 0, "HOLD_HARD_INVALID": 0}; chain13 = "0" * 64
    for axes in itertools.product(range(3), repeat=13):
        expected = oracle_route(axes); observed = classify_currentness_lattice(axes)
        counts[observed] += 1
        hard_repairs += int(0 in axes and observed != "HOLD_HARD_INVALID")
        decision_variations += int(observed != expected)
        chain13 = digest([chain13, list(axes), observed])
    return {
        "omega8_states": 3**8, "omega8": omega, "omega8_root": omega_chain, "omega8_routing_variations": omega_variations,
        "states13d": 3**13, "counts13d": counts, "root13d": chain13,
        "hard_invalid_repairs": hard_repairs, "routing_decision_variations": decision_variations,
    }


def k27_projection_root() -> dict:
    p = K27ConstraintProjector(); snap = make_owner().snapshot(); rows = []
    for x, y, z in itertools.product(range(3), repeat=3):
        c = K27Coordinate(x, y, z)
        soft = p.project(RawGestureIntent.build(GestureObservation(c.code * 2, "open", 900, 650, c)), snap)
        hard = p.project(RawGestureIntent.build(GestureObservation(c.code * 2 + 1, "rotate", 900, 650, c)), snap)
        rows.append([c.code, list(soft.controls), list(hard.controls)])
    return {"coordinates": 27, "projection_root": digest(rows)}


def main() -> None:
    h = hs1000(); lattice = omega8_13d(); k27 = k27_projection_root()
    empty_bench = synthetic_callback_benchmark(make_owner(lookahead_blocks=0), blocks=5_000)
    control_bench = synthetic_callback_benchmark(make_owner(lookahead_blocks=0), blocks=5_000, control_every_blocks=1)
    replay_seq = [
        GestureObservation(0, "open", 900, 620, K27Coordinate(2, 1, 1)), GestureObservation(1, "open", 900, 620, K27Coordinate(2, 1, 1)),
        GestureObservation(2, "open", 400, 620, K27Coordinate(2, 1, 1)), GestureObservation(3, "rotate", 900, 700, K27Coordinate(0, 2, 2)),
        GestureObservation(4, "rotate", 900, 700, K27Coordinate(0, 2, 2)),
    ]
    replay_a = replay_root(replay_seq, recipe_root=RECIPE, engine_root=ENGINE); replay_b = replay_root(replay_seq, recipe_root=RECIPE, engine_root=ENGINE)
    deterministic = {"hs1000": h, "lattice": lattice, "k27": k27, "replay_root": replay_a, "replay_equal": replay_a == replay_b}
    out = {
        **deterministic, "deterministic_root": digest(deterministic),
        "synthetic_callback_benchmark_empty": asdict(empty_bench),
        "synthetic_callback_benchmark_control": asdict(control_bench),
        "authority_ceiling": "D0_PROCESS_LEVEL_ONLY__NO_DEVICE_XRUN_CREDIT",
    }
    print(json.dumps(out, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
