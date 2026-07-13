"""One-time branch finalizer hook; self-removes before tests and CODEMAP."""
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / "aura_federation.py"
text = path.read_text(encoding="utf-8")
old = '''            verifier_result=dict(verifier_result or {}),
            phase_hash=phase_hash,
        )'''
new = '''            verifier_result=dict(verifier_result or {}),
            phase_hash=phase_hash,
            ts=payload["ts"],
        )'''
if old not in text and '            ts=payload["ts"],\n' not in text:
    raise RuntimeError("federation timestamp insertion marker missing")
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
Path(__file__).unlink(missing_ok=True)
