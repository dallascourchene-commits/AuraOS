from __future__ import annotations

"""Relocatable exact-line anchors for Memory City source-span addresses.

D0/non-promoting. A successful relocation preserves a semantic span handle but
never preserves exact parent currentness: parent movement still requires rebind.
"""
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from memory_city_navigator import NavigatorError


class AnchorDisposition(str, Enum):
    REUSE_EXACT = "REUSE_EXACT"
    REBIND_PARENT_CURRENTNESS = "REBIND_PARENT_CURRENTNESS"
    REHYDRATE_SPAN = "REHYDRATE_SPAN"
    HOLD_SOURCE_IDENTITY = "HOLD_SOURCE_IDENTITY"
    HOLD_ANCHOR_AMBIGUITY = "HOLD_ANCHOR_AMBIGUITY"


@dataclass(frozen=True)
class AnchoredSpanLocator:
    source_id: str
    parent_export_sha256: str
    start_anchor: str
    end_anchor: str
    start_line: int
    end_line: int
    span_sha256: str
    span_bytes: int
    authority_minted: bool = False


@dataclass(frozen=True)
class AnchorUseResult:
    disposition: AnchorDisposition
    start_line: int | None
    end_line: int | None
    relocated: bool
    reason: str
    authority_minted: bool = False


def _lines(text: str) -> list[str]:
    if not isinstance(text, str):
        raise NavigatorError("provider text must be str")
    return text.splitlines(keepends=True)


def _unique_line(lines: list[str], anchor: str) -> int:
    if not isinstance(anchor, str) or not anchor:
        raise NavigatorError("anchor must be nonempty")
    matches = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == anchor]
    if len(matches) != 1:
        raise NavigatorError("anchor must match exactly one full line")
    return matches[0]


def _locate(text: str, start_anchor: str, end_anchor: str) -> tuple[int, int, bytes]:
    lines = _lines(text)
    start = _unique_line(lines, start_anchor)
    end = _unique_line(lines, end_anchor)
    if end < start:
        raise NavigatorError("end anchor precedes start anchor")
    span = "".join(lines[start:end + 1]).encode("utf-8")
    return start + 1, end + 1, span


def capture_anchored_span(*, source_id: str, provider_text: str,
                          start_anchor: str, end_anchor: str) -> AnchoredSpanLocator:
    if not source_id:
        raise NavigatorError("source_id is required")
    start, end, span = _locate(provider_text, start_anchor, end_anchor)
    return AnchoredSpanLocator(
        source_id=source_id,
        parent_export_sha256=sha256(provider_text.encode("utf-8")).hexdigest(),
        start_anchor=start_anchor,
        end_anchor=end_anchor,
        start_line=start,
        end_line=end,
        span_sha256=sha256(span).hexdigest(),
        span_bytes=len(span),
    )


def evaluate_anchored_span_at_use(locator: AnchoredSpanLocator, *, source_id: str,
                                  provider_text: str) -> AnchorUseResult:
    if source_id != locator.source_id:
        return AnchorUseResult(AnchorDisposition.HOLD_SOURCE_IDENTITY, None, None, False, "source_id_changed")
    try:
        start, end, span = _locate(provider_text, locator.start_anchor, locator.end_anchor)
    except NavigatorError:
        return AnchorUseResult(AnchorDisposition.HOLD_ANCHOR_AMBIGUITY, None, None, False, "anchor_missing_ambiguous_or_reordered")
    relocated = (start, end) != (locator.start_line, locator.end_line)
    if sha256(span).hexdigest() != locator.span_sha256:
        return AnchorUseResult(AnchorDisposition.REHYDRATE_SPAN, start, end, relocated, "anchored_span_changed")
    parent_root = sha256(provider_text.encode("utf-8")).hexdigest()
    if parent_root != locator.parent_export_sha256:
        return AnchorUseResult(AnchorDisposition.REBIND_PARENT_CURRENTNESS, start, end, relocated, "parent_changed_span_equal")
    return AnchorUseResult(AnchorDisposition.REUSE_EXACT, start, end, False, "exact_parent_and_span")
