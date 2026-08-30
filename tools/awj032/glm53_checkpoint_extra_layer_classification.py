"""Resolver-bound discharge for GLM-5.3 checkpoint layers outside decoder range.

D0 metadata-only. Extra-layer presence, role intent, evidence currentness, and
checkpoint identity are separate planes. A classification cannot clear a blocker
by carrying an arbitrary provenance string: it must be paired with a separate
resolver observation bound to the same evidence object, generation, exact model
revision, index digest, decoder count, and roles.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "CheckpointExtraLayerClassificationV1"
EVIDENCE_SCHEMA = "CheckpointExtraLayerEvidenceObservationV1"
_ALLOWED_ROLES = {"MTP_NON_DECODER"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,511}$")


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


def _token(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise ExtraLayerClassificationError(code)
    out = value.strip()
    if not out or not _TOKEN_RE.fullmatch(out):
        raise ExtraLayerClassificationError(code)
    return out


def _sha256(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise ExtraLayerClassificationError(code)
    out = value.strip().lower()
    if not _SHA256_RE.fullmatch(out):
        raise ExtraLayerClassificationError(code)
    return out


def _commit(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise ExtraLayerClassificationError(code)
    out = value.strip().lower()
    if not _COMMIT_RE.fullmatch(out):
        raise ExtraLayerClassificationError(code)
    return out


def _hidden_layers(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExtraLayerClassificationError("EXTRA_LAYER_NUM_HIDDEN_LAYERS_INVALID")
    return value


def _role_map(
    roles: tuple[tuple[int, str], ...], num_hidden_layers: int
) -> dict[int, str]:
    if not isinstance(roles, tuple):
        raise ExtraLayerClassificationError("EXTRA_LAYER_ROLES_TUPLE_REQUIRED")
    out: dict[int, str] = {}
    for item in roles:
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
        if idx < num_hidden_layers:
            raise ExtraLayerClassificationError("DECODER_LAYER_CLASSIFICATION_FORBIDDEN", str(idx))
        if role not in _ALLOWED_ROLES:
            raise ExtraLayerClassificationError("EXTRA_LAYER_ROLE_UNSUPPORTED", role)
        out[idx] = role
    if not out:
        raise ExtraLayerClassificationError("EXTRA_LAYER_ROLE_REQUIRED")
    return out


def _roles_payload(roles: dict[int, str]) -> list[dict[str, Any]]:
    return [
        {
            "index": idx,
            "role": role,
            "decoder_pager_membership": False,
        }
        for idx, role in sorted(roles.items())
    ]


@dataclass(frozen=True)
class CheckpointExtraLayerClassification:
    model_revision: str
    index_sha256: str
    num_hidden_layers: int
    roles: tuple[tuple[int, str], ...]
    evidence_ref: str
    evidence_digest: str
    evidence_generation: str
    resolver_ref: str
    resolver_generation: str
    schema: str = SCHEMA

    def normalized(self) -> dict[str, Any]:
        model_revision = _commit(self.model_revision, "EXTRA_LAYER_MODEL_REVISION_INVALID")
        index_sha256 = _sha256(self.index_sha256, "EXTRA_LAYER_INDEX_SHA256_INVALID")
        hidden = _hidden_layers(self.num_hidden_layers)
        roles = _role_map(self.roles, hidden)
        return {
            "schema": self.schema,
            "model_revision": model_revision,
            "index_sha256": index_sha256,
            "num_hidden_layers": hidden,
            "roles": _roles_payload(roles),
            "evidence_ref": _token(self.evidence_ref, "EXTRA_LAYER_EVIDENCE_REF_INVALID"),
            "evidence_digest": _sha256(
                self.evidence_digest, "EXTRA_LAYER_EVIDENCE_DIGEST_INVALID"
            ),
            "evidence_generation": _token(
                self.evidence_generation, "EXTRA_LAYER_EVIDENCE_GENERATION_INVALID"
            ),
            "resolver_ref": _token(self.resolver_ref, "EXTRA_LAYER_RESOLVER_REF_INVALID"),
            "resolver_generation": _token(
                self.resolver_generation, "EXTRA_LAYER_RESOLVER_GENERATION_INVALID"
            ),
        }

    def role_map(self) -> dict[int, str]:
        return _role_map(self.roles, _hidden_layers(self.num_hidden_layers))

    def to_dict(self) -> dict[str, Any]:
        return self.normalized()

    @property
    def classification_id(self) -> str:
        return _sha(self.normalized())


@dataclass(frozen=True)
class CheckpointExtraLayerEvidenceObservation:
    evidence_ref: str
    evidence_digest: str
    evidence_generation: str
    resolver_ref: str
    resolver_generation: str
    resolution_receipt_ref: str
    model_revision: str
    index_sha256: str
    num_hidden_layers: int
    roles: tuple[tuple[int, str], ...]
    evidence_current: bool
    schema: str = EVIDENCE_SCHEMA

    def normalized(self) -> dict[str, Any]:
        hidden = _hidden_layers(self.num_hidden_layers)
        roles = _role_map(self.roles, hidden)
        if type(self.evidence_current) is not bool:
            raise ExtraLayerClassificationError("EXTRA_LAYER_EVIDENCE_CURRENT_BOOL_REQUIRED")
        return {
            "schema": self.schema,
            "evidence_ref": _token(self.evidence_ref, "EXTRA_LAYER_EVIDENCE_REF_INVALID"),
            "evidence_digest": _sha256(
                self.evidence_digest, "EXTRA_LAYER_EVIDENCE_DIGEST_INVALID"
            ),
            "evidence_generation": _token(
                self.evidence_generation, "EXTRA_LAYER_EVIDENCE_GENERATION_INVALID"
            ),
            "resolver_ref": _token(self.resolver_ref, "EXTRA_LAYER_RESOLVER_REF_INVALID"),
            "resolver_generation": _token(
                self.resolver_generation, "EXTRA_LAYER_RESOLVER_GENERATION_INVALID"
            ),
            "resolution_receipt_ref": _token(
                self.resolution_receipt_ref, "EXTRA_LAYER_RESOLUTION_RECEIPT_INVALID"
            ),
            "model_revision": _commit(
                self.model_revision, "EXTRA_LAYER_MODEL_REVISION_INVALID"
            ),
            "index_sha256": _sha256(
                self.index_sha256, "EXTRA_LAYER_INDEX_SHA256_INVALID"
            ),
            "num_hidden_layers": hidden,
            "roles": _roles_payload(roles),
            "evidence_current": self.evidence_current,
        }

    def role_map(self) -> dict[int, str]:
        return _role_map(self.roles, _hidden_layers(self.num_hidden_layers))

    def to_dict(self) -> dict[str, Any]:
        return self.normalized()

    @property
    def observation_id(self) -> str:
        return _sha(self.normalized())


def _validate_binding(
    report: Mapping[str, Any],
    classification: CheckpointExtraLayerClassification,
    evidence: CheckpointExtraLayerEvidenceObservation,
) -> dict[int, str]:
    if not isinstance(classification, CheckpointExtraLayerClassification):
        raise ExtraLayerClassificationError("EXTRA_LAYER_CLASSIFICATION_REQUIRED")
    if classification.schema != SCHEMA:
        raise ExtraLayerClassificationError("EXTRA_LAYER_CLASSIFICATION_SCHEMA_MISMATCH")
    if not isinstance(evidence, CheckpointExtraLayerEvidenceObservation):
        raise ExtraLayerClassificationError("EXTRA_LAYER_EVIDENCE_REQUIRED")
    if evidence.schema != EVIDENCE_SCHEMA:
        raise ExtraLayerClassificationError("EXTRA_LAYER_EVIDENCE_SCHEMA_MISMATCH")

    c = classification.normalized()
    e = evidence.normalized()
    expected_source = (
        str(report.get("model_revision", "")).lower(),
        str(report.get("index_sha256", "")).lower(),
        report.get("num_hidden_layers"),
    )
    classified_source = (
        c["model_revision"],
        c["index_sha256"],
        c["num_hidden_layers"],
    )
    observed_source = (
        e["model_revision"],
        e["index_sha256"],
        e["num_hidden_layers"],
    )
    if classified_source != expected_source or observed_source != expected_source:
        raise ExtraLayerClassificationError(
            "EXTRA_LAYER_CLASSIFICATION_SOURCE_MISMATCH",
            f"expected={expected_source!r},classified={classified_source!r},observed={observed_source!r}",
        )

    evidence_identity_fields = (
        "evidence_ref",
        "evidence_digest",
        "evidence_generation",
        "resolver_ref",
        "resolver_generation",
        "roles",
    )
    mismatches = [field for field in evidence_identity_fields if c[field] != e[field]]
    if mismatches:
        raise ExtraLayerClassificationError(
            "EXTRA_LAYER_EVIDENCE_MISMATCH", ",".join(mismatches)
        )
    if e["evidence_current"] is not True:
        raise ExtraLayerClassificationError("EXTRA_LAYER_EVIDENCE_CURRENTNESS_REQUIRED")

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
    evidence: CheckpointExtraLayerEvidenceObservation,
) -> dict[str, Any]:
    """Discharge only role blockers with matching current resolver evidence."""
    if report.get("schema") != "GLM53CheckpointLayoutProbeV1":
        raise ExtraLayerClassificationError("GLM53_LAYOUT_PROBE_REPORT_REQUIRED")
    roles = _validate_binding(report, classification, evidence)

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
    classified = _roles_payload(roles)
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
            "extra_layer_evidence_observation": evidence.to_dict(),
            "extra_layer_evidence_observation_id": evidence.observation_id,
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
