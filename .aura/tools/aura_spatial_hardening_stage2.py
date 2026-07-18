"""Second-stage exact-source repair for canonical spatial record ownership."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "aura_spatial_contracts.py"

BAD = '''        return result\n\n\ndef _record_value(value: Any) -> Any:\n    if isinstance(value, Enum):\n        return value.value\n    if isinstance(value, CanonicalSpatialRecord):\n        return value.to_dict()\n    if isinstance(value, tuple):\n        return [_record_value(item) for item in value]\n    return value\n\n    @property\n    def digest(self) -> str:\n        return stable_digest(self.to_dict(), digest_size=32)\n'''

GOOD = '''        return result\n\n    @property\n    def digest(self) -> str:\n        return stable_digest(self.to_dict(), digest_size=32)\n\n\ndef _record_value(value: Any) -> Any:\n    if isinstance(value, Enum):\n        return value.value\n    if isinstance(value, CanonicalSpatialRecord):\n        return value.to_dict()\n    if isinstance(value, tuple):\n        return [_record_value(item) for item in value]\n    return value\n'''

text = PATH.read_text(encoding="utf-8")
if GOOD in text:
    raise SystemExit(0)
count = text.count(BAD)
if count != 1:
    raise RuntimeError(
        "aura_spatial_contracts.py: expected one misplaced digest block, "
        f"found {count}"
    )
PATH.write_text(text.replace(BAD, GOOD, 1), encoding="utf-8")
