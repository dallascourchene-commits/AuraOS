from __future__ import annotations

from pathlib import Path


path = Path("scripts/apply_coding_waboose_state_authority_hardening.py")
text = path.read_text(encoding="utf-8")
old = '''            "human_review_required": True,
        }

    def _resolve_diff(self, request: AuraReviewRequest) -> tuple[str, list[str]]:
'''
new = '''            "human_review_required": True,
        }

'''
if old not in text:
    raise SystemExit("state hardening generator seam not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
