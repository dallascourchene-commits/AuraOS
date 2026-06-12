"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Self-Optimizing Routing)
DEPENDENCIES: argparse, json, os, time, aura_substrate, aura_llm_egress, aura_proxy_benchmark, aura_matrix_benchmark
FUNCTIONS: CalibrationLedger, ExecutionLog, calibrate, AutoRouter, savings_report
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Auto-Router — self-optimizing model/protocol selection.
============================================================

Aura calibrates external models (the matrix benchmark), remembers what works in
a persistent ledger, and then routes each task to the **most optimal** model +
packet style + output mode automatically — unless the user forces a specific
model, in which case that model is tried first and the order changes.

Pieces:
  * CalibrationLedger   — append-only JSONL of calibration results (newest wins).
  * calibrate()         — runs the matrix for given/working providers, logs rows.
  * AutoRouter          — picks best-available (provider, style, mode) for a task
                          (or a forced model), runs it via the external egress,
                          validates + expands the result, logs the execution.
  * ExecutionLog        — append-only JSONL of routed calls (for savings metrics).
  * savings_report()    — cumulative actual savings + projected savings if every
                          task were routed optimally.

The substrate stays LLM-free; the paid model is only touched at the egress.
Calibration and routing themselves are deterministic.

Run:
    python3 aura_router.py calibrate                 # calibrate working providers
    python3 aura_router.py calibrate --mock          # offline
    python3 aura_router.py route --task mesh_offload  # auto-optimal routing
    python3 aura_router.py route --task mesh_offload --model sambanova   # force model
    python3 aura_router.py status                    # best per task from the ledger
    python3 aura_router.py savings                   # savings metrics
"""

from __future__ import annotations

import argparse
import json
import os
import time

from aura_substrate import (
    REPO_ROOT,
    AuraSubstrate,
    ContextSelector,
    estimate_tokens,
    existing_import_roots,
    sanitize_code,
)
from aura_llm_egress import (
    ExternalLLM,
    KNOWN_WORKING,
    classify_providers,
    usable_providers,
)
from aura_proxy_benchmark import (
    OUTPUT_MODES,
    QualityScorer,
    TASKS,
    _repo_py_files,
    apply_edit_plan,
    edit_plan_to_unified_diff,
    parse_edit_plan,
    with_output_mode,
)
from aura_matrix_benchmark import MockEgress, run_matrix

MEMORY_DIR = os.path.join(REPO_ROOT, "Aura_Memory")
LEDGER_PATH = os.path.join(MEMORY_DIR, "aura_calibration.jsonl")
EXEC_LOG_PATH = os.path.join(MEMORY_DIR, "aura_executions.jsonl")

# Cold-start defaults (used before a task_type has calibration data). Chosen from
# observed real runs: bracket packets + the output-token-efficient edit plan.
DEFAULT_STYLE = "bracket"
DEFAULT_MODE = "json_edit_plan"

# Fields copied from a matrix row into a ledger record.
_LEDGER_FIELDS = (
    "provider", "model", "style", "output_mode",
    "raw_quality", "aura_quality", "quality_delta",
    "raw_input_tokens", "aura_input_tokens", "aura_input_tokens_amortized",
    "raw_output_tokens", "aura_output_tokens",
    "token_reduction_pct", "token_reduction_amortized_pct", "output_token_reduction_pct",
    "raw_total_cost_usd", "aura_total_cost_usd", "cost_saving_usd",
    "aura_latency_sec", "overall_score", "trials",
)


# --------------------------------------------------------------------------- #
# Persistent logs
# --------------------------------------------------------------------------- #

class _JsonlStore:
    def __init__(self, path: str):
        self.path = path

    def append(self, record: dict) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return out


class CalibrationLedger(_JsonlStore):
    """Append-only calibration results. Newest record per key supersedes older."""

    KEY = ("task_type", "provider", "style", "output_mode")

    def record_matrix(self, results: dict) -> int:
        """Append every successful matrix row as a timestamped calibration record."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        task = results.get("task", "?")
        n = 0
        for r in results.get("rows", []):
            rec = {"ts": ts, "task": task, "task_type": r.get("task_type", "patch")}
            for fld in _LEDGER_FIELDS:
                rec[fld] = r.get(fld)
            self.append(rec)
            n += 1
        return n

    def latest(self) -> list[dict]:
        """Deduplicate to the newest record per (task_type, provider, style, mode)."""
        best: dict[tuple, dict] = {}
        for rec in self.read_all():
            key = tuple(rec.get(k) for k in self.KEY)
            cur = best.get(key)
            if cur is None or rec.get("ts", "") >= cur.get("ts", ""):
                best[key] = rec
        return list(best.values())

    def best_candidates(self, task_type: str, available: list[str],
                        prefer_model: str | None = None) -> list[dict]:
        """Ordered (provider, style, output_mode) candidates, best first.

        Forcing a model puts it first (reordering priority). Otherwise providers
        are ordered by their best calibrated overall_score; providers with no
        calibration data fall back to cold-start defaults in priority order.
        """
        rows = [r for r in self.latest()
                if r.get("task_type") == task_type and r.get("provider") in available]
        best_by_prov: dict[str, dict] = {}
        for r in rows:
            cur = best_by_prov.get(r["provider"])
            if cur is None or (r.get("overall_score") or 0) > (cur.get("overall_score") or 0):
                best_by_prov[r["provider"]] = r

        def from_row(r):
            return {"provider": r["provider"], "style": r["style"],
                    "output_mode": r["output_mode"], "overall_score": r.get("overall_score"),
                    "source": "ledger"}

        def default_for(p):
            return {"provider": p, "style": DEFAULT_STYLE, "output_mode": DEFAULT_MODE,
                    "overall_score": None, "source": "default"}

        prefer = prefer_model.lower() if prefer_model else None
        ordered: list[str] = []
        if prefer and prefer in available:
            ordered.append(prefer)
        rest = [p for p in available if p != prefer]
        with_data = sorted([p for p in rest if p in best_by_prov],
                           key=lambda p: best_by_prov[p].get("overall_score") or 0, reverse=True)
        without = sorted([p for p in rest if p not in best_by_prov],
                         key=lambda p: (p not in KNOWN_WORKING, p))
        ordered += with_data + without

        return [from_row(best_by_prov[p]) if p in best_by_prov else default_for(p)
                for p in ordered]


