# Aura Spatial Format and Coordinate Policy — S4-A

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
