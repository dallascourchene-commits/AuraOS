from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping, Sequence

from tools.aura_review.aura_review_context_compiler import (
    PRODUCTION,
    project_review_capsule_inputs,
)

AFFECTED_CONE_SCHEMA = "AffectedConeContextV2"
PLAN_SCHEMA = "QDKTReviewPlanV2"
CACHE_KEY_SCHEMA = "ReviewContextCacheKeyV2"
CACHE_RECORD_SCHEMA = "ReviewContextCacheRecordV2"
CACHE_USE_SCHEMA = "TrustedCacheReadObservationV2"
ROUTER_INPUT_SCHEMA = "TrustedQDKTRouterInputV2"


class ReviewCacheRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class CacheResponsibility(str, Enum):
    REVIEW_CONTEXT = "REVIEW_CONTEXT"
    MODEL_PREFIX_KV = "MODEL_PREFIX_KV"
    REVIEW_RECEIPT = "REVIEW_RECEIPT"


class CacheTier(str, Enum):
    HOT_PREFIX = "HOT_PREFIX"
    WARM_PAGED = "WARM_PAGED"
    COLD_REHYDRATE = "COLD_REHYDRATE"


class GenerationAxis(str, Enum):
    SOURCE = "SOURCE"
    PLACEMENT = "PLACEMENT"
    TARGET = "TARGET"
    PRINCIPAL_CONTEXT = "PRINCIPAL_CONTEXT"
    REVIEW_RUNTIME = "REVIEW_RUNTIME"


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewCacheRefusal(f"INVALID_{name.upper()}")
    return value.strip()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _enum(name: str, value: object, cls):
    if not isinstance(value, cls):
        raise ReviewCacheRefusal(f"INVALID_{name.upper()}")
    return value


def _strict_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise ReviewCacheRefusal(f"INVALID_{name.upper()}")
    return value


def _validate_affected_cone(context: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(context, Mapping) or context.get("schema") != AFFECTED_CONE_SCHEMA:
        raise ReviewCacheRefusal("INVALID_AFFECTED_CONE_CONTEXT")
    if context.get("mode") != PRODUCTION:
        raise ReviewCacheRefusal("NONAUTHORITATIVE_AFFECTED_CONE_CONTEXT")
    try:
        project_review_capsule_inputs(context)
    except Exception as exc:
        raise ReviewCacheRefusal("AFFECTED_CONE_REVALIDATION_FAILED", str(exc)) from exc
    return context


@dataclass(frozen=True)
class ReviewContextCacheKeyV2:
    responsibility: CacheResponsibility
    repository: str
    base_sha: str
    head_sha: str
    diff_digest: str
    context_digest: str
    currentness_ref: str
    source_generation_ref: str
    codemap_generation_ref: str
    workgraph_generation_ref: str
    coordinate_locator_generation_digest: str
    route_policy_ref: str
    reviewer: str
    reviewer_version: str
    model_signature: str
    tokenizer_identity: str
    system_tool_prefix_digest: str
    context_strategy: str
    principal_id: str
    arena_id: str
    schema: str = CACHE_KEY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CACHE_KEY_SCHEMA:
            raise ReviewCacheRefusal("CACHE_KEY_SCHEMA_MISMATCH")
        object.__setattr__(self, "responsibility", _enum("responsibility", self.responsibility, CacheResponsibility))
        if self.responsibility is not CacheResponsibility.REVIEW_CONTEXT:
            raise ReviewCacheRefusal("CACHE_RESPONSIBILITY_OWNER_MISMATCH", self.responsibility.value)
        for field in (
            "repository", "base_sha", "head_sha", "diff_digest", "context_digest",
            "currentness_ref", "source_generation_ref", "codemap_generation_ref",
            "workgraph_generation_ref", "coordinate_locator_generation_digest",
            "route_policy_ref", "reviewer", "reviewer_version", "model_signature",
            "tokenizer_identity", "system_tool_prefix_digest", "context_strategy",
            "principal_id", "arena_id",
        ):
            object.__setattr__(self, field, _text(field, getattr(self, field)))

    @property
    def key_digest(self) -> str:
        body = asdict(self)
        body["responsibility"] = self.responsibility.value
        return _digest(body)


@dataclass(frozen=True)
class ReviewContextCacheRecordV2:
    key_digest: str
    context_digest: str
    currentness_ref: str
    materialized_context_digest: str
    cache_ref: str
    source_ref: str
    tier: CacheTier
    byte_size: int
    owner_ref: str
    owner_generation: str
    owner_currentness_ref: str
    compiler_version: str
    evidence_set_digest: str
    principal_id: str
    arena_id: str
    payload_receipt_ref: str
    owner_signature_ref: str
    revoked: bool = False
    schema: str = CACHE_RECORD_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CACHE_RECORD_SCHEMA:
            raise ReviewCacheRefusal("CACHE_RECORD_SCHEMA_MISMATCH")
        for field in (
            "key_digest", "context_digest", "currentness_ref", "materialized_context_digest",
            "cache_ref", "source_ref", "owner_ref", "owner_generation",
            "owner_currentness_ref", "compiler_version", "evidence_set_digest",
            "principal_id", "arena_id", "payload_receipt_ref", "owner_signature_ref",
        ):
            object.__setattr__(self, field, _text(field, getattr(self, field)))
        object.__setattr__(self, "tier", _enum("tier", self.tier, CacheTier))
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int) or self.byte_size < 0:
            raise ReviewCacheRefusal("INVALID_BYTE_SIZE")
        _strict_bool("revoked", self.revoked)

    @property
    def record_digest(self) -> str:
        body = asdict(self)
        body["tier"] = self.tier.value
        return _digest(body)


