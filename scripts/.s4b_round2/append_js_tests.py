from pathlib import Path

path = Path("tests/js/spatial-gaussian.test.mjs")
s = path.read_text(encoding="utf-8")
marker = "Gaussian per-asset preflight rejects before touching nested attacker-controlled values"
if marker in s:
    raise SystemExit("pre-allocation regressions already present")
s += r'''

test("Gaussian per-asset preflight rejects before touching nested attacker-controlled values", async () => {
  const guarded = await payload(2);
  const scene = gaussianScene(guarded);
  let touched = false;
  Object.defineProperty(guarded.positions, 0, {
    configurable: true,
    get() {
      touched = true;
      throw new Error("nested position must not be read");
    },
  });
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: {
      maxVisibleSplats: 2,
      maxGpuBytes: 4096,
      maxDecodedBytes: 4096,
      maxAllocationBytes: 1,
      maxFrameMs: 20,
    },
    now: () => 0,
  });
  await assert.rejects(
    renderer.initialize(scene, gaussianPlan(), [guarded]),
    /allocation budget exceeded before buffer creation/,
  );
  assert.equal(touched, false);
});

test("Gaussian aggregate preflight rejects every asset before materializing nested values", async () => {
  const first = await payload(1);
  const second = await payload(1);
  second.asset_id = "asset:gaussian-two";
  second.source_digest = "e".repeat(64);
  second.import_receipt_digest = "b".repeat(64);
  const scene = gaussianScene(first);
  const secondManifest = structuredClone(scene.assets[0]);
  secondManifest.asset_id = second.asset_id;
  secondManifest.content_digest = `sha256:${second.source_digest}`;
  secondManifest.source_refs = [
    "fixture:gaussian-two",
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
  Object.defineProperty(first.positions, 0, {
    configurable: true,
    get() {
      touched = true;
      throw new Error("aggregate preflight must not materialize");
    },
  });
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: {
      maxVisibleSplats: 1,
      maxGpuBytes: 4096,
      maxDecodedBytes: 4096,
      maxAllocationBytes: 8192,
      maxFrameMs: 20,
    },
    now: () => 0,
  });
  await assert.rejects(
    renderer.initialize(scene, gaussianPlan(), [first, second]),
    /aggregate visible-splat budget exceeded/,
  );
  assert.equal(touched, false);
});
'''
path.write_text(s, encoding="utf-8")
