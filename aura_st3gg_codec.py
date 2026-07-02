"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9d1-[Q-SYS:ST3GG_CODEC]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Measured AST Context Codec)
DEPENDENCIES: __future__, ast, collections, dataclasses, enum, hashlib, json, re, typing
FUNCTIONS: ST3GGProfile, ST3GGCodecMetrics, ST3GGFrame, ST3GGCodec, choose_profile_for_phase, compare_raw_vs_encoded
SYNOPSIS: Profile-based Python AST/context codec for Coding Arena compact context.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
import re
from typing import Any

ST3GG_CODEC_VERSION = "AURA_ST3GG_CODEC_V1"
FIDELITY_WARNING_THRESHOLD = 0.68
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|[^\sA-Za-z0-9_]", re.ASCII)


class ST3GGProfile(str, Enum):
    SUMMARY = "SUMMARY"
    SYMBOLIC = "SYMBOLIC"
    PATCH = "PATCH"
    TEST = "TEST"
    VERIFIER = "VERIFIER"

    @classmethod
    def coerce(cls, value: ST3GGProfile | str | None) -> ST3GGProfile:
        if isinstance(value, ST3GGProfile):
            return value
        text = str(value or cls.SYMBOLIC.value).strip().upper()
        return cls.__members__.get(text, cls.SYMBOLIC)


_EXACT_SPAN_PROFILES = {ST3GGProfile.PATCH, ST3GGProfile.TEST, ST3GGProfile.VERIFIER}


@dataclass(frozen=True)
class ST3GGCodecMetrics:
    raw_char_count: int
    encoded_char_count: int
    raw_token_estimate: int
    encoded_token_estimate: int
    compression_ratio: float
    ast_node_count: int
    symbol_count: int
    span_count: int
    fidelity_score: float
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ST3GGFrame:
    version: str
    profile: ST3GGProfile
    source_file: str
    target_symbol: str | None
    source_hash: str
    encoded: str
    symbols: tuple[dict[str, Any], ...]
    spans: tuple[dict[str, Any], ...]
    metrics: ST3GGCodecMetrics
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "profile": self.profile.value,
            "source_file": self.source_file,
            "target_symbol": self.target_symbol,
            "source_hash": self.source_hash,
            "encoded": self.encoded,
            "symbols": list(self.symbols),
            "spans": list(self.spans),
            "metrics": self.metrics.to_dict(),
            "warnings": list(self.warnings),
        }