@dataclass(frozen=True)
class ResolvedCacheOwnerExpectationV2:
    owner_ref: str
    owner_generation: str
    owner_currentness_ref: str
    expected_signature_ref: str
    expected_principal_id: str
    expected_arena_id: str
    resolver_ref: str
    resolver_generation: str
    resolver_currentness_ref: str

    def __post_init__(self) -> None:
        for field in asdict(self):
            object.__setattr__(self, field, _text(field, getattr(self, field)))


@dataclass(frozen=True)
class TrustedCacheReadObservationV2:
    key_digest: str
    record_digest: str
    context_digest: str
    materialized_context_digest: str
    cache_ref: str
    read_attempt_id: str
    observer_ref: str
    observer_generation: str
    observer_currentness_ref: str
    observer_signature_ref: str
    source_currentness_ref: str
    cache_read_observed: bool
    execution_authorized: bool = False
    review_pass_proven: bool = False
    promotion_authorized: bool = False
    schema: str = CACHE_USE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CACHE_USE_SCHEMA:
            raise ReviewCacheRefusal("CACHE_READ_SCHEMA_MISMATCH")
        for field in (
            "key_digest", "record_digest", "context_digest", "materialized_context_digest",
            "cache_ref", "read_attempt_id", "observer_ref", "observer_generation",
            "observer_currentness_ref", "observer_signature_ref", "source_currentness_ref",
        ):
            object.__setattr__(self, field, _text(field, getattr(self, field)))
        _strict_bool("cache_read_observed", self.cache_read_observed)
        if self.execution_authorized or self.review_pass_proven or self.promotion_authorized:
            raise ReviewCacheRefusal("CACHE_EVIDENCE_AUTHORITY_WIDENING")

    @property
    def observation_digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class ResolvedReadObserverExpectationV2:
    observer_ref: str
    observer_generation: str
    observer_currentness_ref: str
    expected_signature_ref: str
    resolver_ref: str
    resolver_generation: str
    resolver_currentness_ref: str

    def __post_init__(self) -> None:
        for field in asdict(self):
            object.__setattr__(self, field, _text(field, getattr(self, field)))


