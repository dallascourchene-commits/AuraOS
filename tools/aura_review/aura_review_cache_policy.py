from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping, Sequence

AFFECTED_CONE_SCHEMA = "AffectedConeContextV1"
PLAN_SCHEMA = "QDKTReviewPlanV1"
CACHE_KEY_SCHEMA = "ReviewContextCacheKeyV1"
CACHE_RECORD_SCHEMA = "ReviewContextCacheRecordV1"
CACHE_USE_SCHEMA = "ReviewCacheUseEvidenceV1"


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


@dataclass(frozen=True)
class ReviewContextCacheKeyV1:
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
    route_policy_ref: str
    reviewer: str
    reviewer_version: str
    model_signature: str
    tokenizer_identity: str
    system_tool_prefix_digest: str
    context_strategy: str
    principal_id: str
    arena_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "responsibility", _enum("responsibility", self.responsibility, CacheResponsibility))
        for field in (
            "repository", "base_sha", "head_sha", "diff_digest", "context_digest",
            "currentness_ref", "source_generation_ref", "codemap_generation_ref",
            "workgraph_generation_ref", "route_policy_ref", "reviewer", "reviewer_version",
            "model_signature", "tokenizer_identity", "system_tool_prefix_digest",
            "context_strategy", "principal_id", "arena_id",
        ):
            object.__setattr__(self, field, _text(field, getattr(self, field)))

    @property
    def key_digest(self) -> str:
        body = asdict(self)
        body["responsibility"] = self.responsibility.value
        return _digest(body)


@dataclass(frozen=True)
class ReviewContextCacheRecordV1:
    key_digest: str
    responsibility: CacheResponsibility
    context_digest: str
    currentness_ref: str
    materialized_context_digest: str
    cache_ref: str
    source_ref: str
    tier: CacheTier
    byte_size: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "key_digest", _text("key_digest", self.key_digest))
        object.__setattr__(self, "responsibility", _enum("responsibility", self.responsibility, CacheResponsibility))
        object.__setattr__(self, "context_digest", _text("context_digest", self.context_digest))
        object.__setattr__(self, "currentness_ref", _text("currentness_ref", self.currentness_ref))
        object.__setattr__(self, "materialized_context_digest", _text("materialized_context_digest", self.materialized_context_digest))
        object.__setattr__(self, "cache_ref", _text("cache_ref", self.cache_ref))
        object.__setattr__(self, "source_ref", _text("source_ref", self.source_ref))
        object.__setattr__(self, "tier", _enum("tier", self.tier, CacheTier))
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int) or self.byte_size < 0:
            raise ReviewCacheRefusal("INVALID_BYTE_SIZE")

    @property
    def record_digest(self) -> str:
        body = asdict(self)
        body["responsibility"] = self.responsibility.value
        body["tier"] = self.tier.value
        return _digest(body)


