# Aura Refactor Candidates

## What This Is

Detects practical coding candidates from the change graph. A RefactorCandidate is advisory only — it cannot authorize patching.

## Candidate Types

bug_fix, refactor, feature, test_gap, docs_update, security_hardening, performance, architecture_cleanup, agent_integration

## Rules

- Advisory only — cannot patch
- Must pass Coding Arena Grounding before Agent Arena handoff
- Must include exact source span requirements before patch
