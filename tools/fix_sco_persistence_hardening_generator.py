"""Correct newline escaping in the one-time persistence hardening generator."""
from pathlib import Path

path = Path(__file__).resolve().parent / "apply_sco_persistence_manual_hardening.py"
text = path.read_text(encoding="utf-8")
old = 'registry_path.write_text(json.dumps(entry) + "\\n", encoding="utf-8")'
new = 'registry_path.write_text(json.dumps(entry) + "\\\\n", encoding="utf-8")'
if new not in text:
    if text.count(old) != 1:
        raise RuntimeError("expected one hardening newline anchor")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
