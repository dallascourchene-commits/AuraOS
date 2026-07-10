"""
Aura Civic Snapshots — curated official source snapshots with manifests.

Each snapshot has: source_id, publisher, jurisdiction, source_uri, retrieved_at,
as_of, licence, content_digest, media_type, schema_version, record_count,
geographic_scope, evidence_class (OFFICIAL_SNAPSHOT), synthetic (false), known_limitations.
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

SNAPSHOTS_DIR = Path(".aura/civic_snapshots")


def load_snapshot(snapshot_id: str) -> dict[str, Any]:
    """Load a snapshot by ID from the civic_snapshots directory."""
    # Validate snapshot_id to prevent path traversal
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', snapshot_id):
        return {"ok": False, "error": f"invalid snapshot_id: {snapshot_id}"}
    path = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    if not path.exists():
        return {"ok": False, "error": f"snapshot not found: {snapshot_id}"}
    data = json.loads(path.read_text(encoding="utf-8"))
    manifest = data.get("manifest", {})
    # Validate manifest has required fields
    required = ["source_id", "publisher", "jurisdiction", "source_uri",
                "as_of", "licence", "content_digest", "evidence_class"]
    missing = [f for f in required if f not in manifest]
    if missing:
        return {"ok": False, "error": f"manifest missing fields: {missing}"}
    if manifest.get("evidence_class") != "OFFICIAL_SNAPSHOT":
        return {"ok": False, "error": "evidence_class must be OFFICIAL_SNAPSHOT"}
    return {"ok": True, "snapshot": data, "manifest": manifest,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def list_snapshots() -> dict[str, Any]:
    """List all available official snapshots."""
    if not SNAPSHOTS_DIR.exists():
        return {"ok": True, "snapshots": []}
    snapshots = []
    for path in SNAPSHOTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            manifest = data.get("manifest", {})
            snapshots.append({
                "snapshot_id": manifest.get("source_id", path.stem),
                "publisher": manifest.get("publisher", ""),
                "jurisdiction": manifest.get("jurisdiction", ""),
                "as_of": manifest.get("as_of", ""),
                "evidence_class": manifest.get("evidence_class", ""),
                "record_count": manifest.get("record_count", 0),
            })
        except json.JSONDecodeError:
            # Skip malformed snapshot files
            continue
    return {"ok": True, "snapshots": snapshots,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def verify_snapshot_digest(snapshot_id: str) -> dict[str, Any]:
    """Verify the content digest of a snapshot."""
    # Validate snapshot_id to prevent path traversal
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', snapshot_id):
        return {"ok": False, "error": f"invalid snapshot_id: {snapshot_id}"}
    r = load_snapshot(snapshot_id)
    if not r["ok"]:
        return r
    data = r["snapshot"]
    manifest = data["manifest"]
    content = json.dumps(data.get("content", {}), sort_keys=True)
    computed = hashlib.blake2b(content.encode(), digest_size=16).hexdigest()
    expected = manifest.get("content_digest", "")
    return {"ok": computed == expected, "computed": computed, "expected": expected,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
