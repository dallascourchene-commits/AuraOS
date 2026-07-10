"""
Aura Ephemeral Manifest Finalizer — explicit finalization lifecycle.

DRAFT_MANIFEST → enrich → FINALIZE → compute digest → persist immutable.
No mutation after finalization. Any post-finalization change creates a new version.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MANIFEST_STATES = ("DRAFT", "FINALIZED", "SUPERSEDED")


class ManifestFinalizer:
    """Manages manifest finalization with deterministic digest."""

    @staticmethod
    def finalize(manifest_dict: dict[str, Any], *, previous_digest: str = "") -> dict[str, Any]:
        """Finalize a manifest: set state, compute digest, return immutable copy."""
        if manifest_dict.get("manifest_state") == "FINALIZED":
            return {"ok": False, "error": "manifest_already_finalized",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        finalized = dict(manifest_dict)
        finalized["manifest_state"] = "FINALIZED"
        finalized["finalized_at"] = time.time()
        finalized["previous_manifest_digest"] = previous_digest
        # Compute digest over finalized manifest excluding volatile fields
        digest_payload = {k: v for k, v in finalized.items()
                         if k not in ("created_at", "expires_at", "finalized_at", "phase_hash", "signature_or_digest")}
        digest_str = hashlib.blake2b(
            json.dumps(digest_payload, sort_keys=True, default=str).encode(),
            digest_size=16,
        ).hexdigest()
        finalized["phase_hash"] = digest_str
        finalized["signature_or_digest"] = digest_str
        return {"ok": True, "finalized_manifest": finalized, "digest": digest_str,
                "previous_digest": previous_digest,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    @staticmethod
    def verify_digest(finalized_manifest: dict[str, Any], expected_digest: str) -> dict[str, Any]:
        """Verify that a finalized manifest's digest matches."""
        digest_payload = {k: v for k, v in finalized_manifest.items()
                         if k not in ("created_at", "expires_at", "finalized_at", "phase_hash", "signature_or_digest")}
        actual = hashlib.blake2b(
            json.dumps(digest_payload, sort_keys=True, default=str).encode(),
            digest_size=16,
        ).hexdigest()
        match = actual == expected_digest
        return {"ok": match, "actual": actual, "expected": expected_digest,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    @staticmethod
    def check_mutation(original: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        """Detect if a finalized manifest was mutated."""
        orig_clean = {k: v for k, v in original.items()
                     if k not in ("created_at", "expires_at", "finalized_at", "phase_hash", "signature_or_digest")}
        curr_clean = {k: v for k, v in current.items()
                     if k not in ("created_at", "expires_at", "finalized_at", "phase_hash", "signature_or_digest")}
        changed_keys = []
        for k in set(list(orig_clean.keys()) + list(curr_clean.keys())):
            if orig_clean.get(k) != curr_clean.get(k):
                changed_keys.append(k)
        return {"ok": len(changed_keys) == 0, "changed_keys": changed_keys,
                "mutated": len(changed_keys) > 0,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    @staticmethod
    def supersede(old_manifest: dict[str, Any], new_manifest: dict[str, Any]) -> dict[str, Any]:
        """Mark old as SUPERSEDED, finalize new with reference to old."""
        old_digest = old_manifest.get("signature_or_digest", old_manifest.get("phase_hash", ""))
        result = ManifestFinalizer.finalize(new_manifest, previous_digest=old_digest)
        return result
