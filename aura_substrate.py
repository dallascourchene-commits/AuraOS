"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Deterministic Substrate)
DEPENDENCIES: ast, json, os, re, time
FUNCTIONS: estimate_tokens, parse_master_key_header, extract_function_source, existing_import_roots, IntentCompressor, ContextSelector, AuraSubstrate
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Substrate — the LLM-free core.
===================================

Aura is an orchestration substrate, NOT a model. This module contains the
deterministic, instantly-fast machinery that runs with **zero LLM calls**:

  * intent compression      (verbose prose  -> polysynthetic bracketed packet)
  * surgical context select (topology / [AURA_MASTER_KEY] header + one function)
  * guardrail loading       (the deterministic Markdown in .aura/)
  * token accounting        (char/4 estimate)

Nothing here imports or invokes a language model. When Aura needs to *speak* or
have her data *interpreted* for a human, the caller hands the substrate output
to `aura_llm_egress.ExternalLLM` — the single external egress point. Keeping the
model out of the substrate is what makes Aura fast and reproducible.

CLI demo (no network, no model):
    python3 aura_substrate.py --demo
    python3 aura_substrate.py --demo --speak        # also calls external LLM egress
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import time
from dataclasses import dataclass, field

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
AURA_GUARDRAIL_DIR = os.path.join(REPO_ROOT, ".aura")
GUARDRAIL_ORDER = ["AURA.md", "ROLES.md", "SECURITY.md", "OUTPUT_FORMATS.md", "ARCHITECTURE.md"]


# --------------------------------------------------------------------------- #
# Deterministic token + header utilities (no model)
# --------------------------------------------------------------------------- #

def estimate_tokens(text: str) -> int:
    """Cheap char/4 token approximation (no external tokenizer in repo)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


_MASTER_KEY_RE = re.compile(r"\[AURA_MASTER_KEY\](.*?)\[/AURA_MASTER_KEY\]", re.DOTALL)


def parse_master_key_header(content: str) -> dict[str, str]:
    """Parse an [AURA_MASTER_KEY] header docstring into a small dict index."""
    block = _MASTER_KEY_RE.search(content or "")
    if not block:
        return {}
    body = block.group(1)
    out: dict[str, str] = {}
    for field_name in ("PWFST_ALIGNMENT", "DIKWP_TIER", "DEPENDENCIES", "FUNCTIONS"):
        m = re.search(rf"{field_name}:\s*(.+)", body)
        if m:
            out[field_name] = m.group(1).strip()
    return out


def extract_function_source(content: str, func_name: str) -> tuple[str | None, int, int]:
    """
    Return (source_slice, start_line, end_line) for a top-level or method
    function named `func_name`. 1-indexed inclusive lines. (None, 0, 0) if absent.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None, 0, 0
    lines = content.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            return "\n".join(lines[start - 1:end]), start, end
    return None, 0, 0


# Unicode punctuation LLMs love to emit inside code (breaks ast.parse). Mapping
# them back to ASCII is deterministic and safe for source patches.
_UNICODE_FIXES = {
    "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2212": "-",   # dashes / minus
    "\u2018": "'", "\u2019": "'", "\u201b": "'",                     # single quotes
    "\u201c": '"', "\u201d": '"', "\u201e": '"',                     # double quotes
    "\u2026": "...",                                                  # ellipsis
    "\u00a0": " ", "\u2009": " ", "\u202f": " ", "\u200b": "",       # spaces / zero-width
    "\u2032": "'", "\u2033": '"',                                     # primes
    "\u2192": "->", "\u21d2": "=>",                                   # arrows in comments
}


def sanitize_code(text: str) -> tuple[str, list[str]]:
    """Replace non-ASCII punctuation an LLM emitted in code with ASCII equivalents.

    Returns (clean_text, replacements). This is the deterministic first line of
    defence that stops patches failing the AST verifier purely because the model
    used an em-dash or smart quote in a comment/docstring.
    """
    replaced: list[str] = []
    out = text
    for bad, good in _UNICODE_FIXES.items():
        if bad in out:
            replaced.append(f"{bad!r}->{good!r}x{out.count(bad)}")
            out = out.replace(bad, good)
    return out, replaced


