"""Temporary draft-only exact transport receipt for bilateral intent PR2.

This file is removed before the verified source diff is staged. It validates the
already committed gzip/tar payload, records its exact base64 transport bytes in
pytest's JUnit artifact, and deliberately fails closed so no transport-only head
can pass CI.
"""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _emit_pr2_transport_receipt(record_testsuite_property):
    parts = sorted(Path(".aura/materialize").glob("pr2.payload.part*"))
    if not parts:
        raise RuntimeError("PR2 transport parts are missing")
    encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
    compressed = base64.b64decode(encoded, validate=True)
    raw = gzip.decompress(compressed)
    if len(raw) < 512 or raw[257:262] != b"ustar":
        raise RuntimeError("PR2 transport payload is not a valid tar archive")
    record_testsuite_property("aura_pr2_payload_gzip_b64", encoded)
    record_testsuite_property("aura_pr2_payload_raw_bytes", str(len(raw)))
    raise RuntimeError(
        "AURA_PR2_TRANSPORT_RECEIPT_EMITTED: intentional draft-only fail-closed checkpoint"
    )
