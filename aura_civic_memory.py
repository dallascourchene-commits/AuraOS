"""Aura Civic Memory — governed community history archive.

Not a political dossier, ideology profile, reputation score, or training corpus.
"""
from __future__ import annotations
import json, time, hashlib
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

@dataclass
class CivicMemoryRecord:
    record_id: str
    record_type: str
    content_ref: str
    privacy_class: str = "COMMUNITY_ONLY"
    governance_profile: str = ""
    retention_period_days: int = 365
    authorized_audiences: list[str] = field(default_factory=list)
    export_permission: bool = False
    redaction_state: str = "none"
    provenance: str = ""
    revocation_status: str = "active"
    truth_class: str = "COMMUNITY_ASSERTED"
    created_at: float = 0.0
    def to_dict(self): return asdict(self)

class CivicMemoryArchive:
    def __init__(self): self._records: dict[str, CivicMemoryRecord] = {}
    def store(self, record: CivicMemoryRecord) -> dict[str, Any]:
        self._records[record.record_id] = record
        return {"ok": True, "record_id": record.record_id}
    def get(self, rid: str) -> dict[str, Any]:
        r = self._records.get(rid)
        return {"ok": bool(r), "record": r.to_dict() if r else None}
    def export_governed(self, audience: str) -> dict[str, Any]:
        exported = []
        for r in self._records.values():
            if r.revocation_status != "active": continue
            if audience not in r.authorized_audiences and "FACILITATOR_ONLY" != r.privacy_class: continue
            exported.append(r.to_dict())
        return {"ok": True, "records": exported, "count": len(exported)}
    def revoke(self, rid: str) -> dict[str, Any]:
        r = self._records.get(rid)
        if not r: return {"ok": False, "error": "not found"}
        r.revocation_status = "revoked"
        return {"ok": True}
    def check_retention_expiry(self, now: float | None = None) -> dict[str, Any]:
        t = now or time.time()
        expired = [r.record_id for r in self._records.values()
                   if r.created_at + r.retention_period_days * 86400 < t and r.revocation_status == "active"]
        return {"ok": True, "expired": expired}
