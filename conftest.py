"""Temporary draft-only exact transport receipt for bilateral intent PR2.

This file is removed before the verified source diff is staged. It decodes the
already committed payload, records the canonical decompressed bytes in pytest's
JUnit artifact, and deliberately fails closed so no transport-only head can pass CI.
"""
from __future__ import annotations

import base64
import gzip
import json
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
    payload = json.loads(raw.decode("utf-8"))
    records = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(records, dict) or not records:
        raise RuntimeError("PR2 transport payload has no canonical file records")
    record_testsuite_property(
        "aura_pr2_payload_b64",
        base64.b64encode(raw).decode("ascii"),
    )
    record_testsuite_property(
        "aura_pr2_payload_paths",
        ",".join(sorted(str(path) for path in records)),
    )
    raise RuntimeError(
        "AURA_PR2_TRANSPORT_RECEIPT_EMITTED: intentional draft-only fail-closed checkpoint"
    )
