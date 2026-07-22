#!/usr/bin/env python3
"""Explicit, fail-closed acquisition of the pinned TU Wien demo IFC.

This script is operator-only. Aura startup and demo runtime must never import or
invoke it. It accepts no arbitrary URL and writes only a verified local source
file plus its immutable source manifest.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, BinaryIO
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

PINNED_RECORD_DOI = "10.48436/a185k-86v39"
PINNED_SOURCE_FILENAME = "CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc"
PINNED_DOWNLOAD_URL = (
    "https://researchdata.tuwien.ac.at/records/a185k-86v39/files/"
    "CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc?download=1"
)
PINNED_HOST = "researchdata.tuwien.ac.at"
PINNED_BYTE_LENGTH = 7_404_420
PINNED_MD5 = "58a6e009b16bd3808cacd72b11fcf216"
PINNED_SHA256 = "29945f654c636d758a95b66eb0e107ec35afc7e1c7857a7ff652586e7728ba29"
MAX_DOWNLOAD_BYTES = 16 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 45.0
CHUNK_BYTES = 1024 * 1024


class RedirectRefused(HTTPRedirectHandler):
    """Disable all redirects so an approved URL cannot escape its host."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _canonical_utc(value: datetime | None = None) -> str:
    moment = value or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("download timestamp must be timezone-aware")
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_output(repo_root: Path, output_dir: Path) -> Path:
    root = repo_root.expanduser().resolve(strict=True)
    output = output_dir.expanduser()
    if not output.is_absolute():
        output = root / output
    if output.exists() and output.is_symlink():
        raise ValueError("output directory must not be a symlink")
    output = output.resolve(strict=False)
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise ValueError("output directory must stay inside repo root") from exc
    if output.exists() and output.is_symlink():
        raise ValueError("output directory must not be a symlink")
    output.mkdir(parents=True, exist_ok=True)
    if output.resolve(strict=True) != output:
        raise ValueError("output directory resolution changed unexpectedly")
    return output


