"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa13-[Q-SYS:AURA_EFFICIENCY_BENCH_REPORT]
DIKWP_TIER: KNOWLEDGE
PWFST_ALIGNMENT: GIZAAGI'IN (Transparent Benchmark Reporting)
DEPENDENCIES: __future__, argparse, html, json, pathlib
FUNCTIONS: generate_markdown_report, generate_html_report, main
SYNOPSIS: Markdown and HTML report generator for Aura efficiency benchmark outputs.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
from typing import Any


def generate_markdown_report(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}) or {})
    modes = dict(summary.get("modes", {}) or {})
    results = list(payload.get("results", []) or [])
    best_quality = summary.get("best_mode_by_quality", "")
    best_tokens = summary.get("best_mode_by_token_savings", "")
    best_cost = summary.get("best_mode_by_cost_savings", "")
    best_latency = summary.get("best_mode_by_latency", "")
    best_speedup = summary.get("best_mode_by_processing_speedup", "")
    lines: list[str] = [
        "# Aura Efficiency Benchmark Report",
        "",
        "## 1. Executive summary",
        "",
        f"- Suite: `{payload.get('suite', 'efficiency')}`",
        f"- Run ID: `{payload.get('run_id', '')}`",
        f"- Tasks: {summary.get('task_count', 0)}",
        f"- Results: {summary.get('result_count', 0)}",
        f"- Best quality mode: `{best_quality}`",
        f"- Best token-savings mode: `{best_tokens}`",
        f"- Best cost-savings mode: `{best_cost}`",
        f"- Lowest average latency mode: `{best_latency}`",
        f"- Best processing-speedup mode: `{best_speedup}`",
        "",
        _compact_table(modes),
        "",
        _visibility_table(modes),
        "",
        "## 2. Token savings by mode",
        "",
        *_metric_lines(modes, "tokens_saved_pct", suffix="%"),
        "",
        "Input-token savings:",
        *_metric_lines(modes, "input_tokens_saved_pct", suffix="%"),
        "",
        "Output-token savings:",
        *_metric_lines(modes, "output_tokens_saved_pct", suffix="%"),
        "",
        "## 3. Cost savings by mode",
        "",
        *_metric_lines(modes, "cost_saved_pct", suffix="%"),
        "",
        "Cost per quality point:",
        *_metric_lines(modes, "cost_per_quality_point"),
        "",
        "## 4. Quality score by mode",
        "",
        *_metric_lines(modes, "avg_quality"),
        "",
        "Quality gain versus raw baseline:",
        *_metric_lines(modes, "quality_gain"),
        "",
        "## 5. Accuracy per 1,000 tokens",
        "",
        *_metric_lines(modes, "accuracy_per_1000_tokens"),
        "",
        "Quality per 1,000 tokens:",
        *_metric_lines(modes, "quality_per_1000_tokens"),
        "",
        "Latency and processing speed:",
        *_metric_lines(modes, "latency_saved_pct", suffix="% latency saved"),
        *_metric_lines(modes, "processing_speedup", suffix="x speedup"),
        "",
        "## 6. Model routing choices",
        "",
        *_routing_lines(results),
        "",
        "## 7. Unsafe patch attempts blocked",
        "",
        *_unsafe_lines(results),
        "",
        "## 8. Best demo examples",
        "",
        *_best_examples(results),
        "",
        "## 9. Raw vs Aura prompt excerpts",
        "",
        *_prompt_excerpts(results),
        "",
        "## 10. Methodology and limitations",
        "",
        (
            "The harness replays the same deterministic task suite across raw, keyword RAG, "
            "plan-act, Aura compressed, and Aura full modes. Offline runs use a deterministic "
            "mock model caller; provider-reported token and cost fields are accepted when a "
            "compatible caller supplies them. The benchmark measures prompt construction, route "
            "selection, output shape, safety metadata, and local test availability; it does not "
            "apply or stage generated patches."
        ),
        "",
        (
            "Exact source spans and hashes remain patch authority. VSA, ST3GG, JSpace, compact "
            "packets, and affinity scores are recorded as advisory context only."
        ),
        "",
    ]
    return "\n".join(lines)


def generate_html_report(payload: dict[str, Any]) -> str:
    markdown = generate_markdown_report(payload)
    body = "\n".join(_markdown_line_to_html(line) for line in markdown.splitlines())
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Aura Efficiency Benchmark</title>"
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.5}"
        "table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #ddd;padding:6px 8px;text-align:left}"
        "code,pre{background:#f6f8fa;padding:2px 4px;border-radius:4px}pre{padding:12px;overflow:auto}</style>"
        "</head><body>"
        f"{body}"
        "</body></html>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Aura efficiency benchmark report")
    parser.add_argument("input_json")
    parser.add_argument("--markdown", default="")
    parser.add_argument("--html", default="")
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    if args.markdown:
        path = Path(args.markdown)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generate_markdown_report(payload), encoding="utf-8")
    if args.html:
        path = Path(args.html)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generate_html_report(payload), encoding="utf-8")
    if not args.markdown and not args.html:
        print(generate_markdown_report(payload))
    return 0


