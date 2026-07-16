"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xab11-[Q-SYS:ARENA_RESEARCH_BRIDGE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Exact metadata, bounded external evidence)
DEPENDENCIES: __future__, asyncio, hashlib, json, re, urllib, xml.etree.ElementTree,
              arxiv_forager
FUNCTIONS: ArenaResearchBridge, search_arxiv, search_github_repositories,
           fetch_arxiv_sidecar, fetch_github_readme_sidecar
SYNOPSIS: Bounded public research adapters for the Human Agent Arena. arXiv API metadata
and GitHub API repository metadata remain canonical for identity fields; PDF text and README
content are explicitly untrusted sidecars. External evidence never grants patch authority.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import quote, urlencode
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from arxiv_forager import ArXivForager


RESEARCH_BRIDGE_VERSION = "AURA_ARENA_RESEARCH_BRIDGE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ARXIV_METADATA_TRUTH = "ARXIV_API_CANONICAL_METADATA"
GITHUB_METADATA_TRUTH = "GITHUB_API_CANONICAL_REPOSITORY_METADATA"
SIDECAR_TRUTH = "UNTRUSTED_EXTERNAL_SIDECAR_REQUIRES_VERIFICATION"
MAX_QUERY_CHARS = 500
MAX_RESULTS = 20
MAX_SIDECAR_CHARS = 120_000
DEFAULT_TIMEOUT = 20.0
_GITHUB_API = "https://api.github.com"
_USER_AGENT = "AuraOS-Human-Agent-Arena/1.0"


