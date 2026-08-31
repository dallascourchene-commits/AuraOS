#!/usr/bin/env python3
"""Generation-aware semantic-sibling admission.

A post-cut artifact observation, branch-head advance, verification retry, replica,
index, or coordinate materialization is not evidence that the underlying semantic
consequence was generated post-cut.  This membrane adds an explicit semantic
source-generation clock before delegating consequence/evidence classification to
Aura's existing semantic-sibling gate.

Accounting/orchestration only: no semantic truth, effect authority, native/private
transformer KV access, Gate-10, merge, or deployment authority is granted here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping, Sequence

from tools import aura_semantic_sibling_admission as a3

VERSION = "AURA_SEMANTIC_GENERATION_FRESHNESS_V1"
A4_CUT = "2026-08-31T09:01:32Z"

# Exact post-cut falsifier A: generated CODEMAP head over the pre-cut A3 semantic head.
CODEMAP_HEAD = "c9739c9a7d8c3c4329f10df93d4cc4afe8c4dee7"
CODEMAP_PARENT = "202a742de6919b51fac8ec4fb33312290337f907"
CODEMAP_OBSERVED_AT = "2026-08-31T09:05:07Z"
CODEMAP_SEMANTIC_GENERATED_AT = "2026-08-31T08:42:01Z"

# Exact post-cut falsifier B: K27/L0 replica whose embedded source predates the cut.
DRIVE_REPLICA_ID = "1LCli2EFCD1gFMwUwugjSn2K0GBWxHwgc"
DRIVE_SOURCE_ID = "1BraKYQ8m7_pGFhX_9s-uNc2pToHUfiq_"
DRIVE_REPLICA_OBSERVED_AT = "2026-08-31T11:22:56.132Z"
DRIVE_SOURCE_GENERATED_AT = "2026-08-20T05:58:52.140Z"


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("OFFSET_AWARE_TIMESTAMP_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class GenerationBoundCandidate:
    sibling: a3.SemanticSiblingCandidate
    semantic_generated_at: str
    artifact_observed_at: str
    source_generation_id: str
    derivation_kind: str

    def validate(self) -> None:
        semantic_at = _parse_utc(self.semantic_generated_at)
        observed_at = _parse_utc(self.artifact_observed_at)
        terminal_at = _parse_utc(self.sibling.terminal_at)
        if not self.source_generation_id.strip():
            raise ValueError("SOURCE_GENERATION_ID_REQUIRED")
        if not self.derivation_kind.strip():
            raise ValueError("DERIVATION_KIND_REQUIRED")
        if semantic_at > observed_at:
            raise ValueError("SEMANTIC_GENERATION_AFTER_OBSERVATION")
        if observed_at > terminal_at:
            raise ValueError("OBSERVATION_AFTER_TERMINAL")


@dataclass(frozen=True)
class FreshnessClassification:
    artifact_id: str
    disposition: str
    semantic_generated_at: str
    artifact_observed_at: str
    source_generation_id: str
    derivation_kind: str
    sck: str
    egk: str


@dataclass(frozen=True)
class GenerationAwareAdmissionReceipt:
    schema: str
    cut: str
    selected_artifact_ids: tuple[str, ...]
    selected_scks: tuple[str, ...]
    classifications: tuple[FreshnessClassification, ...]
    successor_admissible: bool
    artifact_time_counts_as_semantic_generation: bool
    head_advance_counts_as_semantic_generation: bool
    replica_creation_counts_as_semantic_generation: bool
    coordinate_growth_counts_as_semantic_generation: bool
    semantic_truth_minted: bool
    effect_authority_granted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def admit_generation_aware_successor(
    *,
    candidates: Sequence[GenerationBoundCandidate],
    cut: str,
    current_agent_id: str,
    committed_scks: set[str] | None = None,
    evidence_by_sck: Mapping[str, set[str]] | None = None,
) -> GenerationAwareAdmissionReceipt:
    """Require semantic generation, observation and terminality to all clear the cut.

    Only candidates whose *semantic source generation* is post-cut are delegated to
    A3's SCK/EGK admission.  A post-cut replica/index/head alone therefore cannot
    mint successor freshness even when its SCK is absent from local working state.
    """
    cut_dt = _parse_utc(cut)
    ordered = sorted(
        candidates,
        key=lambda c: (_parse_utc(c.semantic_generated_at), _parse_utc(c.artifact_observed_at), c.sibling.artifact_id),
    )
    preliminary: list[FreshnessClassification] = []
    eligible: list[a3.SemanticSiblingCandidate] = []

    for candidate in ordered:
        candidate.validate()
        s = candidate.sibling
        if not s.terminal_green:
            disposition = "NOT_TERMINAL_GREEN"
        elif s.agent_id == current_agent_id:
            disposition = "SELF_ARTIFACT"
        elif _parse_utc(candidate.artifact_observed_at) <= cut_dt:
            disposition = "STALE_PRE_CUT_OBSERVATION"
        elif _parse_utc(candidate.semantic_generated_at) <= cut_dt:
            disposition = "PRE_CUT_SEMANTIC_GENERATION"
        elif _parse_utc(s.terminal_at) <= cut_dt:
            disposition = "STALE_PRE_CUT_TERMINAL"
        else:
            disposition = "GENERATION_FRESH_DELEGATE_A3"
            eligible.append(s)
        preliminary.append(FreshnessClassification(
            artifact_id=s.artifact_id,
            disposition=disposition,
            semantic_generated_at=candidate.semantic_generated_at,
            artifact_observed_at=candidate.artifact_observed_at,
            source_generation_id=candidate.source_generation_id,
            derivation_kind=candidate.derivation_kind,
            sck=s.sck,
            egk=s.egk,
        ))

    inner = a3.admit_successor(
        candidates=eligible,
        cut=cut,
        current_agent_id=current_agent_id,
        committed_scks=committed_scks,
        evidence_by_sck=evidence_by_sck,
    )
    inner_by_id = {c.artifact_id: c.disposition for c in inner.classifications}
    merged = tuple(
        FreshnessClassification(
            artifact_id=c.artifact_id,
            disposition=inner_by_id.get(c.artifact_id, c.disposition),
            semantic_generated_at=c.semantic_generated_at,
            artifact_observed_at=c.artifact_observed_at,
            source_generation_id=c.source_generation_id,
            derivation_kind=c.derivation_kind,
            sck=c.sck,
            egk=c.egk,
        )
        for c in preliminary
    )
    return GenerationAwareAdmissionReceipt(
        schema=VERSION,
        cut=cut,
        selected_artifact_ids=inner.selected_artifact_ids,
        selected_scks=inner.selected_scks,
        classifications=merged,
        successor_admissible=inner.successor_admissible,
        artifact_time_counts_as_semantic_generation=False,
        head_advance_counts_as_semantic_generation=False,
        replica_creation_counts_as_semantic_generation=False,
        coordinate_growth_counts_as_semantic_generation=False,
        semantic_truth_minted=False,
        effect_authority_granted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def build_demo_candidate(
    *, artifact_id: str, semantic_generated_at: str, artifact_observed_at: str,
    source_generation_id: str, derivation_kind: str, semantic_type: str,
    terminal_at: str, agent_id: str = "OTHER_AGENT",
) -> GenerationBoundCandidate:
    sibling = a3.build_candidate(
        artifact_id=artifact_id,
        agent_id=agent_id,
        terminal_at=terminal_at,
        exact_head="0" * 40,
        exact_run=1,
        terminal_green=True,
        semantic_consequence={"type": semantic_type, "result": "OBSERVED"},
        source_generations=(source_generation_id,),
        evidence_digests=(artifact_id,),
        verifier_generation="A5_FIXTURE",
        currentness_generation=artifact_observed_at,
        authority_scope="AURA_ACCOUNTING_D0",
        effect_ceiling="NO_EFFECT",
        coordinate_keys=(artifact_id,),
        independence_keys=(derivation_kind,),
    )
    return GenerationBoundCandidate(
        sibling=sibling,
        semantic_generated_at=semantic_generated_at,
        artifact_observed_at=artifact_observed_at,
        source_generation_id=source_generation_id,
        derivation_kind=derivation_kind,
    )


def cross_plane_false_freshness_fixture() -> tuple[GenerationBoundCandidate, GenerationBoundCandidate]:
    return (
        build_demo_candidate(
            artifact_id=f"github:commit:{CODEMAP_HEAD}",
            semantic_generated_at=CODEMAP_SEMANTIC_GENERATED_AT,
            artifact_observed_at=CODEMAP_OBSERVED_AT,
            source_generation_id=f"github:commit:{CODEMAP_PARENT}",
            derivation_kind="DERIVED_CODEMAP_HEAD",
            semantic_type="A3_SEMANTIC_SIBLING_ADMISSION",
            terminal_at="2026-08-31T09:05:08Z",
        ),
        build_demo_candidate(
            artifact_id=f"gdrive:{DRIVE_REPLICA_ID}",
            semantic_generated_at=DRIVE_SOURCE_GENERATED_AT,
            artifact_observed_at=DRIVE_REPLICA_OBSERVED_AT,
            source_generation_id=f"gdrive:{DRIVE_SOURCE_ID}",
            derivation_kind="K27_L0_REPLICA",
            semantic_type="WP04_ARENA_OF_ARENAS_HARDENING_GEN003",
            terminal_at="2026-08-31T11:22:57Z",
        ),
    )


def main() -> None:
    receipt = admit_generation_aware_successor(
        candidates=cross_plane_false_freshness_fixture(),
        cut=A4_CUT,
        current_agent_id="GPT56SOL_A5",
    )
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "ArtifactObservedAfterCut!=SemanticGeneratedAfterCut",
        "DerivedHeadAdvance!=SemanticGenerationAdvance",
        "ReplicaCreationTime!=SourceSemanticGenerationTime",
        "K27MaterializationGeneration!=SemanticConsequenceGeneration",
        "ProofCompletionTime!=SemanticGenerationTime",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
