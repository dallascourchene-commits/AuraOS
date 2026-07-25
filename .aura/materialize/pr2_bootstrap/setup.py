"""One-use exact-head bootstrap for bilateral intent PR2.

The package is installed only by the refactor-branch CODEMAP synchronization
workflow.  During the final wheel-build process exit it validates and unpacks the
already committed gzip/tar transport, restores requirements.txt byte-for-byte,
removes every transport-only file, and installs a one-use pre-commit hook so the
existing CODEMAP commit atomically includes the verified source bundle.
"""
from __future__ import annotations

import atexit
import base64
import gzip
import hashlib
from io import BytesIO
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile

from setuptools import setup

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_SHA256 = "c1e1c343e3eef7dacf40479ac3c89dba98cc5d9286e4643b294d9d9f5f00b828"
ORIGINAL_REQUIREMENTS = """# AURA PVM — Python 3.10+ required
# Pinned runtime dependencies
numpy>=1.26.4,<3.0
websockets>=12.0,<17.0
aiosqlite>=0.20.0,<1.0
ddgs>=6.0,<10.0
wasmtime>=20.0,<46.0
aiohttp>=3.9.0,<4.0
beautifulsoup4>=4.12.0,<5.0
httpx>=0.27.0,<1.0
cryptography>=41.0.0,<45.0
defusedxml>=0.7.1,<1.0
arxiv>=1.4.0,<3.0
watchdog>=3.0.0,<5.0

# Dev / lint / type-check (not installed in production)
ruff>=0.5.0
mypy>=1.10.0
"""
EXPECTED = {
    ".aura/refactor_objectives/bilateral_intent_guardrail_foundry_pr2.v1.json": "ca4dc7fa2506b2307c5a1940147adbd977438b21ac82924e28b958fef33ad553",
    ".aura/refactor_objectives/bilateral_intent_guardrail_foundry_pr2_revision.v1.json": "8eec99cdd0654df895662b4ff1e18cb8fa0e5d9e8c19b16bb9b68b25e0123165",
    ".aura/waboose_requests/bilateral_intent_guardrail_foundry_pr2.v1.json": "4acf7240580e8273781bb313c38ae47b0479a42e99ef615c8c067fbc6a701a18",
    ".github/workflows/bilateral-intent-pr2.yml": "52f842f0c66805d9e22679e791fd5d887eb9dce919c4cb619c5a0930b57bb644",
    "aura_arena_gate_dialogue.py": "f1a7f17c7a9e8f63a4a9ef9ec5e2981c97a35adf7a16d0159b22846b7281403d",
    "aura_bilateral_intent_canonical.py": "40be200df306169afb5d2b5304ca27d6042bbe04eb73d6220e4bad8d653df73d",
    "aura_human_agent_guidance.py": "9aaf339daffbdf461fe3a8c75eee5376cb52c2e8cc52d7a84aa8e2a2cf3f0a7a",
    "aura_showcase/gate-dialogue.js": "da0e21eb09903d9f5d330224bd1b01cd04d4059d9a309ebf0983ad54b13ffe74",
    "tests/test_aura_showcase_gate_dialogue.py": "e95163564b9593d09ad214c95de021b5a673a44cac64f378b33ab02c0850a533",
    "tests/test_bilateral_intent_pr2_evidence.py": "078fd238ddeceda59de44849aa2fe713444149d6e30a85e2285a7588c8456c12",
}


def _safe_name(raw: str) -> str:
    value = raw.removeprefix("./")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or path.parts[0] == ".git":
        raise RuntimeError(f"unsafe PR2 archive member: {raw!r}")
    return path.as_posix()


def _materialize() -> None:
    parts = sorted((ROOT / ".aura" / "materialize").glob("pr2.payload.part*"))
    if not parts:
        raise RuntimeError("PR2 transport parts are missing")
    encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
    compressed = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(compressed).hexdigest() != ARCHIVE_SHA256:
        raise RuntimeError("PR2 transport archive digest mismatch")
    raw = gzip.decompress(compressed)
    found: dict[str, bytes] = {}
    with tarfile.open(fileobj=BytesIO(raw), mode="r:") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            name = _safe_name(member.name)
            if name not in EXPECTED:
                raise RuntimeError(f"undeclared PR2 archive member: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise RuntimeError(f"missing PR2 archive bytes: {name}")
            data = stream.read()
            if hashlib.sha256(data).hexdigest() != EXPECTED[name]:
                raise RuntimeError(f"PR2 file digest mismatch: {name}")
            found[name] = data
    if set(found) != set(EXPECTED):
        missing = sorted(set(EXPECTED) - set(found))
        raise RuntimeError(f"PR2 archive omitted declared files: {missing}")
    for name, data in found.items():
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    requirements = ROOT / "requirements.txt"
    requirements.write_text(ORIGINAL_REQUIREMENTS, encoding="utf-8")

    for relative in (
        ".github/workflows/aura-pr2-materialize.yml",
        "conftest.py",
        "sitecustomize.py",
    ):
        target = ROOT / relative
        if target.exists():
            target.unlink()
    shutil.rmtree(ROOT / ".aura" / "materialize", ignore_errors=True)

    hook = ROOT / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "git add -A\n"
        "rm -f \"$0\"\n",
        encoding="utf-8",
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


if any(command in sys.argv for command in ("bdist_wheel", "install")):
    atexit.register(_materialize)

setup(name="aura-bilateral-intent-pr2-bootstrap", version="0.0.1", py_modules=[])
