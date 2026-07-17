# Aura Review Arena — Research Basis and Design Requirements

Status: design evidence for implementation branch
Date: 2026-07-17

## Problem

Generic LLM review prompts are not sufficient for repository-scale review. They can skip files, hallucinate call graphs, drift to the wrong line, over-report stylistic issues, and fail to inspect cascading dependencies. Aura should instead combine deterministic program analysis with a replaceable coding agent that supplies run-specific hypotheses and review focus.

## Primary design evidence

### Existing review systems

- CodeRabbit documents automatic and incremental reviews, repository/path-specific instructions, coding-guideline ingestion, tool integration, CI-log analysis, learnings, structured agent output, and handoff to coding agents.
- Alibaba Open Code Review uses a deterministic-engineering plus agent hybrid: exact file selection, related-file bundling, rule matching, isolated sub-agents, comment positioning, reflection, and a precision-first benchmark. It also exposes delegation mode where a coding agent performs semantic review while the deterministic layer selects files and rules.
- PR-Agent provides configurable review, improve, describe, and ask tools over Git-platform diffs.
- reviewdog provides a language-neutral diagnostic interchange/reporting layer, diff filtering, SARIF/RDFormat ingestion, and Git-platform reporters.
- Vercel OpenReview demonstrates sandboxed review with full repository access, tool execution, inline suggestions, and durable workflows.
- Semgrep, CodeQL, and Joern provide deterministic pattern, semantic, path, taint, data-flow, and code-property-graph analyses.

### Research findings

- AACR-Bench (arXiv:2601.19494) reports that holistic repository context and retrieval granularity materially affect automated-code-review quality, with effects varying by language, model, and agent architecture.
- Towards Practical Defect-Focused Automated Code Review (arXiv:2505.17928) identifies four practical requirements: relevant context extraction, key-bug inclusion, false-alarm reduction, and human-workflow integration. Its approach combines code slicing, multi-role review, filtering, and human-oriented prompts.
- Reducing False Positives in Static Bug Detection with LLMs (arXiv:2601.18844) reports strong false-positive reduction from hybrid static-analysis plus LLM techniques in an industrial setting.
- Do Code LLMs Do Static Analysis? (arXiv:2505.12118) finds that LLMs perform poorly at generating call graphs, ASTs, and data-flow graphs; deterministic analysis should therefore compute those artifacts.
- RepoGraph (arXiv:2410.14684) shows that repository-level code graphs improve software-engineering agents when exposed as a navigation/retrieval tool.
- Bridging Code Property Graphs and Language Models for Program Analysis (arXiv:2603.24837) shows the value of high-level graph tools for slicing, taint tracking, data-flow analysis, and semantic navigation instead of requiring the LLM to author complex graph queries.
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

The missing layer is a canonical Review Arena that compiles these owners into a repeatable review protocol.

## Required architecture

### Separation of responsibilities

Aura must compute:

- exact changed files and changed symbols;
- forward dependencies and reverse dependents;
- bounded impact slices;
- deterministic syntax/tool/test findings;
- source hashes and line anchors;
- evidence strength and finding deduplication;
- repair requests for Forge.

The coding agent may supply:

- run-specific review hypotheses;
- domain invariants;
- risk focus;
- questions to test across the impact graph;
- semantic findings tied to exact evidence.

The coding agent must not:

- invent graph edges as authority;
- mark its own findings proven;
- mutate production code through the reviewer;
- commit, push, open, or merge a PR automatically;
- weaken the contract's verification or human-review requirements.

### Review lifecycle

FRAME → DIFF → SLICE → SCAN → INVESTIGATE → CORROBORATE → RANK → DECIDE → REPAIR_HANDOFF → DISSOLVE

### Precision-first evidence ladder

1. test or runtime failure;
2. deterministic parser/static-tool finding;
3. exact AST/data-flow/graph evidence;
4. agent finding corroborated by exact source and dependency evidence;
5. uncorroborated hypothesis, retained only as advisory.

### Run-specific focus contract

Each focus directive should include:

- name;
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
- high-risk paths reviewed first;
- no-model mode for syntax/tool-only review;
- model-neutral structured packets over MCP;
- output deduplication and confidence calibration;
- cache by repository head, diff digest, focus digest, and tool versions.

## Recommended implementation phases

### V1 — Graph-guided review contracts

- review request/contract/finding schemas;
- exact diff and changed-symbol extraction;
- bidirectional topology impact slicing;
- built-in Python AST correctness/security checks;
- safe optional tool adapters;
- agent focus directives and strict finding submission;
- final review packet and Forge repair handoff;
- MCP tools for Codex, Hermes, Claude, Gemini, and other clients.

### V2 — Polyglot semantic adapters

- tree-sitter/ast-grep adapters;
- Semgrep/SARIF ingestion;
- CodeQL and Joern/codebadger capability adapters;
- language-specific test and type-check discovery.

### V3 — Review Council and false-positive judge

- specialist reviewer roles selected from the run's risk map;
- independent evidence judge;
- contradiction resolution;
- accepted/rejected finding feedback stored as governed proposals, not direct learned truth.

### V4 — Benchmark and adaptive scan budgeting

- AACR-Bench-compatible evaluation;
- mutation-seeded hidden defects;
- precision, recall, F1, key-bug inclusion, false-alarm rate, line-position accuracy, latency, and token cost;
- adaptive graph depth and model budget by risk and historical evidence.

## References

- CodeRabbit documentation: https://docs.coderabbit.ai/
- Alibaba Open Code Review: https://github.com/alibaba/open-code-review
- PR-Agent: https://github.com/The-PR-Agent/pr-agent
- reviewdog: https://github.com/reviewdog/reviewdog
- Vercel OpenReview: https://github.com/vercel-labs/openreview
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
- Code Review Benchmark Survey: https://arxiv.org/abs/2602.13377
