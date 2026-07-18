# Coding Waboose — Research Basis and Design Requirements

Status: implementation and design evidence
Date: 2026-07-17

## Name and language boundary

The founder selected **Coding Waboose** as the product name. The widely documented Ojibwe/Anishinaabemowin dictionary spelling for rabbit or snowshoe hare is **waabooz**. Aura retains the founder-selected product spelling while documenting the distinction and avoiding a claim that the product spelling is the standardized dictionary form.

## Problem

Generic LLM review prompts are not sufficient for repository-scale review. They can skip files, hallucinate call graphs, drift to the wrong line, over-report stylistic issues, and fail to inspect cascading dependencies. Aura should combine deterministic program analysis with a replaceable coding agent that supplies run-specific hypotheses and review focus.

The target is not a clone of one commercial bot. Coding Waboose should be a model-neutral Aura organ that can be driven by Codex, Hermes, Claude Code, Gemini CLI, or another MCP client while retaining exact repository evidence, bounded authority, and separate repair/promotion decisions.

## Primary design evidence

### Existing review systems

- CodeRabbit documents automatic and incremental reviews, repository/path-specific instructions, coding-guideline ingestion, tool integration, CI-log analysis, learnings, structured agent output, and handoff to coding agents.
- Alibaba Open Code Review uses a deterministic-engineering plus agent hybrid: exact file selection, related-file bundling, rule matching, isolated sub-agents, comment positioning, reflection, precision-first filtering, and delegation mode.
- PR-Agent provides configurable review, improve, describe, and ask tools over Git-platform diffs.
- reviewdog provides a language-neutral diagnostic interchange/reporting layer, diff filtering, SARIF/RDFormat ingestion, and Git-platform reporters.
- Vercel OpenReview demonstrates sandboxed review with full repository access, tool execution, inline suggestions, and durable workflows.
- GitHub Copilot code review demonstrates repository instructions, tool-assisted review, and coding-agent handoff inside the GitHub workflow.
- Open Code Review's graph maps and Code Review Graph demonstrate practical demand for file, module, import, and dependency maps as review inputs.
- Semgrep, CodeQL, Joern, tree-sitter, and ast-grep provide deterministic pattern, semantic, path, taint, data-flow, syntax-tree, and code-property-graph analyses.

### Research findings

- AACR-Bench (arXiv:2601.19494) reports that holistic repository context and retrieval granularity materially affect automated-code-review quality, with effects varying by language, model, and agent architecture.
- Towards Practical Defect-Focused Automated Code Review (arXiv:2505.17928) identifies four practical requirements: relevant context extraction, key-bug inclusion, false-alarm reduction, and human-workflow integration. Its approach combines code slicing, multi-role review, filtering, and human-oriented prompts.
- Reducing False Positives in Static Bug Detection with LLMs (arXiv:2601.18844) reports strong false-positive reduction from hybrid static-analysis plus LLM techniques in an industrial setting.
- Do Code LLMs Do Static Analysis? (arXiv:2505.12118) finds that LLMs perform poorly at generating call graphs, ASTs, and data-flow graphs; deterministic analysis should compute those artifacts.
- RepoGraph (arXiv:2410.14684) shows that repository-level code graphs improve software-engineering agents when exposed as a navigation/retrieval tool.
- Bridging Code Property Graphs and Language Models for Program Analysis (arXiv:2603.24837) shows the value of high-level graph tools for slicing, taint tracking, data-flow analysis, and semantic navigation instead of requiring the LLM to author complex graph queries.
- CT-Repair (arXiv:2607.12605) combines code-property graphs with temporal execution graphs, reinforcing the value of connecting static dependency evidence with runtime order and causal behavior.
- Dynamic-slicing research shows that executed dependency slices can reduce the amount of code a reviewer must inspect while preserving behavior-specific causality.
- The 2026 code-review benchmark survey (arXiv:2602.13377) recommends broader task coverage, dynamic runtime evaluation, and fine-grained assessment rather than relying on text-similarity metrics.

## Aura-specific opportunity

Aura already owns:

1. CODEMAP symbol ranges and repository file cards.
2. AST/import/call/shared-resource topology.
3. exact source-slice leases.
4. Coding Arena preparation and risk routing.
5. controlled external-agent sessions.
6. verifier/test execution and repair packets.
7. Forge evidence contracts and human-review authority boundaries.
8. Planning Board and Coding Breadboard contracts with typed ports, preconditions, effects, constraints, reversibility, authority classes, verifiers, and BC0–BC5 continuity.
9. forward planning, backward regression, bidirectional convergence, append-only planning events, and read-only Coding Arena projections.

The missing layer is a canonical code-review organ that compiles these owners into a repeatable diagnostic protocol.

## Breadboard synthesis

The Coding Breadboard is directly useful to Coding Waboose and is likely its strongest architectural differentiator.

A review concern is not merely a prompt. It can be compiled into a temporary diagnostic component:

```text
changed source + topology slice + review hypothesis
  → typed diagnostic action
  → explicit constraints and capabilities
  → forward consequence path
  → backward proof requirements
  → inspection receipts
  → corroborated finding or rejected/advisory hypothesis
```

### Why this is stronger than a graph viewer

A graph viewer only shows relationships. The diagnostic breadboard can represent:

- typed inputs and outputs;
- connected exact evidence;
- explicitly mocked missing inputs;
- out-of-order construction without pretending the circuit is powered;
- forward simulation of possible downstream consequences;
- backward regression from a proposed defect to the proof needed to justify it;
- capability and tool requirements;
- reversibility and idempotency;
- policy classification and human authority;
- verifier receipts and continuity.

### Board continuity for review

```text
BC0 STRUCTURAL   components and fallback paths are valid
BC1 TYPED        ports, effects, and verifier contracts are declared
BC2 CONSTRAINED  review-only policy and budgets are resolved
BC3 GROUNDED     exact source and graph references are bound
BC4 AUTHORIZED   no-execution/review-only classification is present
BC5 VERIFIED     declared diagnostic inspections have bound receipts
```

A BC4 component can be useful and inspectable but unpowered. A BC5 component means the inspection ran; it does not mean a bug was found. Finding evidence and review-component continuity remain separate classes.

### Dynamic Waboose loop

```text
observe diff or workspace
  → update exact changed-source state
  → recompute impact and breadboard connectivity
  → select high-risk feasible diagnostic frontier
  → run deterministic tools and bounded agent inspection
  → bind receipts and finding evidence
  → update circuit status
  → deepen, reject, or hand off an eligible finding to Forge
```

Replanning should occur after a meaningful new fact: a failed test, malformed packet, new caller, contradiction, missing proof, tool timeout, changed risk, or human instruction. It should not occur after every trivial parser step.

## Required architecture

### Separation of responsibilities

Aura must compute:

- exact changed files and changed symbols;
- forward dependencies and reverse dependents;
- bounded impact slices;
- diagnostic breadboard connectivity and explicit mocks;
- deterministic syntax/tool/test findings;
- source hashes and line anchors;
- evidence strength and finding deduplication;
- repair requests for Forge.

The coding agent may supply:

- run-specific review hypotheses;
- domain invariants;
- risk focus;
- questions to test across the impact graph;
- requested diagnostic components;
- semantic findings tied to exact evidence.

The coding agent must not:

- invent graph edges as authority;
- hide an unresolved input rather than declaring a mock;
- mark its own findings proven;
- treat an energized circuit as proof of a defect;
- mutate production code through Waboose;
- commit, push, open, or merge a PR automatically;
- weaken verification or human-review requirements.

### Review lifecycle

FRAME → DIFF → SLICE → SCAN → INVESTIGATE → CORROBORATE → RANK → DECIDE → REPAIR_HANDOFF → DISSOLVE

### Precision-first evidence ladder

1. test, runtime, or causal trace failure;
2. deterministic parser/static-tool finding;
3. exact AST/data-flow/graph/call-site evidence;
4. agent finding corroborated by exact source and dependency evidence;
5. uncorroborated hypothesis retained only as advisory.

