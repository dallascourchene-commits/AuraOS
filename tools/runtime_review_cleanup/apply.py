from __future__ import annotations

import json
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor for {label}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> None:
    old_request = Path(".aura/runtime_profiles/construction_demo_waboose.v1.json")
    new_request = Path(".aura/waboose_requests/construction_demo.v1.json")
    if not old_request.is_file() or new_request.exists():
        raise RuntimeError("Waboose request move precondition failed")
    request = json.loads(old_request.read_text(encoding="utf-8"))
    changed_files = request.get("changed_files")
    if not isinstance(changed_files, list):
        raise RuntimeError("Waboose changed_files contract is missing")
    new_path = new_request.as_posix()
    if new_path not in changed_files:
        changed_files.insert(1, new_path)
    write_json(new_request, request)
    old_request.unlink()

    runtime_profile = Path(".aura/runtime_profiles/construction_demo.v1.json")
    profile = json.loads(runtime_profile.read_text(encoding="utf-8"))
    replacements = 0
    for row in profile.get("verification_commands", []):
        command = row.get("command") if isinstance(row, dict) else None
        if not isinstance(command, list):
            continue
        for index, value in enumerate(command):
            if value == ".aura/runtime_profiles/construction_demo_waboose.v1.json":
                command[index] = new_path
                replacements += 1
    if replacements != 1:
        raise RuntimeError(f"expected one runtime Waboose request reference, found {replacements}")
    write_json(runtime_profile, profile)

    replace_once(
        Path("README.md"),
        "python scripts/aura_architecture_harness.py --repo-root . runtime --profile .aura/runtime_profiles/construction_demo.v1.json --output-dir ../AuraOS-runtime-evidence/construction\n",
        "python scripts/aura_architecture_harness.py --repo-root . runtime --profile .aura/runtime_profiles/construction_demo.v1.json --output-dir ../AuraOS-runtime-evidence/construction --install-requirements\n",
        "README fresh runtime command",
    )
    replace_once(
        Path("USER_GUIDE.md"),
        "  --output-dir ../AuraOS-runtime-evidence/after \\\n  --baseline-receipt ../AuraOS-runtime-evidence/before/runtime_harness_receipt.json\n",
        "  --output-dir ../AuraOS-runtime-evidence/after \\\n  --baseline-receipt ../AuraOS-runtime-evidence/before/runtime_harness_receipt.json \\\n  --install-requirements\n",
        "USER_GUIDE after-run dependencies",
    )
    replace_once(
        Path("docs/AURA_RUNTIME_REFACTOR_HARNESS.md"),
        "  --output-dir ../AuraOS-runtime-evidence/after \\\n  --baseline-receipt ../AuraOS-runtime-evidence/before/runtime_harness_receipt.json\n",
        "  --output-dir ../AuraOS-runtime-evidence/after \\\n  --baseline-receipt ../AuraOS-runtime-evidence/before/runtime_harness_receipt.json \\\n  --install-requirements\n",
        "runtime harness after-run dependencies",
    )


if __name__ == "__main__":
    main()
