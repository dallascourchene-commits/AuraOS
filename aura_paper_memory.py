"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f7-[Q-SYS:PAPER_MEMORY_RAEC]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Resonant Recall)
DEPENDENCIES: base64, dataclasses, hashlib, io, json, math, re, time, typing, numpy, aura_single_seed_lift
FUNCTIONS: EgressResonancePayload, ResearchProfileVector, PaperMemoryRecord, AuraResonanceEgressGate, compile_paper_memory_record, extract_pdf_text_from_bytes, load_research_profiles_from_jsonl, record_to_research_profile, record_to_trace_content, track_egress_savings, upsert_paper_memory_record, verify_egress_contract
SYNOPSIS: Stateless paper-memory and RAEC middleware primitives. Scientific documents are chunked into 10,000-D complex phasor fields, lifted through a cached single-seed dispatch profile, stamped with a 1.2KB holographic header, summarized into three deterministic points, and exposed to egress as compact bracket slots.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import io
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Iterable, List, Sequence

import numpy as np

from aura_single_seed_lift import (
    SingleSeedLiftProfile,
    compact_lift_capsule,
    compile_single_seed_lift,
)

DIMENSIONS = 10_000
HEADER_BYTES = 1_200
DEFAULT_CHUNK_CHARS = 1_800
DEFAULT_CHUNK_OVERLAP = 160
DEFAULT_MAX_TEXT_CHARS = 220_000


@dataclass(frozen=True)
class EgressResonancePayload:
    base_prompt: str
    slot_matrix_string: str
    target_provider: str
    lift_dispatch: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ResearchProfileVector:
    doc_id: str
    summary_capsule: str
    structural_vector: np.ndarray
    single_seed_lift: SingleSeedLiftProfile | None = None


@dataclass(frozen=True)
class PaperMemoryRecord:
    doc_id: str
    title: str
    abstract: str
    authors: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    published: str = ""
    source_url: str = ""
    pdf_url: str = ""
    full_text_sha256: str = ""
    three_main_points: tuple[str, str, str] = ("", "", "")
    summary_capsule: str = ""
    holographic_header: str = ""
    structural_vector: np.ndarray = field(default_factory=lambda: _empty_phasor())
    chunk_vectors: tuple[np.ndarray, ...] = ()
    single_seed_lift: SingleSeedLiftProfile | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": list(self.authors),
            "categories": list(self.categories),
            "published": self.published,
            "source_url": self.source_url,
            "pdf_url": self.pdf_url,
            "full_text_sha256": self.full_text_sha256,
            "three_main_points": list(self.three_main_points),
            "summary_capsule": self.summary_capsule,
            "holographic_header": self.holographic_header,
            "structural_vector": _phasor_to_b64(self.structural_vector),
            "chunk_vectors": [_phasor_to_b64(v) for v in self.chunk_vectors],
            "single_seed_lift": (
                self.single_seed_lift.to_jsonable()
                if self.single_seed_lift is not None
                else {}
            ),
            "metadata": self.metadata,
            "version": "paper-memory-v2",
        }

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any]) -> "PaperMemoryRecord":
        return cls(
            doc_id=str(payload.get("doc_id", "")),
            title=str(payload.get("title", "")),
            abstract=str(payload.get("abstract", "")),
            authors=tuple(payload.get("authors", ()) or ()),
            categories=tuple(payload.get("categories", ()) or ()),
            published=str(payload.get("published", "")),
            source_url=str(payload.get("source_url", "")),
            pdf_url=str(payload.get("pdf_url", "")),
            full_text_sha256=str(payload.get("full_text_sha256", "")),
            three_main_points=_three_tuple(payload.get("three_main_points", ())),
            summary_capsule=str(payload.get("summary_capsule", "")),
            holographic_header=str(payload.get("holographic_header", "")),
            structural_vector=_b64_to_phasor(payload.get("structural_vector", "")),
            chunk_vectors=tuple(
                _b64_to_phasor(v) for v in payload.get("chunk_vectors", ()) or ()
            ),
            single_seed_lift=SingleSeedLiftProfile.from_jsonable(
                payload.get("single_seed_lift")
            ),
            metadata=dict(payload.get("metadata", {}) or {}),
        )