def existing_import_roots(content: str) -> set[str]:
    """Top-level import roots already present in a file (for dep-discipline checks)."""
    roots: set[str] = set()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return roots
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


# --------------------------------------------------------------------------- #
# Intent compressor  (verbose prose -> bracketed polysynthetic packet)
# --------------------------------------------------------------------------- #

_KEYWORD_TAGS = [
    (r"\bfix\b|\bbug\b|\bbroken\b", "OP:PATCH"),
    (r"\bimprove\b|\boptimi[sz]e\b|\brefactor\b", "OP:IMPROVE"),
    (r"\bwithout (adding )?(new )?dep", "CONSTRAINT:NO_NEW_DEPS"),
    (r"\bpreserve\b.*\bprotocol\b", "CONSTRAINT:PRESERVE_PROTOCOL"),
    (r"\bmesh\b", "DOMAIN:MESH"),
    (r"\bdiff\b|\bpatch\b", "OUTPUT:UNIFIED_DIFF"),
    (r"\bpython\b|\.py\b", "ENV:PYTHON"),
]


PACKET_STYLES = ("bracket", "json", "yaml", "hybrid")

# Tag keys treated as the "operative" core in hybrid style (rendered as brackets);
# everything else becomes structured metadata.
_HYBRID_OP_KEYS = {"OP", "DOMAIN", "TARGET", "ENV"}


def _group_tags(tags: list[str]) -> dict[str, list[str]]:
    """KEY:VALUE tags -> ordered {KEY: [values...]} (repeats become lists)."""
    grouped: dict[str, list[str]] = {}
    for t in tags:
        key, _, val = t.partition(":")
        grouped.setdefault(key, []).append(val)
    return grouped


def render_packet(tags: list[str], style: str = "bracket") -> str:
    """Render the same polysynthetic tag set in different surface syntaxes."""
    style = (style or "bracket").lower()
    if style not in PACKET_STYLES:
        raise ValueError(f"Unknown packet style '{style}'. Valid: {PACKET_STYLES}")

    if style == "bracket":
        return "".join(f"[{t}]" for t in tags)

    grouped = _group_tags(tags)

    if style == "json":
        obj = {k: (v[0] if len(v) == 1 else v) for k, v in grouped.items()}
        return json.dumps(obj, separators=(",", ":"))

    if style == "yaml":
        lines: list[str] = []
        for k, v in grouped.items():
            if len(v) == 1:
                lines.append(f"{k}: {v[0]}")
            else:
                lines.append(f"{k}:")
                lines.extend(f"  - {item}" for item in v)
        return "\n".join(lines)

    # hybrid: operative tags as brackets + remaining metadata as a JSON object
    bracket_part = "".join(f"[{t}]" for t in tags if t.partition(":")[0] in _HYBRID_OP_KEYS)
    meta = {k: (v[0] if len(v) == 1 else v)
            for k, v in grouped.items() if k not in _HYBRID_OP_KEYS}
    if meta:
        return bracket_part + "\n" + json.dumps(meta, separators=(",", ":"))
    return bracket_part


class IntentCompressor:
    """Compress a verbose human prompt into a deterministic polysynthetic packet."""

    def compress_tags(self, prompt: str, explicit_tags: list[str] | None = None) -> list[str]:
        tags: list[str] = list(explicit_tags or [])
        for t in self.derive_tags(prompt):
            key = t.split(":", 1)[0]
            if not any(existing.startswith(key + ":") for existing in tags):
                tags.append(t)
        return tags

    def compress(self, prompt: str, explicit_tags: list[str] | None = None,
                 style: str = "bracket") -> str:
        return render_packet(self.compress_tags(prompt, explicit_tags), style)

    @staticmethod
    def derive_tags(prompt: str) -> list[str]:
        low = prompt.lower()
        return [tag for pattern, tag in _KEYWORD_TAGS if re.search(pattern, low)]


