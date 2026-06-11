"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Honest Measurement)
DEPENDENCIES: argparse, ast, json, os, re, time, difflib, aura_substrate, aura_llm_egress
FUNCTIONS: QualityScorer, run_arm, run_benchmark, write_reports, main
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura A/B Proxy Benchmark (real LLM only).
=========================================

Real-LLM A/B split test for the Aura orchestration-substrate thesis. Both arms
send the SAME task to the SAME external LLM (Aura never runs a model herself):

  RAW  : human prompt + full file context  -> external LLM.
         (no substrate, no packet, no guardrails, no context surgery)

  AURA : human prompt -> aura_substrate.AuraSubstrate.compile() [NO LLM, instant]
         -> compact polysynthetic packet + .aura/ guardrails + surgical context
         -> aura_llm_egress.ExternalLLM  (the same external model).

We measure, per arm: input tokens (char/4), latency, est. cost, context leakage
(source lines/chars exposed to the model), and deterministic quality of the REAL
output (format, parseability, no fabricated files, no forbidden deps, signature
preservation, blast radius).

No mock model is used. Gemini and any internal/local engine are excluded by the
egress layer. Default provider order: Mistral -> SambaNova.

Run:
    python3 aura_proxy_benchmark.py --task mesh_offload
    python3 aura_proxy_benchmark.py --task mesh_offload --provider sambanova
    python3 aura_proxy_benchmark.py --list-tasks
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, replace

from aura_substrate import (
    REPO_ROOT,
    AuraSubstrate,
    ContextBundle,
    ContextSelector,
    estimate_tokens,
    existing_import_roots,
    extract_function_source,
    sanitize_code,
)
from aura_llm_egress import ExternalLLM

REPORT_DIR = os.path.join(REPO_ROOT, "Aura_Memory", "benchmarks")

_STDLIB_ROOTS = frozenset({
    "ast", "os", "sys", "json", "re", "time", "math", "asyncio", "sqlite3",
    "hashlib", "struct", "pathlib", "collections", "urllib", "subprocess",
    "gc", "io", "shutil", "random", "socket", "ctypes", "importlib",
    "threading", "uuid", "tempfile", "contextlib", "base64", "difflib",
    "functools", "itertools", "typing", "datetime", "logging", "dataclasses",
    "enum", "abc", "copy", "traceback", "inspect", "warnings",
})


# --------------------------------------------------------------------------- #
# Task definition
# --------------------------------------------------------------------------- #

@dataclass
class TestCase:
    key: str
    human_prompt: str
    target_file: str
    target_func: str
    output_format: str          # "unified_diff" | "python" | "json" | "text"
    packet_tags: list[str]
    extra_context_files: list[str] = field(default_factory=list)
    task_type: str = "patch"    # taxonomy for per-task model routing


TASKS: dict[str, TestCase] = {
    "mesh_offload": TestCase(
        key="mesh_offload",
        human_prompt=(
            "Can you fix or improve the mesh offload function without adding any "
            "new dependencies, and preserve the existing packet protocol?"
        ),
        target_file="aura_mesh.py",
        target_func="offload_compute",
        output_format="unified_diff",
        packet_tags=[
            "ENV:PYTHON", "OP:PATCH", "DOMAIN:MESH", "TARGET:OFFLOAD_COMPUTE",
            "CONSTRAINT:NO_NEW_DEPS", "CONSTRAINT:PRESERVE_PROTOCOL",
            "VERIFY:AST_PARSE", "OUTPUT:UNIFIED_DIFF",
        ],
        task_type="patch",
    ),
    # Isolated sandbox task — calibration/refactor rehearsal that never touches
    # Aura's own source files.
    "sandbox_score": TestCase(
        key="sandbox_score",
        human_prompt=(
            "Fix compute_score so it applies the weight and guards against an empty "
            "list, without adding new dependencies and preserving the signature."
        ),
        target_file="Aura_Sandbox/sample_target.py",
        target_func="compute_score",
        output_format="unified_diff",
        packet_tags=[
            "ENV:PYTHON", "OP:PATCH", "DOMAIN:SANDBOX", "TARGET:COMPUTE_SCORE",
            "CONSTRAINT:NO_NEW_DEPS", "CONSTRAINT:PRESERVE_PROTOCOL",
            "VERIFY:AST_PARSE", "OUTPUT:UNIFIED_DIFF",
        ],
        task_type="patch",
    ),
}