class ExecutionLog(_JsonlStore):
    pass


# --------------------------------------------------------------------------- #
# Calibration
# --------------------------------------------------------------------------- #

def calibrate(task_key: str, providers: list[str], styles: list[str],
              output_modes: list[str], trials: int, mock: bool,
              delay: float = 0.0, ledger: CalibrationLedger | None = None) -> dict:
    """Run the matrix and append results to the calibration ledger."""
    ledger = ledger or CalibrationLedger(LEDGER_PATH)
    results = run_matrix(task_key, providers, styles, mock,
                         trials=trials, output_modes=output_modes, delay=delay)
    # tag rows with task_type so the ledger is per-task
    task_type = TASKS[task_key].task_type
    for r in results["rows"]:
        r.setdefault("task_type", task_type)
    n = ledger.record_matrix(results)
    results["_ledger_records"] = n
    return results


# --------------------------------------------------------------------------- #
# Auto-router
# --------------------------------------------------------------------------- #

class AutoRouter:
    def __init__(self, ledger: CalibrationLedger | None = None,
                 exec_log: ExecutionLog | None = None,
                 egress_factory=None, root: str = REPO_ROOT):
        self.ledger = ledger or CalibrationLedger(LEDGER_PATH)
        self.exec_log = exec_log or ExecutionLog(EXEC_LOG_PATH)
        self.egress_factory = egress_factory or (lambda p, **kw: ExternalLLM(provider=p, **kw))
        self.root = root
        self.selector = ContextSelector(root)
        self.substrate = AuraSubstrate(root)

    def _available(self, mock: bool, forced: str | None) -> list[str]:
        if mock:
            return ["mock"]
        pool = usable_providers(prefer_working=False)  # working + configured (have keys)
        if forced and forced.lower() not in pool:
            # forced model has no usable key — still surface it so we can warn
            pool = [forced.lower()] + pool
        return pool

    def _raw_baseline(self, task) -> tuple[int, int | None, float | None]:
        """Deterministic raw input tokens + ledger-estimated raw output/cost."""
        raw_ctx = self.selector.raw_context(task.target_file, task.extra_context_files)
        raw_prompt = f"{task.human_prompt}\n\nHere is the relevant code:\n\n{raw_ctx.text}\n"
        raw_in = estimate_tokens(raw_prompt)
        outs = [r.get("raw_output_tokens") for r in self.ledger.latest()
                if r.get("task_type") == task.task_type and r.get("raw_output_tokens")]
        costs = [r.get("raw_total_cost_usd") for r in self.ledger.latest()
                 if r.get("task_type") == task.task_type and r.get("raw_total_cost_usd")]
        est_out = int(sum(outs) / len(outs)) if outs else None
        est_cost = round(sum(costs) / len(costs), 6) if costs else None
        return raw_in, est_out, est_cost

    # Safety-critical checks that must pass to accept a patch (vs. nice-to-have).
    _SAFETY_CHECKS = ("parses_ok", "no_fake_files", "no_forbidden_deps")

    def route(self, task_key: str, forced_model: str | None = None,
              mock: bool = False, max_fallbacks: int = 4, aspect: str = "refactor",
              max_retries: int = 1) -> dict:
        if task_key not in TASKS:
            raise SystemExit(f"Unknown task '{task_key}'. Known: {list(TASKS)}")
        return self.route_task(TASKS[task_key], forced_model=forced_model, mock=mock,
                               max_fallbacks=max_fallbacks, aspect=aspect,
                               max_retries=max_retries)

    def route_task(self, task, forced_model: str | None = None, mock: bool = False,
                   max_fallbacks: int = 4, aspect: str = "refactor",
                   max_retries: int = 1) -> dict:
        """Route any TestCase to the best-available model with a sanitize+retry loop.

        On a verification failure the patch is ASCII-sanitized (deterministic);
        if a safety check still fails, the verifier error is fed back to the model
        and the call is retried (up to max_retries) before falling back to the
        next-best provider.
        """
        available = self._available(mock, forced_model)
        candidates = self.ledger.best_candidates(task.task_type, available,
                                                 prefer_model=forced_model)
        if not candidates:
            raise SystemExit("No providers available to route to (no keys / use --mock).")

        original = self.selector.read(task.target_file)
        scorer = QualityScorer(_repo_py_files(), existing_import_roots(original),
                               original, target_func=task.target_func)
        raw_in, est_raw_out, est_raw_cost = self._raw_baseline(task)

        tried: list[dict] = []
        for cand in candidates[:max_fallbacks]:
            try:
                egress = self.egress_factory(cand["provider"])
            except Exception as exc:  # noqa: BLE001
                tried.append({"provider": cand["provider"], "error": str(exc)})
                continue
            task_v = with_output_mode(task, cand["output_mode"])
            correction = ""
            for attempt in range(max_retries + 1):
                pkg = self.substrate.compile(task.human_prompt, target_file=task.target_file,
                                              target_func=task.target_func,
                                              explicit_tags=task_v.packet_tags, style=cand["style"])
                prompt = pkg.prompt if not correction else (
                    pkg.prompt + "\n[CORRECTION]\n" + correction +
                    "\nEmit ASCII only (no smart quotes or em-dashes).\n")
                ain = estimate_tokens(prompt)
                # Wire savings context into the egress so every call is logged
                egress._task = task.key
                egress._aspect = aspect
                egress._baseline_prompt = raw_in
                egress._baseline_output = est_raw_out
                egress._baseline_cost = est_raw_cost
                text, err, lat = egress.generate(prompt)
                if err or not text:
                    tried.append({"provider": cand["provider"], "style": cand["style"],
                                  "output_mode": cand["output_mode"], "error": err or "empty"})
                    print(f"[fallback] {cand['provider']}/{cand['style']}/{cand['output_mode']}: "
                          f"{err or 'empty'}")
                    break  # provider error -> next candidate

                clean, _repl = sanitize_code(text)
                q = scorer.score(clean, task_v)
                safe = all(q["checks"].get(c) for c in self._SAFETY_CHECKS)
                if not safe and attempt < max_retries:
                    correction = "Previous output failed verification: " + "; ".join(q["notes"][:3])
                    print(f"[retry] {cand['provider']}/{cand['style']}: {correction[:80]}")
                    continue

                aout = estimate_tokens(clean)
                artifact = self._expand(clean, task_v, original)
                record = {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "task": task.key, "task_type": task.task_type, "aspect": aspect,
                    "chosen_provider": egress.provider, "model": egress.model,
                    "style": cand["style"], "output_mode": cand["output_mode"],
                    "selection": cand["source"], "forced_model": forced_model,
                    "attempts": attempt + 1, "accepted": safe,
                    "aura_input_tokens": ain, "aura_output_tokens": aout,
                    "aura_total_cost_usd": egress.cost(ain, aout),
                    "raw_input_tokens": raw_in,
                    "est_raw_output_tokens": est_raw_out,
                    "est_raw_total_cost_usd": est_raw_cost,
                    "quality": q["score"], "latency_sec": round(lat, 3),
                    "fallbacks_tried": tried,
                }
                self.exec_log.append(record)
                return {"ok": True, "accepted": safe, "record": record,
                        "checks": q["checks"], "notes": q["notes"],
                        "artifact": artifact, "model_output": text}

        return {"ok": False, "tried": tried,
                "reason": "all candidates failed (no key / rate-limited / error)"}

    @staticmethod
    def _expand(text: str, task_v, original: str) -> str:
        """Deterministically turn the model output into a standard unified diff."""
        if task_v.output_format == "json_edit_plan":
            plan, note = parse_edit_plan(text)
            if plan is None:
                return f"# could not parse edit plan: {note}"
            return edit_plan_to_unified_diff(original, plan, task_v.target_file)
        return text