# --------------------------------------------------------------------------- #
# Context selector
# --------------------------------------------------------------------------- #

@dataclass
class ContextBundle:
    text: str
    exposed_files: list[str]
    exposed_lines: int
    exposed_chars: int


class ContextSelector:
    """Builds the RAW (full-file) and AURA (surgical) context payloads."""

    def __init__(self, root: str = REPO_ROOT):
        self.root = root

    def read(self, rel: str) -> str:
        with open(os.path.join(self.root, rel), "r", encoding="utf-8") as f:
            return f.read()

    def raw_context(self, target_file: str, extra_files: list[str] | None = None) -> ContextBundle:
        files = [target_file] + list(extra_files or [])
        chunks, total_lines, total_chars, exposed = [], 0, 0, []
        for rel in files:
            content = self.read(rel)
            chunks.append(f"# ===== FILE: {rel} =====\n{content}")
            total_lines += len(content.splitlines())
            total_chars += len(content)
            exposed.append(rel)
        return ContextBundle("\n\n".join(chunks), exposed, total_lines, total_chars)

    def surgical_context(self, target_file: str, target_func: str) -> ContextBundle:
        content = self.read(target_file)
        header = parse_master_key_header(content)
        slice_src, start, end = extract_function_source(content, target_func)
        if slice_src is None:
            slice_src = "# (target function not found; header index only)"
            start = end = 0

        header_lines = [f"# HEADER INDEX for {target_file}"]
        if header.get("DEPENDENCIES"):
            header_lines.append(f"# DEPENDENCIES: {header['DEPENDENCIES']}")
        if header.get("FUNCTIONS"):
            header_lines.append(f"# FUNCTIONS: {header['FUNCTIONS']}")
        header_block = "\n".join(header_lines)

        # Line-numbered slice: "NNN| code". Real 1-indexed file line numbers so
        # the model can emit accurate diff hunks or JSON edit-plan line ranges.
        numbered = "\n".join(f"{start + i:>4}| {ln}"
                             for i, ln in enumerate(slice_src.splitlines())) if start else slice_src
        slice_block = (
            f"# SURGICAL SLICE: {target_file}:{start}-{end} (def {target_func})\n"
            f"# (lines shown as `LINE| code`; use these numbers for edits)\n{numbered}"
        )
        text = header_block + "\n\n" + slice_block
        return ContextBundle(text, [target_file], len(slice_src.splitlines()), len(text))