class ArenaResearchBridge:
    """Search official public research/repository APIs under bounded contracts."""

    def __init__(self, repo_root: str = ".") -> None:
        self.repo_root = str(repo_root)

    def search(
        self,
        provider: str,
        query: str,
        *,
        limit: int = 8,
        include_sidecars: bool = False,
        sidecar_limit: int = 2,
    ) -> dict[str, Any]:
        provider_key = str(provider or "").strip().lower()
        clean_query = _clean_query(query)
        bounded_limit = max(1, min(int(limit), MAX_RESULTS))
        bounded_sidecars = max(0, min(int(sidecar_limit), 3, bounded_limit))
        if provider_key == "arxiv":
            return self.search_arxiv(
                clean_query,
                limit=bounded_limit,
                include_sidecars=include_sidecars,
                sidecar_limit=bounded_sidecars,
            )
        if provider_key == "github":
            return self.search_github_repositories(
                clean_query,
                limit=bounded_limit,
                include_sidecars=include_sidecars,
                sidecar_limit=bounded_sidecars,
            )
        return _error("unsupported_provider", provider=provider_key)

    def search_arxiv(
        self,
        query: str,
        *,
        limit: int = 8,
        include_sidecars: bool = False,
        sidecar_limit: int = 2,
    ) -> dict[str, Any]:
        clean_query = _clean_query(query)
        bounded_limit = max(1, min(int(limit), MAX_RESULTS))
        forager = ArXivForager()
        try:
            xml_data, page_size = asyncio.run(
                forager._fetch_arxiv_xml(  # noqa: SLF001 - reuse Aura's paced official API adapter
                    f"all:{clean_query}",
                    max_results=bounded_limit,
                    sort_by="relevance",
                    max_retries=2,
                    timeout=DEFAULT_TIMEOUT,
                )
            )
            results = _parse_arxiv_atom(xml_data)[:bounded_limit]
            if include_sidecars:
                for result in results[: max(0, min(sidecar_limit, 3))]:
                    sidecar = self.fetch_arxiv_sidecar(str(result.get("versioned_id") or result.get("arxiv_id") or ""))
                    if sidecar.get("ok"):
                        result["sidecar"] = sidecar["sidecar"]
            return {
                "ok": True,
                "version": RESEARCH_BRIDGE_VERSION,
                "provider": "arxiv",
                "query": clean_query,
                "count": len(results),
                "requested_page_size": page_size,
                "results": results,
                "metadata_truth": ARXIV_METADATA_TRUTH,
                "sidecar_truth": SIDECAR_TRUTH,
                "external_evidence_is_patch_authority": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:  # noqa: BLE001
            return _error(f"arxiv_search_failed:{type(exc).__name__}:{exc}", provider="arxiv", query=clean_query)

    def fetch_arxiv_sidecar(self, arxiv_id: str) -> dict[str, Any]:
        normalized = _normalize_arxiv_id(arxiv_id)
        if not normalized:
            return _error("invalid_arxiv_id", provider="arxiv")
        forager = ArXivForager()
        pdf_url = f"https://arxiv.org/pdf/{normalized}"
        try:
            text = asyncio.run(
                forager._fetch_pdf_text(  # noqa: SLF001 - existing bounded Aura PDF sidecar
                    pdf_url,
                    timeout=35.0,
                )
            )
            full_text = str(text or "")
            clipped = full_text[:MAX_SIDECAR_CHARS]
            return {
                "ok": bool(clipped),
                "sidecar": {
                    "kind": "arxiv_pdf_text",
                    "arxiv_id": normalized,
                    "pdf_url": pdf_url,
                    "text": clipped,
                    "truncated": len(full_text) > len(clipped),
                    "text_sha256": hashlib.sha256(clipped.encode("utf-8")).hexdigest(),
                    "truth_class": SIDECAR_TRUTH,
                },
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:  # noqa: BLE001
            return _error(f"arxiv_sidecar_failed:{type(exc).__name__}:{exc}", provider="arxiv")

    def search_github_repositories(
        self,
        query: str,
        *,
        limit: int = 8,
        include_sidecars: bool = False,
        sidecar_limit: int = 2,
    ) -> dict[str, Any]:
        clean_query = _clean_query(query)
        bounded_limit = max(1, min(int(limit), MAX_RESULTS))
        params = urlencode({"q": clean_query, "per_page": bounded_limit, "sort": "stars", "order": "desc"})
        url = f"{_GITHUB_API}/search/repositories?{params}"
        try:
            payload, headers = _github_json(url)
            items = list(payload.get("items") or [])[:bounded_limit]
            results = [_github_repository_record(item) for item in items if isinstance(item, dict)]
            if include_sidecars:
                for result in results[: max(0, min(sidecar_limit, 3))]:
                    sidecar = self.fetch_github_readme_sidecar(str(result.get("full_name") or ""))
                    if sidecar.get("ok"):
                        result["sidecar"] = sidecar["sidecar"]
            return {
                "ok": True,
                "version": RESEARCH_BRIDGE_VERSION,
                "provider": "github",
                "query": clean_query,
                "count": len(results),
                "total_count": int(payload.get("total_count") or 0),
                "incomplete_results": bool(payload.get("incomplete_results")),
                "rate_limit_remaining": headers.get("x-ratelimit-remaining", ""),
                "results": results,
                "metadata_truth": GITHUB_METADATA_TRUTH,
                "sidecar_truth": SIDECAR_TRUTH,
                "external_evidence_is_patch_authority": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:  # noqa: BLE001
            return _error(f"github_search_failed:{type(exc).__name__}:{exc}", provider="github", query=clean_query)

    def fetch_github_readme_sidecar(self, full_name: str) -> dict[str, Any]:
        normalized = _normalize_repo_name(full_name)
        if not normalized:
            return _error("invalid_github_repository", provider="github")
        url = f"{_GITHUB_API}/repos/{quote(normalized, safe='/')}/readme"
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "application/vnd.github.raw+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
                raw = response.read(MAX_SIDECAR_CHARS + 1)
                text = raw[:MAX_SIDECAR_CHARS].decode("utf-8", errors="replace")
            return {
                "ok": bool(text),
                "sidecar": {
                    "kind": "github_readme",
                    "full_name": normalized,
                    "source_url": f"https://github.com/{normalized}",
                    "text": text,
                    "truncated": len(raw) > MAX_SIDECAR_CHARS,
                    "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "truth_class": SIDECAR_TRUTH,
                },
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:  # noqa: BLE001
            return _error(f"github_sidecar_failed:{type(exc).__name__}:{exc}", provider="github")


def _parse_arxiv_atom(xml_data: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_data)
    atom = "{http://www.w3.org/2005/Atom}"
    records: list[dict[str, Any]] = []
    for entry in root.findall(f"{atom}entry"):
        entry_id = (entry.findtext(f"{atom}id") or "").strip()
        raw_id = entry_id.rstrip("/").split("/")[-1] if entry_id else ""
        base_id, version = _split_arxiv_version(raw_id)
        title = " ".join((entry.findtext(f"{atom}title") or "").split())
        abstract = " ".join((entry.findtext(f"{atom}summary") or "").split())
        authors = [
            " ".join((author.findtext(f"{atom}name") or "").split())
            for author in entry.findall(f"{atom}author")
            if (author.findtext(f"{atom}name") or "").strip()
        ]
        categories = [
            str(category.get("term") or "")
            for category in entry.findall(f"{atom}category")
            if category.get("term")
        ]
        links = [dict(link.attrib) for link in entry.findall(f"{atom}link")]
        pdf_url = next(
            (str(link.get("href")) for link in links if link.get("type") == "application/pdf"),
            f"https://arxiv.org/pdf/{raw_id}" if raw_id else "",
        )
        record = {
            "provider": "arxiv",
            "arxiv_id": base_id,
            "versioned_id": raw_id,
            "version": version,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "categories": categories,
            "primary_category": categories[0] if categories else "",
            "published": (entry.findtext(f"{atom}published") or "").strip(),
            "updated": (entry.findtext(f"{atom}updated") or "").strip(),
            "entry_url": entry_id,
            "pdf_url": pdf_url,
            "links": links,
            "metadata_sha256": "",
            "truth_class": ARXIV_METADATA_TRUTH,
        }
        record["metadata_sha256"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        records.append(record)
    return records


def _github_repository_record(item: dict[str, Any]) -> dict[str, Any]:
    owner = dict(item.get("owner") or {})
    license_info = dict(item.get("license") or {}) if isinstance(item.get("license"), dict) else {}
    record = {
        "provider": "github",
        "repository_id": item.get("id"),
        "node_id": item.get("node_id"),
        "full_name": str(item.get("full_name") or ""),
        "name": str(item.get("name") or ""),
        "owner": str(owner.get("login") or ""),
        "description": str(item.get("description") or ""),
        "html_url": str(item.get("html_url") or ""),
        "api_url": str(item.get("url") or ""),
        "default_branch": str(item.get("default_branch") or ""),
        "language": str(item.get("language") or ""),
        "topics": list(item.get("topics") or []),
        "license": str(license_info.get("spdx_id") or license_info.get("name") or ""),
        "stargazers_count": int(item.get("stargazers_count") or 0),
        "forks_count": int(item.get("forks_count") or 0),
        "open_issues_count": int(item.get("open_issues_count") or 0),
        "archived": bool(item.get("archived")),
        "fork": bool(item.get("fork")),
        "created_at": str(item.get("created_at") or ""),
        "updated_at": str(item.get("updated_at") or ""),
        "pushed_at": str(item.get("pushed_at") or ""),
        "search_score": float(item.get("score") or 0.0),
        "metadata_sha256": "",
        "truth_class": GITHUB_METADATA_TRUTH,
    }
    record["metadata_sha256"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return record


def _github_json(url: str) -> tuple[dict[str, Any], dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
        headers = {key.lower(): value for key, value in response.headers.items()}
    if not isinstance(payload, dict):
        raise ValueError("GitHub API returned a non-object payload")
    return payload, headers


def _clean_query(query: str) -> str:
    value = " ".join(str(query or "").split())
    if not value:
        raise ValueError("query is required")
    if len(value) > MAX_QUERY_CHARS:
        raise ValueError(f"query exceeds {MAX_QUERY_CHARS} characters")
    return value


def _normalize_arxiv_id(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", text, flags=re.IGNORECASE)
    text = text.removesuffix(".pdf")
    return text if re.fullmatch(r"(?:[a-z-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?", text, re.IGNORECASE) else ""


def _split_arxiv_version(value: str) -> tuple[str, int | None]:
    match = re.fullmatch(r"(.+?)v(\d+)", str(value or ""))
    if not match:
        return str(value or ""), None
    return match.group(1), int(match.group(2))


def _normalize_repo_name(value: str) -> str:
    text = str(value or "").strip().removeprefix("https://github.com/").strip("/")
    return text if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text) else ""


def _error(message: str, *, provider: str = "", query: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "error": str(message),
        "provider": provider,
        "query": query,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "external_evidence_is_patch_authority": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
