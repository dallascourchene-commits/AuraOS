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
import time
import urllib.error
from urllib.parse import urlencode
import urllib.request
import xml.etree.ElementTree as ET

import numpy as np

from aura_scientific_memory import (
    ScientificMemoryIndex,
    ScientificPaperEncoder,
    ScientificRecord,
    ScientificSlots,
    pack_vector,
    unpack_vector,
)

_SCIENTIFIC_ENCODER = ScientificPaperEncoder()


def _scientific_record(
    record_id: str,
    title: str,
    abstract: str,
    *,
    categories=(),
    published=None,
):
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
        self.node = node_ref  # Bind the main node reference

    async def fetch_latest_paper(self, topic: str, max_retries: int = 3, timeout: float = 12.0) -> str:
        """Hits the arXiv API with an asynchronous, non-blocking retry loop, HTTPS, and custom browser headers."""
        query = urllib.parse.quote_plus(topic)
        url = f"https://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=1&sortBy=relevance"
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Moto G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "application/xml,text/xml",
            "Connection": "close"
        }

        xml_data = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                response = await asyncio.to_thread(urllib.request.urlopen, req, timeout=timeout)
                xml_data = response.read()
                break
            except (urllib.error.URLError, TimeoutError, ConnectionResetError) as e:
                if attempt == max_retries - 1:
                    return f"arXiv API connection failed after {max_retries} attempts: {e}"
                backoff = (2 ** attempt) * 0.5 + np.random.uniform(0, 0.1)
                print(f"[⚠️ ARXIV RETRY] Timeout or connection error: {e}. Retrying in {backoff:.2f}s...")
                await asyncio.sleep(backoff)

        if not xml_data:
            return "arXiv API returned empty payload or failed entirely."

        try:
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            if not entries:
                return f"No relevant arXiv papers found for: {topic}"

            entry = entries[0]
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
            summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
            summary = " ".join(summary.split())
            full_text = f"TITLE: {title} | ABSTRACT: {summary}"

            if self.node is not None:
                record = _scientific_record("", title, summary)
                blob_data = pack_vector(record.vector)
                try:
                    conn = self.node.memory_palace.conn
                    trace_id = f"ARXIV_{hashlib.sha256(full_text.encode()).hexdigest()[:8].upper()}"
                    await conn.execute(
                        "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) VALUES (?, ?, 'CRYSTAL', ?, 'Scientific VSA v1', ?)",
                        (trace_id, full_text, datetime.now().isoformat(), blob_data)
                    )
                    await conn.commit()
                except Exception as e:
                    print(f"[-] Local DB write failed: {e}")

            return f"TITLE: {title}\nABSTRACT: {summary}"
        except Exception as e:
            return f"arXiv processing failure: {e}"

    async def upgraded_arxiv_backtracker(self, max_results: int = 100, max_retries: int = 3, timeout: float = 12.0) -> bool:
        """
        Chronologically walks backwards through arXiv computer science submissions.

        The arXiv API hard-caps pagination at start=9999 (≈10 000 total results).
        When the crawler hits that wall it automatically resets the offset to 0
        and narrows the date window — so the crawl can continue indefinitely
        through earlier time periods without ever getting stuck.
        """
        if self.node is None or not self.node.memory_palace.conn:
            print("[-] Backtracker Error: No active database connection linked to Forager.")
            return False

        conn = self.node.memory_palace.conn

        # 1. Load persistent crawler state
        crawler_state = {
            'crawl_offset_index': 0,
            'last_crawl_time': 0.0,
            'crawl_window_end': None,   # ISO date str upper bound (None = wide open)
        }
        try:
            async with conn.execute(
                "SELECT content FROM traces WHERE id = 'ARXIV_CRAWLER_STATE';"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    loaded = json.loads(row[0])
                    crawler_state.update(loaded)
            self.node.runtime_metrics['arxiv_crawler_state'] = crawler_state
        except Exception:
            pass

        # 2. Temporal pacing (3.5 s arXiv compliance)
        current_time = time.time()
        elapsed_time = current_time - crawler_state.get('last_crawl_time', 0.0)
        if elapsed_time < 3.5:
            sleep_needed = 3.5 - elapsed_time
            print(f"[⏳ TEMPORAL PACING] arXiv compliance delay active. Sleeping for {sleep_needed:.2f}s...")
            await asyncio.sleep(sleep_needed)

        current_offset = crawler_state.get('crawl_offset_index', 0)
        window_end = crawler_state.get('crawl_window_end')

        # ---- Build query with optional date-window filter ----
        search_query = 'cat:cs.*'
        if window_end:
            # Scope to papers submitted on or before window_end
            search_query += f'+AND+submittedDate:[*+TO+{window_end}]'

        BASE_URL = 'https://export.arxiv.org/api/query'
        params = {
            'search_query': search_query,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending',
            'max_results': max_results,
            'start': current_offset,
        }
        query_url = f"{BASE_URL}?{urlencode(params)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Moto G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "application/xml,text/xml",
            "Connection": "close",
        }

        # 3. Fetch with retries — detect 10k-cap errors
        xml_data = None
        for attempt in range(max_retries):
            try:
                print(f"[*] Fetching arXiv CS backlog at offset {current_offset}"
                      + (f"  (window ≤ {window_end})" if window_end else "")
                      + "...")
                req = urllib.request.Request(query_url, headers=headers)
                response = await asyncio.to_thread(urllib.request.urlopen, req, timeout=timeout)
                xml_data = response.read()
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionResetError) as e:
                err_str = str(e)
                is_500 = '500' in err_str or 'Internal Server Error' in err_str

                if attempt == max_retries - 1:
                    # ---- 10k hard-cap recovery: reset offset, narrow date window ----
                    if is_500 and current_offset >= 9_000:
                        print("[🔄 10K CAP] arXiv refuses start>=10k. "
                              "Resetting offset to 0 and narrowing date window...")
                        self._advance_backtracker_window(crawler_state)
                        crawler_state['crawl_offset_index'] = 0
                        crawler_state['last_crawl_time'] = time.time()
                        await conn.execute(
                            "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) "
                            "VALUES ('ARXIV_CRAWLER_STATE', ?, 'SYSTEM_STATE', ?, "
                            "'arXiv Backtracker Crawler State Offset', NULL)",
                            (json.dumps(crawler_state), datetime.now().isoformat()),
                        )
                        await conn.commit()
                        print("[+] Date window advanced. Run !backtrack again to continue.")
                        return True  # state saved, caller re-invokes

                    print(f"[-] Backtracker network failed after {max_retries} attempts: {e}")
                    return False

                backoff = (2 ** attempt) * 1.5 + np.random.uniform(0, 0.1)
                print(f"[⚠️ ARXIV RETRY] Connection error: {e}. Retrying in {backoff:.2f}s...")
                await asyncio.sleep(backoff)

        if not xml_data:
            return False

        # 4. Parse and ingest
        try:
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')

            if not entries:
                if current_offset > 0:
                    # We're past the last page for this window — advance the window
                    print("[🔄 WINDOW EDGE] No more results at this offset. "
                          "Narrowing date window to continue...")
                    self._advance_backtracker_window(crawler_state)
                    crawler_state['crawl_offset_index'] = 0
                else:
                    # offset == 0 and no entries: either truly done or window is empty
                    if window_end:
                        print("[🔄 EMPTY WINDOW] No papers in this date range. "
                              "Advancing window further back...")
                        self._advance_backtracker_window(crawler_state)
                        crawler_state['crawl_offset_index'] = 0
                    else:
                        print("[+] Backtracker reached the absolute end of the arXiv CS timeline.")
                        return False

                crawler_state['last_crawl_time'] = time.time()
                await conn.execute(
                    "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) "
                    "VALUES ('ARXIV_CRAWLER_STATE', ?, 'SYSTEM_STATE', ?, "
                    "'arXiv Backtracker Crawler State Offset', NULL)",
                    (json.dumps(crawler_state), datetime.now().isoformat()),
                )
                await conn.commit()
                print("[+] Date window advanced. Run !backtrack again to continue.")
                return True

            ingest_rows: list[tuple] = []
            stamp_ts = datetime.now().isoformat()
            earliest_published = None

            for entry in entries:
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
                summary = " ".join(summary.split())
                published = entry.find('{http://www.w3.org/2005/Atom}published').text.strip()

                # Track the earliest pub date in this batch for window advancement
                if earliest_published is None or published < earliest_published:
                    earliest_published = published

                text_block = f"TITLE: {title} | ABSTRACT: {summary} | PUBLISHED: {published}"
                engram_hash = f"ARXIV_{hashlib.sha256(text_block.encode()).hexdigest()[:8].upper()}"
                record = _scientific_record(
                    engram_hash,
                    title,
                    summary,
                    published=published,
                )
                blob_data = pack_vector(record.vector)
                ingest_rows.append(
                    (engram_hash, text_block, stamp_ts, blob_data)
                )

            if ingest_rows:
                await conn.executemany(
                    "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) "
                    "VALUES (?, ?, 'CRYSTAL', ?, 'Scientific VSA v1', ?)",
                    ingest_rows,
                )
            stamped_count = len(ingest_rows)

            # 5. Advance state
            new_offset = current_offset + len(entries)

            # If the new offset is dangerously close to the 10k cap, pre-emptively
            # advance the window so the next call doesn't hit the wall
            if new_offset >= 9_500:
                print("[🔄 10K GUARD] Approaching arXiv 10k cap. "
                      "Advancing date window pre-emptively...")
                self._advance_backtracker_window(crawler_state, earliest_published)
                crawler_state['crawl_offset_index'] = 0
            else:
                crawler_state['crawl_offset_index'] = new_offset

            crawler_state['last_crawl_time'] = time.time()

            await conn.execute(
                "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) "
                "VALUES ('ARXIV_CRAWLER_STATE', ?, 'SYSTEM_STATE', ?, "
                "'arXiv Backtracker Crawler State Offset', NULL)",
                (json.dumps(crawler_state), datetime.now().isoformat()),
            )
            await conn.commit()

            print(f"[+] [ARXIV BACKTRACKER] Successfully vectorized and ingested {stamped_count} papers.")
            print(f"    Offset: {new_offset}  |  Window end: {window_end or 'unbounded'}")
            return True

        except Exception as e:
            print(f"[-] Backtracker processing error: {e}")
            return False

    def _advance_backtracker_window(self, crawler_state: dict, earliest_published: str = None) -> None:
        """
        Push the date window further into the past so the next crawl cycle
        can continue beyond the arXiv 10k hard cap.

        If *earliest_published* is given (from the most recent batch) the
        window is set to one day before that paper's date.  Otherwise the
        existing window_end is pushed back by 30 days.
        """

        if earliest_published:
            try:
                pub_dt = datetime.fromisoformat(earliest_published.rstrip("Z"))
                new_end = pub_dt - timedelta(days=1)
            except (ValueError, TypeError):
                new_end = datetime.now() - timedelta(days=30)
        else:
            old_end = crawler_state.get('crawl_window_end')
            if old_end:
                try:
                    old_dt = datetime.fromisoformat(str(old_end).rstrip("Z"))
                    new_end = old_dt - timedelta(days=30)
                except (ValueError, TypeError):
                    new_end = datetime.now() - timedelta(days=30)
            else:
                # First time narrowing: start 30 days ago
                new_end = datetime.now() - timedelta(days=30)

        crawler_state['crawl_window_end'] = new_end.strftime("%Y%m%d%H%M")
        print(f"[🪟 WINDOW] crawl_window_end set to {crawler_state['crawl_window_end']}"
              + (f"  (earliest paper: {earliest_published})" if earliest_published else ""))


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
from typing import Dict as _Dict
from typing import List as _List
from typing import Optional as _Optional

