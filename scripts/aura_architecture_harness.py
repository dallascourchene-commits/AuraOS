#!/usr/bin/env python3
"""Reproducible full-repository harness for Aura architecture analysis.

Runs Aura's Connectome, Relational Index, Relationship Atlas, Emergent
Properties, and proposal-only Architect surfaces. It never applies patches or
grants execution authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable
import venv

VERSION = "AURA_ARCHITECTURE_HARNESS_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
MAX_REFERENCE_FILES = 8
MAX_REFERENCE_BYTES = 2_000_000
DEFAULT_OBJECTIVE = (
    "make a new function that combines the properties of Connectome, "
    "Relational Synthesis, and Atlas to code better"
)
REQUIRED_REPOSITORY_FILES = (
    "aura_capability_connectome.py",
    "aura_capability_connectome_v2.py",
    "aura_relational_index.py",
    "aura_relationship_atlas.py",
    "aura_relational_synthesis.py",
    "aura_emergent_potential_repl.py",
    "aura_architect_loop.py",
    "aura_live_architect.py",
    ".aura/CODEMAP.json",
)
TARGET_IMPORTS = tuple(path.removesuffix(".py") for path in REQUIRED_REPOSITORY_FILES[:-1])


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode(), digest_size=16).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    tmp.replace(path)


def _reference_manifest(values: Iterable[str | Path]) -> list[dict[str, Any]]:
    paths = [Path(value).expanduser().resolve() for value in values]
    if len(paths) > MAX_REFERENCE_FILES:
        raise ValueError(f"at most {MAX_REFERENCE_FILES} reference files are allowed")
    manifest: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"reference file is missing: {path}")
        size = path.stat().st_size
        if size > MAX_REFERENCE_BYTES:
            raise ValueError(
                f"reference file exceeds {MAX_REFERENCE_BYTES} bytes: {path}"
            )
        body = path.read_bytes()
        manifest.append(
            {
                "name": path.name,
                "path": str(path),
                "size_bytes": size,
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    return manifest


def _run(cmd: list[str], root: Path, *, check: bool = True, timeout: int = 300,
         env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env or {})
    return subprocess.run(cmd, cwd=root, check=check, capture_output=True,
                          text=True, timeout=timeout, env=merged)


def _root(value: str | Path) -> Path:
    root = Path(value).expanduser().resolve()
    missing = [name for name in REQUIRED_REPOSITORY_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("incomplete AuraOS repository; missing: " + ", ".join(missing))
    return root


def _venv_python(path: Path) -> Path:
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _git_info(root: Path) -> dict[str, Any]:
    if shutil.which("git") is None or not (root / ".git").exists():
        return {"available": False, "clean": False, "head": "", "status": []}
    status = [line for line in _run(["git", "status", "--porcelain"], root).stdout.splitlines() if line]
    value = lambda *args: _run(["git", *args], root, check=False).stdout.strip()
    return {
        "available": True,
        "head": value("rev-parse", "HEAD"),
        "branch": value("branch", "--show-current"),
        "clean": not status,
        "status": status,
        "synthetic_local_identity": value("config", "--get", "aura.harnessSyntheticIdentity") == "true",
        "source_sha": value("config", "--get", "aura.harnessSourceSha"),
    }


def _init_git(root: Path, source_sha: str) -> dict[str, Any]:
    if (root / ".git").exists():
        return _git_info(root)
    if shutil.which("git") is None:
        raise RuntimeError("git is required for Aura's repository identity")
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.name", "Aura Architecture Harness"],
        ["git", "config", "user.email", "aura-harness@local.invalid"],
        ["git", "config", "aura.harnessSyntheticIdentity", "true"],
        ["git", "config", "aura.harnessSourceSha", source_sha or "UNSPECIFIED"],
        ["git", "add", "-A"],
    ):
        _run(cmd, root, timeout=600)
    message = "chore: establish local Aura harness snapshot"
    if source_sha:
        message += f"\n\nSource-GitHub-SHA: {source_sha}"
    _run(["git", "commit", "-m", message], root, timeout=600)
    return _git_info(root)


def _probe(python: Path, root: Path) -> dict[str, Any]:
    code = (
        "import importlib,json\n"
        f"mods={list(TARGET_IMPORTS)!r}\n"
        "out={}\n"
        "for name in mods:\n"
        " try:\n"
        "  m=importlib.import_module(name);out[name]={'ok':True,'file':getattr(m,'__file__','')}\n"
        " except Exception as e: out[name]={'ok':False,'error':f'{type(e).__name__}: {e}'}\n"
        "print(json.dumps(out,sort_keys=True))\n"
    )
    process = _run([str(python), "-c", code], root, check=False,
                   env={"PYTHONPATH": str(root)})
    if process.returncode:
        return {"ok": False, "error": process.stderr or process.stdout, "modules": {}}
    modules = json.loads(process.stdout)
    return {"ok": all(row["ok"] for row in modules.values()), "modules": modules}


def prepare(root: Path, venv_path: Path, *, system_packages: bool,
            install_requirements: bool, initialize_git: bool,
            source_sha: str) -> dict[str, Any]:
    identity = _init_git(root, source_sha) if initialize_git else _git_info(root)
    if not venv_path.exists():
        venv.EnvBuilder(with_pip=True, system_site_packages=system_packages).create(venv_path)
    python = _venv_python(venv_path)
    install: dict[str, Any] = {"requested": install_requirements, "ran": False}
    if install_requirements:
        result = _run([str(python), "-m", "pip", "install", "-r", "requirements.txt"],
                      root, check=False, timeout=1800)
        install = {"requested": True, "ran": True, "returncode": result.returncode,
                   "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-2000:]}
    imports = _probe(python, root)
    output = {
        "ok": imports["ok"], "version": VERSION, "repo_root": str(root),
        "venv_path": str(venv_path), "python": str(python),
        "python_version": _run([str(python), "--version"], root).stdout.strip(),
        "system_site_packages": system_packages, "git_identity": identity,
        "requirements_install": install, "target_imports": imports,
        "safe_to_patch": False, "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
    }
    manifest = venv_path / "aura_harness_environment.json"
    _write(manifest, output)
    output["manifest_path"] = str(manifest)
    return output


def doctor(root: Path, python: Path | None) -> dict[str, Any]:
    codemap = json.loads((root / ".aura/CODEMAP.json").read_text())
    output = {
        "ok": True, "version": VERSION, "repo_root": str(root),
        "git_identity": _git_info(root),
        "codemap": {
            "file_count": len(codemap.get("files") or []),
            "symbol_count": len(codemap.get("symbol_index") or []),
            "digest": _digest(codemap),
        },
        "safe_to_patch": False, "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
    }
    if python and python.is_file():
        output["target_imports"] = _probe(python, root)
        output["ok"] = output["target_imports"]["ok"]
    return output


def run_architecture(root: Path, *, objective: str, combine_with: list[str],
                     profile: str, top: int, pair_limit: int,
                     allow_expansive: bool, output_dir: str | Path,
                     resume: bool, enforce_clean: bool,
                     reference_files: list[str] | None = None) -> dict[str, Any]:
    sys.path.insert(0, str(root))
    from aura_architect_loop import ArchitectFusionLoop
    from aura_capability_connectome import build_capability_connectome
    from aura_capability_connectome_v2 import enrich_connectome
    from aura_emergent_potential_repl import audit_emergent_potential
    from aura_relational_index import build_relational_index
    from aura_relationship_atlas import build_relationship_atlas

    started = time.time()
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_manifest = _reference_manifest(reference_files or [])
    request = {
        "version": VERSION, "repo_identity": _git_info(root),
        "objective": objective, "combine_with": combine_with,
        "atlas_profile": profile.upper(), "top": top,
        "pair_limit": pair_limit, "allow_expansive": allow_expansive,
        "reference_files": reference_manifest,
    }
    request["digest"] = _digest(request)
    request_path = output_dir / "harness_request.json"
    if resume and request_path.exists():
        if json.loads(request_path.read_text()).get("digest") != request["digest"]:
            raise RuntimeError("resume request does not match retained artifacts")
    else:
        _write(request_path, request)

    connectome_path = output_dir / "connectome.json"
    if resume and connectome_path.exists():
        connectome = json.loads(connectome_path.read_text())
    else:
        connectome = enrich_connectome(build_capability_connectome(root))
        _write(connectome_path, connectome)

    index_path = output_dir / "relational_index.json"
    index_summary_path = output_dir / "relational_index_summary.json"
    if resume and index_path.exists() and index_summary_path.exists():
        index_data = json.loads(index_path.read_text())
        index_summary = json.loads(index_summary_path.read_text())
    else:
        built = build_relational_index(root, profile="STANDARD", persist=False, include_index=True)
        index_data = built.pop("index")
        index_summary = built
        _write(index_path, index_data)
        _write(index_summary_path, index_summary)

    participants = int(index_summary.get("participant_count") or 0)
    pairs = participants * max(0, participants - 1) // 2
    profile = profile.upper()
    if profile not in {"MINIMAL", "STANDARD", "DEEP"}:
        raise ValueError("atlas profile must be MINIMAL, STANDARD, or DEEP")
    if profile != "MINIMAL" and pairs > pair_limit and not allow_expansive:
        raise RuntimeError(
            f"refusing {profile} scan over {pairs:,} participant pairs; "
            "use MINIMAL or explicitly allow the expansive scan"
        )

    atlas_path = output_dir / "relationship_atlas.json"
    receipt_path = output_dir / "relationship_atlas_receipt.json"
    if resume and atlas_path.exists():
        atlas = json.loads(atlas_path.read_text())
    else:
        snapshot = build_relationship_atlas(
            repo_root=root,
            profile=profile,
            relational_index_data=index_data,
            persist=False,
        )
        atlas = snapshot.to_dict()
        _write(atlas_path, atlas)
        _write(
            receipt_path,
            {
                "snapshot_digest": snapshot.snapshot_digest,
                "assessments_count": len(snapshot.assessments),
                "prohibitions_count": len(snapshot.prohibitions),
                "missing_configurations_count": len(snapshot.missing_configurations),
                "operational_profile": profile,
                "freshness": "CURRENT",
                "persistence": "external_harness_artifact_only",
            },
        )

    emergent_path = output_dir / "emergent_properties.json"
    if resume and emergent_path.exists():
        emergent = json.loads(emergent_path.read_text())
    else:
        report = audit_emergent_potential(
            root, top=top, focus=objective,
            new_function_description=objective, combine_with=combine_with,
        )
        emergent = report.to_dict()
        _write(emergent_path, emergent)

    architect_path = output_dir / "architect_preparation.json"
    if resume and architect_path.exists():
        architect = json.loads(architect_path.read_text())
    else:
        prepared = ArchitectFusionLoop(repo_root=root).prepare(
            objective,
            architecture_decision=(
                "Compile an objective-scoped, evidence-bound coding relationship "
                "capsule from Connectome anatomy, Atlas meaning, and Relational "
                "Synthesis composition; remain proposal-only."
            ),
            act_tasks=[
                {"objective": "Resolve the smallest capability path.",
                 "target_file": "aura_capability_connectome.py",
                 "target_symbol": "build_capability_connectome"},
                {"objective": "Classify required, missing, candidate, and prohibited relations.",
                 "target_file": "aura_relationship_atlas.py",
                 "target_symbol": "build_relationship_atlas"},
                {"objective": "Compile the objective-specific synthesis capsule.",
                 "target_file": "aura_relational_synthesis.py"},
                {"objective": "Ground combinations with Emergent Properties.",
                 "target_file": "aura_emergent_potential_repl.py",
                 "target_symbol": "audit_emergent_potential"},
            ],
            acceptance_criteria=[
                "Do not duplicate canonical ownership.",
                "Retain evidence and truth class.",
                "Apply prohibitions before ranking.",
                "Remain proposal-only and source-bounded.",
            ],
            rollback_conditions=["stale identity", "prohibited coupling", "unbounded scope"],
            constraints=["no production mutation", "no VSA patch authority",
                         "human review required", "independent verification required"],
            refresh_codemap=False,
        )
        architect = prepared.to_dict()
        _write(architect_path, architect)

    output = {
        "ok": True, "version": VERSION, "objective": objective,
        "repo_identity": _git_info(root), "request_digest": request["digest"],
        "reference_files": reference_manifest,
        "resumed": resume,
        "connectome": {
            "node_count": connectome.get("node_count"),
            "edge_count": connectome.get("edge_count"),
            "graph_digest": connectome.get("graph_digest"),
        },
        "relational_index": index_summary,
        "atlas": {
            "profile": profile, "estimated_full_pair_count": pairs,
            "snapshot_digest": atlas.get("snapshot_digest"),
            "assessment_count": len(atlas.get("assessments") or []),
            "missing_configuration_count": len(atlas.get("missing_configurations") or []),
            "prohibition_count": len(atlas.get("prohibitions") or []),
        },
        "emergent": {
            "summary": emergent.get("summary", {}),
            "verifier_summary": emergent.get("verifier_summary", ""),
            "top_connection_ids": [row.get("connection_id") for row in (emergent.get("connections") or [])[:top]],
        },
        "architect": {
            "phase_hash": architect.get("plan", {}).get("phase_hash"),
            "intensity": architect.get("intensity"),
            "shadow_gate": architect.get("shadow_report", {}).get("gate"),
            "ready_for_incubator": architect.get("arena", {}).get("ready_for_incubator"),
        },
        "elapsed_seconds": round(time.time() - started, 3),
        "safe_to_patch": False, "production_mutation": False,
        "human_review_required": True, "patch_authority": PATCH_AUTHORITY,
    }
    post = _git_info(root)
    output["post_run_repo_identity"] = post
    if enforce_clean and post.get("available") and not post.get("clean"):
        output["ok"] = False
        output["tracked_repository_changes_detected"] = post.get("status", [])
    output["run_digest"] = _digest(output)
    _write(output_dir / "harness_summary.json", output)
    return output


def _default_venv(root: Path) -> Path:
    return root.parent / f".{root.name}-architecture-harness-venv"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--venv")
    prep.add_argument("--system-site-packages", action="store_true")
    prep.add_argument("--install-requirements", action="store_true")
    prep.add_argument("--initialize-local-git", action="store_true")
    prep.add_argument("--source-sha", default="")
    doc = sub.add_parser("doctor")
    doc.add_argument("--venv")
    run = sub.add_parser("run")
    run.add_argument("--venv")
    run.add_argument("--objective", default=DEFAULT_OBJECTIVE)
    run.add_argument("--combine-with", nargs="*", default=["Connectome", "Relational Synthesis", "Atlas"])
    run.add_argument("--atlas-profile", default="MINIMAL")
    run.add_argument("--top", type=int, default=12)
    run.add_argument("--pair-limit", type=int, default=5_000_000)
    run.add_argument("--allow-expansive-atlas", action="store_true")
    run.add_argument("--allow-dirty", action="store_true")
    run.add_argument("--output-dir")
    run.add_argument(
        "--reference-file",
        action="append",
        default=[],
        help="Bind an external specification or evidence file by name, size, and SHA-256.",
    )
    run.add_argument("--resume", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        root = _root(args.repo_root)
        venv_path = Path(args.venv).expanduser().resolve() if getattr(args, "venv", None) else _default_venv(root)
        python = _venv_python(venv_path)
        if args.command == "prepare":
            result = prepare(root, venv_path,
                             system_packages=args.system_site_packages,
                             install_requirements=args.install_requirements,
                             initialize_git=args.initialize_local_git,
                             source_sha=args.source_sha)
        elif args.command == "doctor":
            result = doctor(root, python if python.is_file() else None)
        else:
            identity = _git_info(root)
            if not identity.get("available"):
                raise RuntimeError("run prepare with --initialize-local-git first")
            if not identity.get("clean") and not args.allow_dirty:
                raise RuntimeError("repository is dirty; use a clean checkout")
            if not python.is_file():
                raise RuntimeError("harness venv missing; run prepare first")
            output_dir = Path(args.output_dir).resolve() if args.output_dir else (
                root.parent / f"{root.name}-architecture-harness-runs" /
                time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            )
            payload = {
                "root": str(root), "objective": args.objective,
                "combine_with": args.combine_with, "profile": args.atlas_profile,
                "top": args.top, "pair_limit": args.pair_limit,
                "allow_expansive": args.allow_expansive_atlas,
                "output_dir": str(output_dir), "resume": args.resume,
                "enforce_clean": not args.allow_dirty,
                "reference_files": args.reference_file,
            }
            code = (
                "import json,sys;from pathlib import Path;"
                "sys.path.insert(0,sys.argv[1]);"
                "from scripts.aura_architecture_harness import run_architecture;"
                "p=json.loads(sys.argv[2]);"
                "r=run_architecture(Path(p.pop('root')),**p);"
                "print(json.dumps(r,indent=2,sort_keys=True))"
            )
            process = _run([str(python), "-c", code, str(root), json.dumps(payload)],
                           root, check=False, timeout=7200, env={"PYTHONPATH": str(root)})
            if process.returncode:
                raise RuntimeError(process.stderr.strip() or process.stdout.strip())
            result = json.loads(process.stdout)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "version": VERSION,
                          "error": f"{type(exc).__name__}: {exc}",
                          "safe_to_patch": False, "production_mutation": False},
                         indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
