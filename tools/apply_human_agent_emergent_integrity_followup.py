#!/usr/bin/env python3
"""Preserve evidence capture and enforce the pre-admission preview boundary."""

from pathlib import Path

workspace = Path("aura_emergent_refactor_workspace.py")
text = workspace.read_text(encoding="utf-8")
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
    workspace.write_text(text.replace(old, new, 1), encoding="utf-8")


tests = Path("tests/test_aura_emergent_refactor_workspace.py")
test_text = tests.read_text(encoding="utf-8")
old_assertion = '''    assert state.workflow.evidence["emergent_refactor_packet"]["human_approval_required"] is True
'''
new_assertion = '''    assert "emergent_refactor_packet" not in state.workflow.evidence
'''
if new_assertion not in test_text:
    if old_assertion not in test_text:
        raise SystemExit("preview boundary assertion target not found")
    tests.write_text(test_text.replace(old_assertion, new_assertion, 1), encoding="utf-8")
