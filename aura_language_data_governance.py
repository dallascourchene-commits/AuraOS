"""
Aura Language Data Governance
================================
Schema version: AURA_LANGUAGE_DATA_GOVERNANCE_V1

Enforces OCAP (Ownership, Control, Access, Possession) and CARE
(Collective Benefit, Authority to Control, Responsibility, Ethics)
principles for all language data operations.

Access levels (from most open to most restricted):
  PUBLIC              — Safe for external use, LLM explanation, demos
  COMMUNITY_ONLY      — Shareable within community programs only
  TEACHER_REVIEW      — Requires fluent speaker / teacher approval
  RESTRICTED          — Internal pipeline only; never leaves local process
  CEREMONIAL_PRIVATE  — Must never be accessed programmatically; immediate block

Hard rules:
  - RESTRICTED and CEREMONIAL_PRIVATE data NEVER reach external LLMs.
  - COMMUNITY_ONLY data requires explicit session-level community_context flag.
  - The governance check is enforced at the module boundary, not as a soft hint.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

AURA_LANGUAGE_DATA_GOVERNANCE_V1 = "AURA_LANGUAGE_DATA_GOVERNANCE_V1"


class DataAccessLevel(str, Enum):
    PUBLIC = "PUBLIC"
    COMMUNITY_ONLY = "COMMUNITY_ONLY"
    TEACHER_REVIEW = "TEACHER_REVIEW"
    RESTRICTED = "RESTRICTED"
    CEREMONIAL_PRIVATE = "CEREMONIAL_PRIVATE"


# Levels that are absolutely prohibited from external LLM transmission
_LLM_BLOCKED_LEVELS = {
    DataAccessLevel.RESTRICTED,
    DataAccessLevel.CEREMONIAL_PRIVATE,
}

# Levels that require an active community context
_COMMUNITY_CONTEXT_REQUIRED = {
    DataAccessLevel.COMMUNITY_ONLY,
    DataAccessLevel.TEACHER_REVIEW,
}


@dataclass(frozen=True)
class GovernanceDecision:
    """Result of a governance check."""
    allowed: bool
    reason: str
    schema_version: str = AURA_LANGUAGE_DATA_GOVERNANCE_V1


class LanguageDataGovernancePolicy:
    """
    Central enforcement of OCAP/CARE data governance.

    Instantiate once per session and call .check_can_send_to_llm() or
    .check_access() before every data operation involving language content.

    Args:
        community_context_active: True if a community program or teacher
            session is active and community-only data may be accessed.
            Default False (most restrictive / public mode).
    """

    def __init__(self, community_context_active: bool = False) -> None:
        self.community_context_active = community_context_active
        self._audit_log: list[dict] = []

    # ------------------------------------------------------------------
    # Primary enforcement gates
    # ------------------------------------------------------------------

    def check_can_send_to_llm(
        self,
        access_level: DataAccessLevel,
        item_description: str = "",
    ) -> GovernanceDecision:
        """
        Returns GovernanceDecision(allowed=True) only for PUBLIC data.
        All other levels are refused.

        RESTRICTED and CEREMONIAL_PRIVATE entries are hard blocked.
        COMMUNITY_ONLY and TEACHER_REVIEW are soft blocked — they may not
        leave this process at all via LLM egress.
        """
        if access_level in _LLM_BLOCKED_LEVELS:
            decision = GovernanceDecision(
                allowed=False,
                reason=(
                    f"{access_level.value} data must never be sent to external LLMs. "
                    "OCAP/CARE: community retains ownership and control."
                ),
            )
        elif access_level in _COMMUNITY_CONTEXT_REQUIRED:
            decision = GovernanceDecision(
                allowed=False,
                reason=(
                    f"{access_level.value} data may only be used within community "
                    "programs and must not be transmitted to external LLMs."
                ),
            )
        elif access_level == DataAccessLevel.PUBLIC:
            decision = GovernanceDecision(
                allowed=True,
                reason="PUBLIC data may be used in bounded LLM explanation requests.",
            )
        else:
            decision = GovernanceDecision(
                allowed=False,
                reason=f"Unrecognised access level {access_level!r}; defaulting to block.",
            )

        self._audit(
            operation="check_can_send_to_llm",
            access_level=access_level,
            item_description=item_description,
            decision=decision,
        )
        return decision

    def check_access(
        self,
        access_level: DataAccessLevel,
        item_description: str = "",
    ) -> GovernanceDecision:
        """
        Returns GovernanceDecision(allowed=True) if the current session
        context permits access to data at this level.
        """
        if access_level == DataAccessLevel.CEREMONIAL_PRIVATE:
            decision = GovernanceDecision(
                allowed=False,
                reason=(
                    "CEREMONIAL_PRIVATE data must not be accessed programmatically. "
                    "OCAP: community authority above the model."
                ),
            )
        elif access_level == DataAccessLevel.RESTRICTED:
            decision = GovernanceDecision(
                allowed=False,
                reason="RESTRICTED data is pipeline-internal only.",
            )
        elif access_level in _COMMUNITY_CONTEXT_REQUIRED:
            if self.community_context_active:
                decision = GovernanceDecision(
                    allowed=True,
                    reason=f"{access_level.value} data allowed in active community session.",
                )
            else:
                decision = GovernanceDecision(
                    allowed=False,
                    reason=(
                        f"{access_level.value} data requires an active community context. "
                        "Instantiate LanguageDataGovernancePolicy(community_context_active=True)."
                    ),
                )
        else:
            decision = GovernanceDecision(
                allowed=True,
                reason=f"{access_level.value} data is accessible in this context.",
            )

        self._audit(
            operation="check_access",
            access_level=access_level,
            item_description=item_description,
            decision=decision,
        )
        return decision

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def require_access(
        self,
        access_level: DataAccessLevel,
        item_description: str = "",
    ) -> None:
        """Raise PermissionError if access is not allowed."""
        decision = self.check_access(access_level, item_description)
        if not decision.allowed:
            raise PermissionError(
                f"Governance block [{access_level.value}]: {decision.reason}"
            )

    def require_llm_safe(
        self,
        access_level: DataAccessLevel,
        item_description: str = "",
    ) -> None:
        """Raise PermissionError if data must not be sent to an external LLM."""
        decision = self.check_can_send_to_llm(access_level, item_description)
        if not decision.allowed:
            raise PermissionError(
                f"LLM egress blocked [{access_level.value}]: {decision.reason}"
            )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _audit(
        self,
        operation: str,
        access_level: DataAccessLevel,
        item_description: str,
        decision: GovernanceDecision,
    ) -> None:
        self._audit_log.append(
            {
                "operation": operation,
                "access_level": access_level.value,
                "item_description": item_description,
                "allowed": decision.allowed,
                "reason": decision.reason,
            }
        )

    def audit_log(self) -> list[dict]:
        """Return a copy of the audit log for inspection."""
        return list(self._audit_log)