class _IdentifierCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.counts: dict[str, int] = defaultdict(int)
        self.roles: dict[str, set[str]] = defaultdict(set)

    def add(self, name: str | None, role: str) -> None:
        text = str(name or "").strip()
        if not text:
            return
        self.counts[text] += 1
        self.roles[text].add(role)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.add(node.name, "function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.add(node.name, "async_function")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.add(node.name, "class")
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> Any:
        self.add(node.arg, "argument")
        self.generic_visit(node)

    def visit_alias(self, node: ast.alias) -> Any:
        self.add(node.name, "import")
        if node.asname:
            self.add(node.asname, "import_alias")

    def visit_Name(self, node: ast.Name) -> Any:
        role = "name"
        if isinstance(node.ctx, ast.Store):
            role = "store"
        elif isinstance(node.ctx, ast.Load):
            role = "load"
        elif isinstance(node.ctx, ast.Del):
            role = "delete"
        self.add(node.id, role)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        self.add(node.attr, "attribute")
        self.generic_visit(node)

    def visit_keyword(self, node: ast.keyword) -> Any:
        if node.arg:
            self.add(node.arg, "keyword")
        self.generic_visit(node)


class ST3GGCodec:
    """Measured AST/context codec for prompt-side structure, not byte compression."""

    def __init__(self) -> None:
        self._source = ""
        self._source_lines: list[str] = []
        self._target_symbol: str | None = None
        self._symbol_ids: dict[str, str] = {}
        self._symbol_counts: dict[str, int] = {}
        self._symbol_roles: dict[str, tuple[str, ...]] = {}
        self._spans: tuple[dict[str, Any], ...] = ()
        self._span_by_node_key: dict[tuple[str, int, int, str], str] = {}

    def encode_source(
        self,
        source: str,
        source_file: str = "",
        target_symbol: str | None = None,
        profile: ST3GGProfile = ST3GGProfile.SYMBOLIC,
    ) -> ST3GGFrame:
        profile = ST3GGProfile.coerce(profile)
        raw_source = source or ""
        source_hash = hashlib.sha256(raw_source.encode("utf-8", errors="replace")).hexdigest()
        warnings: list[str] = []
        raw_tokens = self.estimate_token_cost(raw_source)

        try:
            tree = ast.parse(raw_source, filename=source_file or "<st3gg>")
        except SyntaxError as exc:
            return self._encode_syntax_error(
                raw_source,
                source_file=source_file,
                target_symbol=target_symbol,
                profile=profile,
                source_hash=source_hash,
                raw_tokens=raw_tokens,
                error=exc,
            )

        self._source = raw_source
        self._source_lines = raw_source.splitlines()
        self._target_symbol = target_symbol
        self._prepare_symbols(tree)
        self._spans, span_warnings = self._build_spans(tree, profile)
        warnings.extend(span_warnings)
        if profile not in _EXACT_SPAN_PROFILES and ast_get_node_count(tree) > 0:
            warnings.append(f"exact_source_spans_omitted:profile={profile.value}")

        encoded = self.encode_ast(tree, profile)
        symbols = self._symbol_table()
        provisional_metrics = self._metrics(
            source=raw_source,
            encoded=encoded,
            tree=tree,
            symbols=symbols,
            spans=self._spans,
            warnings=tuple(warnings),
            fidelity_score=0.0,
        )
        frame = ST3GGFrame(
            version=ST3GG_CODEC_VERSION,
            profile=profile,
            source_file=source_file,
            target_symbol=target_symbol,
            source_hash=source_hash,
            encoded=encoded,
            symbols=symbols,
            spans=self._spans,
            metrics=provisional_metrics,
            warnings=tuple(warnings),
        )
        fidelity = self.score_fidelity(raw_source, frame)
        if fidelity < FIDELITY_WARNING_THRESHOLD:
            warnings.append(f"fidelity_below_threshold:{fidelity:.2f}")
        metrics = self._metrics(
            source=raw_source,
            encoded=encoded,
            tree=tree,
            symbols=symbols,
            spans=self._spans,
            warnings=tuple(warnings),
            fidelity_score=fidelity,
        )
        return replace(frame, metrics=metrics, warnings=tuple(warnings))

    def encode_ast(self, node: ast.AST, profile: ST3GGProfile) -> str:
        profile = ST3GGProfile.coerce(profile)
        if not self._symbol_ids:
            self._prepare_symbols(node)
        lines = [f"ST3GG_AST|v={ST3GG_CODEC_VERSION}|p={profile.value}"]
        if self._target_symbol:
            lines.append(f"TARGET|{self._target_symbol}")

        if isinstance(node, ast.Module):
            imports = [
                self._import_line(child) for child in node.body if isinstance(child, (ast.Import, ast.ImportFrom))
            ]
            if imports:
                lines.append("IMPORTS|" + ";".join(imports[:24]))
            for child in node.body:
                lines.extend(self._encode_statement(child, profile=profile, depth=0))
        else:
            lines.extend(self._encode_statement(node, profile=profile, depth=0))
        return "\n".join(line for line in lines if line)

    def estimate_token_cost(self, text: str) -> int:
        if not text:
            return 0
        tokens = _TOKEN_RE.findall(text)
        return max(1, len(tokens))

    def score_fidelity(self, source: str, frame: ST3GGFrame) -> float:
        source_hash = hashlib.sha256((source or "").encode("utf-8", errors="replace")).hexdigest()
        score = 0.15
        if frame.source_hash == source_hash:
            score += 0.20
        if frame.symbols:
            score += 0.18
        encoded = frame.encoded.lower()
        if any(marker in encoded for marker in ("calls=", "call|", "assign|", "return|", "assert|", "raise|")):
            score += 0.14
        if frame.spans:
            score += 0.23
            exact_hits = 0
            for span in frame.spans[:12]:
                text = str(span.get("text", ""))
                if text and text in source:
                    exact_hits += 1
            if exact_hits:
                score += min(0.10, exact_hits * 0.02)
        if frame.profile in _EXACT_SPAN_PROFILES and not frame.spans:
            score -= 0.18
        if frame.profile not in _EXACT_SPAN_PROFILES:
            score -= 0.08
        if any("syntax_error" in warning for warning in frame.warnings):
            score = min(score, 0.42)
        return round(max(0.0, min(1.0, score)), 4)

    def render_for_prompt(self, frame: ST3GGFrame) -> str:
        lines = [
            f"[ST3GG_FRAME version={frame.version} profile={frame.profile.value}]",
            f"source_file: {frame.source_file}",
            f"target_symbol: {frame.target_symbol or ''}",
            f"source_hash: {frame.source_hash}",
            (
                "metrics: "
                f"raw_tokens={frame.metrics.raw_token_estimate} "
                f"encoded_tokens={frame.metrics.encoded_token_estimate} "
                f"compression_ratio={frame.metrics.compression_ratio:.4f} "
                f"fidelity={frame.metrics.fidelity_score:.4f}"
            ),
        ]
        if frame.warnings:
            lines.append("warnings: " + "; ".join(frame.warnings))
        if frame.symbols:
            rendered_symbols = [
                f"{item['id']}={item['name']}#{item['count']}:{','.join(item['roles'])}" for item in frame.symbols[:80]
            ]
            lines.append("symbols: " + "; ".join(rendered_symbols))
        lines.append("--- encoded_ast_context ---")
        lines.append(frame.encoded)
        if frame.spans:
            lines.append("--- exact_source_spans ---")
            for span in frame.spans:
                lines.append(
                    f"{span['id']} {span['kind']} {span.get('name', '')} lines={span['line_start']}-{span['line_end']}"
                )
                lines.append(str(span.get("text", "")))
        lines.append("[/ST3GG_FRAME]")
        return "\n".join(lines)

    def _encode_syntax_error(
        self,
        source: str,
        *,
        source_file: str,
        target_symbol: str | None,
        profile: ST3GGProfile,
        source_hash: str,
        raw_tokens: int,
        error: SyntaxError,
    ) -> ST3GGFrame:
        warning = f"syntax_error_fallback:line={error.lineno or 0}:offset={error.offset or 0}:{_safe_inline(error.msg)}"
        sample = _safe_inline(source[:900])
        encoded = (
            f"ST3GG_AST|v={ST3GG_CODEC_VERSION}|p={profile.value}|syntax_error=1\n"
            f"FALLBACK_TEXT|chars={len(source)}|sample={sample}"
        )
        spans: tuple[dict[str, Any], ...] = ()
        warnings = [warning]
        if profile in _EXACT_SPAN_PROFILES and source:
            spans = (
                {
                    "id": "S0",
                    "kind": "syntax_error_fallback",
                    "name": target_symbol or source_file or "source",
                    "line_start": 1,
                    "line_end": max(1, len(source.splitlines())),
                    "col_start": 0,
                    "col_end": 0,
                    "text": source,
                },
            )
        else:
            warnings.append(f"exact_source_spans_omitted:profile={profile.value}")
        metrics = ST3GGCodecMetrics(
            raw_char_count=len(source),
            encoded_char_count=len(encoded),
            raw_token_estimate=raw_tokens,
            encoded_token_estimate=self.estimate_token_cost(encoded),
            compression_ratio=_ratio(self.estimate_token_cost(encoded), raw_tokens),
            ast_node_count=0,
            symbol_count=0,
            span_count=len(spans),
            fidelity_score=0.0,
            warnings=tuple(warnings),
        )
        frame = ST3GGFrame(
            version=ST3GG_CODEC_VERSION,
            profile=profile,
            source_file=source_file,
            target_symbol=target_symbol,
            source_hash=source_hash,
            encoded=encoded,
            symbols=(),
            spans=spans,
            metrics=metrics,
            warnings=tuple(warnings),
        )
        fidelity = self.score_fidelity(source, frame)
        if fidelity < FIDELITY_WARNING_THRESHOLD:
            warnings.append(f"fidelity_below_threshold:{fidelity:.2f}")
        return replace(
            frame,
            warnings=tuple(warnings),
            metrics=replace(metrics, fidelity_score=fidelity, warnings=tuple(warnings)),
        )

    def _prepare_symbols(self, node: ast.AST) -> None:
        collector = _IdentifierCollector()
        collector.visit(node)
        ordered = sorted(collector.counts.keys(), key=lambda item: (item.lower(), item))
        self._symbol_ids = {name: f"I{index}" for index, name in enumerate(ordered)}
        self._symbol_counts = dict(collector.counts)
        self._symbol_roles = {name: tuple(sorted(collector.roles[name])) for name in ordered}

    def _symbol_table(self) -> tuple[dict[str, Any], ...]:
        items = []
        for name, symbol_id in sorted(self._symbol_ids.items(), key=lambda item: int(item[1][1:])):
            items.append(
                {
                    "id": symbol_id,
                    "name": name,
                    "count": self._symbol_counts.get(name, 0),
                    "roles": list(self._symbol_roles.get(name, ())),
                }
            )
        return tuple(items)

    def _sid(self, name: str | None) -> str:
        text = str(name or "").strip()
        if not text:
            return "I?"
        if text not in self._symbol_ids:
            self._symbol_ids[text] = f"I{len(self._symbol_ids)}"
            self._symbol_counts[text] = 0
            self._symbol_roles[text] = ()
        return self._symbol_ids[text]

    def _sym(self, name: str | None) -> str:
        text = str(name or "").strip()
        if not text:
            return "I?"
        return f"{self._sid(text)}:{text}"

    def _encode_statement(self, node: ast.AST, *, profile: ST3GGProfile, depth: int) -> list[str]:
        prefix = "  " * depth
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            span = self._span_ref(node, "import", self._import_name(node))
            return [f"{prefix}IMPORT|{self._import_line(node)}{span}"]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return self._encode_function(node, profile=profile, depth=depth)
        if isinstance(node, ast.ClassDef):
            return self._encode_class(node, profile=profile, depth=depth)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            return [f"{prefix}ASSIGN|{self._assign_summary(node)}{self._span_ref(node, 'assign', '')}"]
        if isinstance(node, ast.Return):
            return [f"{prefix}RETURN|{self._expr_summary(node.value)}{self._span_ref(node, 'return', '')}"]
        if isinstance(node, ast.Raise):
            return [f"{prefix}RAISE|{self._expr_summary(node.exc)}{self._span_ref(node, 'raise', '')}"]
        if isinstance(node, ast.Assert):
            return [
                f"{prefix}ASSERT|{self._expr_summary(node.test)} "
                f"msg={self._expr_summary(node.msg)}{self._span_ref(node, 'assert', '')}"
            ]
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            return [f"{prefix}CALL|{self._call_summary(node.value)}"]
        if isinstance(node, ast.If):
            return [f"{prefix}CTRL|if test={self._expr_summary(node.test)}"]
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return [f"{prefix}CTRL|for target={self._expr_summary(node.target)} iter={self._expr_summary(node.iter)}"]
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return [f"{prefix}CTRL|with items={len(node.items)}"]
        if isinstance(node, ast.Try):
            return [f"{prefix}CTRL|try handlers={len(node.handlers)}"]
        return []

    def _encode_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        profile: ST3GGProfile,
        depth: int,
    ) -> list[str]:
        prefix = "  " * depth
        kind = "ASYNC_FUNC" if isinstance(node, ast.AsyncFunctionDef) else "FUNC"
        decorators = [self._expr_summary(item) for item in node.decorator_list]
        calls = _unique_preserve(self._call_name(call.func) for call in self._walk_type(node, ast.Call))
        assigns = _unique_preserve(self._assign_targets(stmt) for stmt in self._walk_assignments(node))
        returns = sum(1 for _ in self._walk_type(node, ast.Return))
        raises = sum(1 for _ in self._walk_type(node, ast.Raise))
        asserts = sum(1 for _ in self._walk_type(node, ast.Assert))
        line = (
            f"{prefix}{kind}|name={self._sym(node.name)}|sig=({self._format_arguments(node.args)})"
            f"|returns={self._expr_summary(node.returns)}|decorators={_join_limited(decorators, 6)}"
            f"|calls={_join_limited(calls, 12)}|assigns={_join_limited(assigns, 12)}"
            f"|return_count={returns}|raise_count={raises}|assert_count={asserts}"
            f"{self._span_ref(node, 'function', node.name)}"
        )
        lines = [line]
        if profile != ST3GGProfile.SUMMARY:
            for event in self._body_events(node, profile=profile):
                lines.append(f"{prefix}  {event}")
        return lines

    def _encode_class(self, node: ast.ClassDef, *, profile: ST3GGProfile, depth: int) -> list[str]:
        prefix = "  " * depth
        bases = [self._expr_summary(item) for item in node.bases]
        decorators = [self._expr_summary(item) for item in node.decorator_list]
        methods = [item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
        line = (
            f"{prefix}CLASS|name={self._sym(node.name)}|bases={_join_limited(bases, 8)}"
            f"|decorators={_join_limited(decorators, 6)}|methods={_join_limited(methods, 16)}"
            f"{self._span_ref(node, 'class', node.name)}"
        )
        lines = [line]
        if profile != ST3GGProfile.SUMMARY:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines.extend(self._encode_function(child, profile=ST3GGProfile.SUMMARY, depth=depth + 1))
        return lines

    def _body_events(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, profile: ST3GGProfile) -> list[str]:
        limits = {
            ST3GGProfile.SYMBOLIC: 12,
            ST3GGProfile.PATCH: 24,
            ST3GGProfile.TEST: 28,
            ST3GGProfile.VERIFIER: 32,
        }
        limit = limits.get(profile, 10)
        events: list[str] = []
        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                events.append(f"ASSIGN|{self._assign_summary(child)}{self._span_ref(child, 'assign', '')}")
            elif isinstance(child, ast.Return):
                events.append(f"RETURN|{self._expr_summary(child.value)}{self._span_ref(child, 'return', '')}")
            elif isinstance(child, ast.Raise):
                events.append(f"RAISE|{self._expr_summary(child.exc)}{self._span_ref(child, 'raise', '')}")
            elif isinstance(child, ast.Assert):
                events.append(
                    f"ASSERT|{self._expr_summary(child.test)} msg={self._expr_summary(child.msg)}"
                    f"{self._span_ref(child, 'assert', '')}"
                )
            elif isinstance(child, ast.Expr) and isinstance(child.value, ast.Call):
                events.append(f"CALL|{self._call_summary(child.value)}")
            if len(events) >= limit:
                events.append(f"OMITTED_EVENTS|count>={limit}")
                break
        return events

    def _build_spans(self, tree: ast.AST, profile: ST3GGProfile) -> tuple[tuple[dict[str, Any], ...], list[str]]:
        self._span_by_node_key = {}
        if profile not in _EXACT_SPAN_PROFILES:
            return (), []
        spans: list[dict[str, Any]] = []
        warnings: list[str] = []
        seen_node_keys: set[tuple[int, int, str, str]] = set()
        total_chars = 0
        max_total_chars = {ST3GGProfile.PATCH: 8000, ST3GGProfile.TEST: 10000, ST3GGProfile.VERIFIER: 12000}[profile]
        max_spans = {ST3GGProfile.PATCH: 32, ST3GGProfile.TEST: 40, ST3GGProfile.VERIFIER: 48}[profile]
        target_found = self._target_symbol is None

        def add_span(node: ast.AST, kind: str, name: str = "", *, required: bool = False) -> None:
            nonlocal total_chars, target_found
            if len(spans) >= max_spans or not hasattr(node, "lineno"):
                return
            line_start = int(getattr(node, "lineno", 0) or 0)
            col_start = int(getattr(node, "col_offset", 0) or 0)
            node_key = (line_start, col_start, kind, name)
            if node_key in seen_node_keys:
                return
            text = ast.get_source_segment(self._source, node)
            if text is None:
                text = self._line_slice(node)
            if not text:
                return
            if total_chars + len(text) > max_total_chars and not required:
                warnings.append(f"exact_span_budget_exhausted:profile={profile.value}")
                return
            span_id = f"S{len(spans)}"
            span = {
                "id": span_id,
                "kind": kind,
                "name": name,
                "line_start": line_start,
                "line_end": int(getattr(node, "end_lineno", getattr(node, "lineno", 0)) or 0),
                "col_start": col_start,
                "col_end": int(getattr(node, "end_col_offset", 0) or 0),
                "text": text,
            }
            spans.append(span)
            seen_node_keys.add(node_key)
            total_chars += len(text)
            self._span_by_node_key[(kind, span["line_start"], span["col_start"], name)] = span_id
            if self._target_symbol and name == self._target_symbol:
                target_found = True

        if isinstance(tree, ast.Module):
            for child in tree.body:
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    add_span(child, "import", self._import_name(child))
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    is_target = self._target_symbol is not None and child.name == self._target_symbol
                    if is_target or self._target_symbol is None:
                        add_span(
                            child,
                            "class" if isinstance(child, ast.ClassDef) else "function",
                            child.name,
                            required=is_target,
                        )
        if self._target_symbol and not target_found:
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and node.name == self._target_symbol
                ):
                    add_span(
                        node,
                        "class" if isinstance(node, ast.ClassDef) else "function",
                        node.name,
                        required=True,
                    )
        if profile in {ST3GGProfile.TEST, ST3GGProfile.VERIFIER}:
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    add_span(node, "assert", "")
                elif isinstance(node, ast.Raise):
                    add_span(node, "raise", "")
                elif isinstance(node, ast.Return) and profile == ST3GGProfile.VERIFIER:
                    add_span(node, "return", "")

        if self._target_symbol and not target_found:
            warnings.append(f"target_symbol_not_found:{self._target_symbol}")
        if profile == ST3GGProfile.PATCH and not spans:
            warnings.append("patch_frame_summary_only:no_exact_source_spans")
        return tuple(spans), warnings

    def _line_slice(self, node: ast.AST) -> str:
        start = int(getattr(node, "lineno", 0) or 0)
        end = int(getattr(node, "end_lineno", start) or start)
        if start <= 0 or end <= 0:
            return ""
        return "\n".join(self._source_lines[start - 1 : end])

    def _span_ref(self, node: ast.AST, kind: str, name: str) -> str:
        key = (
            kind,
            int(getattr(node, "lineno", 0) or 0),
            int(getattr(node, "col_offset", 0) or 0),
            name,
        )
        span_id = self._span_by_node_key.get(key)
        return f"|span={span_id}" if span_id else ""

    def _metrics(
        self,
        *,
        source: str,
        encoded: str,
        tree: ast.AST,
        symbols: tuple[dict[str, Any], ...],
        spans: tuple[dict[str, Any], ...],
        warnings: tuple[str, ...],
        fidelity_score: float,
    ) -> ST3GGCodecMetrics:
        raw_tokens = self.estimate_token_cost(source)
        encoded_tokens = self.estimate_token_cost(encoded)
        return ST3GGCodecMetrics(
            raw_char_count=len(source),
            encoded_char_count=len(encoded),
            raw_token_estimate=raw_tokens,
            encoded_token_estimate=encoded_tokens,
            compression_ratio=_ratio(encoded_tokens, raw_tokens),
            ast_node_count=ast_get_node_count(tree),
            symbol_count=len(symbols),
            span_count=len(spans),
            fidelity_score=fidelity_score,
            warnings=warnings,
        )

    def _format_arguments(self, args: ast.arguments) -> str:
        parts: list[str] = []
        positional = list(args.posonlyargs) + list(args.args)
        defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
        for arg, default in zip(positional, defaults):
            parts.append(self._format_arg(arg, default))
        if args.vararg:
            parts.append("*" + self._format_arg(args.vararg, None))
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            parts.append(self._format_arg(arg, default))
        if args.kwarg:
            parts.append("**" + self._format_arg(args.kwarg, None))
        return ",".join(parts)

    def _format_arg(self, arg: ast.arg, default: ast.AST | None) -> str:
        text = self._sym(arg.arg)
        if arg.annotation is not None:
            text += f":{self._expr_summary(arg.annotation)}"
        if default is not None:
            text += f"={self._expr_summary(default)}"
        return text

    def _import_name(self, node: ast.Import | ast.ImportFrom) -> str:
        if isinstance(node, ast.Import):
            return ",".join(alias.asname or alias.name for alias in node.names)
        return f"{node.module or ''}:{','.join(alias.asname or alias.name for alias in node.names)}"

    def _import_line(self, node: ast.Import | ast.ImportFrom) -> str:
        if isinstance(node, ast.Import):
            names = ",".join(
                f"{self._sym(alias.name)}" + (f" as {self._sym(alias.asname)}" if alias.asname else "")
                for alias in node.names
            )
            return f"import {names}"
        module = node.module or ""
        names = ",".join(
            f"{self._sym(alias.name)}" + (f" as {self._sym(alias.asname)}" if alias.asname else "")
            for alias in node.names
        )
        return f"from {module} import {names}"

    def _expr_summary(self, node: ast.AST | None) -> str:
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return self._sym(node.id)
        if isinstance(node, ast.Constant):
            return _literal_summary(node.value)
        if isinstance(node, ast.Attribute):
            return f"{self._expr_summary(node.value)}.{self._sym(node.attr)}"
        if isinstance(node, ast.Call):
            return f"call:{self._call_name(node.func)}"
        if isinstance(node, ast.BinOp):
            return f"{type(node.op).__name__}({self._expr_summary(node.left)},{self._expr_summary(node.right)})"
        if isinstance(node, ast.BoolOp):
            return f"{type(node.op).__name__}[{len(node.values)}]"
        if isinstance(node, ast.Compare):
            ops = ",".join(type(op).__name__ for op in node.ops)
            return f"Compare({self._expr_summary(node.left)} {ops} {len(node.comparators)})"
        if isinstance(node, ast.UnaryOp):
            return f"{type(node.op).__name__}({self._expr_summary(node.operand)})"
        if isinstance(node, ast.Subscript):
            return f"Subscript({self._expr_summary(node.value)})"
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return f"{type(node).__name__}[{len(node.elts)}]"
        if isinstance(node, ast.Dict):
            return f"Dict[{len(node.keys)}]"
        if isinstance(node, ast.JoinedStr):
            return f"fstr[parts={len(node.values)}]"
        if isinstance(node, ast.Lambda):
            return "lambda"
        if isinstance(node, ast.arg):
            return self._sym(node.arg)
        return type(node).__name__

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return self._sym(node.id)
        if isinstance(node, ast.Attribute):
            return f"{self._expr_summary(node.value)}.{self._sym(node.attr)}"
        return self._expr_summary(node)

    def _call_summary(self, node: ast.Call) -> str:
        keywords = [kw.arg for kw in node.keywords if kw.arg]
        return f"{self._call_name(node.func)} args={len(node.args)} kwargs={_join_limited(keywords, 8)}"

    def _assign_summary(self, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> str:
        targets = self._assign_targets(node)
        if isinstance(node, ast.Assign):
            value = self._expr_summary(node.value)
        elif isinstance(node, ast.AnnAssign):
            value = self._expr_summary(node.value)
            if node.annotation:
                value = f"{value}:{self._expr_summary(node.annotation)}"
        else:
            value = f"{type(node.op).__name__} {self._expr_summary(node.value)}"
        return f"{targets}<-{value}"

    def _assign_targets(self, node: ast.AST) -> str:
        if isinstance(node, ast.Assign):
            return ",".join(self._expr_summary(target) for target in node.targets)
        if isinstance(node, ast.AnnAssign):
            return self._expr_summary(node.target)
        if isinstance(node, ast.AugAssign):
            return self._expr_summary(node.target)
        return ""

    def _walk_type(self, node: ast.AST, target_type: type[ast.AST]) -> list[ast.AST]:
        return [item for item in ast.walk(node) if isinstance(item, target_type)]

    def _walk_assignments(self, node: ast.AST) -> list[ast.AST]:
        return [item for item in ast.walk(node) if isinstance(item, (ast.Assign, ast.AnnAssign, ast.AugAssign))]


def choose_profile_for_phase(phase: str) -> ST3GGProfile:
    lowered = str(phase or "").strip().lower()
    if any(term in lowered for term in ("verifier", "verify", "hotswap", "judge", "promotion")):
        return ST3GGProfile.VERIFIER
    if any(
        term in lowered
        for term in ("test generation", "test_generation", "test-gap", "test_gap", "gap_filler", "generate_test")
    ):
        return ST3GGProfile.TEST
    if any(term in lowered for term in ("builder", "patch", "act_worker", "worker")):
        return ST3GGProfile.PATCH
    if any(term in lowered for term in ("localizer", "localiser", "shadow", "grounding", "repo_localizer")):
        return ST3GGProfile.SYMBOLIC
    if any(term in lowered for term in ("planner", "plan", "music", "council", "router")):
        return ST3GGProfile.SUMMARY
    return ST3GGProfile.SYMBOLIC


def compare_raw_vs_encoded(source: str, frame: ST3GGFrame) -> dict[str, Any]:
    codec = ST3GGCodec()
    raw_tokens = codec.estimate_token_cost(source or "")
    encoded_tokens = frame.metrics.encoded_token_estimate
    return {
        "version": frame.version,
        "profile": frame.profile.value,
        "source_hash": frame.source_hash,
        "raw_char_count": len(source or ""),
        "encoded_char_count": frame.metrics.encoded_char_count,
        "raw_token_estimate": raw_tokens,
        "encoded_token_estimate": encoded_tokens,
        "token_delta": raw_tokens - encoded_tokens,
        "compression_ratio": _ratio(encoded_tokens, raw_tokens),
        "fidelity_score": frame.metrics.fidelity_score,
        "ast_node_count": frame.metrics.ast_node_count,
        "symbol_count": frame.metrics.symbol_count,
        "span_count": frame.metrics.span_count,
        "warnings": list(frame.warnings),
    }


def ast_get_node_count(node: ast.AST) -> int:
    return sum(1 for _ in ast.walk(node))


def _ratio(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(part / whole, 6)


def _literal_summary(value: Any) -> str:
    if isinstance(value, str):
        if len(value) > 40:
            return f"str(len={len(value)},h={_short_hash(value)})"
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, bytes):
        return f"bytes(len={len(value)},h={_short_hash(value.hex())})"
    return repr(value)


def _short_hash(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=4).hexdigest()


def _safe_inline(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\r", " ").replace("\n", "\\n")).strip()


def _join_limited(values: list[str] | tuple[str, ...], limit: int) -> str:
    selected = [str(item) for item in values if str(item)]
    if len(selected) > limit:
        return ",".join(selected[:limit]) + f",...+{len(selected) - limit}"
    return ",".join(selected)


def _unique_preserve(values: Any) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out
