"""Full inspected-tree binding for AWJ-032 AirLLM HARD_FALSE remediation.

This module is a Different-J membrane over ``airllm_hard_false_remediation``.
The lower-level constructor safely rewrites four exact pinned policy blobs. This
module closes the surrounding provenance seam: a receipt may name the pinned
AirLLM commit/package generation only after *every byte consumed by the existing
PR #311 source-admission gate* is verified against the pinned manifest.

No AirLLM/model code is imported or executed. The remediated mapping is audited
in a temporary source tree with the existing ``airllm_source_admission`` gate.
A PASS here remains static source evidence only; it is not host import,
compatibility, checkpoint, inference, or G2 proof.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from airllm_hard_false_remediation import (
    PINNED_MUTATION_SPECS,
    PINNED_PACKAGE_TREE,
    PINNED_UPSTREAM_COMMIT,
    RemediationError,
    git_blob_sha1,
    remediate_bytes,
)
from airllm_source_admission import audit_airllm_source

SCHEMA = "AuraAirLLMHardFalseInspectedTreeV1"
EXPECTED_VERSION = "3.3.0"

# Exact source set consumed by PR #311's audit:
# air_llm/setup.py + air_llm/airllm/**/*.py at c92cea6914...
PINNED_INSPECTED_BLOBS: dict[str, str] = {
    "air_llm/setup.py": "b349ed7929a3b2801d23c62d3fc9ffa92f3af2c0",
    "air_llm/airllm/__init__.py": "5ce56df372b10f5cff570dcc1311e48666349d6c",
    "air_llm/airllm/airllm.py": "0f44e54d6a4d9c65d1e7938ca8de2ca194a7d9ad",
    "air_llm/airllm/airllm_baichuan.py": "a151b18b5eca51e72733c895702fd2b75dadecf0",
    "air_llm/airllm/airllm_base.py": "8da7ab91c6f0436054f13d885975fa6eb02ad605",
    "air_llm/airllm/airllm_chatglm.py": "b8d38545663fb63d4569150c3cf5bd393a356146",
    "air_llm/airllm/airllm_internlm.py": "22d1a4363797781bf4aad9b142ee2e5e3765c213",
    "air_llm/airllm/airllm_kimi_k3.py": "040649688001afc12a02f92206436706ecdc10c8",
    "air_llm/airllm/airllm_llama_mlx.py": "e47a0bd493c693a115f8012fc9ba90209125872f",
    "air_llm/airllm/airllm_mistral.py": "6981b1e5121bebffab58539923169d3272000a57",
    "air_llm/airllm/airllm_mixtral.py": "3dbd1830421b489736292f5aa4933c817b9efc31",
    "air_llm/airllm/airllm_qwen.py": "aac43d8ddf2f7bf74d53abd9226a5cf19e0f7310",
    "air_llm/airllm/airllm_qwen2.py": "028ef0a2d14d2445e248bfa897d4b8e524adc355",
    "air_llm/airllm/airllm_qwen3_5.py": "b9c04f5e15a38aaa34e8a00c01989dbc6e070140",
    "air_llm/airllm/airllm_qwen4_exp.py": "df81c225c174e40b723b04b8049acebcdb7d03e7",
    "air_llm/airllm/auto_model.py": "f6608dfdf3edfca5dc827f2a312524e776204d24",
    "air_llm/airllm/persist/__init__.py": "794772c53e238416c9ea5b202bf3a939fcf778e4",
    "air_llm/airllm/persist/mlx_model_persister.py": "c1a482faf6b600ec03e00a60f17b2f3f75745bdf",
    "air_llm/airllm/persist/model_persister.py": "963a6f645ccbddc2812aaac17be593f5b0d49266",
    "air_llm/airllm/persist/safetensor_model_persister.py": "8c6caca41e4fb4dc65b53dc9225fc558c1c684ad",
    "air_llm/airllm/profiler.py": "d457605d74591909c37db83771307b9e4e0aefde",
    "air_llm/airllm/tokenization_baichuan.py": "1d347e60698a2da95d34bfeabda0642b36858eec",
    "air_llm/airllm/utils.py": "75740db4d2f3a7ed524d3ece14727ca947b613dc",
}


@dataclass(frozen=True)
class InspectedTreeRemediationReceipt:
    schema: str
    status: str
    upstream_commit: str
    package_tree: str
    expected_version: str
    source_identity_scope: str
    inspected_file_count: int
    input_manifest_digest: str
    output_manifest_digest: str
    input_gate_status: str
    output_gate_status: str
    input_gate_finding_codes: tuple[str, ...]
    output_gate_finding_codes: tuple[str, ...]
    changed_files: tuple[str, ...]
    edit_count_by_file: tuple[tuple[str, int], ...]
    full_gate_consumed_manifest_exact: bool
    hard_remote_code_opt_out: bool
    host_import_proven: bool = False
    model_compatibility_proven: bool = False
    model_downloaded: bool = False
    model_executed: bool = False
    g2_admitted: bool = False
    provider_calls: int = 0
    claim_ceiling: str = "FULL_GATE_CONSUMED_SOURCE_CANDIDATE_NOT_RUNTIME_PROOF"

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["edit_count_by_file"] = dict(self.edit_count_by_file)
        return out


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _manifest(files: Mapping[str, bytes]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path, raw in files.items():
        if not isinstance(path, str) or not path:
            raise RemediationError("SOURCE_PATH_REQUIRED")
        if not isinstance(raw, bytes):
            raise RemediationError("SOURCE_BYTES_REQUIRED", path)
        out[path] = git_blob_sha1(raw)
    return dict(sorted(out.items()))


def _verify_exact_manifest(
    files: Mapping[str, bytes], expected_manifest: Mapping[str, str]
) -> dict[str, str]:
    observed = _manifest(files)
    expected = dict(sorted(expected_manifest.items()))
    if set(observed) != set(expected):
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        raise RemediationError(
            "PINNED_INSPECTED_SOURCE_SET_MISMATCH",
            f"missing={missing};extra={extra}",
        )
    mismatched = sorted(
        path for path, expected_sha in expected.items()
        if observed[path] != expected_sha
    )
    if mismatched:
        raise RemediationError(
            "PINNED_INSPECTED_SOURCE_BLOB_MISMATCH",
            ",".join(mismatched),
        )
    return observed


def _audit_mapping(files: Mapping[str, bytes]):
    """Run the existing path-aware PR #311 gate over an ephemeral mapping."""
    with tempfile.TemporaryDirectory(prefix="aura-airllm-hard-false-") as tmp:
        root = Path(tmp)
        for rel, raw in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        return audit_airllm_source(root, EXPECTED_VERSION)


