from __future__ import annotations

import base64
import inspect
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

FINAL_BRANCH = "refactor/model-cognome-telemetry-final"
HELPER_WORKFLOW = Path(".github/workflows/finalize-cognome-telemetry-once.yml")
SCRIPT = Path("tools/one_time_finalize_cognome_telemetry.py")
FINAL_WORKFLOW = Path(".github/workflows/model-cognome-telemetry.yml")
OBSOLETE_WORKFLOWS = (
    Path(".github/workflows/model-cognome-telemetry-v2.yml"),
    Path(".github/workflows/model-cognome-telemetry-v3.yml"),
    Path(".github/workflows/model-cognome-telemetry-v4.yml"),
)

FINAL_WORKFLOW_TEXT = r'''name: Model Cognome Telemetry

on:
  pull_request:
    paths:
      - "aura_model_cognome_telemetry.py"
      - "aura_model_cognome_call_logger.py"
      - "aura_empirical_cost_ledger.py"
      - "tests/test_aura_model_cognome_telemetry.py"
      - "tests/test_aura_model_cognome_call_logger.py"
      - "tests/test_aura_empirical_cost_ledger_v2.py"
      - "tests/test_aura_model_cognome_telemetry_integration.py"
      - ".github/workflows/model-cognome-telemetry.yml"
  push:
    branches:
      - main
      - "refactor/model-cognome-telemetry*"
    paths:
      - "aura_model_cognome_telemetry.py"
      - "aura_model_cognome_call_logger.py"
      - "aura_empirical_cost_ledger.py"
      - "tests/test_aura_model_cognome_telemetry.py"
      - "tests/test_aura_model_cognome_call_logger.py"
      - "tests/test_aura_empirical_cost_ledger_v2.py"
      - "tests/test_aura_model_cognome_telemetry_integration.py"
      - ".github/workflows/model-cognome-telemetry.yml"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  contracts:
    name: Cross-store telemetry contracts (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.12"]
    steps:
      - name: Clone exact source branch
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SOURCE_REF: ${{ github.head_ref || github.ref_name }}
        run: |
          set -euo pipefail
          find . -mindepth 1 -maxdepth 1 -exec rm -rf {} +
          git clone --depth 1 --branch "${SOURCE_REF}" \
            "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" .
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install test tooling
        run: python -m pip install --upgrade pytest ruff
      - name: Compile cross-store telemetry stack
        run: |
          python -m py_compile \
            aura_model_cognome_telemetry.py \
            aura_model_cognome_call_logger.py \
            aura_empirical_cost_ledger.py \
            aura_usage_normalizer.py \
            aura_pricing_registry.py
      - name: Fatal lint checks
        run: |
          ruff check --select E9,F63,F7,F82 \
            aura_model_cognome_telemetry.py \
            aura_model_cognome_call_logger.py \
            aura_empirical_cost_ledger.py \
            tests/test_aura_model_cognome_telemetry.py \
            tests/test_aura_model_cognome_call_logger.py \
            tests/test_aura_empirical_cost_ledger_v2.py \
            tests/test_aura_model_cognome_telemetry_integration.py
      - name: Run cross-store telemetry contracts
        run: |
          python -m pytest -q \
            tests/test_aura_model_cognome_telemetry.py \
            tests/test_aura_model_cognome_call_logger.py \
            tests/test_aura_empirical_cost_ledger_v2.py \
            tests/test_aura_model_cognome_telemetry_integration.py
'''


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def patch_sources() -> None:
    ledger = Path("aura_empirical_cost_ledger.py")
    text = ledger.read_text(encoding="utf-8")
    text = text.replace(
        '        clean.setdefault("comparison_id", "")\n',
        '        clean["comparison_id"] = str(clean.get("comparison_id") or "")\n',
    )
    ledger.write_text(text, encoding="utf-8")

    tests = Path("tests/test_aura_empirical_cost_ledger_v2.py")
    test_text = tests.read_text(encoding="utf-8")
    if "def test_none_comparison_id_normalizes_to_empty_string" not in test_text:
        test_text += r'''


def test_none_comparison_id_normalizes_to_empty_string(tmp_path: Path) -> None:
    with EmpiricalCostLedger(tmp_path) as ledger:
        ledger.record_run({"run_id": "none-comparison", "comparison_id": None})
        assert ledger.get_run("none-comparison")["comparison_id"] == ""
'''
    tests.write_text(test_text, encoding="utf-8")
    FINAL_WORKFLOW.write_text(FINAL_WORKFLOW_TEXT, encoding="utf-8")


