# Aura Research Cockpit Lane

## What This Is

The Research Cockpit Lane provides research-grounded planning using arXiv/paper memory lookup, research manifest linkage, and evidence-backed refactor proposals.

## Offline Mode

The research lane works offline using `.aura/RESEARCH_MANIFEST.json` and local paper memory. Network/arXiv calls are opt-in and disabled in tests.

### Functions
- `research_manifest_search(query, offline=True)` — search local research manifest
- `paper_memory_recall(query)` — recall from paper memory
- `arxiv_forager_plan(query, offline=True)` — plan arXiv foraging (offline = plan only)
- `research_to_cockpit_evidence_packet(research_results)` — convert to evidence packet with token estimates
- `research_to_agent_context_capsule(research_results)` — compress for agent context

## CLI

```powershell
python -m aura_agent_arena_cli research-evidence --objective "research this approach" --offline
```

## Safety
- Research packets are evidence/advisory, NOT patch authority.
- Research-grounded coding proposals must still pass CODEMAP grounding before patch.
- `patch_authority: "exact_source_spans_and_hashes_only"`
