from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "ReviewContextInvocationBindingV1"
EXPECTATION_SCHEMA = "CurrentReviewContextExpectationV1"
SUPPORTED_CONTEXT_SCHEMAS = {"AffectedConeContextV1", "AffectedConeContextV2"}
REVIEWERS = {"CODEX", "CODERABBIT"}


class ReviewContextBindingRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewContextBindingRefusal(code)
    return value.strip()


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReviewContextBindingRefusal("NONCANONICAL_REVIEW_CONTEXT") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _recomputed_context_digest(context: Mapping[str, Any]) -> str:
    if not isinstance(context, Mapping):
        raise ReviewContextBindingRefusal("AFFECTED_CONE_MAPPING_REQUIRED")
    schema = context.get("schema")
    if schema not in SUPPORTED_CONTEXT_SCHEMAS:
        raise ReviewContextBindingRefusal("AFFECTED_CONE_SCHEMA_UNSUPPORTED")
    claimed = _text(context.get("context_digest"), "AFFECTED_CONE_DIGEST_REQUIRED")
    body = dict(context)
    body.pop("context_digest", None)
    actual = hashlib.sha256(_canonical(body)).hexdigest()
    if claimed != actual:
        raise ReviewContextBindingRefusal("AFFECTED_CONE_DIGEST_MISMATCH")
    if schema == "AffectedConeContextV2":
        mode = _text(context.get("mode"), "AFFECTED_CONE_V2_MODE_REQUIRED")
        if mode != "PRODUCTION":
            raise ReviewContextBindingRefusal("NONPRODUCTION_AFFECTED_CONE_REFUSED")
    return actual


@dataclass(frozen=True)
class CurrentReviewContextExpectationV1:
    issuer_ref: str
    issuer_generation: str
    repository: str
    base_sha: str
    head_sha: str
    diff_digest: str
    currentness_ref: str
    source_generation_ref: str
    codemap_generation_ref: str
    workgraph_generation_ref: str
    route_policy_ref: str
    context_digest: str
    schema: str = EXPECTATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != EXPECTATION_SCHEMA:
            raise ReviewContextBindingRefusal("EXPECTATION_SCHEMA_MISMATCH")
        for field in (
            "issuer_ref", "issuer_generation", "repository", "base_sha", "head_sha",
            "diff_digest", "currentness_ref", "source_generation_ref",
            "codemap_generation_ref", "workgraph_generation_ref", "route_policy_ref",
            "context_digest",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), f"{field.upper()}_INVALID"))

    @property
    def expectation_digest(self) -> str:
        return _digest("CURRENT_REVIEW_CONTEXT_EXPECTATION_V1", asdict(self))


@dataclass(frozen=True)
class ReviewContextInvocationBindingV1:
    reviewer: str
    adapter_ref: str
    adapter_version: str
    attempt_id: str
    review_capsule_digest: str
    affected_cone_schema: str
    affected_cone_digest: str
    expectation_digest: str
    expectation_issuer_ref: str
    expectation_issuer_generation: str
    repository: str
    base_sha: str
    head_sha: str
    diff_digest: str
    currentness_ref: str
    source_generation_ref: str
    codemap_generation_ref: str
    workgraph_generation_ref: str
    route_policy_ref: str
    invocation_binding_digest: str
    schema: str = SCHEMA
    reviewer_executed: bool = False
    review_pass_proven: bool = False
    github_mutation_authorized: bool = False
    execution_authorized: bool = False
    promotion_authorized: bool = False


_CONTEXT_FIELDS = (
    "repository", "base_sha", "head_sha", "diff_digest", "currentness_ref",
    "source_generation_ref", "codemap_generation_ref", "workgraph_generation_ref",
    "route_policy_ref",
)


def bind_current_context_to_review_invocation(
    *,
    context: Mapping[str, Any],
    expectation: CurrentReviewContextExpectationV1,
    reviewer: str,
    adapter_ref: str,
    adapter_version: str,
    attempt_id: str,
    review_capsule_digest: str,
) -> ReviewContextInvocationBindingV1:
    if not isinstance(expectation, CurrentReviewContextExpectationV1):
        raise ReviewContextBindingRefusal("CURRENT_CONTEXT_EXPECTATION_REQUIRED")
    context_digest = _recomputed_context_digest(context)

    for field in _CONTEXT_FIELDS:
        context_value = _text(context.get(field), f"AFFECTED_CONE_{field.upper()}_REQUIRED")
        if context_value != getattr(expectation, field):
            raise ReviewContextBindingRefusal(f"AFFECTED_CONE_{field.upper()}_STALE")

    if context_digest != expectation.context_digest:
        raise ReviewContextBindingRefusal("AFFECTED_CONE_EXPECTATION_DIGEST_MISMATCH")

    reviewer_clean = _text(reviewer, "REVIEWER_REQUIRED").upper()
    if reviewer_clean not in REVIEWERS:
        raise ReviewContextBindingRefusal("REVIEWER_UNSUPPORTED")
    adapter_ref = _text(adapter_ref, "ADAPTER_REF_REQUIRED")
    adapter_version = _text(adapter_version, "ADAPTER_VERSION_REQUIRED")
    attempt_id = _text(attempt_id, "ATTEMPT_ID_REQUIRED")
    review_capsule_digest = _text(review_capsule_digest, "REVIEW_CAPSULE_DIGEST_REQUIRED")

    logical = {
        "schema": SCHEMA,
        "reviewer": reviewer_clean,
        "adapter_ref": adapter_ref,
        "adapter_version": adapter_version,
        "attempt_id": attempt_id,
        "review_capsule_digest": review_capsule_digest,
        "affected_cone_schema": context["schema"],
        "affected_cone_digest": context_digest,
        "expectation_digest": expectation.expectation_digest,
        "expectation_issuer_ref": expectation.issuer_ref,
        "expectation_issuer_generation": expectation.issuer_generation,
        **{field: getattr(expectation, field) for field in _CONTEXT_FIELDS},
    }
    binding_digest = _digest("REVIEW_CONTEXT_INVOCATION_BINDING_V1", logical)
    return ReviewContextInvocationBindingV1(
        **logical,
        invocation_binding_digest=binding_digest,
    )


def revalidate_invocation_binding(
    *,
    binding: ReviewContextInvocationBindingV1,
    context: Mapping[str, Any],
    expectation: CurrentReviewContextExpectationV1,
) -> None:
    if not isinstance(binding, ReviewContextInvocationBindingV1):
        raise ReviewContextBindingRefusal("REVIEW_CONTEXT_BINDING_REQUIRED")
    expected = bind_current_context_to_review_invocation(
        context=context,
        expectation=expectation,
        reviewer=binding.reviewer,
        adapter_ref=binding.adapter_ref,
        adapter_version=binding.adapter_version,
        attempt_id=binding.attempt_id,
        review_capsule_digest=binding.review_capsule_digest,
    )
    if expected.invocation_binding_digest != binding.invocation_binding_digest:
        raise ReviewContextBindingRefusal("REVIEW_CONTEXT_BINDING_STALE")
    if expected.affected_cone_digest != binding.affected_cone_digest:
        raise ReviewContextBindingRefusal("AFFECTED_CONE_CHANGED_AFTER_BINDING")
