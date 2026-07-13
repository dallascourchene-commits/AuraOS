from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import urllib.request

WORKFLOW = Path(".github/workflows/diagnose-codemap-once.yml")
SCRIPT = Path("tools/one_time_codemap_stability_fix.py")


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def patch_files() -> None:
    WORKFLOW.unlink()
    verifier = Path("aura_codemap_verify.py")
    text = verifier.read_text(encoding="utf-8")
    old = '_VOLATILE_SUMMARY_FIELDS = frozenset({"elapsed_ms", "last_incremental_refresh_unix"})'
    new = '_VOLATILE_SUMMARY_FIELDS = frozenset({"elapsed_ms", "last_incremental_refresh_unix", "total_bytes", "text_tokens_est"})'
    if old not in text and new not in text:
        raise SystemExit("volatile summary marker not found")
    text = text.replace(old, new)
    old_card = '''        if str(card.get("path") or "") in _SELF_REFERENTIAL_GENERATED_DIGEST_PATHS:
            card["digest8"] = "SELF_REFERENTIAL_GENERATED_ARTIFACT"
'''
    new_card = '''        if str(card.get("path") or "") in _SELF_REFERENTIAL_GENERATED_DIGEST_PATHS:
            card["bytes"] = 0
            card["lines"] = 0
            card["tokens_est"] = 0
            card["digest8"] = "SELF_REFERENTIAL_GENERATED_ARTIFACT"
'''
    if old_card not in text and new_card not in text:
        raise SystemExit("generated card normalization marker not found")
    text = text.replace(old_card, new_card)
    text = text.replace(
        '            "summary.last_incremental_refresh_unix",\n',
        '            "summary.last_incremental_refresh_unix",\n'
        '            "summary.total_bytes/text_tokens_est (includes generated topology artifact)",\n',
    )
    text = text.replace(
        '            "topology_map.json.digest8 (self-referential generated artifact)",\n',
        '            "topology_map.json bytes/lines/tokens_est/digest8 (generated artifact)",\n',
    )
    verifier.write_text(text, encoding="utf-8")

    tests = Path("tests/test_aura_codemap_verify.py")
    test_text = tests.read_text(encoding="utf-8")
    marker = "def test_generated_topology_size_drift_is_normalized():"
    if marker not in test_text:
        test_text += r'''


def test_generated_topology_size_drift_is_normalized():
    reference = _payload()
    regenerated = json.loads(json.dumps(reference))
    reference_card = {
        "path": "topology_map.json",
        "role": "schema_or_lexicon",
        "bytes": 100,
        "lines": 10,
        "tokens_est": 25,
        "symbol_count": 0,
        "commands": [],
        "command_lines": {},
        "digest8": "first-generated-digest",
    }
    regenerated_card = {
        **reference_card,
        "bytes": 141,
        "lines": 12,
        "tokens_est": 35,
        "digest8": "second-generated-digest",
    }
    reference["files"].append(reference_card)
    regenerated["files"].append(regenerated_card)
    reference["summary"]["file_count"] += 1
    regenerated["summary"]["file_count"] += 1
    reference["summary"]["total_bytes"] += reference_card["bytes"]
    regenerated["summary"]["total_bytes"] += regenerated_card["bytes"]
    reference["summary"]["text_tokens_est"] += reference_card["tokens_est"]
    regenerated["summary"]["text_tokens_est"] += regenerated_card["tokens_est"]
    result = compare_codemap_payloads(reference, regenerated)
    assert result["ok"]


def test_real_source_card_size_change_is_still_detected():
    reference = _payload()
    regenerated = json.loads(json.dumps(reference))
    regenerated["files"][0]["bytes"] += 1
    regenerated["summary"]["total_bytes"] += 1
    result = compare_codemap_payloads(reference, regenerated)
    assert not result["ok"]
    assert "source_cards" in result["differing_fields"]
'''
    tests.write_text(test_text, encoding="utf-8")


def validate_and_generate() -> None:
    run("python", "-m", "py_compile", "aura_codemap_verify.py", "tests/test_aura_codemap_verify.py")
    run("ruff", "check", "--select", "E9,F63,F7,F82", "aura_codemap_verify.py", "tests/test_aura_codemap_verify.py")
    run("python", "-m", "pytest", "-q", "tests/test_aura_codemap_verify.py")
    run("python", "aura_codebase_navigator.py")
    first = Path(os.environ["RUNNER_TEMP"]) / "first-codemap.json"
    first.write_bytes(Path(".aura/CODEMAP.json").read_bytes())
    run("python", "aura_codebase_navigator.py")
    run("python", "-m", "aura_codemap_verify", "--compare-json", str(first))


def request(method: str, url: str, payload: dict | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aura-codemap-stability-fix",
    }
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def create_commit() -> str:
    repository = os.environ["GITHUB_REPOSITORY"]
    parent = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    api = f"https://api.github.com/repos/{repository}/git"
    parent_commit = request("GET", f"{api}/commits/{parent}")
    entries = []
    for relative in (
        "aura_codemap_verify.py",
        "tests/test_aura_codemap_verify.py",
        ".aura/CODEMAP.md",
        ".aura/CODEMAP.json",
        "topology_map.json",
    ):
        blob = request(
            "POST",
            f"{api}/blobs",
            {"content": base64.b64encode(Path(relative).read_bytes()).decode(), "encoding": "base64"},
        )
        entries.append({"path": relative, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    for relative in (str(WORKFLOW), str(SCRIPT)):
        entries.append({"path": relative, "mode": "100644", "type": "blob", "sha": None})
    tree = request("POST", f"{api}/trees", {"base_tree": parent_commit["tree"]["sha"], "tree": entries})
    commit = request(
        "POST",
        f"{api}/commits",
        {
            "message": "fix(codemap): normalize generated topology size drift",
            "tree": tree["sha"],
            "parents": [parent],
        },
    )
    out = Path(os.environ["RUNNER_TEMP"]) / "fix-commit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "commit_sha.txt").write_text(commit["sha"] + "\n")
    (out / "parent_sha.txt").write_text(parent + "\n")
    return commit["sha"]


if __name__ == "__main__":
    patch_files()
    validate_and_generate()
    print(create_commit())