@dataclass(frozen=True)
class TrustedQDKTRouterInputV2:
    risk_score: float
    reviewer_availability: tuple[tuple[str, bool], ...]
    issuer_ref: str
    issuer_generation: str
    issuer_currentness_ref: str
    source_currentness_ref: str
    signature_ref: str
    revoked: bool = False
    schema: str = ROUTER_INPUT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != ROUTER_INPUT_SCHEMA:
            raise ReviewCacheRefusal("QDKT_INPUT_SCHEMA_MISMATCH")
        if isinstance(self.risk_score, bool) or not isinstance(self.risk_score, (int, float)) or not 0.0 <= self.risk_score <= 1.0:
            raise ReviewCacheRefusal("INVALID_RISK_SCORE")
        normalized = []
        for row in self.reviewer_availability:
            if not isinstance(row, tuple) or len(row) != 2:
                raise ReviewCacheRefusal("INVALID_REVIEWER_AVAILABILITY")
            reviewer = _text("reviewer", row[0]).upper()
            available = _strict_bool("reviewer_available", row[1])
            normalized.append((reviewer, available))
        object.__setattr__(self, "reviewer_availability", tuple(sorted(set(normalized))))
        for field in (
            "issuer_ref", "issuer_generation", "issuer_currentness_ref",
            "source_currentness_ref", "signature_ref",
        ):
            object.__setattr__(self, field, _text(field, getattr(self, field)))
        _strict_bool("revoked", self.revoked)

    @property
    def input_digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class ResolvedQDKTInputExpectationV2:
    issuer_ref: str
    issuer_generation: str
    issuer_currentness_ref: str
    expected_signature_ref: str
    source_currentness_ref: str
    resolver_ref: str
    resolver_generation: str
    resolver_currentness_ref: str

    def __post_init__(self) -> None:
        for field in asdict(self):
            object.__setattr__(self, field, _text(field, getattr(self, field)))


def compile_cache_key(
    context: Mapping[str, object],
    *,
    responsibility: CacheResponsibility,
    reviewer: str,
    reviewer_version: str,
    model_signature: str,
    tokenizer_identity: str,
    system_tool_prefix_digest: str,
    context_strategy: str,
    principal_id: str,
    arena_id: str,
) -> ReviewContextCacheKeyV2:
    context = _validate_affected_cone(context)
    return ReviewContextCacheKeyV2(
        responsibility=responsibility,
        repository=_text("repository", context.get("repository")),
        base_sha=_text("base_sha", context.get("base_sha")),
        head_sha=_text("head_sha", context.get("head_sha")),
        diff_digest=_text("diff_digest", context.get("diff_digest")),
        context_digest=_text("context_digest", context.get("context_digest")),
        currentness_ref=_text("currentness_ref", context.get("currentness_ref")),
        source_generation_ref=_text("source_generation_ref", context.get("source_generation_ref")),
        codemap_generation_ref=_text("codemap_generation_ref", context.get("codemap_generation_ref")),
        workgraph_generation_ref=_text("workgraph_generation_ref", context.get("workgraph_generation_ref")),
        coordinate_locator_generation_digest=_text(
            "coordinate_locator_generation_digest",
            context.get("coordinate_locator_generation_digest"),
        ),
        route_policy_ref=_text("route_policy_ref", context.get("route_policy_ref")),
        reviewer=reviewer,
        reviewer_version=reviewer_version,
        model_signature=model_signature,
        tokenizer_identity=tokenizer_identity,
        system_tool_prefix_digest=system_tool_prefix_digest,
        context_strategy=context_strategy,
        principal_id=principal_id,
        arena_id=arena_id,
    )


