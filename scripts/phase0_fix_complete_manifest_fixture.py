from pathlib import Path

path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
text = path.read_text(encoding="utf-8")
old = "    substituted.phase_hash = substituted.compute_digest()\n"
new = (
    "    substituted.phase_hash = \"\"\n"
    "    substituted.phase_hash = substituted.compute_digest()\n"
)
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected exactly one regression-fixture hash assignment, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Corrected self-consistent substituted-manifest fixture")
