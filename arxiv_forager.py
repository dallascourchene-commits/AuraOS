"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e1-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: urllib.error, asyncio, datetime, urllib.request, os, xml.etree.ElementTree, numpy, urllib.parse, hashlib, time, json
FUNCTIONS: __init__, fetch_latest_paper, upgraded_arxiv_backtracker
SYNOPSIS: The `AuraArxivSynopsis` module, a strict Python 3.10+ dependency-heavy utility, integrates `urllib.error`, `asyncio`, `datetime`, `urllib.request`, `os`, `xml.etree.ElementTree`, `numpy`, `urllib.parse`, `hashlib`, `time`, and `json` to initialize a lightweight arXiv API client (`__init__`) that asynchronously fetches latest research papers (`fetch_latest_paper`) and implements an upgraded backtracking mechanism (`upgraded_arxiv_backtracker`) for robust paper retrieval with integrity verification via cryptographic hashing and structured XML parsing.
[/AURA_MASTER_KEY]
"""
import asyncio
import base64
from datetime import datetime, timedelta
import hashlib
import json
import os
import time
import urllib.error
from urllib.parse import urlencode
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

import numpy as np

from aura_paper_memory import (
    compile_paper_memory_record,
    extract_pdf_text_from_bytes,
    record_to_trace_content,
    upsert_paper_memory_record,
)
from aura_scientific_memory import (
    ScientificMemoryIndex,
    ScientificPaperEncoder,
    ScientificRecord,
    ScientificSlots,
    pack_vector,
    unpack_vector,
)

_SCIENTIFIC_ENCODER = ScientificPaperEncoder()
_ARXIV_API_URL = "https://export.arxiv.org/api/query"
_ARXIV_OAI_URL = "https://export.arxiv.org/oai2"
_ARXIV_USER_AGENT = "AuraOS/1.0 (mailto:aura.os.q@gmail.com)"
_ARXIV_MIN_REQUEST_DELAY = 3.5
_ARXIV_SAFE_PAGE_SIZE = 200
_ARXIV_BACKTRACK_WINDOW = timedelta(days=1)
_ARXIV_MAX_PDF_BYTES = 15_000_000
_PAPER_MEMORY_LEDGER = "Aura_Memory/paper_memory_ledger.jsonl"


def _scientific_record(
    record_id: str,
    title: str,
    abstract: str,
    *,
    categories=(),
    published=None,
):
    """
    Encodes a scientific paper record using VSA-based vectorization.

    Parameters:
        record_id (str): Unique identifier for the record
        published: Optional publication date, either as a datetime object or ISO-like string

    Returns:
        ScientificRecord: Encoded record with vector representation and semantic slots
    """
    year = getattr(published, "year", None)
    if year is None and isinstance(published, str):
        year = published[:4] if len(published) >= 4 else None
    return _SCIENTIFIC_ENCODER.encode_document(
        record_id,
        title,
        abstract,
        categories=categories,
        year=year,
    )


class ArXivForager:
    def __init__(self, node_ref=None):
        """
        Initialize the forager with an optional node reference for database operations.

        Parameters:
            node_ref: Optional node object providing database persistence via memory_palace.conn.
        """
        self.node = node_ref  # Bind the main node reference
        self._last_request_time = 0.0
        self.paper_memory_ledger_path = _PAPER_MEMORY_LEDGER

    async def _fetch_pdf_text(
        self,
        pdf_url: str | None,
        *,
        timeout: float = 45.0,
        max_bytes: int = _ARXIV_MAX_PDF_BYTES,
    ) -> str:
        if not pdf_url:
            return ""

        request = urllib.request.Request(
            pdf_url,
            headers={
                "User-Agent": _ARXIV_USER_AGENT,
                "Accept": "application/pdf",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )

        def _read_pdf() -> bytes:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                length = response.headers.get("Content-Length")
                if length and int(length) > max_bytes:
                    return b""
                payload = response.read(max_bytes + 1)
                if len(payload) > max_bytes:
                    return b""
                return payload

        try:
            payload = await asyncio.to_thread(_read_pdf)
            if not payload:
                return ""
            return await asyncio.to_thread(extract_pdf_text_from_bytes, payload)
        except Exception:
            return ""

    async def _persist_paper_memory(
        self,
        *,
        doc_id: str,
        title: str,
        abstract: str,
        full_text: str = "",
        authors=(),
        categories=(),
        published: str = "",
        source_url: str = "",
        pdf_url: str = "",
        metadata: dict | None = None,
    ):
        record = compile_paper_memory_record(
            doc_id=doc_id,
            title=title,
            abstract=abstract,
            full_text=full_text,
            authors=authors,
            categories=categories,
            published=published,
            source_url=source_url,
            pdf_url=pdf_url,
            metadata=metadata or {},
        )
        try:
            await asyncio.to_thread(
                upsert_paper_memory_record,
                record,
                self.paper_memory_ledger_path,
            )
        except Exception as exc:
            print(f"[-] Paper memory ledger write skipped: {exc}")
        return record

    async def _ensure_backtracker_schema(self, conn) -> None:
        """Ensure legacy Aura memory DBs can accept scientific backtrack rows."""
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                content TEXT,
                tier TEXT,
                timestamp TEXT,
                tags TEXT,
                vector_blob BLOB
            )
            """
        )
        required_columns = {
            "id": "TEXT",
            "content": "TEXT",
            "tier": "TEXT",
            "timestamp": "TEXT",
            "tags": "TEXT",
            "vector_blob": "BLOB",
        }
        async with conn.execute("PRAGMA table_info(traces);") as cursor:
            rows = await cursor.fetchall()
        existing = {str(row[1]) for row in rows}
        for name, declaration in required_columns.items():
            if name in existing:
                continue
            try:
                await conn.execute(
                    f"ALTER TABLE traces ADD COLUMN {name} {declaration};"
                )
            except Exception as exc:
                if "duplicate column" not in str(exc).lower():
                    raise
        await conn.commit()

    async def _fetch_arxiv_xml(
        self,
        search_query: str = "",
        *,
        id_list: str | None = None,
        start: int = 0,
        max_results: int = 100,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        max_retries: int = 3,
        timeout: float = 30.0,
        min_delay: float = _ARXIV_MIN_REQUEST_DELAY,
    ) -> tuple[bytes, int]:
        """Fetch one Atom page without blocking the event loop.

        arXiv recommends at least three seconds between requests and smaller
        result slices for broad queries.  Retries therefore pace themselves,
        increase the socket timeout, and halve the requested page after a
        timeout, throttle response, or transient server failure.
        """
        page_size = max(1, min(int(max_results), 2_000))
        retries = max(1, int(max_retries))
        base_timeout = max(1.0, float(timeout))
        request_delay = max(3.0, float(min_delay))
        last_error: Exception | None = None

        for attempt in range(retries):
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < request_delay:
                await asyncio.sleep(request_delay - elapsed)

            params = {
                "start": max(0, int(start)),
                "max_results": page_size,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            }
            if search_query:
                params["search_query"] = search_query
            if id_list:
                params["id_list"] = id_list
            request = urllib.request.Request(
                f"{_ARXIV_API_URL}?{urlencode(params)}",
                headers={
                    "User-Agent": _ARXIV_USER_AGENT,
                    "Accept": "application/atom+xml,application/xml,text/xml",
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                },
            )
            attempt_timeout = min(90.0, base_timeout * (1.5 ** attempt))

            def _read_response() -> bytes:
                with urllib.request.urlopen(
                    request, timeout=attempt_timeout
                ) as response:
                    return response.read()

            try:
                payload = await asyncio.to_thread(_read_response)
                self._last_request_time = time.monotonic()
                if not payload:
                    raise ValueError("arXiv returned an empty response")
                return payload, page_size
            except urllib.error.HTTPError as exc:
                self._last_request_time = time.monotonic()
                last_error = exc
                transient = exc.code in {408, 425, 429, 500, 502, 503, 504}
                if not transient or attempt == retries - 1:
                    raise
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = max(request_delay, float(retry_after))
                except (TypeError, ValueError):
                    if exc.code == 429:
                        delay = min(120.0, 15.0 * (2 ** attempt))
                    else:
                        delay = request_delay * (2 ** attempt)
            except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError, ValueError) as exc:
                self._last_request_time = time.monotonic()
                last_error = exc
                if attempt == retries - 1:
                    raise
                delay = request_delay * (2 ** attempt)

            page_size = max(1, page_size // 2)
            print(
                f"[⚠️ ARXIV RETRY] {last_error}. "
                f"Retrying in {delay:.2f}s with {page_size} results..."
            )
            await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error

    async def _fetch_arxiv_oai_xml(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        resumption_token: str | None = None,
        max_retries: int = 3,
        timeout: float = 60.0,
        min_delay: float = _ARXIV_MIN_REQUEST_DELAY,
    ) -> bytes:
        """Fetch one official OAI-PMH metadata page as an API fallback."""
        if resumption_token:
            params = {
                "verb": "ListRecords",
                "resumptionToken": resumption_token,
            }
        else:
            params = {
                "verb": "ListRecords",
                "set": "cs",
                "metadataPrefix": "arXiv",
                "from": (date_from or datetime.utcnow()).strftime("%Y-%m-%d"),
                "until": (date_to or datetime.utcnow()).strftime("%Y-%m-%d"),
            }

        retries = max(1, int(max_retries))
        base_timeout = max(1.0, float(timeout))
        request_delay = max(3.0, float(min_delay))
        last_error: Exception | None = None

        for attempt in range(retries):
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < request_delay:
                await asyncio.sleep(request_delay - elapsed)

            request = urllib.request.Request(
                f"{_ARXIV_OAI_URL}?{urlencode(params)}",
                headers={
                    "User-Agent": _ARXIV_USER_AGENT,
                    "Accept": "application/xml,text/xml",
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                },
            )
            attempt_timeout = min(120.0, base_timeout * (1.5 ** attempt))

            def _read_response() -> bytes:
                with urllib.request.urlopen(
                    request, timeout=attempt_timeout
                ) as response:
                    return response.read()

            try:
                payload = await asyncio.to_thread(_read_response)
                self._last_request_time = time.monotonic()
                if not payload:
                    raise ValueError("arXiv OAI-PMH returned an empty response")
                return payload
            except urllib.error.HTTPError as exc:
                self._last_request_time = time.monotonic()
                last_error = exc
                if (
                    exc.code not in {408, 425, 429, 500, 502, 503, 504}
                    or attempt == retries - 1
                ):
                    raise
                delay = (
                    min(120.0, 15.0 * (2 ** attempt))
                    if exc.code == 429
                    else request_delay * (2 ** attempt)
                )
            except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError, ValueError) as exc:
                self._last_request_time = time.monotonic()
                last_error = exc
                if attempt == retries - 1:
                    raise
                delay = request_delay * (2 ** attempt)

            print(
                f"[⚠️ ARXIV OAI RETRY] {last_error}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _parse_arxiv_oai_records(
        xml_data: bytes,
    ) -> tuple[list[dict], str | None]:
        """Convert an OAI-PMH arXiv page to the enhanced-forager record shape."""
        oai_ns = "http://www.openarchives.org/OAI/2.0/"
        arxiv_ns = "http://arxiv.org/OAI/arXiv/"
        root = ET.fromstring(xml_data)
        papers: list[dict] = []

        for record in root.findall(f".//{{{oai_ns}}}record"):
            header = record.find(f"{{{oai_ns}}}header")
            if header is not None and header.get("status") == "deleted":
                continue
            metadata = record.find(f"{{{oai_ns}}}metadata")
            if metadata is None:
                continue
            paper = metadata.find(f"{{{arxiv_ns}}}arXiv")
            if paper is None:
                continue

            paper_id = (paper.findtext(f"{{{arxiv_ns}}}id") or "").strip()
            if not paper_id:
                continue
            created = (paper.findtext(f"{{{arxiv_ns}}}created") or "").strip()
            published = None
            for date_format in ("%Y-%m-%d", "%d-%b-%Y"):
                try:
                    published = datetime.strptime(created, date_format)
                    break
                except ValueError:
                    continue
            if published is None:
                published = datetime.utcnow()
            authors = []
            for author in paper.findall(
                f"{{{arxiv_ns}}}authors/{{{arxiv_ns}}}author"
            ):
                forenames = (
                    author.findtext(f"{{{arxiv_ns}}}forenames") or ""
                ).strip()
                keyname = (
                    author.findtext(f"{{{arxiv_ns}}}keyname") or ""
                ).strip()
                name = " ".join(part for part in (forenames, keyname) if part)
                if name:
                    authors.append(name)

            papers.append({
                "paper_id": paper_id,
                "entry_id": f"https://arxiv.org/abs/{paper_id}",
                "title": " ".join(
                    (paper.findtext(f"{{{arxiv_ns}}}title") or "").split()
                ),
                "abstract": " ".join(
                    (paper.findtext(f"{{{arxiv_ns}}}abstract") or "").split()
                ),
                "published": published,
                "authors": authors,
                "categories": (
                    paper.findtext(f"{{{arxiv_ns}}}categories") or ""
                ).split(),
                "pdf_url": f"https://arxiv.org/pdf/{paper_id}",
            })

        token = root.findtext(
            f".//{{{oai_ns}}}resumptionToken",
            default="",
        ).strip()
        return papers, token or None

    async def fetch_latest_paper(self, topic: str, max_retries: int = 3, timeout: float = 30.0) -> str:
        """
        Fetch the most relevant arXiv paper for a given topic.

        Queries the arXiv API with retry logic, parses the result, and optionally encodes and persists a scientific record to the database if a node is available.

        Parameters:
            topic (str): The search topic to query on arXiv.
            max_retries (int): Maximum number of retry attempts on network failures. Default 3.
            timeout (float): Initial request timeout in seconds. Default 30.0.

        Returns:
            str: A formatted string containing the paper's title and abstract on success, or an error message on failure.
        """
        try:
            xml_data, _ = await self._fetch_arxiv_xml(
                f"all:{topic.strip()}",
                max_results=1,
                sort_by="relevance",
                max_retries=max_retries,
                timeout=timeout,
            )
        except Exception as exc:
            return (
                f"arXiv API connection failed after "
                f"{max(1, int(max_retries))} attempts: {exc}"
            )

        try:
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            if not entries:
                return f"No relevant arXiv papers found for: {topic}"

            entry = entries[0]
            atom_ns = "{http://www.w3.org/2005/Atom}"
            title = (entry.findtext(f"{atom_ns}title") or "").strip()
            summary = (entry.findtext(f"{atom_ns}summary") or "").strip()
            summary = " ".join(summary.split())
            entry_id = (entry.findtext(f"{atom_ns}id") or "").strip()
            paper_id = entry_id.rstrip("/").split("/")[-1] if entry_id else ""
            pdf_url = next(
                (
                    link.get("href")
                    for link in entry.findall(f"{atom_ns}link")
                    if link.get("type") == "application/pdf"
                ),
                f"https://arxiv.org/pdf/{paper_id}" if paper_id else "",
            )
            authors = [
                (author.findtext(f"{atom_ns}name") or "").strip()
                for author in entry.findall(f"{atom_ns}author")
                if (author.findtext(f"{atom_ns}name") or "").strip()
            ]
            categories = [
                category.get("term", "")
                for category in entry.findall(f"{atom_ns}category")
                if category.get("term")
            ]
            published = (entry.findtext(f"{atom_ns}published") or "").strip()
            doc_id = f"ARXIV_{paper_id.replace('/', '_')}" if paper_id else (
                f"ARXIV_{hashlib.sha256((title + summary).encode()).hexdigest()[:8].upper()}"
            )
            pdf_text = await self._fetch_pdf_text(pdf_url)
            paper_memory = await self._persist_paper_memory(
                doc_id=doc_id,
                title=title,
                abstract=summary,
                full_text=pdf_text,
                authors=authors,
                categories=categories,
                published=published,
                source_url=entry_id,
                pdf_url=pdf_url,
                metadata={"ingest_path": "fetch_latest_paper"},
            )
            full_text = record_to_trace_content(paper_memory)

            if self.node is not None:
                record = _scientific_record(doc_id, title, summary)
                blob_data = pack_vector(record.vector)
                try:
                    conn = self.node.memory_palace.conn
                    await conn.execute(
                        "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) VALUES (?, ?, 'CRYSTAL', ?, 'Scientific VSA v1', ?)",
                        (doc_id, full_text, datetime.now().isoformat(), blob_data)
                    )
                    await conn.commit()
                except Exception as e:
                    print(f"[-] Local DB write failed: {e}")

            points = "\n".join(
                f"POINT {idx + 1}: {point}"
                for idx, point in enumerate(paper_memory.three_main_points)
                if point
            )
            return f"TITLE: {title}\nABSTRACT: {summary}\n{points}"
        except Exception as e:
            return f"arXiv processing failure: {e}"

    async def upgraded_arxiv_backtracker(
        self,
        max_results: int = 200,
        max_retries: int = 3,
        timeout: float = 30.0,
        pdf_fetch_limit: int | None = None,
    ) -> bool:
        """
        Asynchronously crawl backwards through arXiv CS submissions, vectorizing and storing papers while managing pagination limits.

        This method maintains a persistent offset inside a bounded one-day
        submission window. Bounded windows keep the server-side result set
        small, and the shared request helper performs paced, adaptive retries.
        Fetched papers are vectorized via `_scientific_record`, packed, and
        inserted into the database.

        Requires an active database connection via `self.node.memory_palace.conn`.

        Parameters:
            max_results (int): Number of papers to fetch per API request. Defaults to 200.
            max_retries (int): Number of retry attempts for network failures. Defaults to 3.
            timeout (float): Initial request timeout in seconds. Defaults to 30.0.

        Returns:
            `True` if papers were successfully ingested, the 10k limit was recovered, or the date window
            was advanced; `False` if the absolute end of the timeline was reached or a final network
            error occurred without recovery. When `True` is returned after recovery, the caller should
            re-invoke to continue ingestion.
        """
        if self.node is None or not self.node.memory_palace.conn:
            print("[-] Backtracker Error: No active database connection linked to Forager.")
            return False

        conn = self.node.memory_palace.conn
        try:
            await self._ensure_backtracker_schema(conn)
        except Exception as schema_exc:
            print(f"[-] Backtracker DB schema error: {schema_exc}")
            return False

        # 1. Load persistent crawler state
        crawler_state = {
            'crawl_offset_index': 0,
            'last_crawl_time': 0.0,
            'crawl_window_start': None,
            'crawl_window_end': None,
        }
        loaded_had_window_start = False
        try:
            async with conn.execute(
                "SELECT content FROM traces WHERE id = 'ARXIV_CRAWLER_STATE';"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    loaded = json.loads(row[0])
                    loaded_had_window_start = bool(
                        loaded.get('crawl_window_start')
                    )
                    crawler_state.update(loaded)
        except Exception:
            pass

        window_start, window_end = self._normalise_backtracker_window(
            crawler_state
        )
        if not loaded_had_window_start:
            # A legacy offset belonged to an unbounded query and cannot be
            # reused safely inside the new bounded window.
            crawler_state['crawl_offset_index'] = 0
        runtime_metrics = getattr(self.node, "runtime_metrics", None)
        if isinstance(runtime_metrics, dict):
            runtime_metrics['arxiv_crawler_state'] = crawler_state

        # 2. Temporal pacing across separate !backtrack invocations
        current_time = time.time()
        elapsed_time = current_time - crawler_state.get('last_crawl_time', 0.0)
        if elapsed_time < _ARXIV_MIN_REQUEST_DELAY:
            sleep_needed = _ARXIV_MIN_REQUEST_DELAY - elapsed_time
            print(f"[⏳ TEMPORAL PACING] arXiv compliance delay active. Sleeping for {sleep_needed:.2f}s...")
            await asyncio.sleep(sleep_needed)

        current_offset = max(
            0, int(crawler_state.get('crawl_offset_index', 0) or 0)
        )
        search_query = (
            "cat:cs.* AND "
            f"submittedDate:[{window_start} TO {window_end}]"
        )

        # 3. Fetch with adaptive retries. If the query API is throttled,
        # continue through arXiv's official OAI-PMH metadata endpoint.
        print(
            f"[*] Fetching arXiv CS backlog at offset {current_offset}  "
            f"(window {window_start}..{window_end})..."
        )
        raw_papers: list[dict] = []
        total_available = 0
        requested_page_size = min(
            max(1, int(max_results)), _ARXIV_SAFE_PAGE_SIZE
        )
        if pdf_fetch_limit is None:
            try:
                pdf_fetch_limit = int(os.environ.get("AURA_BACKTRACK_PDF_LIMIT", "3"))
            except ValueError:
                pdf_fetch_limit = 3
        pdf_fetch_limit = max(0, int(pdf_fetch_limit))
        pdf_fetch_count = 0
        oai_next_token = None
        using_oai = bool(crawler_state.get('oai_resumption_token'))

        if not using_oai:
            try:
                xml_data, requested_page_size = await self._fetch_arxiv_xml(
                    search_query,
                    start=current_offset,
                    max_results=requested_page_size,
                    max_retries=max_retries,
                    timeout=timeout,
                )
                root = ET.fromstring(xml_data)
                entries = root.findall('{http://www.w3.org/2005/Atom}entry')
                total_text = root.findtext(
                    '{http://a9.com/-/spec/opensearch/1.1/}totalResults',
                    '0',
                )
                try:
                    total_available = int(total_text)
                except (TypeError, ValueError):
                    total_available = 0
                for entry in entries:
                    atom_ns = "{http://www.w3.org/2005/Atom}"
                    entry_id = (
                        entry.findtext(f"{atom_ns}id") or ""
                    ).strip()
                    paper_id = entry_id.rstrip("/").split("/")[-1] if entry_id else ""
                    published = (
                        entry.findtext(
                            f'{atom_ns}published'
                        ) or ""
                    ).strip()
                    try:
                        published_dt = datetime.fromisoformat(
                            published.rstrip("Z")
                        )
                    except ValueError:
                        published_dt = datetime.utcnow()
                    raw_papers.append({
                        "paper_id": paper_id,
                        "entry_id": entry_id,
                        "title": (
                            entry.findtext(
                                f'{atom_ns}title'
                            ) or ""
                        ).strip(),
                        "abstract": " ".join(
                            (
                                entry.findtext(
                                    f'{atom_ns}summary'
                                ) or ""
                            ).split()
                        ),
                        "authors": [
                            (author.findtext(f"{atom_ns}name") or "").strip()
                            for author in entry.findall(f"{atom_ns}author")
                            if (author.findtext(f"{atom_ns}name") or "").strip()
                        ],
                        "published": published_dt,
                        "categories": [
                            category.get("term", "")
                            for category in entry.findall(
                                f'{atom_ns}category'
                            )
                            if category.get("term")
                        ],
                        "pdf_url": next(
                            (
                                link.get("href")
                                for link in entry.findall(f"{atom_ns}link")
                                if link.get("type") == "application/pdf"
                            ),
                            f"https://arxiv.org/pdf/{paper_id}" if paper_id else "",
                        ),
                    })
            except Exception as api_exc:
                print(
                    f"[⚠️ ARXIV FALLBACK] Query API unavailable ({api_exc}); "
                    "switching to official OAI-PMH metadata."
                )
                using_oai = True

        if using_oai:
            try:
                oai_xml = await self._fetch_arxiv_oai_xml(
                    date_from=self._parse_backtracker_timestamp(window_start),
                    date_to=self._parse_backtracker_timestamp(window_end),
                    resumption_token=crawler_state.get(
                        'oai_resumption_token'
                    ),
                    max_retries=max_retries,
                    timeout=max(60.0, timeout),
                )
                raw_papers, oai_next_token = self._parse_arxiv_oai_records(
                    oai_xml
                )
            except Exception as oai_exc:
                print(
                    f"[-] Backtracker network failed on both arXiv endpoints: "
                    f"{oai_exc}"
                )
                crawler_state['last_crawl_time'] = time.time()
                await self._save_backtracker_state(conn, crawler_state)
                return False

        # 4. Parse and ingest
        try:
            if not raw_papers:
                if using_oai and oai_next_token:
                    crawler_state['oai_resumption_token'] = oai_next_token
                    crawler_state['last_crawl_time'] = time.time()
                    await self._save_backtracker_state(conn, crawler_state)
                    return True
                if datetime.strptime(window_end, "%Y%m%d%H%M").year < 1991:
                    print("[+] Backtracker reached the start of the arXiv timeline.")
                    return False
                print("[🔄 WINDOW EDGE] Advancing to the previous bounded window...")
                crawler_state.pop('oai_resumption_token', None)
                self._advance_backtracker_window(crawler_state)
                crawler_state['crawl_offset_index'] = 0
                crawler_state['last_crawl_time'] = time.time()
                await self._save_backtracker_state(conn, crawler_state)
                print("[+] Date window advanced. Run !backtrack again to continue.")
                return True

            ingest_rows: list[tuple] = []
            stamp_ts = datetime.now().isoformat()
            earliest_published = None

            for paper in raw_papers:
                title = paper.get("title", "").strip()
                summary = " ".join(paper.get("abstract", "").split())
                published_dt = paper.get("published") or datetime.utcnow()
                published = (
                    published_dt.isoformat()
                    if hasattr(published_dt, "isoformat")
                    else str(published_dt)
                )

                # Track the earliest pub date in this batch for window advancement
                if earliest_published is None or published < earliest_published:
                    earliest_published = published

                paper_id = str(paper.get("paper_id") or "").strip()
                doc_id = f"ARXIV_{paper_id.replace('/', '_')}" if paper_id else (
                    f"ARXIV_{hashlib.sha256((title + summary).encode()).hexdigest()[:8].upper()}"
                )
                pdf_url = paper.get("pdf_url") or (
                    f"https://arxiv.org/pdf/{paper_id}" if paper_id else ""
                )
                pdf_text = ""
                if pdf_fetch_count < pdf_fetch_limit:
                    pdf_fetch_count += 1
                    pdf_text = await self._fetch_pdf_text(pdf_url, timeout=max(45.0, timeout))

                paper_memory = await self._persist_paper_memory(
                    doc_id=doc_id,
                    title=title,
                    abstract=summary,
                    full_text=pdf_text,
                    authors=paper.get("authors", ()),
                    categories=paper.get("categories", ()),
                    published=published,
                    source_url=paper.get("entry_id", ""),
                    pdf_url=pdf_url,
                    metadata={"ingest_path": "upgraded_arxiv_backtracker"},
                )
                text_block = record_to_trace_content(paper_memory)
                record = _scientific_record(
                    doc_id,
                    title,
                    summary,
                    categories=paper.get("categories", ()),
                    published=published,
                )
                blob_data = pack_vector(record.vector)
                ingest_rows.append(
                    (doc_id, text_block, stamp_ts, blob_data)
                )

            if ingest_rows:
                await conn.executemany(
                    "DELETE FROM traces WHERE id = ?",
                    [(row[0],) for row in ingest_rows],
                )
                await conn.executemany(
                    "INSERT INTO traces (id, content, tier, timestamp, tags, vector_blob) "
                    "VALUES (?, ?, 'CRYSTAL', ?, 'Scientific VSA v1', ?)",
                    ingest_rows,
                )
            stamped_count = len(ingest_rows)

            # 5. Advance state
            new_offset = current_offset + len(raw_papers)

            if using_oai and oai_next_token:
                crawler_state['oai_resumption_token'] = oai_next_token
                crawler_state['crawl_offset_index'] = 0
            elif using_oai:
                crawler_state.pop('oai_resumption_token', None)
                self._advance_backtracker_window(crawler_state)
                crawler_state['crawl_offset_index'] = 0
            elif new_offset >= 9_500:
                print("[🔄 10K GUARD] Approaching arXiv 10k cap. "
                      "Advancing date window pre-emptively...")
                self._advance_backtracker_window(crawler_state, earliest_published)
                crawler_state['crawl_offset_index'] = 0
            elif (
                (total_available > 0 and new_offset >= total_available)
                or len(raw_papers) < requested_page_size
            ):
                self._advance_backtracker_window(crawler_state)
                crawler_state['crawl_offset_index'] = 0
            else:
                crawler_state['crawl_offset_index'] = new_offset

            crawler_state['last_crawl_time'] = time.time()
            await self._save_backtracker_state(conn, crawler_state)

            print(
                f"[+] [ARXIV BACKTRACKER] Successfully vectorized and ingested "
                f"{stamped_count} papers ({pdf_fetch_count} PDF VSA fetch attempts)."
            )
            print(
                f"    Next offset: {crawler_state['crawl_offset_index']}  |  "
                f"Window: {crawler_state['crawl_window_start']}.."
                f"{crawler_state['crawl_window_end']}"
            )
            return True

        except Exception as e:
            print(f"[-] Backtracker processing error: {e}")
            return False

    @staticmethod
    def _parse_backtracker_timestamp(value) -> datetime | None:
        if not value:
            return None
        text = str(value).strip().rstrip("Z")
        try:
            if len(text) == 12 and text.isdigit():
                return datetime.strptime(text, "%Y%m%d%H%M")
            return datetime.fromisoformat(text)
        except (TypeError, ValueError):
            return None

    def _normalise_backtracker_window(
        self, crawler_state: dict
    ) -> tuple[str, str]:
        """Upgrade legacy unbounded state to a contiguous one-day window."""
        end_dt = self._parse_backtracker_timestamp(
            crawler_state.get('crawl_window_end')
        ) or datetime.utcnow()
        start_dt = self._parse_backtracker_timestamp(
            crawler_state.get('crawl_window_start')
        )
        if start_dt is None or start_dt >= end_dt:
            start_dt = end_dt - _ARXIV_BACKTRACK_WINDOW
        crawler_state['crawl_window_start'] = start_dt.strftime("%Y%m%d%H%M")
        crawler_state['crawl_window_end'] = end_dt.strftime("%Y%m%d%H%M")
        return (
            crawler_state['crawl_window_start'],
            crawler_state['crawl_window_end'],
        )

    async def _save_backtracker_state(self, conn, crawler_state: dict) -> None:
        await conn.execute(
            "DELETE FROM traces WHERE id = ?",
            ("ARXIV_CRAWLER_STATE",),
        )
        await conn.execute(
            "INSERT INTO traces "
            "(id, content, tier, timestamp, tags, vector_blob) "
            "VALUES ('ARXIV_CRAWLER_STATE', ?, 'SYSTEM_STATE', ?, "
            "'arXiv Backtracker Crawler State Offset', NULL)",
            (json.dumps(crawler_state), datetime.now().isoformat()),
        )
        await conn.commit()

    def _advance_backtracker_window(self, crawler_state: dict, earliest_published: str | None = None) -> None:
        """
        Push the date window further into the past so the next crawl cycle
        can continue beyond the arXiv 10k hard cap.

        If *earliest_published* is given, continue at that paper's minute.
        Otherwise continue at the current window start. The shared
        boundary minute is intentionally re-read so no same-minute submission
        can be skipped; stable trace IDs make those duplicates harmless.
        """
        new_end = self._parse_backtracker_timestamp(earliest_published)
        if new_end is None:
            new_end = self._parse_backtracker_timestamp(
                crawler_state.get('crawl_window_start')
            )
        if new_end is None:
            old_end = self._parse_backtracker_timestamp(
                crawler_state.get('crawl_window_end')
            ) or datetime.utcnow()
            new_end = old_end - _ARXIV_BACKTRACK_WINDOW
        new_start = new_end - _ARXIV_BACKTRACK_WINDOW
        crawler_state['crawl_window_start'] = new_start.strftime("%Y%m%d%H%M")
        crawler_state['crawl_window_end'] = new_end.strftime("%Y%m%d%H%M")
        print(
            f"[🪟 WINDOW] crawl window set to "
            f"{crawler_state['crawl_window_start']}.."
            f"{crawler_state['crawl_window_end']}"
        )

    async def ingest_arxiv_ids(self, arxiv_ids: list[str]) -> dict[str, Any]:
        """
        Mass ingest papers by their arXiv IDs.
        """
        if not arxiv_ids:
            return {"status": "success", "count": 0, "ingested": [], "failed": []}

        # sanitize the list of ids (remove spaces/prefixes like cs/ etc. if needed, keep basic arxiv format)
        sanitized_ids = []
        for raw_id in arxiv_ids:
            clean_id = raw_id.strip()
            # If ID is full url, extract final component
            if "arxiv.org/abs/" in clean_id:
                clean_id = clean_id.split("arxiv.org/abs/")[-1]
            elif "arxiv.org/pdf/" in clean_id:
                clean_id = clean_id.split("arxiv.org/pdf/")[-1].replace(".pdf", "")
            if clean_id:
                sanitized_ids.append(clean_id)

        if not sanitized_ids:
            return {"status": "success", "count": 0, "ingested": [], "failed": []}

        id_str = ",".join(sanitized_ids)
        try:
            xml_data, _ = await self._fetch_arxiv_xml(
                "",
                id_list=id_str,
                max_results=len(sanitized_ids),
                sort_by="submittedDate",
                sort_order="descending",
            )
        except Exception as exc:
            return {
                "status": "error",
                "message": f"arXiv API fetch failed: {exc}",
                "count": 0,
                "ingested": [],
                "failed": sanitized_ids
            }

        try:
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            if not entries:
                return {
                    "status": "error",
                    "message": "No papers found in arXiv response",
                    "count": 0,
                    "ingested": [],
                    "failed": sanitized_ids
                }

            ingested = []
            failed = list(sanitized_ids)
            conn = self.node.memory_palace.conn if self.node else None
            if conn:
                try:
                    await self._ensure_backtracker_schema(conn)
                except Exception as e:
                    print(f"[-] Database schema validation failed: {e}")

            for entry in entries:
                atom_ns = "{http://www.w3.org/2005/Atom}"
                title = (entry.findtext(f"{atom_ns}title") or "").strip()
                summary = (entry.findtext(f"{atom_ns}summary") or "").strip()
                summary = " ".join(summary.split())
                entry_id = (entry.findtext(f"{atom_ns}id") or "").strip()
                paper_id = entry_id.rstrip("/").split("/")[-1] if entry_id else ""
                
                if not paper_id:
                    continue

                # Remove from failed list if found (check partial matching just in case version suffixes exist, e.g. v1)
                found_id = None
                for raw_id in failed:
                    if raw_id in paper_id or paper_id in raw_id:
                        found_id = raw_id
                        break
                if found_id:
                    failed.remove(found_id)
                
                pdf_url = next(
                    (
                        link.get("href")
                        for link in entry.findall(f"{atom_ns}link")
                        if link.get("type") == "application/pdf"
                    ),
                    f"https://arxiv.org/pdf/{paper_id}" if paper_id else "",
                )
                authors = [
                    (author.findtext(f"{atom_ns}name") or "").strip()
                    for author in entry.findall(f"{atom_ns}author")
                    if (author.findtext(f"{atom_ns}name") or "").strip()
                ]
                categories = [
                    category.get("term", "")
                    for category in entry.findall(f"{atom_ns}category")
                    if category.get("term")
                ]
                published = (entry.findtext(f"{atom_ns}published") or "").strip()
                doc_id = f"ARXIV_{paper_id.replace('/', '_')}"

                pdf_text = await self._fetch_pdf_text(pdf_url)
                paper_memory = await self._persist_paper_memory(
                    doc_id=doc_id,
                    title=title,
                    abstract=summary,
                    full_text=pdf_text,
                    authors=authors,
                    categories=categories,
                    published=published,
                    source_url=entry_id,
                    pdf_url=pdf_url,
                    metadata={"ingest_path": "ingest_arxiv_ids"},
                )
                full_text = record_to_trace_content(paper_memory)

                if conn is not None:
                    record = _scientific_record(doc_id, title, summary, categories=categories, published=published)
                    blob_data = pack_vector(record.vector)
                    try:
                        await conn.execute(
                            "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) VALUES (?, ?, 'CRYSTAL', ?, 'Scientific VSA v1', ?)",
                            (doc_id, full_text, datetime.now().isoformat(), blob_data)
                        )
                        await conn.commit()
                    except Exception as e:
                        print(f"[-] Local DB write failed: {e}")

                ingested.append(paper_id)

            return {
                "status": "success",
                "count": len(ingested),
                "ingested": ingested,
                "failed": failed
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"arXiv processing failure: {e}",
                "count": 0,
                "ingested": [],
                "failed": sanitized_ids
            }


# =============================================================================
# ENHANCED ARXIV FORAGER — VSA storage, async, rate-limiting, similarity search
# Addresses DEEP_AUDIT_REPORT: no async processing, no AuraOS VSA integration,
# no error handling, no connection to existing arxiv_forager.py.
# Extends ArXivForager so existing aura_node.py code continues to work.
# =============================================================================

from dataclasses import dataclass as _dc
from dataclasses import field as _dcfield
from datetime import datetime as _dt
from datetime import timedelta as _td
import logging as _logging
from pathlib import Path as _Path

_eaf_logger = _logging.getLogger("aura.arxiv_forager")


@_dc
class ArxivPaper:
    """Structured representation of an arXiv paper with VSA vector support."""
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    published: _dt
    categories: list[str]
    pdf_url: str | None = None
    full_text: str | None = None
    vector: np.ndarray | None = None
    slots: dict = _dcfield(default_factory=dict)
    metadata: dict = _dcfield(default_factory=dict)

    def to_dict(self) -> dict:
        """
        Serialize the paper to a JSON-compatible dictionary.

        The vector field is base64-encoded after packing; if no vector exists, it is set to None.

        Returns:
            dict: Dictionary containing paper_id, title, authors, abstract, published (ISO format), categories, pdf_url, slots, vector (base64-encoded if present), and metadata.
        """
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "published": self.published.isoformat(),
            "categories": self.categories,
            "pdf_url": self.pdf_url,
            "slots": self.slots,
            "vector": (
                base64.b64encode(pack_vector(self.vector)).decode("ascii")
                if self.vector is not None
                else None
            ),
            "metadata": self.metadata,
        }


