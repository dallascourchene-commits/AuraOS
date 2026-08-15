# Bounty Patch Verification Scorecard

## 1. claude-builders-bounty/claude-builders-bounty#3 — $100 advertised / Opire-backed

Patch: `claude-hook/READY_FOR_PR.patch`

- Initial detector run: FAIL — required `rm -rf` and `rm -fr` cases escaped the first regex.
- Corrective metabolism: replaced regex lookahead with token-level `rm` option parsing using stdlib `shlex`.
- Final isolated suite: PASS — 4 unittest methods covering 17 destructive/benign/non-Bash/invalid-input cases.
- `git apply --check`: PASS.
- Source boundary: current Claude Code PreToolUse command-hook semantics; exit `2` blocks the tool call.
- Residue: this is a focused denylist gate, not a complete shell policy engine.

## 2. mergeos-bounties/PlantGuide#10 — 50 MRG

Patch: `plantguide-sdk/READY_FOR_PR.patch`

- Python source bindings: current `identify_from_tags()`, `ToyPlantIdentifier.identify()`, `care_card_for_species()`.
- JSON Schema Draft 2020-12 positive source-shaped fixture: PASS.
- Negative fixture (`score > 1`): correctly rejected.
- TypeScript: `tsc --strict --noEmit --target ES2020 index.ts`: PASS.
- `git apply --check`: PASS.
- Residue: full upstream `pytest`/ruff suite was not cloned into this network-isolated container; verification is isolated to the new contracts and source-defined shapes.

## 3. mergeos-bounties/Loru#19 — 25 MRG

Patch: `loru-contributing/READY_FOR_PR.patch`

- Setup/test commands cross-checked against current `pyproject.toml` and README.
- MergeOS claim/evidence flow cross-checked against `docs/BOUNTY.md`.
- Required contributing anchors: PASS (setup, `ruff`, `pytest`, `loru demo`, PR checklist, bounty policy, good-first path).
- `git apply --check`: PASS.
- Residue: documentation-only patch; no upstream behavioral code changed.

## External-action boundary

No claim, star/follow, `/opire try`, wallet signature, bond, fork, third-party branch, or PR was created. These patches are staged for human selection/submission.
