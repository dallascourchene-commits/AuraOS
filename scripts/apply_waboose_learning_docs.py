from __future__ import annotations

from pathlib import Path


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing Waboose documentation target: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    path = Path("docs/AURA_CODING_WABOOSE.md")
    text = path.read_text(encoding="utf-8")
    text = replace_required(text, "# Coding Waboose V1\n", "# Coding Waboose V1.1\n", "title")
    text = replace_required(
        text,
        '''- focused pytest regressions selected from changed and topology-related files.

Coding Waboose does not silently download rule packs''',
        '''- focused pytest regressions selected from changed and topology-related files.

### Semantic integrity rule packs

V1.1 adds deterministic semantic review packs for defect classes that ordinary
syntax checks and linters often miss:

- `strict_input_types` — catches truthiness-based parsing of declared boolean options;
- `symbol_identity` — preserves qualified identities such as `Worker.run` at every exact target boundary;
- `source_integrity` — requires exact Python decoding and fail-closed repository inventories;
- `bounded_graph_integrity` — prevents dependency edges from escaping bounded node closures;
- `test_evidence_preservation` — keeps test callable nodes and their call/test edges in bounded audit evidence.

Each pack has positive and false-positive regression tests. A detector receipt
means the pack actually executed over exact source; it is not a claim that a
defect exists.

### Semantic completeness gate

`aura_coding_waboose_cli.py run` is a deterministic-only path. It may complete a
custom focus directive only when a registered deterministic semantic pack truly
implements that directive. Any unsupported agent-origin directive remains
unverified and blocks finalization:

```yaml
ok: false
error: semantic_review_incomplete
status: BLOCKED_INCOMPLETE_SEMANTIC_REVIEW
forge_repair_requests: []
automatic_merge: false
```

A custom semantic question can otherwise be completed only by an actual coding
agent submission that Aura corroborates against exact current source. Passing
tests or linters alone can no longer masquerade as completion of an unrelated
semantic question.

Coding Waboose does not silently download rule packs''',
        "semantic rule sections",
    )
    text = replace_required(
        text,
        '''## Evidence ladder and false-positive control
''',
        '''## Learning from successful CodeRabbit reviews

CodeRabbit is treated as an external **teacher signal**, never as patch,
verification, or merge authority. A lesson enters Waboose memory only when:

1. the CodeRabbit review completed successfully;
2. its review is bound to the exact pull-request head SHA;
3. its repository-relative file and line range still exist at that head;
4. any supplied evidence excerpt matches the exact source window;
5. Python source is decoded exactly with its declared encoding;
6. the lesson is deduplicated against prior grounded episodes.

The learning path composes Aura's existing organs:

```text
successful CodeRabbit finding
  → exact reviewed-head/source grounding
  → AST/source signature
  → Capability Resolver + Capability Connectome path
  → DREAM-lite similarity ranking against prior review lessons
  → QDKT observation and causal-update event
  → repeated-confirmation confidence update
  → QDKT crystal after the governed threshold
  → retrieval before a future Waboose review
  → current-source reproof before any repair handoff
```

Known recurring defect families reinforce deterministic semantic rule packs.
Unknown recurring patterns may surface only as `probable` advisory findings;
they cannot generate a Forge repair request without fresh current-source
corroboration.

### Cross-PR persistence and trust boundary

The GitHub integration uses two workflows:

- `coderabbit-waboose-learning.yml` receives a CodeRabbit review event and
  dispatches a trusted learning run on the repository's default branch;
- `coderabbit-waboose-learning-persist.yml` serializes updates to shared
  DREAM/QDKT memory, verifies the exact reviewed SHA, and materializes that head
  as read-only source data.

The trusted default-branch runtime performs the learning. Python from the
reviewed pull request is **never executed**, installed, sourced, or tested by the
learning workflow. The persistent memory is stored outside the repository and
is shared across later pull requests.

CLI:

```bash
python aura_coderabbit_learning_cli.py ingest --review coderabbit_review.json
python aura_coderabbit_learning_cli.py summary
```

Every learning result preserves:

```yaml
teacher: CodeRabbit
teacher_is_patch_authority: false
connectome_is_advisory: true
dream_lite_is_ranking_only: true
qdkt_crystals_are_patch_authority: false
production_mutation: false
automatic_merge: false
human_review_required: true
```

## Evidence ladder and false-positive control
''',
        "learning section",
    )
    text = replace_required(
        text,
        '''- `aura_waboose_status`
''',
        '''- `aura_waboose_status`
- `aura_waboose_learn_coderabbit`
- `aura_waboose_learning_summary`
''',
        "MCP learning tools",
    )
    text = replace_required(
        text,
        '''- `aura_coding_waboose_cli.py` — one-shot CLI;
''',
        '''- `aura_coding_waboose_cli.py` — one-shot review CLI;
- `aura_waboose_semantic_rules.py` — deterministic semantic-integrity packs;
- `aura_waboose_learning.py` — exact grounding, Connectome routing, DREAM-lite retrieval, and QDKT learning;
- `aura_coderabbit_learning_cli.py` — external-review lesson ingestion and memory summary;
''',
        "canonical learning owners",
    )
    text = replace_required(
        text,
        '''Planned extensions include polyglot tree-sitter/ast-grep analysis, local SARIF/RDFormat ingestion, CodeQL/Joern code-property-graph tools, dynamic and causal slicing, specialist Waboose Council roles, an independent false-positive judge, mutation-seeded hidden defects, and AACR-Bench-compatible precision/recall/token-cost evaluation.
''',
        '''Planned extensions include polyglot tree-sitter/ast-grep analysis, local SARIF/RDFormat ingestion, CodeQL/Joern code-property-graph tools, dynamic and causal slicing, specialist Waboose Council roles, an independent false-positive judge, mutation-seeded hidden defects, AACR-Bench-compatible precision/recall/token-cost evaluation, and governed promotion of repeatedly grounded learned patterns into new deterministic rule packs.
''',
        "future learning extension",
    )
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
