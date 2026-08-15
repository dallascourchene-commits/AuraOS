# PR packet — mergeos-bounties/Loru#19

## Disposition

`TECHNICALLY_READY / CLAIM_PREREQUISITES_PENDING / NO_EXTERNAL_PR_OPENED`

## Proposed PR title

`docs: add contributing guide and bounty claim path`

## Proposed body

Fixes #19

Adds a contributor guide with development setup, baseline test/lint/demo commands, a focused PR checklist, evidence expectations, and the repository's current MergeOS claim flow. Links the guide from the README table of contents.

### Verification
- Structural contract validator: PASS
- Current README source checked before patch: PASS
- `CONTRIBUTING.md` absent on current `master`: PASS
- Setup/check commands sourced from current README/pyproject: PASS
- Claim flow sourced from current `docs/BOUNTY.md` and issue #19: PASS

### External prerequisites before opening
Complete the star/follow/claim-comment requirements in issue #19 / `docs/BOUNTY.md`. This staged packet does not assert that those account-level actions have occurred.

## Patch contents
- new `CONTRIBUTING.md`
- one README backlink hunk in `README.patch`

## Local artifact hashes
- `CONTRIBUTING.md` SHA-256: `13b4ba8752577828a681297dc4b130a3980e4dfa9b3d94e6079290a9f16cfd97`
- `README.patch` SHA-256: `53a7e662da8b3fa9f02a59bb1d560cef4bdcc36735d2ea0b97ccc2d009256306`
