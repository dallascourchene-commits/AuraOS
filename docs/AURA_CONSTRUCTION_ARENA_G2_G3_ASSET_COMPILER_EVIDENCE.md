# Aura Construction Arena BIM/Gaussian Demo — G2/G3 Asset Compiler Evidence

```yaml
document_status: G2_G3_IMPLEMENTATION_COMPLETE_REAL_BUILD_PENDING
source_main_sha: 489baef6fc9c0363d5b71c4080efcb7c234e5a39
source_plan_sha256: 03f4cab34822b3cc24cf640b41702a23aeaae511e997231a0e2bc5e596703705
source_ifc_sha256: 29945f654c636d758a95b66eb0e107ec35afc7e1c7857a7ff652586e7728ba29
source_preflight_digest: 02cfdd9469b1a05d21818d78afd00872
focused_asset_tests: 43
focused_asset_tests_passed: 43
authoritative_ifcopenshell_build_completed: false
real_ifcconvert_outputs_completed: false
real_spz_v4_outputs_completed: false
asset_pack_compiled: false
runtime_external_fetch: false
survey_authority: false
production_mutation: false
human_review_required: true
```

## Scope completed

G2 and G3 now provide the deterministic, fail-closed implementation required to turn the pinned
fictional TU Wien IFC into a content-addressed Construction demo asset pack. The source code,
tests, receipts, preflight evidence, dependency records, and operational limitations are all
visible in draft PR #183.

This checkpoint deliberately separates two claims:

1. **Compiler implementation is complete and focused-test verified.**
2. **The real production-like asset build has not yet run**, because this environment cannot
   install or transfer the approved IfcOpenShell/IfcConvert and Niantic SPZ build artifacts.

No GLB, SVG, PLY, SPZ, hierarchy, or asset-pack output is claimed as real until the external tools
run against the pinned IFC and every result passes Aura's existing importers and budgets.

## G2.1 — deterministic IFC hierarchy

Added `scripts/aura_ifc_storey_index.py` with two explicit layers:

- a dependency-free STEP text preflight that reads only `IfcBuildingStorey` identity, name,
  elevation, and entity number;
- an authoritative IfcOpenShell index that requires exactly one project and building, validates
  the full storey hierarchy, enumerates bounded spaces/elements, rejects duplicate GlobalIds, and
  must exactly agree with the preflight storeys.

The STEP scanner is labelled `STEP_TEXT_PREFLIGHT_ONLY`; it is not a geometric parser, survey
surface, importer substitute, or Construction truth owner.

### Real pinned preflight

The exact 7,404,420-byte source produced five deterministic storeys:

| Ordinal | Name | Elevation | IFC GlobalId | Aura storey ID |
|---:|---|---:|---|---|
| 0 | Floor -1 | -2.89 m | `3iYgqg1iW7IP9$nzwL7fTz` | `storey-c4ed039f8f87f818a047` |
| 1 | Floor 0 | 0.00 m | `2jkqT_bFr2PPoKaVDCZO3n` | `storey-733f578aa27f76d590cd` |
| 2 | Floor 1 | 3.40 m | `2XKWmrdx1A59SqqZcu7d_j` | `storey-745ba20f310172ee5d1a` |
| 3 | Floor 2 | 6.29 m | `3nSDuHNnTFoQVPVw1eWgAt` | `storey-812507efb7103814cdff` |
| 4 | Floor 3 | 9.18 m | `1XToyD5eb608eIvc$niOb6` | `storey-a364f94c2d7f03c41367` |

The preflight receipt is committed at
`demo_assets/construction_tuwien/source/source-preflight.json` and remains explicitly pending
IfcOpenShell agreement.

## G2.2 — split, convert, verify, and resume

Added or extended:

```text
scripts/aura_prepare_construction_demo_assets.py
scripts/aura_verify_construction_demo_assets.py
tests/test_aura_prepare_construction_demo_assets.py
tests/test_aura_verify_construction_demo_assets.py
```

The orchestrator supports independently resumable phases:

```text
split → convert → gaussian
```

### Storey splitting

- invokes only IfcPatch `SplitByBuildingStorey`;
- does not trust upstream filenames;
- reopens every output with IfcOpenShell;
- requires exactly one storey per split IFC;
- binds the observed GlobalId back to the canonical Aura storey ID;
- requires complete, unique coverage of the authoritative hierarchy;
- copies atomically into canonical per-storey directories;
- writes a content-addressed split receipt.

### GLB/SVG conversion

- invokes an explicit regular executable path for IfcConvert;
- bounds workers, timeout, stdout, stderr, environment, and output bytes;
- writes to `.partial` files and removes incomplete outputs on any failure;
- rechecks every split IFC digest before conversion;
- verifies GLB v2 headers, declared length, finite JSON, and embedded-only resources;
- sanitizes SVG XML and rejects scripts, foreign objects, event handlers, DOCTYPE/entities,
  external links, data URLs, JavaScript URLs, and file URLs;
- writes one command/verification receipt per output plus a phase receipt.

The verifier is intentionally stricter than a file-extension check. It never turns demo inputs
into trusted survey or Construction state.

## G3 — deterministic degree-0 Gaussian compiler

Added `scripts/aura_mesh_to_gaussian.py` and focused tests.

### Geometry path