def _remediate_inspected_tree(
    files: Mapping[str, bytes],
    *,
    expected_manifest: Mapping[str, str],
    mutation_specs: Mapping[str, tuple[str, int]],
    upstream_commit: str,
    package_tree: str,
) -> tuple[dict[str, bytes], InspectedTreeRemediationReceipt]:
    if not isinstance(files, Mapping):
        raise RemediationError("SOURCE_FILE_MAPPING_REQUIRED")

    input_manifest = _verify_exact_manifest(files, expected_manifest)
    input_gate = _audit_mapping(files)

    # The exact pinned input is expected to be blocked only by the remote-code
    # policy. Any unrelated source blocker means this constructor is the wrong
    # repair surface and must fail closed.
    remote_codes = {
        "REMOTE_CODE_TRUE",
        "REMOTE_CODE_DYNAMIC",
        "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
    }
    nonremote = sorted(
        {finding.code for finding in input_gate.findings} - remote_codes
    )
    if nonremote:
        raise RemediationError(
            "PINNED_INSPECTED_TREE_NONREMOTE_BLOCKER",
            ",".join(nonremote),
        )

    outputs = dict(files)
    edit_counts: dict[str, int] = {}
    for path, (expected_blob, expected_count) in sorted(mutation_specs.items()):
        if path not in outputs:
            raise RemediationError("PINNED_MUTATION_FILE_MISSING", path)
        remediated, file_receipt = remediate_bytes(
            path=path,
            raw=outputs[path],
            expected_git_blob_sha1=expected_blob,
            expected_edit_count=expected_count,
        )
        outputs[path] = remediated
        edit_counts[path] = file_receipt.edit_count

    output_manifest = _manifest(outputs)
    changed = tuple(
        sorted(
            path
            for path in input_manifest
            if input_manifest[path] != output_manifest[path]
        )
    )
    if set(changed) != set(mutation_specs):
        raise RemediationError(
            "REMEDIATED_INSPECTED_CHANGE_SET_MISMATCH",
            ",".join(changed),
        )

    # Existing PR #311 audit remains the authority; this wrapper cannot self-
    # declare a safe source generation if that gate finds anything remaining.
    output_gate = _audit_mapping(outputs)
    if output_gate.status != "PASS":
        codes = sorted({finding.code for finding in output_gate.findings})
        raise RemediationError(
            "REMEDIATED_INSPECTED_TREE_POST_AUDIT_BLOCKED",
            ",".join(codes),
        )

    receipt = InspectedTreeRemediationReceipt(
        schema=SCHEMA,
        status="PASS_SOURCE_CANDIDATE",
        upstream_commit=upstream_commit,
        package_tree=package_tree,
        expected_version=EXPECTED_VERSION,
        source_identity_scope="FULL_PR311_GATE_CONSUMED_TREE",
        inspected_file_count=len(input_manifest),
        input_manifest_digest=_canonical_digest(input_manifest),
        output_manifest_digest=_canonical_digest(output_manifest),
        input_gate_status=input_gate.status,
        output_gate_status=output_gate.status,
        input_gate_finding_codes=tuple(
            sorted({finding.code for finding in input_gate.findings})
        ),
        output_gate_finding_codes=tuple(
            sorted({finding.code for finding in output_gate.findings})
        ),
        changed_files=changed,
        edit_count_by_file=tuple(sorted(edit_counts.items())),
        full_gate_consumed_manifest_exact=True,
        hard_remote_code_opt_out=True,
    )
    return outputs, receipt


def remediate_pinned_inspected_tree(
    files: Mapping[str, bytes],
) -> tuple[dict[str, bytes], InspectedTreeRemediationReceipt]:
    """Remediate only the exact PR #311-inspected AirLLM v3.3.0 source generation."""
    return _remediate_inspected_tree(
        files,
        expected_manifest=PINNED_INSPECTED_BLOBS,
        mutation_specs=PINNED_MUTATION_SPECS,
        upstream_commit=PINNED_UPSTREAM_COMMIT,
        package_tree=PINNED_PACKAGE_TREE,
    )
