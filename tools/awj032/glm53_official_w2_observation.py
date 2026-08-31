"""Immutable producer-side identity for the AWJ032 GLM-5.3 W2 canary.

This is intentionally narrower than a generic trust resolver. It records the exact
already-observed PR398 producer result so a downstream pager plan can distinguish
"caller supplied a self-consistent expected receipt" from "this candidate equals
the independently observed W2 canary". It never generalizes one canary to all
experts and never admits tensor payload, runtime, G2, or authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "GLM53OfficialW2ObservationV1"
OFFICIAL_REPO_ID = "zai-org/GLM-5.3"
OFFICIAL_MODEL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_LAYER = 3
OFFICIAL_EXPERT = 0
OFFICIAL_RECEIPT_DIGEST = "736f0a117eb02c486736e7224c4e0f5363ae60b9"
OFFICIAL_PRODUCER_SEMANTIC_HEAD = "131dd2a5fc8b4e2cf96c0bf598845d35e6706ef8"
OFFICIAL_PRODUCER_RUN_REF = "github-actions:run:33336508527:job:99324255699"
OFFICIAL_DRIVE_OBSERVATION_REF = "drive:1FIz2aGHogE32scM4pmxDkHT7MiGfr2UbUkWlIDfpI_w"


class OfficialW2ObservationError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class OfficialW2Observation:
    repo_id: str = OFFICIAL_REPO_ID
    model_revision: str = OFFICIAL_MODEL_REVISION
    index_sha256: str = OFFICIAL_INDEX_SHA256
    layer: int = OFFICIAL_LAYER
    expert: int = OFFICIAL_EXPERT
    receipt_digest: str = OFFICIAL_RECEIPT_DIGEST
    producer_semantic_head: str = OFFICIAL_PRODUCER_SEMANTIC_HEAD
    producer_run_ref: str = OFFICIAL_PRODUCER_RUN_REF
    drive_observation_ref: str = OFFICIAL_DRIVE_OBSERVATION_REF
    representative_only: bool = True
    tensor_payload_read: bool = False
    g2_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def observation_digest(self) -> str:
        return _digest(self.to_dict())


OFFICIAL_W2_OBSERVATION = OfficialW2Observation()


def bind_official_w2_observation(
    *,
    repo_id: str,
    model_revision: str,
    index_sha256: str,
    layer: int,
    expert: int,
    observed_receipt_digest: str,
) -> OfficialW2Observation | None:
    """Return the immutable producer descriptor only for the exact observed canary.

    Non-canary sources simply remain lower-plane/synthetic (`None`). If the exact
    official source+coordinate is presented with a different receipt, fail hard:
    that is a direct contradiction of the producer observation, not merely a new
    synthetic candidate.
    """
    o = OFFICIAL_W2_OBSERVATION
    same_source = (
        repo_id == o.repo_id
        and model_revision == o.model_revision
        and index_sha256 == o.index_sha256
    )
    same_coordinate = layer == o.layer and expert == o.expert
    if not (same_source and same_coordinate):
        return None
    if observed_receipt_digest != o.receipt_digest:
        raise OfficialW2ObservationError(
            "OFFICIAL_W2_OBSERVATION_RECEIPT_MISMATCH",
            f"expected={o.receipt_digest},observed={observed_receipt_digest}",
        )
    return o
