"""Source-bound discharge for GLM-5.3 checkpoint layers outside decoder range.

This module is D0 metadata-only. It does not infer an extra layer's role from
position, K27 placement, cache locality, or filename shape. A classification is
accepted only when it is bound to the exact model revision, index digest, decoder
count, and an explicit provenance reference. It may discharge only the matching
extra-layer blocker in a GLM53CheckpointLayoutProbeV1 report.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "CheckpointExtraLayerClassificationV1"
_ALLOWED_ROLES = {"MTP_NON_DECODER"}


class ExtraLayerClassificationError(ValueError):
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


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class CheckpointExtraLayerClassification:
    model_revision: str
    index_sha256: str
    num_hidden_layers: int
    roles: tuple[tuple[int, str], ...]
    provenance_ref: str
    schema: str = SCHEMA

    def role_map(self) -> dict[int, str]:
        out: dict[int, str] = {}
        for item in self.roles:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or isinstance(item[0], bool)
                or not isinstance(item[0], int)
                or not isinstance(item[1], str)
            ):
                raise ExtraLayerClassificationError("EXTRA_LAYER_ROLE_ENTRY_INVALID")
            idx, role = item
            if idx in out:
                raise ExtraLayerClassificationError("EXTRA_LAYER_ROLE_DUPLICATE", str(idx))
            if idx < self.num_hidden_layers:
                raise ExtraLayerClassificationError("DECODER_LAYER_CLASSIFICATION_FORBIDDEN", str(idx))
            if role not in _ALLOWED_ROLES:
                raise ExtraLayerClassificationError("EXTRA_LAYER_ROLE_UNSUPPORTED", role)
            out[idx] = role
        if not out:
            raise ExtraLayerClassificationError("EXTRA_LAYER_ROLE_REQUIRED")
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "model_revision": self.model_revision,
            "index_sha256": self.index_sha256,
            "num_hidden_layers": self.num_hidden_layers,
            "roles": [
                {
                    "index": idx,
                    "role": role,
                    "decoder_pager_membership": False,
                }
                for idx, role in sorted(self.role_map().items())
            ],
            "provenance_ref": self.provenance_ref,
        }

    @property
    def classification_id(self) -> str:
        return _sha(self.to_dict())


def _validate_binding(
    report: Mapping[str, Any], classification: CheckpointExtraLayerClassification
) -> dict[int, str]:
    if not isinstance(classification, CheckpointExtraLayerClassification):
        raise ExtraLayerClassificationError("EXTRA_LAYER_CLASSIFICATION_REQUIRED")
    if classification.schema != SCHEMA:
        raise ExtraLayerClassificationError("EXTRA_LAYER_CLASSIFICATION_SCHEMA_MISMATCH")
    if not isinstance(classification.model_revision, str) or not classification.model_revision.strip():
        raise ExtraLayerClassificationError("EXTRA_LAYER_MODEL_REVISION_REQUIRED")
    if not isinstance(classification.index_sha256, str) or not classification.index_sha256.strip():
        raise ExtraLayerClassificationError("EXTRA_LAYER_INDEX_SHA256_REQUIRED")
    if (
        isinstance(classification.num_hidden_layers, bool)
        or not isinstance(classification.num_hidden_layers, int)
        or classification.num_hidden_layers <= 0
    ):
        raise ExtraLayerClassificationError("EXTRA_LAYER_NUM_HIDDEN_LAYERS_INVALID")
    if not isinstance(classification.provenance_ref, str) or not classification.provenance_ref.strip():
        raise ExtraLayerClassificationError("EXTRA_LAYER_PROVENANCE_REQUIRED")

    expected = (
        str(report.get("model_revision", "")),
        str(report.get("index_sha256", "")),
        report.get("num_hidden_layers"),
    )
    observed = (
        classification.model_revision.strip(),
        classification.index_sha256.strip(),
        classification.num_hidden_layers,
    )
    if observed != expected:
        raise ExtraLayerClassificationError(
            "EXTRA_LAYER_CLASSIFICATION_SOURCE_MISMATCH",
            f"expected={expected!r},observed={observed!r}",
        )

    actual_extra = report.get("extra_checkpoint_layer_indices")
    if not isinstance(actual_extra, list) or any(
        isinstance(v, bool) or not isinstance(v, int) for v in actual_extra
    ):
        raise ExtraLayerClassificationError("EXTRA_LAYER_REPORT_INVALID")
    actual_set = set(actual_extra)
    roles = classification.role_map()
    absent = sorted(set(roles) - actual_set)
    if absent:
        raise ExtraLayerClassificationError(
            "CLASSIFIED_EXTRA_LAYER_NOT_PRESENT", ",".join(map(str, absent))
        )
    return roles


def _status_from_blockers(blockers: list[str]) -> str:
    if "AIRLLM_REMOTE_CODE_SECURITY_BLOCK" in blockers:
        return "BLOCKED_SECURITY"
    if "GLM53_INDEX_GEOMETRY_CONFLICT" in blockers:
        return "BLOCKED_ARCHITECTURE"
    if blockers:
        return "PARTIAL"
    return "READY_FOR_HEADER_AND_TINY_FIXTURE"


def apply_extra_layer_classification(
    report: Mapping[str, Any],
    classification: CheckpointExtraLayerClassification,
) -> dict[str, Any]:
    """Discharge only extra-layer blockers proven by exact source-bound roles."""
    if report.get("schema") != "GLM53CheckpointLayoutProbeV1":
        raise ExtraLayerClassificationError("GLM53_LAYOUT_PROBE_REPORT_REQUIRED")
    roles = _validate_binding(report, classification)

    raw_blockers = report.get("blockers")
    if not isinstance(raw_blockers, list) or any(not isinstance(v, str) for v in raw_blockers):
        raise ExtraLayerClassificationError("EXTRA_LAYER_REPORT_INVALID")
    blockers = list(raw_blockers)

    hidden_layers = classification.num_hidden_layers
    actual_extra = list(report["extra_checkpoint_layer_indices"])
    unexpected = report.get("unexpected_extra_checkpoint_layer_indices")
    if not isinstance(unexpected, list) or any(
        isinstance(v, bool) or not isinstance(v, int) for v in unexpected
    ):
        raise ExtraLayerClassificationError("EXTRA_LAYER_REPORT_INVALID")

    if hidden_layers in actual_extra and roles.get(hidden_layers) == "MTP_NON_DECODER":
        blockers = [b for b in blockers if b != "GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"]

    if unexpected and all(idx in roles for idx in unexpected):
        blockers = [
            b
            for b in blockers
            if b != "GLM53_UNEXPECTED_CHECKPOINT_LAYER_CLASSIFICATION_REQUIRED"
        ]

    blockers = sorted(set(blockers))
    classified = [
        {
            "index": idx,
            "role": role,
            "decoder_pager_membership": False,
        }
        for idx, role in sorted(roles.items())
    ]
    unclassified = sorted(idx for idx in actual_extra if idx not in roles)

    logical = {
        key: value
        for key, value in report.items()
        if key not in {"logical_id", "observation_time", "claim_ceiling"}
    }
    logical.update(
        {
            "status": _status_from_blockers(blockers),
            "blockers": blockers,
            "classified_extra_checkpoint_layers": classified,
            "unclassified_extra_checkpoint_layer_indices": unclassified,
            "extra_layer_classification": classification.to_dict(),
            "extra_layer_classification_id": classification.classification_id,
        }
    )
    return {
        **logical,
        "logical_id": _sha(logical),
        "observation_time": report.get("observation_time"),
        "claim_ceiling": report.get(
            "claim_ceiling", "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT"
        ),
    }
