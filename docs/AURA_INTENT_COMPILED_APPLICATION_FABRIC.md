# Aura Intent-Compiled Application Fabric

## Status

This document defines an architecture-supported product direction for AuraOS. It is not a claim that the complete module marketplace, personal data fabric, spatial interface, or consumer ecosystem described here is already implemented.

Aura already contains many of the necessary primitives:

- structured human intent packets;
- the six-slot software grammar `DIR → ASP → CLASS → SUBJ → VOICE → STEM`;
- deterministic route admission;
- capability discovery and reuse-before-invention;
- bounded Arenas and Boundary Contracts;
- ephemeral organs with manifests, leases, verification, revocation, and dissolution;
- exact source and sidecar truth layers;
- local-first memory and user-controlled context;
- declarative interfaces and spatial visualization foundations;
- Human Agent, Civic, Coding, and domain Arena composition.

The future work is to turn these primitives into a general **intent-compiled application fabric** in which people assemble temporary experiences from governed modules rather than entering monolithic applications that own the interface, workflow, and data.

---

## The shift: from applications to intentions

The dominant software model is application-centric:

```text
person
  -> chooses a website or app
  -> accepts its fixed interface
  -> uploads data into its silo
  -> uses only its built-in capabilities
  -> remains inside its business model and recommendation system
```

The Aura model is intent-centric:

```text
person-owned or authorized data
+ current objective
+ preferences, consent, place, time, and constraints
+ discoverable governed modules
  -> compiled IntentPacket
  -> admitted capability graph
  -> temporary personal Arena
  -> adaptive 2D / 3D / AR / voice interface
  -> verified results and memories
  -> revocation and dissolution
```

The user does not begin by choosing a brand or container. The user begins by expressing an objective.

Aura then determines:

- which capabilities are necessary;
- which modules are compatible;
- which sources may be accessed;
- which provider or local implementation should perform each function;
- which information may leave the device or community boundary;
- which interface is appropriate for the person and context;
- which verifiers and approvals are required;
- what should persist after the Arena dissolves.

This is not merely an AI assistant launching conventional apps. It is a substrate that compiles an application-shaped environment for the objective.

---

## Data no longer belongs conceptually to the application

In the existing platform model, data is usually organized around the service that collected it:

- a music platform owns the listening graph;
- a marketplace owns purchase and seller history;
- a dating platform owns preference and interaction history;
- a social network owns the relationship graph;
- a photo service owns albums and memories;
- a health application owns tracking records;
- a calendar provider owns event context.

In an intent-compiled model, data is organized around the person, community, organization, purpose, and governing policy.

A personal or community data fabric may expose narrow, revocable views such as:

```text
music_preferences_for_this_event
calendar_availability_for_these_people
mobility_requirements_for_this_route
approved_photos_for_this_memory_video
budget_range_for_this_purchase
public_profile_for_this_introduction
health_constraint_for_this_activity
```

The module receives only the view required for the present objective. It does not automatically acquire the underlying vault, lifelong profile, unrelated history, or future reuse rights.

### Intent governs access

Access should be a function of:

```text
who is asking
+ the declared objective
+ the active Arena
+ the requested capability
+ the minimum data fields required
+ consent and legal basis
+ destination and provider
+ time-to-live
+ retention and derivative-use rules
```

This makes user intent a first-class data-governance object rather than merely a search query.

### Sidecar truth remains exact

Semantic representations may help find relevant memories, products, people, songs, places, or modules. They do not replace exact records.

- a music vector points to authorized tracks or playlists;
- a relationship vector points to exact consented contacts and interactions;
- a memory vector points to exact photos, videos, dates, and source files;
- a marketplace vector points to verified listings, inventory, prices, and terms;
- a location vector points to exact geospatial sidecars;
- an interest vector points to source posts, events, or profile claims.

The invariant remains:

> Intent selects. Vectors point. Sidecars prove. Governance authorizes.

---

## Modules replace monolithic apps

