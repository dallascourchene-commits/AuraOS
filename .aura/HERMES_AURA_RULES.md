# Hermes → Aura Rules

You are inside AuraOS.

## Mandatory Rules

1. You must use the Aura Agent Arena Bridge before direct file reads.
2. You must call digest first: `python -m aura_agent_arena_cli digest`
3. You must call find-affordances before planning: `python -m aura_agent_arena_cli find-affordances --objective "..."`
4. You must use CODEMAP search before opening files: `python -m aura_agent_arena_cli search --query "..." --kind symbol`
5. You must use read-slice for exact source: `python -m aura_agent_arena_cli read-slice --file <file> --symbol <symbol>`
6. You must produce token savings evidence before editing: `python -m aura_agent_arena_cli token-report --objective "..." --files <files>`
7. You must use a feature branch and PR workflow. Never commit directly to main.
8. You must NOT use `git add .` — stage only specific scoped files.
9. You must NOT read hub files directly (aura_node.py, aura_live_architect.py, etc.). Use read-slice with `--symbol`.
10. You must NOT treat advisory layers (JSpace, VSA, ST3GG, visual topology, summaries) as patch authority.
11. You must NOT read .venv, node_modules, __pycache__, build artifacts, or generated files.
12. All paths must remain repo-relative inside AuraOS.
13. On Windows, use: `python -m aura_agent_arena_cli <subcommand>` (not bash-only scripts).

## Patch Authority

- patch_authority: `exact_source_spans_and_hashes_only`
- vsa_patch_authority: `false`
- Only exact source spans, hashes, CODEMAP facts, tests, and verifier gates are authority.
- JSpace, VSA, ST3GG, screenshots, visual topology, and summaries are advisory only.

## Git Safety

- Do NOT run `git add .`
- Do NOT commit directly to main
- Do NOT include untracked nested AuraOS folders or scratch directories
- STOP if working tree is dirty before branch creation unless user explicitly approves
- Use `git diff --stat` to verify exactly which files will be committed
