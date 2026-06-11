"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa895-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: typing, ast, symbolic_shield, dataclasses, os, re, __future__, json
FUNCTIONS: get_ontology_circuit, summary, __init__, reload, _check_imports, _check_calls, _check_alloc, evaluate_source
SYNOPSIS: The `AuraOSScanner` Python module is a strict static-analysis and runtime-audit utility that leverages `typing`, `ast`, `symbolic_shield`, `dataclasses`, `os`, `re`, `__future__`, and `json` to enforce secure ontology-circuit integrity via `get_ontology_circuit`, `summary`, `__init__`, `reload`, `_check_imports`, `_check_calls`, `_check_alloc`, and `evaluate_source`.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from symbolic_shield import (
    check_syntax,
    check_loop_decay,
    check_import_safety,
    check_memory_safety,
    check_banned_calls,
)

_SHIELD_GATES = (
    check_syntax,
    check_loop_decay,
    check_import_safety,
    check_memory_safety,
    check_banned_calls,
)


_DEFAULT_PATH = "Aura_Memory/aura_ontology.json"


@dataclass
class CircuitVerdict:
    consistent: bool
    violations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.consistent:
            return "ONTOLOGY_CIRCUIT_OK"
        return "; ".join(self.violations)


class AuraOntologyCircuit:
    """Forward-evaluates compiled ontology rules over Python source mutations."""

    def __init__(self, ontology_path: str = _DEFAULT_PATH):
        self.ontology_path = ontology_path
        self._spec: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        if not os.path.exists(self.ontology_path):
            self._spec = {
                "forbidden_import_roots": [],
                "forbidden_calls": [],
                "require_shield": True,
                "require_non_increasing_call_friction": False,
                "max_single_alloc_mb": 512,
            }
            return
        with open(self.ontology_path, "r", encoding="utf-8") as f:
            self._spec = json.load(f)

    def _check_imports(self, source: str) -> list[str]:
        roots = set(self._spec.get("forbidden_import_roots", []))
        if not roots:
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        hits: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base = alias.name.split(".")[0]
                    if base in roots:
                        hits.append(f"ONTOLOGY_IMPORT:{alias.name}@L{node.lineno}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                base = node.module.split(".")[0]
                if base in roots:
                    hits.append(f"ONTOLOGY_IMPORT:{node.module}@L{node.lineno}")
        return hits

    def _check_calls(self, source: str) -> list[str]:
        banned = set(self._spec.get("forbidden_calls", []))
        if not banned:
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        hits: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name and name in banned:
                hits.append(f"ONTOLOGY_CALL:{name}()@L{node.lineno}")
        return hits

    def _check_alloc(self, source: str) -> list[str]:
        cap_mb = int(self._spec.get("max_single_alloc_mb", 512))
        cap_bytes = cap_mb * 1024 * 1024
        pattern = re.compile(
            r"np\.\w+\(\s*\(?\s*(\d[\d_]*)\s*,\s*(\d[\d_]*)", re.MULTILINE
        )
        hits: list[str] = []
        for match in pattern.finditer(source):
            dim0 = int(match.group(1).replace("_", ""))
            dim1 = int(match.group(2).replace("_", ""))
            estimated = dim0 * dim1 * 4
            if estimated > cap_bytes:
                hits.append(
                    f"ONTOLOGY_ALLOC:~{estimated // (1024 * 1024)}MB>{cap_mb}MB"
                )
        return hits

    def evaluate_source(
        self,
        source: str,
        *,
        baseline_friction: int | None = None,
        proposed_friction: int | None = None,
    ) -> CircuitVerdict:
        violations: list[str] = []

        if self._spec.get("require_shield", True):
            for gate in _SHIELD_GATES:
                report = gate(source)
                if not report.passed:
                    violations.append(f"SHIELD:{report.reason}")
                    break

        violations.extend(self._check_imports(source))
        violations.extend(self._check_calls(source))
        violations.extend(self._check_alloc(source))

        if self._spec.get("require_non_increasing_call_friction") and (
            baseline_friction is not None and proposed_friction is not None
        ):
            if proposed_friction > baseline_friction:
                violations.append(
                    f"FRICTION_INCREASE:{baseline_friction}->{proposed_friction}"
                )

        return CircuitVerdict(consistent=not violations, violations=violations)


# Module-level singleton for hot paths (evolve / catalyze / heal)
_default_circuit: AuraOntologyCircuit | None = None


def get_ontology_circuit() -> AuraOntologyCircuit:
    global _default_circuit
    if _default_circuit is None:
        _default_circuit = AuraOntologyCircuit()
    return _default_circuit
