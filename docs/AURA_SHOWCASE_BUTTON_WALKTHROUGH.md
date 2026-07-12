# Aura Winnipeg Showcase — Button-by-Button Recording Walkthrough

## What the demo now proves

The Winnipeg showcase is an interactive guided product demo rather than a static report.

At every Civic stage, Aura displays:

- the current human question;
- evidence already available;
- a ranked menu of applicable actions;
- a deterministic route weight for each action;
- the six-slot intent signature for every button;
- the ephemeral organs activated by the next stage;
- actions that remain prohibited;
- a Winnipeg street basemap with synthetic governed Civic records;
- an exact handoff into a semi-guided Human Agent Coding Arena.

At every Human Agent stage, Aura displays:

- the current phase: `FRAME → GROUND → PLAN → ACT → PROVE → DECIDE`;
- WFST-recommended buttons;
- the exact lexicographic rank vector for each admitted transition;
- required and produced evidence;
- requested tool capabilities;
- blocked transitions and their failed hard guards;
- the complete evidence-gate timeline.

Civic route percentages are deterministic presentation weights for the fixture demo. Human Agent routes use Aura's real WFST rank vectors. Neither is model confidence or authority.

---

## Launch

```bash
git switch main
git pull --ff-only origin main

docker compose -f docker-compose.showcase.yml down --remove-orphans
docker compose -f docker-compose.showcase.yml up -d --build
```

Open:

```text
http://127.0.0.1:8091
```

The recognizable Winnipeg streets come from OpenStreetMap during normal interactive viewing. Aura requests only the tiles visible in the current viewport and displays attribution. The Civic project records remain synthetic. If map tiles cannot load, the governed dark-grid fallback remains usable.

Do not describe the basemap as offline. The Civic workflow and synthetic overlay are local-first; a production offline disaster deployment would use a licensed offline provider or self-hosted vector tiles.

---

# Recording controls

## Top buttons

- **Restart demo** — creates a fresh synthetic session and returns the map to zoom 11.
- **Back** — returns to the prior guide stage without deleting underlying evidence.
- **Run next governed stage** — executes only the transition and organs admitted for the next stage.

## Map buttons

- **− / +** — changes governed projection zoom.
- **West Broadway test community** — focuses a synthetic test-community polygon over recognizable Winnipeg streets at zoom 14.
- **Reveal candidate** — shows the proposed staging site at zoom 12, the policy minimum for candidate features.

## Civic ranked-action cards

Each Civic action shows:

```text
rank
button label
why the action is available
DIR → ASP → CLASS → SUBJ → VOICE → STEM
route weight
organs or client interaction activated
```

## Human Agent recommended-action cards

Each Human Agent card shows:

```text
WFST rank
transition label
phase transition
risk
required evidence
produced evidence
requested capability
exact lexicographic rank vector
```

Hard guards eliminate inadmissible transitions before ranking.

---

# Exact Civic walkthrough

## Step 1 — Welcome

Confirm the screen shows:

- `Step 1 of 12`;
- **Welcome to the Pathways Lab**;
- Winnipeg streets under a locked Civic overlay;
- the ranked Civic action menu;
- permanently prohibited actions.

Say:

> Aura does not begin by giving an AI unlimited tools. It begins with a bounded objective and projects only the actions admitted at the current gate.

Point to the first route card. Show the six-slot signature and route weight.

Click:

**Begin the guided project**

## Step 2 — Frame the objective

Say:

> The objective and mandatory constraints are preserved before decomposition. This is synthetic planning, not a binding Winnipeg decision.

Click:

**Lock the objective and constraints**

## Step 3 — Select jurisdiction and context

Point out that Winnipeg jurisdiction is active and Indigenous or cultural context is not inferred from identity.

Click the ranked map option:

**Focus the West Broadway synthetic test community**

Say:

> The street context is public OpenStreetMap data. The planning records layered above it are synthetic and governed separately.

Then click:

**Activate the Winnipeg profile**

## Step 4 — Explore the governed map

The synthetic Civic overlay is now admitted.

Show:

- West Broadway Synthetic Test Community boundary;
- Community Partner Site;
- Transit Connection;
- Housing Navigation Access Point;
- visible and policy-filtered feature counts.

Click a visible point and show:

- truth class;
- privacy class;
- jurisdiction;
- location precision;
- source reference.

At zoom 11, point out that the candidate is suppressed.

Click:

**Reveal the proposed staging site at governed zoom**

The candidate appears at zoom 12 without changing the general map policy.

Then click:

**Record a service-access concern**

Aura prefills a reservation. Click **Record**.

Say:

> The map leads to a preserved human concern rather than an automated conclusion.

Click:

**Load needs and community assets**

## Step 5 — Needs, assets, and concerns

Show the counts and lists.

Click:

**Preserve a reservation or missing voice**

Record the prefilled statement that people with lived experience must review the project.

