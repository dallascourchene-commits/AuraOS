# Arena Navigation / Domain-Lens Reference

This is a **bounded reference implementation**, not the canonical AuraOS runtime.

It demonstrates four staged ideas:

1. stable Sub-Arena semantic addresses are separate from versioned generation/head;
2. one canonical source object can have multiple domain-lens projections without duplicating truth;
3. the same object can be HOT/WARM/COLD differently by domain while exact L4 source remains shared;
4. a 27-trit (`{0,1,2}^27`) key may serve as a locality/shard hint without becoming semantic identity or authority.

Run:

```bash
python -m venv .arena-nav
# activate .arena-nav for your shell
python domain_lens_reference.py
```

Node 22+ is required for the independent 27-trit parity lane.

Expected current bounded result: `13/13 PASS_NONPROMOTING_REFERENCE`.

The reference preserves the staged Temporal Arena as a separate navigation axis: due/ready/current state may change operational residency or scheduling, but does not change source truth or authority.

For the architecture and claim boundary, see `docs/ARENA-NAVIGATION-DOMAIN-LENS-SHARDING.md`.
