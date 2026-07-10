# Aura Research Evidence Lane

## What This Is

Uses Aura's arXiv/research/paper-memory systems to support coding plans. Research evidence is advisory — cannot authorize source edits.

## Offline Mode

Uses `.aura/RESEARCH_MANIFEST.json` and local paper memory. No network calls in tests.

## Rules

- Research evidence is advisory only
- Research-backed code changes still require CODEMAP grounding and verifier gates
- Network/arXiv calls must be opt-in and disabled in tests
