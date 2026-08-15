# Validation — claude-builders-bounty#3

Disposition: `TECHNICALLY_VERIFIED / FUNDING_PROVIDER_UNRESOLVED / NOT_FUNDED_READY`

Isolated standard-library test run:
- 5 unittest methods PASS
- 14 behavior cases exercised
- required block set covered: `rm -rf` (+ split flag form), `DROP TABLE`, `git push --force`, `TRUNCATE`, `DELETE FROM` without `WHERE`
- allowed set covered: normal git push, normal rm, pytest/npm commands, and `DELETE FROM ... WHERE ...`
- non-Bash tool event ignored
- malformed JSON fails closed
- blocked log includes project path and exact attempted command
- installer run twice successfully in an isolated temporary HOME (idempotent hook entry)

Artifact SHA-256:
- `block_destructive.py`: `c8e891dfbf866fe26cabae49ed40cfd20ec79273da5425de3f13d89677e4fbeb`
- `install_hook.py`: `0e0c75b79cb70bcad75d62135befa8f8f0c87c0348699c604331fb71616de7eb`
- `README.md`: `48e6f9028f320077991116bf2771bc3e98646f82d16ca3ccd0eb1e675e1e6349`
- `test_block_destructive.py`: `77b0fe46067f5cbe913ea5f4888192e70f0f59d6da3dc5d30a72fafb9052ece3`

No claim or external PR was made.
