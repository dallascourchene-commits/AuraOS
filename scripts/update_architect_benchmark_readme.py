"""Render measured Architect benchmark evidence into README.md.

The helper is intentionally side-effect free: it reads committed README content,
replaces only marked benchmark blocks, and writes a candidate file for review or
CI comparison. It never commits, pushes, merges, or mutates production state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PLANNING_START = "<!-- AURA_ARCHITECT_PLANNING_BENCHMARK:START -->"
PLANNING_END = "<!-- AURA_ARCHITECT_PLANNING_BENCHMARK:END -->"
REAL_START = "<!-- AURA_REAL_REFACTOR_TRIAL:START -->"
REAL_END = "<!-- AURA_REAL_REFACTOR_TRIAL:END -->"
CODE_QUALITY_START = "<!-- AURA_REFACTOR_CODE_QUALITY:START -->"
CODE_QUALITY_END = "<!-- AURA_REFACTOR_CODE_QUALITY:END -->"


def _replace_marked(text: str, start: str, end: str, block: str) -> str:
    rendered = f"{start}\n{block.rstrip()}\n{end}"
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError(f"benchmark markers must occur exactly once: {start}, {end}")
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        return before.rstrip() + "\n\n" + rendered + after
    return text


def _percent_statement(label: str, value: float) -> str:
    if value >= 0:
        return f"{label} was **{value:.2f}% lower** than broad context."
    return f"{label} was **{abs(value):.2f}% higher** than broad context."


def render_planning(report: dict[str, Any]) -> str:
    arms = dict(report["arms"])
    raw = dict(arms["raw_broad_context"])
    sliced = dict(arms["aura_slice_single"])
    council = dict(arms["aura_architect_council"])
    comparison = dict(report["comparison"])
    selected = dict(council.get("selected_plan") or {})
    profile = dict(selected.get("length_profile") or council.get("length_profile") or {})
    usage = dict(council.get("model_usage") or {})
    findings = {
        str(item.get("id")): dict(item)
        for item in list(report.get("findings") or [])
        if isinstance(item, dict)
    }
    lost_fields = list(findings.get("F5_PLAN_CONTRACT_LOSS", {}).get("lost_fields") or [])
    contract = (
        "all submitted plan-level governance fields preserved"
        if not lost_fields
        else "missing: " + ", ".join(str(item) for item in lost_fields)
    )
    roles = dict(report.get("role_token_totals") or report.get("council_role_totals") or {})
    role_lines = [
        "| Role | Calls | Estimated input | Estimated output |",
        "|---|---:|---:|---:|",
    ]
    for role in ("planner", "planner_alt", "shadow", "judge"):
        item = dict(roles.get(role) or {})
        if not item:
            continue
        role_lines.append(
            f"| {role.replace('_', ' ').title()} | {int(item.get('calls') or 0)} | "
            f"{int(item.get('input_tokens_estimated') or item.get('input_tokens') or 0):,} | "
            f"{int(item.get('output_tokens_estimated') or item.get('output_tokens') or 0):,} |"
        )
    completion = dict(report.get("fixture_completion") or {})
    aliases = dict(completion.get("added_long_critic_aliases") or {})
    alias_text = ", ".join(f"{lane}→{source}" for lane, source in sorted(aliases.items()))
    prompt_count = int(dict(report.get("prompt_manifest") or {}).get("entry_count") or 0)
    measured_head = str(report.get("repository_commit_sha") or "UNAVAILABLE")
    lines = [
        "## Planning Benchmarks",
        "",
        "**Status:** reproducible fixture-based planning benchmark; no production mutation.  ",
        f"**Measured code head:** `{measured_head}`.  ",
        "**Tokens:** deterministic char/4 proxies; normalized cost is comparative, not a provider invoice.",
        "",
        "| Arm | Calls | Input token proxy | Output token proxy | Total token proxy | Grounded-plan quality | Normalized cost* |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Broad-context single planner | {raw['model_calls']} | {raw['input_tokens']:,} | {raw['output_tokens']:,} | {raw['total_tokens']:,} | {raw['quality']['quality_score']:.4f} | ${raw['normalized_cost_usd']:.6f} |",
        f"| **Aura-slice single planner** | **{sliced['model_calls']}** | **{sliced['input_tokens']:,}** | **{sliced['output_tokens']:,}** | **{sliced['total_tokens']:,}** | **{sliced['quality']['quality_score']:.4f}** | **${sliced['normalized_cost_usd']:.6f}** |",
        f"| Length-aware Architect Council V2 | {council['model_calls']} | {council['input_tokens']:,} | {council['output_tokens']:,} | {council['total_tokens']:,} | **{council['quality']['quality_score']:.4f}** | ${council['normalized_cost_usd']:.6f} |",
        "",
        "\*Normalized cost uses a declared $1/M input and $3/M output proxy rate card.",
        "",
        "### Current measured findings",
        "",
        f"- Aura slices reduced input-token proxy by **{float(comparison['slice_input_reduction_pct']):.2f}%** and total-token proxy by **{float(comparison['slice_total_reduction_pct']):.2f}%** versus broad context.",
        f"- The sliced plan changed grounded-plan quality by **{float(comparison['slice_quality_delta']):+.4f}**.",
        f"- {_percent_statement('Council total-token proxy', float(comparison['council_total_reduction_pct']))}",
        f"- The Council changed grounded-plan quality by **{float(comparison['council_quality_delta']):+.4f}**.",
        f"- Selected plan profile: **{profile.get('length_class', 'UNKNOWN')}**, {int(profile.get('task_count') or 0)} tasks, {int(profile.get('distinct_file_count') or 0)} distinct files.",
        f"- Governance contract: **{contract}**.",
        f"- Call accounting: **{int(usage.get('attempted_call_count') or council['model_calls'])} attempted, {int(usage.get('call_count') or council['model_calls'])} recorded, {int(usage.get('failed_call_count') or 0)} failed**.",
        f"- Prompt manifest: **{prompt_count} exact entries**.",
        "",
        "### Council role accounting",
        "",
        *role_lines,
        "",
        "### Fixture and claim boundary",
        "",
        (
            f"The long-plan critic lanes use explicit deterministic fixture aliases ({alias_text}). "
            if alias_text
            else ""
        )
        + "These are reproducible fixture invocations, not independent live-provider responses. The benchmark supports context-selection and controlled planning comparisons for this measured head; it does not establish general model superiority, provider-billed savings, consciousness, or production readiness.",
    ]
    return "\n".join(lines)


def render_real_trial(trial: dict[str, Any]) -> str:
    evidence = dict(trial.get("execution_evidence") or {})
    record = dict(trial.get("code_quality_record") or {})
    comparison = dict(trial.get("plan_comparison") or {})
    visible = dict(evidence.get("visible_junit") or {})
    hidden = dict(evidence.get("hidden_junit") or {})
    regression = dict(evidence.get("regression_junit") or {})
    gates = dict(evidence.get("gates") or {})
    gate_names = (
        "compile",
        "api_compatibility",
        "security",
        "static_analysis",
        "container_build",
        "selected_plan_bound_to_arena",
        "local_output_vault",
        "record_redaction",
    )
    gate_summary = ", ".join(f"{name}={gates.get(name, 'NOT_MEASURED')}" for name in gate_names)
    return "\n".join(
        [
            "### Latest real AuraOS refactor trial",
            "",
            f"**Measured code head:** `{evidence.get('head_sha') or 'UNAVAILABLE'}`.  ",
            f"**Selected plan:** `{comparison.get('selected_candidate_id') or 'UNAVAILABLE'}`; expected selection match: **{bool(trial.get('selected_plan_match'))}**.  ",
            f"**Working status:** `{record.get('working_status') or 'UNAVAILABLE'}`; disposition: `{trial.get('disposition') or record.get('disposition') or 'UNAVAILABLE'}`.",
            "",
            "| Gate family | Passed | Total | Failures | Errors |",
            "|---|---:|---:|---:|---:|",
            f"| Visible/property | {visible.get('passed')} | {visible.get('tests')} | {visible.get('failures')} | {visible.get('errors')} |",
            f"| Review-derived adversarial | {hidden.get('passed')} | {hidden.get('tests')} | {hidden.get('failures')} | {hidden.get('errors')} |",
            f"| Focused regression | {regression.get('passed')} | {regression.get('tests')} | {regression.get('failures')} | {regression.get('errors')} |",
            "",
            f"- Observed quality: **{float(record.get('observed_quality_score') or 0):.2f}**.",
            f"- Benchmark quality: **{float(record.get('benchmark_quality_score') or 0):.2f}**.",
            f"- Measurement completeness: **{float(record.get('measurement_completeness_pct') or 0):.1f}%**.",
            f"- Patch digest: `{evidence.get('patch_digest') or 'UNAVAILABLE'}`.",
            f"- Required gates: {gate_summary}.",
            "",
            "This trial is a real branch refactor with held-out and review-derived tests, but the planning arms are frozen assisted artifacts rather than blinded independent-provider generations. Performance and calibrated maintainability remain unmeasured.",
        ]
    )


def update_readme(
    readme_text: str,
    *,
    planning_report: dict[str, Any] | None = None,
    real_trial: dict[str, Any] | None = None,
) -> str:
    text = readme_text
    if planning_report is not None:
        block = render_planning(planning_report)
        if PLANNING_START not in text:
            section_start = text.find("## Planning Benchmarks")
            section_end = text.find(CODE_QUALITY_START)
            if section_start < 0 or section_end < 0 or section_end <= section_start:
                raise ValueError("README planning section boundary not found")
            text = (
                text[:section_start].rstrip()
                + "\n\n"
                + PLANNING_START
                + "\n"
                + block
                + "\n"
                + PLANNING_END
                + "\n\n"
                + text[section_end:]
            )
        else:
            text = _replace_marked(text, PLANNING_START, PLANNING_END, block)
    if real_trial is not None:
        block = render_real_trial(real_trial)
        if REAL_START not in text:
            if CODE_QUALITY_END not in text:
                raise ValueError("README code-quality end marker not found")
            insertion = f"{REAL_START}\n{block}\n{REAL_END}\n"
            text = text.replace(CODE_QUALITY_END, insertion + CODE_QUALITY_END, 1)
        else:
            text = _replace_marked(text, REAL_START, REAL_END, block)
    return text.rstrip() + "\n"


def _load(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--planning-report", type=Path)
    parser.add_argument("--real-trial", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark-output/README.updated.md"),
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    readme = args.readme if args.readme.is_absolute() else root / args.readme
    target = args.output if args.output.is_absolute() else root / args.output
    planning_path = (
        args.planning_report
        if args.planning_report is None or args.planning_report.is_absolute()
        else root / args.planning_report
    )
    real_path = (
        args.real_trial
        if args.real_trial is None or args.real_trial.is_absolute()
        else root / args.real_trial
    )
    rendered = update_readme(
        readme.read_text(encoding="utf-8"),
        planning_report=_load(planning_path),
        real_trial=_load(real_path),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