# Compact output modes. Each maps to the packet [OUTPUT:...] tag the model is
# told to use and the scorer format it is graded against. JSON_EDIT_PLAN is the
# output-token-efficient mode: the model returns minimal line edits, Aura
# validates + expands them locally into a standard diff.
OUTPUT_MODES: dict[str, dict] = {
    "unified_diff": {"tag": "OUTPUT:UNIFIED_DIFF", "format": "unified_diff"},
    "json_edit_plan": {"tag": "OUTPUT:JSON_EDIT_PLAN", "format": "json_edit_plan"},
}


def with_output_mode(task: TestCase, mode: str) -> TestCase:
    """Return a task variant whose packet OUTPUT tag + scorer format match `mode`."""
    if mode not in OUTPUT_MODES:
        raise ValueError(f"Unknown output mode '{mode}'. Valid: {list(OUTPUT_MODES)}")
    spec = OUTPUT_MODES[mode]
    new_tags = [t for t in task.packet_tags if not t.startswith("OUTPUT:")] + [spec["tag"]]
    return replace(task, packet_tags=new_tags, output_format=spec["format"])


# --------------------------------------------------------------------------- #
# Quality scorer (objective, deterministic checks on the REAL output)
# --------------------------------------------------------------------------- #

_PY_FILE_RE = re.compile(r"[A-Za-z0-9_./-]+\.py")
_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.]+))", re.M)
_CODE_FENCE_RE = re.compile(r"```(?:python|diff)?\s*(.*?)```", re.DOTALL)


def _strip_fences(output: str) -> str:
    m = _CODE_FENCE_RE.search(output)
    return m.group(1).strip() if m else output.strip()


def _apply_unified_diff(original: str, diff_text: str) -> tuple[str | None, str]:
    """Minimal unified-diff applier. Returns (patched_text, note)."""
    orig_lines = original.splitlines()
    out: list[str] = []
    cursor = 0
    diff_lines = diff_text.splitlines()
    i = 0
    applied_any = False
    while i < len(diff_lines):
        line = diff_lines[i]
        if line.startswith("@@"):
            m = re.search(r"@@\s*-(\d+)(?:,(\d+))?\s*\+(\d+)(?:,(\d+))?\s*@@", line)
            if not m:
                return None, f"bad hunk header: {line}"
            start = max(0, int(m.group(1)) - 1)
            if start > len(orig_lines):
                return None, "hunk start beyond file"
            out.extend(orig_lines[cursor:start])
            cursor = start
            i += 1
            while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
                hl = diff_lines[i]
                if hl.startswith("--- ") or hl.startswith("+++ "):
                    i += 1
                    continue
                tag, body = (hl[0], hl[1:]) if hl else (" ", "")
                if tag == " ":
                    if cursor < len(orig_lines):
                        out.append(orig_lines[cursor])
                        cursor += 1
                elif tag == "-":
                    if cursor < len(orig_lines):
                        cursor += 1
                    applied_any = True
                elif tag == "+":
                    out.append(body)
                    applied_any = True
                else:
                    if cursor < len(orig_lines):
                        out.append(orig_lines[cursor])
                        cursor += 1
                i += 1
        else:
            i += 1
    out.extend(orig_lines[cursor:])
    if not applied_any:
        return None, "no hunk content applied"
    return "\n".join(out), "ok"


_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_edit_plan(output: str) -> tuple[dict | None, str]:
    """Parse a JSON_EDIT_PLAN from model output (tolerates fences/prose)."""
    body = _strip_fences(output)
    candidates = [body]
    m = _JSON_OBJ_RE.search(body)
    if m:
        candidates.append(m.group(0))
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("edits"), list):
            return obj, "ok"
    return None, "no valid JSON edit plan found"


def _valid_edit(e: dict) -> bool:
    return (isinstance(e, dict)
            and isinstance(e.get("file"), str)
            and isinstance(e.get("start_line"), int)
            and isinstance(e.get("end_line"), int)
            and e["start_line"] >= 1 and e["end_line"] >= e["start_line"]
            and isinstance(e.get("replacement"), str))