The reusable unit is not a full website. It is a bounded capability module that can be discovered and composed inside many Arenas.

Examples include:

- calendar availability;
- music preference and playlist generation;
- astronomical sky positioning;
- weather and route planning;
- restaurant discovery and reservations;
- translation and accessibility;
- camera capture;
- audio recording;
- video editing;
- memory timeline generation;
- budgeting and payment handoff;
- family permissions and shared albums;
- AR lighting, spatial themes, and object placement;
- safety check-ins;
- transportation coordination;
- marketplace search;
- consent capture;
- provenance verification.

A provider may offer one excellent module without controlling the complete user journey.

### Proposed Aura Module Contract

Every distributable module should declare a machine-readable contract:

```text
module_id
publisher_id
version
purpose
supported_intent_slots
input_schema
output_schema
required_capabilities
optional_capabilities
accepted_truth_classes
permitted_data_classes
prohibited_data_classes
network_destinations
retention_policy
training_and_derivative_use_policy
resource_budget
offline_capability
interface_schema
accessibility_contract
verification_contract
failure_and_rollback_behavior
licence
signature_and_digest
revocation_endpoint
```

A module should not be admitted because it is popular or because an LLM recommended it. Admission requires compatibility, integrity, policy, capability, resource, provenance, and verifier checks.

### Module categories

Modules can be separated into categories with different authority:

- **Perception modules** — camera, microphone, sensors, imports;
- **Knowledge modules** — maps, catalogues, public information, personal sidecars;
- **Planning modules** — schedules, routes, budgets, MUSIC comparisons;
- **Creation modules** — writing, image, audio, video, spatial design;
- **Action modules** — reservations, purchases, messages, device control;
- **Governance modules** — consent, identity, policy, legal or cultural constraints;
- **Verification modules** — signatures, tests, receipts, source checks;
- **Interface modules** — 2D, 3D, AR, voice, accessibility, tactile views;
- **Memory modules** — timelines, albums, relationship memories, governed recall.

Action modules require stricter approvals than advisory or visualization modules.

---

## The six-slot grammar as a semantic ABI

The six-slot software grammar can serve as a semantic application binary interface: a common way for independently developed modules to describe where they operate, how they unfold, what kind of capability they provide, who acts, how authority is expressed, and what operation is performed.

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

At the application-fabric level, the slots can be interpreted as:

- **DIR** — target, destination, domain, or spatial direction;
- **ASP** — lifecycle, timing, duration, recurrence, or completion state;
- **CLASS** — capability or object class;
- **SUBJ** — person, group, device, institution, or authorized actor;
- **VOICE** — agency, permission, delegation, proposal, automation, or review mode;
- **STEM** — the core operation or transformation.

Example:

```text
DIR: shared_evening
ASP: one_time_then_memory
CLASS: relationship_experience
SUBJ: consenting_couple
VOICE: human_guided
STEM: plan_capture_edit_replay
```

This packet can be expanded into a capability graph without binding the experience to one company.

The grammar does not guarantee module safety by itself. It provides canonical ordering and routing. Module signatures, capability leases, policy manifests, sandboxes, verifiers, and human approvals remain necessary.

---

## Example: the Perfect Date Arena

A user asks:

> Create a meaningful date for us Friday evening. We like stargazing, live acoustic music, quiet food, and personal memories. Keep the total under $180. Avoid sharing our location publicly. Record only after both of us consent, and create a private short film afterward.

Aura compiles a temporary Arena.

### Possible modules

- shared calendar module;
- weather module;
- astronomy and night-sky module;
- mobility and route module;
- quiet restaurant or picnic module;
- event and music module;
- budget module;
- accessibility module;
- private location policy module;
- mutual media-consent module;
- camera and audio-capture module;
- video-editing module;
- relationship memory-timeline module;
- private playback or AR-memory module.

### Arena phases