Click:

**Decompose into bounded workstreams**

## Step 6 — MITOSIS workstreams

Show the bounded workstreams and the organ activated by this transition.

Say:

> MITOSIS breaks the objective into manageable work without dropping the original constraints.

Click:

**Compare four possible approaches**

## Step 7 — MUSIC scenarios

Show:

1. Distributed Neighbourhood Hubs
2. Mobile Outreach and Housing Navigation
3. Central Healing, Training, and Employment Centre
4. Coordinated Existing-Service Network

Say:

> MUSIC exposes weights, sensitivity, trade-offs, and Pareto information. Aura does not manufacture a hidden winner.

Click:

**Review consent, objections, and gaps**

## Step 8 — Consent and representation

Show:

- the transportation objection;
- lived-experience representation gap;
- youth representation gap;
- Elder and cultural-governance invitation requirement;
- recorded reservations.

Click:

**Run a non-predictive What-If**

## Step 9 — What-If

Say:

> What-If results are simulations of changed assumptions, not forecasts or guarantees.

Click:

**Design the reversible 90-day pilot**

## Step 10 — Pilot

Show:

- duration;
- review days;
- components;
- unresolved owners;
- funding not allocated;
- no binding authority.

Click:

**Assemble the non-binding decision packet**

## Step 11 — Decision packet

Point to the decision-packet-ready indicator.

Say:

> Aura has organized evidence and disagreement into a reviewable packet. It has not voted, spent money, approved law, or submitted anything to government.

Click:

**Complete with human authority intact**

## Step 12 — Complete

Pause on the final human-authority question.

Then use the Civic route card or issue panel:

**Investigate the map behavior in the Human Agent Arena**

---

# Exact Human Agent walkthrough

The Human Agent tab opens with the Civic issue already grounded.

## PLAN — Prepare Arena capsule

At the top, show:

- grammar `human-agent-wfst-v1`;
- current state hash;
- the highest-ranked recommended transition;
- its required and produced evidence;
- its exact rank vector;
- blocked transitions below.

Say:

> The Human Agent interface is semi-guided by the actual guarded WFST. Hard guards remove unsupported actions before the remaining transitions are ranked.

Click the first recommended card:

**Prepare Arena capsule**

## ACT — Stage candidate patch

After the workflow refreshes, the new recommended card should be:

**Stage candidate patch**

Show that it requires:

- plan hash;
- exact candidate diff;
- exact affected files.

Click it.

Say:

> The candidate is staged in a detached workspace. Production is not mutated.

## PROVE — Run tests

Click:

**Run ephemeral test lab**

Wait for the result.

Show:

- ALLOWED or DENIED result;
- exact test target;
- measured evidence;
- remediation if the action is denied.

If tests pass, click:

**Verify evidence**

Say:

> Verification is an independent gate. Model confidence cannot replace measured test evidence.

## DECIDE — Hotswap and human review

Click:

**Check hotswap gate**

Then click:

**Human review**

For the demo, Aura records approval as false.

Say:

> Human review is recorded, but this showcase never commits, pushes, opens a pull request, or merges.

Optionally click:

**Export review packet**

## Show blocked alternatives

Open:

**Inspect available alternatives and blocked transitions**

Point to one blocked action and its:

- failed guard;
- missing evidence;
- fail-closed status.

Conclude:

> The same interaction pattern governs civic planning and software change: only applicable actions appear, every gate is explainable, and authority remains outside the model.

---

# Presenter fallback paths

## Basemap does not load

Continue recording with the dark governed grid. Say:

> The public street basemap is optional. The local Civic workflow and policy-filtered synthetic overlay continue without it.

Do not repeatedly refresh or pan in an attempt to bulk-load OpenStreetMap tiles.

## A Human Agent action is denied

Do not hide the denial.

Show the failed guard and remediation, then say:

> A visible denial is evidence that Aura refuses to improvise authority or pretend missing evidence exists.

## Tests take too long

Show the exact test target and use **Export review packet**. The handoff itself still proves exact grounding and bounded authority.

## Candidate does not appear

Confirm zoom is 12 or higher and click **Reveal candidate**. The candidate is intentionally hidden below its policy threshold.

---

# Claims to use

- The Civic workflow and fixture are local-first and synthetic.
- The optional OpenStreetMap basemap provides recognizable public street context during normal interactive viewing.
- Every Civic stage offers a deterministic inspectable action menu.
- Human Agent actions are projected from the real guarded WFST.
- Hard guards run before weighted ranking.
- Vectors and rankings guide; exact evidence and human decisions authorize.

# Claims to avoid

- Do not call the route weight an AI confidence score.
- Do not say OpenStreetMap tiles are packaged for offline use.
- Do not describe West Broadway fixture records as real community data.
- Do not say the Human Agent Arena automatically commits or merges.
- Do not claim the synthetic pilot has community or government approval.
