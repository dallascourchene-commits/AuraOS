#!/usr/bin/env python3
"""Exact-head GitHub review-triad admission for AuraOS.

Required planes:
- OpenAI Codex code review
- CodeRabbit code review
- Codacy quality/static analysis

Provider identity is pinned to GitHub-owned actor IDs/logins or GitHub App slugs.
Mutable status names, check names, review bodies, and comment text never establish
provider identity. This module does not merge, approve, mutate, or promote code.
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
from typing import Any, Iterable

VERSION = "AURA_GITHUB_REVIEW_TRIAD_GATE_V1"
CANONICALIZATION = "JSON_SORT_KEYS_COMPACT_UTF8_V1"
REQUIRED_REVIEWERS = ("codex", "coderabbit", "codacy")

# GitHub-owned immutable user IDs paired with their expected bot login. A login
# string alone is never trusted. Codex's GitHub connector actor is 199175422;
# CodeRabbit's repository bot actor observed on this repository is 136622811.
TRUSTED_USER_ACTORS: dict[str, frozenset[tuple[int, str]]] = {
    "codex": frozenset({(199175422, "chatgpt-codex-connector[bot]")}),
    "coderabbit": frozenset({(136622811, "coderabbitai[bot]")}),
    "codacy": frozenset(),
}

# GitHub App slugs are provider-owned identities. Codacy is a private GitHub App
# at github.com/apps/codacy. If an installed provider exposes a different slug,
# the gate MUST remain HOLD until this canonical allowlist is deliberately updated.
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "kind": self.kind,
            "actor": self.actor,
            "label": self.label,
            "state": self.state,
            "head_bound": self.head_bound,
            "source_id": self.source_id,
        }


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


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
    if not isinstance(app, dict):
        return ""
    return _norm(app.get("slug"))


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
    """Accept a full SHA or a provider-style 'Reviewed commit: <prefix>' marker.

    Provider identity is established independently by immutable actor identity.
    A short SHA is only a head-binding coordinate after provider identity is pinned;
    at least seven hexadecimal characters are required.
    """
    if head_sha in body:
        return True
    for match in re.finditer(r"Reviewed commit:\s*`?([0-9a-fA-F]{7,40})`?", body):
        prefix = match.group(1).lower()
        if head_sha.lower().startswith(prefix):
            return True
    return False


def collect_evidence(snapshot: dict[str, Any], head_sha: str) -> tuple[list[Evidence], list[str]]:
    """Collect only trusted-provider evidence bound to the exact current head."""
    evidence: list[Evidence] = []
    notes: list[str] = []

    # Only a CodeRabbit-authored skip marker can suppress CodeRabbit evidence.
    coderabbit_skip = any(
        _trusted_provider_from_user(item.get("user")) == "coderabbit"
        and _is_coderabbit_skip(item.get("body"))
        for item in snapshot.get("issue_comments", [])
        if isinstance(item, dict)
    )

    # Commit status context is mutable and therefore NEVER establishes provider
    # identity. Only its GitHub-owned creator identity may do so.
    for item in snapshot.get("statuses", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_user(item.get("creator"))
        if provider is None:
            continue
        state = _norm(item.get("state"))
        if state not in SUCCESS_STATUS_STATES:
            continue
        if provider == "coderabbit" and coderabbit_skip:
            notes.append("CODERABBIT_STATUS_PRESENT_BUT_DRAFT_SKIP_MARKER_SEEN")
            continue
        evidence.append(
            Evidence(
                provider=provider,
                kind="commit_status",
                actor=_actor_label_from_user(item.get("creator")),
                label=str(item.get("context") or ""),
                state=state,
                head_bound=True,
                source_id=str(item.get("id") or item.get("url") or ""),
            )
        )

    # Check-run name is mutable. Only the GitHub App slug establishes provider.
    for item in snapshot.get("check_runs", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_app(item.get("app"))
        if provider is None:
            continue
        if _norm(item.get("status")) != "completed":
            continue
        conclusion = _norm(item.get("conclusion"))
        if conclusion not in SUCCESS_CHECK_CONCLUSIONS:
            continue
        if provider == "coderabbit" and coderabbit_skip:
            notes.append("CODERABBIT_CHECK_PRESENT_BUT_DRAFT_SKIP_MARKER_SEEN")
            continue
        evidence.append(
            Evidence(
                provider=provider,
                kind="check_run",
                actor=_actor_label_from_app(item.get("app")),
                label=str(item.get("name") or ""),
                state=conclusion,
                head_bound=True,
                source_id=str(item.get("id") or item.get("url") or ""),
            )
        )

    # Review body text never establishes provider identity. The GitHub reviewer
    # actor must be pinned, and the review commit_id must equal the current head.
    for collection_name, kind in (
        ("reviews", "pull_request_review"),
        ("review_comments", "review_comment"),
    ):
        for item in snapshot.get(collection_name, []):
            if not isinstance(item, dict):
                continue
            provider = _trusted_provider_from_user(item.get("user"))
            if provider not in {"codex", "coderabbit"}:
                continue
            if str(item.get("commit_id") or "") != head_sha:
                continue
            state = str(
                item.get("state")
                or (item.get("review") or {}).get("state")
                or "COMMENTED"
            ).upper()
            if state not in REVIEW_STATES:
                continue
            if provider == "coderabbit" and _is_coderabbit_skip(item.get("body")):
                continue
            evidence.append(
                Evidence(
                    provider=provider,
                    kind=kind,
                    actor=_actor_label_from_user(item.get("user")),
                    label=str(item.get("body") or "")[:160],
                    state=state,
                    head_bound=True,
                    source_id=str(item.get("id") or item.get("url") or ""),
                )
            )

    # Provider-authored issue comments may represent a clean review. They count
    # only from a pinned actor and only when they explicitly bind the current head.
    for item in snapshot.get("issue_comments", []):
        if not isinstance(item, dict):
            continue
        provider = _trusted_provider_from_user(item.get("user"))
        if provider not in {"codex", "coderabbit"}:
            continue
        body = str(item.get("body") or "")
        if provider == "coderabbit" and _is_coderabbit_skip(body):
            continue
        if not _comment_binds_head(body, head_sha):
            continue
        evidence.append(
            Evidence(
                provider=provider,
                kind="trusted_provider_issue_comment_with_head_binding",
                actor=_actor_label_from_user(item.get("user")),
                label=body[:160],
                state="COMMENTED",
                head_bound=True,
                source_id=str(item.get("id") or item.get("url") or ""),
            )
        )

    return evidence, notes


def evaluate_review_triad(snapshot: dict[str, Any], expected_head_sha: str) -> dict[str, Any]:
    pr = snapshot.get("pull_request")
    actual_head = ""
    if isinstance(pr, dict):
        head = pr.get("head")
        if isinstance(head, dict):
            actual_head = str(head.get("sha") or "")
        else:
            actual_head = str(pr.get("head_sha") or "")

    exact_head = bool(expected_head_sha) and actual_head == expected_head_sha
    evidence, notes = collect_evidence(snapshot, expected_head_sha)
    by_provider: dict[str, list[dict[str, Any]]] = {name: [] for name in REQUIRED_REVIEWERS}
    for item in evidence:
        by_provider[item.provider].append(item.as_dict())

    reviewer_pass = {name: bool(by_provider[name]) for name in REQUIRED_REVIEWERS}
    admitted = exact_head and all(reviewer_pass.values())
    violations: list[str] = []
    if not exact_head:
        violations.append("PULL_REQUEST_HEAD_SHA_MISMATCH")
    for provider in REQUIRED_REVIEWERS:
        if not reviewer_pass[provider]:
            violations.append(f"MISSING_EXACT_HEAD_{provider.upper()}_EVIDENCE")

    receipt: dict[str, Any] = {
        "version": VERSION,
        "canonicalization_profile": CANONICALIZATION,
        "expected_head_sha": expected_head_sha,
        "actual_pull_request_head_sha": actual_head,
        "exact_head_bound": exact_head,
        "provider_identity_policy": "PINNED_GITHUB_ACTOR_OR_APP_IDENTITY_V1",
        "required_reviewers": list(REQUIRED_REVIEWERS),
        "reviewer_pass": reviewer_pass,
        "evidence": by_provider,
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


def fetch_snapshot(repo: str, pr_number: int, head_sha: str, token: str) -> dict[str, Any]:
    api = f"https://api.github.com/repos/{repo}"
    pull_request = _api_get(f"{api}/pulls/{pr_number}", token)
    combined = _api_get(f"{api}/commits/{head_sha}/status", token)
    check_payload = _api_get(f"{api}/commits/{head_sha}/check-runs?per_page=100", token)
    return {
        "pull_request": pull_request,
        "statuses": combined.get("statuses", []) if isinstance(combined, dict) else [],
        "check_runs": check_payload.get("check_runs", []) if isinstance(check_payload, dict) else [],
        "reviews": _paged(f"{api}/pulls/{pr_number}/reviews", token),
        "review_comments": _paged(f"{api}/pulls/{pr_number}/comments", token),
        "issue_comments": _paged(f"{api}/issues/{pr_number}/comments", token),
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