@_dc
class ForagerConfig:
    """Configuration for the enhanced arXiv forager.

    The arXiv API hard-caps total results at 10 000 per query.  To collect
    more than that the forager automatically partitions the date range into
    narrower slices (see ``_search_via_urllib`` and ``forage()``).
    """
    query: str
    max_results: int = 200               # reliable page size for broad queries
    categories: list[str] | None = None
    max_days_old: int = 365
    batch_size: int = 50                 # papers to process in one async batch
    rate_limit_delay: float = 3.5        # arXiv compliance: 3.5 s between batches
    max_total: int = 1_000_000           # total papers to collect (date-chunked)
    storage_dir: str = "Aura_Memory/arxiv_cache"

    # --- arXiv API hard cap (do not raise) ---
    _ARXIV_HARD_LIMIT: int = 10_000      # total results per single query


@_dc
class ForagerStats:
    """Runtime statistics for the enhanced forager."""
    papers_fetched: int = 0
    papers_parsed: int = 0
    papers_stored: int = 0
    errors: int = 0
    start_time: _dt | None = None
    end_time: _dt | None = None

    @property
    def duration(self) -> _td | None:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def papers_per_second(self) -> float:
        """
        Calculates the rate of papers fetched per second.

        Returns:
            float: The number of papers fetched per second, or 0.0 if duration is unavailable or non-positive.
        """
        d = self.duration
        if d and d.total_seconds() > 0:
            return self.papers_fetched / d.total_seconds()
        return 0.0


