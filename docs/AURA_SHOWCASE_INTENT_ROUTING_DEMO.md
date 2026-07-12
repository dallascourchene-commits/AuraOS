# Aura Showcase — Guided Bulk-Intent Routing Demo

## Purpose

The Sovereign Learning Arena demonstrates a distinctive Aura capability:

```text
ordinary bulk human intention
  → deterministic local lexical addressing
  → lightweight local tag extraction
  → canonical six-slot intent packet
  → machine FST hard-gate routing
  → CODEMAP localization
  → bounded context for a replaceable worker
```

No LLM is called during these stages.

The demo is intentionally guided rather than an unconstrained prompt surface. Each
screen reveals one observable transformation and keeps the authority boundary visible.

## Launch

Use the unified showcase:

```bash
python aura_showcase_server.py --host 127.0.0.1 --port 8091
```

Open:

```text
http://127.0.0.1:8091
```

Select **Sovereign Learning Arena**.

## Presenter path

### 1. Give Aura bulk intention

Paste or retain the supplied natural-language objective and click:

**Compile intention without an LLM**

The user does not need to write slot names, JSON, a special prompt, or a command DSL.
The server treats the text as an unstructured `AURA_INTENT` objective and passes it to
Aura's existing intent-ingestion subsystem.

The endpoint is:

```text
POST /api/showcase/intent/compile
```

The maximum accepted input is 12,000 characters. Common secret-like values are redacted
before display or handoff construction.

### 2. Show lexical addressing

The next screen displays how words map into `english_lexicon.json`.

The repository compiler locks this file to:

```text
4096 primitives
12-bit addresses
```

Known words use their stored 12-bit index. Unknown words use the existing deterministic
checksum fallback used by `AthabaskanPositionalParser`.

Important claim boundary:

> The codebook supplies stable lexical addresses. It does not, by itself, understand the
> whole intention or grant execution authority.

The demo separately shows the classification and routing layers that consume those
stable lexical features.

### 3. Show local routing tags

Aura's existing lightweight extractor recognizes patterns for:

- operation;
- domain;
- target;
- expected output.

For example, ordinary phrases such as `improve`, `Learning Arena`, `intent`, `routing`,
and `tests` can produce a compact packet such as:

```text
[OP:IMPROVE]
[DOMAIN:CODING_ARENA]
[TARGET:INTENT_INGESTION]
[ENV:PYTHON]
[CONSTRAINT:TOKEN_SPARING]
[OUTPUT:TEST_RESULT]
```

The panel shows the exact matched text that produced every tag.

The expandable LEXC section reads the real `aura.lexc` file and shows:

- lexicon layers;
- transition arcs;
- symbols grouped under `DIR`, `ASP`, `CLASS`, `SUBJ`, `VOICE`, and `STEM`;
- a structurally complete candidate route when the classified intent matches an
  existing LEXC path.

The candidate LEXC path is advisory in this screen. The Coding Arena machine FST is the
operative hard-gate router.

### 4. Show the canonical six-slot packet

The demo displays:

```text
DIR → ASP → CLASS → SUBJ → VOICE → STEM
```

For the guided routing trace these mean:

| Slot | Demo meaning |
|---|---|
| `DIR` | selected route or lifecycle direction |
| `ASP` | bounded, decomposition-first, or test-gap execution aspect |
| `CLASS` | classified intent/effect class |
| `SUBJ` | target artifact and scope |
| `VOICE` | model policy and verifier context |
| `STEM` | terminal operation |

The screen also shows the deterministic VSA packet and vector digests. VSA remains
advisory after hard guards and has no patch authority.

### 5. Show the machine FST hard gate

The machine-oriented routing frame emits the exact input symbols:

| Prefix | Meaning |
|---|---|
| `I:` | intent |
| `A:` | artifact |
| `X:` | action |
| `S:` | scope |
| `R:` | risk |
| `G:` | grounding |
| `T:` | test state |
| `Q:` | quality policy |
| `C:` | cost/model policy |

