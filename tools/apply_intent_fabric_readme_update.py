"""One-time canonical README update for the intent-compiled application fabric."""
from pathlib import Path

README = Path("README.md")
text = README.read_text(encoding="utf-8")

TOC_MARKER = "- [Future Arena Families](#future-arena-families)\n"
TOC_ENTRY = "- [Intent-Compiled Application Fabric](#intent-compiled-application-fabric)\n"
if TOC_ENTRY not in text:
    if TOC_MARKER not in text:
        raise SystemExit("README contents marker not found")
    text = text.replace(TOC_MARKER, TOC_MARKER + TOC_ENTRY, 1)

SECTION_MARKER = "\n---\n\n## Federated Arena Vision\n"
SECTION = r'''
---

## Intent-Compiled Application Fabric

Aura's consumer-scale future is not a larger collection of monolithic websites and apps. It is an intent-compiled application fabric in which a person begins with an objective and Aura assembles a temporary, governed environment from compatible modules.

```text
person-owned or authorized data
+ current intent
+ consent, place, time, budget, and constraints
+ governed capability modules
  -> six-slot IntentPacket
  -> admitted capability graph
  -> temporary personal Arena
  -> adaptive 2D / 3D / AR / voice interface
  -> verified result or memory
  -> capability revocation and dissolution
```

The user no longer has to begin by choosing which platform will own the journey. The user states what they are trying to accomplish. Aura discovers the smallest compatible capabilities, presents their permissions and trade-offs, assembles the interface, and preserves only what the user or participants approve.

### From data silos to purpose-limited views

In the conventional platform model, a music service owns listening history, a dating service owns relationship preferences, a marketplace owns transaction history, and a social network owns the relationship graph.

In an Aura fabric, the person or governing community retains the authoritative data and grants narrow views such as:

```text
music_preferences_for_this_event
calendar_availability_for_these_people
approved_photos_for_this_memory_video
mobility_requirements_for_this_route
budget_range_for_this_purchase
```

The active intent becomes a first-class data-governance object. A module receives only the fields, duration, destination, and derivative-use rights required for the objective.

Semantic representations may locate relevant songs, people, products, memories, places, posts, or modules, but exact content and permissions remain in authoritative sidecars.

> **Intent selects. Vectors point. Sidecars prove. Governance authorizes.**

### Modules instead of totalizing applications

The reusable unit becomes a signed, bounded capability module rather than a complete platform. Modules may provide calendar access, music selection, night-sky positioning, weather, routing, reservations, camera capture, audio recording, video editing, budgeting, accessibility, consent, AR presentation, or memory timelines.

A module contract should declare:

- supported intent slots;
- input and output schemas;
- required capabilities;
- data classes and destinations;
- retention and training policy;
- offline behavior and resource budget;
- declarative interface and accessibility contract;
- verifier, rollback, licence, signature, digest, and revocation information.

Providers can contribute one excellent capability without acquiring the user's complete identity, relationship, media, location, and payment history.

### Six-slot grammar as a semantic compatibility layer

The canonical software grammar can act as a semantic ABI for independently developed capabilities:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

At the fabric level:

- `DIR` identifies target, domain, or destination;
- `ASP` identifies lifecycle, timing, duration, or completion state;
- `CLASS` identifies capability or object class;
- `SUBJ` identifies the authorized person, group, device, or institution;
- `VOICE` identifies agency, delegation, proposal, automation, or review mode;
- `STEM` identifies the core operation.

This common ordering helps Aura determine which modules can compose. It does not replace signatures, schemas, policy, sandboxes, leases, verifiers, or human approval.

### Example: Perfect Date Arena

A person could ask:

> Create a meaningful date Friday evening. We like stargazing, quiet food, live acoustic music, and personal memories. Keep it under $180, do not expose our location publicly, record only after mutual consent, and create a private short film afterward.

Aura may assemble:

- shared calendar and weather modules;
- astronomy and route modules;
- restaurant, event, music, and budget modules;
- accessibility and private-location policy modules;
- mutual media-consent, camera, audio, and video-editing modules;
- a relationship memory-timeline and private playback module.

The music provider does not need to own the calendar. The video editor does not need the complete relationship history. The reservation provider does not acquire the memory archive. Each module receives a purpose-limited view and loses its temporary lease when the Arena dissolves.

### Family and personal Arenas

The same substrate can support family reunion planning, caregiving, household coordination, emergency preparedness, shared histories, education, travel, creative projects, and private celebrations.

A family governance layer may persist while temporary sub-Arenas form for particular objectives. Children, Elders, caregivers, guests, and administrators receive different permissions rather than unrestricted access to a single family graph.

### Interfaces as replaceable projections

An Arena may render as an accessible 2D screen, a voice workflow, a 3D constellation, an AR environment, a shared wall display, or a task-specific control panel. The interface adapts to the objective, user, device, accessibility needs, attention, privacy, and surroundings.

Rendering remains a view over truth. Every spatial object must resolve to exact source data, provenance, permissions, and available actions.

The strongest expression is a **personal reality compiler**:

```text
intent
+ governed personal context
+ authorized world data
+ modular capabilities
+ chosen aesthetic and accessibility profile
  -> temporary digital environment for the present moment
```

### Creator and module economy

Developers, artists, communities, institutions, and service providers can publish narrow interoperable capabilities and Arena templates rather than rebuilding identity, messaging, media, payments, recommendations, and governance inside every app.

Potential templates include a Perfect Date Arena, Family Reunion Arena, Personal Learning Arena, Travel Arena, Community Event Arena, Emergency Preparedness Arena, Creative Production Arena, or Small Business Launch Arena.

Users should be able to fork a template, replace modules, change governance, and preserve an editable version without surrendering their data to the template publisher.

### Fractal composition

The same pattern applies at every scale:

```text
module
  -> temporary organ
  -> personal Arena
  -> family or team Arena
  -> community or institutional Arena
  -> temporary Arena of Arenas
```

A camera module inside a Date Arena and a Health Capacity Arena inside a national emergency federation use the same principles: explicit boundaries, exact sidecars, minimum leases, replaceable interfaces, purpose-limited federation, verification, approval, revocation, and dissolution.

### What must be solved

This future requires more than adding plugins to an LLM. It depends on:

- signed module manifests and supply-chain security;
- stable schemas, identity references, units, and version negotiation;
- usable consent and permission design;
- coherent generated interfaces and accessibility guarantees;
- source licences, API terms, and derivative-data controls;
- resistance to manipulative personalization and hidden advertising;
- participant rights in dating, family, health, memory, and social Arenas;
- graceful failure, module replacement, and rollback;
- economic incentives for interoperability rather than data capture.

The detailed architecture, module contract, examples, roadmap, risks, and first demonstration are documented in `docs/AURA_INTENT_COMPILED_APPLICATION_FABRIC.md`.
'''
if "## Intent-Compiled Application Fabric" not in text:
    if SECTION_MARKER not in text:
        raise SystemExit("README federated vision marker not found")
    text = text.replace(SECTION_MARKER, "\n" + SECTION + SECTION_MARKER, 1)

DOC_ROW_MARKER = "| `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md` | Arena federation, disaster relief, public-sector, social-intent, and market vision | Canonical architecture-supported direction |\n"
DOC_ROW = "| `docs/AURA_INTENT_COMPILED_APPLICATION_FABRIC.md` | Modular personal Arenas, governed data views, spatial interfaces, and module economy | Canonical architecture-supported direction |\n"
if DOC_ROW not in text:
    if DOC_ROW_MARKER not in text:
        raise SystemExit("README documentation row marker not found")
    text = text.replace(DOC_ROW_MARKER, DOC_ROW_MARKER + DOC_ROW, 1)

README.write_text(text, encoding="utf-8")
