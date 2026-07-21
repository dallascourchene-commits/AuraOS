"""Temporary CI-only repository export hook.

This file is isolated to the analysis/full-repo-export-20260720 branch. It is
inactive unless GitHub Actions is running and the explicit export marker exists.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile


def _export_repository_snapshot() -> None:
    if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
        return

    workspace_raw = os.environ.get("GITHUB_WORKSPACE", "")
    if not workspace_raw:
        return
    repo_root = Path(workspace_raw).resolve()
    marker = repo_root / ".aura" / "EXPORT_FULL_REPO_SNAPSHOT"
    if not marker.is_file():
        return

    output_dir = repo_root / "benchmark-output" / "real-refactor-trial"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "AuraOS-full-repository.zip"
    manifest_path = output_dir / "AuraOS-full-repository.manifest.json"
    digest_path = output_dir / "AuraOS-full-repository.zip.sha256"
    error_path = output_dir / "AuraOS-full-repository.export-error.txt"
    if archive_path.is_file() and manifest_path.is_file() and digest_path.is_file():
        return

    temporary_helpers = {
        ".aura/EXPORT_FULL_REPO_SNAPSHOT",
        "sitecustomize.py",
    }

    try:
        head_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        tracked_raw = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            timeout=60,
        ).stdout
        tracked = sorted(
            path.decode("utf-8", errors="strict")
            for path in tracked_raw.split(b"\0")
            if path and path.decode("utf-8", errors="strict") not in temporary_helpers
        )

        marker_payload = marker.read_text(encoding="utf-8").strip()
        source_main_sha = marker_payload or "UNAVAILABLE"
        manifest = {
            "archive_format": "zip",
            "archive_root": "AuraOS/",
            "source_repository": "dallascourchene-commits/AuraOS",
            "source_main_sha": source_main_sha,
            "export_branch_head_sha": head_sha,
            "tracked_file_count": len(tracked),
            "temporary_helpers_excluded": sorted(temporary_helpers),
            "working_tree_source": "exact Git-tracked files from export branch; export helpers excluded",
        }

        temp_path = archive_path.with_suffix(".zip.tmp")
        if temp_path.exists():
            temp_path.unlink()
        with zipfile.ZipFile(
            temp_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            for relative in tracked:
                source = repo_root / relative
                if not source.exists() or source.is_dir():
                    continue
                archive.write(source, arcname=f"AuraOS/{relative}")
            archive.writestr(
                "AuraOS/.aura/export_manifest.json",
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
        temp_path.replace(archive_path)

        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        manifest["archive_sha256"] = digest
        manifest["archive_size_bytes"] = archive_path.stat().st_size
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        digest_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
        if error_path.exists():
            error_path.unlink()
    except Exception as exc:  # Export must never alter the workflow's authority or result.
        error_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")


_export_repository_snapshot()
