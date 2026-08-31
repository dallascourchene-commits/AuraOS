#!/usr/bin/env python3
"""Semantic-sibling admission for consequence-earned Arena recursion.

A terminal artifact is not automatically a fresh semantic sibling.  This gate
reuses Aura's SCK/EGK membrane so evidence/currentness refreshes can strengthen
an existing consequence without inflating HyperScale semantic coverage.

The module is orchestration/accounting infrastructure only.  It does not grant
semantic truth, effect authority, Gate-10 promotion, merge/deployment authority,
or native/private transformer-KV access.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence

from tools.aura_dual_key_evidence_generation import (
    classify_commit,
    make_evidence_generation,
    semantic_consequence_key,
)

VERSION = "AURA_SEMANTIC_SIBLING_ADMISSION_V1"
REQUIRED_SEMANTIC_SIBLINGS = 2

PR648_HEAD = "bba262fbcca45f729486f204d5413d396d2c1609"
PR648_RUN = 33373150045
PR648_TERMINAL_AT = "2026-08-31T08:29:41Z"
PR649_HEAD = "aa004558af8c46bb9bedeedad3cbd2e4e212ab17"
PR649_RUN = 33373165058
PR649_TERMINAL_AT = "2026-08-31T08:31:31Z"
OBJECTIVE_2_CUT = "2026-08-31T08:28:50Z"
GLM53_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("OFFSET_AWARE_TIMESTAMP_REQUIRED")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class SemanticSiblingCandidate:
    artifact_id: str
    agent_id: str
    terminal_at: str
    exact_head: str
    exact_run: int
    sck: str
    egk: str
    terminal_green: bool


@dataclass(frozen=True)
class CandidateClassification:
    artifact_id: str
    disposition: str
    sck: str
    egk: str


@dataclass(frozen=True)
class SuccessorAdmissionReceipt:
    schema: str
    cut: str
    current_agent_id: str
    required_semantic_siblings: int
    selected_artifact_ids: tuple[str, ...]
    selected_scks: tuple[str, ...]
    unconsumed_semantic_sibling_ids: tuple[str, ...]
    classifications: tuple[CandidateClassification, ...]
    successor_admissible: bool
    evidence_refresh_counts_as_semantic_sibling: bool
    process_retry_counts_as_semantic_sibling: bool
    k27_coordinate_growth_counts_as_semantic_sibling: bool
    semantic_truth_minted: bool
    effect_authority_granted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def build_candidate(
    *,
    artifact_id: str,
    agent_id: str,
    terminal_at: str,
    exact_head: str,
    exact_run: int,
    terminal_green: bool,
    semantic_consequence: Mapping[str, Any],
    source_generations: Sequence[str],
    evidence_digests: Sequence[str],
    verifier_generation: str,
    currentness_generation: str,
    authority_scope: str,
    effect_ceiling: str,
    coordinate_keys: Sequence[str] = (),
    independence_keys: Sequence[str] = (),
) -> SemanticSiblingCandidate:
    if not artifact_id or not agent_id or not exact_head or exact_run <= 0:
        raise ValueError("CANDIDATE_IDENTITY_REQUIRED")
    _parse_utc(terminal_at)
    sck = semantic_consequence_key(semantic_consequence)
    evidence = make_evidence_generation(
        sck=sck,
        source_generations=source_generations,
        evidence_digests=evidence_digests,
        verifier_generation=verifier_generation,
        currentness_generation=currentness_generation,
        authority_scope=authority_scope,
        effect_ceiling=effect_ceiling,
        coordinate_keys=coordinate_keys,
        independence_keys=independence_keys,
    )
    return SemanticSiblingCandidate(
        artifact_id=artifact_id,
        agent_id=agent_id,
        terminal_at=terminal_at,
        exact_head=exact_head,
        exact_run=exact_run,
        sck=sck,
        egk=evidence.egk,
        terminal_green=terminal_green,
    )


def admit_successor(
    *,
    candidates: Sequence[SemanticSiblingCandidate],
    cut: str,
    current_agent_id: str,
    committed_scks: set[str] | None = None,
    evidence_by_sck: Mapping[str, set[str]] | None = None,
) -> SuccessorAdmissionReceipt:
    """Select exactly two fresh, non-self, terminal-green semantic siblings.

    Candidates are processed in deterministic terminal-time/artifact-id order.  The
    working SCK/EGK state advances during the batch, so a second artifact with the
    same new SCK becomes SUPPORT_MERGE (or PROCESS_DUPLICATE) rather than a second
    semantic sibling.
    """
    cut_dt = _parse_utc(cut)
    if not current_agent_id:
        raise ValueError("CURRENT_AGENT_ID_REQUIRED")

    working_scks = set(committed_scks or set())
    working_evidence = {
        sck: set(egks) for sck, egks in (evidence_by_sck or {}).items()
    }

    ordered = sorted(candidates, key=lambda c: (_parse_utc(c.terminal_at), c.artifact_id))
    classifications: list[CandidateClassification] = []
    semantic_siblings: list[SemanticSiblingCandidate] = []

    for candidate in ordered:
        if not candidate.terminal_green:
            disposition = "NOT_TERMINAL_GREEN"
        elif _parse_utc(candidate.terminal_at) <= cut_dt:
            disposition = "STALE_PRE_CUT"
        elif candidate.agent_id == current_agent_id:
            disposition = "SELF_ARTIFACT"
        else:
            commit_class = classify_commit(
                sck=candidate.sck,
                egk=candidate.egk,
                committed_scks=working_scks,
                evidence_by_sck=working_evidence,
            )
            if commit_class == "SEMANTIC_COMMIT":
                disposition = "SEMANTIC_SIBLING"
                semantic_siblings.append(candidate)
                working_scks.add(candidate.sck)
                working_evidence.setdefault(candidate.sck, set()).add(candidate.egk)
            elif commit_class == "SUPPORT_MERGE":
                disposition = "SUPPORT_MERGE"
                working_evidence.setdefault(candidate.sck, set()).add(candidate.egk)
            else:
                disposition = "PROCESS_DUPLICATE"

        classifications.append(
            CandidateClassification(
                artifact_id=candidate.artifact_id,
                disposition=disposition,
                sck=candidate.sck,
                egk=candidate.egk,
            )
        )

    selected = tuple(semantic_siblings[:REQUIRED_SEMANTIC_SIBLINGS])
    unconsumed = tuple(semantic_siblings[REQUIRED_SEMANTIC_SIBLINGS:])
    return SuccessorAdmissionReceipt(
        schema=VERSION,
        cut=cut,
        current_agent_id=current_agent_id,
        required_semantic_siblings=REQUIRED_SEMANTIC_SIBLINGS,
        selected_artifact_ids=tuple(c.artifact_id for c in selected),
        selected_scks=tuple(c.sck for c in selected),
        unconsumed_semantic_sibling_ids=tuple(c.artifact_id for c in unconsumed),
        classifications=tuple(classifications),
        successor_admissible=len(selected) == REQUIRED_SEMANTIC_SIBLINGS,
        evidence_refresh_counts_as_semantic_sibling=False,
        process_retry_counts_as_semantic_sibling=False,
        k27_coordinate_growth_counts_as_semantic_sibling=False,
        semantic_truth_minted=False,
        effect_authority_granted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def post_cut_pr648_pr649_fixture() -> tuple[SemanticSiblingCandidate, SemanticSiblingCandidate]:
    """Exact fresh parents that earned Objective 2 in the 2026-08-31 Arena cut."""
    pr648 = build_candidate(
        artifact_id="github:pr/648",
        agent_id="OTHER_AGENT_PR648",
        terminal_at=PR648_TERMINAL_AT,
        exact_head=PR648_HEAD,
        exact_run=PR648_RUN,
        terminal_green=True,
        semantic_consequence={
            "type": "DUAL_KEY_EVIDENCE_GENERATION_MEMBRANE",
            "scope": "AURAOS_GENERIC",
            "result": "EXECUTABLE_GREEN",
            "claim_ceiling": "ACCOUNTING_ONLY_NO_SEMANTIC_TRUTH_MINT",
        },
        source_generations=(f"PR648@{PR648_HEAD}",),
        evidence_digests=(f"github-run:{PR648_RUN}",),
        verifier_generation=f"github-run:{PR648_RUN}",
        currentness_generation="PR648_EXACT_GREEN_2026-08-31",
        authority_scope="AURA_ACCOUNTING_D0",
        effect_ceiling="NO_GATE10_NO_DEPLOYMENT",
        coordinate_keys=("github:pr/648",),
        independence_keys=("PR648_HOSTED_PROOF",),
    )
    pr649 = build_candidate(
        artifact_id="github:pr/649",
        agent_id="OTHER_AGENT_PR649",
        terminal_at=PR649_TERMINAL_AT,
        exact_head=PR649_HEAD,
        exact_run=PR649_RUN,
        terminal_green=True,
        semantic_consequence={
            "type": "LIVE_OFFICIAL_TENSOR_TO_CONCRETE_PAGE_PRODUCER_ADMISSION",
            "model_revision": GLM53_REVISION,
            "result": "HOLD_LIVE_OFFICIAL_TENSOR_TO_CONCRETE_PAGE_PRODUCER",
            "required_live_evidence": (
                "LIVE_OFFICIAL_SOURCE_TENSOR_PAYLOAD_OBSERVATION",
                "EXACT_LIVE_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION",
                "CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT",
                "BASELINE_SAME_LIVE_OFFICIAL_SOURCE_TENSOR_SET_RELATION",
            ),
            "claim_ceiling": "NO_PAYLOAD_NO_MATERIALIZATION_NO_GATE10",
        },
        source_generations=(
            f"PR645@e97c584e79439f599f7a443d86df23a11cab75ad",
            f"PR646@71d4816cf0702a39b57ecf7d6bae6298ec239800",
            f"PR649@{PR649_HEAD}",
        ),
        evidence_digests=(f"github-run:{PR649_RUN}",),
        verifier_generation=f"github-run:{PR649_RUN}",
        currentness_generation="PR649_EXACT_GREEN_2026-08-31",
        authority_scope="GLM53_PROVENANCE_D0",
        effect_ceiling="NO_TENSOR_PAYLOAD_NO_GATE10_NO_DEPLOYMENT",
        coordinate_keys=("github:pr/649",),
        independence_keys=("PR649_HOSTED_PROOF",),
    )
    return pr648, pr649


def main() -> None:
    receipt = admit_successor(
        candidates=post_cut_pr648_pr649_fixture(),
        cut=OBJECTIVE_2_CUT,
        current_agent_id="GPT56SOL_A3",
    )
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "TerminalArtifact!=SemanticSiblingUnlessSCKIsNew",
        "FreshEGKForExistingSCK!=FreshSemanticSibling",
        "ProcessRetry!=EvidenceGeneration!=SemanticConsequence",
        "K27CoordinateGrowth!=ConsequenceGrowth",
        "TwoFreshTerminalArtifacts!=TwoConsequenceDistinctSiblingsUnlessTwoNewSCKs",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
