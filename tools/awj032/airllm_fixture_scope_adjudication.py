"""Exact-scope adjudication for the AWJ032 pinned AirLLM tiny fixture.

The general source gate is intentionally conservative. This helper proves one
narrow residual on the exact remediated AirLLM v3.3.0 tree without weakening the
general gate: ``AirLLMBaseModel._instantiate_on_meta`` may expand ``**kwargs``
into ``from_config`` only when that lexical mapping has one mutation-free
assignment containing literal ``trust_remote_code=False`` and the fallback call
also passes literal False.

This is fixture-only evidence. It is not a general Python name resolver and does
not convert a source-gate finding into runtime or effect authority.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "AWJ032FixtureScopeAdjudicationV1"
TARGET_PATH = "air_llm/airllm/airllm_base.py"
TARGET_CLASS = "AirLLMBaseModel"
TARGET_METHOD = "_instantiate_on_meta"
TARGET_MAPPING = "kwargs"


class ScopeAdjudicationError(ValueError):
    pass


@dataclass(frozen=True)
class ScopeAdjudicationReceipt:
    schema: str
    status: str
    path: str
    remediated_git_blob_sha1: str
    method: str
    mapping_name: str
    mapping_assignment_line: int
    primary_from_config_lines: tuple[int, ...]
    explicit_fallback_lines: tuple[int, ...]
    trust_remote_code_state: str
    claim_ceiling: str = (
        "PINNED_TINY_FIXTURE_SCOPE_PROOF_NOT_GENERAL_SOURCE_GATE_PASS"
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()  # noqa: S324 - Git identity


def _find_method(tree: ast.Module) -> ast.FunctionDef | ast.AsyncFunctionDef:
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == TARGET_CLASS
    ]
    if len(classes) != 1:
        raise ScopeAdjudicationError("TARGET_CLASS_UNIQUE_REQUIRED")
    methods = [
        node
        for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == TARGET_METHOD
    ]
    if len(methods) != 1:
        raise ScopeAdjudicationError("TARGET_METHOD_UNIQUE_REQUIRED")
    return methods[0]


def _current_scope_nodes(scope: ast.AST):
    """Walk one lexical scope without mixing sibling/nested local bindings."""
    for child in ast.iter_child_nodes(scope):
        yield child
        if isinstance(
            child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
        ):
            continue
        yield from _current_scope_nodes(child)


def _mapping_assignment(method: ast.AST) -> tuple[ast.Assign, ast.Dict]:
    modeled_target_ids: set[int] = set()
    candidates: list[ast.Assign] = []
    for node in _current_scope_nodes(method):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == TARGET_MAPPING
        ):
            candidates.append(node)
            modeled_target_ids.add(id(node.targets[0]))
    if len(candidates) != 1:
        raise ScopeAdjudicationError(
            f"MAPPING_SINGLE_ASSIGNMENT_REQUIRED:{len(candidates)}"
        )
    assignment = candidates[0]
    if not isinstance(assignment.value, ast.Dict):
        raise ScopeAdjudicationError("MAPPING_LITERAL_DICT_REQUIRED")

    for node in _current_scope_nodes(method):
        if (
            isinstance(node, ast.Name)
            and node.id == TARGET_MAPPING
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and id(node) not in modeled_target_ids
        ):
            raise ScopeAdjudicationError(
                f"MAPPING_REBIND_OR_DELETE:{getattr(node, 'lineno', 0)}"
            )
        if isinstance(node, (ast.AugAssign, ast.NamedExpr)):
            target = node.target
            if isinstance(target, ast.Name) and target.id == TARGET_MAPPING:
                raise ScopeAdjudicationError(
                    f"MAPPING_MUTATION:{getattr(node, 'lineno', 0)}"
                )
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == TARGET_MAPPING
                ):
                    raise ScopeAdjudicationError(
                        f"MAPPING_SUBSCRIPT_MUTATION:{getattr(node, 'lineno', 0)}"
                    )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == TARGET_MAPPING
            and node.func.attr
            in {"update", "setdefault", "pop", "popitem", "clear", "__setitem__"}
        ):
            raise ScopeAdjudicationError(
                f"MAPPING_METHOD_MUTATION:{node.func.attr}:{getattr(node, 'lineno', 0)}"
            )
    return assignment, assignment.value


def _dict_trust_state(mapping: ast.Dict) -> str:
    states: list[str] = []
    for key, value in zip(mapping.keys, mapping.values):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise ScopeAdjudicationError("MAPPING_DYNAMIC_KEY")
        if key.value != "trust_remote_code":
            continue
        if isinstance(value, ast.Constant) and value.value is False:
            states.append("FALSE")
        elif isinstance(value, ast.Constant) and value.value is True:
            states.append("TRUE")
        else:
            states.append("DYNAMIC")
    if states != ["FALSE"]:
        raise ScopeAdjudicationError(f"MAPPING_HARD_FALSE_REQUIRED:{states}")
    return "FALSE"


def adjudicate(
    root: str | Path, remediation_receipt: str | Path
) -> ScopeAdjudicationReceipt:
    root = Path(root)
    remediation = json.loads(Path(remediation_receipt).read_text(encoding="utf-8"))
    if remediation.get("schema") != "AuraAirLLMHardFalseRemediationV1":
        raise ScopeAdjudicationError("REMEDIATION_SCHEMA_MISMATCH")
    if remediation.get("remote_code_policy") != "HARD_FALSE":
        raise ScopeAdjudicationError("REMEDIATION_POLICY_MISMATCH")
    file_receipts = [
        item for item in remediation.get("files", []) if item.get("path") == TARGET_PATH
    ]
    if len(file_receipts) != 1:
        raise ScopeAdjudicationError("REMEDIATED_FILE_RECEIPT_UNIQUE_REQUIRED")

    raw = (root / TARGET_PATH).read_bytes()
    observed_blob = git_blob_sha1(raw)
    if observed_blob != file_receipts[0].get("remediated_git_blob_sha1"):
        raise ScopeAdjudicationError(f"REMEDIATED_BLOB_MISMATCH:{observed_blob}")

    tree = ast.parse(raw.decode("utf-8"), filename=TARGET_PATH)
    method = _find_method(tree)
    assignment, mapping = _mapping_assignment(method)
    state = _dict_trust_state(mapping)

    primary: list[int] = []
    fallback: list[int] = []
    for node in _current_scope_nodes(method):
        if (
            not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Attribute)
            or node.func.attr != "from_config"
        ):
            continue
        expansions = [kw.value for kw in node.keywords if kw.arg is None]
        explicit = [kw.value for kw in node.keywords if kw.arg == "trust_remote_code"]
        if expansions:
            if (
                len(expansions) != 1
                or not isinstance(expansions[0], ast.Name)
                or expansions[0].id != TARGET_MAPPING
            ):
                raise ScopeAdjudicationError(
                    f"UNBOUND_FROM_CONFIG_EXPANSION:{getattr(node, 'lineno', 0)}"
                )
            primary.append(int(node.lineno))
        else:
            if (
                len(explicit) != 1
                or not isinstance(explicit[0], ast.Constant)
                or explicit[0].value is not False
            ):
                raise ScopeAdjudicationError(
                    f"FALLBACK_HARD_FALSE_REQUIRED:{getattr(node, 'lineno', 0)}"
                )
            fallback.append(int(node.lineno))
    if not primary or not fallback:
        raise ScopeAdjudicationError(
            f"EXPECTED_PRIMARY_AND_FALLBACK:{primary}:{fallback}"
        )

    return ScopeAdjudicationReceipt(
        schema=SCHEMA,
        status="PASS",
        path=TARGET_PATH,
        remediated_git_blob_sha1=observed_blob,
        method=f"{TARGET_CLASS}.{TARGET_METHOD}",
        mapping_name=TARGET_MAPPING,
        mapping_assignment_line=int(assignment.lineno),
        primary_from_config_lines=tuple(primary),
        explicit_fallback_lines=tuple(fallback),
        trust_remote_code_state=state,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--remediation-receipt", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        receipt = adjudicate(args.root, args.remediation_receipt)
        output = receipt.to_dict()
        rc = 0
    except Exception as exc:  # fail closed with a typed receipt
        output = {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        rc = 2
    text = json.dumps(output, sort_keys=True, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