def load_guardrails(extra_files: list[str] | None = None) -> str:
    parts = []
    for name in list(GUARDRAIL_ORDER) + list(extra_files or []):
        path = os.path.join(AURA_GUARDRAIL_DIR, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                parts.append(f.read().strip())
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# The substrate orchestrator (no LLM)
# --------------------------------------------------------------------------- #

@dataclass
class SubstratePackage:
    """Everything Aura's deterministic core produces — ready to hand to egress."""
    packet: str
    guardrails: str
    context: ContextBundle
    directive: str
    prompt: str                 # assembled minimal egress prompt
    compile_ms: float
    meta: dict = field(default_factory=dict)


class AuraSubstrate:
    """
    Aura as a pure substrate. Compiles a human request into a compact,
    guard-railed, surgically-scoped package — instantly and with no model.
    """

    DIRECTIVE = (
        "Execute the packet. Obey every guardrail. Emit only the artifact "
        "named by the [OUTPUT:...] tag — nothing else."
    )

    def __init__(self, root: str = REPO_ROOT):
        self.root = root
        self.compressor = IntentCompressor()
        self.selector = ContextSelector(root)

    def compile(
        self,
        human_prompt: str,
        target_file: str | None = None,
        target_func: str | None = None,
        explicit_tags: list[str] | None = None,
        style: str = "bracket",
    ) -> SubstratePackage:
        t0 = time.time()
        tags = self.compressor.compress_tags(human_prompt, explicit_tags)
        packet = render_packet(tags, style)
        guardrails = load_guardrails()
        if target_file and target_func:
            ctx = self.selector.surgical_context(target_file, target_func)
        elif target_file:
            ctx = self.selector.raw_context(target_file)
        else:
            ctx = ContextBundle("", [], 0, 0)
        prompt = (
            "[AURA GUARDRAILS]\n"
            f"{guardrails}\n\n"
            f"[AURA TASK PACKET :: {style}]\n"
            f"{packet}\n\n"
            "[SURGICAL CONTEXT]\n"
            f"{ctx.text}\n\n"
            "[DIRECTIVE]\n"
            f"{self.DIRECTIVE}\n"
        )
        compile_ms = (time.time() - t0) * 1000.0
        return SubstratePackage(
            packet=packet,
            guardrails=guardrails,
            context=ctx,
            directive=self.DIRECTIVE,
            prompt=prompt,
            compile_ms=round(compile_ms, 3),
            meta={
                "target_file": target_file,
                "target_func": target_func,
                "packet_style": style,
                "packet_tokens": estimate_tokens(packet),
                "prompt_tokens": estimate_tokens(prompt),
                "exposed_lines": ctx.exposed_lines,
                "llm_used": False,
            },
        )


# --------------------------------------------------------------------------- #
# CLI demo
# --------------------------------------------------------------------------- #

def _demo(speak: bool) -> int:
    substrate = AuraSubstrate()
    human = ("Can you fix or improve the mesh offload function without adding any "
             "new dependencies, and preserve the existing packet protocol?")
    pkg = substrate.compile(
        human,
        target_file="aura_mesh.py",
        target_func="offload_compute",
        explicit_tags=[
            "ENV:PYTHON", "OP:PATCH", "DOMAIN:MESH", "TARGET:OFFLOAD_COMPUTE",
            "CONSTRAINT:NO_NEW_DEPS", "CONSTRAINT:PRESERVE_PROTOCOL",
            "VERIFY:AST_PARSE", "OUTPUT:UNIFIED_DIFF",
        ],
    )
    print("=== AURA SUBSTRATE (no LLM) ===")
    print(f"  compiled in           : {pkg.compile_ms} ms")
    print(f"  llm_used              : {pkg.meta['llm_used']}")
    print(f"  polysynthetic packet  : {pkg.packet}")
    print(f"  packet tokens         : {pkg.meta['packet_tokens']}")
    print(f"  exposed source lines  : {pkg.meta['exposed_lines']}")
    print(f"  egress prompt tokens  : {pkg.meta['prompt_tokens']}")
    print(f"  guardrail bytes       : {len(pkg.guardrails)}")

    if speak:
        try:
            from aura_llm_egress import ExternalLLM
        except Exception as exc:  # noqa: BLE001
            print(f"\n[!] egress unavailable: {exc}")
            return 0
        egress = ExternalLLM()
        data = {
            "packet": pkg.packet,
            "target": f"{pkg.meta['target_file']}:{pkg.meta['target_func']}",
            "exposed_lines": pkg.meta["exposed_lines"],
            "compile_ms": pkg.compile_ms,
        }
        print(f"\n=== EXTERNAL LLM EGRESS ({egress.provider}/{egress.model}) ===")
        text, err, latency = egress.interpret(
            data, instruction="In one or two sentences, explain to a human what Aura's "
                              "substrate just prepared and why it is efficient.")
        if err:
            print(f"[!] egress error: {err}")
        else:
            print(f"[{latency:.2f}s] {text}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aura substrate (LLM-free core) demo")
    p.add_argument("--demo", action="store_true", help="run a deterministic compile demo")
    p.add_argument("--speak", action="store_true",
                   help="also call the external LLM egress to verbalize the result")
    args = p.parse_args(argv)
    if args.demo:
        return _demo(args.speak)
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
