#!/usr/bin/env python3
"""Fail-closed HyperScale admission for exploration versus verification work.

Aura already owns two independent rules at exact external generations:
* semantic-sibling admission separates new semantic consequence identity (SCK)
  from evidence/currentness generations (EGK) and process retries; and
* minimum-evidence-cone planning says verification should touch only unresolved,
  decision-relevant evidence leaves rather than expanding to an entire substrate.

This module composes those rules without granting effect authority.  It decides
whether a *proposal* is worth admitting as exploration or verification work and,
for verification, computes a deterministic minimum evidence cover.  It executes
no observation, model, provider, repository merge, or Gate-10 effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import itertools
import json
from typing import Iterable, Sequence

SCHEMA = "AURA_HYPERSCALE_WORK_ADMISSION_V1"

SEMANTIC_SIBLING = "SEMANTIC_SIBLING"
SUPPORT_MERGE = "SUPPORT_MERGE"
PROCESS_DUPLICATE = "PROCESS_DUPLICATE"

MODE_EXPLORATION = "EXPLORATION"
MODE_VERIFICATION = "VERIFICATION"
MODE_DUPLICATE = "NO_WORK_PROCESS_DUPLICATE"
MODE_REJECTED = "REJECTED"

MAX_OBSERVATIONS = 16
MAX_UNRESOLVED_LEAVES = 32


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _stable_unique(values: Iterable[str]) -> tuple[str, ...]:
    out = sorted(set(values))
    if any(not isinstance(value, str) or not value for value in out):
        raise ValueError("NONEMPTY_STRING_KEYS_REQUIRED")
    return tuple(out)


@dataclass(frozen=True)
class EvidenceObservation:
    observation_id: str
    covers: tuple[str, ...]
    cost_score: int
    byte_cost: int
    effect_class: str = "READ_ONLY_EVIDENCE"

    def validate(self) -> None:
        if not self.observation_id:
            raise ValueError("OBSERVATION_ID_REQUIRED")
        covers = _stable_unique(self.covers)
        if not covers:
            raise ValueError("OBSERVATION_COVERAGE_REQUIRED")
        if covers != self.covers:
            raise ValueError("OBSERVATION_COVERAGE_MUST_BE_CANONICAL")
        if type(self.cost_score) is not int or self.cost_score <= 0:
            raise ValueError("POSITIVE_COST_SCORE_REQUIRED")
        if type(self.byte_cost) is not int or self.byte_cost < 0:
            raise ValueError("NONNEGATIVE_BYTE_COST_REQUIRED")
        if self.effect_class != "READ_ONLY_EVIDENCE":
            raise ValueError("ONLY_READ_ONLY_EVIDENCE_ADMISSIBLE_V1")


@dataclass(frozen=True)
class MinimumEvidenceCover:
    unresolved_leaves: tuple[str, ...]
    selected_observation_ids: tuple[str, ...]
    selected_cost_score: int
    selected_byte_cost: int
    complete: bool

    @property
    def digest(self) -> str:
        return _sha(asdict(self))


@dataclass(frozen=True)
class WorkAdmissionReceipt:
    schema: str
    semantic_disposition: str
    mode: str
    admitted: bool
    hard_gates_pass: bool
    unresolved_leaves: tuple[str, ...]
    selected_observation_ids: tuple[str, ...]
    selected_cost_score: int
    selected_byte_cost: int
    exploration_benefit_score: int
    exploration_cost_score: int
    verification_benefit_score: int
    minimum_cover_complete: bool
    eligible_to_seek_new_sck: bool
    eligible_to_add_new_egk: bool
    counts_as_terminal_semantic_sibling_now: bool
    verification_inflates_semantic_mass: bool
    process_retry_inflates_evidence_mass: bool
    k27_coordinate_growth_grants_semantic_authority: bool
    automatic_effect_execution: bool
    semantic_truth_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def minimum_evidence_cover(
    unresolved_leaves: Sequence[str], observations: Sequence[EvidenceObservation]
) -> MinimumEvidenceCover:
    """Return the deterministic cheapest complete cover of unresolved evidence.

    Ranking is lexicographic by normalized cost score, then bytes, observation
    count, then observation IDs.  This is an exact bounded search, deliberately
    capped because HyperScale should widen only after the small cone is proven
    insufficient.
    """
    unresolved = _stable_unique(unresolved_leaves)
    if len(unresolved) > MAX_UNRESOLVED_LEAVES:
        raise ValueError("UNRESOLVED_LEAF_LIMIT_EXCEEDED")
    if len(observations) > MAX_OBSERVATIONS:
        raise ValueError("OBSERVATION_LIMIT_EXCEEDED")
    if not unresolved:
        return MinimumEvidenceCover((), (), 0, 0, True)

    canonical: list[EvidenceObservation] = []
    seen: set[str] = set()
    for observation in observations:
        observation.validate()
        if observation.observation_id in seen:
            raise ValueError("DUPLICATE_OBSERVATION_ID")
        seen.add(observation.observation_id)
        canonical.append(observation)
    canonical.sort(key=lambda item: item.observation_id)

    target = set(unresolved)
    best: tuple[tuple[object, ...], tuple[EvidenceObservation, ...]] | None = None
    for width in range(1, len(canonical) + 1):
        for combo in itertools.combinations(canonical, width):
            covered: set[str] = set()
            for item in combo:
                covered.update(item.covers)
            if not target.issubset(covered):
                continue
            ids = tuple(item.observation_id for item in combo)
            score = sum(item.cost_score for item in combo)
            bytes_ = sum(item.byte_cost for item in combo)
            rank: tuple[object, ...] = (score, bytes_, len(combo), ids)
            if best is None or rank < best[0]:
                best = (rank, combo)

    if best is None:
        return MinimumEvidenceCover(unresolved, (), 0, 0, False)
    combo = best[1]
    return MinimumEvidenceCover(
        unresolved_leaves=unresolved,
        selected_observation_ids=tuple(item.observation_id for item in combo),
        selected_cost_score=sum(item.cost_score for item in combo),
        selected_byte_cost=sum(item.byte_cost for item in combo),
        complete=True,
    )


def admit_work(
    *,
    semantic_disposition: str,
    hard_gates_pass: bool,
    unresolved_leaves: Sequence[str] = (),
    observations: Sequence[EvidenceObservation] = (),
    exploration_benefit_score: int = 0,
    exploration_cost_score: int = 0,
    verification_benefit_score: int = 0,
) -> WorkAdmissionReceipt:
    """Admit exploration or verification without conflating their evidence mass."""
    if type(hard_gates_pass) is not bool:
        raise ValueError("HARD_GATES_BOOL_REQUIRED")
    for value in (
        exploration_benefit_score,
        exploration_cost_score,
        verification_benefit_score,
    ):
        if type(value) is not int or value < 0:
            raise ValueError("NONNEGATIVE_INTEGER_SCORE_REQUIRED")

    unresolved = _stable_unique(unresolved_leaves)
    cover = minimum_evidence_cover(unresolved, observations)

    admitted = False
    eligible_sck = False
    eligible_egk = False
    reason = "UNCLASSIFIED"
    mode = MODE_REJECTED

    if semantic_disposition == PROCESS_DUPLICATE:
        mode = MODE_DUPLICATE
        reason = "PROCESS_DUPLICATE_HAS_NO_NEW_SEMANTIC_OR_EVIDENCE_GENERATION"
    elif semantic_disposition == SEMANTIC_SIBLING:
        if not hard_gates_pass:
            reason = "EXPLORATION_HARD_GATE_FAILED"
        elif exploration_benefit_score <= exploration_cost_score:
            reason = "EXPLORATION_VALUE_NOT_GREATER_THAN_COST"
        else:
            mode = MODE_EXPLORATION
            admitted = True
            eligible_sck = True
            reason = "NEW_SCK_EXPLORATION_VALUE_EXCEEDS_COST"
    elif semantic_disposition == SUPPORT_MERGE:
        if not hard_gates_pass:
            reason = "VERIFICATION_HARD_GATE_FAILED"
        elif not unresolved:
            reason = "VERIFICATION_HAS_NO_UNRESOLVED_EVIDENCE"
        elif not cover.complete:
            reason = "VERIFICATION_EVIDENCE_CONE_NOT_COVERABLE"
        elif verification_benefit_score <= cover.selected_cost_score:
            reason = "VERIFICATION_VALUE_NOT_GREATER_THAN_MINIMUM_COVER_COST"
        else:
            mode = MODE_VERIFICATION
            admitted = True
            eligible_egk = True
            reason = "NEW_EGK_VERIFICATION_VALUE_EXCEEDS_MINIMUM_COVER_COST"
    else:
        reason = "SEMANTIC_DISPOSITION_NOT_WORK_ADMISSIBLE"

    return WorkAdmissionReceipt(
        schema=SCHEMA,
        semantic_disposition=semantic_disposition,
        mode=mode,
        admitted=admitted,
        hard_gates_pass=hard_gates_pass,
        unresolved_leaves=unresolved,
        selected_observation_ids=(cover.selected_observation_ids if mode == MODE_VERIFICATION else ()),
        selected_cost_score=(cover.selected_cost_score if mode == MODE_VERIFICATION else 0),
        selected_byte_cost=(cover.selected_byte_cost if mode == MODE_VERIFICATION else 0),
        exploration_benefit_score=exploration_benefit_score,
        exploration_cost_score=exploration_cost_score,
        verification_benefit_score=verification_benefit_score,
        minimum_cover_complete=cover.complete,
        eligible_to_seek_new_sck=eligible_sck,
        eligible_to_add_new_egk=eligible_egk,
        # Admission is a proposal state, never a terminal proof artifact.
        counts_as_terminal_semantic_sibling_now=False,
        verification_inflates_semantic_mass=False,
        process_retry_inflates_evidence_mass=False,
        k27_coordinate_growth_grants_semantic_authority=False,
        automatic_effect_execution=False,
        semantic_truth_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
        reason=reason,
    )


def glm53_remaining_payload_verification_fixture() -> WorkAdmissionReceipt:
    """Apply the generic gate to the current four-slice GLM evidence debt."""
    unresolved = (
        "DOWN_SCALE_PAYLOAD",
        "DOWN_WEIGHT_PAYLOAD",
        "UP_SCALE_PAYLOAD",
        "UP_WEIGHT_PAYLOAD",
    )
    observations = (
        EvidenceObservation(
            observation_id="down-pair",
            covers=("DOWN_SCALE_PAYLOAD", "DOWN_WEIGHT_PAYLOAD"),
            cost_score=1,
            byte_cost=12_585_984,
        ),
        EvidenceObservation(
            observation_id="up-pair",
            covers=("UP_SCALE_PAYLOAD", "UP_WEIGHT_PAYLOAD"),
            cost_score=1,
            byte_cost=12_585_984,
        ),
        EvidenceObservation(
            observation_id="whole-shard",
            covers=unresolved,
            cost_score=20,
            byte_cost=4_200_000_000,
        ),
    )
    return admit_work(
        semantic_disposition=SUPPORT_MERGE,
        hard_gates_pass=True,
        unresolved_leaves=unresolved,
        observations=observations,
        verification_benefit_score=3,
    )


def public_api_has_effect_boolean() -> bool:
    """V1 must not accept any caller flag that directly authorizes an effect."""
    forbidden = {"execute", "authorize", "promote", "deploy", "gate10"}
    parameters = set(inspect.signature(admit_work).parameters)
    return bool(parameters & forbidden)


def main() -> None:
    receipt = glm53_remaining_payload_verification_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "ExplorationValue!=VerificationValue",
        "VerificationMayIncreaseEvidenceRankWithoutIncreasingSemanticMass",
        "MinimumEvidenceConeBeforeHyperScaleFanout",
        "WorkAdmission!=TerminalProof!=EffectAuthority",
        "K27CoordinateGrowth!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