### Run-specific focus contract

Each focus directive should include:

- name and stable directive ID;
- review question;
- risk category;
- target files/symbols/patterns;
- dependency direction: callers, callees, both, shared resources;
- graph depth/node budget;
- required evidence;
- suggested deterministic tools;
- acceptance/rejection condition.

### Efficiency requirements

- diff-first and symbol-first retrieval;
- incremental graph slices rather than whole-repository prompts;
- deterministic prefilter before LLM review;
- related-file bundles with isolated context;
- high-risk breadboard components energized first;
- no-model mode for syntax/tool-only review;
- model-neutral structured packets over MCP;
- output deduplication and confidence calibration;
- cache by repository head, diff digest, focus digest, graph digest, and tool versions;
- dynamic/runtime slicing only when the static circuit cannot resolve a causal question.

## Implementation phases

### V1 — Coding Waboose contracts and diagnostic breadboard

- request, contract, finding, and product-envelope schemas;
- exact diff and changed-symbol extraction;
- bidirectional topology impact slicing;
- built-in Python AST correctness/security checks;
- safe optional local tool adapters;
- agent focus directives and strict finding submission;
- Planning Board diagnostic components with explicit mocks;
- BC0–BC5 continuity and inspection receipts;
- final Waboose packet and Forge repair handoff;
- MCP tools for Codex, Hermes, Claude, Gemini, and other clients.

### V2 — Polyglot semantic and graph adapters

- tree-sitter and ast-grep adapters;
- Semgrep/SARIF/RDFormat ingestion;
- CodeQL and Joern/code-property-graph capability adapters;
- language-specific type-check and test discovery;
- exact cross-language import and symbol bindings.

### V3 — Dynamic and causal breadboard traces

- bounded runtime traces for changed paths;
- dynamic slicing over failing or suspicious executions;
- static CPG + temporal execution graph fusion;
- branch/path feasibility evidence;
- mocked external dependencies with explicit provenance.

### V4 — Waboose Council and false-positive judge

- specialist reviewer roles selected from the run's risk map;
- independent evidence judge;
- contradiction resolution;
- accepted/rejected feedback stored as governed proposals, not direct learned truth.

### V5 — Benchmark and adaptive scan budgeting

- AACR-Bench-compatible evaluation;
- mutation-seeded hidden defects;
- precision, recall, F1, key-bug inclusion, false-alarm rate, line-position accuracy, latency, and token cost;
- adaptive graph depth, breadboard frontier, tool choice, and model budget by risk and historical evidence.

## References

- Ojibwe People's Dictionary, `waabooz`: https://ojibwe.lib.umn.edu/main-entry/waabooz-na
- CodeRabbit documentation: https://docs.coderabbit.ai/
- Alibaba Open Code Review: https://github.com/alibaba/open-code-review
- PR-Agent: https://github.com/The-PR-Agent/pr-agent
- reviewdog: https://github.com/reviewdog/reviewdog
- Vercel OpenReview: https://github.com/vercel-labs/openreview
- GitHub Copilot code review: https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review
- Code Review Graph: https://github.com/tirth8205/code-review-graph
- RepoGraph: https://github.com/ozyyshr/RepoGraph
- Semgrep: https://github.com/semgrep/semgrep
- CodeQL: https://github.com/github/codeql
- Joern: https://github.com/joernio/joern
- AACR-Bench: https://arxiv.org/abs/2601.19494
- Practical Defect-Focused ACR: https://arxiv.org/abs/2505.17928
- False-Positive Reduction: https://arxiv.org/abs/2601.18844
- Do Code LLMs Do Static Analysis?: https://arxiv.org/abs/2505.12118
- RepoGraph paper: https://arxiv.org/abs/2410.14684
- Code Property Graphs + LMs: https://arxiv.org/abs/2603.24837
- CT-Repair: https://arxiv.org/abs/2607.12605
- Dynamic slicing empirical study: https://arxiv.org/abs/2101.03008
- Code Review Benchmark Survey: https://arxiv.org/abs/2602.13377
