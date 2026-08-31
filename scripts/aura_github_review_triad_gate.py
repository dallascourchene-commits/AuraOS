#!/usr/bin/env python3
"""Fail-closed exact-head review triad gate for AuraOS.

Required independent planes:
- OpenAI Codex review
- CodeRabbit review
- Codacy static/code-quality analysis

Identity is accepted only from pinned GitHub-owned immutable identities. Mutable
check names, status contexts, review bodies, display names, and copied bot logins
never establish provider identity. Completion evidence must also be clean: skipped,
queued, unavailable, or unresolved exact-head findings remain HOLD.

This module verifies evidence only. It never grants merge, promotion, execution,
provider-effect, public-effect, or human authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

VERSION = "AURA_GITHUB_REVIEW_TRIAD_GATE_V1"
CANONICALIZATION = "JSON_SORT_KEYS_COMPACT_UTF8_V1"
IDENTITY_POLICY = "PINNED_GITHUB_ACTOR_ID_OR_APP_ID_PLUS_SLUG_V2"
OUTCOME_POLICY = "CLEAN_COMPLETION_AND_NO_UNRESOLVED_EXACT_HEAD_FINDINGS_V1"
REQUIRED_REVIEWERS = ("codex", "coderabbit", "codacy")

# Observed GitHub-owned identities only. Do not guess future provider IDs.
TRUSTED_USER_ACTORS: dict[str, frozenset[tuple[int, str]]] = {
    "codex": frozenset({(199175422, "chatgpt-codex-connector[bot]")}),
    "coderabbit": frozenset({(136622811, "coderabbitai[bot]")}),
    "codacy": frozenset(),
}
TRUSTED_APP_IDENTITIES: dict[str, frozenset[tuple[int, str]]] = {
    "codex": frozenset(),
    "coderabbit": frozenset(),
    # Observed on AuraOS exact-head Codacy check 2026-08-31.
    "codacy": frozenset({(56611, "codacy-production")}),
}

SUCCESS_CHECK_CONCLUSIONS = {"success"}
SUCCESS_STATUS_STATES = {"success"}


@dataclass(frozen=True)
class Evidence:
    provider: str
    kind: str
    actor: str
    label: str
    state: str
    head_bound: bool
    source_id: str
    timestamp: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "kind": self.kind,
            "actor": self.actor,
            "label": self.label,
            "state": self.state,
            "head_bound": self.head_bound,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
        }


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _when(value: Any) -> str:
    text = str(value or "")
    return text or "1970-01-01T00:00:00Z"


def _parse_time(value: Any) -> datetime:
    text = _when(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _user_identity(user: Any) -> tuple[int | None, str]:
    if not isinstance(user, dict):
        return None, ""
    raw_id = user.get("id")
    try:
        user_id = int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        user_id = None
    return user_id, _norm(user.get("login"))


def _app_identity(app: Any) -> tuple[int | None, str]:
    if not isinstance(app, dict):
        return None, ""
    raw_id = app.get("id")
    try:
        app_id = int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        app_id = None
    return app_id, _norm(app.get("slug"))


def _trusted_provider_from_user(user: Any) -> str | None:
    identity = _user_identity(user)
    if identity[0] is None or not identity[1]:
        return None
    for provider, allowed in TRUSTED_USER_ACTORS.items():
        if identity in allowed:
            return provider
    return None


def _trusted_provider_from_app(app: Any) -> str | None:
    identity = _app_identity(app)
    if identity[0] is None or not identity[1]:
        return None
    for provider, allowed in TRUSTED_APP_IDENTITIES.items():
        if identity in allowed:
            return provider
    return None


def _actor_label_from_user(user: Any) -> str:
    user_id, login = _user_identity(user)
    return f"{login}#{user_id}" if login and user_id is not None else login


def _actor_label_from_app(app: Any) -> str:
    app_id, slug = _app_identity(app)
    return f"{slug}#{app_id}" if slug and app_id is not None else slug


def _is_skip_text(value: Any) -> bool:
    text = _norm(value)
    return any(
        marker in text
        for marker in (
            "draft pr not reviewed",
            "skip review by coderabbit.ai",
            "review skipped",
            "manual review required",
        )
    )


def _is_noncompletion_text(value: Any) -> bool:
    text = _norm(value)
    return _is_skip_text(text) or any(
        marker in text
        for marker in (
            "review queued",
            "review running",
            "still running",
            "unavailable",
            "rate limit",
            "rate-limited",
        )
    )


def _comment_binds_head(body: str, head_sha: str) -> bool:
    if head_sha.lower() in body.lower():
        return True
    for match in re.finditer(r"Reviewed commit:\s*`?([0-9a-fA-F]{7,40})`?", body):
        if head_sha.lower().startswith(match.group(1).lower()):
            return True
    return False


def _codex_clean_completion(body: str, head_sha: str) -> bool:
    text = body.lower()
    return (
        _comment_binds_head(body, head_sha)
        and "codex review" in text
        and not _is_noncompletion_text(body)
        and any(
            marker in text
            for marker in (
                "didn't find any major issues",
                "did not find any major issues",
                "no major issues",
                "no blocking issues",
            )
        )
    )


def _latest(records: list[Evidence]) -> datetime:
    if not records:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return max(_parse_time(record.timestamp) for record in records)


def _head_sha(pr: Any) -> str:
    if not isinstance(pr, dict):
        return ""
    head = pr.get("head")
    if isinstance(head, dict):
        return str(head.get("sha") or "")
    return str(pr.get("head_sha") or "")


def collect_evidence(
    snapshot: dict[str, Any], head_sha: str
) -> tuple[list[Evidence], dict[str, list[dict[str, Any]]], list[str]]:
    evidence: list[Evidence] = []
    blockers: dict[str, list[dict[str, Any]]] = {name: [] for name in REQUIRED_REVIEWERS}
    notes: list[str] = []

    rabbit_skips: list[Evidence] = []
    for item in snapshot.get("issue_comments", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_user(item.get("user"))
        body = str(item.get("body") or "")
        if provider == "coderabbit" and _is_skip_text(body):
            rabbit_skips.append(
                Evidence(
                    provider="coderabbit",
                    kind="provider_skip",
                    actor=_actor_label_from_user(item.get("user")),
                    label=body[:160],
                    state="SKIPPED",
                    head_bound=False,
                    source_id=str(item.get("id") or item.get("url") or ""),
                    timestamp=_when(item.get("updated_at") or item.get("created_at")),
                )
            )

    for item in snapshot.get("statuses", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_user(item.get("creator"))
        if provider is None or _norm(item.get("state")) not in SUCCESS_STATUS_STATES:
            continue
        # A provider may encode "skipped" in a successful commit status. Never count it.
        if _is_noncompletion_text(item.get("description")):
            notes.append(f"{provider.upper()}_SUCCESS_STATUS_IS_NONCOMPLETION")
            continue
        evidence.append(
            Evidence(
                provider=provider,
                kind="commit_status",
                actor=_actor_label_from_user(item.get("creator")),
                label=str(item.get("context") or ""),
                state="success",
                head_bound=True,
                source_id=str(item.get("id") or item.get("url") or ""),
                timestamp=_when(item.get("updated_at") or item.get("created_at")),
            )
        )

    for item in snapshot.get("check_runs", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_app(item.get("app"))
        if provider is None:
            continue
        if _norm(item.get("status")) != "completed" or _norm(item.get("conclusion")) not in SUCCESS_CHECK_CONCLUSIONS:
            continue
        output = item.get("output") if isinstance(item.get("output"), dict) else {}
        if _is_noncompletion_text(item.get("name")) or _is_noncompletion_text(output.get("title")) or _is_noncompletion_text(output.get("summary")):
            notes.append(f"{provider.upper()}_SUCCESS_CHECK_IS_NONCOMPLETION")
            continue
        evidence.append(
            Evidence(
                provider=provider,
                kind="check_run",
                actor=_actor_label_from_app(item.get("app")),
                label=str(item.get("name") or ""),
                state="success",
                head_bound=True,
                source_id=str(item.get("id") or item.get("url") or ""),
                timestamp=_when(item.get("completed_at") or item.get("updated_at") or item.get("started_at")),
            )
        )

    for item in snapshot.get("reviews", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_user(item.get("user"))
        if provider not in {"codex", "coderabbit"} or str(item.get("commit_id") or "") != head_sha:
            continue
        state = str(item.get("state") or "COMMENTED").upper()
        record = Evidence(
            provider=provider,
            kind="pull_request_review",
            actor=_actor_label_from_user(item.get("user")),
            label=str(item.get("body") or "")[:160],
            state=state,
            head_bound=True,
            source_id=str(item.get("id") or item.get("url") or ""),
            timestamp=_when(item.get("submitted_at") or item.get("updated_at") or item.get("created_at")),
        )
        if state == "APPROVED":
            evidence.append(record)
        elif state == "CHANGES_REQUESTED":
            blockers[provider].append(record.as_dict())

    # Inline provider comments are unresolved findings on exactly the reviewed commit.
    for item in snapshot.get("review_comments", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_user(item.get("user"))
        if provider not in {"codex", "coderabbit"} or str(item.get("commit_id") or "") != head_sha:
            continue
        blockers[provider].append(
            Evidence(
                provider=provider,
                kind="review_finding",
                actor=_actor_label_from_user(item.get("user")),
                label=str(item.get("body") or "")[:160],
                state="BLOCKING_FINDING",
                head_bound=True,
                source_id=str(item.get("id") or item.get("url") or ""),
                timestamp=_when(item.get("updated_at") or item.get("created_at")),
            ).as_dict()
        )

    # Codex may report a clean review through a provider-authored issue comment.
    for item in snapshot.get("issue_comments", []):
        if not isinstance(item, dict):
            continue
        if _trusted_provider_from_user(item.get("user")) != "codex":
            continue
        body = str(item.get("body") or "")
        if _codex_clean_completion(body, head_sha):
            evidence.append(
                Evidence(
                    provider="codex",
                    kind="clean_provider_summary",
                    actor=_actor_label_from_user(item.get("user")),
                    label=body[:160],
                    state="CLEAN",
                    head_bound=True,
                    source_id=str(item.get("id") or item.get("url") or ""),
                    timestamp=_when(item.get("updated_at") or item.get("created_at")),
                )
            )

    # Historical CodeRabbit skip comments cannot poison future heads forever.
    rabbit_completion = [item for item in evidence if item.provider == "coderabbit"]
    if rabbit_skips and _latest(rabbit_skips) >= _latest(rabbit_completion):
        if rabbit_completion:
            notes.append("CODERABBIT_COMPLETION_PRECEDED_BY_OR_TIED_TO_LATEST_SKIP")
        evidence = [item for item in evidence if item.provider != "coderabbit"]

    return evidence, blockers, notes


def evaluate_review_triad(snapshot: dict[str, Any], expected_head_sha: str) -> dict[str, Any]:
    before = _head_sha(snapshot.get("pull_request"))
    after = _head_sha(snapshot.get("pull_request_after")) or before
    exact_head = bool(expected_head_sha) and before == expected_head_sha and after == expected_head_sha

    evidence, blockers, notes = collect_evidence(snapshot, expected_head_sha)
    by_provider: dict[str, list[dict[str, Any]]] = {name: [] for name in REQUIRED_REVIEWERS}
    for item in evidence:
        by_provider[item.provider].append(item.as_dict())

    reviewer_completed = {name: bool(by_provider[name]) for name in REQUIRED_REVIEWERS}
    reviewer_clear = {name: not bool(blockers[name]) for name in REQUIRED_REVIEWERS}
    reviewer_pass = {
        name: reviewer_completed[name] and reviewer_clear[name]
        for name in REQUIRED_REVIEWERS
    }
    admitted = exact_head and all(reviewer_pass.values())

    violations: list[str] = []
    if not exact_head:
        violations.append("PULL_REQUEST_HEAD_SHA_CHANGED_OR_MISMATCHED")
    for provider in REQUIRED_REVIEWERS:
        if not reviewer_completed[provider]:
            violations.append(f"MISSING_EXACT_HEAD_{provider.upper()}_CLEAN_COMPLETION")
        if blockers[provider]:
            violations.append(f"UNRESOLVED_EXACT_HEAD_{provider.upper()}_FINDINGS")

    receipt: dict[str, Any] = {
        "version": VERSION,
        "canonicalization_profile": CANONICALIZATION,
        "expected_head_sha": expected_head_sha,
        "initial_pull_request_head_sha": before,
        "final_pull_request_head_sha": after,
        "exact_head_bound": exact_head,
        "provider_identity_policy": IDENTITY_POLICY,
        "provider_outcome_policy": OUTCOME_POLICY,
        "required_reviewers": list(REQUIRED_REVIEWERS),
        "reviewer_completed": reviewer_completed,
        "reviewer_clear": reviewer_clear,
        "reviewer_pass": reviewer_pass,
        "evidence": by_provider,
        "blocking_findings": blockers,
        "notes": sorted(set(notes)),
        "violations": violations,
        "review_triad_admitted": admitted,
        "merge_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "provider_effect_authorized": False,
        "public_effect_authorized": False,
        "human_authority": False,
        "semantic_correctness_minted": False,
    }
    receipt["receipt_sha256"] = _sha256(receipt)
    return receipt


def _api_get(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "aura-review-triad-gate-v1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} for {url}: {detail}") from exc


def _paged_list(url: str, token: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    separator = "&" if "?" in url else "?"
    page = 1
    while True:
        payload = _api_get(f"{url}{separator}per_page=100&page={page}", token)
        if not isinstance(payload, list):
            raise RuntimeError(f"Expected list from paged endpoint: {url}")
        rows = [item for item in payload if isinstance(item, dict)]
        out.extend(rows)
        if len(payload) < 100:
            return out
        page += 1


def _paged_check_runs(url: str, token: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    separator = "&" if "?" in url else "?"
    page = 1
    while True:
        payload = _api_get(f"{url}{separator}per_page=100&page={page}", token)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected object from check-runs endpoint: {url}")
        rows = payload.get("check_runs")
        if not isinstance(rows, list):
            raise RuntimeError(f"Expected check_runs list from: {url}")
        out.extend(item for item in rows if isinstance(item, dict))
        if len(rows) < 100:
            return out
        page += 1


def fetch_snapshot(repo: str, pr_number: int, head_sha: str, token: str) -> dict[str, Any]:
    api = f"https://api.github.com/repos/{repo}"
    before = _api_get(f"{api}/pulls/{pr_number}", token)
    statuses = _paged_list(f"{api}/commits/{head_sha}/statuses", token)
    checks = _paged_check_runs(f"{api}/commits/{head_sha}/check-runs", token)
    reviews = _paged_list(f"{api}/pulls/{pr_number}/reviews", token)
    review_comments = _paged_list(f"{api}/pulls/{pr_number}/comments", token)
    issue_comments = _paged_list(f"{api}/issues/{pr_number}/comments", token)
    after = _api_get(f"{api}/pulls/{pr_number}", token)
    return {
        "pull_request": before,
        "pull_request_after": after,
        "statuses": statuses,
        "check_runs": checks,
        "reviews": reviews,
        "review_comments": review_comments,
        "issue_comments": issue_comments,
    }


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--head")
    parser.add_argument("--snapshot-json")
    parser.add_argument("--output", default="aura-review-triad-receipt.json")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = _parse_args(argv)
    if args.snapshot_json:
        with open(args.snapshot_json, encoding="utf-8") as handle:
            snapshot = json.load(handle)
        expected_head = args.head or str(snapshot.get("expected_head_sha") or "")
    else:
        repo = args.repo or os.environ.get("GITHUB_REPOSITORY", "")
        pr_number = args.pr or int(os.environ.get("AURA_PR_NUMBER", "0") or 0)
        expected_head = args.head or os.environ.get("AURA_REVIEW_HEAD_SHA", "")
        token = os.environ.get("GITHUB_TOKEN", "")
        if not repo or not pr_number or not expected_head or not token:
            raise SystemExit("repo, PR number, exact head SHA, and GITHUB_TOKEN are required")
        snapshot = fetch_snapshot(repo, pr_number, expected_head, token)

    receipt = evaluate_review_triad(snapshot, expected_head)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["review_triad_admitted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
