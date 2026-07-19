# Aura Spatial Format and Coordinate Policy — S4-B

## Canonical target frame

All imported geometry is converted into:

```yaml
handedness: RIGHT_HANDED
up_axis: Y_UP
meters_per_unit: 1.0
```

A format adapter may not silently reinterpret handedness, up axis, or units. The conversion matrix is compiled from declared source metadata, validated as finite, and embedded in the import receipt.

## Admitted formats

### glTF 2.0 / GLB

The S4-A adapter admits bounded, local, static triangle geometry only. It supports float32 positions and bounded unsigned indices. Embedded base64 buffers and the GLB BIN chunk are the only buffer sources.

Rejected surfaces include external URIs, remote fetches, relative file resolution, images, cameras, skins, animation, required extensions, sparse accessors, executable metadata, and compressed extension plugins.

### PLY

The S4-A adapter admits bounded vertex-only point clouds in ASCII, binary little-endian, or binary big-endian form. Coordinates are required. RGBA channels are optional. Faces, lists, non-finite values, undeclared properties, and ambiguous coordinate metadata are rejected.

## Resource ceilings

Importers enforce source-byte, decoded-byte, element, primitive, JSON depth/item, header, line, property, and canonical receipt limits before or during decoding. Local file imports reject symlinks and enforce an optional resolved root boundary.

## Evidence and authority

An import receipt proves only that particular bytes were decoded under the declared policy. It does not establish authorship, ownership, correctness, safety for production, or domain truth. Imported assets remain projection-only and require existing Aura governance before any consequential use.


## Gaussian interchange — S4-B

### SPZ v4

Aura admits only current SPZ v4 `NGSP` files. The source format is RUB (right, up, back). Aura retains that right-handed Y-up basis explicitly, including its +Z-back forward-axis semantics, rather than silently relabelling it. Legacy gzip SPZ versions, vendor extensions, unknown flags, nonzero reserved bytes, ambiguous stream tables, and unsupported spherical-harmonic degrees fail closed. Header, table, compressed-range, decoded-size, point-count, decompression-ratio, and allocation bounds are established before the optional Zstandard decoder runs.

### `KHR_gaussian_splatting`

Aura pins an exact Release-Candidate profile rather than treating the evolving Khronos extension name as a stable version. Gaussian glTF remains a strict local, embedded-buffer adapter. Required accessors are validated before expansion, integer normalized encodings are admitted only where the profile permits them, and unknown required semantics fail closed. Every accepted Gaussian primitive retains a deterministic point-cloud, accessible, and headless fallback.

### Mixed scenes

Topology primitives, triangle meshes, PLY points, and Gaussian splats may coexist in one immutable scene manifest. Representation type does not alter object identity, coordinate ownership, selection semantics, source/provenance digests, or authority. Stable canonical ordering and content-addressed manifests are preserved across all fallbacks.

## Gaussian resource ceilings

In addition to the S4-A limits, S4-B enforces source bytes, decompressed bytes, compression ratio, stream count, table size, Gaussian count, bytes per Gaussian, aggregate allocation, visible-splat, GPU-buffer, sort-work, frame-time, recursion, metadata, cancellation, and cleanup bounds. A count ceiling without a pre-allocation byte ceiling is not sufficient.

## No capture or training

No S4-B importer or renderer captures sensors, reconstructs scenes, optimizes Gaussian parameters, trains a model, or publishes an imported representation. Such work requires a separately governed research and promotion plan.
