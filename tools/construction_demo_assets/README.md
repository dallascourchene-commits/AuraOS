# Construction Demo Asset Toolchain

These dependencies are used only to build and verify the local Construction Arena asset pack.
They are not Aura runtime dependencies and must not trigger network access during a demo.

- **IfcOpenShell / IfcPatch / IfcConvert**: inspect and split IFC storeys; create GLB and SVG.
- **NumPy + trimesh**: deterministic bounded surface sampling for degree-0 Gaussian PLY.
- **Niantic SPZ**: compile validated PLY payloads to SPZ v4 with explicit coordinates. SPZ is
  built separately from its pinned upstream source and is not represented as a Python package
  in `requirements.txt`.

Tool versions, executable identities, source digests, request digest, stdout/stderr, and output
digests must be written into build receipts. A version change invalidates resumable outputs unless
an explicit rebuild is requested.