_eaf_logger = _logging.getLogger("aura.arxiv_forager")


@_dc
class ArxivPaper:
    """Structured representation of an arXiv paper with VSA vector support."""
    paper_id: str
    title: str
    authors: _List[str]
    abstract: str
    published: _dt
    categories: _List[str]
    pdf_url: _Optional[str] = None
    full_text: _Optional[str] = None
    vector: _Optional[np.ndarray] = None
    slots: _Dict = _dcfield(default_factory=dict)
    metadata: _Dict = _dcfield(default_factory=dict)

    def to_dict(self) -> dict:
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
    max_results: int = 100               # per-page results (arXiv allows <=2000)
    categories: _Optional[_List[str]] = None
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
    start_time: _Optional[_dt] = None
    end_time: _Optional[_dt] = None

    @property
    def duration(self) -> _Optional[_td]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def papers_per_second(self) -> float:
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
        super().__init__(node_ref)

        self._scientific_encoder = ScientificPaperEncoder()
        self._scientific_index = ScientificMemoryIndex(self._scientific_encoder)
        self._paper_cache: _Dict[str, ArxivPaper] = {}
        self._storage_dir = _Path("Aura_Memory/arxiv_cache")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time: float = 0.0
        self.stats = ForagerStats()
        _eaf_logger.info("EnhancedArxivForager initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def forage(self, config: ForagerConfig) -> _List[ArxivPaper]:
        """
        Forage arXiv papers matching *config*.

        When ``config.max_total`` exceeds the arXiv 10 000 hard cap the
        date range is automatically sliced into narrower windows so the
        API never returns more than ~5 000 results per window — well
        under the limit.

        Papers are processed in async batches and VSA-indexed.
        """
        self.stats = ForagerStats()
        self.stats.start_time = _dt.now()
        self._paper_cache.clear()
        self._scientific_index = ScientificMemoryIndex(self._scientific_encoder)
        self._storage_dir = _Path(config.storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        _eaf_logger.info(
            "Starting forage: query=%r  max_total=%d  max_results=%d",
            config.query, config.max_total, config.max_results,
        )

        try:
            # ------------------------------------------------------------------
            # Date-range partitioning to bypass the arXiv 10k hard cap
            # ------------------------------------------------------------------
            now = _dt.now()
            overall_start = now - _td(days=config.max_days_old)

            # If the total we want is under the hard cap, do a single query.
            # Otherwise slice into windows that target ~5k results each.
            if config.max_total <= ForagerConfig._ARXIV_HARD_LIMIT:
                date_windows = [(overall_start, now)]
            else:
                # Estimate: how many windows do we need?
                # Heuristic: ~5k papers per window to stay safely under 10k
                safe_per_window = 5_000
                total_wanted = min(config.max_total, 1_000_000)
                num_windows = max(1, total_wanted // safe_per_window)
                window_delta = _td(days=max(1, config.max_days_old // num_windows))
                date_windows = []
                cursor = now
                while cursor > overall_start and len(date_windows) < 200:
                    w_start = cursor - window_delta
                    if w_start < overall_start:
                        w_start = overall_start
                    date_windows.append((w_start, cursor))
                    cursor = w_start
                    if w_start <= overall_start:
                        break

            _eaf_logger.info(
                "Date windows: %d  (target ~%d papers/window)",
                len(date_windows),
                safe_per_window if config.max_total > ForagerConfig._ARXIV_HARD_LIMIT
                else config.max_total,
            )

            raw_papers: _List[dict] = []
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
                # Rate-limit between date windows
                if wi + 1 < len(date_windows) and chunk_papers:
                    await asyncio.sleep(config.rate_limit_delay)

            # ------------------------------------------------------------------
            # Process in async batches with rate-limit spacing
            # ------------------------------------------------------------------
            for i in range(0, len(raw_papers), config.batch_size):
                batch = raw_papers[i:i + config.batch_size]
                tasks = [self._process_paper_dict(p, config) for p in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

                if i + config.batch_size < len(raw_papers):
                    await asyncio.sleep(config.rate_limit_delay)

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
    ) -> _List[ArxivPaper]:
        """
        Return the *top_k* most similar cached papers to *query*.

        Uses the same structured encoder as ingestion. Missing query slots
        behave as wildcards; hierarchy and LSH reduce exact comparisons.
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

    async def get_paper(self, paper_id: str) -> _Optional[ArxivPaper]:
        """Get a paper by ID from cache or disk."""
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
        date_from: _Optional[_dt] = None,
        date_to: _Optional[_dt] = None,
    ) -> _List[dict]:
        """
        Hit the arXiv Atom API with full pagination.

        If *date_from* / *date_to* are given the query is scoped to that
        window so the per-query 10 000 result cap is not hit.
        Loops through pages of ``config.max_results`` until
        ``config.max_total`` papers are collected or the API returns empty.
        """
        import xml.etree.ElementTree as _ET

        # Build the base search query, optionally scoped by date range
        search_terms = f"all:{urllib.parse.quote_plus(config.query)}"
        if date_from is not None or date_to is not None:
            # arXiv date-range syntax: submittedDate:[YYYYMMDDHHMM TO YYYYMMDDHHMM]
            df_str = date_from.strftime("%Y%m%d%H%M") if date_from else "*"
            dt_str = date_to.strftime("%Y%m%d%H%M") if date_to else "*"
            search_terms += (
                f"+AND+submittedDate:[{df_str}+TO+{dt_str}]"
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 10; Moto G) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            ),
            "Accept": "application/xml,text/xml",
            "Connection": "close",
        }

        NS = "{http://www.w3.org/2005/Atom}"
        ONS = "{http://a9.com/-/spec/opensearch/1.1/}"
        cutoff = _dt.now() - _td(days=config.max_days_old)
        papers: _List[dict] = []
        seen_ids: set = set()
        start = 0

        while len(papers) < config.max_total:
            per_page = min(config.max_results, config.max_total - len(papers))
            url = (
                f"https://export.arxiv.org/api/query"
                f"?search_query={search_terms}"
                f"&start={start}&max_results={per_page}"
                f"&sortBy=submittedDate&sortOrder=descending"
            )

            xml_data = None
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers=headers)
                    response = await asyncio.to_thread(
                        urllib.request.urlopen, req, timeout=12.0
                    )
                    xml_data = response.read()
                    break
                except Exception as exc:
                    if attempt == 2:
                        _eaf_logger.error(
                            "arXiv search failed [start=%d]: %s", start, exc
                        )
                        return papers  # return what we have so far
                    await asyncio.sleep((2 ** attempt) * 0.5)

            if not xml_data:
                break

            page_papers = 0
            try:
                root = _ET.fromstring(xml_data)

                # Check totalResults from OpenSearch namespace
                total_str = root.findtext(f"{ONS}totalResults", "")
                total_available = int(total_str) if total_str else 0

                for entry in root.findall(f"{NS}entry"):
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
                            for t in entry.findall(
                                "{http://arxiv.org/schemas/atom}primary_category"
                            )
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
                if page_papers == 0:
                    break
                if page_papers < per_page and start + page_papers >= total_available:
                    break

                # Hard cap: arXiv won't return results beyond start=ARXIV_HARD_LIMIT
                if start + per_page >= ForagerConfig._ARXIV_HARD_LIMIT:
                    _eaf_logger.warning(
                        "Hit arXiv 10k hard cap for this date window — "
                        "narrower date chunks are needed for more results."
                    )
                    break

            except Exception as exc:
                _eaf_logger.error("XML parse failed [start=%d]: %s", start, exc)
                break

            start += per_page

            # Rate-limit pacing between pages
            if start < config.max_total and page_papers > 0:
                await asyncio.sleep(config.rate_limit_delay)

        return papers

    async def _process_paper_dict(
        self, raw: dict, config: ForagerConfig
    ) -> None:
        """Process a single paper dict: vectorise, cache, persist."""
        paper_id = raw.get("paper_id", "")
        if paper_id in self._paper_cache:
            return

        try:
            paper = ArxivPaper(
                paper_id=paper_id,
                title=raw["title"],
                authors=raw.get("authors", []),
                abstract=raw.get("abstract", ""),
                published=raw.get("published", _dt.now()),
                categories=raw.get("categories", []),
                pdf_url=raw.get("pdf_url"),
                metadata={"entry_id": raw.get("entry_id", "")},
            )
            record = self._record_for_paper(paper)
            paper.vector = record.vector
            paper.slots = record.slots.to_jsonable()
            self._paper_cache[paper_id] = paper
            self._scientific_index.add(record)
            self.stats.papers_parsed += 1

            # Persist to existing memory palace via node reference (same as ArXivForager)
            if self.node is not None and getattr(self.node, "memory_palace", None):
                text_block = f"TITLE: {paper.title} | ABSTRACT: {paper.abstract}"
                blob = pack_vector(record.vector)
                engram = f"ARXIV_{hashlib.sha256(text_block.encode()).hexdigest()[:8].upper()}"
                try:
                    conn = self.node.memory_palace.conn
                    await conn.execute(
                        "INSERT OR REPLACE INTO traces "
                        "(id, content, tier, timestamp, tags, vector_blob) "
                        "VALUES (?, ?, 'CRYSTAL', ?, 'Scientific VSA v1', ?)",
                        (engram, text_block, _dt.now().isoformat(), blob),
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

    def _generate_vector(self, paper: ArxivPaper) -> _Optional[np.ndarray]:
        """Generate the shared structured 10,000-D vector for a paper."""
        record = self._record_for_paper(paper)
        paper.slots = record.slots.to_jsonable()
        return record.vector

    def _record_for_paper(self, paper: ArxivPaper) -> ScientificRecord:
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
