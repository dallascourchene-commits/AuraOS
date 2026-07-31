# Standalone Construction + Pascal Spatial Foundry Demo

## Purpose

This is the dedicated Construction presentation entry point. It does not use the Civic, Human Agent, Observatory, or Crucible showcase document as its page shell.

The page composes the existing canonical owners:

- P2 pinned Pascal 2D/3D workbench;
- P3 Construction Design, Floor Plan, As-built, and Compare decision lane;
- P4 deterministic fifteen-chapter Director and bounded repair/reproof sequence.

No duplicate Construction truth, renderer truth, evidence, authority, runtime, rollback, archive, or learning owner is introduced.

## Launch

From a clean AuraOS checkout:

```bash
python aura_construction_pascal_spatial_foundry_standalone_server.py \
  --repo-root . \
  --host 127.0.0.1 \
  --port 8768
```

Open:

```text
http://127.0.0.1:8768/
```

The root page should show:

- the standalone Aura Construction header;
- the P4 Director controls;
- the P3 Construction view controls;
- the actual pinned Pascal workbench canvas in Design and Floor Plan modes;
- the Aura-derived as-built canvas in As-built mode;
- both renderers in Compare mode;
- Construction evidence, obligations, candidates, and the human decision packet.

The old combined Aura showcase remains available only as an explicit compatibility route:

```text
http://127.0.0.1:8768/legacy-showcase
```

## Readiness checks

```bash
curl -fsS http://127.0.0.1:8768/api/construction/director/status \
  | python3 -m json.tool
```

Verify the standalone document, rather than the prior Civic page:

```bash
curl -fsS http://127.0.0.1:8768/ \
  | grep -F 'data-aura-surface="CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY"'
```

Verify the real owner surfaces are present:

```bash
curl -fsS http://127.0.0.1:8768/ \
  | grep -E 'construction-foundry-director|construction-decision-foundry|pascal-construction-foundry'
```

## Operation

Use the P3 view controls to inspect the product directly:

- **Design** uses Pascal’s 3D building working copy.
- **Floor Plan** uses Pascal’s 2D floor-plan view.
- **As-built** uses Aura’s derived Construction renderer.
- **Compare** displays Pascal design and Aura as-built side by side.

Use the Director’s **Next** control for the guided fifteen-chapter demonstration. The Director remains responsible for consequential chapter order; the view controls are presentation controls only.

## Generated navigation

Changes to the standalone server, presentation stylesheet, runtime profiles, tests, or this guide require the trusted CODEMAP and topology synchronization lane before merge. Generated navigation artifacts are not hand-edited.

## Authority boundary

The standalone page remains projection-only. It does not authorize physical work, professional approval, payment, access, deployment, merge, or automatic learning promotion. Human review remains required.