def _three_tuple(values: Iterable[Any]) -> tuple[str, str, str]:
    items = [str(v) for v in values if str(v).strip()][:3]
    while len(items) < 3:
        items.append("")
    return items[0], items[1], items[2]


def _empty_phasor() -> np.ndarray:
    return np.ones(DIMENSIONS, dtype=np.complex64)


def _seeded_phasor(label: str, dimensions: int = DIMENSIONS) -> np.ndarray:
    seed = int.from_bytes(
        hashlib.blake2b(label.encode("utf-8"), digest_size=8).digest(),
        "big",
    )
    rng = np.random.default_rng(seed)
    phases = rng.uniform(-math.pi, math.pi, dimensions).astype(np.float32)
    return np.exp(1j * phases).astype(np.complex64, copy=False)


def _unit_phase(vector: np.ndarray) -> np.ndarray:
    arr = np.asarray(vector, dtype=np.complex64).reshape(-1)
    if arr.size != DIMENSIONS:
        padded = np.ones(DIMENSIONS, dtype=np.complex64)
        padded[: min(arr.size, DIMENSIONS)] = arr[:DIMENSIONS]
        arr = padded
    if not np.any(arr):
        return _empty_phasor()
    return np.exp(1j * np.angle(arr)).astype(np.complex64, copy=False)


def encode_text_as_phasor(text: str) -> np.ndarray:
    chunks = chunk_text(text)
    if not chunks:
        return _seeded_phasor("EMPTY::PAPER")
    field = np.zeros(DIMENSIONS, dtype=np.complex64)
    for idx, chunk in enumerate(chunks):
        digest = hashlib.blake2b(chunk.encode("utf-8"), digest_size=16).hexdigest()
        field += np.roll(_seeded_phasor(f"CHUNK::{digest}"), idx * 4097)
    return _unit_phase(field)


