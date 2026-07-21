"""Immutable relationship contracts for the Aura Coding Relationship Compass.

These contracts are deterministic, proposal-only projections over Aura's existing
intent, source, policy, graph, and memory owners.  They do not grant mutation,
patch, execution, commit, publication, or merge authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping, Sequence, TypeVar

RELATIONSHIP_CONTRACT_VERSION = "AURA_RELATIONSHIP_CONTRACT_V1"
RELATIONSHIP_COMPATIBILITY_VERSION = "AURA_RELATIONSHIP_COMPATIBILITY_V1"
RELATIONAL_NEIGHBORHOOD_REQUEST_VERSION = "AURA_RELATIONAL_NEIGHBORHOOD_REQUEST_V1"
COMPASS_OBJECTIVE_CONTRACT_VERSION = "AURA_CODING_RELATIONSHIP_COMPASS_OBJECTIVE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class RelationshipDomain(str, Enum):
    CODE = "CODE"
    MEMORY = "MEMORY"
    GOVERNANCE = "GOVERNANCE"
    SPATIAL = "SPATIAL"
    NETWORK = "NETWORK"
    OTHER = "OTHER"


class TruthClass(str, Enum):
    EXACT_SOURCE = "EXACT_SOURCE"
    EXACT_DECLARED = "EXACT_DECLARED"
    EXACT_RUNTIME = "EXACT_RUNTIME"
    DERIVED = "DERIVED"
    ADVISORY = "ADVISORY"
    UNKNOWN = "UNKNOWN"


class ProofStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    GROUNDED = "GROUNDED"
    TEST_REQUIRED = "TEST_REQUIRED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class AuthorityPosture(str, Enum):
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    REVIEW_ONLY = "REVIEW_ONLY"
    OBSERVATION_ONLY = "OBSERVATION_ONLY"


class CompatibilityOutcome(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    ADAPTER_REQUIRED = "ADAPTER_REQUIRED"
    AUXILIARY_ONLY = "AUXILIARY_ONLY"
    PROHIBITED = "PROHIBITED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class HardGuardCode(str, Enum):
    REPOSITORY_IDENTITY = "REPOSITORY_IDENTITY"
    SOURCE_FRESHNESS = "SOURCE_FRESHNESS"
    CAPABILITY_POLICY_SCOPE = "CAPABILITY_POLICY_SCOPE"
    ACTOR_AUTHORITY = "ACTOR_AUTHORITY"
    PROHIBITED_RELATIONSHIP = "PROHIBITED_RELATIONSHIP"
    RESOURCE_BUDGET = "RESOURCE_BUDGET"
    PROOF_READINESS = "PROOF_READINESS"


class CapabilitySelectionStatus(str, Enum):
    SELECTED = "SELECTED"
    ACTIVE = "ACTIVE"
    AUXILIARY = "AUXILIARY"
    UNRESOLVED = "UNRESOLVED"
    PROHIBITED = "PROHIBITED"


T = TypeVar("T")


def _canonical_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _ordered_unique(values: Iterable[Any]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Iterable):
        raise TypeError("sequence value must be a non-text iterable")
    return tuple(dict.fromkeys(_canonical_text(value) for value in values if _canonical_text(value)))


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be a boolean")
    return value


def _canonical_repo_path(value: Any) -> str:
    text = _canonical_text(value)
    if not text or "\\" in text or "//" in text:
        raise ValueError("source file_path must be canonical repository-relative POSIX form")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("source file_path must be canonical repository-relative POSIX form")
    if path.as_posix() != text:
        raise ValueError("source file_path must be canonical repository-relative POSIX form")
    return text


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def content_digest(value: Any, *, digest_size: int = 24) -> str:
    return hashlib.blake2b(canonical_json(value).encode("utf-8"), digest_size=digest_size).hexdigest()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value


def _strict_keys(value: Mapping[str, Any], *, required: set[str], optional: set[str] = set()) -> None:
    keys = set(value)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise ValueError("missing keys: " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError("unknown keys: " + ", ".join(sorted(unknown)))


def _enum(enum_type: type[T], value: Any, name: str) -> T:
    try:
        return enum_type(str(value))  # type: ignore[call-arg]
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)  # type: ignore[attr-defined]
        raise ValueError(f"{name} must be one of: {allowed}") from exc


def _positive_int(value: Any, name: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


@dataclass(frozen=True)
class SixSlotProjection:
    dir: str
    asp: str
    class_: str
    subj: str
    voice: str
    stem: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SixSlotProjection":
        data = _mapping(value, "slots")
        _strict_keys(data, required={"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"})
        normalized = {key: _canonical_text(data[key]) for key in data}
        empty = [key for key, item in normalized.items() if not item]
        if empty:
            raise ValueError("empty slot fillers: " + ", ".join(sorted(empty)))
        return cls(
            dir=normalized["DIR"], asp=normalized["ASP"], class_=normalized["CLASS"],
            subj=normalized["SUBJ"], voice=normalized["VOICE"], stem=normalized["STEM"],
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "DIR": self.dir, "ASP": self.asp, "CLASS": self.class_,
            "SUBJ": self.subj, "VOICE": self.voice, "STEM": self.stem,
        }


@dataclass(frozen=True)
class RepositoryIdentity:
    repo_head: str
    working_tree_digest: str
    relational_index_digest: str
    atlas_digest: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RepositoryIdentity":
        data = _mapping(value, "source_repository")
        _strict_keys(
            data,
            required={"repo_head", "working_tree_digest", "relational_index_digest", "atlas_digest"},
        )
        fields = {key: _canonical_text(data[key]) for key in data}
        if not fields["repo_head"]:
            raise ValueError("repo_head is required")
        return cls(**fields)

    def to_dict(self) -> dict[str, str]:
        return {
            "repo_head": self.repo_head,
            "working_tree_digest": self.working_tree_digest,
            "relational_index_digest": self.relational_index_digest,
            "atlas_digest": self.atlas_digest,
        }


@dataclass(frozen=True)
class ResourceBudget:
    max_hops: int = 1
    max_nodes: int = 64
    max_edges: int = 256
    max_candidate_pairs: int = 2016
    max_output_bytes: int = 1_000_000
    max_elapsed_ms: int = 30_000

    def __post_init__(self) -> None:
        _positive_int(self.max_hops, "max_hops", minimum=1, maximum=3)
        _positive_int(self.max_nodes, "max_nodes", minimum=1, maximum=256)
        _positive_int(self.max_edges, "max_edges", minimum=1, maximum=1024)
        _positive_int(self.max_candidate_pairs, "max_candidate_pairs", minimum=0, maximum=32640)
        _positive_int(self.max_output_bytes, "max_output_bytes", minimum=1)
        _positive_int(self.max_elapsed_ms, "max_elapsed_ms", minimum=1)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResourceBudget":
        data = _mapping(value, "resource_budget")
        required = {
            "max_hops", "max_nodes", "max_edges", "max_candidate_pairs",
            "max_output_bytes", "max_elapsed_ms",
        }
        _strict_keys(data, required=required)
        return cls(
            max_hops=_positive_int(data["max_hops"], "max_hops", minimum=1, maximum=3),
            max_nodes=_positive_int(data["max_nodes"], "max_nodes", minimum=1, maximum=256),
            max_edges=_positive_int(data["max_edges"], "max_edges", minimum=1, maximum=1024),
            max_candidate_pairs=_positive_int(
                data["max_candidate_pairs"], "max_candidate_pairs", minimum=0, maximum=32640
            ),
            max_output_bytes=_positive_int(data["max_output_bytes"], "max_output_bytes", minimum=1),
            max_elapsed_ms=_positive_int(data["max_elapsed_ms"], "max_elapsed_ms", minimum=1),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_hops": self.max_hops,
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_candidate_pairs": self.max_candidate_pairs,
            "max_output_bytes": self.max_output_bytes,
            "max_elapsed_ms": self.max_elapsed_ms,
        }


@dataclass(frozen=True)
class SourceReference:
    file_path: str
    symbol: str
    line_start: int
    line_end: int
    source_hash: str
    file_source_hash: str = ""

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceReference":
        data = _mapping(value, "source_ref")
        _strict_keys(
            data,
            required={"file_path", "symbol", "line_start", "line_end", "source_hash"},
            optional={"file_source_hash"},
        )
        line_start = _positive_int(data["line_start"], "line_start", minimum=1)
        line_end = _positive_int(data["line_end"], "line_end", minimum=line_start)
        file_path = _canonical_repo_path(data["file_path"])
        source_hash = _canonical_text(data["source_hash"])
        if not file_path or not source_hash:
            raise ValueError("source refs require file_path and source_hash")
        return cls(
            file_path=file_path,
            symbol=_canonical_text(data["symbol"]),
            line_start=line_start,
            line_end=line_end,
            source_hash=source_hash,
            file_source_hash=_canonical_text(data.get("file_source_hash")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "symbol": self.symbol,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "source_hash": self.source_hash,
            "file_source_hash": self.file_source_hash,
        }


@dataclass(frozen=True)
class CapabilitySelection:
    capability_id: str
    status: CapabilitySelectionStatus
    reasons: tuple[str, ...] = ()
    implementation_files: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    model_required: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CapabilitySelection":
        data = _mapping(value, "capability_selection")
        _strict_keys(
            data,
            required={
                "capability_id", "status", "reasons", "implementation_files",
                "symbols", "tests", "model_required",
            },
        )
        capability_id = _canonical_text(data["capability_id"])
        if not capability_id:
            raise ValueError("capability_id is required")
        return cls(
            capability_id=capability_id,
            status=_enum(CapabilitySelectionStatus, data["status"], "status"),
            reasons=_ordered_unique(data["reasons"]),
            implementation_files=_ordered_unique(data["implementation_files"]),
            symbols=_ordered_unique(data["symbols"]),
            tests=_ordered_unique(data["tests"]),
            model_required=_strict_bool(data["model_required"], "model_required"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "status": self.status.value,
            "reasons": list(self.reasons),
            "implementation_files": list(self.implementation_files),
            "symbols": list(self.symbols),
            "tests": list(self.tests),
            "model_required": self.model_required,
        }


def capability_selections_from_path(path_packet: Mapping[str, Any]) -> tuple[CapabilitySelection, ...]:
    packet = _mapping(path_packet, "capability_path")
    required = _ordered_unique(packet.get("required_capability_ids", ()))
    deterministic = set(_ordered_unique(packet.get("deterministic_capability_ids", ())))
    model_dependent = set(_ordered_unique(packet.get("model_dependent_capability_ids", ())))
    unresolved = set(_ordered_unique(packet.get("unresolved_execution_capability_ids", ())))
    prohibited = set(_ordered_unique(packet.get("prohibited_capability_ids", ())))
    auxiliary = set(_ordered_unique(packet.get("auxiliary_capability_ids", ())))
    details = {
        _canonical_text(item.get("capability_id")): item
        for item in packet.get("path_details", ())
        if isinstance(item, Mapping) and _canonical_text(item.get("capability_id"))
    }
    selections: list[CapabilitySelection] = []
    all_ids = _ordered_unique([*required, *unresolved, *prohibited, *auxiliary])
    for capability_id in all_ids:
        if capability_id in prohibited:
            status = CapabilitySelectionStatus.PROHIBITED
        elif capability_id in unresolved:
            status = CapabilitySelectionStatus.UNRESOLVED
        elif capability_id in deterministic:
            status = CapabilitySelectionStatus.ACTIVE
        elif capability_id in auxiliary:
            status = CapabilitySelectionStatus.AUXILIARY
        else:
            status = CapabilitySelectionStatus.SELECTED
        detail = details.get(capability_id, {})
        selections.append(
            CapabilitySelection(
                capability_id=capability_id,
                status=status,
                reasons=_ordered_unique(
                    [
                        detail.get("reason", ""),
                        detail.get("selection_reason", ""),
                        f"connectome_status:{status.value.lower()}",
                    ]
                ),
                implementation_files=_ordered_unique(detail.get("implemented_by", ())),
                symbols=_ordered_unique(detail.get("symbols", ())),
                tests=_ordered_unique(detail.get("tests", ())),
                model_required=capability_id in model_dependent,
            )
        )
    return tuple(selections)


def capability_class_index(selections: Sequence[CapabilitySelection]) -> dict[str, list[str]]:
    output = {status.value: [] for status in CapabilitySelectionStatus}
    for selection in selections:
        output[selection.status.value].append(selection.capability_id)
    return output


@dataclass(frozen=True)
class CompassObjectiveContract:
    objective: str
    objective_digest: str
    intent_packet_digest: str
    slots: SixSlotProjection
    repository_head: str
    target_files: tuple[str, ...]
    target_symbols: tuple[str, ...]
    capabilities: tuple[CapabilitySelection, ...]
    route_reasons: tuple[str, ...]
    zero_model_eligible: bool
    contract_id: str = ""

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        intent_packet: Mapping[str, Any],
        intent_packet_digest: str,
        repository_head: str,
        target_files: Sequence[str],
        target_symbols: Sequence[str],
        capabilities: Sequence[CapabilitySelection],
        route_reasons: Sequence[str],
    ) -> "CompassObjectiveContract":
        canonical_objective = _canonical_text(objective)
        if not canonical_objective:
            raise ValueError("objective is required")
        packet = _mapping(intent_packet, "intent_packet")
        slots = SixSlotProjection.from_mapping(_mapping(packet.get("slots"), "intent slots"))
        values = {
            "schema_version": COMPASS_OBJECTIVE_CONTRACT_VERSION,
            "objective": canonical_objective,
            "objective_digest": content_digest(canonical_objective, digest_size=20),
            "intent_packet_digest": _canonical_text(intent_packet_digest),
            "slots": slots.to_dict(),
            "repository_head": _canonical_text(repository_head),
            "target_files": list(_ordered_unique(target_files)),
            "target_symbols": list(_ordered_unique(target_symbols)),
            "capabilities": [item.to_dict() for item in capabilities],
            "route_reasons": list(_ordered_unique(route_reasons)),
            "zero_model_eligible": not any(item.model_required for item in capabilities)
            and not any(item.status in {CapabilitySelectionStatus.UNRESOLVED, CapabilitySelectionStatus.PROHIBITED} for item in capabilities),
            "safe_to_patch": False,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        if not values["intent_packet_digest"]:
            raise ValueError("intent_packet_digest is required")
        if not values["repository_head"]:
            raise ValueError("repository_head is required")
        if not values["target_files"]:
            raise ValueError("at least one bounded target file is required")
        contract_id = content_digest(values)
        return cls(
            objective=values["objective"],
            objective_digest=values["objective_digest"],
            intent_packet_digest=values["intent_packet_digest"],
            slots=slots,
            repository_head=values["repository_head"],
            target_files=tuple(values["target_files"]),
            target_symbols=tuple(values["target_symbols"]),
            capabilities=tuple(capabilities),
            route_reasons=tuple(values["route_reasons"]),
            zero_model_eligible=bool(values["zero_model_eligible"]),
            contract_id=contract_id,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CompassObjectiveContract":
        data = _mapping(value, "objective_contract")
        required = {
            "schema_version", "contract_id", "objective", "objective_digest",
            "intent_packet_digest", "slots", "repository_head", "target_files",
            "target_symbols", "capabilities", "route_reasons", "zero_model_eligible",
            "safe_to_patch", "production_mutation", "human_review_required",
            "patch_authority", "vsa_patch_authority",
        }
        _strict_keys(data, required=required)
        if data["schema_version"] != COMPASS_OBJECTIVE_CONTRACT_VERSION:
            raise ValueError("unsupported objective contract schema version")
        if data["safe_to_patch"] is not False or data["production_mutation"] is not False:
            raise ValueError("objective contract authority flags must remain false")
        if data["human_review_required"] is not True:
            raise ValueError("human_review_required must remain true")
        if data["patch_authority"] != PATCH_AUTHORITY or data["vsa_patch_authority"] is not False:
            raise ValueError("objective contract authority metadata is invalid")
        contract = cls(
            objective=_canonical_text(data["objective"]),
            objective_digest=_canonical_text(data["objective_digest"]),
            intent_packet_digest=_canonical_text(data["intent_packet_digest"]),
            slots=SixSlotProjection.from_mapping(data["slots"]),
            repository_head=_canonical_text(data["repository_head"]),
            target_files=_ordered_unique(data["target_files"]),
            target_symbols=_ordered_unique(data["target_symbols"]),
            capabilities=tuple(CapabilitySelection.from_dict(item) for item in data["capabilities"]),
            route_reasons=_ordered_unique(data["route_reasons"]),
            zero_model_eligible=_strict_bool(data["zero_model_eligible"], "zero_model_eligible"),
            contract_id=_canonical_text(data["contract_id"]),
        )
        expected = content_digest({key: item for key, item in contract.to_dict().items() if key != "contract_id"})
        if contract.contract_id != expected:
            raise ValueError("objective contract digest mismatch")
        if contract.objective_digest != content_digest(contract.objective, digest_size=20):
            raise ValueError("objective digest mismatch")
        if not contract.intent_packet_digest or not contract.repository_head or not contract.target_files:
            raise ValueError("objective contract grounding fields are incomplete")
        expected_zero_model = not any(item.model_required for item in contract.capabilities) and not any(
            item.status in {CapabilitySelectionStatus.UNRESOLVED, CapabilitySelectionStatus.PROHIBITED}
            for item in contract.capabilities
        )
        if contract.zero_model_eligible is not expected_zero_model:
            raise ValueError("zero_model_eligible does not match capability classes")
        return contract

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": COMPASS_OBJECTIVE_CONTRACT_VERSION,
            "contract_id": self.contract_id,
            "objective": self.objective,
            "objective_digest": self.objective_digest,
            "intent_packet_digest": self.intent_packet_digest,
            "slots": self.slots.to_dict(),
            "repository_head": self.repository_head,
            "target_files": list(self.target_files),
            "target_symbols": list(self.target_symbols),
            "capabilities": [item.to_dict() for item in self.capabilities],
            "route_reasons": list(self.route_reasons),
            "zero_model_eligible": self.zero_model_eligible,
            "safe_to_patch": False,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


@dataclass(frozen=True)
class RelationshipContract:
    objective_digest: str
    intent_packet_digest: str
    source_repository: RepositoryIdentity
    domain: RelationshipDomain
    slots: SixSlotProjection
    truth_class: TruthClass
    authority_posture: AuthorityPosture
    proof_status: ProofStatus
    policy_scope: tuple[str, ...]
    resource_budget: ResourceBudget
    source_refs: tuple[SourceReference, ...]
    prohibition_ids: tuple[str, ...] = ()
    contract_id: str = ""

    def __post_init__(self) -> None:
        if not _canonical_text(self.objective_digest) or not _canonical_text(self.intent_packet_digest):
            raise ValueError("objective_digest and intent_packet_digest are required")
        if not self.policy_scope:
            raise ValueError("policy_scope requires at least one explicit scope")
        if not self.source_refs:
            raise ValueError("source_refs require exact evidence")

    @classmethod
    def create(cls, **kwargs: Any) -> "RelationshipContract":
        contract = cls(**kwargs)
        digest = content_digest({key: item for key, item in contract.to_dict().items() if key != "contract_id"})
        return cls(**{**contract.__dict__, "contract_id": digest})

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationshipContract":
        data = _mapping(value, "relationship_contract")
        required = {
            "schema_version", "contract_id", "objective_digest", "intent_packet_digest",
            "source_repository", "domain", "slots", "truth_class", "authority_posture",
            "proof_status", "policy_scope", "resource_budget", "source_refs",
            "prohibition_ids", "safe_to_patch", "production_mutation",
            "human_review_required", "patch_authority", "vsa_patch_authority",
        }
        _strict_keys(data, required=required)
        if data["schema_version"] != RELATIONSHIP_CONTRACT_VERSION:
            raise ValueError("unsupported relationship contract schema version")
        if data["safe_to_patch"] is not False or data["production_mutation"] is not False:
            raise ValueError("relationship contract cannot carry mutation authority")
        if data["human_review_required"] is not True:
            raise ValueError("human_review_required must remain true")
        if data["patch_authority"] != PATCH_AUTHORITY or data["vsa_patch_authority"] is not False:
            raise ValueError("relationship contract authority metadata is invalid")
        contract = cls(
            objective_digest=_canonical_text(data["objective_digest"]),
            intent_packet_digest=_canonical_text(data["intent_packet_digest"]),
            source_repository=RepositoryIdentity.from_dict(data["source_repository"]),
            domain=_enum(RelationshipDomain, data["domain"], "domain"),
            slots=SixSlotProjection.from_mapping(data["slots"]),
            truth_class=_enum(TruthClass, data["truth_class"], "truth_class"),
            authority_posture=_enum(AuthorityPosture, data["authority_posture"], "authority_posture"),
            proof_status=_enum(ProofStatus, data["proof_status"], "proof_status"),
            policy_scope=_ordered_unique(data["policy_scope"]),
            resource_budget=ResourceBudget.from_dict(data["resource_budget"]),
            source_refs=tuple(SourceReference.from_dict(item) for item in data["source_refs"]),
            prohibition_ids=_ordered_unique(data["prohibition_ids"]),
            contract_id=_canonical_text(data["contract_id"]),
        )
        expected = content_digest({key: item for key, item in contract.to_dict().items() if key != "contract_id"})
        if expected != contract.contract_id:
            raise ValueError("relationship contract digest mismatch")
        return contract

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELATIONSHIP_CONTRACT_VERSION,
            "contract_id": self.contract_id,
            "objective_digest": self.objective_digest,
            "intent_packet_digest": self.intent_packet_digest,
            "source_repository": self.source_repository.to_dict(),
            "domain": self.domain.value,
            "slots": self.slots.to_dict(),
            "truth_class": self.truth_class.value,
            "authority_posture": self.authority_posture.value,
            "proof_status": self.proof_status.value,
            "policy_scope": list(self.policy_scope),
            "resource_budget": self.resource_budget.to_dict(),
            "source_refs": [item.to_dict() for item in self.source_refs],
            "prohibition_ids": list(self.prohibition_ids),
            "safe_to_patch": False,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


@dataclass(frozen=True)
class HardGuardResult:
    code: HardGuardCode
    passed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "passed": self.passed, "reason": self.reason}


@dataclass(frozen=True)
class RelationshipCompatibilityAssessment:
    left_contract_digest: str
    right_contract_digest: str
    outcome: CompatibilityOutcome
    hard_guard_results: tuple[HardGuardResult, ...]
    required_adapters: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    required_verifiers: tuple[str, ...] = ()
    advisory_score: float | None = None
    assessment_id: str = ""

    def __post_init__(self) -> None:
        if not _canonical_text(self.left_contract_digest) or not _canonical_text(self.right_contract_digest):
            raise ValueError("compatibility assessments require both contract digests")
        expected_codes = tuple(HardGuardCode)
        actual_codes = tuple(item.code for item in self.hard_guard_results)
        if actual_codes != expected_codes:
            raise ValueError("hard guards must be complete and preserve canonical evaluation order")
        if self.advisory_score is not None:
            if isinstance(self.advisory_score, bool) or not isinstance(self.advisory_score, (int, float)):
                raise TypeError("advisory_score must be numeric or null")
            if not all(item.passed for item in self.hard_guard_results):
                raise ValueError("advisory ranking is allowed only after every hard guard passes")

    @classmethod
    def create(cls, **kwargs: Any) -> "RelationshipCompatibilityAssessment":
        assessment = cls(**kwargs)
        digest = content_digest({key: item for key, item in assessment.to_dict().items() if key != "assessment_id"})
        return cls(**{**assessment.__dict__, "assessment_id": digest})

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationshipCompatibilityAssessment":
        data = _mapping(value, "relationship_compatibility")
        required = {
            "schema_version", "assessment_id", "left_contract_digest", "right_contract_digest",
            "outcome", "hard_guard_results", "required_adapters", "missing_evidence",
            "risks", "required_verifiers", "advisory_score", "safe_to_patch",
            "production_mutation", "human_review_required", "patch_authority", "vsa_patch_authority",
        }
        _strict_keys(data, required=required)
        if data["schema_version"] != RELATIONSHIP_COMPATIBILITY_VERSION:
            raise ValueError("unsupported compatibility schema version")
        if data["safe_to_patch"] is not False or data["production_mutation"] is not False:
            raise ValueError("compatibility assessment cannot carry mutation authority")
        if data["human_review_required"] is not True:
            raise ValueError("human_review_required must remain true")
        if data["patch_authority"] != PATCH_AUTHORITY or data["vsa_patch_authority"] is not False:
            raise ValueError("compatibility authority metadata is invalid")
        guards_raw = data["hard_guard_results"]
        if isinstance(guards_raw, (str, bytes, bytearray)) or not isinstance(guards_raw, Sequence):
            raise TypeError("hard_guard_results must be a sequence")
        guards: list[HardGuardResult] = []
        for raw in guards_raw:
            item = _mapping(raw, "hard_guard_result")
            _strict_keys(item, required={"code", "passed", "reason"})
            reason = _canonical_text(item["reason"])
            if not reason:
                raise ValueError("hard guard reason is required")
            guards.append(HardGuardResult(
                code=_enum(HardGuardCode, item["code"], "hard guard code"),
                passed=_strict_bool(item["passed"], "hard guard passed"),
                reason=reason,
            ))
        assessment = cls(
            left_contract_digest=_canonical_text(data["left_contract_digest"]),
            right_contract_digest=_canonical_text(data["right_contract_digest"]),
            outcome=_enum(CompatibilityOutcome, data["outcome"], "outcome"),
            hard_guard_results=tuple(guards),
            required_adapters=_ordered_unique(data["required_adapters"]),
            missing_evidence=_ordered_unique(data["missing_evidence"]),
            risks=_ordered_unique(data["risks"]),
            required_verifiers=_ordered_unique(data["required_verifiers"]),
            advisory_score=data["advisory_score"],
            assessment_id=_canonical_text(data["assessment_id"]),
        )
        expected = content_digest({key: item for key, item in assessment.to_dict().items() if key != "assessment_id"})
        if assessment.assessment_id != expected:
            raise ValueError("compatibility assessment digest mismatch")
        return assessment

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELATIONSHIP_COMPATIBILITY_VERSION,
            "assessment_id": self.assessment_id,
            "left_contract_digest": self.left_contract_digest,
            "right_contract_digest": self.right_contract_digest,
            "outcome": self.outcome.value,
            "hard_guard_results": [item.to_dict() for item in self.hard_guard_results],
            "required_adapters": list(self.required_adapters),
            "missing_evidence": list(self.missing_evidence),
            "risks": list(self.risks),
            "required_verifiers": list(self.required_verifiers),
            "advisory_score": self.advisory_score,
            "safe_to_patch": False,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def evaluate_relationship_compatibility(
    left: RelationshipContract,
    right: RelationshipContract,
) -> RelationshipCompatibilityAssessment:
    guards: list[HardGuardResult] = []

    same_repository = left.source_repository.repo_head == right.source_repository.repo_head
    guards.append(HardGuardResult(HardGuardCode.REPOSITORY_IDENTITY, same_repository, "exact repo heads match" if same_repository else "repo heads differ"))

    fresh = bool(left.source_refs and right.source_refs) and left.truth_class is not TruthClass.UNKNOWN and right.truth_class is not TruthClass.UNKNOWN
    guards.append(HardGuardResult(HardGuardCode.SOURCE_FRESHNESS, fresh, "exact source refs present" if fresh else "exact source evidence is missing"))

    shared_scope = bool(set(left.policy_scope) & set(right.policy_scope))
    guards.append(HardGuardResult(HardGuardCode.CAPABILITY_POLICY_SCOPE, shared_scope, "policy scopes overlap" if shared_scope else "policy scopes do not overlap"))

    proposal_only = left.authority_posture is not None and right.authority_posture is not None
    guards.append(HardGuardResult(HardGuardCode.ACTOR_AUTHORITY, proposal_only, "derived contracts remain proposal/review scoped"))

    prohibited = bool(set(left.prohibition_ids) | set(right.prohibition_ids))
    guards.append(HardGuardResult(HardGuardCode.PROHIBITED_RELATIONSHIP, not prohibited, "no prohibition bound" if not prohibited else "a prohibition is bound to the candidate"))

    budget_fit = (
        left.resource_budget.max_nodes <= 256 and right.resource_budget.max_nodes <= 256
        and left.resource_budget.max_edges <= 1024 and right.resource_budget.max_edges <= 1024
    )
    guards.append(HardGuardResult(HardGuardCode.RESOURCE_BUDGET, budget_fit, "budgets are within hard limits" if budget_fit else "budget exceeds hard limit"))

    proof_ready = left.proof_status not in {ProofStatus.UNVERIFIED, ProofStatus.REJECTED} and right.proof_status not in {ProofStatus.UNVERIFIED, ProofStatus.REJECTED}
    guards.append(HardGuardResult(HardGuardCode.PROOF_READINESS, proof_ready, "proof states admit preflight" if proof_ready else "proof readiness is insufficient"))

    failed = {item.code for item in guards if not item.passed}
    if HardGuardCode.PROHIBITED_RELATIONSHIP in failed or HardGuardCode.REPOSITORY_IDENTITY in failed or HardGuardCode.CAPABILITY_POLICY_SCOPE in failed:
        outcome = CompatibilityOutcome.PROHIBITED
    elif HardGuardCode.SOURCE_FRESHNESS in failed or HardGuardCode.PROOF_READINESS in failed:
        outcome = CompatibilityOutcome.INSUFFICIENT_EVIDENCE
    elif HardGuardCode.RESOURCE_BUDGET in failed:
        outcome = CompatibilityOutcome.ADAPTER_REQUIRED
    else:
        outcome = CompatibilityOutcome.COMPATIBLE

    return RelationshipCompatibilityAssessment.create(
        left_contract_digest=left.contract_id,
        right_contract_digest=right.contract_id,
        outcome=outcome,
        hard_guard_results=tuple(guards),
        required_adapters=("bounded_resource_adapter",) if outcome is CompatibilityOutcome.ADAPTER_REQUIRED else (),
        missing_evidence=tuple(item.code.value for item in guards if not item.passed and item.code in {HardGuardCode.SOURCE_FRESHNESS, HardGuardCode.PROOF_READINESS}),
        risks=tuple(item.reason for item in guards if not item.passed),
        required_verifiers=("exact_source_freshness", "focused_tests"),
        advisory_score=None,
    )


@dataclass(frozen=True)
class RelationalNeighborhoodRequest:
    objective_digest: str
    seed_participant_ids: tuple[str, ...]
    seed_source_refs: tuple[SourceReference, ...]
    max_hops: int = 1
    max_nodes: int = 64
    max_edges: int = 256
    max_candidate_pairs: int = 2016
    max_output_bytes: int = 1_000_000
    max_elapsed_ms: int = 30_000
    allowed_relation_types: tuple[str, ...] = ()
    minimum_truth_class: TruthClass = TruthClass.EXACT_SOURCE
    include_tests: bool = True
    include_docs: bool = False
    include_auxiliary: bool = True
    stop_on_prohibition: bool = True

    def __post_init__(self) -> None:
        ResourceBudget(
            max_hops=self.max_hops,
            max_nodes=self.max_nodes,
            max_edges=self.max_edges,
            max_candidate_pairs=self.max_candidate_pairs,
            max_output_bytes=self.max_output_bytes,
            max_elapsed_ms=self.max_elapsed_ms,
        )
        if not self.objective_digest:
            raise ValueError("objective_digest is required")
        if not self.seed_participant_ids and not self.seed_source_refs:
            raise ValueError("at least one exact seed is required")
        for name in ("include_tests", "include_docs", "include_auxiliary", "stop_on_prohibition"):
            _strict_bool(getattr(self, name), name)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationalNeighborhoodRequest":
        data = _mapping(value, "relational_neighborhood_request")
        required = {
            "schema_version", "objective_digest", "seed_participant_ids", "seed_source_refs",
            "max_hops", "max_nodes", "max_edges", "max_candidate_pairs", "max_output_bytes",
            "max_elapsed_ms", "allowed_relation_types", "minimum_truth_class", "include_tests",
            "include_docs", "include_auxiliary", "stop_on_prohibition", "safe_to_patch",
            "production_mutation", "human_review_required", "patch_authority", "vsa_patch_authority",
        }
        _strict_keys(data, required=required)
        if data["schema_version"] != RELATIONAL_NEIGHBORHOOD_REQUEST_VERSION:
            raise ValueError("unsupported neighborhood request schema version")
        if data["safe_to_patch"] is not False or data["production_mutation"] is not False:
            raise ValueError("neighborhood request cannot carry mutation authority")
        if data["human_review_required"] is not True:
            raise ValueError("human_review_required must remain true")
        if data["patch_authority"] != PATCH_AUTHORITY or data["vsa_patch_authority"] is not False:
            raise ValueError("neighborhood request authority metadata is invalid")
        budget = ResourceBudget.from_dict({key: data[key] for key in (
            "max_hops", "max_nodes", "max_edges", "max_candidate_pairs", "max_output_bytes", "max_elapsed_ms"
        )})
        return cls(
            objective_digest=_canonical_text(data["objective_digest"]),
            seed_participant_ids=_ordered_unique(data["seed_participant_ids"]),
            seed_source_refs=tuple(SourceReference.from_dict(item) for item in data["seed_source_refs"]),
            max_hops=budget.max_hops,
            max_nodes=budget.max_nodes,
            max_edges=budget.max_edges,
            max_candidate_pairs=budget.max_candidate_pairs,
            max_output_bytes=budget.max_output_bytes,
            max_elapsed_ms=budget.max_elapsed_ms,
            allowed_relation_types=_ordered_unique(data["allowed_relation_types"]),
            minimum_truth_class=_enum(TruthClass, data["minimum_truth_class"], "minimum_truth_class"),
            include_tests=_strict_bool(data["include_tests"], "include_tests"),
            include_docs=_strict_bool(data["include_docs"], "include_docs"),
            include_auxiliary=_strict_bool(data["include_auxiliary"], "include_auxiliary"),
            stop_on_prohibition=_strict_bool(data["stop_on_prohibition"], "stop_on_prohibition"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELATIONAL_NEIGHBORHOOD_REQUEST_VERSION,
            "objective_digest": self.objective_digest,
            "seed_participant_ids": list(_ordered_unique(self.seed_participant_ids)),
            "seed_source_refs": [item.to_dict() for item in self.seed_source_refs],
            "max_hops": self.max_hops,
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_candidate_pairs": self.max_candidate_pairs,
            "max_output_bytes": self.max_output_bytes,
            "max_elapsed_ms": self.max_elapsed_ms,
            "allowed_relation_types": list(_ordered_unique(self.allowed_relation_types)),
            "minimum_truth_class": self.minimum_truth_class.value,
            "include_tests": self.include_tests,
            "include_docs": self.include_docs,
            "include_auxiliary": self.include_auxiliary,
            "stop_on_prohibition": self.stop_on_prohibition,
            "safe_to_patch": False,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


__all__ = [
    "AuthorityPosture",
    "CapabilitySelection",
    "CapabilitySelectionStatus",
    "COMPASS_OBJECTIVE_CONTRACT_VERSION",
    "CompatibilityOutcome",
    "CompassObjectiveContract",
    "HardGuardCode",
    "HardGuardResult",
    "PATCH_AUTHORITY",
    "ProofStatus",
    "RELATIONAL_NEIGHBORHOOD_REQUEST_VERSION",
    "RELATIONSHIP_COMPATIBILITY_VERSION",
    "RELATIONSHIP_CONTRACT_VERSION",
    "RelationalNeighborhoodRequest",
    "RelationshipCompatibilityAssessment",
    "RelationshipContract",
    "RelationshipDomain",
    "RepositoryIdentity",
    "ResourceBudget",
    "SixSlotProjection",
    "SourceReference",
    "TruthClass",
    "VSA_PATCH_AUTHORITY",
    "canonical_json",
    "capability_class_index",
    "capability_selections_from_path",
    "content_digest",
    "evaluate_relationship_compatibility",
]
