"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: typing, __future__, dataclasses, unicodedata
FUNCTIONS: _in_any, _hazard_label, sanitize_tokenizer_channels, sanitize_message_payloads, changed, to_jsonable, warnings, to_jsonable
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import unicodedata

_TAG_RANGE = range(0xE0000, 0xE0080)
_VARIATION_RANGES = (range(0xFE00, 0xFE10), range(0xE0100, 0xE01F0))
_BIDI_RANGES = (range(0x202A, 0x202F), range(0x2066, 0x206A))
_PRIVATE_USE_RANGES = (
    range(0xE000, 0xF900),
    range(0xF0000, 0x100000),
    range(0x100000, 0x110000),
)
_FORMAT_ALLOWLIST = {"\n", "\r", "\t"}


@dataclass(frozen=True)
class TokenizerSanitizationReport:
    sanitized_text: str
    original_chars: int
    sanitized_chars: int
    removed_counts: tuple[tuple[str, int], ...] = ()
    normalized: bool = False

    @property
    def changed(self) -> bool:
        return self.normalized or bool(self.removed_counts) or self.original_chars != self.sanitized_chars

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "original_chars": self.original_chars,
            "sanitized_chars": self.sanitized_chars,
            "normalized": self.normalized,
            "removed_counts": dict(self.removed_counts),
        }

    def warnings(self) -> tuple[str, ...]:
        items = [f"tokenizer_guard_removed_{label}:{count}" for label, count in self.removed_counts]
        if self.normalized:
            items.append("tokenizer_guard_nfkc_normalized")
        return tuple(items)


@dataclass(frozen=True)
class MessageSanitizationBatch:
    messages: list[dict[str, Any]]
    reports: tuple[TokenizerSanitizationReport, ...]

    def to_jsonable(self) -> dict[str, Any]:
        changed = [report for report in self.reports if report.changed]
        totals: dict[str, int] = {}
        for report in changed:
            for label, count in report.removed_counts:
                totals[label] = totals.get(label, 0) + count
        return {
            "changed_message_count": len(changed),
            "removed_counts": totals,
            "normalized_message_count": sum(1 for report in changed if report.normalized),
            "reports": [report.to_jsonable() for report in changed],
        }


def _in_any(codepoint: int, ranges: tuple[range, ...]) -> bool:
    return any(codepoint in item for item in ranges)


def _hazard_label(ch: str) -> str | None:
    codepoint = ord(ch)
    if codepoint in _TAG_RANGE:
        return "tag_char"
    if _in_any(codepoint, _PRIVATE_USE_RANGES):
        return "private_use"
    if _in_any(codepoint, _VARIATION_RANGES):
        return "variation_selector"
    if _in_any(codepoint, _BIDI_RANGES):
        return "bidi_control"
    if unicodedata.category(ch) == "Cf" and ch not in _FORMAT_ALLOWLIST:
        return "format_control"
    return None


def sanitize_tokenizer_channels(text: str) -> TokenizerSanitizationReport:
    """Remove tokenizer-survival carriers and normalize visible text with NFKC."""
    raw = text or ""
    counts: dict[str, int] = {}
    kept: list[str] = []
    for ch in raw:
        label = _hazard_label(ch)
        if label is not None:
            counts[label] = counts.get(label, 0) + 1
            continue
        kept.append(ch)
    stripped = "".join(kept)
    normalized = unicodedata.normalize("NFKC", stripped)
    return TokenizerSanitizationReport(
        sanitized_text=normalized,
        original_chars=len(raw),
        sanitized_chars=len(normalized),
        removed_counts=tuple(sorted(counts.items())),
        normalized=normalized != stripped,
    )


def sanitize_message_payloads(messages: list[dict[str, Any]]) -> MessageSanitizationBatch:
    rewritten: list[dict[str, Any]] = []
    reports: list[TokenizerSanitizationReport] = []
    for message in messages:
        item = dict(message)
        content = item.get("content")
        if isinstance(content, str):
            report = sanitize_tokenizer_channels(content)
            item["content"] = report.sanitized_text
            reports.append(report)
        rewritten.append(item)
    return MessageSanitizationBatch(messages=rewritten, reports=tuple(reports))
