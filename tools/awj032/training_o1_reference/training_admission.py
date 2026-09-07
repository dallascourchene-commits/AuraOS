from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import ast
import json

SCHEMA = "AURA-AWJ032-AIRLLM-TRAINING-ADMISSION-v1"
AIRLLM_COMMIT = "55e435087d951da8c25ab3672e969025241a398e"
REQ_FILES = {
    "air_llm/airllm/airllm_lora.py": "442c70a85a53603089ce14604bdc48550e343e3b3405dccc080a4d841bc50172",
    "air_llm/airllm/lora_linear.py": "acda13718742c7f79c2713b04d06787c81999a85d6792aa1fa836ab77e1745f5",
    "README.md": "746f35e0bee6598643666792c050c8833b5d441d36e0a60dd0846ae0d34ece73",
}


def h(data: bytes) -> str:
    return sha256(data).hexdigest()


def jhash(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def root(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name}: sha256 required")
    return value


@dataclass(frozen=True)
class SourceReceipt:
    commit: str
    file_roots: dict[str, str]
    family_routes: dict[str, str]
    partial_load_guard_required: bool
    provenance_envelope_required: bool

    @property
    def receipt_root(self) -> str:
        return jhash({"schema": SCHEMA, "kind": "source", **asdict(self)})


@dataclass(frozen=True)
class AdapterManifest:
    base_checkpoint_root: str
    base_config_root: str
    tokenizer_root: str
    runtime_root: str
    airllm_commit: str
    family: str
    trainer_class: str
    target_paths: tuple[str, ...]
    lora_r: int
    lora_alpha: int
    packed_experts: bool
    adapter_keys: tuple[str, ...]
    adapter_value_roots: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("base_checkpoint_root", "base_config_root", "tokenizer_root", "runtime_root"):
            root(getattr(self, name), name)
        if self.airllm_commit != AIRLLM_COMMIT:
            raise ValueError("airllm commit drift")
        if self.lora_r < 1 or self.lora_alpha <= 0:
            raise ValueError("invalid LoRA hyperparameters")
        if len(self.adapter_keys) != len(self.adapter_value_roots):
            raise ValueError("key/value root cardinality mismatch")
        if len(set(self.adapter_keys)) != len(self.adapter_keys):
            raise ValueError("duplicate adapter key")
        if len(set(self.target_paths)) != len(self.target_paths):
            raise ValueError("duplicate target path")
        for value in self.adapter_value_roots:
            root(value, "adapter_value_root")

    @property
    def identity_root(self) -> str:
        return jhash({"schema": SCHEMA, "kind": "adapter_manifest", **asdict(self)})


@dataclass(frozen=True)
class Admission:
    action: str
    reason: str
    source_root: str
    adapter_root: str | None = None
    authority: str = "D0_NONPROMOTING"
    gate10: bool = False


def _class_bases(tree: ast.Module) -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out[node.name] = tuple(ast.unparse(base) for base in node.bases)
    return out


def _function_text(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node) or ast.unparse(node)
    return ""


def audit_source(repo: Path, commit: str) -> SourceReceipt:
    if commit != AIRLLM_COMMIT:
        raise ValueError("unbound AirLLM commit")
    roots: dict[str, str] = {}
    for rel, expected in REQ_FILES.items():
        data = (repo / rel).read_bytes()
        got = h(data)
        roots[rel] = got
        if got != expected:
            raise ValueError(f"source drift {rel}: {got}")

    lora_source = (repo / "air_llm/airllm/airllm_lora.py").read_text()
    linear_source = (repo / "air_llm/airllm/lora_linear.py").read_text()
    bases = _class_bases(ast.parse(lora_source))
    if bases.get("AirLLMLoRA") != ("AirLLMQwen3_5",):
        raise ValueError("Qwen3.5 trainer ancestry drift")
    if bases.get("AirLLMLoRAQwen4Exp") != ("AirLLMQwen4Exp",):
        raise ValueError("Qwen4Exp trainer ancestry drift")

    family_routes = {
        "qwen3_5": "ADMIT_SOURCE_FAMILY",
        "qwen3_8_dense": "ADMIT_SOURCE_FAMILY",
        "qwen4_exp": "ADMIT_SOURCE_FAMILY",
        "glm_moe_dsa": "HOLD_PORT_REQUIRED",
        "glm": "HOLD_PORT_REQUIRED",
    }

    load_text = _function_text(linear_source, "load_lora_state_dict")
    if "owned = dict(module.named_parameters())" not in load_text or "for name, value in state.items()" not in load_text:
        raise ValueError("loader structure changed; re-audit required")

    partial_guard = "set(state)" not in load_text and "state.keys()" not in load_text
    provenance_required = (
        "base_checkpoint_root" not in linear_source
        and "tokenizer_root" not in linear_source
        and "runtime_root" not in linear_source
    )
    return SourceReceipt(commit, roots, family_routes, partial_guard, provenance_required)


def check_key_coverage(expected: set[str], provided: set[str]) -> tuple[bool, dict[str, list[str]]]:
    missing = sorted(expected - provided)
    unexpected = sorted(provided - expected)
    if missing or unexpected:
        return False, {"missing": missing, "unexpected": unexpected}
    return True, {"missing": [], "unexpected": []}


def expected_family_trainer(family: str) -> str | None:
    if family in ("qwen3_5", "qwen3_8_dense"):
        return "AirLLMLoRA"
    if family == "qwen4_exp":
        return "AirLLMLoRAQwen4Exp"
    return None


def admit(
    *,
    source: SourceReceipt,
    manifest: AdapterManifest,
    observed_base_checkpoint_root: str,
    observed_config_root: str,
    observed_tokenizer_root: str,
    observed_runtime_root: str,
    observed_target_paths: set[str],
    provided_adapter_keys: set[str],
) -> Admission:
    source_root = source.receipt_root
    adapter_root = manifest.identity_root

    if source.family_routes.get(manifest.family, "HOLD_UNKNOWN") == "HOLD_PORT_REQUIRED":
        return Admission(
            "HOLD_PORT_REQUIRED",
            "CURRENT_AIRLLM_STREAMED_TRAINER_IS_QWEN_SPECIFIC",
            source_root,
            adapter_root,
        )

    want = expected_family_trainer(manifest.family)
    if want is None or manifest.trainer_class != want:
        return Admission("HOLD_FAMILY_MISMATCH", "TRAINER_FAMILY_MISMATCH", source_root, adapter_root)

    observed = (
        observed_base_checkpoint_root,
        observed_config_root,
        observed_tokenizer_root,
        observed_runtime_root,
    )
    expected = (
        manifest.base_checkpoint_root,
        manifest.base_config_root,
        manifest.tokenizer_root,
        manifest.runtime_root,
    )
    if observed != expected:
        return Admission(
            "HOLD_REBIND_REQUIRED",
            "BASE_CONFIG_TOKENIZER_OR_RUNTIME_DRIFT",
            source_root,
            adapter_root,
        )

    if set(manifest.target_paths) != set(observed_target_paths):
        return Admission(
            "HOLD_TARGET_TOPOLOGY_MISMATCH",
            "TARGET_MODULE_TOPOLOGY_DRIFT",
            source_root,
            adapter_root,
        )

    ok, detail = check_key_coverage(set(manifest.adapter_keys), provided_adapter_keys)
    if not ok:
        return Admission(
            "HOLD_ADAPTER_KEY_COVERAGE",
            "ADAPTER_KEY_SET_NOT_EXACT:" + jhash(detail),
            source_root,
            adapter_root,
        )

    return Admission(
        "ADMIT_D0_ADAPTER_LOAD",
        "EXACT_SOURCE_BASE_RUNTIME_TARGET_AND_KEY_COVERAGE",
        source_root,
        adapter_root,
    )


def omega8(bits: tuple[int, ...]) -> bool:
    # source, family, base, tokenizer, runtime, targets, keys, authority separation
    return len(bits) == 8 and all(value == 1 for value in bits)
