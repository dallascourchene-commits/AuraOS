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
