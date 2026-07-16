#!/usr/bin/env python3
"""Keep evidence ingestion permissive while refactor selection remains fail-closed."""

from pathlib import Path

path = Path("aura_emergent_refactor_workspace.py")
text = path.read_text(encoding="utf-8")
old = '''        requested_links = _unique(str(item) for item in linked_finding_ids if str(item).strip())
        missing_links = [item for item in requested_links if not self.get_finding(item).get("ok")]
        if missing_links:
            return {
                "ok": False,
                "error": "unresolved_linked_finding_ids",
                "missing_finding_ids": missing_links,
                "created": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        stable_payload = {
'''
new = '''        requested_links = _unique(str(item) for item in linked_finding_ids if str(item).strip())
        stable_payload = {
'''
if new not in text:
    if old not in text:
        raise SystemExit("evidence-ingestion boundary target not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
