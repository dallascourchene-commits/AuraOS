"""
Aura Language Privacy Policy
==============================
Schema version: AURA_LANGUAGE_PRIVACY_POLICY_V1

Privacy enforcement for the Aura language tutor, with particular attention
to school / community program / youth use cases.

Modes:
  DEFAULT         — Local-only learner profile. No audio uploads. No external LLM
                    egress of learner data. Standard demo mode.
  CLASSROOM       — Anonymized progress. No learner_id in exports.
                    Teacher export requires explicit session grant.
  COMMUNITY       — Community-only data accessible. No external egress.
  TEACHER_EXPORT  — Explicit per-session grant for full profile export.

Rules (all modes):
  1. Learner profile is local-only by default.
  2. Learner data (history, errors, progress) NEVER goes to external LLMs.
  3. Audio is not uploaded without an explicit AudioConsentRegistry entry.
  4. Classroom mode anonymizes all progress data (no learner_id).
  5. Teacher export requires a per-session permission grant.
  6. Restricted/ceremonial language data is always blocked (enforced by governance).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

AURA_LANGUAGE_PRIVACY_POLICY_V1 = "AURA_LANGUAGE_PRIVACY_POLICY_V1"


class PrivacyMode(str, Enum):
    DEFAULT = "DEFAULT"
    CLASSROOM = "CLASSROOM"
    COMMUNITY = "COMMUNITY"
    TEACHER_EXPORT = "TEACHER_EXPORT"


@dataclass(frozen=True)
class PrivacyDecision:
    allowed: bool
    reason: str
    schema_version: str = AURA_LANGUAGE_PRIVACY_POLICY_V1


class LanguagePrivacyPolicy:
    """
    Session-scoped privacy enforcement.

    Instantiate at session start and pass into any module that might
    export or transmit learner data.

    Args:
        mode: The privacy mode for this session.
        teacher_export_granted: True if a teacher has explicitly granted
            full profile export for this session.
    """

    def __init__(
        self,
        mode: PrivacyMode = PrivacyMode.DEFAULT,
        teacher_export_granted: bool = False,
    ) -> None:
        self.mode = mode
        self.teacher_export_granted = teacher_export_granted
        self._audit_log: list[dict] = []

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_learner_data_to_llm(self, description: str = "") -> PrivacyDecision:
        """Learner data (profile, history, errors) must NEVER go to external LLMs."""
        decision = PrivacyDecision(
            allowed=False,
            reason=(
                "Learner profile data is local-only. "
                "It must not be transmitted to external LLMs in any mode."
            ),
        )
        self._audit("check_learner_data_to_llm", description, decision)
        return decision

    def check_audio_upload(self, description: str = "") -> PrivacyDecision:
        """Audio upload requires an AudioConsentRegistry entry. Always blocked by default."""
        decision = PrivacyDecision(
            allowed=False,
            reason=(
                "Audio upload is disabled by default. "
                "An AudioConsentRegistry entry with explicit permission_ref is required. "
                "Check aura_ojibwe_audio_consent_registry.py."
            ),
        )
        self._audit("check_audio_upload", description, decision)
        return decision

    def check_learner_id_in_export(self, description: str = "") -> PrivacyDecision:
        """
        Returns allowed=True only in TEACHER_EXPORT mode with explicit grant.
        CLASSROOM mode always anonymizes (no learner_id).
        """
        if self.mode == PrivacyMode.TEACHER_EXPORT and self.teacher_export_granted:
            decision = PrivacyDecision(
                allowed=True,
                reason="Teacher export mode with explicit grant: learner_id may appear in export.",
            )
        elif self.mode == PrivacyMode.CLASSROOM:
            decision = PrivacyDecision(
                allowed=False,
                reason=(
                    "Classroom mode: learner_id is always anonymized. "
                    "Progress is reported without identifying information."
                ),
            )
        else:
            decision = PrivacyDecision(
                allowed=False,
                reason=(
                    "Learner_id is local-only. "
                    "Export requires TEACHER_EXPORT mode with explicit grant."
                ),
            )
        self._audit("check_learner_id_in_export", description, decision)
        return decision

    def check_community_data_access(self, description: str = "") -> PrivacyDecision:
        """Community-only data requires COMMUNITY or TEACHER_EXPORT mode."""
        if self.mode in (PrivacyMode.COMMUNITY, PrivacyMode.TEACHER_EXPORT):
            decision = PrivacyDecision(
                allowed=True,
                reason=f"Community data accessible in {self.mode.value} mode.",
            )
        else:
            decision = PrivacyDecision(
                allowed=False,
                reason=(
                    f"Community-only data requires COMMUNITY or TEACHER_EXPORT mode. "
                    f"Current mode: {self.mode.value}."
                ),
            )
        self._audit("check_community_data_access", description, decision)
        return decision

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def require_learner_data_local(self, description: str = "") -> None:
        """Always raises — learner data never goes to LLMs."""
        decision = self.check_learner_data_to_llm(description)
        if not decision.allowed:
            raise PermissionError(f"Privacy block: {decision.reason}")

    def audit_log(self) -> list[dict]:
        return list(self._audit_log)

    def _audit(self, operation: str, description: str, decision: PrivacyDecision) -> None:
        self._audit_log.append(
            {
                "operation": operation,
                "mode": self.mode.value,
                "description": description,
                "allowed": decision.allowed,
                "reason": decision.reason,
            }
        )

    # ------------------------------------------------------------------
    # Audio levels (formalized)
    # ------------------------------------------------------------------

    @staticmethod
    def audio_level_description() -> dict:
        """
        Returns the formal audio level schema for the Aura language tutor.

        MVP supports levels 0 and 1 only.
        Levels 2–4 require additional consent infrastructure.
        """
        return {
            "AUDIO_LEVEL_0": {
                "description": "No audio. Phonetic text hints only.",
                "mvp_supported": True,
            },
            "AUDIO_LEVEL_1": {
                "description": "Playback link/reference to permitted public audio only.",
                "mvp_supported": True,
                "requires": "opd_url or publicly licensed audio reference",
            },
            "AUDIO_LEVEL_2": {
                "description": "Local teacher-recorded consented playback.",
                "mvp_supported": False,
                "requires": "AudioConsentRegistry entry with permission_ref",
            },
            "AUDIO_LEVEL_3": {
                "description": "Pronunciation scoring from consented learner audio.",
                "mvp_supported": False,
                "requires": "Learner consent + AudioConsentRegistry",
            },
            "AUDIO_LEVEL_4": {
                "description": "Synthetic TTS from community-approved dataset.",
                "mvp_supported": False,
                "requires": (
                    "Community-approved dataset, human evaluation process, "
                    "cultural review. See Ojibwe/Mi'kmaq TTS literature."
                ),
            },
        }
