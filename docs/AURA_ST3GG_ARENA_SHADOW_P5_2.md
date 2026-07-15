# Aura Arena ST3GG V2 Shadow Compatibility — P5.2

## Scope

P5.2 dual-projects exactly one live exact-recall writer, `aura_arena_st3gg_codec.py`, into the canonical P5.1 ST3GG V2 contracts. The migration is opt-in and shadow-only.

The existing V1 function, packet bytes, recall ledger, retrieval path, Coding Arena callers, and patch-authority boundary remain unchanged.

## Entry point

```python
from aura_arena_st3gg_shadow import encode_arena_capsule_with_v2_shadow

result = encode_arena_capsule_with_v2_shadow(capsule)
live_v1 = result.legacy_capsule
shadow_v2 = result.comparison
```

`live_v1` is the exact result returned by the unchanged V1 writer. `shadow_v2` is a deterministic comparison record and cannot execute, authorize, rewrite recall, or alter the V1 packet. Once V1 succeeds, an unexpected shadow exception is converted into a disabled V2 comparison rather than being allowed to suppress the V1 result.

## Exact-recall admission

A V2 `EXACT_RECALL` projection is accepted only after all of the following are verified:

1. The V1 capsule version, mode, enabled reason, retrieval marker, and visible-ASCII packet are canonical.
2. The caller capsule reproduces the V1 canonical original JSON and SHA-256 digest.
3. The V1 raw/final token estimates and savings ratio are recomputed from the actual original and emitted packet.
4. The V1 phase hash is recomputed from the exact version, mode, packet, original digest, and complete V1 decision.
5. The persisted V1 record is independently recoverable through both the emitted pointer and original-digest alias, and both aliases resolve to the same record.
6. The record's pointer, dash key, glyph, holographic header, digest, content type, source hint, exact original, and compressed packet are internally consistent.
7. The exact V1 original matches the caller capsule byte-for-byte.
8. The complete canonical V2 metadata suffix is included in the final unit count.
9. The V2 savings threshold still passes after that overhead.
10. The canonical V2 persistence receipt is logically bound to the already-verified V1 record; no duplicate record is written.

Any failure disables only the V2 projection. The already-produced V1 result is returned unchanged.

## Comparison record

`ArenaST3GGV2ShadowComparison` exposes:

- the complete immutable V1 decision plus pointer, original digest, payload digest, exact-record identity, transmitted units, and recomputed savings;
- the canonical V2 `ST3GGDecision`, decision digest, pointer, exact reference, restoration mode, overhead, and measured savings;
- exact-recall verification state and deterministic mismatch reasons;
- immutable constitutional fields proving shadow-only, proposal-only, V1-storage ownership, and zero ST3GG patch authority.

## Explicit non-goals

P5.2 does not migrate or alter:

- `aura_st3gg_codec.py`;
- `aura_st3gg_recall.py`;
- `aura_arena_st3gg_egress.py`;
- Coding Arena, Builder, providers, routers, public CLI, authorization, Model Cognome, or QDKT;
- existing recall records or live V1 egress bytes.

## Verification

The focused matrix runs on Python 3.10 and 3.12 and includes:

- syntax compilation and Ruff fatal/static correctness checks;
- a hard-coded golden V1 packet plus direct-versus-wrapper byte equality;
- enabled V2 exact-recall projection over a large Arena capsule;
- forced shadow-projection crashes proving the live V1 result still returns unchanged;
- missing and stale record rejection;
- pointer and digest-alias substitution rejection;
- digest disagreement and non-canonical record metadata rejection;
- forged V1 version/mode, phase-hash, and measurement rejection;
- empty compact-output rejection;
- proof that canonical overhead can disable V2 without disabling or modifying V1;
- deterministic comparison digests, complete V1 decision evidence, and unchanged authority flags;
- all existing Arena V1 and P5.1 canonical contract tests.

Issue: #112. Epic: #93.
