"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fc-[Q-SYS:CONTEXT_CRUSHER]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Reversible Context Compression)
DEPENDENCIES: ast, dataclasses, hashlib, json, os, re, time, pathlib, typing, aura_wasm_bridge
FUNCTIONS: ContextCrushResult, ContextCrushBatch, CachePrefixReport, AuraContextCrusher, apply_context_crush_to_messages, apply_context_crush_to_prompt, retrieve_context_crush
SYNOPSIS: Aura-native adaptation of Headroom-style local context compression. Routes JSON, logs, search results, and code through deterministic lightweight compressors, optionally lets a local Rust/WASI accelerator compete for shorter payloads, stores originals in a local CCR ledger for retrieval, and emits cache-prefix stability metrics without mutating system prompts.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Iterable

from aura_wasm_bridge import AuraRustWasmBridge

CONTEXT_CRUSH_VERSION = "AURA_CONTEXT_CRUSH_V1"
DEFAULT_LEDGER_PATH = "Aura_Memory/context_crush_ledger.jsonl"
DEFAULT_MIN_CHARS = 1_200
DEFAULT_MIN_SAVINGS_RATIO = 0.08
DEFAULT_MAX_ROWS = 24
DEFAULT_MAX_LINES = 80

_LOG_SIGNAL = re.compile(
    r"\b(ERROR|FAIL|FAILED|FATAL|CRITICAL|TRACEBACK|EXCEPTION|WARN|WARNING)\b",
    re.IGNORECASE,
)
_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b")
_SEARCH_HIT = re.compile(r"^[^\s:]+:\d+:", re.MULTILINE)
_DIFF_HEADER = re.compile(r"^(diff --git|--- a/|\+\+\+ b/|@@\s+-\d+)", re.MULTILINE)
_HEX_LENGTHS = {32, 40, 64}


@dataclass(frozen=True)
class VolatileFinding:
    label: str
    sample: str

    def to_jsonable(self) -> dict[str, Any]:
        return {"label": self.label, "sample": self.sample}


@dataclass(frozen=True)
class CachePrefixReport:
    stable_prefix_hash: str
    stable_prefix_bytes: int
    stable_prefix_tokens_est: int
    findings: tuple[VolatileFinding, ...] = ()

    @property
    def alignment_score(self) -> float:
        return max(0.0, min(100.0, 100.0 - len(self.findings) * 10.0))

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "stable_prefix_hash": self.stable_prefix_hash,
            "stable_prefix_bytes": self.stable_prefix_bytes,
            "stable_prefix_tokens_est": self.stable_prefix_tokens_est,
            "alignment_score": self.alignment_score,
            "findings": [finding.to_jsonable() for finding in self.findings],
        }


@dataclass(frozen=True)
class ContextCrushResult:
    compressed_payload: str
    original_hash: str
    content_type: str
    original_chars: int
    compressed_chars: int
    token_savings_estimate: int
    was_compressed: bool
    accelerator: str = "python"
    retrieval_marker: str = ""
    warnings: tuple[str, ...] = ()

    @property
    def savings_ratio(self) -> float:
        if self.original_chars <= 0:
            return 0.0
        return max(0.0, 1.0 - (self.compressed_chars / self.original_chars))

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "version": CONTEXT_CRUSH_VERSION,
            "content_type": self.content_type,
            "original_hash": self.original_hash,
            "original_chars": self.original_chars,
            "compressed_chars": self.compressed_chars,
            "token_savings_estimate": self.token_savings_estimate,
            "savings_ratio": round(self.savings_ratio, 4),
            "was_compressed": self.was_compressed,
            "accelerator": self.accelerator,
            "retrieval_marker": self.retrieval_marker,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ContextCrushBatch:
    messages: list[dict[str, Any]]
    results: tuple[ContextCrushResult, ...]
    cache_prefix: CachePrefixReport

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "version": CONTEXT_CRUSH_VERSION,
            "compressed_message_count": sum(1 for item in self.results if item.was_compressed),
            "token_savings_estimate": sum(item.token_savings_estimate for item in self.results),
            "results": [item.to_jsonable() for item in self.results],
            "cache_prefix": self.cache_prefix.to_jsonable(),
        }


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _short_hash(text: str, *, size: int = 12) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=size).hexdigest()


def _safe_cell(value: Any, *, limit: int = 180) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    else:
        text = str(value)
    text = text.replace("\r", " ").replace("\n", "\\n")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _safe_sample(token: str) -> str:
    return token if len(token) <= 16 else f"{token[:8]}...{token[-4:]}"