def apply_edit_plan(original: str, plan: dict) -> tuple[str | None, str]:
    """Validate + apply a JSON edit plan to original source. Returns (patched, note).

    Aura's deterministic expansion of the compact plan into a real artifact.
    """
    edits = plan.get("edits")
    if not isinstance(edits, list) or not edits:
        return None, "empty edit list"
    for e in edits:
        if not _valid_edit(e):
            return None, f"invalid edit object: {e}"
    lines = original.splitlines()
    n = len(lines)
    # apply from the bottom up so earlier line numbers stay valid
    for e in sorted(edits, key=lambda x: x["start_line"], reverse=True):
        s, en = e["start_line"], e["end_line"]
        if s > n + 1 or en > n:
            return None, f"edit line range {s}-{en} out of bounds (file has {n} lines)"
        repl = e["replacement"].split("\n")
        lines[s - 1:en] = repl
    return "\n".join(lines), "ok"


def edit_plan_to_unified_diff(original: str, plan: dict, path: str) -> str:
    """Deterministically expand an edit plan into a standard unified diff."""
    import difflib
    patched, note = apply_edit_plan(original, plan)
    if patched is None:
        return f"# edit plan did not apply: {note}"
    diff = difflib.unified_diff(
        original.splitlines(), patched.splitlines(),
        fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="")
    return "\n".join(diff)