# --------------------------------------------------------------------------- #
# Savings + status reporting
# --------------------------------------------------------------------------- #

def _blank_acc() -> dict:
    return {"calls": 0, "aura_in": 0, "aura_out": 0, "aura_cost": 0.0,
            "in_saved": 0, "out_saved": 0, "cost_saved": 0.0}


def _accumulate(acc: dict, e: dict) -> None:
    a_in = e.get("aura_input_tokens") or 0
    a_out = e.get("aura_output_tokens") or 0
    a_cost = e.get("aura_total_cost_usd") or 0
    acc["calls"] += 1
    acc["aura_in"] += a_in
    acc["aura_out"] += a_out
    acc["aura_cost"] += a_cost
    if e.get("raw_input_tokens"):
        acc["in_saved"] += e["raw_input_tokens"] - a_in
    if e.get("est_raw_output_tokens"):
        acc["out_saved"] += e["est_raw_output_tokens"] - a_out
    if e.get("est_raw_total_cost_usd") is not None:
        acc["cost_saved"] += e["est_raw_total_cost_usd"] - a_cost


def _round_acc(acc: dict) -> dict:
    return {"calls": acc["calls"],
            "aura_input_tokens": int(acc["aura_in"]), "aura_output_tokens": int(acc["aura_out"]),
            "aura_cost_usd": round(acc["aura_cost"], 6),
            "input_tokens_saved": int(acc["in_saved"]), "output_tokens_saved": int(acc["out_saved"]),
            "est_cost_saved_usd": round(acc["cost_saved"], 6)}


