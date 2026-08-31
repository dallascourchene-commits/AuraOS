from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Optional


class RetrievalDecision(str, Enum):
    ALLOW_INITIAL = "ALLOW_INITIAL"
    ALLOW_CHANGED_AXIS = "ALLOW_CHANGED_AXIS"
    ALLOW_STATE_TRANSITION = "ALLOW_STATE_TRANSITION"
    CHANGE_AXIS_REQUIRED = "CHANGE_AXIS_REQUIRED"
    COLLAPSE_CONE = "COLLAPSE_CONE"


@dataclass(frozen=True)
class RetrievalFingerprint:
    provider: str
    tool: str
    resource: str
    query_or_pattern: str
    page_or_range: str
    semantic_purpose: str

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    def canonical_payload(self) -> dict[str, str]:
        return {
            "provider": self.provider.strip(),
            "tool": self.tool.strip(),
            "resource": self.resource.strip(),
            "query_or_pattern": self.query_or_pattern.strip(),
            "page_or_range": self.page_or_range.strip(),
            "semantic_purpose": self.semantic_purpose.strip(),
        }

    @property
    def digest(self) -> str:
        raw = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class RetrievalObservation:
    fingerprint: RetrievalFingerprint
    provider_state_generation: str
    evidence_digest: str

    def __post_init__(self) -> None:
        if not self.provider_state_generation.strip():
            raise ValueError("provider_state_generation must be non-empty")
        if not self.evidence_digest.strip():
            raise ValueError("evidence_digest must be non-empty")


@dataclass(frozen=True)
class RetrievalProgressReceipt:
    decision: RetrievalDecision
    fingerprint_digest: str
    prior_no_progress_count: int
    next_no_progress_count: int
    fingerprint_changed: bool
    provider_state_changed: bool
    evidence_changed: bool
    receipt_digest: str
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    authority_granted: bool = False
    effect_authority_granted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_claim_ceiling(self) -> None:
        if (
            self.source_currentness_proven
            or self.semantic_truth_proven
            or self.authority_granted
            or self.effect_authority_granted
            or self.native_private_transformer_kv_accessed
        ):
            raise ValueError("retrieval progress cannot promote truth/currentness/authority/KV")


def _decision_tree(
    previous: Optional[RetrievalObservation],
    current: RetrievalObservation,
    prior_no_progress_count: int,
) -> RetrievalDecision:
    if previous is None:
        return RetrievalDecision.ALLOW_INITIAL
    if previous.fingerprint.digest != current.fingerprint.digest:
        return RetrievalDecision.ALLOW_CHANGED_AXIS
    if (
        previous.provider_state_generation != current.provider_state_generation
        or previous.evidence_digest != current.evidence_digest
    ):
        return RetrievalDecision.ALLOW_STATE_TRANSITION
    if prior_no_progress_count == 0:
        return RetrievalDecision.CHANGE_AXIS_REQUIRED
    return RetrievalDecision.COLLAPSE_CONE


def _decision_table(
    previous: Optional[RetrievalObservation],
    current: RetrievalObservation,
    prior_no_progress_count: int,
) -> RetrievalDecision:
    if previous is None:
        key = ("INITIAL", False, False)
    else:
        same_fp = previous.fingerprint.digest == current.fingerprint.digest
        state_changed = (
            previous.provider_state_generation != current.provider_state_generation
        )
        evidence_changed = previous.evidence_digest != current.evidence_digest
        key = (
            "SAME" if same_fp else "CHANGED",
            state_changed,
            evidence_changed,
        )

    if key[0] == "INITIAL":
        return RetrievalDecision.ALLOW_INITIAL
    if key[0] == "CHANGED":
        return RetrievalDecision.ALLOW_CHANGED_AXIS
    if key[1] or key[2]:
        return RetrievalDecision.ALLOW_STATE_TRANSITION
    return (
        RetrievalDecision.CHANGE_AXIS_REQUIRED
        if prior_no_progress_count == 0
        else RetrievalDecision.COLLAPSE_CONE
    )


def assess_retrieval_progress(
    *,
    previous: Optional[RetrievalObservation],
    current: RetrievalObservation,
    prior_no_progress_count: int = 0,
) -> RetrievalProgressReceipt:
    if not isinstance(prior_no_progress_count, int) or isinstance(
        prior_no_progress_count, bool
    ):
        raise ValueError("prior_no_progress_count must be an integer")
    if prior_no_progress_count < 0:
        raise ValueError("prior_no_progress_count must be >= 0")
    if previous is None and prior_no_progress_count != 0:
        raise ValueError("initial retrieval cannot inherit no-progress debt")

    a = _decision_tree(previous, current, prior_no_progress_count)
    b = _decision_table(previous, current, prior_no_progress_count)
    if a != b:
        raise RuntimeError("Different-J retrieval progress classifiers diverged")

    fingerprint_changed = bool(
        previous is not None
        and previous.fingerprint.digest != current.fingerprint.digest
    )
    provider_state_changed = bool(
        previous is not None
        and previous.provider_state_generation != current.provider_state_generation
    )
    evidence_changed = bool(
        previous is not None and previous.evidence_digest != current.evidence_digest
    )

    no_progress = (
        previous is not None
        and not fingerprint_changed
        and not provider_state_changed
        and not evidence_changed
    )
    next_count = prior_no_progress_count + 1 if no_progress else 0

    payload = {
        "decision": a.value,
        "fingerprint_digest": current.fingerprint.digest,
        "prior_no_progress_count": prior_no_progress_count,
        "next_no_progress_count": next_count,
        "fingerprint_changed": fingerprint_changed,
        "provider_state_changed": provider_state_changed,
        "evidence_changed": evidence_changed,
        "claim_ceiling": {
            "source_currentness_proven": False,
            "semantic_truth_proven": False,
            "authority_granted": False,
            "effect_authority_granted": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    receipt_digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    receipt = RetrievalProgressReceipt(
        decision=a,
        fingerprint_digest=current.fingerprint.digest,
        prior_no_progress_count=prior_no_progress_count,
        next_no_progress_count=next_count,
        fingerprint_changed=fingerprint_changed,
        provider_state_changed=provider_state_changed,
        evidence_changed=evidence_changed,
        receipt_digest=receipt_digest,
    )
    receipt.validate_claim_ceiling()
    return receipt


def prove_different_j() -> int:
    base = RetrievalFingerprint("drive", "search", "folder", "q", "0:20", "hydrate")
    changed = RetrievalFingerprint("drive", "fetch", "doc", "q", "0:20", "hydrate")
    checked = 0
    for fingerprint_changed in (False, True):
        for state_changed in (False, True):
            for evidence_changed in (False, True):
                for prior_count in (0, 1, 2):
                    previous = RetrievalObservation(base, "g0", "e0")
                    current = RetrievalObservation(
                        changed if fingerprint_changed else base,
                        "g1" if state_changed else "g0",
                        "e1" if evidence_changed else "e0",
                    )
                    if _decision_tree(previous, current, prior_count) != _decision_table(
                        previous, current, prior_count
                    ):
                        raise AssertionError("Different-J mismatch")
                    checked += 1
    return checked
