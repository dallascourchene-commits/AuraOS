# Aura Agent Bridge — Atomic GitHub Publication

## Purpose

This lane replaces temporary GitHub Actions materializer/bootstrap/publisher
workflows with a bounded GitHub API path whose commit and branch update are a
single server-side compare-and-swap operation. The GraphQL
`CommittableBranch` input uses the exact `branchName` field with an unqualified
branch name.

```text
exact base/head/PR evidence
  → bounded canonical change manifest
  → fresh snapshot branch (create mode only)
  → GraphQL createCommitOnBranch(expectedHeadOid)
  → existing or newly created pull request
  → review and verification
  → separately authenticated human merge action
```

The implementation is in:

- `aura_agent_arena_github_bridge.py`;
- `aura_agent_arena_github_mcp.py`;
- `tests/test_aura_agent_arena_github_bridge.py`.

## Why this is better

The former workaround encoded source or patches into temporary files, committed
a workflow trigger, waited for Actions to materialize the payload, and then
deleted the transport artifacts. It introduced extra commits, temporary
workflow authority, stale-head races, cleanup obligations, and review noise.

The retained lane now uses GitHub GraphQL `createCommitOnBranch`. Its
`expectedHeadOid` input makes commit creation and branch advancement one
server-side compare-and-swap operation. A concurrent branch change causes the
mutation to fail rather than publishing from a stale parent.

No local `git add`, staging directory, shell push, encoded archive, or temporary
workflow is required. This lane rejects every caller-supplied path under
`.github/workflows/`, regardless of filename, and accepts only exact schema
literals and types for change operation, encoding, and mode.

## Agent Bridge tools

```text
aura_github_prepare_publication
aura_github_execute_publication
aura_github_prepare_merge
```

### `aura_github_prepare_publication`

The contract binds:

- repository and create/update mode;
- base and feature branches;
- exact base snapshot SHA;
- exact expected feature-branch parent SHA;
- exact PR number in update mode;
- bounded canonical additions and deletions;
- commit and PR metadata;
- explicit publication authorization.

All additions are sent to GraphQL as RFC 4648 Base64. UTF-8 byte length is
counted incrementally before allocating the encoded payload, including
multibyte code points. Caller Base64 is bounded before ASCII conversion or
decoding and is retained only after strict validation. Limits remain 4 MiB per
decoded file and 32 MiB per publication.

`createCommitOnBranch` does not expose executable-bit mutation, so this lane
accepts regular files (`100644`) only. Executable-mode changes must use a
separately reviewed publication mechanism.

### Create mode

1. Confirm `expected_parent_sha == expected_base_sha`.
2. Confirm the proposed feature ref does not exist.
3. Confirm no historical PR used that branch name.
4. Create the fresh feature ref at the immutable provenance snapshot
   `expected_base_sha`.
5. Run `createCommitOnBranch` on that feature ref with
   `expectedHeadOid=expected_base_sha`.
6. Create the PR.
7. If the mutation or PR creation fails, do not issue an automatic ref DELETE.
   GitHub deletion has no expected-OID compare-and-swap, so a GET-then-DELETE
   could remove a newer writer's commit. Return durable recovery evidence with
   the expected and observed SHA for a trusted operator to revalidate.

The base branch may advance after the snapshot is taken. The guarantee is exact
provenance from `expected_base_sha`, not a false claim that mutable `main`
remains locked.

### Update mode

1. Require the exact existing PR number.
2. Verify the PR is open and unmerged.
3. Verify exact base/head refs and exact `expected_parent_sha`.
4. Verify both PR head and base repositories equal `repository_full_name`;
   fork publication is unsupported and fails closed.
5. Run `createCommitOnBranch` with
   `expectedHeadOid=expected_parent_sha`.
6. Do not PATCH PR metadata after publication. The existing PR follows its
   feature ref automatically.

## Transport security

- token source: operator-controlled `AURA_GITHUB_TOKEN` only;
- token is never accepted through MCP arguments;
- REST and GraphQL are pinned to `https://api.github.com`;
- urllib redirects are disabled before the bearer token is sent;
- redirect-capable opener injection is not supported;
- malformed UTF-8 response bodies become fail-closed publication errors;
- responses are bounded to 8 MiB;
- no shell execution is used.

## Merge boundary

`aura_github_prepare_merge` is evidence-only. MCP callers cannot assert human
merge authority. The tool may return:

```text
READY_FOR_TRUSTED_HUMAN_AUTHORIZATION
```

after checks, review threads, and CODEMAP evidence pass, but it always returns:

```yaml
merge_authority: false
connector_tool: null
connector_arguments: null
automatic_merge: false
```

The actual `GitHub.merge_pull_request` call remains a separate trusted action
initiated by Dallas and bound to the reviewed `expected_head_sha`.

## Authority boundaries

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
publication_requires_explicit_authorization: true
graphql_compare_and_swap: true
automatic_merge: false
merge_authority_in_mcp: false
force_ref_update: false
human_review_required: true
```

## Focused validation

```bash
python3 -m py_compile \
  aura_agent_arena_github_bridge.py \
  aura_agent_arena_github_mcp.py \
  tests/test_aura_agent_arena_github_bridge.py

python3 -m pytest -q tests/test_aura_agent_arena_github_bridge.py
```

The focused suite covers deterministic contracts, schema/runtime parity,
pre-encoding and pre-decoding bounds, GraphQL `branchName` variable shape,
same-repository PR binding, CAS rejection, create-mode recovery evidence,
no update-mode PR PATCH, redirect rejection, malformed UTF-8 response handling,
strict delete payload parity, private/public payload integrity, evidence-only
merge output, and idempotent MCP registration. The current focused suite passes
**33 tests**.
