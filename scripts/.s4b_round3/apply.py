from pathlib import Path

renderer = Path("aura_spatial_web/gaussian_renderer.js")
s = renderer.read_text(encoding="utf-8")
old = '''  let visibleSplats = 0;
  let gpuBytes = 0;
  let allocationBytes = 0;
  for (const asset of preflights) {
    visibleSplats = checkedBudgetAdd(visibleSplats, asset.count, "visible-splat count");
    gpuBytes = checkedBudgetAdd(gpuBytes, asset.gpu_bytes, "GPU bytes");
    allocationBytes = checkedBudgetAdd(allocationBytes, asset.allocation_bytes, "allocation bytes");
  }
  if (visibleSplats > limits.maxVisibleSplats) throw new RangeError("Gaussian aggregate visible-splat budget exceeded");
  if (gpuBytes > limits.maxGpuBytes) throw new RangeError("Gaussian aggregate GPU budget exceeded");
  if (allocationBytes > limits.maxAllocationBytes) throw new RangeError("Gaussian aggregate allocation budget exceeded");
  return Object.freeze({ visibleSplats, gpuBytes, allocationBytes });
'''
new = '''  let visibleSplats = 0;
  let gpuBytes = 0;
  let sortBytes = 0;
  let allocationBytes = 0;
  for (const asset of preflights) {
    visibleSplats = checkedBudgetAdd(visibleSplats, asset.count, "visible-splat count");
    gpuBytes = checkedBudgetAdd(gpuBytes, asset.gpu_bytes, "GPU bytes");
    sortBytes = checkedBudgetAdd(sortBytes, asset.sort_bytes, "sort bytes");
    allocationBytes = checkedBudgetAdd(allocationBytes, asset.allocation_bytes, "allocation bytes");
  }
  if (visibleSplats > limits.maxVisibleSplats) throw new RangeError("Gaussian aggregate visible-splat budget exceeded");
  if (gpuBytes > limits.maxGpuBytes || gpuBytes > limits.maxDecodedBytes) {
    throw new RangeError("Gaussian aggregate GPU/decoded byte budget exceeded");
  }
  if (sortBytes > limits.maxSortBytes) throw new RangeError("Gaussian aggregate sort byte budget exceeded");
  if (allocationBytes > limits.maxAllocationBytes) throw new RangeError("Gaussian aggregate allocation budget exceeded");
  return Object.freeze({ visibleSplats, gpuBytes, sortBytes, allocationBytes });
'''
if old not in s:
    raise SystemExit("aggregate budget block not found")
s = s.replace(old, new, 1)
renderer.write_text(s, encoding="utf-8")

test_path = Path("tests/js/spatial-gaussian.test.mjs")
t = test_path.read_text(encoding="utf-8")
marker = "Gaussian aggregate decoded-byte preflight rejects before nested materialization"
if marker in t:
    raise SystemExit("aggregate decoded-byte regression already present")
t += r'''

test("Gaussian aggregate decoded-byte preflight rejects before nested materialization", async () => {
  const first = await payload(1);
  const second = await payload(1);
  second.asset_id = "asset:gaussian-decoded-two";
  second.source_digest = "c".repeat(64);
  second.import_receipt_digest = "9".repeat(64);
  const scene = gaussianScene(first);
  const secondManifest = structuredClone(scene.assets[0]);
  secondManifest.asset_id = second.asset_id;
  secondManifest.content_digest = `sha256:${second.source_digest}`;
  secondManifest.source_refs = [
    "fixture:gaussian-decoded-two",
    `import-receipt:fixture#${second.import_receipt_digest}`,
    `render-representation:${second.render_representation_digest}`,
  ];
  secondManifest.metadata = {
    ...secondManifest.metadata,
    import_receipt_digest: second.import_receipt_digest,
    render_representation_digest: second.render_representation_digest,
  };
  scene.assets.push(secondManifest);
  scene.entities[0].asset_ids = [first.asset_id, second.asset_id];
  let touched = false;
  Object.defineProperty(first.rotations_xyzw, 0, {
    configurable: true,
    get() {
      touched = true;
      throw new Error("aggregate decoded preflight must not materialize");
    },
  });
  const rendererInstance = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: {
      maxVisibleSplats: 2,
      maxGpuBytes: 4096,
      maxDecodedBytes: 52,
      maxSortBytes: 4096,
      maxAllocationBytes: 8192,
      maxFrameMs: 20,
    },
    now: () => 0,
  });
  await assert.rejects(
    rendererInstance.initialize(scene, gaussianPlan(), [first, second]),
    /aggregate GPU\/decoded byte budget exceeded/,
  );
  assert.equal(touched, false);
});
'''
test_path.write_text(t, encoding="utf-8")
