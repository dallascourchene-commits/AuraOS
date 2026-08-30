# AWJ032 GLM-5.3 G3 host preflight reducer

This branch adds a deterministic reducer only. It does **not** benchmark a host,
materialize GLM-5.3 weights, or admit G3/G4 by itself.

The reducer consumes command-bound host measurements and the preregistered expert
I/O floor from GLM53-02:

- routed expert floor: 22.6492416 GB/token;
- shared expert floor: 2.8311552 GB/token;
- aggregate cold expert floor: 25.4803968 GB/token.

For each caller-supplied target seconds/token it reports separate routed-expert
reuse requirements for a resident shared-expert assumption and a cold shared-
expert assumption. Missing non-storage time or fixed non-expert byte costs are
represented only as an explicitly optimistic lower-bound case, never as measured
zero.

Formal G3 admission remains dependent on `HARD_FALSE_PROVEN` at G1 and the G2
tiny-fixture PASS. Storage fit never admits G4. The intended next host action is
to collect the exact RAM/disk/I/O/power/accelerator measurements required by the
AWJ032 G1-G3 and GLM53-02 work orders, then feed that receipt to this reducer.
