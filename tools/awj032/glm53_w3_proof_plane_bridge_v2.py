"""Proof-plane composition bridge for AWJ032 GLM-5.3 W3.

D0 admission only. This module consumes three already-owned proof planes:
(1) PR350 OfficialW2BoundPagerPlanV1, (2) Objective-21 independently verified
OfficialSourceMTPRoleEvidenceV1, and (3) current AirLLM HARD_FALSE static-source
security evidence. It can admit only a native *synthetic* W3 fixture. It cannot
admit official tensor payload, runtime, provider effects, quality, or G2.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "AWJ032GLM53W3ProofPlaneBridgeV2"
W2_SCHEMA = "OfficialW2BoundPagerPlanV1"
MTP_SCHEMA = "OfficialSourceMTPRoleEvidenceV1"

PR350_BASE_HEAD = "433804f845be72e7b39075d903747cbb570392d6"
PR350_BINDER_SEMANTIC_HEAD = "12959d7f3042bcea146c0d21b26628d9acb53dda"
PR409_APPRAISER_HEAD = "530c828add572d3e17fce3a980ae6e3f4a7d93d6"
AIRLLM_SECURITY_SEMANTIC_HEAD = "e26f5228b2a7ad97aa8325593cf5550febce61ed"

OFFICIAL_REPO = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_CONFIG_RAW_SHA256 = "3ac72612095574542f7fff847ada8e59d9199dd8af44bdf625d7e02615572e69"
OFFICIAL_CONFIG_PARSED_SHA256 = "d497aba98135da3586209ba863e8e42eccf77a014811d0d3df812db9909c5d40"
OFFICIAL_INDEX_PARSED_SHA256 = "08f826679200e2dc91d5e9c5514bab239369122a8d0ef81df9c8accd55d4797c"
OFFICIAL_WEIGHT_MAP_DIGEST = "f201f9a19849fab7d0cb4ce928294aa4536b03fed527ce3bf4b3be2962fbc6a7"
OFFICIAL_SOURCE_BUNDLE_ID = "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b"
OFFICIAL_MTP_EVIDENCE_ID = "b0803af6fdb7afd0dcdbf7c5b718605658a02534c960d965cfc1729eb4d9d3a2"

W2_RECEIPT = "736f0a117eb02c486736e7224c4e0f5363ae60b9"
W2_PRODUCER_SEMANTIC_HEAD = "131dd2a5fc8b4e2cf96c0bf598845d35e6706ef8"
W2_PRODUCER_RUN_REF = "github-actions:run:33336508527:job:99324255699"
W2_DRIVE_REF = "drive:1FIz2aGHogE32scM4pmxDkHT7MiGfr2UbUkWlIDfpI_w"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


class W3ProofPlaneError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise W3ProofPlaneError("NONCANONICAL_EVIDENCE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _mapping(value: Any, code: str) -> dict[str, Any]:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise W3ProofPlaneError(code)
    return dict(value)


def _bool(value: Any, code: str) -> bool:
    if type(value) is not bool:
        raise W3ProofPlaneError(code)
    return value


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise W3ProofPlaneError(code)
    return value.strip()


def _sha40(value: Any, code: str) -> str:
    out = _text(value, code).lower()
    if not _SHA40.fullmatch(out):
        raise W3ProofPlaneError(code)
    return out


def _sha64(value: Any, code: str) -> str:
    out = _text(value, code).lower()
    if not _SHA64.fullmatch(out):
        raise W3ProofPlaneError(code)
    return out


def _w2_observation_digest() -> str:
    return _digest(
        {
            "repo_id": OFFICIAL_REPO,
            "model_revision": OFFICIAL_REVISION,
            "index_sha256": OFFICIAL_INDEX_SHA256,
            "layer": 3,
            "expert": 0,
            "receipt_digest": W2_RECEIPT,
            "producer_semantic_head": W2_PRODUCER_SEMANTIC_HEAD,
            "producer_run_ref": W2_PRODUCER_RUN_REF,
            "drive_observation_ref": W2_DRIVE_REF,
            "representative_only": True,
            "tensor_payload_read": False,
            "g2_admitted": False,
            "authority": False,
            "schema": "GLM53OfficialW2ObservationV1",
        }
    )


EXPECTED_W2_OBSERVATION_DIGEST = _w2_observation_digest()


def _normalize_w2(plan: Any) -> dict[str, Any]:
    p = _mapping(plan, "OFFICIAL_W2_BOUND_PLAN_REQUIRED")
    if p.get("schema") != W2_SCHEMA:
        raise W3ProofPlaneError("OFFICIAL_W2_BOUND_PLAN_REQUIRED")
    inner = _sha64(p.get("inner_source_plan_digest"), "W2_INNER_SOURCE_PLAN_DIGEST_REQUIRED")
    obs = _sha64(p.get("official_w2_observation_digest"), "W2_OBSERVATION_DIGEST_REQUIRED")
    receipt = _sha40(p.get("official_w2_receipt_digest"), "W2_RECEIPT_REQUIRED")
    producer = _sha40(
        p.get("official_w2_producer_semantic_head"), "W2_PRODUCER_SEMANTIC_HEAD_REQUIRED"
    )
    run_ref = _text(p.get("official_w2_producer_run_ref"), "W2_PRODUCER_RUN_REQUIRED")
    drive_ref = _text(p.get("official_w2_drive_observation_ref"), "W2_DRIVE_REF_REQUIRED")
    layer, expert = p.get("representative_layer"), p.get("representative_expert")
    if isinstance(layer, bool) or not isinstance(layer, int):
        raise W3ProofPlaneError("W2_REPRESENTATIVE_LAYER_REQUIRED")
    if isinstance(expert, bool) or not isinstance(expert, int):
        raise W3ProofPlaneError("W2_REPRESENTATIVE_EXPERT_REQUIRED")
    if _bool(p.get("official_w2_producer_observation_proven"), "W2_PRODUCER_PROVEN_BOOL_REQUIRED") is not True:
        raise W3ProofPlaneError("W2_PRODUCER_PROOF_REQUIRED")
    for field, code in (
        ("all_experts_header_uniformity_proven", "W2_UNIVERSALITY_BOOL_REQUIRED"),
        ("g2_admitted", "W2_G2_BOOL_REQUIRED"),
        ("runtime_execution_proven", "W2_RUNTIME_BOOL_REQUIRED"),
        ("large_checkpoint_admitted", "W2_CHECKPOINT_BOOL_REQUIRED"),
        ("authority", "W2_AUTHORITY_BOOL_REQUIRED"),
    ):
        if _bool(p.get(field), code) is not False:
            raise W3ProofPlaneError("W2_EFFECT_OR_SCOPE_WIDENING", field)
    exact = {
        "observation": (obs, EXPECTED_W2_OBSERVATION_DIGEST),
        "receipt": (receipt, W2_RECEIPT),
        "producer": (producer, W2_PRODUCER_SEMANTIC_HEAD),
        "run_ref": (run_ref, W2_PRODUCER_RUN_REF),
        "drive_ref": (drive_ref, W2_DRIVE_REF),
        "layer": (layer, 3),
        "expert": (expert, 0),
    }
    wrong = [name for name, (seen, expected) in exact.items() if seen != expected]
    if wrong:
        raise W3ProofPlaneError("W2_OFFICIAL_PRODUCER_IDENTITY_MISMATCH", ",".join(wrong))
    normalized = {
        "schema": W2_SCHEMA,
        "inner_source_plan_digest": inner,
        "official_w2_observation_digest": obs,
        "official_w2_receipt_digest": receipt,
        "official_w2_producer_semantic_head": producer,
        "official_w2_producer_run_ref": run_ref,
        "official_w2_drive_observation_ref": drive_ref,
        "representative_layer": layer,
        "representative_expert": expert,
        "official_w2_producer_observation_proven": True,
        "all_experts_header_uniformity_proven": False,
        "g2_admitted": False,
        "runtime_execution_proven": False,
        "large_checkpoint_admitted": False,
        "authority": False,
    }
    return {**normalized, "outer_source_plan_digest": _digest(normalized)}


def _normalize_mtp(evidence: Any) -> dict[str, Any]:
    e = _mapping(evidence, "OFFICIAL_MTP_ROLE_EVIDENCE_REQUIRED")
    supplied_id = _sha64(e.pop("evidence_id", None), "OFFICIAL_MTP_EVIDENCE_ID_REQUIRED")
    if e.get("schema") != MTP_SCHEMA:
        raise W3ProofPlaneError("OFFICIAL_MTP_ROLE_EVIDENCE_REQUIRED")
    markers = e.get("mtp_marker_keys")
    if (
        not isinstance(markers, Sequence)
        or isinstance(markers, (str, bytes))
        or not markers
        or any(not isinstance(v, str) or not v.startswith("model.layers.78.eh_proj") for v in markers)
    ):
        raise W3ProofPlaneError("OFFICIAL_MTP_MARKER_REQUIRED")
    extras = e.get("observed_extra_checkpoint_layer_indices")
    if not isinstance(extras, Sequence) or isinstance(extras, (str, bytes)):
        raise W3ProofPlaneError("OFFICIAL_MTP_EXTRA_LAYER_SET_REQUIRED")
    normalized = {
        "owner_repo": _text(e.get("owner_repo"), "OFFICIAL_MTP_REPO_REQUIRED"),
        "immutable_model_revision": _sha40(
            e.get("immutable_model_revision"), "OFFICIAL_MTP_REVISION_REQUIRED"
        ),
        "config_raw_sha256": _sha64(e.get("config_raw_sha256"), "OFFICIAL_MTP_CONFIG_RAW_REQUIRED"),
        "config_parsed_sha256": _sha64(
            e.get("config_parsed_sha256"), "OFFICIAL_MTP_CONFIG_PARSED_REQUIRED"
        ),
        "index_sha256": _sha64(e.get("index_sha256"), "OFFICIAL_MTP_INDEX_REQUIRED"),
        "index_parsed_sha256": _sha64(
            e.get("index_parsed_sha256"), "OFFICIAL_MTP_INDEX_PARSED_REQUIRED"
        ),
        "weight_map_digest": _sha64(e.get("weight_map_digest"), "OFFICIAL_MTP_WEIGHT_MAP_REQUIRED"),
        "source_bundle_id": _sha64(e.get("source_bundle_id"), "OFFICIAL_MTP_SOURCE_BUNDLE_REQUIRED"),
        "num_hidden_layers": e.get("num_hidden_layers"),
        "num_nextn_predict_layers": e.get("num_nextn_predict_layers"),
        "observed_extra_checkpoint_layer_indices": list(extras),
        "mtp_marker_keys": list(markers),
        "role_index": e.get("role_index"),
        "role": _text(e.get("role"), "OFFICIAL_MTP_ROLE_REQUIRED"),
        "decoder_pager_membership": _bool(
            e.get("decoder_pager_membership"), "OFFICIAL_MTP_DECODER_MEMBERSHIP_BOOL_REQUIRED"
        ),
        "source_verified": _bool(e.get("source_verified"), "OFFICIAL_MTP_SOURCE_VERIFIED_BOOL_REQUIRED"),
        "payload_bytes_read": e.get("payload_bytes_read"),
        "g2_admitted": _bool(e.get("g2_admitted"), "OFFICIAL_MTP_G2_BOOL_REQUIRED"),
        "runtime_executed": _bool(e.get("runtime_executed"), "OFFICIAL_MTP_RUNTIME_BOOL_REQUIRED"),
        "authority": _bool(e.get("authority"), "OFFICIAL_MTP_AUTHORITY_BOOL_REQUIRED"),
        "schema": MTP_SCHEMA,
    }
    expected = {
        "owner_repo": OFFICIAL_REPO,
        "immutable_model_revision": OFFICIAL_REVISION,
        "config_raw_sha256": OFFICIAL_CONFIG_RAW_SHA256,
        "config_parsed_sha256": OFFICIAL_CONFIG_PARSED_SHA256,
        "index_sha256": OFFICIAL_INDEX_SHA256,
        "index_parsed_sha256": OFFICIAL_INDEX_PARSED_SHA256,
        "weight_map_digest": OFFICIAL_WEIGHT_MAP_DIGEST,
        "source_bundle_id": OFFICIAL_SOURCE_BUNDLE_ID,
        "num_hidden_layers": 78,
        "num_nextn_predict_layers": 1,
        "observed_extra_checkpoint_layer_indices": [78],
        "role_index": 78,
        "role": "MTP_NON_DECODER",
        "decoder_pager_membership": False,
        "source_verified": True,
        "payload_bytes_read": 0,
        "g2_admitted": False,
        "runtime_executed": False,
        "authority": False,
    }
    wrong = [k for k, v in expected.items() if normalized.get(k) != v]
    if wrong:
        raise W3ProofPlaneError("OFFICIAL_MTP_SOURCE_IDENTITY_MISMATCH", ",".join(wrong))
    observed_id = _digest(normalized)
    if observed_id != supplied_id or supplied_id != OFFICIAL_MTP_EVIDENCE_ID:
        raise W3ProofPlaneError(
            "OFFICIAL_MTP_EVIDENCE_ID_MISMATCH",
            f"supplied={supplied_id},observed={observed_id}",
        )
    return {**normalized, "evidence_id": supplied_id}


def _normalize_security(evidence: Any) -> dict[str, Any]:
    s = _mapping(evidence, "AIRLLM_SECURITY_EVIDENCE_REQUIRED")
    semantic = _sha40(s.get("semantic_head"), "AIRLLM_SECURITY_SEMANTIC_HEAD_REQUIRED")
    hosted = _bool(s.get("hosted_contract_pass"), "AIRLLM_HOSTED_PASS_BOOL_REQUIRED")
    hard_false = _bool(s.get("hard_false_remote_code_proven"), "AIRLLM_HARD_FALSE_BOOL_REQUIRED")
    static_only = _bool(s.get("static_source_security_only"), "AIRLLM_STATIC_ONLY_BOOL_REQUIRED")
    if semantic != AIRLLM_SECURITY_SEMANTIC_HEAD:
        raise W3ProofPlaneError("AIRLLM_SECURITY_GENERATION_STALE")
    if not hosted:
        raise W3ProofPlaneError("AIRLLM_SECURITY_HOSTED_CONTRACT_REQUIRED")
    if not hard_false:
        raise W3ProofPlaneError("AIRLLM_HARD_FALSE_REMOTE_CODE_REQUIRED")
    if not static_only:
        raise W3ProofPlaneError("AIRLLM_SECURITY_CLAIM_CEILING_INVALID")
    return {
        "semantic_head": semantic,
        "hosted_contract_pass": True,
        "hard_false_remote_code_proven": True,
        "static_source_security_only": True,
    }


@dataclass(frozen=True)
class W3ProofPlaneReceipt:
    status: str
    w2_outer_source_plan_digest: str
    w2_inner_source_plan_digest: str
    official_mtp_role_evidence_id: str
    airllm_security_semantic_head: str
    pr350_base_head: str = PR350_BASE_HEAD
    pr350_binder_semantic_head: str = PR350_BINDER_SEMANTIC_HEAD
    pr409_appraiser_head: str = PR409_APPRAISER_HEAD
    native_synthetic_w3_fixture_admitted: bool = True
    official_tensor_payload_admitted: bool = False
    g2_admitted: bool = False
    runtime_execution_admitted: bool = False
    provider_effect_admitted: bool = False
    quality_proven: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def evaluate_w3_proof_planes(
    *,
    official_w2_plan: Any,
    official_mtp_role_evidence: Any,
    airllm_security_evidence: Any,
) -> W3ProofPlaneReceipt:
    w2 = _normalize_w2(official_w2_plan)
    mtp = _normalize_mtp(official_mtp_role_evidence)
    security = _normalize_security(airllm_security_evidence)
    return W3ProofPlaneReceipt(
        status="ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE",
        w2_outer_source_plan_digest=w2["outer_source_plan_digest"],
        w2_inner_source_plan_digest=w2["inner_source_plan_digest"],
        official_mtp_role_evidence_id=mtp["evidence_id"],
        airllm_security_semantic_head=security["semantic_head"],
    )
