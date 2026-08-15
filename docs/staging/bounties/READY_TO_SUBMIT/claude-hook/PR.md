# Pull request package — destructive Bash command guard

Target: `claude-builders-bounty/claude-builders-bounty#3`  
Pinned upstream: `1aeae2adc82d33f971fd7731644348dcdd24b5a6`

## Summary

Adds a focused Claude Code `PreToolUse` guard for the five destructive Bash command classes required by the bounty, with JSONL block logging, clear blocking messages, install instructions, and regression tests.

## Reproduction before edits

From the pinned upstream commit:

```bash
test ! -e hooks/block_destructive_commands.py
test ! -e hooks/test_block_destructive_commands.py
```

Both assertions pass, proving the required hook and its regression suite are absent before the patch.

## Root cause

The bounty repository contains the specification but no implementation of the requested Bash `PreToolUse` guard. Destructive commands therefore have no repository-provided pre-execution detector or audit log.

## What changes

- Adds `hooks/block_destructive_commands.py`.
- Blocks recursive forced removal, `DROP TABLE`, forced `git push`, `TRUNCATE`, and `DELETE FROM` without `WHERE`.
- Logs each blocked attempt as JSONL under `~/.claude/hooks/blocked.log`.
- Leaves normal Bash and non-Bash tool calls unaffected.
- Adds a self-contained unittest suite and two-command installation documentation.

## Verification

Executed in an isolated, read-only upstream clone pinned to the commit above. The patch passes `git apply --check`, `git diff --check`, Python compilation, and the full included unit suite.

See `VERIFICATION.md` for exact execution evidence.

No bounty claim, external branch, pull request, wallet action, or third-party repository mutation is part of this staged package.