def _compact_table(modes: dict[str, Any]) -> str:
    headers = "mode | tasks | success_rate | avg_quality | total_tokens | tokens_saved_pct | cost_saved_pct | avg_latency"
    sep = "--- | ---: | ---: | ---: | ---: | ---: | ---: | ---:"
    rows = [headers, sep]
    for mode, values in sorted(modes.items()):
        rows.append(
            " | ".join(
                [
                    mode,
                    str(values.get("tasks", 0)),
                    f"{float(values.get('success_rate', 0.0)):.3f}",
                    f"{float(values.get('avg_quality', 0.0)):.3f}",
                    str(values.get("total_tokens", 0)),
                    f"{float(values.get('tokens_saved_pct', 0.0)):.2f}",
                    f"{float(values.get('cost_saved_pct', 0.0)):.2f}",
                    f"{float(values.get('avg_latency', 0.0)):.4f}",
                ]
            )
        )
    return "\n".join(rows)


def _visibility_table(modes: dict[str, Any]) -> str:
    headers = (
        "mode | input_saved_pct | output_saved_pct | quality_gain | latency_saved_pct | "
        "processing_speedup | cost_per_quality_point | quality_per_1000_tokens"
    )
    sep = "--- | ---: | ---: | ---: | ---: | ---: | ---: | ---:"
    rows = [headers, sep]
    for mode, values in sorted(modes.items()):
        rows.append(
            " | ".join(
                [
                    mode,
                    f"{float(values.get('input_tokens_saved_pct', 0.0)):.2f}",
                    f"{float(values.get('output_tokens_saved_pct', 0.0)):.2f}",
                    f"{float(values.get('quality_gain', 0.0)):.3f}",
                    f"{float(values.get('latency_saved_pct', 0.0)):.2f}",
                    f"{float(values.get('processing_speedup', 0.0)):.3f}",
                    f"{float(values.get('cost_per_quality_point', 0.0)):.8f}",
                    f"{float(values.get('quality_per_1000_tokens', 0.0)):.4f}",
                ]
            )
        )
    return "\n".join(rows)


def _metric_lines(modes: dict[str, Any], key: str, *, suffix: str = "") -> list[str]:
    if not modes:
        return ["- No mode data available."]
    return [f"- `{mode}`: {values.get(key, 0)}{suffix}" for mode, values in sorted(modes.items())]


def _routing_lines(results: list[dict[str, Any]]) -> list[str]:
    if not results:
        return ["- No route results available."]
    lines = []
    for result in results:
        if result.get("mode") != "aura_full":
            continue
        lines.append(
            f"- `{result.get('task_id')}`: route `{result.get('route')}`, model `{result.get('model')}`, "
            f"expected `{result.get('expected_route')}`"
        )
    return lines or ["- No Aura full route results available."]


def _unsafe_lines(results: list[dict[str, Any]]) -> list[str]:
    unsafe = [item for item in results if item.get("metadata", {}).get("task", {}).get("metadata", {}).get("unsafe_attempt")]
    if not unsafe:
        unsafe = [item for item in results if "unsafe" in str(item.get("task_id", "")).lower()]
    if not unsafe:
        return ["- No unsafe patch attempt tasks were present."]
    return [
        f"- `{item.get('mode')}/{item.get('task_id')}`: blocked={item.get('unsafe_blocked')} route=`{item.get('route')}`"
        for item in unsafe
    ]


def _best_examples(results: list[dict[str, Any]]) -> list[str]:
    if not results:
        return ["- No examples available."]
    selected = sorted(results, key=lambda item: float(item.get("quality_score", 0.0)), reverse=True)[:3]
    return [
        f"- `{item.get('mode')}/{item.get('task_id')}` quality={item.get('quality_score')} "
        f"tokens_saved_pct={item.get('tokens_saved_pct')}"
        for item in selected
    ]


def _prompt_excerpts(results: list[dict[str, Any]]) -> list[str]:
    raw = next((item for item in results if item.get("mode") == "raw_baseline"), None)
    aura = next((item for item in results if item.get("mode") == "aura_full"), None)
    lines: list[str] = []
    for label, result in (("Raw", raw), ("Aura", aura)):
        prompt = ""
        if result:
            prompt = str(result.get("metadata", {}).get("prompt_sent", "") or "")
        excerpt = prompt[:700].replace("```", "` ` `")
        lines.extend([f"### {label}", "", "```text", excerpt, "```", ""])
    return lines


def _markdown_line_to_html(line: str) -> str:
    if line.startswith("# "):
        return f"<h1>{escape(line[2:])}</h1>"
    if line.startswith("## "):
        return f"<h2>{escape(line[3:])}</h2>"
    if line.startswith("### "):
        return f"<h3>{escape(line[4:])}</h3>"
    if line.startswith("- "):
        return f"<li>{escape(line[2:])}</li>"
    if "|" in line and not line.startswith("```"):
        return f"<pre>{escape(line)}</pre>"
    if line.startswith("```"):
        return "<pre>" if line == "```text" else "</pre>"
    if not line:
        return ""
    return f"<p>{escape(line)}</p>"


if __name__ == "__main__":
    raise SystemExit(main())
