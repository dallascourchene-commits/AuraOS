#!/usr/bin/env python3
"""Exact-head GitHub review-triad admission for AuraOS.

Required planes:
- OpenAI Codex code review
- CodeRabbit code review
- Codacy quality/static analysis

Provider identity is pinned to GitHub-owned actor IDs/logins or GitHub App slugs.
Mutable status names, check names, review bodies, and comment text never establish
provider identity. A review is not a pass merely because it happened: exact-head
provider findings remain blocking until a later clean completion exists on the same
head. This module does not merge, approve, mutate, or promote code.
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
REQUIRED_REVIEWERS = ("codex", "coderabbit", "codacy")

TRUSTED_USER_ACTORS: dict[str, frozenset[tuple[int, str]]] = {
    "codex": frozenset({(199175422, "chatgpt-codex-connector[bot]")}),
    "coderabbit": frozenset({(136622811, "coderabbitai[bot]")}),
    "codacy": frozenset(),
}
TRUSTED_APP_SLUGS: dict[str, frozenset[str]] = {
    "codex": frozenset({"chatgpt-codex-connector"}),
    "coderabbit": frozenset({"coderabbitai"}),
    "codacy": frozenset({"codacy"}),
}
SUCCESS_CHECK_CONCLUSIONS = {"success"}
SUCCESS_STATUS_STATES = {"success"}
REVIEW_STATES = {"APPROVED", "COMMENTED", "CHANGES_REQUESTED"}


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
    if text:
        return text
    return "1970-01-01T00:00:00Z"


def _parse_time(value: Any) -> datetime:
    text = _when(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _user_identity(user: Any) -> tuple[int | None, str]:
    if not isinstance(user, dict):
        return None, ""
    raw_id = user.get("id")
    try:
        user_id = int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        user_id = None
    return user_id, _norm(user.get("login"))


def _app_slug(app: Any) -> str:
    return _norm(app.get("slug")) if isinstance(app, dict) else ""


def _trusted_provider_from_user(user: Any) -> str | None:
    identity = _user_identity(user)
    if identity[0] is None or not identity[1]:
        return None
    for provider, allowed in TRUSTED_USER_ACTORS.items():
        if identity in allowed:
            return provider
    return None


def _trusted_provider_from_app(app: Any) -> str | None:
    slug = _app_slug(app)
    if not slug:
        return None
    for provider, allowed in TRUSTED_APP_SLUGS.items():
        if slug in allowed:
            return provider
    return None


def _actor_label_from_user(user: Any) -> str:
    user_id, login = _user_identity(user)
    return f"{login}#{user_id}" if login and user_id is not None else login


def _actor_label_from_app(app: Any) -> str:
    return _app_slug(app)


def _is_coderabbit_skip(body: Any) -> bool:
    text = _norm(body)
    return (
        "draft pr not reviewed" in text
        or "skip review by coderabbit.ai" in text
        or ("review skipped" in text and "coderabbit" in text)
    )


def _comment_binds_head(body: str, head_sha: str) -> bool:
    if head_sha in body:
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
        and (
            "didn't find any major issues" in text
            or "did not find any major issues" in text
            or "no major issues" in text
        )
    )


def _latest(items: list[Evidence]) -> datetime:
    if not items:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return max(_parse_time(item.timestamp) for item in items)


def collect_evidence(
    snapshot: dict[str, Any], head_sha: str
) -> tuple[list[Evidence], dict[str, list[dict[str, Any]]], list[str]]:
    """Collect trusted exact-head completion evidence and blocking findings."""
    evidence: list[Evidence] = []
    blockers: dict[str, list[dict[str, Any]]] = {name: [] for name in REQUIRED_REVIEWERS}
    notes: list[str] = []

    coderabbit_skips: list[Evidence] = []
    for item in snapshot.get("issue_comments", []):
        if not isinstance(item, dict):
            continue
        if _trusted_provider_from_user(item.get("user")) == "coderabbit" and _is_coderabbit_skip(item.get("body")):
            coderabbit_skips.append(
                Evidence(
                    provider="coderabbit",
                    kind="provider_skip",
                    actor=_actor_label_from_user(item.get("user")),
                    label=str(item.get("body") or "")[:160],
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
        evidence.append(
            Evidence(
                provider=provider,
                kind="commit_status",
                actor=_actor_label_from_user(item.get("creator")),
                label=str(item.get("context") or ""),
                state=_norm(item.get("state")),
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
        evidence.append(
            Evidence(
                provider=provider,
                kind="check_run",
                actor=_actor_label_from_app(item.get("app")),
                label=str(item.get("name") or ""),
                state=_norm(item.get("conclusion")),
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

    # Inline provider comments are actionable findings, not completion evidence.
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

    # A clean Codex issue comment is an explicit completion signal. Other exact-SHA
    # mentions (queued, unavailable, running) are never completion evidence.
    for item in snapshot.get("issue_comments", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_user(item.get("user"))
        if provider not in {"codex", "coderabbit"}:
            continue
        body = str(item.get("body") or "")
        if provider == "codex" and _codex_clean_completion(body, head_sha):
            evidence.append(
                Evidence(
                    provider=provider,
                    kind="clean_provider_summary",
                    actor=_actor_label_from_user(item.get("user")),
                    label=body[:160],
                    state="CLEAN",
                    head_bound=True,
                    source_id=str(item.get("id") or item.get("url") or ""),
                    timestamp=_when(item.get("updated_at") or item.get("created_at")),
                )
            )

    # A historical CodeRabbit skip must not poison later heads forever. Suppress
    # CodeRabbit completion only if the latest trusted skip is newer than or equal
    # to the latest current-head CodeRabbit completion evidence.
    rabbit_completion = [item for item in evidence if item.provider == "coderabbit"]
    if coderabbit_skips and _latest(coderabbit_skips) >= _latest(rabbit_completion):
        if rabbit_completion:
            notes.append("CODERABBIT_COMPLETION_PRECEDED_BY_OR_TIED_TO_LATEST_SKIP")
        evidence = [item for item in evidence if item.provider != "coderabbit"]

    return evidence, blockers, notes


def evaluate_review_triad(snapshot: dict[str, Any], expected_head_sha: str) -> dict[str, Any]:
    def head_sha(key: str) -> str:
        pr = snapshot.get(key)
        if not isinstance(pr, dict):
            return ""
        head = pr.get("head")
        if isinstance(head, dict):
            return str(head.get("sha") or "")
        return str(pr.get("head_sha") or "")

    before = head_sha("pull_request")
    after = head_sha("pull_request_after") or before
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
            violations.append(f"MISSING_EXACT_HEAD_{provider.upper()}_COMPLETION")
        if blockers[provider]:
            violations.append(f"UNRESOLVED_EXACT_HEAD_{provider.upper()}_FINDINGS")

    receipt: dict[str, Any] = {
        "version": VERSION,
        "canonicalization_profile": CANONICALIZATION,
        "expected_head_sha": expected_head_sha,
        "initial_pull_request_head_sha": before,
        "final_pull_request_head_sha": after,
        "exact_head_bound": exact_head,
        "provider_identity_policy": "PINNED_GITHUB_ACTOR_OR_APP_IDENTITY_V1",
        "provider_outcome_policy": "COMPLETED_AND_NO_UNRESOLVED_EXACT_HEAD_FINDINGS_V1",
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


def _api_get(url: str, token: str, accept: str = "application/vnd.github+json") -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
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


def _paged(url: str, token: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    separator = "&" if "?" in url else "?"
    page = 1
    while True:
        payload = _api_get(f"{url}{separator}per_page=100&page={page}", token)
        if not isinstance(payload, list):
            raise RuntimeError(f"Expected list from paged GitHub endpoint: {url}")
        out.extend(item for item in payload if isinstance(item, dict))
        if len(payload) < 100:
            return out
        page += 1


def _paged_keyed(url: str, token: str, key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    separator = "&" if "?" in url else "?"
    page = 1
    while True:
        payload = _api_get(f"{url}{separator}per_page=100&page={page}", token)
        if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
            raise RuntimeError(f"Expected keyed list {key!r} from GitHub endpoint: {url}")
        batch = [item for item in payload[key] if isinstance(item, dict)]
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


def fetch_snapshot(repo: str, pr_number: int, head_sha: str, token: str) -> dict[str, Any]:
    api = f"https://api.github.com/repos/{repo}"
    pull_request = _api_get(f"{api}/pulls/{pr_number}", token)
    statuses = _paged(f"{api}/commits/{head_sha}/statuses", token)
    check_runs = _paged_keyed(f"{api}/commits/{head_sha}/check-runs", token, "check_runs")
    reviews = _paged(f"{api}/pulls/{pr_number}/reviews", token)
    review_comments = _paged(f"{api}/pulls/{pr_number}/comments", token)
    issue_comments = _paged(f"{api}/issues/{pr_number}/comments", token)
    pull_request_after = _api_get(f"{api}/pulls/{pr_number}", token)
    return {
        "pull_request": pull_request,
        "pull_request_after": pull_request_after,
        "statuses": statuses,
        "check_runs": check_runs,
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
        snapshot = json.loads(open(args.snapshot_json, encoding="utf-8").read())
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