- validates the source GLB before sampling;
- loads the complete GLB scene through `trimesh` without repair-driven mutation;
- traverses scene instances in stable node-name order;
- bakes each node transform into copied geometry before concatenation;
- rejects non-finite vertices, invalid indexes, empty meshes, and degenerate triangles;
- allocates samples proportional to triangle area with deterministic remainder assignment;
- uses a seed derived from source digest, profile, and admitted count;
- emits stable triangle/sample order.

### Gaussian attributes

For every admitted sample the compiler emits:

- Float32 position and unit normal;
- normalized XYZW quaternion aligning the Gaussian local axis to the surface normal;
- positive bounded anisotropic log-scale;
- bounded pre-sigmoid opacity;
- deterministic RGB colour;
- source-triangle identity;
- exact representation digest.

The initial representation has SH degree 0. The binary PLY records degree-0 DC colour fields and
an explicit `LUF` source coordinate comment. The Niantic SPZ bridge supplies an empty SH array,
sets `PackOptions.from_coord = CoordinateSystem.LUF`, requests version 4 where supported, and then
requires Aura's own SPZ v4 envelope inspector to confirm point count and SH degree before atomic
publication. Stored SPZ coordinates are recorded as canonical `RUB`.

### Density ceilings

```yaml
LOW:
  STOREY: 50000
  BUILDING: 150000
STANDARD:
  STOREY: 150000
  BUILDING: 500000
VIDEO:
  STOREY: 300000
  BUILDING: 1000000
```

These are generation ceilings, not admission promises. Aura's existing SPZ importer, allocation
preflight, device profile, GPU budget, frame budget, accessible fallback, and disposal contracts
remain authoritative. A generated output must be reduced deterministically or rejected; no demo
bypass exists.

## Gaussian orchestration

The `gaussian` phase consumes only validated GLB rows from the conversion receipt. It:

- rechecks every GLB SHA-256;
- requires one unique full-building mesh job;
- distinguishes `BUILDING` and `STOREY` ceilings;
- emits both `.gaussian.ply` and `.spz` for every GLB;
- binds each Gaussian receipt to the exact source GLB receipt;
- records LUF→RUB conversion and degree-0 representation identity;
- writes `receipts/compile-gaussians.json` for safe takeover/resume.

## Verification

The focused foundation command covers:

```text
tests/test_aura_construction_demo_contracts.py
tests/test_aura_fetch_construction_demo_source.py
tests/test_aura_ifc_storey_index.py
tests/test_aura_verify_construction_demo_assets.py
tests/test_aura_prepare_construction_demo_assets.py
tests/test_aura_mesh_to_gaussian.py
```

Local result: **43 passed**.

The tests prove:

- contract and nested-digest tamper detection;
- source consent, containment, hash, size, redirect, cleanup, and offline-reuse boundaries;
- deterministic storey identity/order and fake IfcOpenShell agreement;
- duplicate/mismatch/budget rejection;
- arbitrary IfcPatch filenames mapped to canonical IDs;
- bounded command timeout and nonzero-exit receipts;
- GLB and SVG admission/sanitization;
- deterministic sampling and binary PLY bytes;
- transformed GLB scene instances;
- finite normals/scales/rotations and normalized quaternions;
- seed sensitivity and source-digest binding;
- degree-0 SPZ bridge arrays and explicit coordinates;
- SPZ envelope mismatch cleanup;
- building/storey profile separation;
- resumable Gaussian phase receipts.

GitHub's exact branch CI compiled and fatal-linted the governed source successfully on Python 3.10
and 3.12. The first broad-suite run stopped during collection because its workflow did not install
`jsonschema`; the JUnit artifact contained one collection error and zero test failures. That CI
dependency was corrected in an isolated commit. A dedicated Construction asset-foundation job is
the required exact-branch verification for these 43 tests.

## External toolchain boundary

The approved build dependencies are not Aura runtime dependencies:

- IfcOpenShell / IfcPatch / IfcConvert;
- NumPy and trimesh;
- Niantic SPZ v3.0.0 source/API producing SPZ v4 payloads.

The current internal Python package mirror does not contain the pinned IfcOpenShell release. The
official CPython 3.13 Linux wheel exists and was identified by its published digest, but this
execution environment blocked wheel/ZIP transfer. The real authoritative index, split IFCs,
IfcConvert GLB/SVG outputs, and Niantic SPZ outputs therefore remain pending.

This limitation must not be bypassed by:

- accepting STEP preflight as authoritative hierarchy;
- substituting an unpinned converter;
- weakening source or output digests;
- generating placeholder assets and labelling them real;
- bypassing Aura's GLB/SPZ importers;
- beginning the full Construction fixture/UI against unverified geometry.

## G2/G3 exit disposition

```yaml
compiler_source_complete: true
focused_test_evidence_complete: true
source_preflight_complete: true
authoritative_hierarchy_complete: false
real_storey_split_complete: false
real_glb_svg_complete: false
real_gaussian_ply_spz_complete: false
aura_import_validation_complete: false
immutable_asset_pack_complete: false
proceed_to_g4_full_fixture: false
next_action: run approved external toolchain and compile the real content-addressed asset pack
```

The coding plan's gate remains in force: do not begin the full UI or canonical synthetic project
fixture until the complete asset pack is reproducible, offline at runtime, content-addressed, and
accepted by Aura's existing import paths.
