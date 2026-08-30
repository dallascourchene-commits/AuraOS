"""Conservative, non-authoritative intake linter for Aura command envelopes.

This is a BugHound detector, not the deployed consumer parser and not an
admission engine. It classifies structural hazards observed in the Arena corpus
without normalizing malformed commands or resolving authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "BugHoundEnvelopeLintV1"
_TITLE_PREFIX = "AURA COMMAND ENVELOPE —"
_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
# Current Arena corpus canonical Drive IDs are 44 characters. Future alternate
# lengths fail closed here rather than being guessed into authority candidates.
_DRIVE_ID_EXACT_RE = re.compile(r"(?<![A-Za-z0-9_-])(1[A-Za-z0-9_-]{43})(?![A-Za-z0-9_-])")
_FORBIDDEN_LEAVES = {"credentials", "secret", "secrets", "password", "token"}


class LintDisposition(str, Enum):
    STRUCTURALLY_PARSEABLE = "STRUCTURALLY_PARSEABLE"
    NOT_ENVELOPE_TITLE = "NOT_ENVELOPE_TITLE"
    LINE_FORMAT = "LINE_FORMAT"
    TRAILING_TEXT_AFTER_JSON = "TRAILING_TEXT_AFTER_JSON"
    JSON_NOT_OBJECT = "JSON_NOT_OBJECT"
    JSON_INVALID = "JSON_INVALID"


@dataclass(frozen=True)
class LintFindingV1:
    code: str
    field: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class EnvelopeLintReceiptV1:
    disposition: LintDisposition
    parser_surface: str
    fields: tuple[tuple[str, str], ...]
    findings: tuple[LintFindingV1, ...]
    exact_drive_ids: tuple[str, ...]
    safe_to_autorepair: bool = False
    authority_resolved: bool = False
    execution_authorized: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        body = {
            "schema": self.schema,
            "disposition": self.disposition.value,
            "parser_surface": self.parser_surface,
            "fields": list(self.fields),
            "findings": [
                {"code": f.code, "field": f.field, "detail": f.detail} for f in self.findings
            ],
            "exact_drive_ids": list(self.exact_drive_ids),
            "safe_to_autorepair": False,
            "authority_resolved": False,
            "execution_authorized": False,
            "external_effect": False,
        }
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        return hashlib.sha256(b"AURA_BUGHOUND_ENVELOPE_LINT_V1\0" + raw).hexdigest()


def _flatten_json(obj: Mapping[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            out.extend(_flatten_json(value, path))
        else:
            out.append((path, value))
    return out


def _lint_semantics(pairs: list[tuple[str, Any]]) -> tuple[LintFindingV1, ...]:
    findings: list[LintFindingV1] = []
    lowered = {key.lower(): value for key, value in pairs}
    for key, value in pairs:
        leaf = key.rsplit(".", 1)[-1].lower()
        if leaf in _FORBIDDEN_LEAVES:
            findings.append(LintFindingV1("FORBIDDEN_SENSITIVE_FIELD", key, leaf))
        if key.lower() == "constraints" and not isinstance(value, str):
            findings.append(LintFindingV1("NONSTRING_CONSTRAINTS_EFFECT_GATE_RISK", key, type(value).__name__))

    d0_fields = ("requested_effect", "effect_ceiling", "constraints")
    present = [(name, lowered.get(name)) for name in d0_fields if name in lowered]
    for name, value in present:
        if not isinstance(value, str) or value.strip() != "D0":
            findings.append(LintFindingV1("D0_EXACT_DECLARATION_MISMATCH", name, repr(value)))

    authority = lowered.get("authority_ref")
    if authority is None:
        findings.append(LintFindingV1("AUTHORITY_REF_MISSING", "authority_ref", ""))
    elif not isinstance(authority, str):
        findings.append(LintFindingV1("AUTHORITY_REF_NONSTRING", "authority_ref", type(authority).__name__))
    elif not _DRIVE_ID_EXACT_RE.search(authority):
        findings.append(LintFindingV1("AUTHORITY_REF_NO_EXACT_DRIVE_ID", "authority_ref", authority))

    return tuple(findings)


def lint_envelope(text: str) -> EnvelopeLintReceiptV1:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    source = text.lstrip("\ufeff")
    stripped = source.strip()
    if not stripped:
        return EnvelopeLintReceiptV1(
            disposition=LintDisposition.JSON_INVALID,
            parser_surface="EMPTY",
            fields=(),
            findings=(LintFindingV1("EMPTY_ENVELOPE"),),
            exact_drive_ids=(),
        )

    if stripped.startswith("{") or stripped.startswith("["):
        decoder = json.JSONDecoder()
        try:
            value, end = decoder.raw_decode(stripped)
        except json.JSONDecodeError as exc:
            return EnvelopeLintReceiptV1(
                disposition=LintDisposition.JSON_INVALID,
                parser_surface="JSON",
                fields=(),
                findings=(LintFindingV1("JSON_INVALID", detail=exc.msg),),
                exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
            )
        trailing = stripped[end:].strip()
        if trailing:
            return EnvelopeLintReceiptV1(
                disposition=LintDisposition.TRAILING_TEXT_AFTER_JSON,
                parser_surface="JSON",
                fields=(),
                findings=(LintFindingV1("TRAILING_TEXT_AFTER_JSON", detail=trailing[:120]),),
                exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
            )
        if not isinstance(value, dict):
            return EnvelopeLintReceiptV1(
                disposition=LintDisposition.JSON_NOT_OBJECT,
                parser_surface="JSON",
                fields=(),
                findings=(LintFindingV1("JSON_TOP_LEVEL_OBJECT_REQUIRED"),),
                exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
            )
        flat = _flatten_json(value)
        fields = tuple(sorted((k, v if isinstance(v, str) else json.dumps(v, sort_keys=True)) for k, v in flat))
        return EnvelopeLintReceiptV1(
            disposition=LintDisposition.STRUCTURALLY_PARSEABLE,
            parser_surface="JSON",
            fields=fields,
            findings=_lint_semantics(flat),
            exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
        )

    lines = source.splitlines()
    first = lines[0].strip() if lines else ""
    if not first.startswith(_TITLE_PREFIX):
        return EnvelopeLintReceiptV1(
            disposition=LintDisposition.NOT_ENVELOPE_TITLE,
            parser_surface="GOOGLE_DOC_STRICT_PREFLIGHT",
            fields=(),
            findings=(LintFindingV1("NOT_ENVELOPE_TITLE", detail=first[:120]),),
            exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
        )

    pairs: list[tuple[str, Any]] = []
    for lineno, raw in enumerate(lines[1:], start=2):
        line = raw.strip()
        if not line:
            continue
        if ":" not in line:
            return EnvelopeLintReceiptV1(
                disposition=LintDisposition.LINE_FORMAT,
                parser_surface="GOOGLE_DOC_STRICT_PREFLIGHT",
                fields=tuple((k, str(v)) for k, v in pairs),
                findings=(LintFindingV1("LINE_FORMAT", detail=f"line={lineno}"),),
                exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
            )
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not _KEY_RE.fullmatch(key) or not value:
            return EnvelopeLintReceiptV1(
                disposition=LintDisposition.LINE_FORMAT,
                parser_surface="GOOGLE_DOC_STRICT_PREFLIGHT",
                fields=tuple((k, str(v)) for k, v in pairs),
                findings=(LintFindingV1("LINE_FORMAT", detail=f"line={lineno}"),),
                exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
            )
        pairs.append((key, value))

    return EnvelopeLintReceiptV1(
        disposition=LintDisposition.STRUCTURALLY_PARSEABLE,
        parser_surface="GOOGLE_DOC_STRICT_PREFLIGHT",
        fields=tuple(sorted((k, str(v)) for k, v in pairs)),
        findings=_lint_semantics(pairs),
        exact_drive_ids=tuple(sorted(set(_DRIVE_ID_EXACT_RE.findall(source)))),
    )
