# Aura Agent Bridge — Atomic GitHub Publication

## Purpose

This lane replaces temporary GitHub Actions materializer/bootstrap/publisher workflows with a direct, bounded Git Data API transaction.

```text
exact base/head evidence
  → bounded canonical change manifest
  → one blob per upsert
  → one tree over the exact parent tree
  → one commit with the exact expected parent
  → fresh ref creation or non-forced fast-forward
  → one pull request
  → review and verification
  → separate human-authorized merge call bound to expected_head_sha
```

The implementation is in:

- `aura_agent_arena_github_bridge.py`;
- `aura_agent_arena_github_mcp.py`;
- `tests/test_aura_agent_arena_github_bridge.py`.

## Why this is better

The former workaround encoded source or patches into temporary repository files, committed a workflow trigger, waited for GitHub Actions to materialize the payload, then deleted the transport artifacts. That introduced extra commits, temporary workflow authority, stale-head races, cleanup obligations, review noise, and branch reuse mistakes.

The Git Data API already provides the correct primitive. Aura now prepares all intended file mutations as one deterministic contract and publishes them as a single tree and commit. No local `git add`, staging directory, shell push, encoded payload archive, or temporary workflow is required.

## Agent Bridge tools

Launch the augmented MCP entrypoint:

```bash
python3 -m aura_agent_arena_github_mcp
```

It retains the existing Agent Bridge tools and adds:

```text
aura_github_prepare_publication
aura_github_execute_publication
aura_github_prepare_merge
```

### `aura_github_prepare_publication`

Compiles a deterministic publication contract. The request binds:

- repository;
- create/update mode;
- base and head branches;
- exact expected base SHA;
- exact expected parent SHA;
- canonical bounded file changes;
- commit and PR metadata;
- explicit publication authorization.

Create mode requires a fresh branch and requires `expected_parent_sha == expected_base_sha`. Update mode requires the current feature ref to equal `expected_parent_sha`.

The contract sorts paths, rejects duplicates, hashes every decoded file payload, caps file/aggregate bytes, disallows path escapes, and rejects temporary transport artifacts by default.

### `aura_github_execute_publication`

Execution reads only the operator-controlled `AURA_GITHUB_TOKEN` environment variable. The token is never accepted through MCP arguments, persisted, logged, or returned.

The publisher:

1. resolves the exact base ref;
2. verifies the base SHA;
3. verifies that create mode uses a nonexistent branch, or update mode uses the exact expected parent;
4. resolves the exact parent tree;
5. creates bounded blobs;
6. creates one tree;
7. creates one commit;
8. rechecks the base ref before publishing;
9. creates the fresh ref or advances it with `force=false`;
10. creates or updates the PR;
11. returns a content-addressed publication receipt.

If the base moves during preparation, the branch and PR are not created. The orphaned Git objects are unreachable and GitHub may later collect them.

### `aura_github_prepare_merge`

The publisher never merges. Merge is a second, explicit connector operation and remains blocked until all gates are true:

```text
human_merge_authorized
checks_passed
review_threads_resolved
codemap_regenerated
```

When all gates pass, Aura emits only this bounded call shape:

```text
GitHub.merge_pull_request(
  repository_full_name,
  pr_number,
  merge_method,
  expected_head_sha,
)
```

`expected_head_sha` makes GitHub reject a merge if the PR changed after review.

## Authority boundaries

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
publication_requires_explicit_authorization: true
automatic_merge: false
force_ref_update: false
human_review_required: true
```

A valid publication contract is not proof that tests passed and is not merge authority. Reviewers, CI, Waboose, Codex, CodeRabbit, CODEMAP verification, and the human maintainer remain separate gates.

## Temporary transport rejection

Unless an operator deliberately sets `allow_temporary_transport=true`, the contract rejects:

- `.aura/tmp/**`;
- `scripts/.tmp/**`;
- `*_TEMP.md`;
- workflow names containing `materialize`, `bootstrap`, `publisher`, or `trigger`;
- `*-temp.yml`, `*_temp.yml`, and YAML equivalents.

Normal permanent workflows remain allowed.

## Recommended external-agent workflow

```text
1. Read main and resolve its exact SHA.
2. Choose a new feature branch for a new PR.
3. Prepare and verify the local Arena change.
4. Compile the GitHub publication contract.
5. Execute one atomic publication.
6. Trigger Codex repeatedly as needed.
7. Trigger CodeRabbit once after the source stabilizes.
8. Apply accepted findings through update-mode atomic commits.
9. Regenerate and verify CODEMAP on the final source head.
10. Prepare the exact-head merge packet.
11. Merge only after explicit human instruction.
```

Do not reuse a branch whose previous PR has already merged. Do not use a temporary workflow as a shell surrogate when direct publication is available.

## Focused validation

```bash
python3 -m py_compile \
  aura_agent_arena_github_bridge.py \
  aura_agent_arena_github_mcp.py \
  tests/test_aura_agent_arena_github_bridge.py

python3 -m pytest -q tests/test_aura_agent_arena_github_bridge.py
```

The focused tests cover deterministic contracts, sorted tree entries, single-tree/single-commit publication, exact-base races, temporary workflow rejection, explicit merge gates, private payload suppression, and idempotent MCP registration.
