from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

import pytest

from scripts import aura_fetch_construction_demo_source as fetcher


class _Response:
    def __init__(self, body: bytes, *, url: str | None = None) -> None:
        self._body = io.BytesIO(body)
        self._url = url or fetcher.PINNED_DOWNLOAD_URL
        self.headers = {"Content-Length": str(len(body))}

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Opener:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls = 0

    def open(self, request: object, timeout: float) -> _Response:
        self.calls += 1
        assert timeout > 0
        return self.response


def _pin_payload(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> None:
    monkeypatch.setattr(fetcher, "PINNED_BYTE_LENGTH", len(payload))
    monkeypatch.setattr(
        fetcher,
        "PINNED_MD5",
        hashlib.md5(payload, usedforsecurity=False).hexdigest(),
    )
    monkeypatch.setattr(fetcher, "PINNED_SHA256", hashlib.sha256(payload).hexdigest())


def test_acquire_source_requires_explicit_operator_authority(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="accept-network-download"):
        fetcher.acquire_source(
            repo_root=tmp_path,
            output_dir=Path("assets"),
            record_doi=fetcher.PINNED_RECORD_DOI,
            accept_network_download=False,
        )

    with pytest.raises(ValueError, match="record DOI"):
        fetcher.acquire_source(
            repo_root=tmp_path,
            output_dir=Path("assets"),
            record_doi="wrong-doi",
            accept_network_download=True,
        )


def test_acquire_source_downloads_verifies_and_reuses_exact_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = b"ISO-10303-21;\nHEADER;\nENDSEC;\n"
    _pin_payload(monkeypatch, payload)
    opener = _Opener(_Response(payload))

    result = fetcher.acquire_source(
        repo_root=tmp_path,
        output_dir=Path("demo_assets/construction_tuwien/source"),
        record_doi=fetcher.PINNED_RECORD_DOI,
        accept_network_download=True,
        opener=opener,
        now=datetime(2026, 7, 22, 10, 30, tzinfo=timezone.utc),
    )

    assert result["state"] == "downloaded_and_verified"
    assert result["runtime_external_fetch"] is False
    assert result["survey_authority"] is False
    source = tmp_path / "demo_assets/construction_tuwien/source" / fetcher.PINNED_SOURCE_FILENAME
    manifest_path = source.with_name("source-manifest.json")
    assert source.read_bytes() == payload
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["observed_sha256"] == hashlib.sha256(payload).hexdigest()
    assert manifest["downloaded_at"] == "2026-07-22T10:30:00Z"
    assert manifest["external_fetch_required_at_runtime"] is False
    assert opener.calls == 1

    no_network = _Opener(_Response(b"should-not-be-read"))
    repeated = fetcher.acquire_source(
        repo_root=tmp_path,
        output_dir=Path("demo_assets/construction_tuwien/source"),
        record_doi=fetcher.PINNED_RECORD_DOI,
        accept_network_download=True,
        opener=no_network,
    )
    assert repeated["state"] == "already_verified"
    assert no_network.calls == 0


def test_acquire_source_refuses_response_url_change_and_cleans_temp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = b"pinned"
    _pin_payload(monkeypatch, payload)
    opener = _Opener(_Response(payload, url="https://example.invalid/redirected.ifc"))

    with pytest.raises(ValueError, match="response URL"):
        fetcher.acquire_source(
            repo_root=tmp_path,
            output_dir=Path("assets"),
            record_doi=fetcher.PINNED_RECORD_DOI,
            accept_network_download=True,
            opener=opener,
        )

    assert not list((tmp_path / "assets").glob(".construction-*.tmp"))
    assert not (tmp_path / "assets" / fetcher.PINNED_SOURCE_FILENAME).exists()


def test_acquire_source_refuses_existing_byte_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = b"pinned"
    _pin_payload(monkeypatch, payload)
    output = tmp_path / "assets"
    output.mkdir()
    (output / fetcher.PINNED_SOURCE_FILENAME).write_bytes(b"different")
    (output / "source-manifest.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="differ from the pinned"):
        fetcher.acquire_source(
            repo_root=tmp_path,
            output_dir=Path("assets"),
            record_doi=fetcher.PINNED_RECORD_DOI,
            accept_network_download=True,
            opener=_Opener(_Response(payload)),
        )


def test_output_directory_cannot_escape_or_be_symlinked(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    with pytest.raises(ValueError, match="inside repo root"):
        fetcher._resolve_output(tmp_path, outside)

    target = tmp_path / "real-assets"
    target.mkdir()
    link = tmp_path / "asset-link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink"):
        fetcher._resolve_output(tmp_path, link)


def test_stream_verification_fails_closed_on_digest_or_size(tmp_path: Path) -> None:
    destination = tmp_path / "source.tmp"
    with pytest.raises(ValueError, match="byte length mismatch"):
        fetcher._stream_verified_response(
            io.BytesIO(b"abc"),
            destination,
            expected_byte_length=4,
            expected_md5=hashlib.md5(b"abc", usedforsecurity=False).hexdigest(),
            expected_sha256=hashlib.sha256(b"abc").hexdigest(),
        )

    with pytest.raises(ValueError, match="SHA-256"):
        fetcher._stream_verified_response(
            io.BytesIO(b"abc"),
            destination,
            expected_byte_length=3,
            expected_md5=hashlib.md5(b"abc", usedforsecurity=False).hexdigest(),
            expected_sha256="0" * 64,
        )


def test_acquire_source_refuses_validly_redigested_false_manifest_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = b"pinned-manifest"
    _pin_payload(monkeypatch, payload)
    fetcher.acquire_source(
        repo_root=tmp_path,
        output_dir=Path("assets"),
        record_doi=fetcher.PINNED_RECORD_DOI,
        accept_network_download=True,
        opener=_Opener(_Response(payload)),
    )
    manifest_path = tmp_path / "assets" / "source-manifest.json"
    forged = json.loads(manifest_path.read_text(encoding="utf-8"))
    forged["doi"] = "10.0000/forged"
    forged.pop("source_manifest_digest", None)
    contract = fetcher._load_contract(tmp_path).from_dict(forged)
    manifest_path.write_text(
        json.dumps(contract.to_dict(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="manifest differs"):
        fetcher.acquire_source(
            repo_root=tmp_path,
            output_dir=Path("assets"),
            record_doi=fetcher.PINNED_RECORD_DOI,
            accept_network_download=True,
            opener=_Opener(_Response(payload)),
        )
