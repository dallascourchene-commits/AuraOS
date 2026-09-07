from __future__ import annotations

"""D0 current-read-use seal above the Memory City horizon-fenced handoff.

This module does not recompute read semantics and does not mint trust or effect
permission.  The read owner remains responsible for producing the *current*
read-use root.  This seal only prevents a previously READY read-use decision
from being replayed at a later mutation boundary after the read owner has moved.
"""

from dataclasses import dataclass

from memory_city_horizon_fenced_handoff import (
    HandoffDecision,
    HandoffDisposition,
    HandoffVerificationContext,
    MutationBoundaryProjection,
    SemanticHandoffEvidence,
    compile_horizon_fenced_handoff,
    read_use_root,
    semantic_handoff_root,
)

D0 = "D0_NONPROMOTING"


@dataclass(frozen=True)
class CurrentReadUseBinding:
    """Exact read-owner currentness input; authentication remains upstream."""

    current_read_use_root: str
    read_owner_receipt_root: str
    authority: str = D0
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for name in ("current_read_use_root", "read_owner_receipt_root"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be lowercase sha256 hex")
        if self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("current-read-use binding cannot mint authority")


def compile_current_horizon_fenced_handoff(
    cert,
    use_decision,
    current_read: CurrentReadUseBinding,
    evidence: SemanticHandoffEvidence,
    mutation: MutationBoundaryProjection,
    verification: HandoffVerificationContext,
) -> HandoffDecision:
    """Require the read decision to still be current immediately at handoff.

    A read decision can have been valid when produced and stale by the time the
    mutation boundary consumes it.  The rightful read owner therefore supplies
    its current read-use root at the boundary.  Any movement forces rebind
    before mutation/effect verification continues.
    """

    expected_read_use = read_use_root(cert, use_decision)
    if current_read.current_read_use_root != expected_read_use:
        return HandoffDecision(
            HandoffDisposition.REBIND_REQUIRED,
            "CURRENT_READ_USE_MOVED",
            semantic_handoff_root(cert),
        )
    return compile_horizon_fenced_handoff(
        cert, use_decision, evidence, mutation, verification
    )
