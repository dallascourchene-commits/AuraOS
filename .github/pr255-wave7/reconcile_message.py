from pathlib import Path

path = Path("aura_ephemeral_workspace_contracts.py")
text = path.read_text(encoding="utf-8")
old = 'raise ValueError("referent evidence must be EXACT and current or bounded")'
new = 'raise ValueError("referent evidence must be current or bounded and EXACT")'
if text.count(old) != 1:
    raise RuntimeError("expected exactly one referent evidence message")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("reconciled referent evidence error wording")
