"""Immutable source-derived GLM-5.3 MTP role evidence for the W3 proof plane.

This is deliberately a narrow, code-reviewed descriptor of one independently verified
immutable source relation. It is not a generic resolver and it does not infer runtime
MTP support. The authority of the underlying observation comes from the durable Arena
verification receipt named below; callers cannot manufacture a second source role by
supplying look-alike fields to the W3 consumer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "OfficialSourceMTPRoleEvidenceV1"
OWNER_REPO = "zai-org/GLM-5.3"
IMMUTABLE_MODEL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
NUM_HIDDEN_LAYERS = 78
NUM_NEXTN_PREDICT_LAYERS = 1
EXTRA_LAYER_INDEX = 78
MTP_MARKER = "model.layers.78.eh_proj"
ROLE = "MTP_NON_DECODER"
SOURCE_VERIFICATION_RECEIPT_REF = (
    "drive:1KxqmaTRDumVbGrL0JPhGPXk2tCpoNQyE8QQj3hOh9IE"
    "@AIroW34HOFIhPZvuh4zLXCp5wgA5igjiBuqPz6ncZyLoJT1lMdjApBfL7gxSIHK01TONSkyl2GGfCayuH9HVjbjdl5ERT9dferSEuUIdK3c"
)
SOURCE_SEMANTICS_REF = "transformers:num_nextn_predict_layers:MTP"


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
class OfficialSourceMTPRoleEvidence:
    owner_repo: str = OWNER_REPO
    immutable_model_revision: str = IMMUTABLE_MODEL_REVISION
    index_sha256: str = INDEX_SHA256
    num_hidden_layers: int = NUM_HIDDEN_LAYERS
    num_nextn_predict_layers: int = NUM_NEXTN_PREDICT_LAYERS
    extra_layer_index: int = EXTRA_LAYER_INDEX
    mtp_marker: str = MTP_MARKER
    role: str = ROLE
    decoder_pager_membership: bool = False
    source_verification_proven: bool = True
    source_verification_current: bool = True
    source_verification_receipt_ref: str = SOURCE_VERIFICATION_RECEIPT_REF
    source_semantics_ref: str = SOURCE_SEMANTICS_REF
    g2_admitted: bool = False
    runtime_mtp_support_proven: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def evidence_digest(self) -> str:
        return _digest(self.to_dict())


OFFICIAL_SOURCE_MTP_ROLE_EVIDENCE = OfficialSourceMTPRoleEvidence()
