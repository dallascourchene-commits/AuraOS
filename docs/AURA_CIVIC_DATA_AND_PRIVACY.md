# Aura Civic Data and Privacy

## Truth Classes

Every civic object carries one truth class:

OFFICIAL_PRIMARY_SOURCE, OFFICIAL_DERIVED_DATA, OFFICIAL_SNAPSHOT, COMMUNITY_VERIFIED, COMMUNITY_ASSERTED, PUBLIC_SUBMISSION, MODEL_EXTRACTED, MODEL_INFERRED, SYSTEM_RULE_DERIVED, SYNTHETIC_DEMO_DATA, STALE, DISPUTED, REVOKED, UNKNOWN

Never collapse these into a generic "verified" badge.

## Privacy Classes

PUBLIC_ATTRIBUTED, PUBLIC_PSEUDONYMOUS, COMMUNITY_ONLY, FACILITATOR_ONLY, PRIVATE_NOT_SHARED

## Location Classes

EXACT_PUBLIC_LOCATION, APPROXIMATE_LOCATION, NEIGHBOURHOOD_ONLY, PRIVATE_TO_FACILITATOR, NOT_MAPPED

## Consent to Match

No contributor may be matched or contacted unless consent_to_match == true. Do not expose private contact details to an agent or another participant.

## Data Modes

- **Fixture mode** (default): fully offline, deterministic, SYNTHETIC_DEMO_DATA
- **Official snapshot mode**: curated, locally cached, OFFICIAL_SNAPSHOT
- **Live read-only mode** (stretch): host-controlled broker, no raw socket

## Indigenous Data Governance

OCAP and CARE are specific Indigenous data-governance frameworks. They are not generic compliance checkboxes. Metadata presence does not prove compliance. Cultural/governance profiles activate only through explicit profile selection.

## Community Memory

Community Memory is separate from ephemeral temp storage and unrestricted model memory. It is not a political dossier, ideology profile, reputation score, or training corpus.

## Prohibited Heatmaps

Person-level crime, addiction, homelessness, health diagnoses, child welfare, Indigenous identity, poverty, immigration status.

## Map Attribution

OpenStreetMap contributors. No bulk download from public tile servers.
