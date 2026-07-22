# Aura Architecture Harness — Atomic Git-Tree Routing

**Version:** `AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING_V3`  
**Recorded:** July 22, 2026  
**Proven during:** AuraOS PR #184

This is the reusable publication route used when an external coding agent has already
validated a multi-file patch but GitHub's file-by-file Contents API or pull-request
workflow semantics would expose partial commits or fail to execute a branch-new
publisher. The companion implementation is
`aura_architecture_harness_git_tree_routing.py`.

## Discovery that led to the route

During PR #184, several temporary publisher workflows were added or materially changed
only on the pull-request branch. GitHub continued executing workflow definitions that
were registered from the base branch. This is expected for `pull_request` workflows:
the trusted workflow definition comes from the base branch, so a new job that exists
only on the PR branch is not a reliable way to publish that same PR's source.

The GitHub connector's commit-workflow lookup also surfaced pull-request-triggered runs
but did not reliably expose branch `push` runs. That made workflow transport a poor
source of truth for a time-sensitive, multi-file publication.

The atomic Git-object route removed both problems.

## Exact route

1. **Resolve the live PR identity and tree.** Read the PR and require an open state,
   the expected head branch, and an exact expected head commit SHA. Resolve that commit's
   exact tree SHA separately. Any commit or tree drift aborts the route.
2. **Create immutable blobs.** Create one Git blob per already-validated file. Record the
   local SHA-256, byte length, mode, returned Git blob SHA, and exact path allowlist.
3. **Create one tree.** Call `create_tree` with the exact tree SHA resolved from the
   PR head commit as `base_tree_sha`. Never substitute the commit SHA for the tree SHA.
   Include every addition/replacement and every cleanup deletion in the same tree.
4. **Create one commit.** Point one new single-parent commit at that tree, with the exact
   prior PR head as its parent.
5. **Fast-forward the PR branch.** Move only the PR branch ref to the new commit with
   `force=false`. Never update the base branch and never force-rewind a branch.
6. **Verify the result.** Re-read the PR, require the new head, compare the changed-file
   allowlist, prove temporary transport files are absent, run the final validation gate,
   regenerate CODEMAP/topology from the final tree, and leave merging to a separately
   authorized human-reviewed action.

```text
get_pr_info(expected head commit)
  → fetch_commit(expected head commit; resolve exact tree SHA)
  → create_blob(file 1..N)
  → create_tree(base_tree_sha = resolved head tree; replacements + deletions)
  → create_commit(parent = exact head commit)
  → update_ref(PR branch, force = false)
  → verify PR head, diff allowlist, tests, cleanup, CODEMAP
```

## Why this is safer than sequential file writes

The Contents API creates a commit for each file update. A four-file logical change can
therefore expose one, two, or three files before the fourth arrives. Git objects are
immutable and unattached until the ref moves: blobs and a tree can be assembled first,
then exposed through one commit and one fast-forward update. Before `update_ref`, a
failure leaves the branch unchanged.

## Required safety gates

- exact expected PR head commit SHA, resolved tree SHA, and branch;
- canonical repository-relative POSIX paths only;
- explicit addition/replacement and deletion allowlists;
- regular blobs only (`100644` or `100755`), never symlink blobs;
- SHA-256 and byte-length binding for every local file;
- one-parent commit rooted at the exact previous head;
- `force=false` ref update;
- temporary payload/workflow cleanup in the same tree;
- final-tree tests, CODEMAP regeneration, and topology verification;
- no automatic merge, base-branch update, production authority, or bypass of human
  review.

## Authority boundary

The harness records and validates the route. It does **not** call GitHub or authorize a
mutation by itself. Execution requires an external authorized GitHub connector and a
specific user-approved coding task. A successful publication does not authorize merge,
physical action, payment, production mutation, or any other consequential authority.
