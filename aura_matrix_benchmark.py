"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Honest Measurement)
DEPENDENCIES: argparse, json, os, time, aura_substrate, aura_llm_egress, aura_proxy_benchmark
FUNCTIONS: MockEgress, run_cell, run_matrix, build_leaderboard, write_reports, main
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Model/Protocol Matrix Benchmark.
=====================================

Extends the single-pair A/B benchmark into a **provider x packet-style matrix**
to discover model-protocol fit: which external LLM responds best to Aura's
compressed polysynthetic packets, and which packet syntax each model prefers.

For every (provider, packet_style) pair we run the SAME task:

  RAW  : human prompt + full file context -> model            (once per provider)
  AURA : substrate.compile(style) [NO LLM] -> packet+guardrails+surgical slice
         -> external egress (same model)                       (once per style)

Packet styles: bracket | json | yaml | hybrid.

Providers are discovered from aura_secrets.json (never local/internal, never
Gemini). Providers without a key are skipped. A `--mock` mode runs fully offline
with a deterministic synthetic model for pipeline testing.

Outputs a Markdown leaderboard (best quality / cost / latency / overall) plus a
per-model "preferred packet style" summary, stored in Aura_Memory/benchmarks/.

Run:
    python3 aura_matrix_benchmark.py --task mesh_offload
    python3 aura_matrix_benchmark.py --providers mistral,sambanova --styles bracket,json
    python3 aura_matrix_benchmark.py --mock          # offline, no API calls
