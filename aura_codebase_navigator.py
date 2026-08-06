"""One-use, hash-locked PR2 transport bootstrap.

This file exists only on analysis/pr2-materializer-transport. It reconstructs the
reviewed PR2 transaction, resets onto the exact PR1 merge commit, creates one
nine-file source commit, then execs the canonical Aura navigator from that clean
source commit. It grants no merge or domain authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

SOURCE_SHA = "9c04a1efa57461a6078acb9f3b569766cbd2ab24"
REQUEST_SHA256 = "ce14c4abfb53a0ead81a0396b1d362c18e156611a56081bc176600bf838e17cc"
ARCHIVE_SHA256 = "6061cd9840b1ab1f85e1cd169b709c080fa5a8294e99994c88ef546f3eac8f4f"
BASE_TRANSACTION_DIGEST = "1dab830173cdba71b9578486da8e119a0aac0f8dfa0f23baaacc785711484bd9"
REPAIR_PATCH_SHA256 = "09b7d70297f91e725f5a8c77f6aa4401436adb7a637248a17c9a5e9a1dc5625c"
FINAL_TRANSACTION_DIGEST = "b07b28f1a850d474aea8629725112270423bae041588eac3a310fc8839b09803"
BASE_EXPECTED = {
    ".aura/refactor_objectives/intent_native_ephemeral_workspace_pr2.v1.json": "aa601e1d22c86acd36a6a671fe0bd6604eafab7dad2c1028089a8a904d278562",
    ".aura/waboose_requests/intent_native_ephemeral_workspace_pr2.v1.json": "19cb4862044bb753a121a86797b8424a1fb2d94d0589c99cc21c3b28e412decc",
    "aura_ephemeral_adapter_registry.py": "3ea90ee653ef6850fff7957987b0350380e3d3bf03cbf90b8e567b92dea3e732",
    "aura_ephemeral_registry_store.py": "226afbd58a42c54bff3dfd30a55cf6c94375a9b75d73db6422a242cbbace5333",
    "aura_ephemeral_workspace_runtime_v2.py": "ee979cef330aae39c42ff9f43e607560a5bcf228a1182af9d78353cf2350f22f",
    "docs/AURA_VERIFIED_EPHEMERAL_WORKSPACE_PR2.md": "71d44e792ff4ce5519b157ea8dc1b2c6655851008dfafe3148db4d3a3f1300cf",
    "schemas/aura_spatial_action_certificate_v2.schema.json": "9853ad2b7bc6398aaec5c25fecb0a72c4818ea958f77b14ee5ae1b1cedc88382",
    "schemas/aura_workspace_execution_graph_v2.schema.json": "4d74fcb3791a5eaa8f7387feafb8cd0eb6502d3cc0e4152647f2ea4ab14864ad",
    "tests/test_aura_ephemeral_workspace_runtime_v2.py": "5f21d6accf7349555e1487af4d8a3208814c85484b4e212914f151c0176ba770",
}
FINAL_EXPECTED = {
    **BASE_EXPECTED,
    "aura_ephemeral_registry_store.py": "254566be49c0d0426e307287f94817c882a10699fb3444fb2521015914ba7487",
    "aura_ephemeral_workspace_runtime_v2.py": "67238ea5aca40a84e2eb0f0a43e954dcc64ecdb611cb51e1bf21672a2c91493a",
    "docs/AURA_VERIFIED_EPHEMERAL_WORKSPACE_PR2.md": "16cdb28a5cf0b3d545e103006247ead42fed346fde97c1b72df9217c357917b0",
    "tests/test_aura_ephemeral_workspace_runtime_v2.py": "fbd34e9b0af673865c344b18cdca998263eaa2ba1a90c412492e5ff4ed7bc43b",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def main() -> None:
    repo = Path.cwd()
    if run("git", "rev-parse", "HEAD") == SOURCE_SHA:
        raise SystemExit("bootstrap must run only from the bounded transport head")
    if run("git", "status", "--porcelain=v1"):
        raise SystemExit("transport checkout is dirty")

    payload = "".join(
        (repo / f".aura/pr2_materialize_chunks_v3/{index:03d}.b64").read_text(encoding="utf-8")
        for index in range(16)
    )
    if hashlib.sha256(payload.encode()).hexdigest() != REQUEST_SHA256:
        raise SystemExit("sealed base64 payload hash mismatch")
    archive = base64.b64decode(payload, validate=True)
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise SystemExit("sealed archive hash mismatch")

    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "aura-pr2-exact-transaction"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)
    archive_path = temp / "transaction.tar.gz"
    archive_path.write_bytes(archive)
    extracted = temp / "files"
    extracted.mkdir()
    with tarfile.open(archive_path, "r:gz") as tf:
        members = tf.getmembers()
        if len(members) != len(BASE_EXPECTED) or {m.name for m in members} != set(BASE_EXPECTED):
            raise SystemExit("transaction scope mismatch")
        for member in members:
            relative = Path(member.name)
            if not member.isfile() or relative.is_absolute() or ".." in relative.parts:
                raise SystemExit(f"unsafe archive member: {member.name}")
            source = tf.extractfile(member)
            if source is None:
                raise SystemExit(f"missing archive payload: {member.name}")
            target = extracted / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read())

    actual = {
        path: hashlib.sha256((extracted / path).read_bytes()).hexdigest()
        for path in BASE_EXPECTED
    }
    if actual != BASE_EXPECTED:
        raise SystemExit(f"base file hash mismatch: {actual}")
    digest = hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()
    if digest != BASE_TRANSACTION_DIGEST:
        raise SystemExit("base transaction digest mismatch")

    repair_patch = repo / ".aura/PR2_REPAIR_V2.patch"
    if hashlib.sha256(repair_patch.read_bytes()).hexdigest() != REPAIR_PATCH_SHA256:
        raise SystemExit("repair patch hash mismatch")
    subprocess.run(["git", "apply", "--check", str(repair_patch)], cwd=extracted, check=True)
    subprocess.run(["git", "apply", str(repair_patch)], cwd=extracted, check=True)
    final_actual = {
        path: hashlib.sha256((extracted / path).read_bytes()).hexdigest()
        for path in FINAL_EXPECTED
    }
    if final_actual != FINAL_EXPECTED:
        raise SystemExit(f"final file hash mismatch: {final_actual}")
    final_digest = hashlib.sha256(
        json.dumps(final_actual, sort_keys=True).encode()
    ).hexdigest()
    if final_digest != FINAL_TRANSACTION_DIGEST:
        raise SystemExit("final transaction digest mismatch")

    subprocess.run(["git", "checkout", "--detach", SOURCE_SHA], check=True)
    if run("git", "rev-parse", "HEAD") != SOURCE_SHA:
        raise SystemExit("exact PR1 base checkout failed")
    for path in FINAL_EXPECTED:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(extracted / path, target)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            "aura_ephemeral_adapter_registry.py",
            "aura_ephemeral_registry_store.py",
            "aura_ephemeral_workspace_runtime_v2.py",
            "tests/test_aura_ephemeral_workspace_runtime_v2.py",
        ],
        check=True,
    )
    for path in (
        "schemas/aura_workspace_execution_graph_v2.schema.json",
        "schemas/aura_spatial_action_certificate_v2.schema.json",
        ".aura/refactor_objectives/intent_native_ephemeral_workspace_pr2.v1.json",
        ".aura/waboose_requests/intent_native_ephemeral_workspace_pr2.v1.json",
    ):
        json.loads((repo / path).read_text(encoding="utf-8"))

    subprocess.run(["git", "config", "user.name", "AuraOS Verified Materializer"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", "--", *FINAL_EXPECTED], check=True)
    staged = set(run("git", "diff", "--cached", "--name-only").splitlines())
    if staged != set(FINAL_EXPECTED):
        raise SystemExit(f"staged scope mismatch: {sorted(staged)}")
    subprocess.run(["git", "diff", "--cached", "--check"], check=True)
    subprocess.run(["git", "commit", "-m", "PR2: Add verified ephemeral workspace runtime"], check=True)
    if run("git", "rev-parse", "HEAD^") != SOURCE_SHA:
        raise SystemExit("published source commit has the wrong parent")

    # The workflow owns the only publication step. It applies an exact-SHA,
    # branch-scoped force-with-lease after the canonical navigator finishes.
    # No PATH or git-command rewriting is permitted here.
    os.execv(sys.executable, [sys.executable, str(repo / "aura_codebase_navigator.py")])


if __name__ == "__main__":
    main()
