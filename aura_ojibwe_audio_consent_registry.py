"""
Aura Ojibwe Audio Consent Registry
=====================================
Schema version: AURA_AUDIO_CONSENT_REGISTRY_V1

Enforces per-entry audio permission for all language audio operations.
No audio (community recordings, learner audio, public links) may be
accessed without a registered AudioConsentRecord with a valid permission_ref.

Audio levels (formalized in aura_language_privacy_policy.py):
  LEVEL_0 — no audio; phonetic text only
  LEVEL_1 — playback link to permitted public audio
  LEVEL_2 — local teacher-recorded consented playback
  LEVEL_3 — pronunciation scoring from consented learner audio
  LEVEL_4 — synthetic TTS from community-approved dataset

MVP scope: Levels 0 and 1 only.  Level 2+ entries may be registered but
Aura will not attempt playback without explicit playback_enabled flag.

Audit log:
  Every query (permitted or blocked) is logged for community review.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

AURA_AUDIO_CONSENT_REGISTRY_V1 = "AURA_AUDIO_CONSENT_REGISTRY_V1"


class AudioLevel(int, Enum):
    LEVEL_0_TEXT_ONLY = 0
    LEVEL_1_PUBLIC_LINK = 1
    LEVEL_2_CONSENTED_TEACHER = 2
    LEVEL_3_LEARNER_SCORING = 3
    LEVEL_4_SYNTHETIC_TTS = 4


# MVP hard limit: no level above this without additional infrastructure
MVP_MAX_AUDIO_LEVEL = AudioLevel.LEVEL_1_PUBLIC_LINK


@dataclass(frozen=True)
class AudioConsentRecord:
    """
    A registered audio permission record.

    audio_id is the key used in LexiconEntry.audio_ref.
    permission_ref must be a non-empty consent record or license identifier.
    """
    schema_version: str
    audio_id: str
    word: str
    permission_ref: str                 # Community consent record or license ID
    audio_level: AudioLevel
    source_name: str                    # Who made the recording or where audio comes from
    url: Optional[str] = None          # For LEVEL_1: public URL reference (not upload)
    playback_enabled: bool = False      # Must be explicitly True to allow playback
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.schema_version != AURA_AUDIO_CONSENT_REGISTRY_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_AUDIO_CONSENT_REGISTRY_V1}"
            )
        if not self.permission_ref:
            raise ValueError(
                f"AudioConsentRecord for {self.word!r} requires a non-empty permission_ref"
            )


@dataclass(frozen=True)
class AudioAccessDecision:
    """Result of an audio access check."""
    allowed: bool
    reason: str
    audio_level: Optional[AudioLevel]
    url: Optional[str]
    schema_version: str = AURA_AUDIO_CONSENT_REGISTRY_V1


class AudioConsentRegistry:
    """
    Registry of consented audio entries.

    Usage:
        registry = AudioConsentRegistry()
        registry.register(AudioConsentRecord(...))
        decision = registry.check_access("audio_boozhoo_01")
    """

    def __init__(self) -> None:
        self._records: Dict[str, AudioConsentRecord] = {}
        self._audit_log: List[dict] = []

    def register(self, record: AudioConsentRecord) -> None:
        self._records[record.audio_id] = record

    def check_access(self, audio_id: str) -> AudioAccessDecision:
        """
        Check whether an audio_id is registered and accessible.

        Blocked if:
          - No record exists for this audio_id
          - Record has playback_enabled=False
          - Audio level exceeds MVP_MAX_AUDIO_LEVEL
        """
        record = self._records.get(audio_id)

        if record is None:
            decision = AudioAccessDecision(
                allowed=False,
                reason=(
                    f"No audio consent record found for audio_id={audio_id!r}. "
                    "Audio access requires registration in AudioConsentRegistry "
                    "with a valid permission_ref."
                ),
                audio_level=None,
                url=None,
            )
        elif not record.playback_enabled:
            decision = AudioAccessDecision(
                allowed=False,
                reason=(
                    f"Audio for {record.word!r} (audio_id={audio_id!r}) has "
                    "playback_enabled=False. Explicit community enablement required."
                ),
                audio_level=record.audio_level,
                url=None,
            )
        elif record.audio_level > MVP_MAX_AUDIO_LEVEL:
            decision = AudioAccessDecision(
                allowed=False,
                reason=(
                    f"Audio level {record.audio_level.value} for {record.word!r} exceeds "
                    f"MVP maximum ({MVP_MAX_AUDIO_LEVEL.value}). "
                    "Higher levels require additional consent infrastructure."
                ),
                audio_level=record.audio_level,
                url=None,
            )
        else:
            decision = AudioAccessDecision(
                allowed=True,
                reason=(
                    f"Audio for {record.word!r} is registered and accessible "
                    f"at level {record.audio_level.value} ({record.source_name})."
                ),
                audio_level=record.audio_level,
                url=record.url,
            )

        self._audit(audio_id, decision)
        return decision

    def require_access(self, audio_id: str) -> AudioConsentRecord:
        """Return the record if accessible, raise PermissionError otherwise."""
        decision = self.check_access(audio_id)
        if not decision.allowed:
            raise PermissionError(f"Audio access blocked: {decision.reason}")
        return self._records[audio_id]

    def audit_log(self) -> List[dict]:
        return list(self._audit_log)

    def _audit(self, audio_id: str, decision: AudioAccessDecision) -> None:
        self._audit_log.append(
            {
                "audio_id": audio_id,
                "allowed": decision.allowed,
                "reason": decision.reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