def savings_report(ledger: CalibrationLedger | None = None,
                   exec_log: ExecutionLog | None = None) -> dict:
    ledger = ledger or CalibrationLedger(LEDGER_PATH)
    exec_log = exec_log or ExecutionLog(EXEC_LOG_PATH)
    try:
        from aura_pricing import get_pricebook
        prices_updated = get_pricebook().updated_at()
    except Exception:  # noqa: BLE001
        prices_updated = "unknown"

    execs = exec_log.read_all()
    overall = _blank_acc()
    by_provider: dict[str, dict] = {}
    by_aspect: dict[str, dict] = {}
    counted = 0
    for e in execs:
        _accumulate(overall, e)
        prov = e.get("chosen_provider", "?")
        asp = e.get("aspect", "unspecified")
        _accumulate(by_provider.setdefault(prov, _blank_acc()), e)
        _accumulate(by_aspect.setdefault(asp, _blank_acc()), e)
        if e.get("est_raw_total_cost_usd") is not None:
            counted += 1

    # Projected per-task savings if every task_type were routed to its best cell.
    projection: dict[str, dict] = {}
    by_type: dict[str, list[dict]] = {}
    for r in ledger.latest():
        by_type.setdefault(r.get("task_type", "?"), []).append(r)
    for ttype, rows in by_type.items():
        best = max(rows, key=lambda r: r.get("overall_score") or 0)
        projection[ttype] = {
            "best": f"{best['provider']}/{best['style']}/{best['output_mode']}",
            "input_reduction_pct": best.get("token_reduction_amortized_pct"),
            "output_reduction_pct": best.get("output_token_reduction_pct"),
            "cost_saving_per_task_usd": best.get("cost_saving_usd"),
        }

    return {
        "executions": len(execs),
        "prices_updated": prices_updated,
        "overall": _round_acc(overall),
        "by_provider": {k: _round_acc(v) for k, v in by_provider.items()},
        "by_aspect": {k: _round_acc(v) for k, v in by_aspect.items()},
        "note": f"output/cost baselines estimated from calibration for {counted} of "
                f"{len(execs)} executions; $ at PriceBook rates (updated {prices_updated})",
        "projection_if_optimal": projection,
    }


