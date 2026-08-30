"""Source-bound GLM-5.3 MTP checkpoint classifier.

D0 metadata only. This module resolves exactly one blocker emitted by the current
GLM53CheckpointLayoutProbeV1: ``GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED``.
It never infers MTP from an extra layer number alone. Classification requires the
same immutable source bundle used by the #340 probe, an explicit
``num_nextn_predict_layers == 1`` config declaration, and MTP-specific key-family
evidence on the exact layer immediately after the decoder stack.

The returned overlay may remove only the MTP classification blocker. Every other
security/layout/scale/chunk/currentness blocker survives unchanged. No model
weights are opened and G2/large-checkpoint/runtime admission remains false.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping


SCHEMA = "GLM53MTPCheckpointClassificationV1"
PROBE_SCHEMA = "GLM53CheckpointLayoutProbeV1"
MTP_BLOCKER = "GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class MTPClassificationError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MTPClassificationError("NONCANONICAL_MTP_EVIDENCE") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha_field(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise MTPClassificationError(code)
    out = value.strip().lower()
    if not _SHA256_RE.fullmatch(out):
        raise MTPClassificationError(code)
    return out


def _positive_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MTPClassificationError(code)
    return value


def _weight_map(sources: Any) -> Mapping[str, str]:
    index = sources.index.mapping()
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, Mapping) or not weight_map:
        raise MTPClassificationError("INDEX_WEIGHT_MAP_REQUIRED")
    for key, shard in weight_map.items():
        if not isinstance(key, str) or not key or not isinstance(shard, str) or not shard:
            raise MTPClassificationError("INDEX_WEIGHT_MAP_ENTRY_INVALID")
    return weight_map


def _has_key_family(weight_map: Mapping[str, str], base: str) -> bool:
    return any(key == base or key.startswith(base + ".") for key in weight_map)


def _layer_indices(weight_map: Mapping[str, str]) -> tuple[int, ...]:
    pattern = re.compile(r"^model\.layers\.(\d+)\.")
    out: set[int] = set()
    for key in weight_map:
        match = pattern.match(key)
        if match:
            out.add(int(match.group(1)))
    return tuple(sorted(out))


@dataclass(frozen=True)
class MTPClassificationReceipt:
    source_bundle_id: str
    weight_map_digest: str
    model_revision: str
    decoder_layer_count: int
    declared_nextn_layers: int
    mtp_layer_indices: tuple[int, ...]
    required_marker_families: tuple[str, ...]
    marker_evidence_digest: str
    classification: str
    resolved_blocker: str
    classification_digest: str
    schema: str = SCHEMA
    g2_admitted: bool = False
    large_checkpoint_admitted: bool = False
    runtime_execution_proven: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_mtp_checkpoint(*, sources: Any, report: Mapping[str, Any]) -> MTPClassificationReceipt:
    if report.get("schema") != PROBE_SCHEMA:
        raise MTPClassificationError("PROBE_SCHEMA_MISMATCH")
    if report.get("source_binding_proven") is not True:
        raise MTPClassificationError("SOURCE_BINDING_REQUIRED")
    if MTP_BLOCKER not in report.get("blockers", []):
        raise MTPClassificationError("MTP_BLOCKER_NOT_PRESENT")

    source_bundle_id = _sha_field(getattr(sources, "source_bundle_id", None), "SOURCE_BUNDLE_ID_REQUIRED")
    report_bundle_id = _sha_field(report.get("source_bundle_id"), "REPORT_SOURCE_BUNDLE_ID_REQUIRED")
    if report_bundle_id != source_bundle_id:
        raise MTPClassificationError("SOURCE_BUNDLE_MISMATCH")

    source_weight_map_digest = _sha_field(getattr(sources, "weight_map_digest", None), "SOURCE_WEIGHT_MAP_DIGEST_REQUIRED")
    report_weight_map_digest = _sha_field(report.get("weight_map_digest"), "REPORT_WEIGHT_MAP_DIGEST_REQUIRED")
    if report_weight_map_digest != source_weight_map_digest:
        raise MTPClassificationError("SOURCE_WEIGHT_MAP_DIGEST_MISMATCH")

    config = sources.config.mapping()
    hidden_layers = _positive_int(config.get("num_hidden_layers"), "NUM_HIDDEN_LAYERS_INVALID")
    declared_nextn = _positive_int(config.get("num_nextn_predict_layers"), "NUM_NEXTN_PREDICT_LAYERS_REQUIRED")
    if declared_nextn != 1:
        raise MTPClassificationError("MTP_LAYER_COUNT_UNSUPPORTED", str(declared_nextn))

    if report.get("num_hidden_layers") != hidden_layers:
        raise MTPClassificationError("REPORT_DECODER_LAYER_COUNT_MISMATCH")
    if report.get("mtp_index_present") is not True:
        raise MTPClassificationError("REPORT_MTP_INDEX_NOT_PRESENT")

    weight_map = _weight_map(sources)
    indices = _layer_indices(weight_map)
    expected_mtp = (hidden_layers,)
    extra = tuple(i for i in indices if i >= hidden_layers)
    if extra != expected_mtp:
        raise MTPClassificationError("MTP_EXTRA_LAYER_SET_MISMATCH", f"expected={expected_mtp},observed={extra}")

    reported_extra = tuple(report.get("extra_checkpoint_layer_indices", ()))
    if reported_extra != expected_mtp:
        raise MTPClassificationError("REPORT_EXTRA_LAYER_SET_MISMATCH")
    if tuple(report.get("unexpected_extra_checkpoint_layer_indices", ())) != ():
        raise MTPClassificationError("UNEXPECTED_EXTRA_LAYER_PRESENT")

    layer = hidden_layers
    markers = (
        f"model.layers.{layer}.eh_proj",
        f"model.layers.{layer}.enorm",
        f"model.layers.{layer}.hnorm",
        f"model.layers.{layer}.shared_head.norm",
    )
    missing = tuple(marker for marker in markers if not _has_key_family(weight_map, marker))
    if missing:
        raise MTPClassificationError("MTP_MARKER_FAMILY_MISSING", ",".join(missing))

    marker_evidence = {
        marker: sorted(key for key in weight_map if key == marker or key.startswith(marker + "."))
        for marker in markers
    }
    marker_digest = _sha(marker_evidence)
    payload = {
        "schema": SCHEMA,
        "source_bundle_id": source_bundle_id,
        "weight_map_digest": source_weight_map_digest,
        "model_revision": sources.model_revision,
        "decoder_layer_count": hidden_layers,
        "declared_nextn_layers": declared_nextn,
        "mtp_layer_indices": expected_mtp,
        "required_marker_families": markers,
        "marker_evidence_digest": marker_digest,
        "classification": "NON_DECODER_MULTI_TOKEN_PREDICTION",
        "resolved_blocker": MTP_BLOCKER,
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
    }
    return MTPClassificationReceipt(
        source_bundle_id=source_bundle_id,
        weight_map_digest=source_weight_map_digest,
        model_revision=sources.model_revision,
        decoder_layer_count=hidden_layers,
        declared_nextn_layers=declared_nextn,
        mtp_layer_indices=expected_mtp,
        required_marker_families=markers,
        marker_evidence_digest=marker_digest,
        classification="NON_DECODER_MULTI_TOKEN_PREDICTION",
        resolved_blocker=MTP_BLOCKER,
        classification_digest=_sha(payload),
    )


def apply_mtp_classification(
    report: Mapping[str, Any],
    receipt: MTPClassificationReceipt,
) -> dict[str, Any]:
    """Return a bridge-compatible report overlay that clears only the MTP blocker."""
    if report.get("schema") != PROBE_SCHEMA:
        raise MTPClassificationError("PROBE_SCHEMA_MISMATCH")
    if not isinstance(receipt, MTPClassificationReceipt) or receipt.schema != SCHEMA:
        raise MTPClassificationError("MTP_CLASSIFICATION_RECEIPT_REQUIRED")
    if report.get("source_binding_proven") is not True:
        raise MTPClassificationError("SOURCE_BINDING_REQUIRED")
    if _sha_field(report.get("source_bundle_id"), "REPORT_SOURCE_BUNDLE_ID_REQUIRED") != receipt.source_bundle_id:
        raise MTPClassificationError("CLASSIFICATION_SOURCE_BUNDLE_MISMATCH")
    if _sha_field(report.get("weight_map_digest"), "REPORT_WEIGHT_MAP_DIGEST_REQUIRED") != receipt.weight_map_digest:
        raise MTPClassificationError("CLASSIFICATION_WEIGHT_MAP_DIGEST_MISMATCH")
    if report.get("model_revision") != receipt.model_revision:
        raise MTPClassificationError("CLASSIFICATION_MODEL_REVISION_MISMATCH")

    raw_blockers = report.get("blockers")
    if not isinstance(raw_blockers, list):
        raise MTPClassificationError("INVALID_PROBE_BLOCKERS")
    if MTP_BLOCKER not in raw_blockers:
        raise MTPClassificationError("MTP_BLOCKER_NOT_PRESENT")
    blockers = sorted(blocker for blocker in raw_blockers if blocker != MTP_BLOCKER)

    if "AIRLLM_REMOTE_CODE_SECURITY_BLOCK" in blockers:
        status = "BLOCKED_SECURITY"
    elif "GLM53_INDEX_GEOMETRY_CONFLICT" in blockers:
        status = "BLOCKED_ARCHITECTURE"
    elif blockers:
        status = "PARTIAL"
    else:
        status = "READY_FOR_HEADER_AND_TINY_FIXTURE"

    resolved = dict(report)
    resolved["blockers"] = blockers
    resolved["status"] = status
    resolved["mtp_classification"] = receipt.to_dict()
    resolved["g2_admitted"] = False
    resolved["large_checkpoint_admitted"] = False
    resolved["runtime_execution_proven"] = False

    logical = {
        key: value
        for key, value in resolved.items()
        if key not in {"logical_id", "observation_time", "claim_ceiling"}
    }
    resolved["logical_id"] = _sha(logical)
    resolved["claim_ceiling"] = "SOURCE_BOUND_MTP_CLASSIFICATION_ONLY_NO_MODEL_WEIGHT_EFFECT"
    return resolved
