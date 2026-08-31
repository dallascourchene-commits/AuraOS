"""Provider adapters for Aura external-knowledge discovery.

Discovery is intentionally weaker than admission. Returned records are normalized
source observations; `aura_external_knowledge_ingress` remains the owner that
decides whether they can become CURRENT_REFERENCE nodes.

No adapter executes downloaded code, imports remote model modules, or downloads
model weights.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Iterable


USER_AGENT = "AuraOS-ExternalIngress/1.0 (source-resolvable research index)"
GOOGLE_SCHOLAR_BLOCK = "GOOGLE_SCHOLAR_AUTOMATION_NOT_ADMITTED_NO_OFFICIAL_API"


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return _sha_text(body)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DiscoveryRecord:
    provider: str
    source_kind: str
    canonical_id: str
    canonical_uri: str
    title: str
    provider_revision: str
    source_generated_at: str
    exact_source_uri: str
    provider_metadata_digest: str
    metadata: dict[str, Any]
    revision_strength: str
    read_only_discovery: bool = True
    code_execution_authorized: bool = False
    model_download_authorized: bool = False
    remote_code_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DiscoveryError(RuntimeError):
    pass


def _json_get(url: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[Any, dict[str, str]]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        body = json.loads(raw.decode("utf-8"))
        response_headers = {k.lower(): v for k, v in response.headers.items()}
    return body, response_headers


def _text_get(url: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[str, dict[str, str]]:
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8")
        response_headers = {k.lower(): v for k, v in response.headers.items()}
    return text, response_headers


def _iso_or_now(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return _utc_now()


def discover_arxiv(query: str, *, limit: int = 5) -> list[DiscoveryRecord]:
    encoded = urllib.parse.quote(query)
    url = f"https://export.arxiv.org/api/query?search_query=all:{encoded}&start=0&max_results={limit}"
    text, _ = _text_get(url, headers={"Accept": "application/atom+xml"})
    root = ET.fromstring(text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    records: list[DiscoveryRecord] = []
    for entry in root.findall("a:entry", ns):
        raw_id = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
        title = " ".join((entry.findtext("a:title", default="", namespaces=ns) or "").split())
        updated = (entry.findtext("a:updated", default="", namespaces=ns) or "").strip()
        published = (entry.findtext("a:published", default="", namespaces=ns) or "").strip()
        summary = " ".join((entry.findtext("a:summary", default="", namespaces=ns) or "").split())
        links = {
            node.attrib.get("rel", ""): node.attrib.get("href", "")
            for node in entry.findall("a:link", ns)
        }
        metadata = {
            "summary": summary,
            "published": published,
            "updated": updated,
            "authors": [
                (author.findtext("a:name", default="", namespaces=ns) or "").strip()
                for author in entry.findall("a:author", ns)
            ],
            "links": links,
        }
        canonical_id = raw_id.rsplit("/", 1)[-1]
        records.append(
            DiscoveryRecord(
                provider="ARXIV",
                source_kind="PAPER",
                canonical_id=canonical_id,
                canonical_uri=raw_id,
                title=title,
                provider_revision=canonical_id,
                source_generated_at=_iso_or_now(updated or published),
                exact_source_uri=raw_id,
                provider_metadata_digest=_canonical_digest(metadata),
                metadata=metadata,
                revision_strength="EXACT_VERSION_ID",
            )
        )
    return records


def discover_github(query: str, *, limit: int = 5, token: str | None = None) -> list[DiscoveryRecord]:
    url = "https://api.github.com/search/repositories?q=" + urllib.parse.quote(query) + f"&per_page={limit}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body, _ = _json_get(url, headers=headers)
    records: list[DiscoveryRecord] = []
    for item in body.get("items", []):
        full_name = item["full_name"]
        branch = item.get("default_branch") or "main"
        commit_url = f"https://api.github.com/repos/{full_name}/commits/{urllib.parse.quote(branch)}"
        commit, commit_headers = _json_get(commit_url, headers=headers)
        sha = commit["sha"]
        exact = f"https://github.com/{full_name}/tree/{sha}"
        metadata = {
            "description": item.get("description"),
            "language": item.get("language"),
            "license": (item.get("license") or {}).get("spdx_id"),
            "topics": item.get("topics") or [],
            "archived": bool(item.get("archived")),
            "fork": bool(item.get("fork")),
            "default_branch": branch,
            "stars": item.get("stargazers_count"),
            "updated_at": item.get("updated_at"),
            "pushed_at": item.get("pushed_at"),
            "etag": commit_headers.get("etag"),
        }
        records.append(
            DiscoveryRecord(
                provider="GITHUB",
                source_kind="REPOSITORY",
                canonical_id=full_name,
                canonical_uri=item["html_url"],
                title=full_name,
                provider_revision=sha,
                source_generated_at=_iso_or_now((commit.get("commit") or {}).get("committer", {}).get("date")),
                exact_source_uri=exact,
                provider_metadata_digest=_canonical_digest(metadata),
                metadata=metadata,
                revision_strength="EXACT_COMMIT_SHA",
            )
        )
    return records


def discover_hugging_face(query: str, *, limit: int = 5, token: str | None = None, repo_type: str = "model") -> list[DiscoveryRecord]:
    if repo_type not in {"model", "dataset", "space"}:
        raise DiscoveryError("HF_REPO_TYPE_UNSUPPORTED")
    endpoint = {"model": "models", "dataset": "datasets", "space": "spaces"}[repo_type]
    url = f"https://huggingface.co/api/{endpoint}?search={urllib.parse.quote(query)}&limit={limit}&full=true"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body, _ = _json_get(url, headers=headers)
    records: list[DiscoveryRecord] = []
    for item in body:
        repo_id = item.get("id") or item.get("modelId")
        sha = item.get("sha")
        if not repo_id or not sha:
            continue
        kind = {"model": "MODEL", "dataset": "DATASET", "space": "SPACE"}[repo_type]
        prefix = "datasets/" if repo_type == "dataset" else "spaces/" if repo_type == "space" else ""
        exact = f"https://huggingface.co/{prefix}{repo_id}/tree/{sha}"
        metadata = {
            "tags": item.get("tags") or [],
            "pipeline_tag": item.get("pipeline_tag"),
            "library_name": item.get("library_name"),
            "gated": item.get("gated"),
            "private": bool(item.get("private")),
            "disabled": bool(item.get("disabled")),
            "downloads": item.get("downloads"),
            "likes": item.get("likes"),
            "lastModified": item.get("lastModified"),
            "securityStatus": item.get("securityStatus"),
        }
        records.append(
            DiscoveryRecord(
                provider="HUGGING_FACE",
                source_kind=kind,
                canonical_id=repo_id,
                canonical_uri=f"https://huggingface.co/{prefix}{repo_id}",
                title=repo_id,
                provider_revision=sha,
                source_generated_at=_iso_or_now(item.get("lastModified")),
                exact_source_uri=exact,
                provider_metadata_digest=_canonical_digest(metadata),
                metadata=metadata,
                revision_strength="EXACT_REPO_SHA",
            )
        )
    return records


def discover_openalex(query: str, *, limit: int = 5, api_key: str | None = None) -> list[DiscoveryRecord]:
    params = {"search": query, "per-page": str(limit)}
    if api_key:
        params["api_key"] = api_key
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    body, _ = _json_get(url)
    records: list[DiscoveryRecord] = []
    for item in body.get("results", []):
        canonical_id = item["id"]
        doi = item.get("doi")
        primary = item.get("primary_location") or {}
        landing = primary.get("landing_page_url") or doi or canonical_id
        metadata = {
            "doi": doi,
            "publication_date": item.get("publication_date"),
            "updated_date": item.get("updated_date"),
            "type": item.get("type"),
            "open_access": item.get("open_access"),
            "primary_topic": item.get("primary_topic"),
            "authorships": item.get("authorships") or [],
        }
        records.append(
            DiscoveryRecord(
                provider="OPENALEX",
                source_kind="PAPER",
                canonical_id=canonical_id,
                canonical_uri=canonical_id,
                title=item.get("title") or canonical_id,
                provider_revision=str(item.get("updated_date") or item.get("created_date") or "UNKNOWN"),
                source_generated_at=_iso_or_now(item.get("updated_date") or item.get("publication_date")),
                exact_source_uri=landing,
                provider_metadata_digest=_canonical_digest(metadata),
                metadata=metadata,
                revision_strength="PROVIDER_UPDATED_TIMESTAMP",
            )
        )
    return records


def discover_crossref(query: str, *, limit: int = 5, mailto: str | None = None) -> list[DiscoveryRecord]:
    params = {"query.bibliographic": query, "rows": str(limit)}
    if mailto:
        params["mailto"] = mailto
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    body, _ = _json_get(url)
    records: list[DiscoveryRecord] = []
    for item in (body.get("message") or {}).get("items", []):
        doi = item.get("DOI")
        if not doi:
            continue
        indexed = (item.get("indexed") or {}).get("date-time")
        updated = (item.get("deposited") or {}).get("date-time")
        metadata = {
            "type": item.get("type"),
            "publisher": item.get("publisher"),
            "license": item.get("license") or [],
            "relation": item.get("relation") or {},
            "indexed": item.get("indexed"),
            "deposited": item.get("deposited"),
            "URL": item.get("URL"),
        }
        records.append(
            DiscoveryRecord(
                provider="CROSSREF",
                source_kind="PAPER",
                canonical_id=doi,
                canonical_uri=f"https://doi.org/{doi}",
                title=" ".join(item.get("title") or [doi]),
                provider_revision=str(indexed or updated or "UNKNOWN"),
                source_generated_at=_iso_or_now(indexed or updated),
                exact_source_uri=item.get("URL") or f"https://doi.org/{doi}",
                provider_metadata_digest=_canonical_digest(metadata),
                metadata=metadata,
                revision_strength="PROVIDER_INDEX_TIMESTAMP",
            )
        )
    return records


def discover_semantic_scholar(query: str, *, limit: int = 5, api_key: str | None = None) -> list[DiscoveryRecord]:
    fields = "paperId,title,url,abstract,year,externalIds,openAccessPdf,publicationDate,publicationTypes"
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search?"
        + urllib.parse.urlencode({"query": query, "limit": str(limit), "fields": fields})
    )
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    body, _ = _json_get(url, headers=headers)
    records: list[DiscoveryRecord] = []
    for item in body.get("data", []):
        paper_id = item["paperId"]
        exact = ((item.get("openAccessPdf") or {}).get("url")) or item.get("url")
        metadata = {
            "abstract": item.get("abstract"),
            "year": item.get("year"),
            "externalIds": item.get("externalIds") or {},
            "publicationDate": item.get("publicationDate"),
            "publicationTypes": item.get("publicationTypes") or [],
        }
        records.append(
            DiscoveryRecord(
                provider="SEMANTIC_SCHOLAR",
                source_kind="PAPER",
                canonical_id=paper_id,
                canonical_uri=item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}",
                title=item.get("title") or paper_id,
                provider_revision=_canonical_digest(metadata),
                source_generated_at=_iso_or_now(item.get("publicationDate")),
                exact_source_uri=exact or item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}",
                provider_metadata_digest=_canonical_digest(metadata),
                metadata=metadata,
                revision_strength="SYNTHETIC_METADATA_GENERATION_NO_NATIVE_UPDATED_AT",
            )
        )
    return records


def discover(provider: str, query: str, *, limit: int = 5, token: str | None = None, mailto: str | None = None, repo_type: str = "model") -> list[DiscoveryRecord]:
    provider = provider.upper()
    if provider == "GOOGLE_SCHOLAR":
        raise DiscoveryError(GOOGLE_SCHOLAR_BLOCK)
    if provider == "ARXIV":
        return discover_arxiv(query, limit=limit)
    if provider == "GITHUB":
        return discover_github(query, limit=limit, token=token)
    if provider == "HUGGING_FACE":
        return discover_hugging_face(query, limit=limit, token=token, repo_type=repo_type)
    if provider == "OPENALEX":
        return discover_openalex(query, limit=limit, api_key=token)
    if provider == "CROSSREF":
        return discover_crossref(query, limit=limit, mailto=mailto)
    if provider == "SEMANTIC_SCHOLAR":
        return discover_semantic_scholar(query, limit=limit, api_key=token)
    raise DiscoveryError("PROVIDER_NOT_IMPLEMENTED")


def emit_json(records: Iterable[DiscoveryRecord]) -> str:
    return json.dumps([record.to_dict() for record in records], sort_keys=True, indent=2)