class QualityScorer:
    def __init__(self, repo_files: set[str], allowed_import_roots: set[str],
                 original_source: str, target_func: str = ""):
        self.repo_files = repo_files
        self.allowed = allowed_import_roots | _STDLIB_ROOTS
        self.original_source = original_source
        self.target_func = target_func
        self.original_slice, self.original_sig = self._original_func_info()

    def _original_func_info(self) -> tuple[str, str]:
        if not self.target_func:
            return "", ""
        src, _, _ = extract_function_source(self.original_source, self.target_func)
        if not src:
            return "", ""
        return src, src.splitlines()[0].strip()

    def score(self, output: str | None, task: TestCase) -> dict:
        checks: dict[str, bool] = {}
        notes: list[str] = []
        if not output:
            return {"score": 0.0, "checks": {}, "notes": ["empty output"],
                    "metrics": {"blast_radius_lines": 0}}

        produced_code, code_note = self._extract_code(output, task)
        if code_note:
            notes.append(code_note)

        checks["format_ok"] = self._format_ok(output, task.output_format, notes)
        checks["parses_ok"] = self._parses_ok(produced_code, notes)
        checks["no_fake_files"] = self._no_fake_files(output, notes)
        checks["no_forbidden_deps"] = self._no_forbidden_deps(output, task, notes)
        checks["preserves_signature"] = self._preserves_signature(produced_code, notes)
        minimal, blast = self._minimal_scope(output, produced_code, task, notes)
        checks["minimal_scope"] = minimal

        score = round(sum(1 for v in checks.values() if v) / len(checks), 3)
        return {"score": score, "checks": checks, "notes": notes,
                "metrics": {"blast_radius_lines": blast}}

    def _extract_code(self, output: str, task: TestCase) -> tuple[str, str]:
        output = sanitize_code(output)[0]  # deterministic ASCII fix before parsing
        if task.output_format == "json_edit_plan":
            plan, note = parse_edit_plan(output)
            if plan is None:
                return "", note
            patched, anote = apply_edit_plan(self.original_source, plan)
            if patched is None:
                return "", f"edit plan invalid: {anote}"
            return patched, ""
        if task.output_format == "unified_diff" and ("@@" in output and "--- " in output):
            diff_body = output
            fence = _CODE_FENCE_RE.search(output)
            if fence and "@@" in fence.group(1):
                diff_body = fence.group(1)
            patched, note = _apply_unified_diff(self.original_source, diff_body)
            if patched is not None:
                return patched, ""
            recovered = self._recover_from_diff(diff_body)
            if recovered.strip():
                return recovered, f"diff not applyable ({note}); scored on recovered code"
            return "", f"diff did not apply: {note}"
        return _strip_fences(output), ""

    @staticmethod
    def _recover_from_diff(diff_body: str) -> str:
        out: list[str] = []
        for ln in diff_body.splitlines():
            if ln.startswith(("--- ", "+++ ", "@@", "```")):
                continue
            if ln.startswith("-"):
                continue
            out.append(ln[1:] if ln.startswith(("+", " ")) else ln)
        return "\n".join(out)

    def _format_ok(self, output: str, fmt: str, notes: list[str]) -> bool:
        if fmt == "unified_diff":
            ok = ("--- " in output and "+++ " in output and "@@" in output)
            if not ok:
                notes.append("format: expected a unified diff (--- / +++ / @@) — not found")
            return ok
        if fmt == "python":
            try:
                ast.parse(_strip_fences(output))
                return True
            except SyntaxError:
                notes.append("format: expected parseable python block")
                return False
        if fmt == "json_edit_plan":
            plan, note = parse_edit_plan(output)
            if plan is None:
                notes.append(f"format: expected JSON edit plan — {note}")
                return False
            if not all(_valid_edit(e) for e in plan["edits"]) or not plan["edits"]:
                notes.append("format: edit plan has invalid/empty edits")
                return False
            return True
        if fmt == "json":
            try:
                json.loads(_strip_fences(output))
                return True
            except Exception:
                notes.append("format: expected valid JSON")
                return False
        return True

    def _parses_ok(self, produced_code: str, notes: list[str]) -> bool:
        if not produced_code.strip():
            notes.append("no parseable code produced")
            return False
        try:
            ast.parse(produced_code)
            return True
        except SyntaxError:
            try:
                ast.parse("class _S:\n" + "\n".join("    " + ln for ln in produced_code.splitlines()))
                return True
            except SyntaxError as e:
                notes.append(f"produced code does not parse: {e}")
                return False

    def _no_fake_files(self, output: str, notes: list[str]) -> bool:
        fabricated = []
        for ref in set(_PY_FILE_RE.findall(output)):
            base = os.path.basename(ref.replace("a/", "").replace("b/", ""))
            if base not in self.repo_files:
                fabricated.append(base)
        if fabricated:
            notes.append(f"fabricated file refs: {sorted(set(fabricated))}")
            return False
        return True

    def _no_forbidden_deps(self, output: str, task: TestCase, notes: list[str]) -> bool:
        constraint = any("NO_NEW_DEPS" in t for t in task.packet_tags)
        if not constraint and "without" not in task.human_prompt.lower():
            return True
        added_roots: set[str] = set()
        for line in output.splitlines():
            if line.startswith("-"):
                continue
            stripped = line.lstrip("+").strip() if line.startswith("+") else line
            m = _IMPORT_RE.match(stripped if stripped.startswith(("import", "from")) else line)
            if m:
                root = (m.group(1) or m.group(2) or "").split(".")[0]
                if root:
                    added_roots.add(root)
        forbidden = {r for r in added_roots if r not in self.allowed}
        if forbidden:
            notes.append(f"forbidden new deps: {sorted(forbidden)}")
            return False
        return True

    def _preserves_signature(self, produced_code: str, notes: list[str]) -> bool:
        if not self.original_sig:
            return True
        if re.sub(r"\s+", " ", self.original_sig) in re.sub(r"\s+", " ", produced_code):
            return True
        notes.append("target signature/protocol not preserved verbatim")
        return False

    def _minimal_scope(self, output: str, produced_code: str, task: TestCase,
                       notes: list[str]) -> tuple[bool, int]:
        if task.output_format == "json_edit_plan":
            plan, _ = parse_edit_plan(output)
            if plan is None:
                return False, 0
            blast = sum(len(e.get("replacement", "").split("\n"))
                        for e in plan["edits"] if _valid_edit(e))
            limit = 12
            ok = 0 < blast <= limit
            if not ok:
                notes.append(f"edit-plan scope: {blast} replacement lines (limit {limit})")
            return ok, blast
        if task.output_format == "unified_diff" and "@@" in output:
            blast = sum(1 for ln in output.splitlines()
                        if ln.startswith("+") and not ln.startswith("+++"))
            limit = 12
        else:
            orig_n = len([l for l in self.original_slice.splitlines() if l.strip()])
            new_n = len([l for l in produced_code.splitlines() if l.strip()])
            blast = max(0, new_n - orig_n)
            limit = max(6, orig_n // 2)
        ok = blast <= limit
        if not ok:
            notes.append(f"over-engineered: +{blast} lines (limit {limit}) — scope creep")
        return ok, blast


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def _repo_py_files() -> set[str]:
    files = {f for f in os.listdir(REPO_ROOT) if f.endswith(".py")}
    sandbox = os.path.join(REPO_ROOT, "Aura_Sandbox")
    if os.path.isdir(sandbox):
        files |= {f for f in os.listdir(sandbox) if f.endswith(".py")}
    return files


def run_arm(arm: str, prompt: str, ctx: ContextBundle, egress: ExternalLLM,
            scorer: QualityScorer, task: TestCase, packet: str | None = None,
            compile_ms: float = 0.0) -> dict:
    in_tokens = estimate_tokens(prompt)
    text, err, latency = egress.generate(prompt)
    out_tokens = estimate_tokens(text or "")
    quality = scorer.score(text, task)
    return {
        "arm": arm,
        "packet": packet,
        "substrate_compile_ms": round(compile_ms, 3),
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "latency_sec": round(latency, 3),
        "est_cost_usd": egress.cost(in_tokens, out_tokens),
        "exposed_files": ctx.exposed_files,
        "exposed_source_lines": ctx.exposed_lines,
        "exposed_source_chars": ctx.exposed_chars,
        "quality_score": quality["score"],
        "quality_checks": quality["checks"],
        "quality_notes": quality["notes"],
        "blast_radius_lines": quality.get("metrics", {}).get("blast_radius_lines", 0),
        "error": err,
        "output": text,
        "prompt": prompt,
    }


def run_benchmark(task_key: str, provider_name: str | None, model: str | None,
                  output_mode: str = "unified_diff") -> dict:
    if task_key not in TASKS:
        raise SystemExit(f"Unknown task '{task_key}'. Known: {list(TASKS)}")
    task = with_output_mode(TASKS[task_key], output_mode)

    egress = ExternalLLM(provider=provider_name, model=model)

    selector = ContextSelector()
    substrate = AuraSubstrate()

    original_source = selector.read(task.target_file)
    allowed_roots = existing_import_roots(original_source)
    scorer = QualityScorer(_repo_py_files(), allowed_roots, original_source,
                           target_func=task.target_func)

    # RAW arm — no substrate at all: human prompt + full file dumped to the model.
    raw_ctx = selector.raw_context(task.target_file, task.extra_context_files)
    raw_prompt = f"{task.human_prompt}\n\nHere is the relevant code:\n\n{raw_ctx.text}\n"

    # AURA arm — substrate compiles (NO LLM) then we forward to the same model.
    pkg = substrate.compile(
        task.human_prompt,
        target_file=task.target_file,
        target_func=task.target_func,
        explicit_tags=task.packet_tags,
    )

    print(f"[*] Egress provider: {egress.provider} ({egress.model})")
    print(f"[*] Task: {task.key} -> {task.target_file}:{task.target_func}")
    print(f"[*] Substrate compiled in {pkg.compile_ms} ms (llm_used={pkg.meta['llm_used']})")
    print(f"[*] Polysynthetic packet: {pkg.packet}")
    print("[*] Running RAW arm (no Aura substrate)...")
    raw = run_arm("raw", raw_prompt, raw_ctx, egress, scorer, task)
    print(f"    raw: {raw['input_tokens']} in-tokens, quality={raw['quality_score']}, err={raw['error']}")
    print("[*] Running AURA arm (substrate packet + guardrails + surgical context)...")
    aura = run_arm("aura", pkg.prompt, pkg.context, egress, scorer, task,
                   packet=pkg.packet, compile_ms=pkg.compile_ms)
    print(f"    aura: {aura['input_tokens']} in-tokens, quality={aura['quality_score']}, err={aura['error']}")

    reduction = 0.0
    if raw["input_tokens"]:
        reduction = round((raw["input_tokens"] - aura["input_tokens"]) / raw["input_tokens"] * 100, 1)
    # Guardrails are a fixed, cacheable system-prompt cost; report the amortized
    # reduction (packet + surgical context only) too, since in a real proxy the
    # guardrails are sent once and reused across many requests.
    guardrail_tokens = estimate_tokens(pkg.guardrails)
    aura_ex_guardrail_tokens = max(0, aura["input_tokens"] - guardrail_tokens)
    reduction_amortized = 0.0
    if raw["input_tokens"]:
        reduction_amortized = round(
            (raw["input_tokens"] - aura_ex_guardrail_tokens) / raw["input_tokens"] * 100, 1)
    leak_reduction = 0.0
    if raw["exposed_source_lines"]:
        leak_reduction = round(
            (raw["exposed_source_lines"] - aura["exposed_source_lines"])
            / raw["exposed_source_lines"] * 100, 1)

    return {
        "task": task.key,
        "provider": egress.provider,
        "model": egress.model,
        "output_mode": task.output_format,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "architecture": "aura_substrate(no LLM) -> aura_llm_egress(external only)",
        "summary": {
            "raw_input_tokens": raw["input_tokens"],
            "aura_input_tokens": aura["input_tokens"],
            "aura_guardrail_tokens": guardrail_tokens,
            "aura_packet_context_tokens": aura_ex_guardrail_tokens,
            "token_reduction_pct": reduction,
            "token_reduction_amortized_pct": reduction_amortized,
            "substrate_compile_ms": aura["substrate_compile_ms"],
            "raw_latency_sec": raw["latency_sec"],
            "aura_latency_sec": aura["latency_sec"],
            "raw_est_cost_usd": raw["est_cost_usd"],
            "aura_est_cost_usd": aura["est_cost_usd"],
            "cost_saving_usd": round(raw["est_cost_usd"] - aura["est_cost_usd"], 6),
            "raw_exposed_lines": raw["exposed_source_lines"],
            "aura_exposed_lines": aura["exposed_source_lines"],
            "context_leak_reduction_pct": leak_reduction,
            "raw_quality_score": raw["quality_score"],
            "aura_quality_score": aura["quality_score"],
            "raw_blast_radius_lines": raw["blast_radius_lines"],
            "aura_blast_radius_lines": aura["blast_radius_lines"],
        },
        "raw": raw,
        "aura": aura,
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def write_reports(results: dict) -> tuple[str, str]:
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    base = f"{results['task']}_{results['provider']}_{stamp}"
    json_path = os.path.join(REPORT_DIR, base + ".json")
    md_path = os.path.join(REPORT_DIR, base + ".md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    s = results["summary"]
    raw, aura = results["raw"], results["aura"]

    def fmt_checks(c: dict) -> str:
        return ", ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in c.items()) or "n/a"

    md = f"""# Aura A/B Proxy Benchmark — `{results['task']}`

**Provider:** {results['provider']} (`{results['model']}`)
**Timestamp:** {results['timestamp']}
**Architecture:** {results['architecture']}
**Mode:** REAL LLM (no mock; Aura runs no model herself)

## Headline metrics

| Metric | RAW (no Aura) | AURA | Delta |
|---|---|---|---|
| Input tokens (with guardrails) | {s['raw_input_tokens']} | {s['aura_input_tokens']} | **{s['token_reduction_pct']}% reduction** |
| Input tokens (guardrails amortized) | {s['raw_input_tokens']} | {s['aura_packet_context_tokens']} | **{s['token_reduction_amortized_pct']}% reduction** |
| ↳ fixed guardrail overhead | — | {s['aura_guardrail_tokens']} | cacheable system prompt |
| Substrate compile (ms) | n/a | {s['substrate_compile_ms']} | local, no LLM |
| Latency (s) | {s['raw_latency_sec']} | {s['aura_latency_sec']} | — |
| Est. cost (USD) | {s['raw_est_cost_usd']} | {s['aura_est_cost_usd']} | save {s['cost_saving_usd']} |
| Exposed source lines | {s['raw_exposed_lines']} | {s['aura_exposed_lines']} | **{s['context_leak_reduction_pct']}% less leakage** |
| Quality score | {s['raw_quality_score']} | {s['aura_quality_score']} | — |
| Blast radius (changed lines) | {s['raw_blast_radius_lines']} | {s['aura_blast_radius_lines']} | smaller = more surgical |

## Polysynthetic task packet (Aura arm only)

```
{aura['packet']}
```

## Context exposed to the model

- **RAW:** files {raw['exposed_files']} — {raw['exposed_source_lines']} source lines, {raw['exposed_source_chars']} chars.
- **AURA:** files {aura['exposed_files']} — {aura['exposed_source_lines']} surgical lines (header index + target function only), {aura['exposed_source_chars']} chars.

## Quality breakdown (objective checks on the REAL model output)

- **RAW** quality {raw['quality_score']}: {fmt_checks(raw['quality_checks'])}
  - notes: {raw['quality_notes'] or 'none'}
- **AURA** quality {aura['quality_score']}: {fmt_checks(aura['quality_checks'])}
  - notes: {aura['quality_notes'] or 'none'}

## RAW model output

```
{(raw['output'] or '(empty / error: %s)' % raw['error'])[:4000]}
```

## AURA model output

```
{(aura['output'] or '(empty / error: %s)' % aura['error'])[:4000]}
```

## Interpretation

Aura's substrate compiled the request in **{s['substrate_compile_ms']} ms with no
LLM call**, then forwarded a compact packet to the external model. This reduced
input tokens by **{s['token_reduction_pct']}%** (or
**{s['token_reduction_amortized_pct']}%** once the fixed
{s['aura_guardrail_tokens']}-token guardrail block is treated as a cached system
prompt) and exposed **{s['context_leak_reduction_pct']}% fewer source lines**,
while the objective
quality score went from **{s['raw_quality_score']}** (raw) to
**{s['aura_quality_score']}** (aura). Quality is scored on format compliance,
code parseability, absence of fabricated files, absence of forbidden new
dependencies, signature/protocol preservation, and blast radius.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    return json_path, md_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _print_providers() -> None:
    from aura_llm_egress import classify_providers, PROVIDERS
    buckets = classify_providers()
    print("catalog:", ", ".join(PROVIDERS.keys()))
    print("working (have keys, verified):", ", ".join(buckets["working"]) or "(none)")
    print("configured (have keys, unverified):", ", ".join(buckets["configured"]) or "(none)")
    print("placeholders (no key yet, skipped):", ", ".join(buckets["placeholder"]) or "(none)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aura A/B proxy benchmark (real LLM)")
    p.add_argument("--task", default="mesh_offload", help="task key (see --list-tasks)")
    p.add_argument("--provider", default=None,
                   help="mistral | sambanova | groq | gemini | ... (internal/local "
                        "engines disabled). Default: try mistral then sambanova.")
    p.add_argument("--model", default=None, help="override provider model id")
    p.add_argument("--output-mode", default="unified_diff", choices=list(OUTPUT_MODES),
                   help="output artifact mode (compact json_edit_plan saves output tokens)")
    p.add_argument("--list-tasks", action="store_true")
    p.add_argument("--list-providers", action="store_true",
                   help="show catalog and which providers have usable keys")
    args = p.parse_args(argv)

    if args.list_providers:
        _print_providers()
        return 0
    if args.list_tasks:
        for k, t in TASKS.items():
            print(f"{k}: {t.target_file}:{t.target_func} [{t.output_format}]")
        return 0

    results = run_benchmark(args.task, args.provider, args.model, output_mode=args.output_mode)
    json_path, md_path = write_reports(results)
    s = results["summary"]
    print("\n=== A/B RESULT ===")
    print(f"  substrate compile     : {s['substrate_compile_ms']} ms (no LLM)")
    print(f"  token reduction       : {s['token_reduction_pct']}% "
          f"(guardrails amortized: {s['token_reduction_amortized_pct']}%)")
    print(f"  context leak reduction: {s['context_leak_reduction_pct']}%")
    print(f"  raw quality -> aura   : {s['raw_quality_score']} -> {s['aura_quality_score']}")
    print(f"  blast radius raw->aura: {s['raw_blast_radius_lines']} -> {s['aura_blast_radius_lines']}")
    print(f"  cost saving (USD)     : {s['cost_saving_usd']}")
    print(f"\n[+] JSON report: {json_path}")
    print(f"[+] MD   report: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
