"""Bounded normalization of CodeRabbit, Codex, and manual PR review evidence."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aura_review_lessons_contracts import (
    _MAX_REVIEW_PAYLOAD_BYTES,
    _MAX_STORED_FINDINGS,
    PATCH_AUTHORITY,
    REVIEW_LESSON_VERSION,
    VSA_PATCH_AUTHORITY,
    NormalizedReviewFinding,
    ReviewLessonError,
    _bounded_json,
    _detector_from_text,
    _digest,
    _disposition,
    _is_sequence,
    _reviewer_name,
    _safe_repo_path,
    _safe_text,
    _strip_markdown,
    _title_from_body,
)


def normalize_external_review(
    payload: Mapping[str, Any],
    *,
    current_head: str = "",
) -> dict[str, Any]:
    """Normalize bounded review evidence without trusting caller freshness."""

    if not isinstance(payload, Mapping):
        raise ReviewLessonError("review payload must be an object")
    _bounded_json(payload, maximum=_MAX_REVIEW_PAYLOAD_BYTES, label="review payload")
    reviewed_head = str(payload.get("head_sha") or payload.get("commit_sha") or "")
    current = current_head or reviewed_head
    pr_number = int(payload.get("pr_number") or payload.get("pull_request_number") or 0)
    raw: list[dict[str, Any]] = []
    rejected_count = 0

    def append_row(value: Mapping[str, Any], *, review_kind: str) -> bool:
        nonlocal rejected_count
        if len(raw) >= _MAX_STORED_FINDINGS:
            return False
        try:
            raw.append(
                _raw_review_row(
                    value,
                    review_kind=review_kind,
                    reviewed_head=reviewed_head,
                    current_head=current,
                    pr_number=pr_number,
                )
            )
        except (ReviewLessonError, TypeError, ValueError, OverflowError):
            rejected_count += 1
        return len(raw) < _MAX_STORED_FINDINGS

    comments = payload.get("comments") or payload.get("issue_comments") or []
    if _is_sequence(comments):
        for comment in comments:
            if isinstance(comment, Mapping):
                if not append_row(comment, review_kind="top_level_pr_comment"):
                    break

    threads = payload.get("review_threads") or payload.get("threads") or []
    if len(raw) < _MAX_STORED_FINDINGS and _is_sequence(threads):
        for thread in threads:
            if len(raw) >= _MAX_STORED_FINDINGS:
                break
            if not isinstance(thread, Mapping):
                continue
            thread_comments = thread.get("comments") or []
            if not _is_sequence(thread_comments):
                continue
            for comment in thread_comments:
                if len(raw) >= _MAX_STORED_FINDINGS:
                    break
                if not isinstance(comment, Mapping):
                    continue
                merged = dict(comment)
                merged.setdefault("path", thread.get("path"))
                merged.setdefault("line", thread.get("line") or thread.get("original_line"))
                merged.setdefault(
                    "start_line",
                    thread.get("start_line") or thread.get("original_start_line"),
                )
                merged["is_resolved"] = thread.get("is_resolved", False)
                merged["is_outdated"] = thread.get("is_outdated", False)
                append_row(merged, review_kind="inline_review_thread")

    reviews = payload.get("reviews") or payload.get("review_submissions") or []
    if len(raw) < _MAX_STORED_FINDINGS and _is_sequence(reviews):
        for review in reviews:
            if isinstance(review, Mapping):
                if not append_row(review, review_kind="review_submission"):
                    break

    findings = payload.get("findings") or []
    if not raw and _is_sequence(findings):
        for finding in findings:
            if isinstance(finding, Mapping):
                if not append_row(
                    finding,
                    review_kind=str(finding.get("review_kind") or "normalized_finding"),
                ):
                    break

    dedupe: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    for row in raw:
        identity = _digest(
            {
                "reviewer": row["reviewer"],
                "path": row["path"],
                "line": [row["line_start"], row["line_end"]],
                "message": row["message"].casefold(),
            },
            size=12,
        )
        duplicate_of = dedupe.get(identity, "")
        if not duplicate_of:
            dedupe[identity] = row["finding_id"]
        row["duplicate_of"] = duplicate_of
        if duplicate_of:
            row["disposition"] = "duplicate"
        normalized.append(row)

    packet = {
        "version": REVIEW_LESSON_VERSION,
        "status": "normalized",
        "repository_head": reviewed_head,
        "current_head": current,
        "pr_number": pr_number,
        "finding_count": len(normalized),
        "rejected_finding_count": rejected_count,
        "finding_limit_reached": len(raw) >= _MAX_STORED_FINDINGS,
        "findings": normalized,
        "truth_boundary": "typed_external_review_evidence",
        "source_grounding_required_before_learning": True,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


def _strict_flag(value: Any, *, field_name: str) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    raise ReviewLessonError(f"{field_name} must be a boolean")


def _raw_review_row(
    value: Mapping[str, Any],
    *,
    review_kind: str,
    reviewed_head: str,
    current_head: str,
    pr_number: int,
) -> dict[str, Any]:
    body = _safe_text(value.get("body") or value.get("message") or value.get("title") or "")
    reviewer = _reviewer_name(value.get("author") or value.get("user") or value.get("source"))
    path = _safe_repo_path(value.get("path") or value.get("file") or "")
    line_start = int(value.get("start_line") or value.get("line_start") or value.get("line") or 0)
    line_end = int(value.get("line_end") or value.get("line") or line_start)
    if line_start < 0 or line_end < line_start:
        raise ReviewLessonError("review line range is invalid")
    resolved = _strict_flag(
        value.get("is_resolved", value.get("resolved")),
        field_name="is_resolved",
    )
    outdated = _strict_flag(
        value.get("is_outdated", value.get("outdated")),
        field_name="is_outdated",
    )
    message = _strip_markdown(body)
    title = _safe_text(value.get("title") or _title_from_body(body), maximum_bytes=1024)
    detector_id = str(value.get("detector_id") or _detector_from_text(f"{title} {message}"))
    invariant = str(value.get("invariant") or "")
    confidence = float(value.get("confidence") or (0.98 if reviewer in {"CodeRabbit", "Codex"} else 0.75))
    provenance = {
        "comment_id": str(value.get("id") or value.get("comment_id") or ""),
        "url": str(value.get("url") or ""),
        "created_at": str(value.get("created_at") or ""),
        "updated_at": str(value.get("updated_at") or ""),
    }
    identity = {
        "reviewer": reviewer,
        "kind": review_kind,
        "head": reviewed_head,
        "path": path,
        "line": [line_start, line_end],
        "message": message,
        "comment_id": provenance["comment_id"],
    }
    finding = NormalizedReviewFinding(
        finding_id="XRF-" + _digest(identity, size=12),
        reviewer=reviewer,
        review_kind=review_kind,
        repository_head=reviewed_head,
        current_head=current_head,
        pr_number=pr_number,
        comment_id=provenance["comment_id"],
        path=path,
        line_start=line_start,
        line_end=line_end,
        title=title,
        message=message,
        severity=str(value.get("severity") or _severity_from_body(body)).lower(),
        category=str(value.get("category") or "correctness").lower(),
        disposition=_disposition(
            reviewed_head=reviewed_head,
            current_head=current_head,
            resolved=resolved,
            outdated=outdated,
        ),
        resolved=resolved,
        outdated=outdated,
        duplicate_of="",
        detector_id=detector_id,
        invariant=invariant,
        source_grounded=_strict_flag(
            value.get("source_grounded"),
            field_name="source_grounded",
        ),
        confidence=max(0.0, min(1.0, confidence)),
        provenance=provenance,
    )
    return finding.to_dict()


def _severity_from_body(body: str) -> str:
    lowered = body.casefold()
    if "p0" in lowered or "critical" in lowered:
        return "critical"
    if "p1" in lowered or "major" in lowered:
        return "high"
    if "p2" in lowered:
        return "medium"
    return "low"

__all__ = ["normalize_external_review"]