def _is_uuid(token: str) -> bool:
    if len(token) != 36 or token.count("-") != 4:
        return False
    try:
        import uuid

        uuid.UUID(token)
        return True
    except Exception:
        return False


def _is_iso8601(token: str) -> bool:
    if len(token) < 8 or ("T" not in token and "-" not in token):
        return False
    from datetime import datetime

    candidate = token[:-1] + "+00:00" if token.endswith("Z") else token
    try:
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        return False


def _is_hex_hash(token: str) -> bool:
    if len(token) not in _HEX_LENGTHS:
        return False
    try:
        int(token, 16)
        return True
    except ValueError:
        return False


def _volatile_findings(text: str) -> tuple[VolatileFinding, ...]:
    findings: list[VolatileFinding] = []
    for raw in (text or "").split():
        token = raw.strip(".,;:!?\"'()[]{}<>")
        if not token:
            continue
        label = None
        if _is_uuid(token):
            label = "uuid"
        elif token.count(".") == 2 and all(len(part) >= 4 for part in token.split(".")):
            label = "jwt_shape"
        elif _is_iso8601(token):
            label = "iso8601"
        elif _is_hex_hash(token):
            label = "hex_hash"
        if label:
            findings.append(VolatileFinding(label=label, sample=_safe_sample(token)))
    return tuple(findings)


def compute_cache_prefix_report(messages: list[dict[str, Any]]) -> CachePrefixReport:
    system_text = "\n---\n".join(
        str(message.get("content") or "")
        for message in messages
        if message.get("role") == "system" and isinstance(message.get("content"), str)
    )
    return CachePrefixReport(
        stable_prefix_hash=_short_hash(system_text),
        stable_prefix_bytes=len(system_text.encode("utf-8")),
        stable_prefix_tokens_est=_estimate_tokens(system_text),
        findings=_volatile_findings(system_text),
    )


