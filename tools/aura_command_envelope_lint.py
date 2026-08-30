from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DRIVE_ID_RE = re.compile(r"\b1[A-Za-z0-9_-]{32,43}\b")
SUPPORTED_SCHEMA = "AuraCommandEnvelopeV1-candidate"
FORBIDDEN_KEYS = frozenset({"executor_command"})
PROFILE = "AuraCommandEnvelopeV1-candidate/D0-authoring"


def extract_drive_ids(text: str) -> list[str]:
    """Extract candidate Google Drive IDs without consuming prose prefixes."""
    if not isinstance(text, str) or not text:
        return []
    return list(dict.fromkeys(DRIVE_ID_RE.findall(text)))


def _find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text.casefold() in FORBIDDEN_KEYS:
                found.append(child_path)
            found.extend(_find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, f"{path}[{index}]"))
    return found


def _receipt(*, errors: list[str], warnings: list[str], drive_ids: list[str]) -> dict[str, Any]:
    return {
        "valid": not errors,
        "profile": PROFILE,
        "errors": errors,
        "warnings": warnings,
        "drive_ids": drive_ids,
        # Structural lint can prove only that a resolvable-looking coordinate is present.
        # It does not walk Drive, establish current owner authority, or prove execution.
        "authority_resolution": "UNVERIFIED",
    }


def validate_d0_envelope(env: Any) -> dict[str, Any]:
    """Validate the observed hardened D0 authoring profile, not runtime authority.

    This deliberately fails closed on shape ambiguity. It mirrors the current
    author-side constraints established by the 2026-08-30 Arena admission and
    dispatcher evidence: byte-exact D0 declarations, JSON-first envelopes,
    real Drive-ID candidates, a dispatcher-compatible ``objective.text`` field,
    and no known raw executor-command key. Runtime currentness, authority walks,
    allowlisting, provider admission, and effect execution remain separate gates.
    """
    errors: list[str] = []
    warnings: list[str] = []
    drive_ids: list[str] = []

    if not isinstance(env, dict):
        return _receipt(errors=["ENVELOPE_NOT_OBJECT"], warnings=[], drive_ids=[])

    if env.get("schema") != SUPPORTED_SCHEMA:
        errors.append("SCHEMA_UNSUPPORTED")

    for key in ("command_id", "idempotency_key"):
        value = env.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{key.upper()}_MISSING")

    authority_ref = env.get("authority_ref")
    if not isinstance(authority_ref, str) or not authority_ref:
        errors.append("AUTHORITY_REF_MISSING")
    else:
        drive_ids = extract_drive_ids(authority_ref)
        if not drive_ids:
            errors.append("AUTHORITY_REF_NO_DRIVE_ID")

    if env.get("execution_authorized") is not True:
        errors.append("EXECUTION_AUTHORIZED_NOT_TRUE")

    if env.get("effect_ceiling") != "D0":
        errors.append("EFFECT_CEILING_NOT_EXACT_D0")

    if "constraints" in env and env.get("constraints") != "D0":
        errors.append("CONSTRAINTS_NOT_EXACT_D0")

    objective = env.get("objective")
    if not isinstance(objective, dict):
        errors.append("OBJECTIVE_NOT_OBJECT")
    else:
        if objective.get("requested_effect") != "D0":
            errors.append("REQUESTED_EFFECT_NOT_EXACT_D0")
        text = objective.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append("OBJECTIVE_TEXT_MISSING")

    work_order_ref = env.get("work_order_ref")
    if not isinstance(work_order_ref, str) or not work_order_ref:
        errors.append("WORK_ORDER_REF_MISSING")
    elif not extract_drive_ids(work_order_ref):
        errors.append("WORK_ORDER_REF_NO_DRIVE_ID")

    forbidden = _find_forbidden_keys(env)
    if forbidden:
        errors.append("FORBIDDEN_KEY:" + ",".join(forbidden))

    currentness = env.get("currentness")
    if currentness is None:
        warnings.append("CURRENTNESS_BLOCK_MISSING")
    elif not isinstance(currentness, dict):
        errors.append("CURRENTNESS_NOT_OBJECT")
    elif currentness.get("resolve_awj001_current_at_admission") is not True:
        warnings.append("CURRENTNESS_REBIND_NOT_EXPLICIT")

    return _receipt(errors=errors, warnings=warnings, drive_ids=drive_ids)


def lint_text(text: str) -> dict[str, Any]:
    """Parse one JSON envelope and return a deterministic lint receipt."""
    try:
        # Google Docs / Drive exports may include a UTF-8 BOM. json.loads rejects
        # it, while the live consumer explicitly tolerates it.
        env = json.loads(text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        return _receipt(
            errors=[f"JSON_PARSE_ERROR:{exc.msg}@{exc.lineno}:{exc.colno}"],
            warnings=[],
            drive_ids=[],
        )
    return validate_d0_envelope(env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed structural lint for Aura D0 command envelopes."
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    try:
        text = args.path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        receipt = _receipt(errors=[f"READ_ERROR:{exc}"], warnings=[], drive_ids=[])
        print(json.dumps(receipt, sort_keys=True))
        return 2

    receipt = lint_text(text)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
