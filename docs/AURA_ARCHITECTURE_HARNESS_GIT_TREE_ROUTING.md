# Aura Architecture Harness — Atomic Git-Tree Routing

**Version:** `AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING_V4`  
**Recorded:** July 22, 2026

The route is proposal-only and must be executed by an external authorized connector after human review.

```text
get_pr_info(exact head commit)
→ fetch_commit(derive and bind exact tree SHA from that commit response)
→ create_blob(validated files)
→ create_tree(base = bound tree SHA; exact replacements and deletions)
→ create_commit(parent = bound head commit SHA)
→ update_ref(PR branch, force = false)
→ verify exact head, allowlist, deletions, tests, and unmerged state
```

A commit SHA and tree SHA are never accepted as unrelated caller-supplied identities. `VerifiedHeadBinding.from_fetch_commit` derives both from one exact connector response and rejects commit drift or a commit-as-tree substitution.

The recorded PR #184 case study is the manual remediation publication from parent `7207c2bf6ab179d6af41ca4ed6b9f5adcce1b307` and bound tree `359a19f26aa3f4066c51263965709c8b026eae6c` to commit `ea9675ada226bae31fbd74e10dced81797aac1a8`. It documents atomic review remediation, not G4 payload cleanup.

Safety requirements:

- canonical repository-relative POSIX paths only;
- exact SHA-256 and byte-length binding per regular-file blob;
- one verified commit/tree binding;
- one-parent commit;
- non-forced fast-forward of the PR branch only;
- no base-branch update, automatic merge, or production authority;
- every listed deletion must be absent in the final tree;
- human review remains mandatory.
