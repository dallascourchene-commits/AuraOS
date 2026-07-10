# Aura Agent Command Risk Gate

## What This Is

Classifies command-effect risk before agents run commands. Hard blocks risky commands unless human explicitly approves.

## Risk Categories

safe_read_only, repo_local_test, git_commit, git_push, package_install, credential_access, encoded_payload, external_script, dns_lookup, destructive_file_op, git_history_rewrite

## Hard Blocks

- `curl | sh`, `wget | sh` — external scripts
- Encoded shell payloads — `eval(base64 -d)`
- Credential/token reads — `cat ~/.ssh/id_rsa`
- Destructive deletes — `rm -rf /`
- `git push --force` — history rewrite
- Unknown setup scripts from untrusted docs

## CLI

```powershell
python -m aura_agent_arena_cli command-risk --command "python setup.py install"
```
