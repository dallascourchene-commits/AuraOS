# Aura Construction Arena BIM/Gaussian Demo — G1 Source and Contracts Evidence

```yaml
document_status: G1_COMPLETE
source_main_sha: 489baef6fc9c0363d5b71c4080efcb7c234e5a39
source_plan_sha256: 03f4cab34822b3cc24cf640b41702a23aeaae511e997231a0e2bc5e596703705
source_id: tuwien-custom-escape-route-ifc-v2
source_filename: CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc
source_byte_length: 7404420
published_md5: 58a6e009b16bd3808cacd72b11fcf216
observed_sha256: 29945f654c636d758a95b66eb0e107ec35afc7e1c7857a7ff652586e7728ba29
source_manifest_digest: bda63e3e6d3e536c1dffa51ccb8c7b37
runtime_external_fetch: false
survey_authority: false
production_mutation: false
human_review_required: true
```

## Delivered contracts

`aura_construction_demo_contracts.py` adds frozen, canonical, digest-bound contracts for:

- `ConstructionDemoSourceManifest` — source identity, creators, publisher, DOI, pinned bytes,
  licence, acquisition timestamp, and non-authority flags;
- `ConstructionDemoStorey` — deterministic storey identity, source reference, elevation/order,
  bounds, frame, and required representation IDs;
- `ConstructionDemoAssetBinding` — local representation URI, media type, SHA-256, byte length,
  coordinates/units/bounds, importer receipt, representation digest, truth class, and projection
  boundary;
- `ConstructionDemoAssetPack` — immutable source/storey/asset membership plus hierarchy,
  element-index, generator-request, and pack digests.

The asset pack explicitly denies ownership of Construction project state, schedule truth,
financial truth, regulatory truth, professional release, renderer authority, and physical
location truth. It also denies production mutation and automatic merge.

## Source identity

The exact source bytes were acquired from the pinned TU Wien record through an explicit operator
run and independently measured:

```text
bytes   7,404,420
MD5     58a6e009b16bd3808cacd72b11fcf216
SHA256  29945f654c636d758a95b66eb0e107ec35afc7e1c7857a7ff652586e7728ba29
```

The repository records the immutable identity in
`demo_assets/construction_tuwien/source/source-manifest.json`; the binary IFC itself remains an
operator-acquired build input until repository-size and publication strategy are measured.

## Operator-only acquisition boundary

`scripts/aura_fetch_construction_demo_source.py`:

1. requires `--accept-network-download`;
2. accepts only DOI `10.48436/a185k-86v39`;
3. contains one pinned HTTPS TU Wien URL and no arbitrary URL argument;
4. refuses all redirects and any final-URL change;
5. requires the pinned filename, `Content-Length`, byte count, published MD5, and Aura SHA-256;
6. imposes a 16 MiB hard maximum and bounded timeout;
7. writes into a temporary file inside a repository-contained, non-symlink output directory;
8. fsyncs and atomically replaces only after all verification succeeds;
9. refuses overwrite races or existing byte drift;
10. reuses already verified local bytes without opening a network connection;
11. emits a canonical immutable source manifest;
12. is not imported by Aura startup or the Construction demo runtime.

## Attribution and toolchain records

Added:

```text
demo_assets/construction_tuwien/README.md
demo_assets/construction_tuwien/ATTRIBUTION.md
demo_assets/construction_tuwien/LICENSE-CC-BY-4.0.txt
demo_assets/construction_tuwien/source/source-manifest.json
tools/construction_demo_assets/README.md
tools/construction_demo_assets/requirements.txt
```

Build-time dependency pins are isolated from Aura runtime. Niantic SPZ remains a separately pinned
build tool rather than an undeclared Python runtime dependency.

## Verification

```text
python -m py_compile \
  aura_construction_demo_contracts.py \
  scripts/aura_fetch_construction_demo_source.py \
  tests/test_aura_construction_demo_contracts.py \
  tests/test_aura_fetch_construction_demo_source.py

python -m pytest -q \
  tests/test_aura_construction_demo_contracts.py \
  tests/test_aura_fetch_construction_demo_source.py
```

Result: **14 passed**.

The tests cover deterministic round trips, nested digest tamper detection, authority escalation,
network/absolute URI rejection, unknown storey assets, explicit operator consent, exact DOI,
response URL/redirect drift, size/hash mismatch, output containment, symlink rejection, temporary
file cleanup, exact existing-byte reuse, and zero repeated network calls.

The source manifest was loaded through `ConstructionDemoSourceManifest.from_dict()` and reproduced
its pinned digest, SHA-256, and byte length exactly.

Ruff was not installed in either available local interpreter. No lint-pass claim is made. The
repository configuration was inspected directly (`Python 3.10`, Ruff line length 120, E501 ignored),
and formal Ruff verification remains required in GitHub CI/G8.

## G1 exit gate

```yaml
immutable_contracts_present: true
source_identity_pinned: true
attribution_present: true
operator_only_acquisition_present: true
runtime_fetch_absent: true
focused_tests_pass: true
ruff_local_result: NOT_AVAILABLE
next_gate: G2_DETERMINISTIC_IFC_COMPILER
```
