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
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlencode

import numpy as np

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
                phasor_wave = self.node.polysynthetic_vram_compress(full_text)
                blob_data = np.array(phasor_wave, dtype=np.complex64).tobytes()
                try:
                    conn = self.node.memory_palace.conn
                    trace_id = f"ARXIV_{hashlib.sha256(full_text.encode()).hexdigest()[:8].upper()}"
                    await conn.execute(
                        "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) VALUES (?, ?, 'CRYSTAL', ?, 'Academic arXiv Paper Ingest', ?)",
                        (trace_id, full_text, datetime.now().isoformat(), blob_data)
                    )
                    await conn.commit()
                except Exception as e:
                    print(f"[-] Local DB write failed: {e}")
            
            return f"TITLE: {title}\nABSTRACT: {summary}"
        except Exception as e:
            return f"arXiv processing failure: {e}"

    async def upgraded_arxiv_backtracker(self, max_results: int = 20, max_retries: int = 3, timeout: float = 12.0) -> bool:
        """
        Chronologically walks backwards through arXiv computer science submissions.
        Uses direct, non-blocking DB commits and enforces a strict 3.5s rate-limit delay.
        """
        if self.node is None or not self.node.memory_palace.conn:
            print("[-] Backtracker Error: No active database connection linked to Forager.")
            return False

        conn = self.node.memory_palace.conn

        # 1. Load persistent crawler state directly from her database
        crawler_state = {'crawl_offset_index': 0, 'last_crawl_time': 0.0}
        try:
            async with conn.execute("SELECT content FROM traces WHERE id = 'ARXIV_CRAWLER_STATE';") as cursor:
                row = await cursor.fetchone()
                if row:
                    crawler_state = json.loads(row[0])
            self.node.runtime_metrics['arxiv_crawler_state'] = crawler_state
        except Exception:
            pass

        # 2. Strict Temporal Pacing Guard (Enforces 3.5-second arXiv compliance delay)
        current_time = time.time()
        elapsed_time = current_time - crawler_state.get('last_crawl_time', 0.0)
        if elapsed_time < 3.5:
            sleep_needed = 3.5 - elapsed_time
            print(f"[⏳ TEMPORAL PACING] arXiv compliance delay active. Sleeping for {sleep_needed:.2f}s...")
            await asyncio.sleep(sleep_needed)
            current_time = time.time()

        current_offset = crawler_state.get('crawl_offset_index', 0)
        BASE_URL = 'https://export.arxiv.org/api/query'
        params = {
            'search_query': 'cat:cs.*',
            'sortBy': 'submittedDate',
            'sortOrder': 'descending',
            'max_results': max_results,
            'start': current_offset
        }
        query_url = f"{BASE_URL}?{urlencode(params)}"
        
        xml_data = None
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Moto G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "application/xml,text/xml",
            "Connection": "close"
        }
        for attempt in range(max_retries):
            try:
                print(f"[*] Fetching arXiv CS backlog at offset: {current_offset}...")
                req = urllib.request.Request(query_url, headers=headers)
                response = await asyncio.to_thread(urllib.request.urlopen, req, timeout=timeout)
                xml_data = response.read()
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionResetError) as e:
                if attempt == max_retries - 1:
                    print(f"[-] Backtracker network failed after {max_retries} attempts: {e}")
                    return False
                backoff = (2 ** attempt) * 1.5 + np.random.uniform(0, 0.1)
                print(f"[⚠️ ARXIV RETRY] Connection error: {e}. Retrying in {backoff:.2f}s...")
                await asyncio.sleep(backoff)

        if not xml_data:
            return False

        try:
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            if not entries:
                print("[+] Backtracker reached the absolute end of the arXiv CS timeline.")
                return False

            ingest_rows: list[tuple] = []
            stamp_ts = datetime.now().isoformat()
            for entry in entries:
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
                summary = " ".join(summary.split())
                published = entry.find('{http://www.w3.org/2005/Atom}published').text.strip()

                text_block = f"TITLE: {title} | ABSTRACT: {summary} | PUBLISHED: {published}"
                phasor_wave = self.node.polysynthetic_vram_compress(text_block)
                blob_data = np.array(phasor_wave, dtype=np.complex64).tobytes()
                engram_hash = f"ARXIV_{hashlib.sha256(text_block.encode()).hexdigest()[:8].upper()}"
                ingest_rows.append(
                    (engram_hash, text_block, stamp_ts, blob_data)
                )

            if ingest_rows:
                await conn.executemany(
                    "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) "
                    "VALUES (?, ?, 'CRYSTAL', ?, 'Academic arXiv Paper Ingest', ?)",
                    ingest_rows,
                )
            stamped_count = len(ingest_rows)

            # Update and persist crawler offset state inside database
            crawler_state['crawl_offset_index'] = current_offset + len(entries)
            crawler_state['last_crawl_time'] = time.time()
            
            await conn.execute(
                "INSERT OR REPLACE INTO traces (id, content, tier, timestamp, tags, vector_blob) VALUES ('ARXIV_CRAWLER_STATE', ?, 'SYSTEM_STATE', ?, 'arXiv Backtracker Crawler State Offset', NULL)",
                (json.dumps(crawler_state), datetime.now().isoformat())
            )
            await conn.commit()
            
            print(f"[+] [ARXIV BACKTRACKER] Successfully vectorized and ingested {stamped_count} papers.")
            print(f"    New crawl timeline offset index: {crawler_state['crawl_offset_index']}")
            return True

        except Exception as e:
            print(f"[-] Backtracker processing error: {e}")
            return False