@dataclass(frozen=True)
class ReviewCacheUseEvidenceV1:
    key_digest: str
    record_digest: str
    context_digest: str
    read_attempt_id: str
    observer_ref: str
    observed_materialized_digest: str
    cache_read_observed: bool
    source_currentness_ref: str
    execution_authorized: bool = False
    review_pass_proven: bool = False

    def __post_init__(self) -> None:
        for field in (
            "key_digest", "record_digest", "context_digest", "read_attempt_id",
            "observer_ref", "observed_materialized_digest", "source_currentness_ref",
        ):
            object.__setattr__(self, field, _text(field, getattr(self, field)))
        if not isinstance(self.cache_read_observed, bool):
            raise ReviewCacheRefusal("INVALID_CACHE_READ_OBSERVED")
        if self.execution_authorized or self.review_pass_proven:
            raise ReviewCacheRefusal("CACHE_EVIDENCE_AUTHORITY_WIDENING")


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
) -> ReviewContextCacheKeyV1:
    if context.get("schema") != AFFECTED_CONE_SCHEMA or not context.get("context_digest"):
        raise ReviewCacheRefusal("INVALID_AFFECTED_CONE_CONTEXT")
    return ReviewContextCacheKeyV1(
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


def admit_cache_candidate(key: ReviewContextCacheKeyV1, record: ReviewContextCacheRecordV1 | None) -> dict:
    if not isinstance(key, ReviewContextCacheKeyV1):
        raise ReviewCacheRefusal("INVALID_CACHE_KEY")
    if record is None:
        return {"disposition": "REHYDRATE", "reason": "CACHE_MISS", "cache_hit_proven": False}
    if not isinstance(record, ReviewContextCacheRecordV1):
        raise ReviewCacheRefusal("INVALID_CACHE_RECORD")
    if record.responsibility is not key.responsibility:
        return {"disposition": "REHYDRATE", "reason": "RESPONSIBILITY_MISMATCH", "cache_hit_proven": False}
    if record.key_digest != key.key_digest:
        return {"disposition": "REHYDRATE", "reason": "CACHE_KEY_MISMATCH", "cache_hit_proven": False}
    if record.context_digest != key.context_digest or record.materialized_context_digest != key.context_digest:
        return {"disposition": "REHYDRATE", "reason": "CONTEXT_DIGEST_MISMATCH", "cache_hit_proven": False}
    if record.currentness_ref != key.currentness_ref:
        return {"disposition": "REHYDRATE", "reason": "CACHE_CURRENTNESS_STALE", "cache_hit_proven": False}
    return {
        "disposition": "CACHE_REUSE_ELIGIBLE",
        "reason": "EXACT_CACHE_RECORD",
        "cache_hit_proven": False,
        "cache_ref": record.cache_ref,
        "record_digest": record.record_digest,
    }


def observe_cache_use(
    key: ReviewContextCacheKeyV1,
    record: ReviewContextCacheRecordV1,
    *,
    read_attempt_id: str,
    observer_ref: str,
    observed_materialized_digest: str,
    cache_read_observed: bool,
    source_currentness_ref: str,
) -> ReviewCacheUseEvidenceV1:
    admission = admit_cache_candidate(key, record)
    if admission["disposition"] != "CACHE_REUSE_ELIGIBLE":
        raise ReviewCacheRefusal("CACHE_NOT_REUSE_ELIGIBLE", admission["reason"])
    if not cache_read_observed:
        raise ReviewCacheRefusal("CACHE_READ_NOT_OBSERVED")
    if _text("observed_materialized_digest", observed_materialized_digest) != key.context_digest:
        raise ReviewCacheRefusal("OBSERVED_CACHE_CONTENT_MISMATCH")
    if _text("source_currentness_ref", source_currentness_ref) != key.currentness_ref:
        raise ReviewCacheRefusal("OBSERVED_CACHE_CURRENTNESS_STALE")
    return ReviewCacheUseEvidenceV1(
        key_digest=key.key_digest,
        record_digest=record.record_digest,
        context_digest=key.context_digest,
        read_attempt_id=read_attempt_id,
        observer_ref=observer_ref,
        observed_materialized_digest=observed_materialized_digest,
        cache_read_observed=True,
        source_currentness_ref=source_currentness_ref,
    )


def compile_qdkt_review_plan(
    context: Mapping[str, object],
    *,
    phase: str,
    risk_score: float,
    deterministic_tools: Sequence[str],
    reviewer_availability: Mapping[str, bool],
) -> dict:
    if context.get("schema") != AFFECTED_CONE_SCHEMA or not context.get("context_digest"):
        raise ReviewCacheRefusal("INVALID_AFFECTED_CONE_CONTEXT")
    if isinstance(risk_score, bool) or not isinstance(risk_score, (int, float)) or not 0.0 <= risk_score <= 1.0:
        raise ReviewCacheRefusal("INVALID_RISK_SCORE")
    if phase not in {"PRE_GITHUB", "GITHUB_REVIEW_LANE"}:
        raise ReviewCacheRefusal("UNKNOWN_REVIEW_PHASE")
    required_reviewers = ("CODEX",) if phase == "PRE_GITHUB" else ("CODEX", "CODERABBIT")
    unavailable = tuple(r for r in required_reviewers if reviewer_availability.get(r) is not True)

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
        "repository": context["repository"],
        "head_sha": context["head_sha"],
        "currentness_ref": context["currentness_ref"],
        "route_policy_ref": context["route_policy_ref"],
        "phase": phase,
        "risk_score": float(risk_score),
        "mandatory_paths": mandatory_paths,
        "optional_depth_rank": optional_depth,
        "deterministic_tools": tools,
        "reviewer_sequence": required_reviewers,
        "unavailable_reviewers": unavailable,
        "review_disposition": "REVIEW_INCOMPLETE" if unavailable else "REVIEW_ROUTE_READY",
        "topology": topology,
        "qdkt_is_authority": False,
        "cache_is_truth": False,
        "topology_is_authority": False,
        "execution_authorized": False,
        "promotion_authorized": False,
    }
    body["plan_digest"] = _digest(body)
    return body
