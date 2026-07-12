# AMD Developer Hackathon ACT II — Track 3 Submission Guide

## Project

**AuraOS: Sovereign Human-AI Arenas**

AuraOS is a local-first cognitive operating substrate that turns human or community objectives into bounded Arenas. Language models are replaceable workers; exact evidence, verifier gates, and human or community governance retain authority.

## Track 3 fit

AuraOS is submitted to the **Unicorn / Open Innovation Track** as a product-oriented AI platform rather than a benchmark entry.

The judge-facing story is:

```text
human or community objective
  -> structured intent and guarded routing
  -> bounded Arena and temporary capabilities
  -> replaceable AI worker
  -> exact verification
  -> preserved human/community authority
```

The two implemented showcase surfaces are:

1. **Winnipeg Community Pathways Lab** — governed Civic planning with synthetic data, privacy-filtered maps, scenario trade-offs, preserved objections, a reversible pilot, and a handoff into the Human Agent Coding Arena.
2. **Sovereign Learning Arena** — a bounded coding task, detached verification, verified crystal creation, and reuse of a previously verified procedure.

## Platform vision and market potential

AuraOS is designed as a reusable substrate rather than one narrow application. Separate domain Arenas can retain their own data, policies, capabilities, and authority, then temporarily compose around a shared objective.

```text
Domain Arena A ─┐
Domain Arena B ─┼─> Temporary Federated Objective Arena
Domain Arena C ─┤      -> minimum authorized representations
Domain Arena D ─┘      -> verified cross-domain coordination
```

Major product directions include:

- **Offline Disaster Coordination Arena** — local-first coordination of shelters, health, transportation, supplies, volunteers, infrastructure, NGOs, governments, and community emergency teams during disrupted connectivity.
- **Government and Institutional Federation** — purpose-limited coordination among social policy, budgets, healthcare, housing, infrastructure, environment, emergency management, education, and Indigenous or treaty-obligation Arenas.
- **Intent-Indexed Social and Public Information Network** — licensed public and consented sources clustered by VSA intent representations, with every topic, claim, post, article, or event resolving to exact governed sidecars.
- **Regulated Enterprise Arenas** — sovereign coordination for healthcare networks, utilities, logistics, supply chains, finance, education, and auditable AI development.

The detailed architecture, competitive landscape, market directions, and non-negotiable safety boundaries are documented in `docs/AURA_FEDERATED_ARENAS_MARKET_VISION.md`.

These are architecture-supported product directions, not claims that national government, disaster-relief, or cross-platform social deployments are already certified production systems.

## AMD resources

The AMD path is implemented and documented in `docs/AMD_TRACK3_CRUCIBLE_DEMO.md`:

```text
AMD ROCm notebook or AMD-hosted Fireworks inference
  -> Gemma through an OpenAI-compatible endpoint
  -> bounded Aura worker
  -> detached verification
  -> verified crystals
  -> optional PEFT/LoRA Gemma adapter training
```

Primary implementation files:

- `aura_amd_track3_worker.py`
- `aura_amd_track3_cli.py`
- `aura_amd_track3_train.py`
- `requirements-amd-track3.txt`
- `Dockerfile.amd-track3`
- `docker-compose.track3.yml`
- `docs/AMD_TRACK3_CRUCIBLE_DEMO.md`

Local Ollama is an optional inspection worker and is **not** represented as AMD compute. AMD usage is represented by the ROCm/Gemma and AMD-hosted Fireworks paths above.

## Containerized judge demos

### Unified Winnipeg Civic + Human Agent showcase

```bash
docker compose -f docker-compose.showcase.yml up --build
```

Open `http://127.0.0.1:8091`.

Detailed guide: `docs/AURA_WINNIPEG_PATHWAYS_DEMO.md`.

### Track 3 Sovereign Learning Arena

```bash
docker compose -f docker-compose.track3.yml up --build
```

Open `http://127.0.0.1:8080`.

The default mode uses deterministic fixtures so it can be inspected without an API key or model download. Optional local Ollama and AMD/Gemma configurations are documented in `docs/AMD_TRACK3_CRUCIBLE_DEMO.md`.

## What judges should inspect

- `SYNTHETIC_DEMO_DATA` labels and person-level map restrictions;
- visible scenario trade-offs with no hidden civic winner;
- the Civic-to-Human-Agent handoff with exact files, hashes, tests, and review-only diff;
- the six-slot intent packet and hard-guarded WFST route;
- exact allowed files and verifier commands;
- detached workspace verification;
- verified crystal creation and reuse;
- `source_checkout_mutated=false` and dissolution receipts;
- the documented AMD ROCm / AMD-hosted Fireworks / Gemma path;
- the federation principle: vectors and compact capsules route, exact sidecars prove, and people or lawful institutions authorize.

## Market narrative for the video and deck

The recommended final message is:

> Aura is not one AI application. It is a sovereign operating substrate for many bounded Arenas. A Civic Arena can coordinate a community, a Coding Arena can improve the software, and future Disaster, Health, Infrastructure, Government, and Social Information Arenas can remain isolated until a shared objective requires a temporary, governed federation.

The strongest disaster-relief example is a frontline worker operating during a communications outage. The worker can see verified aggregate shelter capacity, roads, supplies, transport, assignments, and unresolved needs, while restricted personal records remain role-scoped. Local devices continue through deterministic workflows and synchronize compact signed updates when connectivity returns.

The strongest social-network example is intent-first exploration rather than an engagement feed. VSA clusters public or consented discussions and events, but the exact post, source, permissions, timestamp, and deletion state remain in sidecars or source systems.

## Authority and truth boundaries

- No automatic civic decision, funding allocation, vote, or government submission.
- No person-level homelessness, addiction, crime, health, poverty, identity, displacement, or political-profile heatmaps.
- No automatic production patch, commit, push, pull request, review request, or merge.
- No autonomous government, military targeting, weapon, lethal decision, or mass-surveillance authority.
- Defence-related market direction is limited to governed logistics, readiness, humanitarian support, infrastructure, supply, and civil-emergency coordination.
- Local Ollama execution is not described as AMD execution.
- Fixture data is not described as live Winnipeg or disaster data.
- Linguistic and cultural governance remains with speakers, teachers, and communities.
- VSA and other symbolic representations remain indexes and routing layers; exact records remain in files, databases, snapshots, or sidecars.

## Validation

The dedicated showcase workflows validate Python 3.10 and 3.12 compilation, fatal lint, focused Civic and Human Agent contracts, live HTTP startup, and container default commands. The AMD Track 3 workflow validates the deterministic two-task crystal-reuse sequence and container path.

## Submission assets

The LabLab submission should include:

- public GitHub repository URL;
- demo video;
- slide deck PDF;
- cover image;
- hosted demo URL when available;
- technology/category tags;
- an explicit statement of the AMD resource actually used during development or demonstration;
- a market slide that distinguishes implemented demonstrations from future federated Arena products.

Recording guide: `docs/AMD_DEMO_RECORDING_SCRIPT.md`.

## License

AuraOS is currently published under **AGPL-3.0** as declared in `README.md`. Do not represent the repository as MIT-licensed unless the copyright holder intentionally changes or dual-licenses the relevant work.
