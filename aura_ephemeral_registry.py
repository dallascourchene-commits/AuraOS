"""
Aura Ephemeral Registry — track active and dissolved ephemeral organs.

Tracks: organ_id, manifest digest, state, expiry, capability lease,
sandbox path, verifier status, dissolution receipt, crystallization proposal.

No raw secret config may be returned. Persist only minimum audit data.

Dependencies: stdlib only.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass
class EphemeralOrganRecord:
    organ_id: str
    manifest_digest: str
    state: str
    created_at: float
    expires_at: float
    capability_lease: list[str] = field(default_factory=list)
    sandbox_path: str = ""
    verifier_status: str = "pending"
    dissolution_receipt: dict[str, Any] = field(default_factory=dict)
    crystallization_proposal: dict[str, Any] = field(default_factory=dict)
    objective: str = ""
    ttl_seconds: int = 300
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    @property
    def is_active(self) -> bool:
        return self.state not in ("DISSOLVED", "FAILED") and not self.is_expired


class EphemeralRegistry:
    """In-memory registry for ephemeral organs. No secrets stored."""

    def __init__(self) -> None:
        self._organs: dict[str, EphemeralOrganRecord] = {}

    def register(self, record: EphemeralOrganRecord) -> dict[str, Any]:
        """Register a new ephemeral organ."""
        self._organs[record.organ_id] = record
        return {"ok": True, "organ_id": record.organ_id, "state": record.state,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def get(self, organ_id: str) -> dict[str, Any]:
        """Get an organ record (no secrets)."""
        record = self._organs.get(organ_id)
        if not record:
            return {"ok": False, "error": f"organ not found: {organ_id}",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "organ": record.to_dict(),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def update_state(self, organ_id: str, new_state: str) -> dict[str, Any]:
        """Update an organ's state."""
        record = self._organs.get(organ_id)
        if not record:
            return {"ok": False, "error": f"organ not found: {organ_id}",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        record.state = new_state
        return {"ok": True, "organ_id": organ_id, "state": new_state,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def set_dissolution_receipt(self, organ_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        """Record dissolution receipt."""
        record = self._organs.get(organ_id)
        if not record:
            return {"ok": False, "error": f"organ not found: {organ_id}"}
        record.dissolution_receipt = receipt
        record.state = "DISSOLVED"
        return {"ok": True, "organ_id": organ_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def set_crystallization_proposal(self, organ_id: str, proposal: dict[str, Any]) -> dict[str, Any]:
        """Record a crystallization proposal (review only, no automatic promotion)."""
        record = self._organs.get(organ_id)
        if not record:
            return {"ok": False, "error": f"organ not found: {organ_id}"}
        record.crystallization_proposal = proposal
        record.state = "CRYSTALLIZATION_PROPOSED"
        return {"ok": True, "organ_id": organ_id, "note": "proposal_only_no_automatic_promotion",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def list_active(self) -> dict[str, Any]:
        """List all active (non-dissolved, non-expired) organs."""
        active = [r.to_dict() for r in self._organs.values() if r.is_active]
        return {"ok": True, "active_organs": active, "count": len(active),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def list_all(self) -> dict[str, Any]:
        """List all organs including dissolved."""
        all_records = [r.to_dict() for r in self._organs.values()]
        return {"ok": True, "organs": all_records, "count": len(all_records),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def check_expired(self) -> dict[str, Any]:
        """Check for expired organs that need dissolution."""
        expired = [r.organ_id for r in self._organs.values() if r.is_expired and r.state not in ("DISSOLVED", "DISSOLVING")]
        return {"ok": True, "expired_organ_ids": expired, "count": len(expired),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def export_audit(self) -> dict[str, Any]:
        """Export minimum audit data. No secrets, no raw private prompts."""
        audit_records = []
        for r in self._organs.values():
            audit_records.append({
                "organ_id": r.organ_id,
                "manifest_digest": r.manifest_digest,
                "state": r.state,
                "created_at": r.created_at,
                "expires_at": r.expires_at,
                "verifier_status": r.verifier_status,
                "dissolved": r.state == "DISSOLVED",
                "capabilities_revoked": bool(r.dissolution_receipt),
            })
        return {"ok": True, "audit_records": audit_records, "count": len(audit_records),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


# Module-level singleton
_registry: EphemeralRegistry | None = None


def get_registry() -> EphemeralRegistry:
    global _registry
    if _registry is None:
        _registry = EphemeralRegistry()
    return _registry
