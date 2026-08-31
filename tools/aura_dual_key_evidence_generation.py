#!/usr/bin/env python3
"""Dual-key semantic/evidence identity for Aura evidence generations.

SCK identifies a canonical semantic consequence and is intentionally stable across
source/currentness/verifier refreshes. EGK identifies one exact evidence generation
supporting or falsifying that SCK. RIK identifies one process/rendezvous attempt.

This module is accounting/provenance infrastructure only. It does not turn evidence
presence, coordinates, or a successful workflow into semantic truth or effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

VERSION = "AURA_DUAL_KEY_EVIDENCE_GENERATION_V1"
A1_DRIVE_PARENT = "1mc0wUGe2tpUNesiCvwuI7JzjULZBrMIf90FirmIAfrE"
PR646_HEAD = "71d4816cf0702a39b57ecf7d6bae6298ec239800"
PR646_RUN = 33371459229
PR398_HEAD = "131dd2a5fc8b4e2cf96c0bf598845d35e6706ef8"
PR398_RUN = 33336508527
PR398_JOB = 99324255699
PR398_DRIVE_OBSERVATION = "1FIz2aGHogE32scM4pmxDkHT7MiGfr2UbUkWlIDfpI_w"
GLM53_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _domain_hash(domain: str, value: Any) -> str:
    h = hashlib.sha256()
    h.update(domain.encode("ascii"))
    h.update(b"\0")
    h.update(_canonical(value))
    return h.hexdigest()


def _sorted_unique(values: Sequence[str], field: str) -> tuple[str, ...]:
    if any(not isinstance(v, str) or not v for v in values):
        raise ValueError(f"{field}_NONEMPTY_STRINGS_REQUIRED")
    return tuple(sorted(set(values)))


@dataclass(frozen=True)
class EvidenceGeneration:
    sck: str
    source_generations: tuple[str, ...]
    evidence_digests: tuple[str, ...]
    verifier_generation: str
    currentness_generation: str
    authority_scope: str
    effect_ceiling: str
    coordinate_keys: tuple[str, ...] = ()
    independence_keys: tuple[str, ...] = ()

    @property
    def egk(self) -> str:
        return _domain_hash("AURA-EGK-v1", asdict(self))


@dataclass(frozen=True)
class ProcessIdentity:
    objective_id: str
    worker_id: str
    task_id: str
    input_hash: str
    sequence: int
    lease_id: str | None = None
    epoch: str | None = None

    @property
    def rik(self) -> str:
        return _domain_hash("AURA-RIK-v1", asdict(self))


def semantic_consequence_key(consequence: Mapping[str, Any]) -> str:
    if not isinstance(consequence, Mapping) or not consequence:
        raise ValueError("CANONICAL_CONSEQUENCE_MAPPING_REQUIRED")
    return _domain_hash("AURA-SCK-v1", dict(consequence))


def make_evidence_generation(
    *,
    sck: str,
    source_generations: Sequence[str],
    evidence_digests: Sequence[str],
    verifier_generation: str,
    currentness_generation: str,
    authority_scope: str,
    effect_ceiling: str,
    coordinate_keys: Sequence[str] = (),
    independence_keys: Sequence[str] = (),
) -> EvidenceGeneration:
    if len(sck) != 64:
        raise ValueError("SCK_SHA256_REQUIRED")
    for field, value in (
        ("verifier_generation", verifier_generation),
        ("currentness_generation", currentness_generation),
        ("authority_scope", authority_scope),
        ("effect_ceiling", effect_ceiling),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field.upper()}_REQUIRED")
    return EvidenceGeneration(
        sck=sck,
        source_generations=_sorted_unique(source_generations, "SOURCE_GENERATIONS"),
        evidence_digests=_sorted_unique(evidence_digests, "EVIDENCE_DIGESTS"),
        verifier_generation=verifier_generation,
        currentness_generation=currentness_generation,
        authority_scope=authority_scope,
        effect_ceiling=effect_ceiling,
        coordinate_keys=_sorted_unique(coordinate_keys, "COORDINATE_KEYS"),
        independence_keys=_sorted_unique(independence_keys, "INDEPENDENCE_KEYS"),
    )


def classify_commit(
    *,
    sck: str,
    egk: str,
    committed_scks: set[str],
    evidence_by_sck: Mapping[str, set[str]],
) -> str:
    if sck not in committed_scks:
        return "SEMANTIC_COMMIT"
    if egk not in evidence_by_sck.get(sck, set()):
        return "SUPPORT_MERGE"
    return "PROCESS_DUPLICATE"


def historical_glm53_fixture() -> dict[str, Any]:
    consequence = {
        "type": "REPRESENTATIVE_OFFICIAL_HEADER_GEOMETRY_CONFORMS",
        "model_revision": GLM53_REVISION,
        "scope": "layer3/expert0",
        "claim_ceiling": "REPRESENTATIVE_HEADERS_ONLY_NO_TENSOR_PAYLOAD",
    }
    sck = semantic_consequence_key(consequence)
    historical = make_evidence_generation(
        sck=sck,
        source_generations=(f"PR398@{PR398_HEAD}", f"PR646@{PR646_HEAD}"),
        evidence_digests=(
            "736f0a117eb02c486736e7224c4e0f5363ae60b9",
            "8607b1b281f5ca8c7b166376e8f6d7eb9ca07f79200f6095f0f55ca35149ba56",
        ),
        verifier_generation=f"github-run:{PR646_RUN}",
        currentness_generation="HISTORICAL_OFFICIAL_W2_OBSERVATION",
        authority_scope="SOURCE_GEOMETRY_EVIDENCE_ONLY",
        effect_ceiling="NO_CURRENT_RAW_BYTES_NO_TENSOR_PAYLOAD_NO_GATE10",
        coordinate_keys=(
            f"drive:{PR398_DRIVE_OBSERVATION}",
            f"github-job:{PR398_JOB}",
            f"github-run:{PR398_RUN}",
        ),
        independence_keys=("PR398_HOSTED_OBSERVATION", "PR646_REBIND_PROOF"),
    )
    return {
        "consequence": consequence,
        "sck": sck,
        "historical_egk": historical.egk,
        "historical": asdict(historical),
    }


def main() -> None:
    fixture = historical_glm53_fixture()
    print(json.dumps({
        "version": VERSION,
        "a1_drive_parent": A1_DRIVE_PARENT,
        "pr646_head": PR646_HEAD,
        "pr646_run": PR646_RUN,
        **fixture,
        "laws": [
            "SCKStableAcrossEvidenceRefresh",
            "EGKChangesOnSourceOrVerifierGenerationChange",
            "FreshEGKForHistoricalSCK!=FreshSemanticSibling",
            "CoordinateKeysBindEvidenceGenerationNotSemanticAuthority",
            "ProcessRetry!=EvidenceGeneration!=SemanticConsequence",
        ],
        "claim_ceiling": {
            "semantic_truth_minted": False,
            "native_private_transformer_kv_accessed": False,
            "gate10_promoted": False,
            "merge_or_deployment_authorized": False,
        },
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