def cache_key_delta(previous: ReviewContextCacheKeyV2, current: ReviewContextCacheKeyV2) -> dict:
    if not isinstance(previous, ReviewContextCacheKeyV2) or not isinstance(current, ReviewContextCacheKeyV2):
        raise ReviewCacheRefusal("INVALID_CACHE_KEY")
    axes: set[GenerationAxis] = set()
    if (
        previous.source_generation_ref != current.source_generation_ref
        or previous.codemap_generation_ref != current.codemap_generation_ref
        or previous.workgraph_generation_ref != current.workgraph_generation_ref
    ):
        axes.add(GenerationAxis.SOURCE)
    if previous.coordinate_locator_generation_digest != current.coordinate_locator_generation_digest:
        axes.add(GenerationAxis.PLACEMENT)
    if (
        previous.repository != current.repository
        or previous.base_sha != current.base_sha
        or previous.head_sha != current.head_sha
        or previous.diff_digest != current.diff_digest
        or previous.currentness_ref != current.currentness_ref
        or previous.route_policy_ref != current.route_policy_ref
        or previous.context_digest != current.context_digest
    ):
        only_context_digest = (
            previous.repository == current.repository
            and previous.base_sha == current.base_sha
            and previous.head_sha == current.head_sha
            and previous.diff_digest == current.diff_digest
            and previous.currentness_ref == current.currentness_ref
            and previous.route_policy_ref == current.route_policy_ref
            and previous.context_digest != current.context_digest
            and GenerationAxis.PLACEMENT in axes
        )
        if not only_context_digest:
            axes.add(GenerationAxis.TARGET)
    if previous.principal_id != current.principal_id or previous.arena_id != current.arena_id:
        axes.add(GenerationAxis.PRINCIPAL_CONTEXT)
    if (
        previous.reviewer != current.reviewer
        or previous.reviewer_version != current.reviewer_version
        or previous.model_signature != current.model_signature
        or previous.tokenizer_identity != current.tokenizer_identity
        or previous.system_tool_prefix_digest != current.system_tool_prefix_digest
        or previous.context_strategy != current.context_strategy
    ):
        axes.add(GenerationAxis.REVIEW_RUNTIME)

    ordered = tuple(sorted(axis.value for axis in axes))
    if not ordered:
        disposition = "REUSE_KEY_EXACT"
    elif axes == {GenerationAxis.PLACEMENT}:
        disposition = "RELOCALIZE_REVIEW_CONTEXT"
    elif GenerationAxis.PRINCIPAL_CONTEXT in axes:
        disposition = "REHYDRATE_NO_CROSS_PRINCIPAL_REUSE"
    else:
        disposition = "REHYDRATE_REVALIDATE"
    return {
        "changed_axes": ordered,
        "disposition": disposition,
        "semantic_source_refetch_required": GenerationAxis.SOURCE in axes,
        "physical_relocalize_required": GenerationAxis.PLACEMENT in axes,
        "review_pass_proven": False,
        "execution_authorized": False,
        "promotion_authorized": False,
    }


def _owner_matches(
    key: ReviewContextCacheKeyV2,
    record: ReviewContextCacheRecordV2,
    expected: ResolvedCacheOwnerExpectationV2,
) -> tuple[bool, str]:
    if record.revoked:
        return False, "CACHE_RECORD_REVOKED"
    if (
        record.owner_ref != expected.owner_ref
        or record.owner_generation != expected.owner_generation
        or record.owner_currentness_ref != expected.owner_currentness_ref
        or record.owner_signature_ref != expected.expected_signature_ref
    ):
        return False, "CACHE_OWNER_TRUST_MISMATCH"
    if record.principal_id != expected.expected_principal_id or record.arena_id != expected.expected_arena_id:
        return False, "CACHE_PRINCIPAL_ARENA_MISMATCH"
    if record.principal_id != key.principal_id or record.arena_id != key.arena_id:
        return False, "CACHE_KEY_PRINCIPAL_ARENA_MISMATCH"
    return True, "CACHE_OWNER_TRUSTED"


