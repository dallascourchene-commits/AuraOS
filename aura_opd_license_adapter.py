"""
Aura OPD License Adapter
==========================
Schema version: AURA_OPD_LICENSE_ADAPTER_V1

Enforces Ojibwe People's Dictionary (OPD) copyright restrictions:
  - CC BY-NC-SA 4.0 (generally)
  - Non-commercial use only
  - No bulk redistribution without written permission
  - University of Minnesota logos/trademarks excluded
  - Certain third-party media excluded

Reference:
  Nichols, J., Golla, V. et al. Ojibwe People's Dictionary.
  University of Minnesota. https://ojibwe.lib.umn.edu/
  Copyright © 2012–present Regents of the University of Minnesota.

Hackathon note:
  The AMD hackathon may constitute a public demo. Even if non-commercial,
  avoid bulk-reproducing OPD content. Use minimal manually-entered metadata
  examples and cite/link rather than copying. This adapter enforces that.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

AURA_OPD_LICENSE_ADAPTER_V1 = "AURA_OPD_LICENSE_ADAPTER_V1"

OPD_SOURCE_ID = "opd_main"
OPD_LICENSE = "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International"
OPD_LICENSE_SPDX = "CC-BY-NC-SA-4.0"
OPD_MAX_BULK_ENTRIES = 10  # Hard cap: more than this triggers a bulk-export block


class OPDUseContext(str, Enum):
    INDIVIDUAL_LOOKUP = "INDIVIDUAL_LOOKUP"   # Single word look-up — permitted
    PEDAGOGICAL_EXAMPLE = "PEDAGOGICAL_EXAMPLE"  # Teaching example — permitted
    CITATION_LINK = "CITATION_LINK"           # Pointing to OPD URL — always permitted
    BULK_EXPORT = "BULK_EXPORT"               # > N entries at once — blocked
    COMMERCIAL = "COMMERCIAL"                 # Any commercial use — blocked
    TRADEMARK_USE = "TRADEMARK_USE"           # UMN logos/trademarks — blocked


@dataclass(frozen=True)
class OPDAccessDecision:
    """Result of an OPD license check."""
    allowed: bool
    reason: str
    attribution_required: bool
    noncommercial_only: bool
    share_alike: bool
    schema_version: str = AURA_OPD_LICENSE_ADAPTER_V1


# ---------------------------------------------------------------------------
# OPD entry wrapper
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OPDEntry:
    """
    An entry derived from or cross-referenced with the OPD.

    Always tagged CROSS_REFERENCE — never VERIFIED.
    Always carries source_id = "opd_main" and the CC-BY-NC-SA license.
    """
    schema_version: str
    word: str
    gloss_en: str
    part_of_speech: str
    opd_url: Optional[str]                 # Direct link to the OPD entry
    dialect_note: str = (
        "OPD documents Central Southwestern Ojibwe (Minnesota/Wisconsin). "
        "This entry is a cross-reference only — verify against Treaty #1 sources."
    )
    source_id: str = OPD_SOURCE_ID
    source_type: str = "CROSS_REFERENCE"
    license: str = OPD_LICENSE_SPDX

    def __post_init__(self) -> None:
        if self.schema_version != AURA_OPD_LICENSE_ADAPTER_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_OPD_LICENSE_ADAPTER_V1}"
            )
        if self.source_type != "CROSS_REFERENCE":
            raise ValueError(
                "OPD entries must always carry source_type='CROSS_REFERENCE'. "
                "They are never VERIFIED or VETTED for Treaty #1 Plains Ojibwe."
            )


# ---------------------------------------------------------------------------
# License adapter
# ---------------------------------------------------------------------------

class OPDLicenseAdapter:
    """
    Validates OPD use against CC-BY-NC-SA 4.0 constraints.

    Call check_use_permitted() before any operation that surfaces OPD data.
    """

    def check_use_permitted(
        self,
        context: OPDUseContext,
        entry_count: int = 1,
    ) -> OPDAccessDecision:
        """
        Returns OPDAccessDecision. Raises nothing — callers decide how to handle.
        """
        if context == OPDUseContext.COMMERCIAL:
            return OPDAccessDecision(
                allowed=False,
                reason=(
                    "OPD is CC-BY-NC-SA 4.0. Commercial use requires written "
                    "permission from the University of Minnesota."
                ),
                attribution_required=True,
                noncommercial_only=True,
                share_alike=True,
            )

        if context == OPDUseContext.TRADEMARK_USE:
            return OPDAccessDecision(
                allowed=False,
                reason=(
                    "University of Minnesota logos and trademarks are excluded from the "
                    "CC-BY-NC-SA license and may not be used without explicit permission."
                ),
                attribution_required=True,
                noncommercial_only=True,
                share_alike=True,
            )

        if context == OPDUseContext.BULK_EXPORT and entry_count > OPD_MAX_BULK_ENTRIES:
            return OPDAccessDecision(
                allowed=False,
                reason=(
                    f"Bulk export of {entry_count} OPD entries exceeds the Aura safe limit "
                    f"({OPD_MAX_BULK_ENTRIES}). Redistributing large portions of the OPD "
                    "requires written permission. Use citation links instead."
                ),
                attribution_required=True,
                noncommercial_only=True,
                share_alike=True,
            )

        # Individual lookup, pedagogical example, citation link — permitted
        return OPDAccessDecision(
            allowed=True,
            reason=(
                f"OPD use in context {context.value!r} is permitted under CC-BY-NC-SA 4.0. "
                "Attribution required. Non-commercial only. Share-alike applies to derivatives."
            ),
            attribution_required=True,
            noncommercial_only=True,
            share_alike=True,
        )

    def attribution_string(self) -> str:
        """Required attribution text for any OPD-derived content."""
        return (
            "Ojibwe People's Dictionary. Nichols, J., Golla, V. et al. "
            "University of Minnesota. https://ojibwe.lib.umn.edu/ "
            f"Licensed under {OPD_LICENSE}."
        )

    def require_permitted(self, context: OPDUseContext, entry_count: int = 1) -> None:
        """Raise PermissionError if OPD use is not permitted in this context."""
        decision = self.check_use_permitted(context, entry_count)
        if not decision.allowed:
            raise PermissionError(f"OPD license block: {decision.reason}")
