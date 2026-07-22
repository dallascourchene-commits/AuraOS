# Aura Architecture Harness — Atomic Git-Tree Routing

**Version:** `AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING_V5`  
**Recorded:** July 22, 2026

This component emits **untrusted, proposal-only routing data**. The executing
authorized GitHub connector must independently re-fetch the live pull request
and exact head commit before object creation, and must re-fetch the pull request
again immediately before a non-forced ref update.

```text
get_pr_info(bind repository, PR, head ref, base ref, head SHA)
→ fetch_commit(bind exact tree SHA)
→ create_blob(validated additions/replacements; optional for deletion-only route)
→ create_tree(base = independently re-fetched tree SHA)
→ create_commit(parent = independently re-fetched head SHA)
→ get_pr_info(revalidate exact non-base head immediately before publication)
→ update_ref(verified PR head branch, force = false)
→ verify exact final head, allowlist, deletions, tests, maps, and unmerged state
```

## Binding rules

`PullRequestRouteBinding.from_connector_metadata` derives repository identity,
PR number, open/unmerged state, head ref, base ref, head SHA, and tree SHA from
one normalized PR response plus the matching commit response. The head and base
refs must differ.

Factory construction reduces accidental fabrication, but the object is not an
authentication capability. Serialized or in-process proposal data is never
trusted by itself; the executing connector must independently re-fetch and
compare all fields.

## Path rules

- canonical repository-relative POSIX paths only;
- exact SHA-256 and byte length for each regular-file blob;
- `100644` and `100755` modes only;
- no exact replacement/deletion overlap;
- no case-folded or NFC/NFD-equivalent aliases;
- no file path that is also an ancestor of another proposed path;
- deletion-only routes are supported;
- a completely empty route is rejected.

## Historical case study

`pr184_atomic_publication_case_study()` records independently checked object
identifiers from the July 22, 2026 manual review-remediation publication:

- parent commit: `7207c2bf6ab179d6af41ca4ed6b9f5adcce1b307`
- resolved parent tree: `359a19f26aa3f4066c51263965709c8b026eae6c`
- created tree: `beed4f512975dd304ff36aa7e2936bf2212cead1`
- created commit: `ea9675ada226bae31fbd74e10dced81797aac1a8`

The case study is explicitly **non-replayable**. It contains no synthetic
placeholder blob, no route digest, and no claim that its digest proves the
actual published bytes. Its scope is review remediation, not G4 payload cleanup.

## Authority boundary

The routing component performs no GitHub mutation itself. It grants no force
update, base-branch update, automatic merge, production mutation, deployment,
physical-work, payment, survey, professional, legal, or regulatory authority.
Human review remains mandatory.