def chunk_text(
    text: str,
    *,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    max_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> list[str]:
    clean = " ".join((text or "").split())[:max_chars]
    if not clean:
        return []
    width = max(256, int(chunk_chars))
    step = max(128, width - max(0, int(overlap)))
    return [clean[pos : pos + width] for pos in range(0, len(clean), step)]


def _sentence_candidates(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return []
    raw = re.split(r"(?<=[.!?])\s+", clean)
    candidates = []
    for sent in raw:
        sent = sent.strip(" -\t\r\n")
        word_count = len(sent.split())
        if 7 <= word_count <= 42:
            candidates.append(sent)
    return candidates


def extract_three_main_points(title: str, abstract: str, full_text: str = "") -> tuple[str, str, str]:
    source = f"{abstract} {full_text[:12000]}"
    candidates = _sentence_candidates(source)
    if not candidates:
        candidates = [title.strip()] if title.strip() else []
    scored = []
    seen = set()
    for sentence in candidates:
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        score = len(set(re.findall(r"[a-zA-Z]{4,}", key)))
        if any(term in key for term in ("propose", "show", "demonstrate", "result", "method", "achieve")):
            score += 8
        scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    points = [_slot_safe(sentence, limit=260) for _, sentence in scored[:3]]
    while len(points) < 3:
        points.append("")
    return points[0], points[1], points[2]


def _slot_safe(value: str, *, limit: int = 420) -> str:
    clean = re.sub(r"[\[\]\r\n]+", " ", value or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:limit]


def compile_summary_capsule(record: PaperMemoryRecord | dict[str, Any]) -> str:
    if isinstance(record, PaperMemoryRecord):
        points = record.three_main_points
        categories = record.categories
        published = record.published
    else:
        points = _three_tuple(record.get("three_main_points", ()))
        categories = tuple(record.get("categories", ()) or ())
        published = str(record.get("published", ""))
    point_text = "|".join(
        f"P{idx + 1}={_slot_safe(point, limit=220)}"
        for idx, point in enumerate(points)
        if point
    )
    meta = ",".join(_slot_safe(cat, limit=40) for cat in categories[:4])
    date = published[:10] if published else ""
    return _slot_safe(f"{point_text}|CAT={meta}|DATE={date}", limit=720)


def _holographic_header(vector: np.ndarray) -> str:
    q = np.clip(np.asarray(vector).real * 127, -128, 127).astype(np.int8)
    raw = q.tobytes()[:HEADER_BYTES]
    if len(raw) < HEADER_BYTES:
        raw += b"\x00" * (HEADER_BYTES - len(raw))
    return base64.b64encode(raw).decode("ascii")


def _phasor_to_b64(vector: np.ndarray) -> str:
    arr = np.asarray(vector, dtype=np.complex64).reshape(DIMENSIONS)
    return base64.b64encode(arr.tobytes()).decode("ascii")


def _b64_to_phasor(value: str) -> np.ndarray:
    if not value:
        return _empty_phasor()
    try:
        arr = np.frombuffer(base64.b64decode(value), dtype=np.complex64)
        return _unit_phase(arr)
    except Exception:
        return _empty_phasor()


def compile_paper_memory_record(
    *,
    doc_id: str,
    title: str,
    abstract: str,
    full_text: str = "",
    authors: Sequence[str] = (),
    categories: Sequence[str] = (),
    published: str = "",
    source_url: str = "",
    pdf_url: str = "",
    metadata: dict[str, Any] | None = None,
) -> PaperMemoryRecord:
    body = " ".join(part for part in (title, abstract, full_text) if part)
    chunks = chunk_text(body)
    chunk_vectors = tuple(encode_text_as_phasor(chunk) for chunk in chunks)
    if chunk_vectors:
        structural_vector = _unit_phase(np.sum(np.stack(chunk_vectors), axis=0))
    else:
        structural_vector = encode_text_as_phasor(body)
    lift = compile_single_seed_lift(
        doc_id or title or "AURA_PAPER_MEMORY",
        chunk_vectors or (structural_vector,),
        base_vector=structural_vector,
        dimensions=DIMENSIONS,
    )
    structural_vector = _unit_phase(lift.lifted_vector)
    points = extract_three_main_points(title, abstract, full_text)
    full_hash = hashlib.sha256((full_text or abstract or title).encode("utf-8")).hexdigest()
    temp = {
        "three_main_points": points,
        "categories": tuple(categories),
        "published": published,
    }
    capsule = compile_summary_capsule(temp)
    meta = dict(metadata or {})
    meta.update({
        "chunk_count": len(chunks),
        "full_text_chars": len(full_text or ""),
        "abstract_chars": len(abstract or ""),
        "holographic_header_bytes": HEADER_BYTES,
        "single_seed_lift_version": lift.profile.version,
        "single_seed_lift_layers": lift.profile.lift_layers,
        "single_seed_lift_seed": lift.profile.seed_id,
        "single_seed_trace_count": len(lift.profile.top_traces),
    })
    return PaperMemoryRecord(
        doc_id=doc_id,
        title=title,
        abstract=abstract,
        authors=tuple(authors or ()),
        categories=tuple(categories or ()),
        published=published,
        source_url=source_url,
        pdf_url=pdf_url,
        full_text_sha256=full_hash,
        three_main_points=points,
        summary_capsule=capsule,
        holographic_header=_holographic_header(structural_vector),
        structural_vector=structural_vector,
        chunk_vectors=chunk_vectors,
        single_seed_lift=lift.profile,
        metadata=meta,
    )


def record_to_trace_content(record: PaperMemoryRecord) -> str:
    points = " ; ".join(p for p in record.three_main_points if p)
    return (
        f"TITLE: {record.title} | ABSTRACT: {record.abstract} | "
        f"PUBLISHED: {record.published} | POINTS: {points} | "
        f"HEADER: {record.holographic_header[:32]} | "
        f"SHA256: {record.full_text_sha256}"
    )


def record_to_research_profile(record: PaperMemoryRecord) -> ResearchProfileVector:
    return ResearchProfileVector(
        doc_id=record.doc_id,
        summary_capsule=record.summary_capsule or compile_summary_capsule(record),
        structural_vector=record.structural_vector,
        single_seed_lift=record.single_seed_lift,
    )


def upsert_paper_memory_record(record: PaperMemoryRecord, ledger_path: str | Path) -> None:
    target = Path(ledger_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict[str, Any]] = {}
    if target.exists():
        with target.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    key = str(payload.get("doc_id", ""))
                    if key:
                        rows[key] = payload
                except json.JSONDecodeError:
                    continue
    rows[record.doc_id] = record.to_jsonable()
    with target.open("w", encoding="utf-8") as handle:
        for key in sorted(rows):
            handle.write(json.dumps(rows[key], separators=(",", ":"), sort_keys=True) + "\n")


def load_paper_memory_records(ledger_path: str | Path) -> list[PaperMemoryRecord]:
    target = Path(ledger_path)
    if not target.exists():
        return []
    records: list[PaperMemoryRecord] = []
    with target.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                records.append(PaperMemoryRecord.from_jsonable(json.loads(line)))
            except Exception:
                continue
    return records


def load_research_profiles_from_jsonl(ledger_path: str | Path) -> list[ResearchProfileVector]:
    return [record_to_research_profile(record) for record in load_paper_memory_records(ledger_path)]


class AuraResonanceEgressGate:
    def __init__(self, dimensions: int = DIMENSIONS) -> None:
        self.dimensions = dimensions

    def _intent_vector(self, user_intent: str) -> np.ndarray:
        return encode_text_as_phasor(user_intent)

    def inject_latent_context(
        self,
        user_intent: str,
        local_ledger: List[ResearchProfileVector],
        provider: str,
    ) -> EgressResonancePayload:
        intent_vector = self._intent_vector(user_intent)
        scored: list[tuple[float, ResearchProfileVector]] = []
        for node in local_ledger:
            vector = np.asarray(node.structural_vector, dtype=np.complex64).reshape(-1)
            if vector.size != self.dimensions:
                continue
            resonance = float(np.real(np.dot(intent_vector, np.conjugate(vector))) / self.dimensions)
            scored.append((resonance, node))
        scored.sort(key=lambda item: item[0], reverse=True)
        slots = []
        lift_dispatch: list[dict[str, Any]] = []
        for _, node in scored[:2]:
            constraints = _slot_safe(node.summary_capsule)
            if node.single_seed_lift is not None:
                lift_capsule = compact_lift_capsule(node.single_seed_lift, limit=260)
                if lift_capsule:
                    lift_marker = f"|LIFT={lift_capsule}"
                    summary_limit = max(1, 720 - len(lift_marker))
                    constraints = (
                        f"{_slot_safe(node.summary_capsule, limit=summary_limit)}"
                        f"{lift_marker}"
                    )
                    lift_dispatch.append(node.single_seed_lift.to_jsonable())
            slots.append(
                f"[ANCHOR_ID:{_slot_safe(node.doc_id, limit=96)}]"
                f"[CONSTRAINTS:{constraints}]"
            )
        return EgressResonancePayload(
            base_prompt=user_intent,
            slot_matrix_string="".join(slots),
            target_provider=provider,
            lift_dispatch=tuple(lift_dispatch),
        )


def verify_egress_contract(payload: EgressResonancePayload, grammar_stencil: str) -> bool:
    if not payload.slot_matrix_string:
        return False
    if len(payload.base_prompt) == 0:
        return False
    if "root ::=" not in grammar_stencil:
        return False
    return True


def track_egress_savings(
    input_chars: int,
    output_tokens: int,
    processing_latency: float,
) -> dict[str, Any]:
    input_tokens = max(1, int(input_chars) // 4)
    latency = max(0.0, float(processing_latency))
    outputs = max(0, int(output_tokens))
    denominator = max(1e-9, latency + (outputs / max(1, input_tokens)))
    efficiency = 0.99 / denominator
    return {
        "efficiency_score": efficiency,
        "input_chars": int(input_chars),
        "input_tokens_est": input_tokens,
        "output_tokens": outputs,
        "processing_latency": latency,
    }


def extract_pdf_text_from_bytes(
    pdf_bytes: bytes,
    *,
    max_pages: int | None = None,
    max_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> str:
    if not pdf_bytes:
        return ""
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
            text = "\n".join((page.extract_text() or "") for page in pages)
            return text[:max_chars]
    except Exception:
        pass
    try:
        import PyPDF2  # type: ignore

        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        pages = reader.pages if max_pages is None else reader.pages[:max_pages]
        text = "\n".join((page.extract_text() or "") for page in pages)
        return text[:max_chars]
    except Exception:
        return ""


def extract_pdf_text_from_path(
    pdf_path: str | Path,
    *,
    max_pages: int | None = None,
    max_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> str:
    return extract_pdf_text_from_bytes(
        Path(pdf_path).read_bytes(),
        max_pages=max_pages,
        max_chars=max_chars,
    )
