"""Arena-aware J1 continuity packets with backwards-compatible J0 parsing.

J1 packets are compact advisory state. They never replace exact evidence, leases,
source hashes, tests, policy records, or verifier authority.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

ARENA_STATE_PACKET_VERSION = "AURA_ARENA_STATE_PACKET_J1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_PREFIX = "J1/"


@dataclass(frozen=True)
class ArenaStatePacket:
    arena_id: str
    arena_version: str
    grammar_version: str
    phase: str
    substate: str
    state_code: str
    focus_digest: str = ""
    evidence_digest: str = ""
    policy_digest: str = ""
    lease_digest: str = ""
    repository_commit: str = ""
    working_tree_digest: str = ""
    selected_transition: str = ""
    next_state: str = ""
    phase_hash: str = ""
    verifier_requirement: str = "none"
    packet_version: str = ARENA_STATE_PACKET_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def canonical_identity(self) -> tuple[str, ...]:
        return (
            self.arena_id,
            self.arena_version,
            self.grammar_version,
            self.state_code,
            self.phase_hash,
            self.evidence_digest,
            self.policy_digest,
            self.repository_commit or self.working_tree_digest,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_arena_state_packet(
    *,
    arena_id: str,
    arena_version: str,
    grammar_version: str,
    phase: str,
    substate: str = "",
    state_code: str = "",
    focus_digest: str = "",
    evidence_digest: str = "",
    policy_digest: str = "",
    lease_digest: str = "",
    repository_commit: str = "",
    working_tree_digest: str = "",
    selected_transition: str = "",
    next_state: str = "",
    verifier_requirement: str = "none",
) -> tuple[ArenaStatePacket, str]:
    core = {
        "arena_id": _text(arena_id),
        "arena_version": _text(arena_version),
        "grammar_version": _text(grammar_version),
        "phase": _text(phase),
        "substate": _text(substate),
        "state_code": _text(state_code or phase),
        "focus_digest": _digest_text(focus_digest),
        "evidence_digest": _digest_text(evidence_digest),
        "policy_digest": _digest_text(policy_digest),
        "lease_digest": _digest_text(lease_digest),
        "repository_commit": _digest_text(repository_commit),
        "working_tree_digest": _digest_text(working_tree_digest),
        "selected_transition": _text(selected_transition),
        "next_state": _text(next_state),
        "verifier_requirement": _text(verifier_requirement or "none"),
    }
    if not core["arena_id"] or not core["grammar_version"] or not core["phase"]:
        raise ValueError("arena_id, grammar_version, and phase are required")
    phase_hash = _hash(core)
    packet = ArenaStatePacket(**core, phase_hash=phase_hash)
    encoded = _encode_payload(packet.to_dict())
    return packet, f"{_PREFIX}{encoded}#{phase_hash}"


def parse_arena_state_packet(raw_packet: str) -> dict[str, Any]:
    raw = str(raw_packet or "").strip()
    if raw.startswith("J0/"):
        try:
            from aura_jspace_codec import parse_jspace_packet
            return {
                "ok": True,
                "legacy": True,
                "packet_version": "J0",
                "state": parse_jspace_packet(raw),
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:
            return {"ok": False, "legacy": True, "error": f"legacy_j0_parse_failed:{type(exc).__name__}"}
    if not raw.startswith(_PREFIX):
        return {"ok": False, "error": "unsupported_state_packet_prefix"}
    body = raw[len(_PREFIX):]
    encoded, separator, supplied_hash = body.rpartition("#")
    if not separator or not encoded or not supplied_hash:
        return {"ok": False, "error": "malformed_j1_packet"}
    try:
        data = _decode_payload(encoded)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"ok": False, "error": f"invalid_j1_payload:{type(exc).__name__}"}
    if not isinstance(data, dict):
        return {"ok": False, "error": "j1_payload_not_object"}
    recorded_hash = str(data.get("phase_hash") or "")
    if supplied_hash != recorded_hash:
        return {"ok": False, "error": "j1_phase_hash_suffix_mismatch"}
    core = {key: value for key, value in data.items() if key not in {"phase_hash", "packet_version", "patch_authority", "vsa_patch_authority"}}
    if _hash(core) != recorded_hash:
        return {"ok": False, "error": "j1_phase_hash_invalid"}
    try:
        packet = ArenaStatePacket(**{key: data.get(key) for key in ArenaStatePacket.__dataclass_fields__})
    except TypeError as exc:
        return {"ok": False, "error": f"j1_schema_invalid:{exc}"}
    return {
        "ok": True,
        "legacy": False,
        "packet_version": ARENA_STATE_PACKET_VERSION,
        "state": packet.to_dict(),
        "canonical_identity": list(packet.canonical_identity()),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _encode_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")


def _decode_payload(value: str) -> dict[str, Any]:
    padding = "=" * ((4 - len(value) % 4) % 4)
    raw = base64.urlsafe_b64decode((value + padding).encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def _hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _digest_text(value: Any) -> str:
    return str(value or "").strip()[:256]