def admit_cache_candidate(
    key: ReviewContextCacheKeyV2,
    record: ReviewContextCacheRecordV2 | None,
    *,
    owner_expectation: ResolvedCacheOwnerExpectationV2 | None,
) -> dict:
    if not isinstance(key, ReviewContextCacheKeyV2):
        raise ReviewCacheRefusal("INVALID_CACHE_KEY")
    if record is None:
        return {"disposition": "REHYDRATE", "reason": "CACHE_MISS", "cache_hit_proven": False}
    if not isinstance(record, ReviewContextCacheRecordV2):
        raise ReviewCacheRefusal("INVALID_CACHE_RECORD")
    if owner_expectation is None:
        return {"disposition": "REHYDRATE", "reason": "CACHE_OWNER_TRUST_UNRESOLVED", "cache_hit_proven": False}
    if not isinstance(owner_expectation, ResolvedCacheOwnerExpectationV2):
        raise ReviewCacheRefusal("INVALID_CACHE_OWNER_EXPECTATION")
    if record.key_digest != key.key_digest:
        return {"disposition": "REHYDRATE", "reason": "CACHE_KEY_MISMATCH", "cache_hit_proven": False}
    if record.context_digest != key.context_digest:
        return {"disposition": "REHYDRATE", "reason": "CONTEXT_DIGEST_MISMATCH", "cache_hit_proven": False}
    if record.currentness_ref != key.currentness_ref:
        return {"disposition": "REHYDRATE", "reason": "CACHE_CURRENTNESS_STALE", "cache_hit_proven": False}
    trusted, reason = _owner_matches(key, record, owner_expectation)
    if not trusted:
        return {"disposition": "REHYDRATE", "reason": reason, "cache_hit_proven": False}
    return {
        "disposition": "CACHE_REUSE_ELIGIBLE",
        "reason": "EXACT_TRUSTED_CACHE_RECORD",
        "cache_hit_proven": False,
        "cache_ref": record.cache_ref,
        "record_digest": record.record_digest,
        "materialized_context_digest": record.materialized_context_digest,
    }


def observe_cache_use(
    key: ReviewContextCacheKeyV2,
    record: ReviewContextCacheRecordV2,
    *,
    owner_expectation: ResolvedCacheOwnerExpectationV2,
    read_observation: TrustedCacheReadObservationV2,
    observer_expectation: ResolvedReadObserverExpectationV2,
) -> TrustedCacheReadObservationV2:
    admission = admit_cache_candidate(key, record, owner_expectation=owner_expectation)
    if admission["disposition"] != "CACHE_REUSE_ELIGIBLE":
        raise ReviewCacheRefusal("CACHE_NOT_REUSE_ELIGIBLE", admission["reason"])
    if not isinstance(read_observation, TrustedCacheReadObservationV2):
        raise ReviewCacheRefusal("TRUSTED_CACHE_READ_OBSERVATION_REQUIRED")
    if not isinstance(observer_expectation, ResolvedReadObserverExpectationV2):
        raise ReviewCacheRefusal("READ_OBSERVER_EXPECTATION_REQUIRED")
    if not read_observation.cache_read_observed:
        raise ReviewCacheRefusal("CACHE_READ_NOT_OBSERVED")
    if (
        read_observation.observer_ref != observer_expectation.observer_ref
        or read_observation.observer_generation != observer_expectation.observer_generation
        or read_observation.observer_currentness_ref != observer_expectation.observer_currentness_ref
        or read_observation.observer_signature_ref != observer_expectation.expected_signature_ref
    ):
        raise ReviewCacheRefusal("CACHE_READ_OBSERVER_TRUST_MISMATCH")
    exact = (
        read_observation.key_digest == key.key_digest
        and read_observation.record_digest == record.record_digest
        and read_observation.context_digest == key.context_digest
        and read_observation.materialized_context_digest == record.materialized_context_digest
        and read_observation.cache_ref == record.cache_ref
        and read_observation.source_currentness_ref == key.currentness_ref
    )
    if not exact:
        raise ReviewCacheRefusal("CACHE_READ_BINDING_MISMATCH")
    return read_observation


