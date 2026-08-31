#!/usr/bin/env python3
"""Generation-aware admission for portable semantic evidence.

A portable evidence receipt may be perfectly exact and reusable inside its owned
scope while still representing a semantic producer generation that predates the
current Arena cut.  This membrane composes A5 semantic-generation freshness with
O61 portable semantic-evidence transfer without allowing transfer time, replay
time, K27 materialization time, or proof completion to reset the semantic clock.

Accounting only: no semantic truth, producer authentication, effect authority,
semantic K27 authority, native/private transformer KV access, Gate-10, merge, or
deployment authority is granted here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools import aura_semantic_generation_freshness as a5
from tools import arena_portable_semantic_evidence_transfer as o61

VERSION = "AURA_FRESH_PORTABLE_SEMANTIC_EVIDENCE_ADMISSION_V1"
CURRENT_CUT = "2026-08-31T13:12:59Z"

A5_HEAD = "6926acabaf1a6543b52e0af4042fcb4bcac45d2f"
A5_RUN = 33396232285
A5_JOB = 99501302648
O61_HEAD = "1e37cf78cb1aee0a6605f7b8fc99ec3632279b11"
O61_RUN = 33396234209
O61_JOB = 99501304240

# Provider/Git-observed semantic commit times for the two exact O61 exemplars.
Q6_SEMANTIC_GENERATED_AT = "2026-08-31T07:52:28Z"
R3_SEMANTIC_GENERATED_AT = "2026-08-31T07:52:30Z"


def _sha(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class FreshPortableEvidenceReceipt:
    schema: str
    cut: str
    artifact_id: str
    producer_head: str
    producer_semantic_generated_at: str
    transfer_observed_at: str
    terminal_at: str
    transfer_disposition: str
    portable_semantic_evidence_admitted: bool
    freshness_disposition: str
    semantic_sibling_credit: bool
    portable_evidence_reuse_allowed: bool
    transfer_time_counts_as_semantic_generation: bool
    proof_completion_counts_as_semantic_generation: bool
    replica_or_coordinate_time_counts_as_semantic_generation: bool
    producer_generation_authenticated: bool
    semantic_truth_minted: bool
    broader_claims_inherited: bool
    effect_authority_granted: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def classify_fresh_portable_evidence(
    *,
    evidence: o61.SemanticEvidenceDescriptor,
    consumer: o61.ConsumerExpectation,
    producer_semantic_generated_at: str,
    transfer_observed_at: str,
    terminal_at: str,
    cut: str,
    artifact_id: str,
    agent_id: str = "OTHER_AGENT",
    current_agent_id: str = "GPT56SOL_A6",
) -> FreshPortableEvidenceReceipt:
    """Compose exact portable transfer with source-generation freshness.

    Exact portable reuse and successor semantic novelty are deliberately separate.
    The producer-generation timestamp is structural input here; concrete hosted
    proofs must bind it to the exact producer commit/provider generation before
    assigning `producer_generation_authenticated` anywhere downstream.  This V1
    never authenticates that clock by itself.
    """
    transfer = o61.classify_transfer(evidence=evidence, consumer=consumer)
    if not artifact_id.strip():
        raise ValueError("ARTIFACT_ID_REQUIRED")

    if not transfer.portable_semantic_evidence_admitted:
        return FreshPortableEvidenceReceipt(
            schema=VERSION,
            cut=cut,
            artifact_id=artifact_id,
            producer_head=evidence.producer_head,
            producer_semantic_generated_at=producer_semantic_generated_at,
            transfer_observed_at=transfer_observed_at,
            terminal_at=terminal_at,
            transfer_disposition=transfer.disposition,
            portable_semantic_evidence_admitted=False,
            freshness_disposition="TRANSFER_NOT_ADMITTED",
            semantic_sibling_credit=False,
            portable_evidence_reuse_allowed=False,
            transfer_time_counts_as_semantic_generation=False,
            proof_completion_counts_as_semantic_generation=False,
            replica_or_coordinate_time_counts_as_semantic_generation=False,
            producer_generation_authenticated=False,
            semantic_truth_minted=False,
            broader_claims_inherited=False,
            effect_authority_granted=False,
            semantic_k27_authority_minted=False,
            native_private_transformer_kv_accessed=False,
            gate10_promoted=False,
            merge_or_deployment_authorized=False,
        )

    semantic_consequence = {
        "type": "PORTABLE_SEMANTIC_EVIDENCE_WITHIN_OWNED_SCOPE",
        "subject_digest": evidence.subject_digest,
        "producer_head": evidence.producer_head,
        "producer_run": evidence.producer_run,
        "producer_job": evidence.producer_job,
        "consequence_scope": evidence.consequence_scope,
        "consequence_digest": evidence.consequence_digest,
        "consumer_class": consumer.consumer_class,
    }
    sibling = a5.a3.build_candidate(
        artifact_id=artifact_id,
        agent_id=agent_id,
        terminal_at=terminal_at,
        exact_head=evidence.producer_head,
        exact_run=evidence.producer_run,
        terminal_green=True,
        semantic_consequence=semantic_consequence,
        source_generations=(evidence.producer_head,),
        evidence_digests=(evidence.descriptor_digest, transfer.receipt_digest),
        verifier_generation=f"run:{evidence.producer_run}:job:{evidence.producer_job}",
        currentness_generation=transfer_observed_at,
        authority_scope="PORTABLE_EVIDENCE_D0_ONLY",
        effect_ceiling="NO_EFFECT",
        coordinate_keys=(artifact_id,),
        independence_keys=(evidence.native_consumer_class,),
    )
    generation_bound = a5.GenerationBoundCandidate(
        sibling=sibling,
        semantic_generated_at=producer_semantic_generated_at,
        artifact_observed_at=transfer_observed_at,
        source_generation_id=f"github:commit:{evidence.producer_head}",
        derivation_kind="PORTABLE_SEMANTIC_EVIDENCE_TRANSFER",
    )
    admission = a5.admit_generation_aware_successor(
        candidates=(generation_bound,),
        cut=cut,
        current_agent_id=current_agent_id,
    )
    if len(admission.classifications) != 1:
        raise AssertionError("EXPECTED_ONE_FRESHNESS_CLASSIFICATION")
    freshness = admission.classifications[0].disposition
    sibling_credit = freshness == "SEMANTIC_SIBLING"

    return FreshPortableEvidenceReceipt(
        schema=VERSION,
        cut=cut,
        artifact_id=artifact_id,
        producer_head=evidence.producer_head,
        producer_semantic_generated_at=producer_semantic_generated_at,
        transfer_observed_at=transfer_observed_at,
        terminal_at=terminal_at,
        transfer_disposition=transfer.disposition,
        portable_semantic_evidence_admitted=True,
        freshness_disposition=freshness,
        semantic_sibling_credit=sibling_credit,
        portable_evidence_reuse_allowed=True,
        transfer_time_counts_as_semantic_generation=False,
        proof_completion_counts_as_semantic_generation=False,
        replica_or_coordinate_time_counts_as_semantic_generation=False,
        producer_generation_authenticated=False,
        semantic_truth_minted=False,
        broader_claims_inherited=False,
        effect_authority_granted=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def current_historical_transfer_fixture() -> dict[str, Any]:
    q6 = o61.q6_descriptor()
    r3 = o61.r3_descriptor()
    observed = "2026-08-31T13:23:03Z"
    terminal = "2026-08-31T13:23:04Z"
    q6_receipt = classify_fresh_portable_evidence(
        evidence=q6,
        consumer=o61.native_expectation(q6),
        producer_semantic_generated_at=Q6_SEMANTIC_GENERATED_AT,
        transfer_observed_at=observed,
        terminal_at=terminal,
        cut=CURRENT_CUT,
        artifact_id="portable:q6:exact-reuse",
    )
    r3_receipt = classify_fresh_portable_evidence(
        evidence=r3,
        consumer=o61.native_expectation(r3),
        producer_semantic_generated_at=R3_SEMANTIC_GENERATED_AT,
        transfer_observed_at=observed,
        terminal_at=terminal,
        cut=CURRENT_CUT,
        artifact_id="portable:r3:exact-reuse",
    )
    payload = {
        "schema": VERSION,
        "cut": CURRENT_CUT,
        "q6": {**asdict(q6_receipt), "receipt_digest": q6_receipt.receipt_digest},
        "r3": {**asdict(r3_receipt), "receipt_digest": r3_receipt.receipt_digest},
        "laws": (
            "PortableEvidenceReusable!=FreshSemanticSibling",
            "TransferObservedAfterCut!=ProducerSemanticGenerationAfterCut",
            "ProofCompletionTime!=SemanticGenerationTime",
            "HistoricalExactEvidenceMayRemainReusableWithoutResettingSemanticClock",
            "K27ReplicaOrCoordinateGrowth!=SemanticGenerationAdvance",
        ),
    }
    return {**payload, "receipt_digest": _sha(payload)}


def main() -> None:
    print(json.dumps(current_historical_transfer_fixture(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
