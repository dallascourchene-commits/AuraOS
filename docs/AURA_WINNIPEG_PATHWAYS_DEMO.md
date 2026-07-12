# Aura Winnipeg Community Pathways Lab

## Purpose

This is a guided, synthetic demonstration of Aura's Civic Commons Arena and Human Agent Coding Arena working as one governed system.

The project does **not** claim to solve homelessness, addiction, or service coordination in Winnipeg. It demonstrates how Aura can help people:

- frame a complex community objective;
- explore privacy-filtered infrastructure and aggregate access signals;
- preserve needs, assets, objections, and representation gaps;
- decompose work while retaining mandatory constraints;
- compare scenarios without declaring a hidden winner;
- design a reversible, non-binding pilot;
- discover a product issue and hand it into a human-guided coding workflow;
- stage and review technical work without automatic commit, push, or merge.

Every civic record in the project is labelled `SYNTHETIC_DEMO_DATA`.

## Launch

```bash
python aura_showcase_server.py --demo-project winnipeg_pathways
```

Open:

```text
http://127.0.0.1:8091
```

The server auto-starts the Winnipeg project. To start with an empty session:

```bash
python aura_showcase_server.py --demo-project winnipeg_pathways --no-auto-start
```

Container launch:

```bash
docker compose -f docker-compose.showcase.yml up --build
```

## Guided Civic journey

The project advances through:

```text
WELCOME
→ FRAME_OBJECTIVE
→ SELECT_CONTEXT
→ EXPLORE_MAP
→ ADD_COMMUNITY_INPUT
→ DECOMPOSE_WORK
→ COMPARE_SCENARIOS
→ REVIEW_CONSENT
→ RUN_WHAT_IF
→ DESIGN_PILOT
→ REVIEW_PACKET
→ COMPLETE
```

Each step invokes only the Civic organs declared for that step. Organ output is projected only after verification and every organ emits a dissolution receipt.

## Map governance

The map is a server-filtered projection over governed Civic data. It filters by:

- jurisdiction;
- zoom;
- viewport;
- privacy class;
- location precision.

Allowed aggregate signals include service-access distance, transit access, facility coverage, program capacity, accessibility barriers, and community-stated priority density.

The demo rejects person-level heatmaps for homelessness, addiction, crime, health diagnoses, child welfare, Indigenous identity, poverty, or immigration status.

## Scenario comparison

The fixture compares four synthetic approaches:

1. Distributed Neighbourhood Hubs
2. Mobile Outreach and Housing Navigation
3. Central Healing, Training, and Employment Centre
4. Coordinated Existing-Service Network

MUSIC exposes trade-offs, weights, sensitivity, and Pareto information. Aura does not declare a secret or automatic winner.

## Human Agent handoff

The sample product issue is intentionally understandable:

```text
The showcase opens at zoom 11.
Candidate map features require zoom 12.
Therefore the proposed pilot staging site is initially hidden.
```

The Civic interface can hand this into the Human Agent Coding Arena. The handoff contains:

- exact repository files;
- source hashes;
- marker line ranges;
- focused tests;
- three candidate solutions;
- a review-only candidate diff;
- explicit no-commit, no-push, and no-merge boundaries.

The recommended option is to preserve the general map policy and focus the guided candidate step at zoom 12, rather than weakening candidate visibility globally.

## Human Agent sequence

After selecting **Investigate with Human Agent Arena**:

1. The objective is admitted through the guarded Human Agent WFST.
2. Exact repository facts are imported as grounded evidence.
3. Select **Prepare Arena capsule**.
4. Optionally stage the candidate patch; production remains unchanged.
5. Run focused tests when available.
6. Inspect verifier and hotswap gates.
7. Record human review with approval set to false for the demo.
8. Export the review packet if desired.

The demo is successful even when a later gate remains blocked. A visible denial with remediation is evidence that Aura is preserving authority rather than forcing completion.

## Three-minute script

### 0:00–0:30 — State the thesis

> Aura is not an AI that decides for a community. It creates bounded spaces where people can inspect evidence, preserve disagreement, compare options, and design reversible action.

### 0:30–1:30 — Advance the Civic project

Advance through the objective, context, and map steps. Show:

- synthetic data labels;
- safe aggregate map layers;
- suppressed-feature counts;
- the candidate site hidden at zoom 11 and visible at zoom 12;
- needs, assets, and mandatory constraints.

### 1:30–2:10 — Compare and deliberate

Move through work decomposition and scenario comparison. Point out:

- no hidden winner;
- representation gaps;
- reservations and critical objections;
- simulation-only What-If results;
- the non-binding 90-day pilot.

### 2:10–3:00 — Improve Aura through the Human Agent Arena

Open the sample map issue. Show:

```text
Civic observation
→ exact repository grounding
→ guarded Human Agent workflow
→ bounded Arena capsule
→ staged proposal
→ evidence and human review
```

Conclude:

> The same architecture that prevents Aura from inventing civic authority also prevents an AI coding worker from granting itself software authority.

## From one Civic Arena to a federated response system

The Winnipeg demonstration is also the smallest visible unit of a larger Arena-of-Arenas architecture.

A future synthetic emergency scenario could compose:

```text
Winnipeg Civic Arena
+ Community or First Nation Emergency Arena
+ Shelter Arena
+ Health Capacity Arena
+ Transportation and Logistics Arena
+ Infrastructure Arena
+ Humanitarian Organization Arena
→ Temporary Federated Response Arena
```

Each participant would retain its own data custody, legal or community authority, identity rules, exact source sidecars, and revocation rights. The federated response would receive only the minimum authorized resource, need, location, freshness, and provenance capsules required for the incident.

The same governed map principles demonstrated here would apply during disaster relief:

- public views show aggregate shelter capacity, routes, infrastructure, service coverage, and verified notices;
- frontline views are role- and purpose-scoped;
- personal displacement, medical, child, identity, or vulnerability records remain restricted;
- local operation continues through deterministic workflows when cloud access or an LLM is unavailable;
- compact signed updates synchronize when connectivity returns;
- unresolved conflicts, duplicate requests, stale reports, and uncertainty remain visible.

This is a market direction and demonstration roadmap, not a claim that the current Winnipeg fixture is a certified emergency-management deployment.

Detailed architecture: `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md`.

AMD recording guide: `docs/AMD_DEMO_RECORDING_SCRIPT.md`.

## Authority invariants

- `patch_authority: exact_source_spans_and_hashes_only`
- `vsa_patch_authority: false`
- no identity-based context activation
- no person-level vulnerability mapping
- no legal approval
- no automatic funding allocation
- no binding vote
- no government submission
- no automatic commit
- no automatic push
- no automatic merge
