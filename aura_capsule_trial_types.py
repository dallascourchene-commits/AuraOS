"""Typed proposal-only contracts for Phase C3 capsule trials and procedure induction."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any, Mapping

C3_TRIAL_TYPES_VERSION = "AURA_CAPSULE_TRIAL_TYPES_V1"
C3_TRIAL_POLICY_VERSION = "AURA_CAPSULE_TRIAL_POLICY_V1"
C3_TRIAL_CASES_VERSION = "AURA_CAPSULE_TRIAL_CASES_V1"
PROCEDURE_INDUCTION_PROPOSED = "PROCEDURE_INDUCTION_PROPOSED"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

SAFE_PROPOSAL_DIMENSIONS = frozenset({
    "data_aperture.maximum_files",
    "data_aperture.maximum_symbols",
    "data_aperture.maximum_lines",
    "execution_budget.input_tokens",
    "execution_budget.output_tokens",
    "execution_budget.tool_calls",
    "execution_budget.wall_seconds",
})
DATASETS = ("TRAIN", "VALIDATION", "SHADOW")


def canonical_digest(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def repository_relative_path(value: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if (
        not raw
        or path.is_absolute()
        or not path.parts
        or ":" in path.parts[0]
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"unsafe repository-relative path: {value!r}")
    return path.as_posix()


@dataclass(frozen=True)
class CapsuleTrialPolicy:
    policy_id: str
    route_capsule_ref: str
    executor_id: str
    proposal_safe_dimensions: dict[str, tuple[int, ...]]
    maximum_variants: int = 8
    repetitions: int = 2
    minimum_train_score: float = 0.50
    minimum_validation_score: float = 0.50
    minimum_shadow_score: float = 0.50
    maximum_validation_regression: float = 0.02
    maximum_shadow_regression: float = 0.02
    require_reproducibility: bool = True
    version: str = C3_TRIAL_POLICY_VERSION
    threshold_scope: str = "PROPOSAL_ONLY"
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    automatic_capsule_activation: bool = False
    automatic_code_installation: bool = False
    automatic_commit: bool = False
    automatic_push: bool = False
    automatic_merge: bool = False

    def __post_init__(self) -> None:
        if self.version != C3_TRIAL_POLICY_VERSION:
            raise ValueError(f"expected policy schema {C3_TRIAL_POLICY_VERSION}")
        if not str(self.policy_id).strip() or not str(self.executor_id).strip():
            raise ValueError("policy_id and executor_id are required")
        repository_relative_path(self.route_capsule_ref)
        if not 1 <= int(self.maximum_variants) <= 64:
            raise ValueError("maximum_variants must be between 1 and 64")
        if not 1 <= int(self.repetitions) <= 10:
            raise ValueError("repetitions must be between 1 and 10")
        for name in (
            "minimum_train_score",
            "minimum_validation_score",
            "minimum_shadow_score",
            "maximum_validation_regression",
            "maximum_shadow_regression",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        unknown = sorted(set(self.proposal_safe_dimensions) - SAFE_PROPOSAL_DIMENSIONS)
        if unknown:
            raise ValueError(f"unsupported proposal-safe dimensions: {unknown}")
        if not self.proposal_safe_dimensions:
            raise ValueError("at least one proposal-safe dimension is required")
        for path, values in self.proposal_safe_dimensions.items():
            if not values:
                raise ValueError(f"dimension {path} requires at least one value")
            if any(int(value) <= 0 for value in values):
                raise ValueError(f"dimension {path} values must be positive integers")
        if self.threshold_scope != "PROPOSAL_ONLY":
            raise ValueError("C3 thresholds must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or any((
            self.vsa_patch_authority,
            self.automatic_capsule_activation,
            self.automatic_code_installation,
            self.automatic_commit,
            self.automatic_push,
            self.automatic_merge,
        )):
            raise ValueError("C3 policy cannot carry activation, installation, or repository authority")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CapsuleTrialPolicy":
        data = dict(value or {})
        schema = str(data.pop("schema_version", data.get("version", "")) or "")
        data["version"] = schema
        allowed = set(cls.__dataclass_fields__)
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown C3 trial policy fields: {unknown}")
        dimensions = data.get("proposal_safe_dimensions") or {}
        if not isinstance(dimensions, dict):
            raise TypeError("proposal_safe_dimensions must be an object")
        data["proposal_safe_dimensions"] = {
            str(path): tuple(dict.fromkeys(int(item) for item in values))
            for path, values in dimensions.items()
            if isinstance(values, list)
        }
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = data.pop("version")
        data["proposal_safe_dimensions"] = {
            key: list(values) for key, values in sorted(self.proposal_safe_dimensions.items())
        }
        data["runtime_authority"] = False
        return data


@dataclass(frozen=True)
class CapsuleTrialCase:
    case_id: str
    dataset: str
    objective: str
    context_items: tuple[dict[str, Any], ...]
    expected_files: tuple[str, ...]
    expected_symbols: tuple[str, ...] = ()
    expected_tests: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.case_id).strip() or not str(self.objective).strip():
            raise ValueError("case_id and objective are required")
        if self.dataset not in DATASETS:
            raise ValueError(f"dataset must be one of {DATASETS}")
        if not self.context_items:
            raise ValueError("trial case requires bounded context_items")
        for item in self.context_items:
            if not isinstance(item, dict):
                raise TypeError("context_items must contain objects")
            repository_relative_path(str(item.get("path") or ""))
        for path in (*self.expected_files, *self.expected_tests):
            repository_relative_path(path)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CapsuleTrialCase":
        data = dict(value or {})
        allowed = set(cls.__dataclass_fields__)
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown trial case fields: {unknown}")
        data["dataset"] = str(data.get("dataset") or "").upper()
        data["context_items"] = tuple(dict(item) for item in data.get("context_items") or ())
        for key in ("expected_files", "expected_symbols", "expected_tests"):
            data[key] = tuple(str(item) for item in data.get(key) or () if str(item))
        data["metadata"] = dict(data.get("metadata") or {})
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("context_items", "expected_files", "expected_symbols", "expected_tests"):
            data[key] = list(getattr(self, key))
        data["case_digest"] = self.digest()
        return data

    def digest(self) -> str:
        data = asdict(self)
        return canonical_digest(data)


@dataclass(frozen=True)
class CapsuleVariant:
    variant_id: str
    policy_id: str
    capsule_id: str
    capsule_digest: str
    capsule_manifest_digest: str
    source_path: str
    requested_capabilities: tuple[str, ...]
    component_digests: dict[str, str]
    overrides: dict[str, int]
    data_aperture: dict[str, Any]
    execution_budget: dict[str, Any]
    generation_reason: str
    version: str = C3_TRIAL_TYPES_VERSION
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    automatic_capsule_activation: bool = False
    automatic_code_installation: bool = False

    def __post_init__(self) -> None:
        if not self.variant_id or not self.capsule_id or not self.capsule_digest:
            raise ValueError("variant identity is incomplete")
        if set(self.overrides) - SAFE_PROPOSAL_DIMENSIONS:
            raise ValueError("variant contains a non-proposal-safe override")
        if not self.proposal_only or self.patch_authority != PATCH_AUTHORITY or any((
            self.vsa_patch_authority,
            self.automatic_capsule_activation,
            self.automatic_code_installation,
        )):
            raise ValueError("variant cannot carry runtime or installation authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["requested_capabilities"] = list(self.requested_capabilities)
        data["variant_digest"] = canonical_digest(data)
        data["runtime_authority"] = False
        data["automatic_commit"] = False
        data["automatic_push"] = False
        data["automatic_merge"] = False
        return data


@dataclass(frozen=True)
class InducedProcedureProposal:
    procedure_id: str
    run_id: str
    policy_id: str
    capsule_id: str
    capsule_digest: str
    variant_id: str
    ir_floor: str
    floor_history: tuple[str, ...]
    agent_ir_node: dict[str, Any]
    morphology_ir_bridge: dict[str, Any]
    source_trial_ids: tuple[str, ...]
    source_trial_digest: str
    assessment: dict[str, Any]
    created_at: float
    status: str = PROCEDURE_INDUCTION_PROPOSED
    required_next_gate: str = "VERIFIER_AND_HUMAN_REVIEW"
    version: str = C3_TRIAL_TYPES_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    executable_code_generated: bool = False
    automatic_code_installation: bool = False
    automatic_commit: bool = False
    automatic_push: bool = False
    automatic_merge: bool = False

    def __post_init__(self) -> None:
        if self.status != PROCEDURE_INDUCTION_PROPOSED:
            raise ValueError("C3 procedure output must remain a proposal")
        if self.required_next_gate != "VERIFIER_AND_HUMAN_REVIEW":
            raise ValueError("procedure induction requires verifier and human review")
        if self.patch_authority != PATCH_AUTHORITY or any((
            self.vsa_patch_authority,
            self.executable_code_generated,
            self.automatic_code_installation,
            self.automatic_commit,
            self.automatic_push,
            self.automatic_merge,
        )):
            raise ValueError("procedure proposal cannot carry code or repository authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["floor_history"] = list(self.floor_history)
        data["source_trial_ids"] = list(self.source_trial_ids)
        data["procedure_digest"] = canonical_digest(data)
        return data