def status(ledger: CalibrationLedger | None = None) -> dict:
    ledger = ledger or CalibrationLedger(LEDGER_PATH)
    latest = ledger.latest()
    by_type: dict[str, list[dict]] = {}
    for r in latest:
        by_type.setdefault(r.get("task_type", "?"), []).append(r)
    out = {}
    for ttype, rows in by_type.items():
        ranked = sorted(rows, key=lambda r: r.get("overall_score") or 0, reverse=True)
        out[ttype] = [{
            "provider": r["provider"], "style": r["style"], "output_mode": r["output_mode"],
            "aura_quality": r.get("aura_quality"), "overall_score": r.get("overall_score"),
        } for r in ranked]
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _egress_factory(mock: bool):
    if mock:
        return lambda p: MockEgress(provider=p)
    return lambda p: ExternalLLM(provider=p)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aura auto-router (calibrate + optimal routing)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("calibrate", help="run calibration and append to the ledger")
    pc.add_argument("--task", default="sandbox_score",
                    help="calibration task (default: isolated sandbox — never touches source)")
    pc.add_argument("--providers", default=None, help="comma list (default: working providers)")
    pc.add_argument("--styles", default="bracket,json,yaml,hybrid")
    pc.add_argument("--output-modes", default=",".join(OUTPUT_MODES))
    pc.add_argument("--trials", type=int, default=1)
    pc.add_argument("--delay", type=float, default=0.0)
    pc.add_argument("--mock", action="store_true")

    pr = sub.add_parser("route", help="route a task to the most optimal (or forced) model")
    pr.add_argument("--task", default="mesh_offload")
    pr.add_argument("--model", default=None, help="force a specific model (reorders priority)")
    pr.add_argument("--mock", action="store_true")

    sub.add_parser("status", help="show best calibrated protocol per task type")
    sub.add_parser("savings", help="show cumulative + projected savings")
    sub.add_parser("list-providers", help="show provider buckets")

    args = p.parse_args(argv)

    if args.cmd == "list-providers":
        b = classify_providers()
        print("working:", ", ".join(b["working"]) or "(none)")
        print("configured:", ", ".join(b["configured"]) or "(none)")
        print("placeholders:", ", ".join(b["placeholder"]) or "(none)")
        return 0

    if args.cmd == "calibrate":
        styles = [s.strip() for s in args.styles.split(",") if s.strip()]
        modes = [m.strip() for m in args.output_modes.split(",") if m.strip()]
        if args.providers:
            providers = [x.strip() for x in args.providers.split(",") if x.strip()]
        elif args.mock:
            providers = ["mock"]
        else:
            providers = usable_providers(prefer_working=True)
            if not providers:
                raise SystemExit("No working providers. Use --mock for offline calibration.")
        print(f"[*] calibrating task={args.task} providers={providers} "
              f"styles={styles} modes={modes} trials={args.trials} mock={args.mock}")
        res = calibrate(args.task, providers, styles, modes, args.trials, args.mock,
                        delay=args.delay)
        print(f"[+] logged {res.get('_ledger_records', 0)} calibration records to {LEDGER_PATH}")
        lb = res.get("leaderboard", {})
        if lb:
            bo = lb["best_overall"]
            print(f"    best overall: {bo['provider']}/{bo['style']}/{bo['output_mode']} "
                  f"(q_aura={bo['aura_quality']}, overall={bo['overall_score']})")
        return 0

    if args.cmd == "route":
        router = AutoRouter(egress_factory=_egress_factory(args.mock))
        res = router.route(args.task, forced_model=args.model, mock=args.mock)
        if not res["ok"]:
            print(f"[-] routing failed: {res['reason']}")
            for t in res["tried"]:
                print(f"    tried {t}")
            return 1
        rec = res["record"]
        print(f"[+] routed {rec['task']} -> {rec['chosen_provider']}/{rec['style']}/"
              f"{rec['output_mode']} ({rec['selection']}"
              f"{', forced' if rec['forced_model'] else ''})")
        print(f"    quality={rec['quality']} latency={rec['latency_sec']}s "
              f"aura_tokens(in/out)={rec['aura_input_tokens']}/{rec['aura_output_tokens']} "
              f"cost=${rec['aura_total_cost_usd']}")
        if rec["fallbacks_tried"]:
            print(f"    fell back past: {[t['provider'] for t in rec['fallbacks_tried']]}")
        print("\n--- expanded artifact ---")
        print(res["artifact"][:1500])
        return 0

    if args.cmd == "status":
        st = status()
        if not st:
            print("No calibration data yet. Run: python3 aura_router.py calibrate")
            return 0
        for ttype, rows in st.items():
            print(f"task_type '{ttype}':")
            for r in rows:
                print(f"  {r['provider']:10s} {r['style']:7s} {r['output_mode']:14s} "
                      f"q_aura={r['aura_quality']} overall={r['overall_score']}")
        return 0

    if args.cmd == "savings":
        rep = savings_report()
        o = rep["overall"]
        print(f"=== OVERALL (over {rep['executions']} routed calls) ===")
        print(f"  tokens used (in/out): {o['aura_input_tokens']}/{o['aura_output_tokens']}")
        print(f"  tokens saved (in/out): {o['input_tokens_saved']}/{o['output_tokens_saved']}")
        print(f"  cost used   : ${o['aura_cost_usd']}")
        print(f"  cost SAVED  : ${o['est_cost_saved_usd']}")
        print("=== PER PROVIDER (actual rates) ===")
        for prov, v in rep["by_provider"].items():
            print(f"  {prov:10s} calls={v['calls']} used=${v['aura_cost_usd']} "
                  f"saved=${v['est_cost_saved_usd']} "
                  f"tok_saved(in/out)={v['input_tokens_saved']}/{v['output_tokens_saved']}")
        print("=== PER ASPECT (conversation / refactor / self_optimize / ...) ===")
        for asp, v in rep["by_aspect"].items():
            print(f"  {asp:14s} calls={v['calls']} saved=${v['est_cost_saved_usd']} "
                  f"tok_saved(in/out)={v['input_tokens_saved']}/{v['output_tokens_saved']}")
        print(f"  ({rep['note']})")
        print("=== PROJECTION (if every task routed optimally) ===")
        for ttype, pr in rep["projection_if_optimal"].items():
            print(f"  {ttype}: best={pr['best']} in-{pr['input_reduction_pct']}% "
                  f"out-{pr['output_reduction_pct']}% save/task=${pr['cost_saving_per_task_usd']}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
