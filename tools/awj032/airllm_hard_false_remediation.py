"""Exact-source AirLLM HARD_FALSE remediation candidate for AWJ-032 G1.

The stock AirLLM v3.3.0 source is a valid negative control but cannot pass Aura's
HARD_FALSE source gate because remote-code widening appears in several loader
paths. This module does not import, install, execute, or fetch AirLLM. Instead it
turns exact pinned source bytes into a deterministic candidate patch set.

Safety properties:
- every production mutation file is bound to its exact upstream Git blob SHA-1;
- only AST expression spans that control ``trust_remote_code`` are replaced;
- unrelated source bytes remain byte-for-byte unchanged;
- the expected mutation count for each pinned blob is fixed and fail-closed;
- the output is still only a candidate: the complete remediated tree must pass
  ``airllm_source_admission.audit_airllm_source`` before any import/runtime claim.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "AuraAirLLMHardFalseRemediationV1"
PINNED_UPSTREAM_COMMIT = "c92cea691412715a218306acb01fc9c2c681a8f2"
PINNED_PACKAGE_TREE = "bc02aa8f4600c8d34fea4d50c31a79b5bb3497e4"

# Exact Git blobs from the pinned AirLLM v3.3.0 package tree. Counts are the
# number of non-False trust_remote_code policy expressions expected in that blob.
PINNED_MUTATION_SPECS: dict[str, tuple[str, int]] = {
    "air_llm/airllm/auto_model.py": (
        "f6608dfdf3edfca5dc827f2a312524e776204d24",
        2,
    ),
    "air_llm/airllm/airllm_base.py": (
        "8da7ab91c6f0436054f13d885975fa6eb02ad605",
        6,
    ),
    "air_llm/airllm/airllm_baichuan.py": (
        "a151b18b5eca51e72733c895702fd2b75dadecf0",
        1,
    ),
    "air_llm/airllm/airllm_llama_mlx.py": (
        "e47a0bd493c693a115f8012fc9ba90209125872f",
        4,
    ),
}


class RemediationError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class FileRemediationReceipt:
    path: str
    source_git_blob_sha1: str
    remediated_git_blob_sha1: str
    remediated_sha256: str
    edit_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "source_git_blob_sha1": self.source_git_blob_sha1,
            "remediated_git_blob_sha1": self.remediated_git_blob_sha1,
            "remediated_sha256": self.remediated_sha256,
            "edit_count": self.edit_count,
        }


def git_blob_sha1(raw: bytes) -> str:
    if not isinstance(raw, bytes):
        raise RemediationError("SOURCE_BYTES_REQUIRED")
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()  # noqa: S324 - Git object identity, not security


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _is_false(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _const_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _target_is_trust_remote_code(node: ast.AST | None) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "trust_remote_code"
    if isinstance(node, ast.Name):
        return node.id == "trust_remote_code"
    if isinstance(node, ast.Subscript):
        return _const_string(node.slice) == "trust_remote_code"
    return False


def _add_edit(edits: set[tuple[int, int, int, int]], node: ast.AST | None) -> None:
    if node is None or _is_false(node):
        return
    if not all(
        hasattr(node, attr)
        for attr in ("lineno", "col_offset", "end_lineno", "end_col_offset")
    ):
        raise RemediationError("AST_SOURCE_SPAN_REQUIRED")
    edits.add(
        (
            int(node.lineno),
            int(node.col_offset),
            int(node.end_lineno),
            int(node.end_col_offset),
        )
    )


def _collect_policy_edits(tree: ast.AST) -> set[tuple[int, int, int, int]]:
    edits: set[tuple[int, int, int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "trust_remote_code":
                    _add_edit(edits, kw.value)

            if isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault":
                if node.args and _const_string(node.args[0]) == "trust_remote_code":
                    if len(node.args) < 2:
                        raise RemediationError("TRUST_REMOTE_CODE_SETDEFAULT_WITHOUT_VALUE")
                    _add_edit(edits, node.args[1])

            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "setattr"
                and len(node.args) >= 3
                and _const_string(node.args[1]) == "trust_remote_code"
            ):
                _add_edit(edits, node.args[2])

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if key is not None and _const_string(key) == "trust_remote_code":
                    _add_edit(edits, value)

        if isinstance(node, ast.Assign):
            if any(_target_is_trust_remote_code(target) for target in node.targets):
                _add_edit(edits, node.value)
        elif isinstance(node, ast.AnnAssign):
            if _target_is_trust_remote_code(node.target):
                _add_edit(edits, node.value)

    return edits


def _line_starts(raw: bytes) -> list[int]:
    starts = [0]
    for idx, value in enumerate(raw):
        if value == 0x0A:
            starts.append(idx + 1)
    return starts


def _absolute_offset(starts: list[int], line: int, col: int) -> int:
    if line <= 0 or line > len(starts):
        raise RemediationError("AST_SOURCE_SPAN_INVALID", f"line={line}")
    return starts[line - 1] + col


def _apply_false_edits(raw: bytes, edits: set[tuple[int, int, int, int]]) -> bytes:
    starts = _line_starts(raw)
    spans: list[tuple[int, int]] = []
    for start_line, start_col, end_line, end_col in edits:
        start = _absolute_offset(starts, start_line, start_col)
        end = _absolute_offset(starts, end_line, end_col)
        if end <= start:
            raise RemediationError("AST_SOURCE_SPAN_INVALID", f"{start}:{end}")
        spans.append((start, end))

    ordered = sorted(spans)
    for (_, left_end), (right_start, _) in zip(ordered, ordered[1:]):
        if left_end > right_start:
            raise RemediationError("OVERLAPPING_REMEDIATION_EDITS")

    out = raw
    for start, end in reversed(ordered):
        out = out[:start] + b"False" + out[end:]
    return out


def remediate_bytes(
    *,
    path: str,
    raw: bytes,
    expected_git_blob_sha1: str,
    expected_edit_count: int,
) -> tuple[bytes, FileRemediationReceipt]:
    if not isinstance(path, str) or not path:
        raise RemediationError("SOURCE_PATH_REQUIRED")
    if not isinstance(raw, bytes):
        raise RemediationError("SOURCE_BYTES_REQUIRED", path)
    observed_blob = git_blob_sha1(raw)
    if observed_blob != expected_git_blob_sha1:
        raise RemediationError(
            "PINNED_SOURCE_BLOB_MISMATCH",
            f"{path}:expected={expected_git_blob_sha1},observed={observed_blob}",
        )
    try:
        text = raw.decode("utf-8")
        tree = ast.parse(text, filename=path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise RemediationError("PINNED_SOURCE_PARSE_FAILED", path) from exc

    edits = _collect_policy_edits(tree)
    if len(edits) != expected_edit_count:
        raise RemediationError(
            "PINNED_REMEDIATION_EDIT_COUNT_MISMATCH",
            f"{path}:expected={expected_edit_count},observed={len(edits)}",
        )
    remediated = _apply_false_edits(raw, edits)
    try:
        ast.parse(remediated.decode("utf-8"), filename=path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise RemediationError("REMEDIATED_SOURCE_PARSE_FAILED", path) from exc

    receipt = FileRemediationReceipt(
        path=path,
        source_git_blob_sha1=observed_blob,
        remediated_git_blob_sha1=git_blob_sha1(remediated),
        remediated_sha256=_sha256(remediated),
        edit_count=len(edits),
    )
    return remediated, receipt


def remediate_pinned_policy_files(
    files: Mapping[str, bytes],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if not isinstance(files, Mapping):
        raise RemediationError("SOURCE_FILE_MAPPING_REQUIRED")
    missing = sorted(set(PINNED_MUTATION_SPECS) - set(files))
    if missing:
        raise RemediationError("PINNED_MUTATION_FILE_MISSING", ",".join(missing))

    outputs: dict[str, bytes] = {}
    receipts: list[FileRemediationReceipt] = []
    for path in sorted(PINNED_MUTATION_SPECS):
        expected_blob, expected_count = PINNED_MUTATION_SPECS[path]
        remediated, receipt = remediate_bytes(
            path=path,
            raw=files[path],
            expected_git_blob_sha1=expected_blob,
            expected_edit_count=expected_count,
        )
        outputs[path] = remediated
        receipts.append(receipt)

    logical = {
        "schema": SCHEMA,
        "upstream_commit": PINNED_UPSTREAM_COMMIT,
        "package_tree": PINNED_PACKAGE_TREE,
        "remote_code_policy": "HARD_FALSE",
        "files": [receipt.to_dict() for receipt in receipts],
        "total_edits": sum(receipt.edit_count for receipt in receipts),
        "complete_tree_static_gate_required": True,
        "host_import_proven": False,
        "model_compatibility_proven": False,
        "g2_admitted": False,
        "provider_calls": 0,
        "claim_ceiling": "STATIC_REMEDIATED_SOURCE_CANDIDATE_NOT_RUNTIME_PROOF",
    }
    logical_id = hashlib.sha256(_canonical(logical)).hexdigest()
    return outputs, {**logical, "logical_id": logical_id}