The selected route emits:

| Prefix | Meaning |
|---|---|
| `O:` | output route |
| `M:` | model policy |
| `K:` | context class |
| `E:` | routing reason |
| `V:` | verifier requirement |

The panel shows the actual hard rule, selected route, model policy, context class,
reason, verifier requirement, compact symbols, and JSpace packet.

Hard gates run before weighted alternatives. Soft routing scores cannot override missing
grounding, missing tests, live risk, unresolved symbols, or approval requirements.

### 6. Show the bounded worker handoff

Only after routing does the demo reveal the packet prepared for a replaceable worker.
It includes:

- compressed context;
- route decision;
- localized files and symbols;
- grounding summary;
- bounded topology packet;
- exact patch-authority policy.

The same topology substrate introduced for the Human Agent Coding Arena is reused. The
browser receives only a bounded micro-arena, never Aura's complete repository topology.

The visual topology is an orientation and selection surface. Exact source spans, hashes,
tests, verifier output, and human review remain authoritative.

## Distinct provenance layers

The demo must preserve the distinction documented in
`docs/AURA_FST_PROVENANCE_AND_SECURITY.md`.

### Anishinaabemowin-derived governance alignment

Anishinaabemowin concepts inform governance principles such as mutual benefit,
relational responsibility, integrity, and memory extension. They are design alignments,
not automatic executable semantics by themselves.

### Athabaskan-inspired six-slot ordering

The six-slot sequence is a software morphotactic ordering constraint inspired by the
Athabaskan language family, as identified by the project creator. It is not presented as
a universal or formally validated linguistic model.

### Aura machine routing DSL

The `I/A/X/S/R/G/T/Q/C → O/M/K/E/V` symbols are Aura's computational routing language.
They implement deterministic admission rules and machine-oriented routing features.

Do not flatten these three layers into one generic “Indigenous grammar.”

## Always-visible guardrails

### Admitted before an LLM

- parse local text;
- assign deterministic lexical addresses;
- classify routing features;
- apply hard FST gates;
- localize CODEMAP candidates;
- compress bounded context;
- prepare a replaceable-worker handoff.

### Blocked

- secret disclosure;
- hidden chain-of-thought or private-reasoning storage;
- unrelated repository access;
- visual topology becoming patch authority;
- automatic source mutation;
- automatic commit;
- automatic push;
- automatic pull request;
- automatic merge.

## Claims to use

- Aura accepts ordinary bulk intention; users do not need to manually populate slots.
- The pre-LLM routing trace is deterministic and local.
- The English codebook contains 4,096 stable 12-bit lexical primitives.
- Local classification, six-slot binding, FST hard gates, and CODEMAP localization are
  separate observable operations.
- The LLM is a replaceable worker receiving a bounded handoff.
- Hard evidence and human authority remain outside the model.

## Claims to avoid

- Do not say the 4,096-word codebook alone provides full natural-language understanding.
- Do not say every unknown word is semantically understood; unknown words use a stable
  checksum fallback.
- Do not call the six-slot contract a universally validated linguistic theory.
- Do not conflate Anishinaabemowin governance concepts with the Athabaskan-inspired slot
  order or Aura's machine routing symbols.
- Do not say the visual topology can authorize a patch.
- Do not say Aura automatically commits, pushes, opens a PR, or merges.

## Validation

The focused showcase workflow validates:

- Python 3.10 and 3.12 compilation;
- fatal Ruff checks;
- JavaScript syntax for `intent.js`;
- exact 4,096-entry lexical-codebook loading;
- zero model calls before handoff;
- secret redaction;
- six-slot completeness;
- machine input and output symbol prefixes;
- real LEXC loading;
- bounded topology reuse;
- live server compilation;
- container startup;
- no automatic commit, push, or merge.
