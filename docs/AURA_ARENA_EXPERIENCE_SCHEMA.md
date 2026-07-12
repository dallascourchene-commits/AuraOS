# Aura Arena Experience Schema

`ArenaExperienceV1` is the authoritative structured trace format recorded by Arena
workflows and mined by the proposal-only Phase B Crucible.

## Storage

The exact structured ledger uses SQLite WAL at:

```text
Aura_Memory/arena_experience.db
```

The path is runtime-local and should remain ignored. The ledger supports migrations,
idempotent writes, indexed queries, correlation IDs, sanitized JSONL export, and
content digests.

It does not replace:

- the Empirical Cost Observatory;
- symbolic trace memory;
- ST3GG recall ledgers;
- source files and hashes;
- verifier records;
- ephemeral lifecycle receipts.

Instead, it references their IDs and digests.

## Stored classes

A record includes:

- Arena, grammar, runtime, and compiler versions;
- task, workflow, and correlation IDs;
- state before and after;
- selected transition and outcome;
- repository commit and working-tree digest;
- source-hash collection digest;
- provider/model metadata when applicable;
- cost-run, trace-atom, and raw-evidence references;
- sanitized observable route, guard, capability, tool, verifier, and result payloads.

## Excluded content

The sanitizer removes or redacts:

- API keys;
- bearer tokens;
- passwords and secrets;
- authorization headers;
- private-key material;
- cookies;
- hidden chain-of-thought;
- scratchpads and private reasoning fields.

Aura stores observable short rationales, decisions, evidence, and outcomes—not hidden
model reasoning.

## Idempotency

Repeating the same `experience_id` with the same canonical digest is accepted as an
idempotent replay. Reusing the ID for different content fails closed with
`experience_id_digest_conflict`.

## Phase B Crucible boundary

The Phase B Arena Crucible may read complete schema-valid records and emit proposals.
It may not mutate an active grammar or runtime weight. Candidate output must terminate
at:

```text
CRYSTALLIZATION_PROPOSED
```

Every stored proposal requires verifier and human review. In Phase B, the only
supported candidate path is:

```text
soft_weight_profile.empirical_uncertainty
```

Hard guards, aliases, states, capabilities, risk declarations, verifier requirements,
and approval requirements are outside the Phase B learning surface.
