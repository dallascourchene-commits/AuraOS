"""Official immutable-source appraiser for the GLM-5.3 MTP extra-layer role.

D0 metadata/source verification only. This module fetches only the immutable
config.json and model.safetensors.index.json for the pinned official release,
derives the single MTP_NON_DECODER role from same-generation source facts, and
may discharge only GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED on an already
source-bound PR340 report. It never reads tensor payload, imports the model,
executes inference, or admits G2.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Callable, Mapping
from urllib.parse import quote
from urllib.request import Request, urlopen

SCHEMA = "OfficialSourceMTPRoleEvidenceV1"
SOURCE_BUNDLE_SCHEMA = "GLM53CheckpointSourceBundleV1"
OFFICIAL_REPO = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_NUM_HIDDEN_LAYERS = 78
OFFICIAL_NUM_NEXTN_PREDICT_LAYERS = 1
OFFICIAL_MTP_LAYER = 78
OFFICIAL_ROLE = "MTP_NON_DECODER"
PROVENANCE_BLOCKER = "GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"
MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_INDEX_BYTES = 16 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class OfficialSourceMTPRoleError(ValueError):
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
        raise OfficialSourceMTPRoleError("NONCANONICAL_SOURCE") from exc


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical(value))


def _immutable_url(path: str) -> str:
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
        raise OfficialSourceMTPRoleError("REMOTE_PATH_INVALID")
    return (
        f"https://huggingface.co/{OFFICIAL_REPO}/resolve/"
        f"{OFFICIAL_REVISION}/{quote(path, safe='/')}?download=true"
    )


def urllib_read_full(url: str, max_bytes: int) -> bytes:
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise OfficialSourceMTPRoleError("BYTE_CEILING_INVALID")
    req = Request(url, headers={"User-Agent": "AuraOS-AWJ032/1"})
    with urlopen(req, timeout=60) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise OfficialSourceMTPRoleError("BYTE_CEILING_EXCEEDED")
    return raw


def _parse_json_object(raw: bytes, name: str) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise OfficialSourceMTPRoleError("RAW_BYTES_REQUIRED", name)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficialSourceMTPRoleError("SOURCE_JSON_INVALID", name) from exc
    if not isinstance(value, dict):
        raise OfficialSourceMTPRoleError("SOURCE_JSON_OBJECT_REQUIRED", name)
    return value


def _normalize_weight_map(index: Mapping[str, Any]) -> dict[str, str]:
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, Mapping) or not weight_map:
        raise OfficialSourceMTPRoleError("INDEX_WEIGHT_MAP_REQUIRED")
    normalized: dict[str, str] = {}
    for key, shard in weight_map.items():
        if not isinstance(key, str) or not key or not isinstance(shard, str) or not shard:
            raise OfficialSourceMTPRoleError("INDEX_WEIGHT_MAP_ENTRY_INVALID")
        normalized[key] = shard
    return dict(sorted(normalized.items()))


def _layer_indices(weight_map: Mapping[str, str]) -> tuple[int, ...]:
    out: set[int] = set()
    prefix = "model.layers."
    for key in weight_map:
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix):]
        raw_index = rest.split(".", 1)[0]
        if raw_index.isdigit():
            out.add(int(raw_index))
    return tuple(sorted(out))


def _source_bundle_id(
    *,
    config_raw_sha256: str,
    config_parsed_sha256: str,
    index_raw_sha256: str,
    index_parsed_sha256: str,
    weight_map_digest: str,
) -> str:
    return _sha256_json(
        {
            "schema": SOURCE_BUNDLE_SCHEMA,
            "model_revision": OFFICIAL_REVISION,
            "config_raw_sha256": config_raw_sha256,
            "config_parsed_sha256": config_parsed_sha256,
            "index_raw_sha256": index_raw_sha256,
            "index_parsed_sha256": index_parsed_sha256,
            "weight_map_digest": weight_map_digest,
        }
    )


@dataclass(frozen=True)
class OfficialSourceMTPRoleEvidence:
    owner_repo: str
    immutable_model_revision: str
    config_raw_sha256: str
    config_parsed_sha256: str
    index_sha256: str
    index_parsed_sha256: str
    weight_map_digest: str
    source_bundle_id: str
    num_hidden_layers: int
    num_nextn_predict_layers: int
    observed_extra_checkpoint_layer_indices: tuple[int, ...]
    mtp_marker_keys: tuple[str, ...]
    role_index: int
    role: str
    decoder_pager_membership: bool = False
    source_verified: bool = True
    payload_bytes_read: int = 0
    g2_admitted: bool = False
    runtime_executed: bool = False
    authority: bool = False
    schema: str = SCHEMA

    @property
    def evidence_id(self) -> str:
        return _sha256_json(asdict(self))


def observe_official_mtp_role(
    *,
    read_full: Callable[[str, int], bytes] = urllib_read_full,
) -> OfficialSourceMTPRoleEvidence:
    """Verify the narrow layer-78 MTP role from exact immutable official source."""
    config_raw = read_full(_immutable_url("config.json"), MAX_CONFIG_BYTES)
    index_raw = read_full(_immutable_url("model.safetensors.index.json"), MAX_INDEX_BYTES)

    observed_index_sha = _sha256_bytes(index_raw)
    if observed_index_sha != OFFICIAL_INDEX_SHA256:
        raise OfficialSourceMTPRoleError(
            "OFFICIAL_INDEX_SHA256_MISMATCH",
            f"expected={OFFICIAL_INDEX_SHA256},observed={observed_index_sha}",
        )

    config = _parse_json_object(config_raw, "config.json")
    index = _parse_json_object(index_raw, "model.safetensors.index.json")
    hidden = config.get("num_hidden_layers")
    nextn = config.get("num_nextn_predict_layers")
    if isinstance(hidden, bool) or hidden != OFFICIAL_NUM_HIDDEN_LAYERS:
        raise OfficialSourceMTPRoleError(
            "OFFICIAL_NUM_HIDDEN_LAYERS_MISMATCH", str(hidden)
        )
    if isinstance(nextn, bool) or nextn != OFFICIAL_NUM_NEXTN_PREDICT_LAYERS:
        raise OfficialSourceMTPRoleError(
            "OFFICIAL_NUM_NEXTN_PREDICT_LAYERS_MISMATCH", str(nextn)
        )

    weight_map = _normalize_weight_map(index)
    all_indices = _layer_indices(weight_map)
    extra = tuple(i for i in all_indices if i >= hidden)
    if extra != (OFFICIAL_MTP_LAYER,):
        raise OfficialSourceMTPRoleError(
            "OFFICIAL_EXTRA_LAYER_SET_MISMATCH", repr(extra)
        )

    marker_prefix = f"model.layers.{OFFICIAL_MTP_LAYER}.eh_proj"
    marker_keys = tuple(sorted(key for key in weight_map if key.startswith(marker_prefix)))
    if not marker_keys:
        raise OfficialSourceMTPRoleError("OFFICIAL_MTP_MARKER_REQUIRED", marker_prefix)

    config_parsed_sha = _sha256_json(config)
    index_parsed_sha = _sha256_json(index)
    weight_map_digest = _sha256_json(weight_map)
    config_raw_sha = _sha256_bytes(config_raw)

    return OfficialSourceMTPRoleEvidence(
        owner_repo=OFFICIAL_REPO,
        immutable_model_revision=OFFICIAL_REVISION,
        config_raw_sha256=config_raw_sha,
        config_parsed_sha256=config_parsed_sha,
        index_sha256=observed_index_sha,
        index_parsed_sha256=index_parsed_sha,
        weight_map_digest=weight_map_digest,
        source_bundle_id=_source_bundle_id(
            config_raw_sha256=config_raw_sha,
            config_parsed_sha256=config_parsed_sha,
            index_raw_sha256=observed_index_sha,
            index_parsed_sha256=index_parsed_sha,
            weight_map_digest=weight_map_digest,
        ),
        num_hidden_layers=hidden,
        num_nextn_predict_layers=nextn,
        observed_extra_checkpoint_layer_indices=extra,
        mtp_marker_keys=marker_keys,
        role_index=OFFICIAL_MTP_LAYER,
        role=OFFICIAL_ROLE,
    )


def _status_from_blockers(blockers: list[str]) -> str:
    if "AIRLLM_REMOTE_CODE_SECURITY_BLOCK" in blockers:
        return "BLOCKED_SECURITY"
    if "GLM53_INDEX_GEOMETRY_CONFLICT" in blockers:
        return "BLOCKED_ARCHITECTURE"
    if blockers:
        return "PARTIAL"
    return "READY_FOR_HEADER_AND_TINY_FIXTURE"


def _apply_verified_source_role(
    report: Mapping[str, Any],
    evidence: OfficialSourceMTPRoleEvidence,
) -> dict[str, Any]:
    """Discharge only the resolver-provenance blocker on an exact source-bound report."""
    if report.get("schema") != "GLM53CheckpointLayoutProbeV1":
        raise OfficialSourceMTPRoleError("GLM53_LAYOUT_PROBE_REPORT_REQUIRED")
    if report.get("source_binding_proven") is not True:
        raise OfficialSourceMTPRoleError("SOURCE_BINDING_REQUIRED")
    if report.get("extra_layer_resolver_provenance_proven") is not False:
        raise OfficialSourceMTPRoleError("PROVENANCE_PRESTATE_INVALID")
    if not isinstance(evidence, OfficialSourceMTPRoleEvidence):
        raise OfficialSourceMTPRoleError("OFFICIAL_SOURCE_EVIDENCE_REQUIRED")
    if evidence.schema != SCHEMA or evidence.source_verified is not True:
        raise OfficialSourceMTPRoleError("OFFICIAL_SOURCE_EVIDENCE_UNVERIFIED")
    if (
        evidence.owner_repo != OFFICIAL_REPO
        or evidence.immutable_model_revision != OFFICIAL_REVISION
        or evidence.index_sha256 != OFFICIAL_INDEX_SHA256
        or evidence.num_hidden_layers != OFFICIAL_NUM_HIDDEN_LAYERS
        or evidence.num_nextn_predict_layers != OFFICIAL_NUM_NEXTN_PREDICT_LAYERS
        or evidence.observed_extra_checkpoint_layer_indices != (OFFICIAL_MTP_LAYER,)
        or evidence.role_index != OFFICIAL_MTP_LAYER
        or evidence.role != OFFICIAL_ROLE
        or evidence.decoder_pager_membership is not False
        or not evidence.mtp_marker_keys
        or any(not k.startswith(f"model.layers.{OFFICIAL_MTP_LAYER}.eh_proj") for k in evidence.mtp_marker_keys)
        or evidence.payload_bytes_read != 0
        or evidence.g2_admitted
        or evidence.runtime_executed
        or evidence.authority
    ):
        raise OfficialSourceMTPRoleError("OFFICIAL_SOURCE_EVIDENCE_INVARIANT_FAILED")

    expected = {
        "model_revision": evidence.immutable_model_revision,
        "index_sha256": evidence.index_sha256,
        "num_hidden_layers": evidence.num_hidden_layers,
        "source_bundle_id": evidence.source_bundle_id,
        "config_parsed_sha256": evidence.config_parsed_sha256,
        "index_parsed_sha256": evidence.index_parsed_sha256,
        "weight_map_digest": evidence.weight_map_digest,
    }
    mismatches = [
        field for field, value in expected.items()
        if report.get(field) != value
    ]
    if mismatches:
        raise OfficialSourceMTPRoleError(
            "OFFICIAL_SOURCE_REPORT_MISMATCH", ",".join(mismatches)
        )

    actual_extra = report.get("extra_checkpoint_layer_indices")
    if actual_extra != [OFFICIAL_MTP_LAYER]:
        raise OfficialSourceMTPRoleError("OFFICIAL_REPORT_EXTRA_LAYER_MISMATCH")
    unclassified = report.get("unclassified_extra_checkpoint_layer_indices")
    if unclassified not in ([], tuple()):
        raise OfficialSourceMTPRoleError("UNCLASSIFIED_EXTRA_LAYER_REMAINS")

    expected_classified = [
        {
            "index": OFFICIAL_MTP_LAYER,
            "role": OFFICIAL_ROLE,
            "decoder_pager_membership": False,
        }
    ]
    if report.get("classified_extra_checkpoint_layers") != expected_classified:
        raise OfficialSourceMTPRoleError("OFFICIAL_REPORT_ROLE_MISMATCH")

    raw_blockers = report.get("blockers")
    if not isinstance(raw_blockers, list) or any(not isinstance(v, str) for v in raw_blockers):
        raise OfficialSourceMTPRoleError("REPORT_BLOCKERS_INVALID")
    if PROVENANCE_BLOCKER not in raw_blockers:
        raise OfficialSourceMTPRoleError("PROVENANCE_BLOCKER_REQUIRED")

    blockers = sorted(set(b for b in raw_blockers if b != PROVENANCE_BLOCKER))
    logical = {
        key: value
        for key, value in report.items()
        if key not in {"logical_id", "observation_time", "claim_ceiling"}
    }
    logical.update(
        {
            "status": _status_from_blockers(blockers),
            "blockers": blockers,
            "extra_layer_resolver_provenance_proven": True,
            "extra_layer_resolver_provenance_method": "OFFICIAL_IMMUTABLE_SOURCE_DERIVATION",
            "official_mtp_role_source_evidence": asdict(evidence),
            "official_mtp_role_source_evidence_id": evidence.evidence_id,
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
        }
    )
    return {
        **logical,
        "logical_id": _sha256_json(logical),
        "observation_time": report.get("observation_time"),
        "claim_ceiling": report.get(
            "claim_ceiling", "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT"
        ),
    }


def verify_and_admit_official_mtp_role(
    report: Mapping[str, Any],
    *,
    read_full: Callable[[str, int], bytes] = urllib_read_full,
) -> dict[str, Any]:
    """Observe official immutable source, then discharge only resolver provenance."""
    return _apply_verified_source_role(
        report,
        observe_official_mtp_role(read_full=read_full),
    )
