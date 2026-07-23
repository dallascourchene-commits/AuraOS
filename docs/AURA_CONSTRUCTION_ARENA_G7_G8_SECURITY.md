# Construction Arena G7–G8 Local Security Boundary

The cinematic demo server is local-only and presentation-only.

It serves only:

- the approved `aura_spatial_web/` browser surface;
- generated Construction demo assets under `demo_assets/construction_tuwien/generated/`;
- the deterministic `/api/construction-demo` packet.

It rejects path traversal, encoded traversal, backslash paths, NUL-containing paths, and all other repository locations. Responses carry no-store caching, content-type hardening, a no-referrer policy, and a restrictive Content Security Policy.

The exact local static boundary is regression-tested before final review, exact-head verification, and merge.

The server grants no Construction, filesystem-mutation, payment, access, professional, legal, regulatory, survey, publication, or merge authority.
