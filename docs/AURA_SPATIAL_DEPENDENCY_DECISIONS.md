# Aura Spatial S4-B Dependency Decisions

**Decision date:** 2026-07-19  
**Scope:** Gaussian interchange and projection only  
**Authority:** imported representations remain projection-only and cannot authorize execution, mutation, promotion, capture, or training.

## SPZ

Aura targets the current SPZ **version 4** wire format documented by the upstream `nianticlabs/spz` project at release `v3.0.0`, commit `5bf2945de1a003cee07133b1e495fe9c6ffdc7e7`. The upstream code is MIT licensed. SPZ v4 uses a 32-byte little-endian `NGSP` header, a plaintext table of contents, and independently Zstandard-compressed attribute streams. Upstream continues to read legacy gzip versions 1-3 and explicitly does not enforce a maximum point count.

Aura intentionally implements a narrower boundary:

- only SPZ v4 is admitted;
- legacy gzip versions 1-3 fail closed rather than entering an unbounded decompression path;
- vendor extension records fail closed until a separately reviewed extension profile exists;
- reserved header bytes and unknown flag bits must be zero;
- point, source-byte, decoded-byte, decompression-ratio, stream-count, table, fractional-bit, and allocation ceilings are verified before decompression or result allocation;
- every stream must have the exact expected uncompressed size and all compressed ranges must cover the file exactly without overlap, gaps, or trailing bytes;
- cancellation is checked before each decompression and during record expansion;
- SPZ's internal RUB convention is explicitly retained as a right-handed Y-up +Z-back projection basis;
- a dependency-free inspection/failure path remains available even when the optional decoder is absent.

### Decoder dependency

The isolated decoder uses `zstandard==0.25.0`, BSD-3-Clause licensed, through the narrow `decompress(data, max_output_size=...)` API. The runtime version is checked exactly before use. `requirements-spatial-s4b.txt` pins exact manylinux2014 x86_64 wheel hashes for CPython 3.10-3.13, and CI installs it with `--require-hashes --only-binary=:all:`.

Removal or rollback is bounded: uninstalling the optional package disables SPZ payload expansion while preserving header/TOC inspection, explicit failure, glTF/PLY interchange, point-cloud/accessibility/headless rendering, and all canonical scene contracts. No scene or receipt identity depends on the decoder package being globally available.

## Khronos Gaussian glTF

Aura follows `KHR_gaussian_splatting` at Khronos glTF repository commit `77b44be7bef26e01fb0b140e3d5bb1716421c5e9`. As of 2026-07-19, Khronos marks the extension **Release Candidate**, not ratified. The extension does not expose a numeric wire-version field, so Aura negotiates an exact implementation profile:

```text
KHR_gaussian_splatting:release-candidate:2026-07-19
```

The admitted profile requires:

- non-indexed `POINTS` primitives;
- `POSITION`, `_ROTATION`, `_SCALE`, `_OPACITY`, and `_SH_0`;
- exact `ellipse` kernel;
- `srgb_rec709_display` or `lin_rec709_display` color space;
- `perspective` projection and `cameraDistance` sorting;
- complete contiguous SH bands and bounded normalized component encodings;
- no unknown required or used extensions, nested extension semantics, arbitrary URI loading, images, animation, skinning, scripts, shaders, or executable content.

A valid Gaussian primitive always retains a deterministic point-cloud representation. When `COLOR_0` is absent, Aura derives a bounded placeholder color from `_SH_0` and labels that fallback honestly. Unknown future mandatory semantics are rejected; upgrading the Khronos profile requires a new primary-source review, compatibility fixtures, rollback decision, and exact-head review cycle.

## Renderer decision

`GaussianRenderer` is a replaceable representation layer around an already admitted `RendererAdapter`. It cannot select or become the presentation owner. It may invoke a bounded replaceable Gaussian pass. When a bounded point-cloud pass is supplied by the retained presentation owner, that fallback is executed and measured; otherwise the adapter reports only accessible and headless fallback evidence and does not falsely claim that points were drawn.

Budgets cover visible splats, decoded bytes, conservative Python expansion, GPU bytes, typed-array allocation, sort work, frame time, cancellation, and deterministic disposal. Device loss terminates the Gaussian layer without claiming that the retained presentation renderer or browser resources were released unless acknowledged by their actual owner.

## Excluded production surfaces

S4-B adds no camera capture, sensor ingestion, reconstruction, optimization, training, model fitting, remote asset fetch, production publishing, or automatic promotion path. Those remain outside production until a separately governed S7 decision and a new implementation plan.