def _hash_file(path: Path) -> tuple[int, str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            size += len(chunk)
            md5.update(chunk)
            sha256.update(chunk)
    return size, md5.hexdigest(), sha256.hexdigest()


def _stream_verified_response(
    response: BinaryIO,
    destination: Path,
    *,
    expected_byte_length: int,
    expected_md5: str,
    expected_sha256: str,
    max_download_bytes: int = MAX_DOWNLOAD_BYTES,
) -> dict[str, Any]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    size = 0
    with destination.open("wb") as handle:
        while True:
            chunk = response.read(CHUNK_BYTES)
            if not chunk:
                break
            size += len(chunk)
            if size > max_download_bytes:
                raise ValueError("download exceeds maximum byte limit")
            handle.write(chunk)
            md5.update(chunk)
            sha256.update(chunk)
        handle.flush()
        os.fsync(handle.fileno())
    observed_md5 = md5.hexdigest()
    observed_sha256 = sha256.hexdigest()
    if size != expected_byte_length:
        raise ValueError(f"download byte length mismatch: expected {expected_byte_length}, observed {size}")
    if observed_md5 != expected_md5:
        raise ValueError("download MD5 does not match published metadata")
    if observed_sha256 != expected_sha256:
        raise ValueError("download SHA-256 does not match Aura pin")
    return {"byte_length": size, "md5": observed_md5, "sha256": observed_sha256}


def _load_contract(repo_root: Path) -> Any:
    root_text = str(repo_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from aura_construction_demo_contracts import ConstructionDemoSourceManifest

    return ConstructionDemoSourceManifest


def _manifest(repo_root: Path, downloaded_at: str) -> dict[str, Any]:
    contract = _load_contract(repo_root)
    value = contract(
        source_id="tuwien-custom-escape-route-ifc-v2",
        title="Custom Test Model for Escape Route Analysis in IFC format",
        creators=("Christian Schranz", "Daniel Pfeiffer", "Harald Urban", "Sebastian Zdanowicz", "Simon Fischer"),
        publisher="TU Wien",
        doi=PINNED_RECORD_DOI,
        source_filename=PINNED_SOURCE_FILENAME,
        source_byte_length=PINNED_BYTE_LENGTH,
        published_md5=PINNED_MD5,
        observed_sha256=PINNED_SHA256,
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        downloaded_at=downloaded_at,
    )
    return value.to_dict()


def _validate_existing(repo_root: Path, source_path: Path, manifest_path: Path) -> dict[str, Any] | None:
    if not source_path.exists() and not manifest_path.exists():
        return None
    if not source_path.is_file() or source_path.is_symlink():
        raise ValueError("existing source path is missing, non-file, or symlinked")
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("existing source manifest is missing, non-file, or symlinked")
    size, md5, sha256 = _hash_file(source_path)
    if (size, md5, sha256) != (PINNED_BYTE_LENGTH, PINNED_MD5, PINNED_SHA256):
        raise ValueError("existing source bytes differ from the pinned TU Wien source")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = _load_contract(repo_root)
    parsed = contract.from_dict(data)
    if parsed.observed_sha256 != PINNED_SHA256 or parsed.source_byte_length != PINNED_BYTE_LENGTH:
        raise ValueError("existing source manifest differs from pinned source identity")
    return {"state": "already_verified", "source": str(source_path), "manifest": str(manifest_path), "source_manifest_digest": parsed.source_manifest_digest}


def acquire_source(
    *,
    repo_root: Path,
    output_dir: Path,
    record_doi: str,
    accept_network_download: bool,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    opener: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not accept_network_download:
        raise ValueError("explicit --accept-network-download is required")
    if record_doi != PINNED_RECORD_DOI:
        raise ValueError("record DOI does not match the pinned TU Wien source")
    if timeout_seconds <= 0 or timeout_seconds > 120:
        raise ValueError("timeout_seconds must be in (0, 120]")
    parsed = urlsplit(PINNED_DOWNLOAD_URL)
    if parsed.scheme != "https" or parsed.hostname != PINNED_HOST:
        raise ValueError("pinned source URL violates the approved host policy")

    root = repo_root.expanduser().resolve(strict=True)
    output = _resolve_output(root, output_dir)
    source_path = output / PINNED_SOURCE_FILENAME
    manifest_path = output / "source-manifest.json"
    existing = _validate_existing(root, source_path, manifest_path)
    if existing is not None:
        return existing

    client = opener or build_opener(RedirectRefused())
    request = Request(PINNED_DOWNLOAD_URL, headers={"User-Agent": "AuraOS-Construction-Demo-Asset-Builder/1"})
    temp_source: Path | None = None
    temp_manifest: Path | None = None
    try:
        with client.open(request, timeout=timeout_seconds) as response:
            final_url = str(response.geturl())
            if final_url != PINNED_DOWNLOAD_URL:
                raise ValueError("source response URL differs from the pinned URL")
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) != PINNED_BYTE_LENGTH:
                raise ValueError("source Content-Length differs from the pinned byte length")
            with tempfile.NamedTemporaryFile(prefix=".construction-source-", suffix=".tmp", dir=output, delete=False) as temporary:
                temp_source = Path(temporary.name)
            verification = _stream_verified_response(
                response,
                temp_source,
                expected_byte_length=PINNED_BYTE_LENGTH,
                expected_md5=PINNED_MD5,
                expected_sha256=PINNED_SHA256,
            )
        manifest = _manifest(root, _canonical_utc(now))
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".construction-manifest-", suffix=".tmp", dir=output, delete=False) as temporary_manifest:
            temp_manifest = Path(temporary_manifest.name)
            json.dump(manifest, temporary_manifest, indent=2, sort_keys=True)
            temporary_manifest.write("\n")
            temporary_manifest.flush()
            os.fsync(temporary_manifest.fileno())
        if source_path.exists() or manifest_path.exists():
            raise ValueError("destination appeared during acquisition; refusing overwrite")
        os.replace(temp_source, source_path)
        temp_source = None
        os.replace(temp_manifest, manifest_path)
        temp_manifest = None
        return {
            "state": "downloaded_and_verified",
            "source": str(source_path),
            "manifest": str(manifest_path),
            "byte_length": verification["byte_length"],
            "published_md5": verification["md5"],
            "observed_sha256": verification["sha256"],
            "source_manifest_digest": manifest["source_manifest_digest"],
            "runtime_external_fetch": False,
            "survey_authority": False,
        }
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            raise ValueError("source redirect refused") from exc
        raise
    finally:
        for path in (temp_source, temp_manifest):
            if path is not None:
                path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--record-doi", required=True)
    parser.add_argument("--accept-network-download", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = acquire_source(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        record_doi=args.record_doi,
        accept_network_download=args.accept_network_download,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