```text
FRAME
  -> confirm intent, people, budget, privacy, accessibility, and consent
GROUND
  -> retrieve exact calendars, weather, locations, events, prices, and preferences
PLAN
  -> compare several date scenarios and expose trade-offs
ACT
  -> make only explicitly approved reservations or reminders
EXPERIENCE
  -> provide a calm adaptive interface rather than constant notifications
CAPTURE
  -> request mutual consent before recording
CREATE
  -> assemble a private video from authorized media
REVIEW
  -> let both people approve edits, retention, and sharing
DISSOLVE
  -> revoke temporary providers and retain only approved memories and receipts
```

The music provider need not own the calendar, the video editor need not own the relationship history, and the restaurant service need not acquire the memory archive.

The user owns the Arena-level intent and decides what persists.

---

## Example: a Family Arena

A family Arena can be persistent at the governance layer while creating temporary sub-Arenas for specific objectives:

- plan a reunion;
- coordinate caregiving;
- create a shared family history;
- manage school and activity schedules;
- preserve stories and language;
- prepare for emergencies;
- create private birthday or anniversary experiences;
- organize a household budget;
- manage shared devices and permissions.

Different family members may have different roles and privacy boundaries. A child, Elder, caregiver, guest, and administrator should not receive identical access merely because they belong to the same family graph.

A family memory constellation may provide a spatial interface where people explore relationships, places, stories, photos, recordings, and events. Each visual object must resolve to an exact authorized sidecar, and every person represented requires appropriate consent and governance.

---

## Interfaces become generated projections

A fixed application ships one interface designed for an average user. An Aura Arena can generate a declarative interface appropriate to:

- the objective;
- the person's abilities and preferences;
- the device and available sensors;
- attention and cognitive load;
- language and literacy;
- location and mobility;
- privacy conditions;
- whether the user is alone, with family, at work, or in public;
- whether the environment is connected, offline, spatial, or voice-only.

Possible projections include:

- a conventional accessible 2D screen;
- a simplified voice workflow;
- a 3D constellation;
- an AR environment layered over the physical world;
- a large shared wall or table display;
- a tactile or screen-reader-equivalent representation;
- a temporary control panel assembled for one task.

The interface is a replaceable view, not the source of truth. A 3D or AR object must resolve to exact data, permissions, provenance, and available actions.

### Personal reality compiler

The strongest expression of this concept is a **personal reality compiler**:

```text
intent
+ governed personal context
+ authorized world data
+ modular capabilities
+ chosen aesthetic and accessibility profile
  -> a temporary digital environment shaped for the present moment
```

This does not mean synthetic reality should manipulate or isolate the user. Recommendations, persuasive elements, advertisements, generated media, and inferred emotions must be visible and governable. The person must be able to inspect why an object or option appears and remove the module responsible.

---

## Module marketplace and creator economy

A future Aura ecosystem can support a marketplace where developers, artists, communities, institutions, and service providers publish narrow modules rather than attempting to build the next totalizing platform.

A creator might publish:

- an excellent stargazing experience module;
- a Treaty-specific cultural protocol module governed by the relevant community;
- a couples' memory-film template;
- a wheelchair-accessible route verifier;
- a local business discovery module;
- a disaster shelter-capacity module;
- a language-learning organ;
- a family oral-history interface;
- a budget scenario module;
- an AR museum or land-based education experience.

The module marketplace should expose:

- exact permissions;
- data destinations;
- retention and training policy;
- cost and resource use;
- offline behavior;
- accessibility support;
- verification status;
- publisher identity and signatures;
- compatible intent slots and Arenas;
- user and community governance restrictions;
- replacement options.

Users should be able to swap one module without rebuilding or abandoning the entire Arena.

### Economic shift

The economic unit changes from control of a silo to contribution of a capability.

Providers can compete on:

- quality;
- privacy;
- cost;
- local operation;
- cultural fit;
- accessibility;
- verification;
- sustainability;
- interoperability;
- beauty and experience design.

This reduces the incentive for every service to capture the full identity graph, attention stream, and lifetime data history of its users.

---

## Arena templates and user-created applications

