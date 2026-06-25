"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f8-[Q-SYS:PHASE_CAPSULE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Deterministic Handoff)
DEPENDENCIES: dataclasses, hashlib, json, zlib
FUNCTIONS: AuraPhaseCapsule, detect_incomplete_json, capture_phase_capsule, resume_instruction, verify_capsule_prefix
SYNOPSIS: Deterministic continuation metadata for handing incomplete AuraFusion work between external models without pretending closed APIs share hidden state.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import zlib

CAPSULE_VERSION = "AURA_PHASE_CAPSULE_V1"
PHASE_LOCK_POWER = 4097


@dataclass
class AuraPhaseCapsule:
    capsule_version: str
    run_id: str
    previous_agent: str
    next_role: str
    target_file: str | None
    target_symbol: str | None
    byte_offset: int
    char_offset: int
    grammar_state: str
    phase_hash: str
    permutation_power: int
    crc32_so_far: str
    tail_context: str
    next_action: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AuraPhaseCapsule:
        return cls(**data)


def detect_incomplete_json(text: str) -> tuple[bool, str]:
    """Return (is_incomplete, grammar_state) for a possibly truncated JSON object."""
    stripped = (text or "").strip()
    if not stripped:
        return True, "EMPTY"
    try:
        json.loads(stripped)
        return False, "JSON_COMPLETE"
    except json.JSONDecodeError as exc:
        opens = stripped.count("{") - stripped.count("}")
        brackets = stripped.count("[") - stripped.count("]")
        if exc.pos >= max(0, len(stripped) - 3) or opens > 0 or brackets > 0:
            return True, f"JSON_INCOMPLETE:{exc.msg}"
        return False, f"JSON_INVALID:{exc.msg}"


def _phase_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def capture_phase_capsule(
    completed_text: str,
    *,
    run_id: str,
    previous_agent: str,
    next_role: str,
    target_file: str | None = None,
    target_symbol: str | None = None,
    grammar_state: str | None = None,
    next_action: str = "Continue from the exact byte boundary and emit only the missing suffix.",
    tail_chars: int = 512,
) -> AuraPhaseCapsule:
    """Capture deterministic continuation state for a partially completed output."""
    text = completed_text or ""
    if grammar_state is None:
        _incomplete, grammar_state = detect_incomplete_json(text)
    prefix_bytes = text.encode("utf-8", errors="replace")
    payload = {
        "run_id": run_id,
        "previous_agent": previous_agent,
        "next_role": next_role,
        "target_file": target_file,
        "target_symbol": target_symbol,
        "byte_offset": len(prefix_bytes),
        "char_offset": len(text),
        "grammar_state": grammar_state,
        "crc32_so_far": f"{zlib.crc32(prefix_bytes) & 0xFFFFFFFF:08x}",
        "tail_context": text[-tail_chars:],
        "next_action": next_action,
        "permutation_power": PHASE_LOCK_POWER,
    }
    return AuraPhaseCapsule(
        capsule_version=CAPSULE_VERSION,
        phase_hash=_phase_hash(payload),
        **payload,
    )


def resume_instruction(capsule: AuraPhaseCapsule) -> str:
    """Compact prompt fragment for the next model in a phase handoff."""
    return json.dumps({
        "capsule_version": capsule.capsule_version,
        "phase_lock": f"PI^{capsule.permutation_power}",
        "run_id": capsule.run_id,
        "next_role": capsule.next_role,
        "target_file": capsule.target_file,
        "target_symbol": capsule.target_symbol,
        "byte_offset": capsule.byte_offset,
        "char_offset": capsule.char_offset,
        "grammar_state": capsule.grammar_state,
        "crc32_so_far": capsule.crc32_so_far,
        "phase_hash": capsule.phase_hash,
        "tail_context": capsule.tail_context,
        "next_action": capsule.next_action,
    }, sort_keys=True)


def verify_capsule_prefix(capsule: AuraPhaseCapsule, completed_text: str) -> bool:
    """Verify the caller is resuming the same prefix captured in the capsule."""
    prefix = (completed_text or "").encode("utf-8", errors="replace")
    return (
        len(prefix) == capsule.byte_offset
        and f"{zlib.crc32(prefix) & 0xFFFFFFFF:08x}" == capsule.crc32_so_far
    )
