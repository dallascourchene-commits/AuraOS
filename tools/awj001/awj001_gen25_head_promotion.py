#!/usr/bin/env python3
"""AWJ-001 GEN25 deterministic typed head-promotion membrane.

D0 / HS1 / fail-closed. This contract compiles the owner-authorized internal
HEAD_PROMOTION effect only when the exact GEN24 predecessor, the GEN25
candidate's own predecessor declaration, source/currentness cut, and promotion
authority all commute. A later use must re-resolve currentness; this receipt is
not a timeless lease.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Any

SCHEMA = "AURA-AWJ001-HEAD-PROMOTION-v1.1"
PREDECESSOR_GENERATION = 24
PREDECESSOR_HEAD = "3aeb8f3db921201f"
PREDECESSOR_DRIVE_ID = "1i_nHZHRhpi_kPqeRAEgAArH0ZC7xKWSOLcXWJ_yve7s"
CANDIDATE_GENERATION = 25
CANDIDATE_DRIVE_ID = "1n2RI0U6Z4G5fV9qI8rxI5nu_36-pM5_t3uWYhdvZV5Q"
CANDIDATE_MODIFIED_TIME = "2026-08-30T05:51:19.309Z"
COMMAND_DRIVE_ID = "1Y868IKHc6ZVX4vl3H8Z5nr5ydYu2ozAl9CUSVee710w"
COMMAND_MODIFIED_TIME = "2026-08-30T06:30:51.926Z"
OWNER_DISPOSITION_DRIVE_ID = "1SnLzRLRDGib2DltXNDKBkgfgI3PWayj6O6b5I8AkyP8"
R8_CONTRACT_DRIVE_ID = "1KgxIM3-HPzfkp2oMU2fR6Mybw6dsZWUxW0Hlx0n-fAE"
R8_WORK_ORDER_DRIVE_ID = "1-TPwoUaPLySw6CQPln_7anE8DlGQ6zcMX9hw7BPpjzA"
R8_COMMAND_DRIVE_ID = "1NFWWcqdCQYSBrwpTIR5QoZCKlF0SNOZxs1NoMAMKD4w"
CURRENTNESS_CUT = "2026-09-01T05:01:41-04:00"
CURRENTNESS_QUERIES = (
    "AWJ-001 HEAD_PROMOTION GEN25 GEN26 current head typed receipt event",
    "AWJ001 g=25 head= current root",
    "AWJ-023 owner-approved bounded D0 AWJ-025 narrow staged D1 AWJ-024 HOLD promotion AWJ-028 AWJ-029 AWJ-031 active AWJ-030 runtime event Issue 308 AWJ-022 R8",
)

PROMOTED = "HEAD_PROMOTION"
HOLD_PREDECESSOR = "HOLD_AUTHORITATIVE_GEN24_MISMATCH"
HOLD_CANDIDATE = "HOLD_GEN25_CANDIDATE_INVALID"
HOLD_SUCCESSOR = "HOLD_SUCCESSOR_RELATION_INVALID"
HOLD_BINDING = "HOLD_PREDECESSOR_CHAIN_MISMATCH"
HOLD_CURRENTNESS = "HOLD_CURRENTNESS_CUT_UNBOUND"
HOLD_NEWER = "HOLD_NEWER_TYPED_HEAD_OBSERVED"
HOLD_AUTHORITY = "HOLD_PROMOTION_AUTHORITY"
HOLD_CEILING = "HOLD_CLAIM_CEILING"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, default=str).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class PromotionCut:
    observed_at: str = CURRENTNESS_CUT
    queries: tuple[str, ...] = CURRENTNESS_QUERIES
    authoritative_generation: int = PREDECESSOR_GENERATION
    authoritative_head: str = PREDECESSOR_HEAD
    candidate_predecessor_generation: int = PREDECESSOR_GENERATION
    candidate_predecessor_head: str = PREDECESSOR_HEAD
    candidate_predecessor_drive_id: str = PREDECESSOR_DRIVE_ID
    newer_typed_head_observed: bool = False
    contradictory_later_owner_disposition_observed: bool = False
    exact_candidate_ref_observed: bool = True
    exact_owner_authority_observed: bool = True
    exact_r8_refs_observed: bool = True

    @property
    def predecessor_bound(self) -> bool:
        return (
            self.candidate_predecessor_generation == PREDECESSOR_GENERATION
            and self.candidate_predecessor_head == PREDECESSOR_HEAD
            and self.candidate_predecessor_drive_id == PREDECESSOR_DRIVE_ID
        )

    @property
    def bound(self) -> bool:
        return (
            bool(self.observed_at)
            and self.queries == CURRENTNESS_QUERIES
            and self.authoritative_generation == PREDECESSOR_GENERATION
            and self.authoritative_head == PREDECESSOR_HEAD
            and self.exact_candidate_ref_observed
            and self.exact_owner_authority_observed
            and self.exact_r8_refs_observed
            and not self.contradictory_later_owner_disposition_observed
        )


@dataclass(frozen=True)
class _Flags:
    predecessor_exact: bool
    candidate_valid: bool
    successor_exact: bool
    predecessor_bound: bool
    currentness_bound: bool
    no_newer_head: bool
    promotion_authorized: bool
    ceiling: bool


def _tree(f: _Flags) -> str:
    if not f.predecessor_exact: return HOLD_PREDECESSOR
    if not f.candidate_valid: return HOLD_CANDIDATE
    if not f.successor_exact: return HOLD_SUCCESSOR
    if not f.predecessor_bound: return HOLD_BINDING
    if not f.currentness_bound: return HOLD_CURRENTNESS
    if not f.no_newer_head: return HOLD_NEWER
    if not f.promotion_authorized: return HOLD_AUTHORITY
    if not f.ceiling: return HOLD_CEILING
    return PROMOTED


def _table(f: _Flags) -> str:
    rows = (
        (not f.predecessor_exact, HOLD_PREDECESSOR),
        (not f.candidate_valid, HOLD_CANDIDATE),
        (not f.successor_exact, HOLD_SUCCESSOR),
        (not f.predecessor_bound, HOLD_BINDING),
        (not f.currentness_bound, HOLD_CURRENTNESS),
        (not f.no_newer_head, HOLD_NEWER),
        (not f.promotion_authorized, HOLD_AUTHORITY),
        (not f.ceiling, HOLD_CEILING),
        (True, PROMOTED),
    )
    return next(d for p, d in rows if p)


def prove_different_j() -> int:
    checked = 0
    for bits in itertools.product((False, True), repeat=8):
        flags = _Flags(*bits)
        if _tree(flags) != _table(flags):
            raise AssertionError("AWJ001_DIFFERENT_J_DIVERGED")
        checked += 1
    return checked


@dataclass(frozen=True)
class HeadPromotionReceipt:
    event_type: str
    disposition: str
    generation: int
    head: str
    join_address: str
    predecessor_generation: int
    predecessor_head: str
    predecessor_drive_id: str
    candidate_drive_id: str
    candidate_modified_time: str
    candidate_predecessor_generation: int
    candidate_predecessor_head: str
    candidate_predecessor_drive_id: str
    candidate_predecessor_binding_digest: str
    command_drive_id: str
    owner_disposition_drive_id: str
    currentness_cut: str
    currentness_queries: tuple[str, ...]
    currentness_observation_digest: str
    receipt_digest: str
    immutable_predecessor_preserved: bool
    current_at_promotion_cut: bool
    current_at_future_use_proven: bool = False
    queue_presence_treated_as_execution: bool = False
    public_effect_authorized: bool = False
    financial_effect_authorized: bool = False
    destructive_effect_authorized: bool = False
    main_merge_authorized: bool = False
    credential_effect_authorized: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.disposition != PROMOTED or self.event_type != PROMOTED:
            raise ValueError("AWJ001_NOT_PROMOTION")
        if self.generation != CANDIDATE_GENERATION or self.predecessor_generation != PREDECESSOR_GENERATION:
            raise ValueError("AWJ001_GENERATION_MISMATCH")
        if self.predecessor_head != PREDECESSOR_HEAD or not self.immutable_predecessor_preserved:
            raise ValueError("AWJ001_PREDECESSOR_NOT_PRESERVED")
        expected_binding = _sha({
            "candidate_drive_id": self.candidate_drive_id,
            "predecessor_generation": self.candidate_predecessor_generation,
            "predecessor_head": self.candidate_predecessor_head,
            "predecessor_drive_id": self.candidate_predecessor_drive_id,
        })
        if (
            self.candidate_predecessor_generation != PREDECESSOR_GENERATION
            or self.candidate_predecessor_head != PREDECESSOR_HEAD
            or self.candidate_predecessor_drive_id != PREDECESSOR_DRIVE_ID
            or self.candidate_predecessor_binding_digest != expected_binding
        ):
            raise ValueError("AWJ001_CANDIDATE_PREDECESSOR_BINDING_INVALID")
        if not self.current_at_promotion_cut or self.current_at_future_use_proven:
            raise ValueError("AWJ001_CURRENTNESS_SCOPE_COLLAPSE")
        if any((
            self.queue_presence_treated_as_execution,
            self.public_effect_authorized,
            self.financial_effect_authorized,
            self.destructive_effect_authorized,
            self.main_merge_authorized,
            self.credential_effect_authorized,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
        )):
            raise ValueError("AWJ001_EXCEEDED_CLAIM_CEILING")


def _binding_digest(cut: PromotionCut) -> str:
    return _sha({
        "candidate_drive_id": CANDIDATE_DRIVE_ID,
        "predecessor_generation": cut.candidate_predecessor_generation,
        "predecessor_head": cut.candidate_predecessor_head,
        "predecessor_drive_id": cut.candidate_predecessor_drive_id,
    })


def _head_body(cut: PromotionCut) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "generation": CANDIDATE_GENERATION,
        "predecessor_generation": PREDECESSOR_GENERATION,
        "predecessor_head": PREDECESSOR_HEAD,
        "predecessor_drive_id": PREDECESSOR_DRIVE_ID,
        "candidate_drive_id": CANDIDATE_DRIVE_ID,
        "candidate_modified_time": CANDIDATE_MODIFIED_TIME,
        "candidate_predecessor_generation": cut.candidate_predecessor_generation,
        "candidate_predecessor_head": cut.candidate_predecessor_head,
        "candidate_predecessor_drive_id": cut.candidate_predecessor_drive_id,
        "candidate_predecessor_binding_digest": _binding_digest(cut),
        "command_drive_id": COMMAND_DRIVE_ID,
        "command_modified_time": COMMAND_MODIFIED_TIME,
        "owner_disposition_drive_id": OWNER_DISPOSITION_DRIVE_ID,
        "r8_contract_drive_id": R8_CONTRACT_DRIVE_ID,
        "r8_work_order_drive_id": R8_WORK_ORDER_DRIVE_ID,
        "r8_command_drive_id": R8_COMMAND_DRIVE_ID,
        "currentness_cut": cut.observed_at,
        "newer_typed_head_observed": cut.newer_typed_head_observed,
    }


def assess_and_promote(*, cut: PromotionCut = PromotionCut(), promotion_authorized: bool = True) -> HeadPromotionReceipt | str:
    flags = _Flags(
        predecessor_exact=cut.authoritative_generation == PREDECESSOR_GENERATION and cut.authoritative_head == PREDECESSOR_HEAD,
        candidate_valid=cut.exact_candidate_ref_observed,
        successor_exact=CANDIDATE_GENERATION == PREDECESSOR_GENERATION + 1,
        predecessor_bound=cut.predecessor_bound,
        currentness_bound=cut.bound,
        no_newer_head=not cut.newer_typed_head_observed,
        promotion_authorized=promotion_authorized,
        ceiling=True,
    )
    disposition = _tree(flags)
    if disposition != _table(flags):
        raise RuntimeError("AWJ001_RUNTIME_DIFFERENT_J_DIVERGED")
    if disposition != PROMOTED:
        return disposition

    body = _head_body(cut)
    full = _sha(body)
    head = full[:16]
    observation_digest = _sha({
        "observed_at": cut.observed_at,
        "queries": cut.queries,
        "authoritative_generation": cut.authoritative_generation,
        "authoritative_head": cut.authoritative_head,
        "candidate_predecessor_binding_digest": _binding_digest(cut),
        "newer_typed_head_observed": cut.newer_typed_head_observed,
        "contradictory_later_owner_disposition_observed": cut.contradictory_later_owner_disposition_observed,
    })
    receipt_body = {
        **body,
        "event_type": PROMOTED,
        "head": head,
        "join_address": f"awj://AWJ-001?g={CANDIDATE_GENERATION}&head={head}",
        "currentness_observation_digest": observation_digest,
    }
    receipt = HeadPromotionReceipt(
        event_type=PROMOTED,
        disposition=PROMOTED,
        generation=CANDIDATE_GENERATION,
        head=head,
        join_address=receipt_body["join_address"],
        predecessor_generation=PREDECESSOR_GENERATION,
        predecessor_head=PREDECESSOR_HEAD,
        predecessor_drive_id=PREDECESSOR_DRIVE_ID,
        candidate_drive_id=CANDIDATE_DRIVE_ID,
        candidate_modified_time=CANDIDATE_MODIFIED_TIME,
        candidate_predecessor_generation=cut.candidate_predecessor_generation,
        candidate_predecessor_head=cut.candidate_predecessor_head,
        candidate_predecessor_drive_id=cut.candidate_predecessor_drive_id,
        candidate_predecessor_binding_digest=_binding_digest(cut),
        command_drive_id=COMMAND_DRIVE_ID,
        owner_disposition_drive_id=OWNER_DISPOSITION_DRIVE_ID,
        currentness_cut=cut.observed_at,
        currentness_queries=cut.queries,
        currentness_observation_digest=observation_digest,
        receipt_digest=_sha(receipt_body),
        immutable_predecessor_preserved=True,
        current_at_promotion_cut=True,
    )
    receipt.validate_claim_ceiling()
    return receipt


LAWS = (
    "HeadCandidate!=CurrentHead",
    "QueuePresence!=Execution",
    "PromotionRequiresExpectedPredecessorGenerationAndHead",
    "CandidateDeclaredPredecessorMustBindAuthoritativePredecessor",
    "NewerTypedHeadObserved=>NoForkHold",
    "CurrentAtPromotionCut!=CurrentAtFutureUse",
    "HeadPromotion!=PublicOrFinancialOrDestructiveAuthority",
    "K27Coordinate!=SemanticTruth!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
