"""Strict D0 trust_remote_code evidence scanner for AWJ032 GLM53 G1.

This is subordinate to PR #311's full AirLLM source-admission gate. It exists so
GLM-specific compatibility evidence never treats a dynamic, omitted, or truthy
`trust_remote_code` value as hard-false merely because literal `True` is absent.
"""
from __future__ import annotations

from dataclasses import dataclass
import ast
from typing import Iterable


@dataclass(frozen=True)
class RemoteCodeFinding:
    code: str
    source: str
    line: int | None
    evidence: str


def _is_from_pretrained(call: ast.Call) -> bool:
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr == "from_pretrained"


def scan_source(name: str, text: str) -> tuple[RemoteCodeFinding, ...]:
    try:
        tree = ast.parse(text, filename=name)
    except SyntaxError as exc:
        return (
            RemoteCodeFinding(
                "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
                name,
                exc.lineno,
                "source parse failed; hard-false policy cannot be proven",
            ),
        )

    findings: list[RemoteCodeFinding] = []
    relevant = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_from_pretrained(node):
            continue
        relevant += 1
        explicit = [kw for kw in node.keywords if kw.arg == "trust_remote_code"]
        splats = [kw for kw in node.keywords if kw.arg is None]
        if splats:
            findings.append(
                RemoteCodeFinding(
                    "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
                    name,
                    getattr(node, "lineno", None),
                    "from_pretrained uses **kwargs; trust_remote_code policy is not statically closed",
                )
            )
            continue
        if len(explicit) != 1:
            findings.append(
                RemoteCodeFinding(
                    "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
                    name,
                    getattr(node, "lineno", None),
                    "from_pretrained must specify trust_remote_code=False exactly once",
                )
            )
            continue
        value = explicit[0].value
        if not (isinstance(value, ast.Constant) and value.value is False):
            findings.append(
                RemoteCodeFinding(
                    "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
                    name,
                    getattr(node, "lineno", None),
                    "trust_remote_code is not explicit literal False",
                )
            )

    if relevant == 0:
        findings.append(
            RemoteCodeFinding(
                "AIRLLM_REMOTE_CODE_POLICY_UNPROVEN",
                name,
                None,
                "no from_pretrained call found; this source cannot prove a hard-false call site",
            )
        )
    return tuple(findings)


def scan_sources(sources: Iterable[tuple[str, str]]) -> tuple[RemoteCodeFinding, ...]:
    out: list[RemoteCodeFinding] = []
    for name, text in sources:
        out.extend(scan_source(name, text))
    return tuple(out)


def hard_false_proven(sources: Iterable[tuple[str, str]]) -> bool:
    findings = scan_sources(sources)
    return not any(
        finding.code in {"AIRLLM_REMOTE_CODE_SECURITY_BLOCK", "AIRLLM_REMOTE_CODE_POLICY_UNPROVEN"}
        for finding in findings
    )