def _trusted_router_input(
    context: Mapping[str, object],
    router_input: TrustedQDKTRouterInputV2 | None,
    expectation: ResolvedQDKTInputExpectationV2 | None,
) -> bool:
    if router_input is None or expectation is None:
        return False
    if not isinstance(router_input, TrustedQDKTRouterInputV2) or not isinstance(expectation, ResolvedQDKTInputExpectationV2):
        return False
    if router_input.revoked:
        return False
    return (
        router_input.issuer_ref == expectation.issuer_ref
        and router_input.issuer_generation == expectation.issuer_generation
        and router_input.issuer_currentness_ref == expectation.issuer_currentness_ref
        and router_input.signature_ref == expectation.expected_signature_ref
        and router_input.source_currentness_ref == expectation.source_currentness_ref
        and router_input.source_currentness_ref == context.get("currentness_ref")
    )


def compile_qdkt_review_plan(
    context: Mapping[str, object],
    *,
    phase: str,
    deterministic_tools: Sequence[str],
    router_input: TrustedQDKTRouterInputV2 | None = None,
    router_expectation: ResolvedQDKTInputExpectationV2 | None = None,
) -> dict:
    context = _validate_affected_cone(context)
    if phase not in {"PRE_GITHUB", "GITHUB_REVIEW_LANE"}:
        raise ReviewCacheRefusal("UNKNOWN_REVIEW_PHASE")
    required_reviewers = ("CODEX",) if phase == "PRE_GITHUB" else ("CODEX", "CODERABBIT")
    trusted = _trusted_router_input(context, router_input, router_expectation)
    if trusted:
        risk_score = float(router_input.risk_score)
        availability = dict(router_input.reviewer_availability)
    else:
        risk_score = 1.0
        availability = {}
    unavailable = tuple(r for r in required_reviewers if availability.get(r) is not True)

    nodes = context.get("nodes") or ()
    mandatory_paths = sorted(
        _text("node_path", n.get("path"))
        for n in nodes
        if isinstance(n, Mapping) and n.get("required") is True
    )
    if len(mandatory_paths) != int(context.get("required_node_count") or -1):
        raise ReviewCacheRefusal("MANDATORY_CONTEXT_COUNT_MISMATCH")

    if risk_score < 0.25:
        optional_depth = 0
        topology = "W0"
    elif risk_score < 0.65:
        optional_depth = 1
        topology = "W3"
    else:
        optional_depth = 2
        topology = "W5"

    tools = tuple(sorted({_text("deterministic_tool", t) for t in deterministic_tools}))
    body = {
        "schema": PLAN_SCHEMA,
        "context_digest": context["context_digest"],
        "coordinate_locator_generation_digest": context["coordinate_locator_generation_digest"],
        "repository": context["repository"],
        "head_sha": context["head_sha"],
        "currentness_ref": context["currentness_ref"],
        "route_policy_ref": context["route_policy_ref"],
        "phase": phase,
        "risk_score": risk_score,
        "mandatory_paths": mandatory_paths,
        "optional_depth_rank": optional_depth,
        "deterministic_tools": tools,
        "reviewer_sequence": required_reviewers,
        "unavailable_reviewers": unavailable,
        "review_disposition": "REVIEW_INCOMPLETE" if unavailable or not trusted else "REVIEW_ROUTE_READY",
        "topology": topology,
        "router_input_trusted": trusted,
        "availability_proven": trusted,
        "qdkt_is_authority": False,
        "cache_is_truth": False,
        "topology_is_authority": False,
        "review_pass_proven": False,
        "execution_authorized": False,
        "promotion_authorized": False,
    }
    body["plan_digest"] = _digest(body)
    return body
