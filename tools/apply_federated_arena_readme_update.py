"""One-time canonical README update for the federated Arena market vision."""
from pathlib import Path

README = Path("README.md")
text = README.read_text(encoding="utf-8")

TOC_MARKER = "- [Future Arena Families](#future-arena-families)\n"
TOC_ENTRY = "- [Federated Arena Vision](#federated-arena-vision)\n"
if TOC_ENTRY not in text:
    if TOC_MARKER not in text:
        raise SystemExit("README contents marker not found")
    text = text.replace(TOC_MARKER, TOC_MARKER + TOC_ENTRY, 1)

SECTION_MARKER = "\n---\n\n## Documentation Map\n"
SECTION = r'''
---

## Federated Arena Vision

Aura's long-term product model is not one omnipotent application. It is a federation of sovereign, bounded Arenas that can temporarily compose around a shared objective.

```text
Social Policy Arena ───────┐
Healthcare Arena ──────────┤
Budget Arena ──────────────┼─> Temporary Federated Objective Arena
Infrastructure Arena ──────┤      -> minimum authorized representations
Emergency Arena ───────────┤      -> cross-domain scenarios
Community Governance Arena ┘      -> human-governed action
```

Each participating Arena retains its own:

- data custody and exact source sidecars;
- legal, professional, cultural, or community authority;
- identity, privacy, and consent rules;
- capability leases and verifier gates;
- right to revoke access, disconnect, or continue offline.

The higher-order Arena receives compact intent and state capsules plus exact authorized references. It does not automatically acquire every underlying record or become a super-agent with unrestricted authority.

### Offline Disaster Coordination Arena

An offline-first Disaster Coordination Arena could compose community, shelter, health, transportation, infrastructure, supply, volunteer, NGO, and government emergency Arenas during a flood, wildfire, storm, evacuation, or communications outage.

A frontline worker should be able to see the operational constellation and answer bounded questions such as:

- Which verified shelters still have accessible capacity?
- Which nearby requests match the worker's role, equipment, and current lease?
- Where are food, water, medicine, fuel, generators, and transport available?
- Which routes are confirmed open, restricted, or unverified?
- Which assignments are already owned so effort is not duplicated?
- Which issue can be handled locally and which requires escalation?

The design should remain useful without an LLM through deterministic routing, local stores, forms, maps, resource matching, append-only event journals, store-and-forward synchronization, and human workflows. Model workers may summarize or propose, but they do not become the incident commander.

This direction aligns with the project's longstanding D.A.R.T. — Disaster Assistance Response Team — concept for First Nations and other communities.

### Government and institutional federation

A public-sector deployment could maintain separate Arenas for social policy, economic policy, budgets, healthcare, housing, infrastructure, environment, education, emergency management, Indigenous and treaty obligations, public safety, and defence logistics or civil support.

A temporary coordination Arena could examine one policy or emergency across those domains while preserving statutory authority, professional responsibility, treaties, Indigenous jurisdiction, procurement rules, privacy law, public accountability, and human decision-making.

Aura is not proposed as an autonomous government, military targeting system, weapon, or mass-surveillance platform. Defence-related direction is limited to governed logistics, readiness, humanitarian support, infrastructure, supply, and civil-emergency coordination.

### Intent-indexed social and public information network

A future Social or Public Information Arena may organize licensed public and consented information by intent rather than engagement ranking:

```text
public or consented sources
  -> connector-specific collection
  -> provenance and rights checks
  -> exact post/article/event sidecars
  -> VSA intent and topic representations
  -> time- and location-aware discussion constellations
  -> semantic zoom to exact sources
```

VSA may cluster related posts, claims, questions, events, offers, and knowledge across different vocabularies. The vector remains an address and routing layer; exact content, timestamps, permissions, deletion state, and provenance remain in authoritative sidecars or source systems.

Discussion heatmaps should represent topics, public questions, claims, and aggregate activity—not covert psychological or political profiles of individuals.

### Market differentiation

Disaster-management systems, crisis maps, common operational pictures, enterprise data integration, federated data spaces, social-listening tools, and agent frameworks already exist as separate categories.

Aura's proposed differentiation is a governed composition substrate joining these categories through:

- local-first and intermittent-network operation;
- purpose-limited Arena federation;
- compact semantic capsules with exact sidecar drill-down;
- temporary capabilities, leases, revocation, and dissolution;
- visible uncertainty, objections, and representation gaps;
- deterministic admission before model reasoning;
- human, professional, legal, Indigenous, and community authority above model confidence.

The detailed architecture, safety boundaries, competitive landscape, market directions, and demonstration roadmap are documented in `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md`.
'''
if "## Federated Arena Vision" not in text:
    if SECTION_MARKER not in text:
        raise SystemExit("README documentation marker not found")
    text = text.replace(SECTION_MARKER, "\n" + SECTION + SECTION_MARKER, 1)

DOC_ROW_MARKER = "| `docs/AURA_CIVIC_COMMONS_ARENA.md` | Civic product architecture | Update alongside completion changes |\n"
DOC_ROW = "| `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md` | Arena federation, disaster relief, public-sector, social-intent, and market vision | Canonical architecture-supported direction |\n"
if DOC_ROW not in text:
    if DOC_ROW_MARKER not in text:
        raise SystemExit("README documentation row marker not found")
    text = text.replace(DOC_ROW_MARKER, DOC_ROW_MARKER + DOC_ROW, 1)

README.write_text(text, encoding="utf-8")