def validate_signature() -> None:
    from aura_savings_db import AuraSavingsDB

    parameters = set(inspect.signature(AuraSavingsDB.insert_llm_call).parameters)
    expected = {
        "provider",
        "model",
        "operation",
        "mode",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "latency_ms",
        "request_chars",
        "response_chars",
        "metadata",
    }
    missing = sorted(expected - parameters)
    if missing:
        raise RuntimeError("AuraSavingsDB.insert_llm_call is missing: " + ", ".join(missing))


def remove_temporary_files() -> None:
    for path in (*OBSOLETE_WORKFLOWS, HELPER_WORKFLOW, SCRIPT):
        path.unlink(missing_ok=True)


def validate_and_map() -> None:
    run(
        "python",
        "-m",
        "py_compile",
        "aura_model_cognome_telemetry.py",
        "aura_model_cognome_call_logger.py",
        "aura_empirical_cost_ledger.py",
        "tests/test_aura_model_cognome_telemetry.py",
        "tests/test_aura_model_cognome_call_logger.py",
        "tests/test_aura_empirical_cost_ledger_v2.py",
        "tests/test_aura_model_cognome_telemetry_integration.py",
    )
    run(
        "ruff",
        "check",
        "--select",
        "E9,F63,F7,F82",
        "aura_model_cognome_telemetry.py",
        "aura_model_cognome_call_logger.py",
        "aura_empirical_cost_ledger.py",
        "tests/test_aura_model_cognome_telemetry.py",
        "tests/test_aura_model_cognome_call_logger.py",
        "tests/test_aura_empirical_cost_ledger_v2.py",
        "tests/test_aura_model_cognome_telemetry_integration.py",
    )
    run(
        "python",
        "-m",
        "pytest",
        "-q",
        "tests/test_aura_model_cognome_telemetry.py",
        "tests/test_aura_model_cognome_call_logger.py",
        "tests/test_aura_empirical_cost_ledger_v2.py",
        "tests/test_aura_model_cognome_telemetry_integration.py",
    )
    run("python", "aura_codebase_navigator.py")
    first = Path(os.environ["RUNNER_TEMP"]) / "telemetry-codemap-first.json"
    first.write_bytes(Path(".aura/CODEMAP.json").read_bytes())
    run("python", "aura_codebase_navigator.py")
    run("python", "-m", "aura_codemap_verify", "--compare-json", str(first))


def request(method: str, url: str, payload: dict | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aura-cognome-telemetry-finalizer",
    }
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def create_commit_and_branch() -> tuple[str, str]:
    repository = os.environ["GITHUB_REPOSITORY"]
    parent = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    api = f"https://api.github.com/repos/{repository}/git"
    parent_commit = request("GET", f"{api}/commits/{parent}")
    entries: list[dict[str, object]] = []
    for relative in (
        "aura_empirical_cost_ledger.py",
        "tests/test_aura_empirical_cost_ledger_v2.py",
        str(FINAL_WORKFLOW),
        ".aura/CODEMAP.md",
        ".aura/CODEMAP.json",
        "topology_map.json",
    ):
        blob = request(
            "POST",
            f"{api}/blobs",
            {
                "content": base64.b64encode(Path(relative).read_bytes()).decode("ascii"),
                "encoding": "base64",
            },
        )
        entries.append({"path": relative, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    for relative in (*OBSOLETE_WORKFLOWS, HELPER_WORKFLOW, SCRIPT):
        entries.append({"path": str(relative), "mode": "100644", "type": "blob", "sha": None})
    tree = request(
        "POST",
        f"{api}/trees",
        {"base_tree": parent_commit["tree"]["sha"], "tree": entries},
    )
    commit = request(
        "POST",
        f"{api}/commits",
        {
            "message": "feat(cognome): finalize linked telemetry and verified latency",
            "tree": tree["sha"],
            "parents": [parent],
        },
    )
    ref_payload = {"ref": f"refs/heads/{FINAL_BRANCH}", "sha": commit["sha"]}
    try:
        request("POST", f"{api}/refs", ref_payload)
    except urllib.error.HTTPError as exc:
        if exc.code != 422:
            raise
        request("PATCH", f"{api}/refs/heads/{FINAL_BRANCH}", {"sha": commit["sha"], "force": True})
    return parent, str(commit["sha"])


if __name__ == "__main__":
    patch_sources()
    validate_signature()
    remove_temporary_files()
    validate_and_map()
    parent_sha, commit_sha = create_commit_and_branch()
    print(json.dumps({"parent": parent_sha, "commit": commit_sha, "branch": FINAL_BRANCH}))