class AuraContextCrusher:
    def __init__(
        self,
        *,
        ledger_path: str | Path | None = None,
        min_chars: int = DEFAULT_MIN_CHARS,
        min_savings_ratio: float = DEFAULT_MIN_SAVINGS_RATIO,
        max_rows: int = DEFAULT_MAX_ROWS,
        max_lines: int = DEFAULT_MAX_LINES,
        enable_wasm: bool | None = None,
    ) -> None:
        self.ledger_path = Path(
            ledger_path
            or os.environ.get("AURA_CONTEXT_CRUSH_LEDGER")
            or DEFAULT_LEDGER_PATH
        )
        self.min_chars = max(0, int(min_chars))
        self.min_savings_ratio = max(0.0, float(min_savings_ratio))
        self.max_rows = max(3, int(max_rows))
        self.max_lines = max(10, int(max_lines))
        if enable_wasm is None:
            mode = os.environ.get("AURA_CONTEXT_CRUSH_WASM", "auto").strip().lower()
            enable_wasm = mode not in {"0", "false", "off", "disabled", "python"}
        self.wasm_bridge = AuraRustWasmBridge.from_env() if enable_wasm else AuraRustWasmBridge(None)

    def detect_content_type(self, raw_content: str, source_hint: str | None = None) -> str:
        hint = (source_hint or "").lower()
        if "json" in hint:
            return "json"
        if "log" in hint or "stderr" in hint or "stdout" in hint:
            return "log"
        content = (raw_content or "").strip()
        if not content:
            return "text"
        try:
            parsed = json.loads(content)
            if isinstance(parsed, (list, dict)):
                return "json"
        except Exception:
            pass
        if _DIFF_HEADER.search(content):
            return "diff"
        if _SEARCH_HIT.search(content):
            return "search"
        if _LOG_SIGNAL.search(content) or "Traceback (most recent call last)" in content:
            return "log"
        if self._looks_like_code(content):
            return "code"
        return "text"

    def compress_context_stream(self, raw_content: str, *, source_hint: str | None = None) -> ContextCrushResult:
        raw = raw_content or ""
        original_hash = f"aura_ccr_{_short_hash(raw, size=10)}"
        content_type = self.detect_content_type(raw, source_hint)
        compressed = self._compress_by_type(raw, content_type, original_hash)
        accelerator = "python"
        warnings: tuple[str, ...] = ()
        accelerated = self.wasm_bridge.accelerate(raw, content_type)
        if accelerated and len(accelerated.compressed_payload) < len(compressed):
            compressed = accelerated.compressed_payload
            accelerator = accelerated.accelerator
            warnings = accelerated.warnings
        candidate = self._with_marker(
            compressed,
            original_hash=original_hash,
            content_type=content_type,
            original_chars=len(raw),
        )
        raw_tokens = _estimate_tokens(raw)
        candidate_tokens = _estimate_tokens(candidate)
        savings = raw_tokens - candidate_tokens
        ratio = 1.0 - (len(candidate) / max(1, len(raw)))

        if len(raw) < self.min_chars or savings <= 0 or ratio < self.min_savings_ratio:
            return ContextCrushResult(
                compressed_payload=raw,
                original_hash=original_hash,
                content_type=content_type,
                original_chars=len(raw),
                compressed_chars=len(raw),
                token_savings_estimate=0,
                was_compressed=False,
                accelerator="python",
            )

        self._upsert_record(
            original_hash=original_hash,
            content_type=content_type,
            original=raw,
            compressed=candidate,
            source_hint=source_hint,
        )
        return ContextCrushResult(
            compressed_payload=candidate,
            original_hash=original_hash,
            content_type=content_type,
            original_chars=len(raw),
            compressed_chars=len(candidate),
            token_savings_estimate=savings,
            was_compressed=True,
            accelerator=accelerator,
            retrieval_marker=f"<<aura_ccr:{original_hash}>>",
            warnings=warnings,
        )

    def _looks_like_code(self, content: str) -> bool:
        if re.search(r"^\s*(def|class|import|from|async def)\s+\w+", content, re.MULTILINE):
            return True
        if re.search(r"^\s*(function|const|let|var|class|export|fn|struct|impl)\s+", content, re.MULTILINE):
            return True
        try:
            ast.parse(content)
            return "\n" in content and any(token in content for token in ("def ", "class ", "import "))
        except SyntaxError:
            return False

    def _compress_by_type(self, raw: str, content_type: str, original_hash: str) -> str:
        if content_type == "json":
            return self._compress_json(raw)
        if content_type == "log":
            return self._compress_log(raw)
        if content_type == "search":
            return self._compress_search(raw)
        if content_type == "code":
            return self._compress_code(raw)
        if content_type == "diff":
            return self._compress_diff(raw)
        return self._compress_text(raw)

    def _compress_json(self, raw: str) -> str:
        try:
            data = json.loads(raw)
        except Exception:
            return raw
        if isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
            keys = sorted({str(key) for item in data for key in item.keys()})
            rows = [[_safe_cell(item.get(key, "")) for key in keys] for item in data[: self.max_rows]]
            omitted = max(0, len(data) - len(rows))
            return json.dumps(
                {"kind": "json_matrix", "keys": keys, "rows": rows, "omitted_rows": omitted},
                separators=(",", ":"),
                sort_keys=True,
            )
        if isinstance(data, dict):
            items = [[str(key), _safe_cell(value)] for key, value in sorted(data.items())[: self.max_rows]]
            omitted = max(0, len(data) - len(items))
            return json.dumps(
                {"kind": "json_kv", "items": items, "omitted_keys": omitted},
                separators=(",", ":"),
                sort_keys=True,
            )
        return json.dumps(data, separators=(",", ":"), sort_keys=True, default=str)

    def _compress_log(self, raw: str) -> str:
        lines = raw.splitlines()
        keep: set[int] = set(range(min(4, len(lines))))
        keep.update(range(max(0, len(lines) - 4), len(lines)))
        for idx, line in enumerate(lines):
            if _LOG_SIGNAL.search(line) or "Traceback (most recent call last)" in line:
                for pos in range(max(0, idx - 2), min(len(lines), idx + 4)):
                    keep.add(pos)
        selected = sorted(keep)[: self.max_lines]
        rendered = [f"{idx + 1}: {_TIMESTAMP.sub('[T]', lines[idx])}" for idx in selected]
        return "\n".join([
            f"[AURA_LOG_CRUSH lines={len(lines)} kept={len(rendered)} omitted={max(0, len(lines) - len(rendered))}]",
            *rendered,
        ])

    def _compress_search(self, raw: str) -> str:
        lines = [line for line in raw.splitlines() if line.strip()]
        file_counts: dict[str, int] = {}
        for line in lines:
            file_name = line.split(":", 1)[0]
            file_counts[file_name] = file_counts.get(file_name, 0) + 1
        selected = lines[: self.max_lines]
        summary = ",".join(f"{Path(path).name}:{count}" for path, count in sorted(file_counts.items())[:12])
        return "\n".join([
            f"[AURA_SEARCH_CRUSH hits={len(lines)} kept={len(selected)} files={summary}]",
            *selected,
        ])

    def _compress_code(self, raw: str) -> str:
        try:
            tree = ast.parse(raw)
        except SyntaxError:
            return self._compress_text(raw)
        imports: list[str] = []
        symbols: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.get_source_segment(raw, node) or f"import@{node.lineno}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "def"
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                symbols.append(f"{kind} {node.name} lines={node.lineno}-{end}")
        payload = {"kind": "python_ast_sketch", "imports": imports[:30], "symbols": symbols[:80]}
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    def _compress_diff(self, raw: str) -> str:
        lines = raw.splitlines()
        keep = [
            line for line in lines
            if line.startswith(("diff --git", "--- ", "+++ ", "@@", "+", "-"))
        ][: self.max_lines]
        return "\n".join([
            f"[AURA_DIFF_CRUSH lines={len(lines)} kept={len(keep)}]",
            *keep,
        ])

    def _compress_text(self, raw: str) -> str:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", raw) if part.strip()]
        if len(paragraphs) <= 6:
            return raw[:1800] + ("\n...[truncated]..." if len(raw) > 1800 else "")
        selected = paragraphs[:3] + [f"[... {max(0, len(paragraphs) - 6)} paragraphs omitted ...]"] + paragraphs[-3:]
        return "\n\n".join(selected)

    def _with_marker(
        self,
        compressed: str,
        *,
        original_hash: str,
        content_type: str,
        original_chars: int,
    ) -> str:
        return (
            f"[AURA_CCR hash={original_hash} type={content_type} original_chars={original_chars}]\n"
            f"{compressed}\n"
            f"[AURA_CCR_RETRIEVE hash={original_hash} fn=retrieve_context_crush]\n"
        )

    def _upsert_record(
        self,
        *,
        original_hash: str,
        content_type: str,
        original: str,
        compressed: str,
        source_hint: str | None,
    ) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "version": CONTEXT_CRUSH_VERSION,
            "hash": original_hash,
            "content_type": content_type,
            "source_hint": source_hint or "",
            "created_unix": time.time(),
            "original_chars": len(original),
            "compressed_chars": len(compressed),
            "original": original,
            "compressed": compressed,
        }
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def apply_context_crush_to_prompt(
    prompt: str,
    *,
    source_hint: str | None = None,
    ledger_path: str | Path | None = None,
    min_chars: int = DEFAULT_MIN_CHARS,
    enable_wasm: bool | None = None,
) -> ContextCrushResult:
    return AuraContextCrusher(
        ledger_path=ledger_path,
        min_chars=min_chars,
        enable_wasm=enable_wasm,
    ).compress_context_stream(
        prompt,
        source_hint=source_hint,
    )