Not every person should have to design a capability graph manually.

Aura can support reusable templates:

- Perfect Date Arena;
- Family Reunion Arena;
- New Parent Arena;
- Community Event Arena;
- Personal Learning Arena;
- Travel Arena;
- Home Renovation Arena;
- Small Business Launch Arena;
- Ceremony or Cultural Event Arena with proper governance;
- Emergency Preparedness Arena;
- Health Appointment Preparation Arena;
- Creative Production Arena.

A template is not a monolithic app. It is a governed intent pattern, module-selection policy, interface schema, and verifier plan.

People can fork a template, replace modules, change governance, and publish a new version without taking ownership of other users' data.

### Natural-language creation

A person may create an Arena by describing it:

> Build a private family reunion planner that works offline, includes Elder accessibility, collects dietary needs with consent, coordinates rides, creates a shared photo space, and dissolves location access after the event.

Aura can:

1. compile the intent into the six-slot route;
2. find compatible existing modules;
3. identify missing capabilities;
4. present permissions and trade-offs;
5. generate a declarative interface;
6. run the Arena in a sandbox;
7. verify behavior;
8. require human approval before external effects;
9. preserve an editable template after dissolution.

This is end-user software creation without assuming that generated code is automatically safe or authoritative.

---

## Relationship to the Arena of Arenas

Personal modular Arenas and institutional federation are the same pattern at different scales.

```text
module
  -> task organ
  -> personal Arena
  -> family or team Arena
  -> community or institutional Arena
  -> temporary Arena of Arenas
```

At every scale:

- boundaries remain explicit;
- exact truth remains outside the vector representation;
- capabilities are leased rather than ambient;
- participants retain authority;
- interfaces are projections;
- federation is purpose-limited;
- the assembled system may dissolve when the objective ends.

This is the fractal property of Aura: the same grammar and governance principles can coordinate a camera module inside a date Arena or a health-capacity Arena inside a national emergency response.

---

## Why this could change software

If implemented successfully, the model changes several foundational assumptions.

### From destination to composition

Users stop asking, “Which app do I open?” and start asking, “What am I trying to accomplish?”

### From data silos to governed views

Services receive minimum purpose-specific access rather than inheriting the user's complete history.

### From one interface to adaptive projections

The same objective can appear as text, voice, 3D, AR, a shared display, or an accessible simplified workflow.

### From platform lock-in to module substitution

A module can be replaced without abandoning the entire personal environment.

### From software development to capability publishing

Creators can build small interoperable capabilities instead of reproducing identity, payments, media, messaging, and recommendation systems in every product.

### From permanent applications to ephemeral systems

The software exists for as long as the objective requires, then revokes temporary access and dissolves.

### From opaque personalization to inspectable intent

Users can see which intent, source, preference, module, and policy caused an option to appear.

---

## Hard problems and failure modes

This future is not achieved merely by adding plugins to an LLM.

### Module supply-chain security

Modules require signatures, reproducible manifests, sandboxing, permission review, dependency constraints, vulnerability handling, and revocation.

### Semantic compatibility

The six-slot grammar provides routing structure, but modules still need stable schemas, ontologies, units, identity references, error semantics, and version negotiation.

### Consent fatigue

Permission systems can become unusable. Aura must group decisions around meaningful objectives without hiding important consequences.

### Interface coherence

A dynamically assembled environment can become inconsistent or overwhelming. Declarative design systems, accessibility contracts, predictable interaction rules, and human-editable templates are essential.

### Business resistance

Incumbent platforms benefit from data lock-in, engagement control, and closed ecosystems. Interoperability requires technical, legal, economic, and governance incentives.

### Source rights and platform terms

An intent fabric cannot assume unrestricted access to commercial services, copyrighted media, private social networks, or proprietary APIs.

### Derived data

Even when raw records remain private, embeddings, summaries, edits, recommendations, and memories may reveal sensitive information. Derivative-use policy must be explicit.

### Identity and relationship harm

