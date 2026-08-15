# Destructive-command PreToolUse hook

Blocks the bounty's required destructive Bash patterns before Claude Code can execute them:
`rm -rf`, `DROP TABLE`, `git push --force`, `TRUNCATE`, and `DELETE FROM` statements without a `WHERE` clause.
Every blocked attempt is appended to `~/.claude/hooks/blocked.log` with UTC timestamp, command, and project path.

## Install — two commands

```bash
mkdir -p ~/.claude/hooks && cp block_destructive.py ~/.claude/hooks/block_destructive.py && chmod +x ~/.claude/hooks/block_destructive.py
python3 install_hook.py
```

`install_hook.py` merges (rather than replaces) the required `PreToolUse` Bash hook into `~/.claude/settings.json` and writes a timestamped backup before changing an existing settings file.

## Verify

```bash
python3 -m unittest discover -s tests -v
```

The hook follows Claude Code's `PreToolUse` contract: JSON is read from stdin; a blocked Bash command returns a `hookSpecificOutput` object with `permissionDecision: "deny"`; allowed commands exit 0 with no output so normal permission handling continues.
