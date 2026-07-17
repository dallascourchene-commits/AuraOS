from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = ROOT / ".aura" / "phase2_payload"
PARTS_ROOT = PAYLOAD_ROOT / "plain"
MANIFEST_PATH = PAYLOAD_ROOT / "plain_manifest.json"
MANIFEST_VERSION = "AURA_SCO_PHASE2_PLAINTEXT_MANIFEST_V1"


def _safe_relative(value: Any, field_name: str) -> str:
    if type(value) is not str or not value:
        raise SystemExit(f"{field_name} must be a non-empty string")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise SystemExit(f"unsafe {field_name}: {value}")
    if pure.as_posix() != value or "\\" in value:
        raise SystemExit(f"non-canonical {field_name}: {value}")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("version") != MANIFEST_VERSION:
        raise SystemExit("unsupported phase payload manifest")
    entries = manifest.get("entries")
    if type(entries) is not list or not entries:
        raise SystemExit("phase payload manifest entries are invalid")

    seen_destinations: set[str] = set()
    expected_parts: set[str] = set()
    materialized: list[str] = []
    for index, raw in enumerate(entries):
        if type(raw) is not dict:
            raise SystemExit(f"manifest entry {index} is not an object")
        destination_name = _safe_relative(raw.get("destination"), "destination")
        if destination_name in seen_destinations:
            raise SystemExit(f"duplicate destination: {destination_name}")
        seen_destinations.add(destination_name)
        parts = raw.get("parts")
        if type(parts) is not list or not parts:
            raise SystemExit(f"manifest parts missing for {destination_name}")
        normalized_parts: list[str] = []
        for value in parts:
            part_name = _safe_relative(value, "part")
            if "/" in part_name:
                raise SystemExit(f"parts must be direct children: {part_name}")
            if part_name in expected_parts:
                raise SystemExit(f"part reused by multiple destinations: {part_name}")
            expected_parts.add(part_name)
            normalized_parts.append(part_name)
        expected_hash = raw.get("sha256")
        expected_bytes = raw.get("bytes")
        if (
            type(expected_hash) is not str
            or len(expected_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in expected_hash)
        ):
            raise SystemExit(f"invalid SHA-256 for {destination_name}")
        if type(expected_bytes) is not int or expected_bytes < 0:
            raise SystemExit(f"invalid byte count for {destination_name}")

        data = b"".join((PARTS_ROOT / name).read_bytes() for name in normalized_parts)
        if len(data) != expected_bytes:
            raise SystemExit(
                f"byte count mismatch for {destination_name}: {len(data)} != {expected_bytes}"
            )
        actual_hash = _sha256(data)
        if actual_hash != expected_hash:
            raise SystemExit(
                f"SHA-256 mismatch for {destination_name}: {actual_hash} != {expected_hash}"
            )
        destination = ROOT / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        post_write_hash = _sha256(destination.read_bytes())
        if post_write_hash != expected_hash:
            raise SystemExit(f"post-write verification failed for {destination_name}")
        materialized.append(destination_name)
        print(f"MATERIALIZED {destination_name} sha256={expected_hash}")

    actual_parts = {path.name for path in PARTS_ROOT.iterdir() if path.is_file()}
    if actual_parts != expected_parts:
        raise SystemExit(
            "plaintext part set mismatch: "
            f"missing={sorted(expected_parts - actual_parts)} "
            f"extra={sorted(actual_parts - expected_parts)}"
        )
    if set(materialized) != seen_destinations:
        raise SystemExit("not every expected destination was materialized")


if __name__ == "__main__":
    main()