def apply_context_crush_to_messages(
    messages: list[dict[str, Any]],
    *,
    ledger_path: str | Path | None = None,
    min_chars: int = DEFAULT_MIN_CHARS,
    skip_roles: Iterable[str] = ("system",),
    enable_wasm: bool | None = None,
) -> ContextCrushBatch:
    crusher = AuraContextCrusher(
        ledger_path=ledger_path,
        min_chars=min_chars,
        enable_wasm=enable_wasm,
    )
    skip = {role.lower() for role in skip_roles}
    rewritten: list[dict[str, Any]] = []
    results: list[ContextCrushResult] = []
    for message in messages:
        item = dict(message)
        role = str(item.get("role", "")).lower()
        content = item.get("content")
        if role not in skip and isinstance(content, str):
            result = crusher.compress_context_stream(content, source_hint=f"message:{role}")
            item["content"] = result.compressed_payload
            results.append(result)
        rewritten.append(item)
    return ContextCrushBatch(
        messages=rewritten,
        results=tuple(results),
        cache_prefix=compute_cache_prefix_report(messages),
    )


def retrieve_context_crush(
    original_hash: str,
    *,
    query: str | None = None,
    ledger_path: str | Path | None = None,
    max_chars: int = 8_000,
) -> str:
    path = Path(ledger_path or os.environ.get("AURA_CONTEXT_CRUSH_LEDGER") or DEFAULT_LEDGER_PATH)
    if not path.exists():
        return ""
    query_terms = [term.lower() for term in (query or "").split() if term.strip()]
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("hash") != original_hash:
                continue
            original = str(payload.get("original", ""))
            if not query_terms:
                return original[:max_chars]
            hits = [
                text_line
                for text_line in original.splitlines()
                if all(term in text_line.lower() for term in query_terms)
            ]
            return "\n".join(hits)[:max_chars]
    return ""
