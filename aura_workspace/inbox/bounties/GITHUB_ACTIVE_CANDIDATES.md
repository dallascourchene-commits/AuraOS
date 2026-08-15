# GitHub bounty candidates — task/constraint intake

## mergeos-bounties/Loru#19 — selected execution target

**Bounty:** 25 MRG  
**State:** open  
**Labels observed:** `documentation`, `good first issue`, `bounty`, `bounty: feature`, `reward:25-mrg`

Task:
- write `CONTRIBUTING.md` with setup, test commands, PR checklist, and MergeOS claim flow;
- link it from README.

Source repo constraints resolved from current `master`:
- Python >=3.11.
- development commands: `pytest -q`, `ruff check src tests`, `loru demo`.
- optional GUI flow uses PySide6; screenshot refresh command is `python scripts/capture_gui_shots.py`.
- bounty policy requires follow/star/claim comments before the PR and targets `master`.
- payout eligibility remains maintainer/ledger controlled after merge.

Source issue: https://github.com/mergeos-bounties/Loru/issues/19
Policy: https://github.com/mergeos-bounties/Loru/blob/master/docs/BOUNTY.md

## claude-builders-bounty#3 — technical execution, funding unresolved

Declared task: Python or Bash Claude Code `PreToolUse` hook that blocks:
- `rm -rf`
- `DROP TABLE`
- `git push --force`
- `TRUNCATE`
- `DELETE FROM` without `WHERE`

It must log every blocked attempt to `~/.claude/hooks/blocked.log` with timestamp, command and project path; explain the block to Claude; avoid interfering with normal Bash; and document installation in <=2 commands.

Technical implementation and isolated contract tests were completed, but exact live provider funding was not independently resolved on Opire, so this packet is not in funded READY_FOR_PR.

Source: https://github.com/claude-builders-bounty/claude-builders-bounty/issues/3