# =============================================================================
# ENHANCED ARXIV FORAGER — VSA storage, async, rate-limiting, similarity search
# Addresses DEEP_AUDIT_REPORT: no async processing, no AuraOS VSA integration,
# no error handling, no connection to existing arxiv_forager.py.
# Extends ArXivForager so existing aura_node.py code continues to work.
# =============================================================================

import re as _re
import logging as _logging
from dataclasses import dataclass as _dc, field as _dcfield
from datetime import datetime as _dt, timedelta as _td
from pathlib import Path as _Path
from typing import List as _List, Optional as _Optional, Dict as _Dict, Set as _Set

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
            "metadata": self.metadata,
        }


@_dc
class ForagerConfig:
    """Configuration for the enhanced arXiv forager."""
    query: str
    max_results: int = 50
    categories: _Optional[_List[str]] = None
    max_days_old: int = 365
    batch_size: int = 10
    rate_limit_delay: float = 3.5        # arXiv compliance: 3.5 s between batches
    storage_dir: str = "Aura_Memory/arxiv_cache"


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


_STOPWORDS: _Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "be", "been",
    "this", "that", "these", "those", "we", "they", "our", "their",
}


class EnhancedArxivForager(ArXivForager):
    """
    Enhanced arXiv forager with VSA storage and async processing.

    Extends the existing ArXivForager (so aura_node.py's ArXivForager(self)
    calls still work) and adds:
    - Per-paper AuraHyperdimensionalCore vector indexing
    - Async batch processing with rate-limiting
    - Cosine similarity search over the in-memory VSA index
    - Disk cache for parsed papers (JSON, no vector)
    - Structured logging

    Usage
    -----
        forager = EnhancedArxivForager(node_ref)
        papers  = await forager.forage(ForagerConfig(query="quantum ML"))
        similar = await forager.search_similar("quantum neural network")
    """

    def __init__(self, node_ref=None) -> None:
        super().__init__(node_ref)

        # Import HDC core lazily to avoid circular imports at module load time
        try:
            from aura_core import AuraHyperdimensionalCore as _HDC
            self._hdc = _HDC()
        except Exception:
            self._hdc = None

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

        Uses the existing fetch_latest_paper / upgraded_arxiv_backtracker
        infrastructure for network access, adds VSA indexing on top.
        """
        self.stats = ForagerStats()
        self.stats.start_time = _dt.now()

        _eaf_logger.info(
            "Starting forage: query=%r  max=%d", config.query, config.max_results
        )

        try:
            raw_papers = await self._search_via_urllib(config)

            # Process in batches with rate-limit spacing
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

        Uses cosine similarity over 10,000-D HDC vectors — O(N) scan
        (N = len(paper_cache), typically small under 4 GB ceiling).
        """
        if not self._hdc:
            _eaf_logger.warning("HDC core not available; returning empty results")
            return []

        q_vec = self._hdc.encode_text(self._preprocess(query))
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        sims: _List[tuple] = []
        for pid, paper in self._paper_cache.items():
            if paper.vector is not None:
                p_norm = np.linalg.norm(paper.vector)
                if p_norm > 0:
                    sim = float(np.dot(q_vec, paper.vector) / (q_norm * p_norm))
                    sims.append((pid, sim))

        sims.sort(key=lambda x: x[1], reverse=True)
        results = [self._paper_cache[pid] for pid, _ in sims[:top_k]]
        _eaf_logger.info(
            "search_similar(%r): %d results from %d indexed papers",
            query[:50],
            len(results),
            len(self._paper_cache),
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
                paper = ArxivPaper(
                    paper_id=d["paper_id"],
                    title=d["title"],
                    authors=d["authors"],
                    abstract=d["abstract"],
                    published=_dt.fromisoformat(d["published"]),
                    categories=d["categories"],
                    pdf_url=d.get("pdf_url"),
                    metadata=d.get("metadata", {}),
                )
                if self._hdc:
                    paper.vector = self._generate_vector(paper)
                self._paper_cache[paper_id] = paper
                return paper
            except Exception as exc:
                _eaf_logger.error("Disk cache load failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _search_via_urllib(
        self, config: ForagerConfig
    ) -> _List[dict]:
        """
        Hit the arXiv Atom API using the existing urllib infrastructure
        and return a list of raw paper dicts.
        """
        import xml.etree.ElementTree as _ET
        query = urllib.parse.quote_plus(config.query)
        url = (
            f"https://export.arxiv.org/api/query"
            f"?search_query=all:{query}"
            f"&start=0&max_results={config.max_results}"
            f"&sortBy=submittedDate&sortOrder=descending"
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
                    _eaf_logger.error("arXiv search failed: %s", exc)
                    return []
                await asyncio.sleep((2 ** attempt) * 0.5)

        if not xml_data:
            return []

        papers: _List[dict] = []
        try:
            NS = "{http://www.w3.org/2005/Atom}"
            root = _ET.fromstring(xml_data)
            cutoff = _dt.now() - _td(days=config.max_days_old)
            for entry in root.findall(f"{NS}entry"):
                pub_str = entry.findtext(f"{NS}published", "").strip()
                try:
                    pub_dt = _dt.fromisoformat(pub_str.rstrip("Z"))
                except ValueError:
                    pub_dt = _dt.now()
                if pub_dt < cutoff:
                    continue
                entry_id = entry.findtext(f"{NS}id", "").strip()
                paper_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id
                papers.append({
                    "paper_id": paper_id,
                    "entry_id": entry_id,
                    "title": (entry.findtext(f"{NS}title") or "").strip(),
                    "abstract": " ".join((entry.findtext(f"{NS}summary") or "").split()),
                    "published": pub_dt,
                    "authors": [
                        a.findtext(f"{NS}name", "") for a in entry.findall(f"{NS}author")
                    ],
                    "categories": [
                        t.get("term", "") for t in entry.findall(
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
        except Exception as exc:
            _eaf_logger.error("XML parse failed: %s", exc)

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
            if self._hdc:
                paper.vector = self._generate_vector(paper)
            self._paper_cache[paper_id] = paper
            self.stats.papers_parsed += 1

            # Persist to existing memory palace via node reference (same as ArXivForager)
            if self.node is not None and hasattr(self.node, "polysynthetic_vram_compress"):
                text_block = f"TITLE: {paper.title} | ABSTRACT: {paper.abstract}"
                phasor = self.node.polysynthetic_vram_compress(text_block)
                blob = np.array(phasor, dtype=np.complex64).tobytes()
                engram = f"ARXIV_{hashlib.sha256(text_block.encode()).hexdigest()[:8].upper()}"
                try:
                    conn = self.node.memory_palace.conn
                    await conn.execute(
                        "INSERT OR REPLACE INTO traces "
                        "(id, content, tier, timestamp, tags, vector_blob) "
                        "VALUES (?, ?, 'CRYSTAL', ?, 'Enhanced arXiv Ingest', ?)",
                        (engram, text_block, _dt.now().isoformat(), blob),
                    )
                    await conn.commit()
                    self.stats.papers_stored += 1
                except Exception as db_exc:
                    _eaf_logger.warning("DB write skipped: %s", db_exc)

            # Disk cache (no vector — too large for JSON)
            await self._save_to_disk(paper, config.storage_dir)

        except Exception as exc:
            self.stats.errors += 1
            _eaf_logger.error("Paper processing failed [%s]: %s", paper_id, exc)

    def _generate_vector(self, paper: ArxivPaper) -> _Optional[np.ndarray]:
        """Generate a 10,000-D HDC vector for a paper."""
        if self._hdc is None:
            return None
        text = " ".join(filter(None, [
            paper.title,
            paper.abstract,
            " ".join(paper.categories),
        ]))
        return self._hdc.encode_text(self._preprocess(text))

    def _preprocess(self, text: str) -> str:
        """Lowercase, strip non-alphanumeric, remove stopwords."""
        text = _re.sub(r"[^a-z0-9\s]", " ", text.lower())
        words = [w for w in text.split() if w not in _STOPWORDS and len(w) > 2]
        return " ".join(words)

    async def _save_to_disk(self, paper: ArxivPaper, storage_dir: str) -> None:
        """Persist paper metadata to disk (JSON, no vector blob)."""
        try:
            import json as _j
            _Path(storage_dir).mkdir(parents=True, exist_ok=True)
            safe_id = paper.paper_id.replace("/", "_")
            path = _Path(storage_dir) / f"{safe_id}.json"
            d = paper.to_dict()
            d.pop("vector", None)
            path.write_text(_j.dumps(d, indent=2), encoding="utf-8")
        except Exception as exc:
            _eaf_logger.debug("Disk save skipped: %s", exc)