class EnhancedArxivForager(ArXivForager):
    """
    Enhanced arXiv forager with VSA storage and async processing.

    Extends the existing ArXivForager (so aura_node.py's ArXivForager(self)
    calls still work) and adds:
    - Shared 10-slot scientific vector indexing for papers and queries
    - Async batch processing with rate-limiting
    - Hierarchical and LSH-routed scientific-memory search
    - Disk cache with compact bit-packed 10,000-D vectors
    - Structured logging

    Usage
    -----
        forager = EnhancedArxivForager(node_ref)
        papers  = await forager.forage(ForagerConfig(query="quantum ML"))
        similar = await forager.search_similar("quantum neural network")
    """

    def __init__(self, node_ref=None) -> None:
        """
        Initialize the enhanced arXiv forager with vector encoding and caching.

        Sets up a scientific paper encoder and vector index for similarity search, in-memory paper caching, disk-based storage, rate limiting, and statistics tracking.
        """
        super().__init__(node_ref)

        self._scientific_encoder = ScientificPaperEncoder()
        self._scientific_index = ScientificMemoryIndex(self._scientific_encoder)
        self._paper_cache: dict[str, ArxivPaper] = {}
        self._overflow_windows: list[tuple] = []  # (date_from, date_to) pairs that hit 10K cap
        self._storage_dir = _Path("Aura_Memory/arxiv_cache")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time: float = 0.0
        self.stats = ForagerStats()
        _eaf_logger.info("EnhancedArxivForager initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def expand_curiosity_queries(
        self, base_query: str, max_expansions: int = 5,
    ) -> list[str]:
        """
        Curiosity-driven query expansion using scientific memory topology.

        Axiom P1 (Null State is Potential): The arXiv corpus is the latent
        field. Each query is a perturbation. This method generates NEW
        perturbation vectors from the gaps in the existing knowledge topology.

        Axiom P3 (Coherence is Attractor): We expand toward domains that
        are adjacent to but not yet covered by the existing cluster topology.

        Returns a list of expanded query strings derived from the scientific
        memory's domain bundles and detected knowledge gaps.
        """
        queries = [base_query]

        # Check what domains are well-covered vs sparse
        if not self._scientific_index._records:
            return queries

        domain_counts: dict[str, int] = {}
        for rec in self._scientific_index._records.values():
            for domain in rec.slots.get("domain"):
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

        if not domain_counts:
            return queries

        # Sort domains by coverage (ascending = least explored)
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1])

        # Generate expansion queries for underexplored adjacent domains
        # Use the base query combined with underexplored domain terms
        for domain, count in sorted_domains[:max_expansions]:
            if domain and domain != "general":
                expanded = f"{base_query} {domain}"
                if expanded not in queries:
                    queries.append(expanded)

        # Also check for mechanism gaps — domains with papers but few mechanisms
        mechanism_counts: dict[str, int] = {}
        for rec in self._scientific_index._records.values():
            for mech in rec.slots.get("mechanism"):
                mechanism_counts[mech] = mechanism_counts.get(mech, 0) + 1

        for mech, count in sorted(mechanism_counts.items(), key=lambda x: x[1])[:3]:
            if mech and len(queries) < max_expansions + 1:
                expanded = f"{base_query} {mech}"
                if expanded not in queries:
                    queries.append(expanded)

        _eaf_logger.info(
            "Curiosity expansion: %d queries from %d domains, %d mechanisms",
            len(queries), len(domain_counts), len(mechanism_counts),
        )
        return queries[:max_expansions + 1]

    async def forage(self, config: ForagerConfig) -> list[ArxivPaper]:
        """
        Forage arXiv papers matching *config*.

        The requested history is always sliced into bounded date windows.
        This prevents even small result requests from forcing arXiv to sort
        an entire year of matches before returning the first page.

        Papers are processed in async batches and VSA-indexed.
        """
        self.stats = ForagerStats()
        self.stats.start_time = _dt.now()
        self._paper_cache.clear()
        self._overflow_windows.clear()
        self._scientific_index = ScientificMemoryIndex(self._scientific_encoder)
        self._storage_dir = _Path(config.storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        _eaf_logger.info(
            "Starting forage: query=%r  max_total=%d  max_results=%d",
            config.query, config.max_total, config.max_results,
        )

        try:
            # ------------------------------------------------------------------
            # Bounded date windows keep each server-side query tractable.
            # ------------------------------------------------------------------
            now = _dt.now()
            overall_start = now - _td(days=config.max_days_old)
            broad_query = config.query.strip() in {"", "*"}
            window_days = 1 if broad_query else 7
            window_delta = _td(days=window_days)
            max_windows = max(
                1,
                (max(0, int(config.max_days_old)) + window_days - 1)
                // window_days,
            )
            date_windows = []
            cursor = now
            while cursor > overall_start and len(date_windows) < max_windows:
                w_start = max(overall_start, cursor - window_delta)
                date_windows.append((w_start, cursor))
                cursor = w_start
            if not date_windows:
                date_windows = [(overall_start, now)]

            _eaf_logger.info(
                "Date windows: %d  (%d day%s each)",
                len(date_windows), window_days,
                "" if window_days == 1 else "s",
            )

            raw_papers: list[dict] = []
            seen_ids: set = set()
            for wi, (df, dt_) in enumerate(date_windows):
                if len(raw_papers) >= config.max_total:
                    break
                chunk_papers = await self._search_via_urllib(config, df, dt_)
                for p in chunk_papers:
                    if p["paper_id"] not in seen_ids:
                        seen_ids.add(p["paper_id"])
                        raw_papers.append(p)
                _eaf_logger.info(
                    "Window %d/%d [%s → %s]: +%d papers (total: %d)",
                    wi + 1, len(date_windows),
                    df.strftime("%Y-%m-%d"), dt_.strftime("%Y-%m-%d"),
                    len(chunk_papers), len(raw_papers),
                )

            # ------------------------------------------------------------------
            # Fractal subdivision: recursively split overflowed windows
            # Axiom A5: same partitioning at every scale
            # ------------------------------------------------------------------
            _max_subdivision_depth = 4  # prevent infinite recursion
            _subdivision_round = 0
            while self._overflow_windows and _subdivision_round < _max_subdivision_depth:
                _subdivision_round += 1
                overflow_copy = list(self._overflow_windows)
                self._overflow_windows.clear()
                _eaf_logger.info(
                    "Fractal subdivision round %d: %d overflowed windows",
                    _subdivision_round, len(overflow_copy),
                )
                for ow_start, ow_end in overflow_copy:
                    if len(raw_papers) >= config.max_total:
                        break
                    # Split the overflowed window in half
                    if ow_start is not None and ow_end is not None:
                        mid = ow_start + (ow_end - ow_start) / 2
                        sub_windows = [(ow_start, mid), (mid, ow_end)]
                    else:
                        break
                    for sw_start, sw_end in sub_windows:
                        if len(raw_papers) >= config.max_total:
                            break
                        chunk = await self._search_via_urllib(config, sw_start, sw_end)
                        for p in chunk:
                            if p["paper_id"] not in seen_ids:
                                seen_ids.add(p["paper_id"])
                                raw_papers.append(p)
                        _eaf_logger.info(
                            "Subdivision [%s -> %s]: +%d papers (total: %d)",
                            sw_start.strftime("%Y-%m-%d") if sw_start else "?",
                            sw_end.strftime("%Y-%m-%d") if sw_end else "?",
                            len(chunk), len(raw_papers),
                        )

            # ------------------------------------------------------------------
            # Process in async batches; network pacing is handled at fetch time
            # ------------------------------------------------------------------
            for i in range(0, len(raw_papers), config.batch_size):
                batch = raw_papers[i:i + config.batch_size]
                tasks = [self._process_paper_dict(p, config) for p in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

            self.stats.end_time = _dt.now()
            _eaf_logger.info(
                "Forage done: fetched=%d  parsed=%d  stored=%d  errors=%d  %.2f p/s",
                self.stats.papers_fetched,
                self.stats.papers_parsed,
                self.stats.papers_stored,
                self.stats.errors,
                self.stats.papers_per_second,
            )
            return list(self._paper_cache.values())

        except Exception as exc:
            _eaf_logger.error("Forage failed: %s", exc, exc_info=True)
            self.stats.end_time = _dt.now()
            raise

    async def search_similar(
        self, query: str, top_k: int = 5
    ) -> list[ArxivPaper]:
        """
        Search for papers most similar to a query string.

        Automatically loads papers from disk cache if the in-memory cache is empty.
        Performs a vector similarity search and returns matching papers that exist
        in the cache.

        Returns:
            A list of up to `top_k` ArxivPaper objects ranked by similarity to the query.
        """
        if not self._paper_cache:
            await asyncio.to_thread(self._load_disk_cache)
        hits = self._scientific_index.search(query, top_k=top_k)
        results = [
            self._paper_cache[hit.record_id]
            for hit in hits
            if hit.record_id in self._paper_cache
        ]
        _eaf_logger.info(
            "search_similar(%r): %d results from %d indexed papers (%d candidates)",
            query[:50],
            len(results),
            len(self._paper_cache),
            self._scientific_index.last_candidates_considered,
        )
        return results

    async def get_paper(self, paper_id: str) -> ArxivPaper | None:
        """
        Retrieves a paper by ID from cache or disk.

        Returns:
            ArxivPaper if found in memory or on disk, None otherwise.
        """
        if paper_id in self._paper_cache:
            return self._paper_cache[paper_id]

        cache_path = self._storage_dir / f"{paper_id.replace('/', '_')}.json"
        if cache_path.exists():
            try:
                import json as _j
                with open(cache_path, encoding="utf-8") as fh:
                    d = _j.load(fh)
                paper = self._paper_from_dict(d)
                self._paper_cache[paper_id] = paper
                self._scientific_index.add(self._record_for_paper(paper))
                return paper
            except Exception as exc:
                _eaf_logger.error("Disk cache load failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _search_via_urllib(
        self, config: ForagerConfig,
        date_from: _dt | None = None,
        date_to: _dt | None = None,
    ) -> list[dict]:
        """
        Hit the arXiv Atom API with full pagination.

        If *date_from* / *date_to* are given the query is scoped to that
        window so the per-query 10 000 result cap is not hit.
        Loops through pages of ``config.max_results`` until
        ``config.max_total`` papers are collected or the API returns empty.
        """
        # Build the base search query, optionally scoped by date range
        search_terms = f"all:{config.query.strip()}"
        if config.categories:
            category_terms = " OR ".join(
                f"cat:{category}" for category in config.categories
            )
            search_terms = f"({category_terms}) AND ({search_terms})"
        if date_from is not None or date_to is not None:
            # arXiv date-range syntax: submittedDate:[YYYYMMDDHHMM TO YYYYMMDDHHMM]
            df_str = date_from.strftime("%Y%m%d%H%M") if date_from else "*"
            dt_str = date_to.strftime("%Y%m%d%H%M") if date_to else "*"
            search_terms += f" AND submittedDate:[{df_str} TO {dt_str}]"

        NS = "{http://www.w3.org/2005/Atom}"
        ONS = "{http://a9.com/-/spec/opensearch/1.1/}"
        cutoff = _dt.now() - _td(days=config.max_days_old)
        papers: list[dict] = []
        seen_ids: set = set()
        start = 0

        while len(papers) < config.max_total:
            per_page = min(
                max(1, int(config.max_results)),
                _ARXIV_SAFE_PAGE_SIZE,
                config.max_total - len(papers),
            )

            try:
                xml_data, requested_page_size = await self._fetch_arxiv_xml(
                    search_terms,
                    start=start,
                    max_results=per_page,
                    max_retries=3,
                    timeout=30.0,
                    min_delay=config.rate_limit_delay,
                )
            except Exception as exc:
                _eaf_logger.warning(
                    "arXiv query API failed [start=%d]: %s; using OAI-PMH",
                    start, exc,
                )
                return await self._search_via_oai(
                    config, date_from, date_to
                )

            page_papers = 0
            try:
                root = ET.fromstring(xml_data)
                entries = root.findall(f"{NS}entry")
                returned_count = len(entries)

                # Check totalResults from OpenSearch namespace
                total_str = root.findtext(f"{ONS}totalResults", "")
                total_available = int(total_str) if total_str else 0

                for entry in entries:
                    pub_str = entry.findtext(f"{NS}published", "").strip()
                    try:
                        pub_dt = _dt.fromisoformat(pub_str.rstrip("Z"))
                    except ValueError:
                        pub_dt = _dt.now()
                    if pub_dt < cutoff:
                        continue

                    entry_id = entry.findtext(f"{NS}id", "").strip()
                    paper_id = (
                        entry_id.split("/abs/")[-1]
                        if "/abs/" in entry_id
                        else entry_id
                    )
                    if paper_id in seen_ids:
                        continue
                    seen_ids.add(paper_id)

                    papers.append({
                        "paper_id": paper_id,
                        "entry_id": entry_id,
                        "title": (entry.findtext(f"{NS}title") or "").strip(),
                        "abstract": " ".join(
                            (entry.findtext(f"{NS}summary") or "").split()
                        ),
                        "published": pub_dt,
                        "authors": [
                            a.findtext(f"{NS}name", "")
                            for a in entry.findall(f"{NS}author")
                        ],
                        "categories": [
                            t.get("term", "")
                            for t in entry.findall(f"{NS}category")
                        ],
                        "pdf_url": next(
                            (
                                lk.get("href", "")
                                for lk in entry.findall(f"{NS}link")
                                if lk.get("type") == "application/pdf"
                            ),
                            None,
                        ),
                    })
                    self.stats.papers_fetched += 1
                    page_papers += 1

                _eaf_logger.debug(
                    "arXiv page start=%d  got=%d  total_available=%s  collected=%d",
                    start, page_papers, total_str, len(papers),
                )

                # Stop conditions:
                # - no papers on this page (past the end or date-cutoff filtered all)
                # - fewer papers returned than requested AND total_available says we're done
                if returned_count == 0:
                    break
                start += returned_count
                if (
                    returned_count < requested_page_size
                    or (total_available > 0 and start >= total_available)
                ):
                    break

                # Hard cap: arXiv won't return results beyond start=ARXIV_HARD_LIMIT
                # Axiom A5 (Fractal Self-Organization): when a window overflows,
                # recursively subdivide it — the same partitioning at every scale.
                if start >= ForagerConfig._ARXIV_HARD_LIMIT:
                    _eaf_logger.warning(
                        "Hit arXiv 10k hard cap for this date window — "
                        "triggering fractal subdivision."
                    )
                    # Signal the caller to subdivide this window
                    overflow_window = (date_from, date_to)
                    if overflow_window not in self._overflow_windows:
                        self._overflow_windows.append(overflow_window)
                    break

            except Exception as exc:
                _eaf_logger.error("XML parse failed [start=%d]: %s", start, exc)
                break

        return papers

    async def _search_via_oai(
        self,
        config: ForagerConfig,
        date_from: _dt | None,
        date_to: _dt | None,
    ) -> list[dict]:
        """Fallback search over official OAI-PMH metadata, filtered locally."""
        cutoff = _dt.now() - _td(days=config.max_days_old)
        query_terms = [
            "".join(ch for ch in term.lower() if ch.isalnum())
            for term in config.query.split()
        ]
        query_terms = [
            term for term in query_terms
            if term and term not in {"and", "or", "not"}
        ]
        wanted_categories = set(config.categories or ())
        papers: list[dict] = []
        seen_ids: set = set()
        token = None

        for _page in range(20):
            try:
                xml_data = await self._fetch_arxiv_oai_xml(
                    date_from=date_from,
                    date_to=date_to,
                    resumption_token=token,
                    max_retries=3,
                    timeout=60.0,
                    min_delay=config.rate_limit_delay,
                )
                records, token = self._parse_arxiv_oai_records(xml_data)
            except Exception as exc:
                self.stats.errors += 1
                _eaf_logger.error("arXiv OAI-PMH fallback failed: %s", exc)
                break

            for record in records:
                if len(papers) >= config.max_total:
                    break
                if record["paper_id"] in seen_ids:
                    continue
                if record["published"] < cutoff:
                    continue
                if (
                    wanted_categories
                    and not wanted_categories.intersection(
                        record.get("categories", ())
                    )
                ):
                    continue
                searchable = (
                    f"{record.get('title', '')} "
                    f"{record.get('abstract', '')}"
                ).lower()
                if query_terms and not all(
                    term in searchable for term in query_terms
                ):
                    continue
                seen_ids.add(record["paper_id"])
                papers.append(record)
                self.stats.papers_fetched += 1

            if len(papers) >= config.max_total or not token:
                break

        return papers

    async def _process_paper_dict(
        self, raw: dict, config: ForagerConfig
    ) -> None:
        """
        Transform a raw paper dictionary into a cached and indexed ArxivPaper.

        Encodes the paper into a vector and slots using the scientific encoder, caches it in memory, adds it to the search index, and persists it to disk. If a memory palace node is available, also writes the vector to the database. Skips processing if the paper is already cached.

        Parameters:
            raw (dict): Paper data containing paper_id, title, abstract, authors, categories, published, pdf_url, and entry_id.
            config (ForagerConfig): Configuration specifying storage location for disk cache.
        """
        title = str(raw.get("title", "")).strip()
        abstract = " ".join(str(raw.get("abstract", "")).split())
        paper_id = str(raw.get("paper_id", "")).strip()
        if not paper_id:
            paper_id = hashlib.sha256((title + abstract).encode()).hexdigest()[:8].upper()
        if paper_id in self._paper_cache:
            return

        try:
            paper = ArxivPaper(
                paper_id=paper_id,
                title=title,
                authors=raw.get("authors", []),
                abstract=abstract,
                published=raw.get("published", _dt.now()),
                categories=raw.get("categories", []),
                pdf_url=raw.get("pdf_url"),
                full_text=raw.get("full_text") or "",
                metadata={"entry_id": raw.get("entry_id", "")},
            )
            doc_id = f"ARXIV_{paper_id.replace('/', '_')}"
            paper_memory = await self._persist_paper_memory(
                doc_id=doc_id,
                title=paper.title,
                abstract=paper.abstract,
                full_text=paper.full_text or "",
                authors=paper.authors,
                categories=paper.categories,
                published=paper.published.isoformat() if paper.published else "",
                source_url=raw.get("entry_id", ""),
                pdf_url=paper.pdf_url or "",
                metadata={"ingest_path": "EnhancedArxivForager"},
            )
            paper.metadata.update({
                "paper_memory_doc_id": paper_memory.doc_id,
                "paper_memory_ledger": self.paper_memory_ledger_path,
                "paper_memory_header": paper_memory.holographic_header,
                "paper_memory_points": list(paper_memory.three_main_points),
                "full_text_sha256": paper_memory.full_text_sha256,
            })
            record = self._record_for_paper(paper)
            paper.vector = record.vector
            paper.slots = record.slots.to_jsonable()
            self._paper_cache[paper_id] = paper
            self._scientific_index.add(record)
            self.stats.papers_parsed += 1

            # Persist to existing memory palace via node reference (same as ArXivForager)
            if self.node is not None and getattr(self.node, "memory_palace", None):
                text_block = record_to_trace_content(paper_memory)
                blob = pack_vector(record.vector)
                try:
                    conn = self.node.memory_palace.conn
                    await conn.execute(
                        "INSERT OR REPLACE INTO traces "
                        "(id, content, tier, timestamp, tags, vector_blob) "
                        "VALUES (?, ?, 'CRYSTAL', ?, 'Scientific VSA v1', ?)",
                        (doc_id, text_block, _dt.now().isoformat(), blob),
                    )
                    await conn.commit()
                    self.stats.papers_stored += 1
                except Exception as db_exc:
                    _eaf_logger.warning("DB write skipped: %s", db_exc)

            # Disk cache includes the compact 1,250-byte packed vector.
            await self._save_to_disk(paper, config.storage_dir)

        except Exception as exc:
            self.stats.errors += 1
            _eaf_logger.error("Paper processing failed [%s]: %s", paper_id, exc)

    def _generate_vector(self, paper: ArxivPaper) -> np.ndarray | None:
        """
        Encode a vector for a paper and update its slots.

        Returns:
        	The encoded vector, or `None` if encoding yields no vector.
        """
        record = self._record_for_paper(paper)
        paper.slots = record.slots.to_jsonable()
        return record.vector

    def _record_for_paper(self, paper: ArxivPaper) -> ScientificRecord:
        """
        Obtains a ScientificRecord for a paper, reusing cached vectors if available.

        If the paper has cached vector and slots data, returns a reconstructed record using those values. Otherwise, encodes a fresh record from the paper's title, abstract, categories, and publication year.

        Parameters:
        	paper (ArxivPaper): The paper to encode or reconstruct.

        Returns:
        	ScientificRecord: The paper's vector encoding and semantic slots.
        """
        if paper.vector is not None and paper.slots:
            return ScientificRecord(
                paper.paper_id,
                paper.title,
                paper.abstract,
                ScientificSlots.from_jsonable(paper.slots),
                np.asarray(paper.vector, dtype=np.int8),
                paper.metadata,
            )
        return self._scientific_encoder.encode_document(
            paper.paper_id,
            paper.title,
            paper.abstract,
            categories=paper.categories,
            year=paper.published.year if paper.published else None,
            metadata=paper.metadata,
        )

    def _paper_from_dict(self, data: dict) -> ArxivPaper:
        """
        Reconstruct an ArxivPaper from cached JSON data.

        Parameters:
            data (dict): Serialized paper dictionary from disk cache

        Returns:
            ArxivPaper: The deserialized paper with vector and slots
        """
        paper = ArxivPaper(
            paper_id=data["paper_id"],
            title=data["title"],
            authors=data.get("authors", []),
            abstract=data.get("abstract", ""),
            published=_dt.fromisoformat(data["published"]),
            categories=data.get("categories", []),
            pdf_url=data.get("pdf_url"),
            slots=data.get("slots", {}),
            metadata=data.get("metadata", {}),
        )
        packed = data.get("vector")
        if packed:
            try:
                paper.vector = unpack_vector(base64.b64decode(packed))
            except Exception:
                paper.vector = None
        if paper.vector is None or not paper.slots:
            paper.vector = self._generate_vector(paper)
        return paper

    def _load_disk_cache(self) -> None:
        """
        Load cached papers from disk storage and index them.

        Loads papers from the storage directory and makes them available in the
        in-memory cache for similarity search. Existing cached papers are skipped,
        and load failures are silently logged at debug level.
        """
        for path in self._storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                paper = self._paper_from_dict(data)
                if paper.paper_id in self._paper_cache:
                    continue
                self._paper_cache[paper.paper_id] = paper
                self._scientific_index.add(self._record_for_paper(paper))
            except Exception as exc:
                _eaf_logger.debug("Disk cache entry skipped [%s]: %s", path, exc)

    async def _save_to_disk(self, paper: ArxivPaper, storage_dir: str) -> None:
        """Persist paper metadata and its compact packed scientific vector."""
        try:
            import json as _j
            _Path(storage_dir).mkdir(parents=True, exist_ok=True)
            safe_id = paper.paper_id.replace("/", "_")
            path = _Path(storage_dir) / f"{safe_id}.json"
            d = paper.to_dict()
            path.write_text(_j.dumps(d, indent=2), encoding="utf-8")
        except Exception as exc:
            _eaf_logger.debug("Disk save skipped: %s", exc)
