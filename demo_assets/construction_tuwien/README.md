# TU Wien Construction Arena Demo Assets

This directory owns the reproducible source and generated representation pack for AuraOS's
synthetic Construction Arena demonstration. It does not own Construction project state,
schedule or financial truth, regulatory interpretation, professional release, renderer state,
or physical location truth.

## Source

The single geometric source is TU Wien's fictional IFC4 “Custom Test Model for Escape Route
Analysis in IFC format,” DOI `10.48436/a185k-86v39`, licensed under CC BY 4.0.

The source IFC is intentionally not fetched during Aura startup or demo runtime. An operator must
run the dedicated acquisition command, which accepts only the pinned TU Wien URL and verifies the
exact filename, byte length, published MD5, and Aura-pinned SHA-256 before writing locally.

```bash
python scripts/aura_fetch_construction_demo_source.py \
  --repo-root . \
  --output-dir demo_assets/construction_tuwien/source \
  --record-doi 10.48436/a185k-86v39 \
  --accept-network-download
```

## Planned generated pack

Each discovered storey receives an IFC slice, GLB mesh, sanitized SVG floor plan, deterministic
degree-0 Gaussian PLY, SPZ v4 representation, and manifest. Full-building GLB/PLY/SPZ,
hierarchy, element index, and one immutable asset-pack manifest are generated as well.

Generated assets remain local and content-addressed. The base IFC/mesh remains immutable source
geometry; work status, trade history, blockers, inspections, schedule, budget, and proposal state
are separate Aura projections.

## Authority boundary

```yaml
fictional_source: true
survey_authority: false
person_level_data_included: false
runtime_external_fetch: false
physical_work_authority: false
payment_authority: false
access_authority: false
professional_authority: false
legal_or_regulatory_authority: false
renderer_authority: false
production_mutation: false
human_review_required: true
```

See `ATTRIBUTION.md`, `LICENSE-CC-BY-4.0.txt`, and `source/source-manifest.json`.
