# Arena Navigation, Sub-Arenas and Domain-Lens Memory Sharding

> **Status:** staged reference architecture / non-production / test required.

The current Aura work treats the **Root Arena as an organizing and navigation substrate**, not merely a disposable execution environment. A Python venv, container, local process, provider call or swarm worker is one realization inside an Arena; it is not the Arena's durable identity.

```text
objective
→ Root Arena L0
→ AuraOS navigation order
→ candidate Sub-Arenas
→ hard dependency closure
→ domain/scope mask
→ minimum L0-L4 hydration
→ deterministic work / model / swarm only when earned
→ Construct / Challenge / Verify
→ affected-cone update
→ HyperDrive collapse
→ SuccessorFrame + exact reopen handles
```

## Stable Arena addresses

Every admitted material project, finding, tool, domain or durable idea should receive a stable semantic address:

```text
tp://arena/<arena_sid>/subarena/<semantic_sid>
```

A current manifest is versioned separately:

```text
<stable address>?g=<generation>&head=<manifest_digest_16>
```

A newly surfaced idea may begin as `UNBOUND_STAGING_PORTAL`; activation requires source/currentness/authority binding.

`ADDRESS != AUTHORITY` and `PORTAL != SOURCE COPY`.

## One source, many domain-lens shards

Domain-specific memory should be a projection over one canonical source object, not duplicated truth:

```text
DomainLensShard(o,d,q) =
<object SID,
 domain SID,
 source generation,
 relation subset,
 salience prior,
 residency projection,
 L0-L3 projection,
 L4 exact reopen,
 invalidators,
 authority ceiling>
```

The same object may be HOT for one domain and COLD for another:

```text
rho_t(o | domain, objective)
  ∈ {HOT, WARM, COLD, TRANSIENT, FENCE, BLOCK}
```

Salience changes routing/attention, not truth. Cross-domain composition may reveal a useful path that was low-salience under either lens alone, but any new relation remains a candidate until exact source or independent evidence verifies it.

## Temporal composition

The staged Temporal Arena keeps time separate from domain salience:

```text
ARENA STATE = SEMANTIC GRAPH × TEMPORAL GRAPH × SOURCE/CURRENTNESS × AUTHORITY
```

Something that is normally cold for a domain may become operationally hotter because it is READY/DUE/ACTIVE. That changes scheduling/hydration, not source truth or authority.

## 27-trit boundary

The source lineage reviewed for this staging pass establishes ternary 27-cell clusters (`3^3=27`) and a scale with **27-trit** logical address depth (`3^27` states). It does **not** establish a canonical 27-binary-bit semantic identity.

The reference therefore uses:

```text
K27(object, domain) ∈ {0,1,2}^27
```

only as a partition/locality hint. Stable semantic SID + generation + source binding remain identity. Collisions fail closed to semantic disambiguation.

## AuraOS navigation contract

A hosted model should be able to ask AuraOS for a D0 map instead of reconstructing Aura manually. A navigation response can contain:

- current root/head;
- candidate portals;
- hard dependency closure;
- lateral overlaps;
- selected domain lenses and scoped shards;
- bounded `ArenaNowCapsule` reference;
- L0/L1 packets and exact L4 reopen handles;
- source/currentness/authority state;
- relevant scripts/equations/capabilities;
- Triadic role recipe;
- HyperScale worker recommendation;
- active residuals and receipts.

A navigation order or command document is **not** execution proof.

## Current reference witness

A fresh Python 3.13.5 venv plus independent Node 22.16.0 exact 27-trit lane passed **13/13** bounded gates. The sample `RESOLVE_NAVIGATION` objective reduced eligible domain-lens projections to **24 of 96** possible before detailed traversal.

The tests cover one-source/many-lenses, domain-specific residency, stable address vs manifest head, reverse affected-portal invalidation, 27-trit width/parity, distinct domain neighborhoods, source-grounded cross-domain paths, scope-before-routing, AuraOS/swarm/reopen surfaces, preservation of the Temporal Arena axis, collision fail-closed behavior and rejection of unsupported lens relations.

**Claim ceiling:** This is a reference routing/sharding implementation, not proof of production AuraOS navigation, complete mapping of all Aura artifacts, causal cognitive superiority, a canonical 27-bit encoding or live DeepSeek/C81 execution.

## Falsification target

Hold evidence fixed and compare neutral, single-domain A, single-domain B, dual A+B, misleading/adversarial lens and source-only verifier conditions. Measure valid unique relations, unsupported relations/false analogy, source fidelity, context bytes, latency/cost, affected-cone size and fresh-worker continuation. Promote the lens mechanism only if the verified benefit survives those controls.