Dating, family, health, social, and memory Arenas can expose intimate information. Mutual consent, deletion, correction, non-retaliation, and separate participant rights are mandatory.

### Persuasion and reality shaping

A personalized AR environment could become more manipulative than an engagement feed. Advertising, generated content, ranking objectives, and emotional inference must be visible, bounded, and removable.

### Reliability

When modules fail, the Arena must identify the failing capability, preserve valid state, offer replacements, and avoid cascading corruption.

---

## Proposed implementation roadmap

### Phase 1 — Module manifest and registry

- formalize `AuraModuleManifest`;
- define capability, data, interface, verifier, licence, and retention fields;
- sign and digest modules;
- extend the Capability Genome Resolver to discover compatible modules;
- implement deny-by-default admission.

### Phase 2 — Declarative module composition

- compile an intent packet into a typed capability graph;
- validate slot and schema compatibility;
- resolve dependencies and conflicts;
- produce a human-readable permission plan;
- generate a basic 2D interface.

### Phase 3 — Personal data views

- implement local governed data vault adapters;
- create purpose-limited sidecar views;
- add TTL, revocation, retention, and derivative-use receipts;
- support provider-local and offline module alternatives.

### Phase 4 — Template builder

- let users create, fork, and edit Arena templates;
- support natural-language intent plus visual permission editing;
- verify templates using synthetic fixtures;
- export portable signed template bundles.

### Phase 5 — Spatial and AR projection

- map declarative interface objects into 3D or AR;
- preserve exact-source drill-down;
- maintain equivalent accessible 2D, list, table, and voice views;
- allow users to replace the renderer.

### Phase 6 — Module marketplace

- publisher identity and signing;
- compatibility and safety metadata;
- transparent cost and data-use policies;
- community-controlled registries;
- module replacement and revocation;
- provenance-preserving payments and licensing.

### Phase 7 — Federated personal and institutional Arenas

- compose personal, family, community, enterprise, and government Arenas through the same typed federation capsules;
- prove that revoking one participant or module does not collapse unrelated Arenas;
- support local-first and intermittent-network federation.

---

## First demonstration

A credible first demonstration should use synthetic data and local modules:

### Perfect Date Arena demo

1. enter a natural-language objective;
2. show the six-slot packet;
3. show discovered modules and rejected incompatible modules;
4. show exact permissions requested by calendar, music, location, camera, and editing modules;
5. compare three plans with MUSIC;
6. approve one external action while denying another;
7. generate a customizable 2D or 3D interface;
8. simulate mutual recording consent;
9. assemble a short synthetic memory video;
10. revoke temporary location and media capabilities;
11. retain only the approved plan, memories, and receipts;
12. replace one module and rerun the Arena without migrating the entire experience.

This would demonstrate the deeper platform thesis more effectively than a conventional app mock-up.

---

## Non-negotiable rules

1. User intent limits access; it does not erase consent, law, or another participant's rights.
2. Modules receive minimum purpose-specific data views.
3. Vectors and generated interfaces are not authoritative records.
4. Exact sources remain inspectable through sidecars.
5. External effects require declared action modules and approval.
6. Modules are signed, sandboxed, revocable, and replaceable.
7. A provider cannot silently expand the objective or retention period.
8. Participants can inspect, correct, export, and delete governed personal records where legally and technically applicable.
9. AR and personalization logic must disclose ranking, advertising, generated content, and persuasive objectives.
10. A dissolved Arena must revoke temporary capability leases and record what remains.

## Related documentation

- `README.md`
- `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md`
- `docs/AURA_EPHEMERAL_ORGAN_RUNTIME.md`
- `docs/AURA_EPHEMERAL_SECURITY_MODEL.md`
- `docs/AURA_FST_PROVENANCE_AND_SECURITY.md`
- `docs/AURA_HUMAN_AGENT_ARENA.md`
- `docs/AURA_CIVIC_COMMONS_ARENA.md`
- `AMD_HACKATHON_SUBMISSION.md`