"""

from __future__ import annotations

import argparse
import json
import os
import time

from aura_substrate import (
    PACKET_STYLES,
    REPO_ROOT,
    AuraSubstrate,
    ContextSelector,
    estimate_tokens,
    existing_import_roots,
    load_guardrails,
)
from aura_llm_egress import (
    ExternalLLM,
    PROVIDERS,
    classify_providers,
    usable_providers,
)
from aura_proxy_benchmark import OUTPUT_MODES, QualityScorer, TASKS, _repo_py_files, with_output_mode

REPORT_DIR = os.path.join(REPO_ROOT, "Aura_Memory", "benchmarks")

# Composite "overall" weighting (documented in the report).
_W_QUALITY = 0.55
_W_DELTA = 0.15
_W_LATENCY = 0.15
_W_COST = 0.15


# --------------------------------------------------------------------------- #
# Offline mock egress (deterministic; for pipeline testing only)
# --------------------------------------------------------------------------- #

class MockEgress:
    """Deterministic, offline stand-in for ExternalLLM. No network.

    RAW arm  -> an over-engineered python rewrite (adds a new dep) => lower score.
    AURA arm -> a minimal, signature-preserving unified diff       => higher score.
    Provider identity does not affect output (mock cannot model real preference);
    use real mode to discover genuine model-protocol fit.
    """

    def __init__(self, provider: str = "mock", model: str = "mock-deterministic"):
        self.provider = provider
        self.model = model
        self.cfg = {"price_in_per_1k": 0.0, "price_out_per_1k": 0.0}

    def generate(self, prompt: str, *, max_tokens: int = 1300, temperature: float = 0.1):
        is_aura = "[AURA TASK PACKET" in prompt
        wants_edit_plan = "JSON_EDIT_PLAN" in prompt
        if "OP:CONVERSE" in prompt or "POLY_REPLY" in prompt:
            text = ("[REPLY]\nINTENT: ANSWER\n"
                    "ANSWER: Mock reply in the compact polysynthetic envelope.\n"
                    "REFS: none\nNEXT: none\n[/REPLY]")
            return text, None, 0.001
        if is_aura and wants_edit_plan:
            text = (
                '{"edits": [{"file": "aura_mesh.py", "start_line": 174, '
                '"end_line": 174, "replacement": "            secure_packet = '
                'self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)"}]}'
            )
        elif is_aura:
            text = (
                "--- a/aura_mesh.py\n+++ b/aura_mesh.py\n"
                "@@ -172,3 +172,4 @@\n"
                "         try:\n"
                "             print(f\"[*] Offloading {module} to {target_ip}:4445...\")\n"
                "+            # validate target before packing (no new deps)\n"
                "             secure_packet = self.pack_secure_polysynthetic_packet("
                "[0, 0, 0, 0, 0, 0], 1.0)\n"
            )
        else:
            text = (
                "Sure! Here is an improved version with retries and logging:\n\n"
                "```python\nimport aiohttp  # new dependency for robust transport\n"
                "async def offload_compute(self, target_ip, module, data_payload, retries=3):\n"
                "    for attempt in range(retries):\n"
                "        timestamp = time.time()\n"
                "        node_id = getattr(self.node, 'id', 'UNKNOWN')\n"
                "        # ... lots of extra orchestration ...\n"
                "    return None\n```\n"
            )
        return text, None, 0.001

    def cost(self, in_tokens: int, out_tokens: int) -> float:
        return 0.0


# --------------------------------------------------------------------------- #
# Single matrix cell
# --------------------------------------------------------------------------- #

_CHECK_KEYS = ("format_ok", "parses_ok", "no_fake_files", "no_forbidden_deps",
               "preserves_signature", "minimal_scope")


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


_RATELIMIT_MARKERS = ("429", "too many", "rate", "quota", "resource exhausted")


def _is_ratelimit(err: str | None) -> bool:
    return bool(err) and any(m in err.lower() for m in _RATELIMIT_MARKERS)


def _generate_with_backoff(egress, prompt: str, rl_retries: int):
    """Single generation that backs off and retries on rate-limit (429) errors."""
    backoff = 5.0
    text, err, lat = None, None, 0.0
    for attempt in range(rl_retries + 1):
        text, err, lat = egress.generate(prompt)
        if err and _is_ratelimit(err) and attempt < rl_retries:
            time.sleep(backoff)
            backoff *= 2
            continue
        break
    return text, err, lat


def _generate_trials(egress, prompt: str, trials: int, rl_retries: int = 2,
                     delay: float = 0.0) -> dict:
    """Generate-only: run N trials of one prompt (no scoring; scoring is per-mode)."""
    texts, latencies = [], []
    last_err = None
    for _ in range(max(1, trials)):
        text, err, lat = _generate_with_backoff(egress, prompt, rl_retries)
        last_err = err
        texts.append(text)
        latencies.append(lat)
        if err:  # hard error after retries — no point repeating this prompt
            break
        if delay:
            time.sleep(delay)
    return {
        "texts": texts,
        "latency": round(_mean(latencies), 3),
        "out_tokens": int(_mean([estimate_tokens(t or "") for t in texts])),
        "error": last_err,
        "trials": len(texts),
    }


def _score_texts(texts: list[str], scorer: QualityScorer, task) -> dict:
    """Average quality + majority-vote each objective check over trial outputs."""
    qualities, blasts = [], []
    hits = {k: 0 for k in _CHECK_KEYS}
    for text in texts:
        q = scorer.score(text, task)
        qualities.append(q["score"])
        blasts.append(q["metrics"]["blast_radius_lines"])
        for k in _CHECK_KEYS:
            hits[k] += 1 if q["checks"].get(k) else 0
    n = max(1, len(texts))
    return {
        "quality": round(_mean(qualities), 3),
        "blast": round(_mean(blasts), 1),
        "checks": {k: hits[k] >= (n + 1) // 2 for k in _CHECK_KEYS},
    }


def run_cell(egress, task_base, scorer, selector, substrate, style: str,
             output_mode: str, raw_cache: dict, guardrail_tokens: int,
             trials: int = 1, rl_retries: int = 2, delay: float = 0.0) -> dict:
    """Run one (provider, style, output_mode) cell. RAW generation is cached per
    provider; it is re-scored per output_mode (the model output is identical, only
    the grading format changes)."""
    task = with_output_mode(task_base, output_mode)

    # --- RAW generation (style/mode-independent; once per provider) ---
    if "gen" not in raw_cache:
        raw_ctx = selector.raw_context(task.target_file, task.extra_context_files)
        raw_prompt = f"{task.human_prompt}\n\nHere is the relevant code:\n\n{raw_ctx.text}\n"
        raw_cache["ctx"] = raw_ctx
        raw_cache["in_tokens"] = estimate_tokens(raw_prompt)
        raw_cache["gen"] = _generate_trials(egress, raw_prompt, trials, rl_retries, delay)
    rgen = raw_cache["gen"]
    rscore = _score_texts(rgen["texts"], scorer, task)
    raw_in = raw_cache["in_tokens"]
    raw_total_cost = egress.cost(raw_in, rgen["out_tokens"])

    # --- AURA arm for this (style, mode) ---
    pkg = substrate.compile(task.human_prompt, target_file=task.target_file,
                            target_func=task.target_func,
                            explicit_tags=task.packet_tags, style=style)
    ain = estimate_tokens(pkg.prompt)
    agen = _generate_trials(egress, pkg.prompt, trials, rl_retries, delay)
    ascore = _score_texts(agen["texts"], scorer, task)
    a_total_cost = egress.cost(ain, agen["out_tokens"])

    a_ex_guard = max(0, ain - guardrail_tokens)
    tok_red = round((raw_in - ain) / raw_in * 100, 1) if raw_in else 0.0
    tok_red_amort = round((raw_in - a_ex_guard) / raw_in * 100, 1) if raw_in else 0.0
    leak_red = (round((raw_cache["ctx"].exposed_lines - pkg.context.exposed_lines)
                      / raw_cache["ctx"].exposed_lines * 100, 1)
                if raw_cache["ctx"].exposed_lines else 0.0)
    out_tok_red = (round((rgen["out_tokens"] - agen["out_tokens"]) / rgen["out_tokens"] * 100, 1)
                   if rgen["out_tokens"] else 0.0)

    return {
        "provider": egress.provider,
        "model": egress.model,
        "style": style,
        "output_mode": output_mode,
        "packet": pkg.packet,
        "substrate_compile_ms": pkg.compile_ms,
        "trials": agen["trials"],
        "errored": bool(agen["error"]) or not (agen["texts"] and agen["texts"][-1]),
        "raw_errored": bool(rgen["error"]) or not (rgen["texts"] and rgen["texts"][-1]),
        "raw_quality": rscore["quality"],
        "aura_quality": ascore["quality"],
        "quality_delta": round(ascore["quality"] - rscore["quality"], 3),
        "raw_input_tokens": raw_in,
        "aura_input_tokens": ain,
        "aura_input_tokens_amortized": a_ex_guard,
        "token_reduction_pct": tok_red,
        "token_reduction_amortized_pct": tok_red_amort,
        "raw_output_tokens": rgen["out_tokens"],
        "aura_output_tokens": agen["out_tokens"],
        "output_token_reduction_pct": out_tok_red,
        "raw_total_cost_usd": raw_total_cost,
        "aura_total_cost_usd": a_total_cost,
        "cost_saving_usd": round(raw_total_cost - a_total_cost, 6),
        "raw_latency_sec": rgen["latency"],
        "aura_latency_sec": agen["latency"],
        "exposed_source_lines": pkg.context.exposed_lines,
        "context_leak_reduction_pct": leak_red,
        "raw_blast_radius": rscore["blast"],
        "aura_blast_radius": ascore["blast"],
        "checks": ascore["checks"],
        "format_ok": ascore["checks"]["format_ok"],
        "parses_ok": ascore["checks"]["parses_ok"],
        "no_fake_files": ascore["checks"]["no_fake_files"],
        "no_forbidden_deps": ascore["checks"]["no_forbidden_deps"],
        "preserves_signature": ascore["checks"]["preserves_signature"],
        "minimal_scope": ascore["checks"]["minimal_scope"],
        "error": agen["error"] or rgen["error"],
        "aura_output": agen["texts"][-1] if agen["texts"] else None,
    }


# --------------------------------------------------------------------------- #
# Matrix runner
# --------------------------------------------------------------------------- #

def rows_for(provider: str, rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["provider"] == provider]


def _make_egress(provider: str, mock: bool):
    if mock:
        return MockEgress(provider=provider)
    return ExternalLLM(provider=provider)


def run_matrix(task_key: str, providers: list[str], styles: list[str], mock: bool,
               trials: int = 1, output_modes: list[str] | None = None,
               delay: float = 0.0, rl_retries: int = 2) -> dict:
    if task_key not in TASKS:
        raise SystemExit(f"Unknown task '{task_key}'. Known: {list(TASKS)}")
    task = TASKS[task_key]
    output_modes = output_modes or ["unified_diff"]

    selector = ContextSelector()
    substrate = AuraSubstrate()
    original_source = selector.read(task.target_file)
    allowed_roots = existing_import_roots(original_source)
    scorer = QualityScorer(_repo_py_files(), allowed_roots, original_source,
                           target_func=task.target_func)
    guardrail_tokens = estimate_tokens(load_guardrails())

    rows: list[dict] = []
    skipped: list[dict] = []

    for provider in providers:
        try:
            egress = _make_egress(provider, mock)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"provider": provider, "reason": str(exc)})
            print(f"[skip] {provider}: {exc}")
            continue

        raw_cache: dict = {}
        provider_failed = False
        for mode in output_modes:
            for style in styles:
                try:
                    cell = run_cell(egress, task, scorer, selector, substrate, style,
                                    mode, raw_cache, guardrail_tokens, trials=trials,
                                    rl_retries=rl_retries, delay=delay)
                except Exception as exc:  # noqa: BLE001
                    skipped.append({"provider": provider, "style": style,
                                    "mode": mode, "reason": str(exc)})
                    print(f"[skip] {provider}/{style}/{mode}: {exc}")
                    provider_failed = True
                    break
                # Hard provider failure (e.g. 403 auth) on the very first cell -> skip provider.
                if cell["raw_errored"] and not rows_for(provider, rows):
                    skipped.append({"provider": provider, "style": style,
                                    "mode": mode, "reason": cell["error"]})
                    print(f"[skip] {provider}: provider error -> {cell['error']}")
                    provider_failed = True
                    break
                # Cell-level error (e.g. 429 after retries): record as skipped, not a
                # quality-0 row, so it does not pollute the leaderboard.
                if cell["errored"]:
                    skipped.append({"provider": provider, "style": style,
                                    "mode": mode, "reason": cell["error"] or "empty output"})
                    print(f"[skip] {provider}/{style}/{mode}: {cell['error'] or 'empty output'}")
                    continue
                rows.append(cell)
                print(f"[ok]   {egress.provider:10s} {style:7s} {mode:14s} "
                      f"q_raw={cell['raw_quality']} q_aura={cell['aura_quality']} "
                      f"dq={cell['quality_delta']:+} in-{cell['token_reduction_pct']}% "
                      f"out-{cell['output_token_reduction_pct']}% lat={cell['aura_latency_sec']}s")
            if provider_failed:
                break

    leaderboard = build_leaderboard(rows)
    return {
        "task": task.key,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "mock" if mock else "real",
        "trials_per_cell": trials,
        "providers_requested": providers,
        "styles": styles,
        "output_modes": output_modes,
        "architecture": "aura_substrate(no LLM) -> aura_llm_egress(external only)",
        "weights": {"quality": _W_QUALITY, "quality_delta": _W_DELTA,
                    "latency": _W_LATENCY, "cost": _W_COST},
        "rows": rows,
        "skipped": skipped,
        "leaderboard": leaderboard,
    }


def build_leaderboard(rows: list[dict]) -> dict:
    if not rows:
        return {}

    lats = [r["aura_latency_sec"] for r in rows]
    costs = [r["aura_total_cost_usd"] for r in rows]
    lo_l, hi_l = min(lats), max(lats)
    lo_c, hi_c = min(costs), max(costs)

    def norm_lower_better(x, lo, hi):
        if hi <= lo:
            return 1.0
        return (hi - x) / (hi - lo)

    for r in rows:
        lat_score = norm_lower_better(r["aura_latency_sec"], lo_l, hi_l)
        cost_score = norm_lower_better(r["aura_total_cost_usd"], lo_c, hi_c)
        delta_clamped = max(0.0, min(1.0, r["quality_delta"]))
        r["overall_score"] = round(
            _W_QUALITY * r["aura_quality"] + _W_DELTA * delta_clamped
            + _W_LATENCY * lat_score + _W_COST * cost_score, 4)

    best_quality = sorted(rows, key=lambda r: (r["aura_quality"], r["quality_delta"]),
                          reverse=True)[0]
    best_cost = sorted(rows, key=lambda r: (r["aura_total_cost_usd"], -r["aura_quality"]))[0]
    best_latency = sorted(rows, key=lambda r: (r["aura_latency_sec"], -r["aura_quality"]))[0]
    best_overall = sorted(rows, key=lambda r: r["overall_score"], reverse=True)[0]

    # Per-provider best (style, output_mode) by overall, then quality.
    preferred: dict[str, dict] = {}
    for r in rows:
        cur = preferred.get(r["provider"])
        if cur is None or (r["overall_score"], r["aura_quality"]) > (cur["overall_score"], cur["aura_quality"]):
            preferred[r["provider"]] = {
                "style": r["style"], "output_mode": r["output_mode"],
                "aura_quality": r["aura_quality"], "overall_score": r["overall_score"],
                "quality_delta": r["quality_delta"],
            }

    def cell_id(r):
        return {"provider": r["provider"], "style": r["style"], "output_mode": r["output_mode"],
                "aura_quality": r["aura_quality"], "quality_delta": r["quality_delta"],
                "aura_latency_sec": r["aura_latency_sec"],
                "aura_total_cost_usd": r["aura_total_cost_usd"],
                "overall_score": r.get("overall_score")}

    return {
        "best_quality": cell_id(best_quality),
        "best_total_cost": cell_id(best_cost),
        "best_latency": cell_id(best_latency),
        "best_overall": cell_id(best_overall),
        "preferred_style_per_provider": preferred,
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def write_reports(results: dict) -> tuple[str, str]:
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    base = f"matrix_{results['task']}_{results['mode']}_{stamp}"
    json_path = os.path.join(REPORT_DIR, base + ".json")
    md_path = os.path.join(REPORT_DIR, base + ".md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    rows = results["rows"]
    lb = results["leaderboard"]

    lines = [
        f"# Aura Model/Protocol Matrix — `{results['task']}`",
        "",
        f"**Mode:** {results['mode'].upper()}  |  **Trials/cell:** {results.get('trials_per_cell', 1)}  |  **Timestamp:** {results['timestamp']}",
        f"**Architecture:** {results['architecture']}",
        f"**Packet styles:** {', '.join(results['styles'])}  |  **Output modes:** {', '.join(results.get('output_modes', []))}",
        "",
        "Goal: discover model-protocol fit — which external model responds best to",
        "Aura's compressed polysynthetic packets, which packet syntax it prefers, and",
        "how much the compact output mode saves on output tokens.",
        "",
        "## Matrix",
        "",
        "Checks legend (6-char mask, uppercase=pass): F=format P=parse K=no-fake-files "
        "D=no-new-deps S=signature M=minimal-scope.",
        "",
        "| Provider | Style | Output | q_raw | q_aura | Δq | in↓% | in↓ amort | out tok r→a | out↓% | total$ | leak↓% | blast r→a | checks | lat(s) | overall |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    def mask(r):
        order = [("format_ok", "F"), ("parses_ok", "P"), ("no_fake_files", "K"),
                 ("no_forbidden_deps", "D"), ("preserves_signature", "S"), ("minimal_scope", "M")]
        return "".join(ltr if r.get(k) else ltr.lower() for k, ltr in order)

    for r in sorted(rows, key=lambda x: (x["provider"], x["output_mode"], x["style"])):
        lines.append(
            f"| {r['provider']} | {r['style']} | {r['output_mode']} | {r['raw_quality']} | "
            f"{r['aura_quality']} | {r['quality_delta']:+} | {r['token_reduction_pct']} | "
            f"{r['token_reduction_amortized_pct']} | {r['raw_output_tokens']}→{r['aura_output_tokens']} | "
            f"{r['output_token_reduction_pct']} | {r['aura_total_cost_usd']} | "
            f"{r['context_leak_reduction_pct']} | {r['raw_blast_radius']}→{r['aura_blast_radius']} | "
            f"{mask(r)} | {r['aura_latency_sec']} | {r.get('overall_score','-')} |")

    lines += ["", "## Leaderboard", ""]
    if lb:
        def fmt(c):
            return (f"**{c['provider']} / {c['style']} / {c['output_mode']}** "
                    f"(q_aura={c['aura_quality']}, Δq={c['quality_delta']:+}, "
                    f"lat={c['aura_latency_sec']}s, total=${c['aura_total_cost_usd']}, "
                    f"overall={c['overall_score']})")
        lines += [
            f"- **Best quality:** {fmt(lb['best_quality'])}",
            f"- **Best total cost:** {fmt(lb['best_total_cost'])}",
            f"- **Best latency:** {fmt(lb['best_latency'])}",
            f"- **Best overall:** {fmt(lb['best_overall'])}",
            "",
            "### Best protocol (style + output mode) per provider",
            "",
            "| Provider | Style | Output mode | q_aura | overall |",
            "|---|---|---|---|---|",
        ]
        for prov, info in lb["preferred_style_per_provider"].items():
            lines.append(f"| {prov} | {info['style']} | {info['output_mode']} | "
                         f"{info['aura_quality']} | {info['overall_score']} |")
    else:
        lines.append("_No successful cells._")

    w = results["weights"]
    lines += [
        "",
        "## Methodology",
        "",
        f"- **overall** = {w['quality']}·q_aura + {w['quality_delta']}·Δq(clamped 0–1) "
        f"+ {w['latency']}·latency_score + {w['cost']}·total_cost_score "
        "(latency/total-cost normalized within this run; lower is better).",
        "- **total$** = input+output token cost at provider list prices. The compact "
        "`json_edit_plan` mode is designed to cut **output** tokens: the model returns "
        "minimal line edits and Aura validates + expands them locally into a real diff.",
        "- **q_aura / q_raw**: fraction of objective checks passed (format, parse, "
        "no fake files, no new deps, signature preservation, minimal blast radius).",
        "- Aura's substrate runs with **no LLM** and produces no fluent prose — it only "
        "validates, applies, logs and reports via deterministic templates. Only the "
        "external egress calls a model; local/internal in-process engines are disabled.",
    ]
    if results["skipped"]:
        lines += ["", "## Skipped (no key / rejected — not failures)", ""]
        for s in results["skipped"]:
            tag = s.get("provider", "?")
            if "style" in s:
                tag += f"/{s['style']}/{s.get('mode','')}"
            lines.append(f"- `{tag}`: {s['reason']}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return json_path, md_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aura model/protocol matrix benchmark")
    p.add_argument("--task", default="mesh_offload")
    p.add_argument("--providers", default=None,
                   help="comma list (default: all providers with keys in aura_secrets.json)")
    p.add_argument("--styles", default=",".join(PACKET_STYLES),
                   help=f"comma list from {PACKET_STYLES}")
    p.add_argument("--output-modes", default=",".join(OUTPUT_MODES),
                   help=f"comma list from {list(OUTPUT_MODES)}")
    p.add_argument("--mock", action="store_true", help="offline deterministic mode (no API calls)")
    p.add_argument("--trials", type=int, default=1,
                   help="generations per cell, averaged (reduces run-to-run variance)")
    p.add_argument("--delay", type=float, default=0.0,
                   help="seconds to wait between calls (helps with rate-limited tiers)")
    p.add_argument("--rl-retries", type=int, default=2,
                   help="retries with backoff on rate-limit (429) errors")
    p.add_argument("--all-configured", action="store_true",
                   help="also run providers that have keys but are unverified (default: known-working only)")
    p.add_argument("--list-providers", action="store_true")
    args = p.parse_args(argv)

    if args.list_providers:
        buckets = classify_providers()
        print("catalog:", ", ".join(PROVIDERS.keys()))
        print("working (have keys, verified):", ", ".join(buckets["working"]) or "(none)")
        print("configured (have keys, unverified):", ", ".join(buckets["configured"]) or "(none)")
        print("placeholders (no key yet, skipped):", ", ".join(buckets["placeholder"]) or "(none)")
        return 0

    styles = [s.strip() for s in args.styles.split(",") if s.strip()]
    for s in styles:
        if s not in PACKET_STYLES:
            raise SystemExit(f"Unknown style '{s}'. Valid: {PACKET_STYLES}")
    modes = [m.strip() for m in args.output_modes.split(",") if m.strip()]
    for m in modes:
        if m not in OUTPUT_MODES:
            raise SystemExit(f"Unknown output mode '{m}'. Valid: {list(OUTPUT_MODES)}")

    if args.providers:
        providers = [x.strip() for x in args.providers.split(",") if x.strip()]
    elif args.mock:
        providers = ["mock"]
    else:
        providers = ["anthropic", "mistral", "sambanova", "groq", "cerebras", "openrouter", "gemini"]
        if not providers:
            raise SystemExit("No providers with usable API keys found. Use --mock for offline run.")

    print(f"[*] task={args.task} mode={'mock' if args.mock else 'real'} "
          f"trials={args.trials} providers={providers} styles={styles} output_modes={modes}")
    results = run_matrix(args.task, providers, styles, args.mock,
                         trials=args.trials, output_modes=modes,
                         delay=args.delay, rl_retries=args.rl_retries)
    json_path, md_path = write_reports(results)

    lb = results["leaderboard"]
    print("\n=== LEADERBOARD ===")
    if lb:
        for k in ("best_quality", "best_total_cost", "best_latency", "best_overall"):
            c = lb[k]
            print(f"  {k:16s}: {c['provider']}/{c['style']}/{c['output_mode']} "
                  f"q_aura={c['aura_quality']} overall={c['overall_score']}")
        print("  best protocol per provider:")
        for prov, info in lb["preferred_style_per_provider"].items():
            print(f"    {prov:10s} -> {info['style']}/{info['output_mode']} (q_aura={info['aura_quality']})")
    else:
        print("  (no successful cells)")
    print(f"\n[+] JSON: {json_path}")
    print(f"[+] MD  : {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
