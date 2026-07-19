from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_gaussian_gltf() -> None:
    path = Path("aura_spatial_importers/gaussian_gltf.py")
    text = path.read_text(encoding="utf-8")
    marker = "        coefficient_count = (degree + 1) ** 2 * 3\n"
    insertion = """        for semantic, accessor_index in attributes.items():
            accessor_count = _accessor(document, accessor_index).get("count")
            if (
                isinstance(accessor_count, bool)
                or not isinstance(accessor_count, int)
                or accessor_count != declared_count
            ):
                raise ValueError(
                    f"Gaussian glTF {semantic} count does not match POSITION before accessor expansion"
                )
        coefficient_count = (degree + 1) ** 2 * 3
"""
    text = replace_once(text, marker, insertion, "Gaussian accessor-count preflight")
    path.write_text(text, encoding="utf-8")
    print("patched Gaussian glTF accessor-count preflight")


def patch_renderer() -> None:
    path = Path("aura_spatial_web/gaussian_renderer.js")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "async function validateGaussianAsset(payload, sceneAsset, limits) {",
        "function preflightGaussianAsset(payload, sceneAsset, limits) {",
        "renderer preflight rename",
    )

    allocation_marker = '  const positions = allocateFloat32Vectors(payload.positions, 3, "Gaussian position");\n'
    allocation_index = text.index(allocation_marker)
    function_end_marker = "\n}\n\nfunction cameraVector"
    function_end = text.index(function_end_marker, allocation_index)
    allocation_tail = text[allocation_index:function_end]
    preflight_return = """  return Object.freeze({
    count,
    coefficient_count: coefficientCount,
    representation_bytes: representationBytes,
    allocation_bytes: allocationBytes,
  });
}

async function materializeGaussianAsset(payload, preflight) {
  const count = preflight.count;
  const coefficientCount = preflight.coefficient_count;
  const representationBytes = preflight.representation_bytes;
  const allocationBytes = preflight.allocation_bytes;
"""
    text = text[:allocation_index] + preflight_return + allocation_tail + text[function_end:]

    old_initialize = """    const seen = new Set();
    const assets = [];
    for (const payload of gaussianPayloads) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      if (seen.has(payload?.asset_id)) throw new TypeError("Gaussian asset payload is duplicated");
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("Gaussian payload is not admitted by the scene");
      assets.push(await validateGaussianAsset(payload, manifest, this.limits));
    }
    const totalGpuBytes = assets.reduce((total, asset) => total + asset.gpu_bytes, 0);
    const totalAllocationBytes = assets.reduce(
      (total, asset) => total + asset.allocation_bytes,
      0,
    );
    const totalSplats = assets.reduce((total, asset) => total + asset.count, 0);
    if (
      totalGpuBytes > this.limits.maxDecodedBytes ||
      totalGpuBytes > this.limits.maxGpuBytes ||
      totalAllocationBytes > this.limits.maxAllocationBytes ||
      totalSplats > this.limits.maxVisibleSplats
    ) {
      throw new RangeError("Gaussian aggregate allocation budget exceeded");
    }
    await this.presentationRenderer.initialize(scenePayload, planPayload);
    if (signal?.aborted) {
      await this.presentationRenderer.dispose();
      throw new Error("Gaussian initialization cancelled");
    }
    this.assets = Object.freeze([...assets].sort((a, b) => a.asset_id.localeCompare(b.asset_id)));
"""
    new_initialize = """    const seen = new Set();
    const admitted = [];
    for (const payload of gaussianPayloads) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      if (seen.has(payload?.asset_id)) throw new TypeError("Gaussian asset payload is duplicated");
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("Gaussian payload is not admitted by the scene");
      admitted.push(
        Object.freeze({
          payload,
          preflight: preflightGaussianAsset(payload, manifest, this.limits),
        }),
      );
    }
    const totalGpuBytes = admitted.reduce(
      (total, item) => total + item.preflight.representation_bytes,
      0,
    );
    const totalAllocationBytes = admitted.reduce(
      (total, item) => total + item.preflight.allocation_bytes,
      0,
    );
    const totalSplats = admitted.reduce((total, item) => total + item.preflight.count, 0);
    if (
      totalGpuBytes > this.limits.maxDecodedBytes ||
      totalGpuBytes > this.limits.maxGpuBytes ||
      totalAllocationBytes > this.limits.maxAllocationBytes ||
      totalSplats > this.limits.maxVisibleSplats
    ) {
      throw new RangeError("Gaussian aggregate allocation budget exceeded before materialization");
    }

    const assets = [];
    for (const item of admitted) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      assets.push(await materializeGaussianAsset(item.payload, item.preflight));
    }

    try {
      await this.presentationRenderer.initialize(scenePayload, planPayload);
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
    } catch (error) {
      let cleanupError = null;
      try {
        await this.presentationRenderer.dispose();
      } catch (cleanup) {
        cleanupError = cleanup;
      }
      this.assets = Object.freeze([]);
      this.scene = null;
      this.plan = null;
      this.limits = null;
      this.cancelled = true;
      this.state = RENDERER_STATES.LOST;
      if (cleanupError) {
        throw new AggregateError(
          [error, cleanupError],
          "Gaussian initialization and cleanup failed",
        );
      }
      throw error;
    }
    this.assets = Object.freeze([...assets].sort((a, b) => a.asset_id.localeCompare(b.asset_id)));
"""
    text = replace_once(text, old_initialize, new_initialize, "renderer aggregate preflight and init cleanup")
    path.write_text(text, encoding="utf-8")
    print("patched renderer aggregate preflight and initialization cleanup")


def patch_python_test() -> None:
    path = Path("tests/test_aura_spatial_gaussian_gltf.py")
    text = path.read_text(encoding="utf-8")
    marker = "def test_gaussian_gltf_rejects_accessor_count_mismatch_before_expansion() -> None:"
    if marker in text:
        print("Python regression already present")
        return
    addition = """


def test_gaussian_gltf_rejects_accessor_count_mismatch_before_expansion() -> None:
    document = json.loads(gaussian_gltf())
    rotation_accessor = document["meshes"][0]["primitives"][0]["attributes"][
        "KHR_gaussian_splatting:ROTATION"
    ]
    document["accessors"][rotation_accessor]["count"] = 2
    with pytest.raises(ValueError, match="before accessor expansion"):
        import_gaussian_gltf_bytes(
            json.dumps(document, separators=(",", ":")).encode(),
            provenance_refs=("fixture",),
        )
"""
    path.write_text(text.rstrip() + addition + "\n", encoding="utf-8")
    print("added Gaussian glTF accessor-count regression")


def patch_js_tests() -> None:
    path = Path("tests/js/spatial-gaussian.test.mjs")
    text = path.read_text(encoding="utf-8")
    if 'test("Gaussian aggregate preflight rejects before nested reads and typed-array materialization"' not in text:
        addition = r'''

test("Gaussian aggregate preflight rejects before nested reads and typed-array materialization", async () => {
  const first = payload();
  const second = payload();
  second.asset_id = "asset:gaussian:second";
  let nestedReads = 0;
  for (const value of [first, second]) {
    const original = value.positions[0][0];
    Object.defineProperty(value.positions[0], 0, {
      configurable: true,
      enumerable: true,
      get() {
        nestedReads += 1;
        return original;
      },
    });
  }

  const scene = gaussianScene(first);
  scene.assets.push({ ...structuredClone(scene.assets[0]), asset_id: second.asset_id });
  scene.entities[0].asset_ids = [first.asset_id, second.asset_id];
  const plan = gaussianPlan();
  plan.scene_asset_count = 2;
  plan.scene_asset_bytes = 96;
  const renderer = new GaussianRenderer({
    presentationRenderer: new HeadlessRenderer(),
    limits: limits({ maxAllocationBytes: 5_000 }),
    now: () => 0,
  });

  await assert.rejects(
    renderer.initialize(scene, plan, [first, second]),
    /aggregate allocation budget exceeded before materialization/,
  );
  assert.equal(nestedReads, 0);
});

test("Gaussian initialization rejection disposes partial presentation resources and enters LOST", async () => {
  const value = payload();
  let disposed = 0;
  const presentationRenderer = {
    kind: "PARTIAL_TEST",
    async initialize() {
      throw new Error("partial initialization failed");
    },
    async present() {
      throw new Error("not reachable");
    },
    async dispose() {
      disposed += 1;
    },
  };
  const renderer = new GaussianRenderer({
    presentationRenderer,
    limits: limits(),
    now: () => 0,
  });

  await assert.rejects(
    renderer.initialize(gaussianScene(value), gaussianPlan(), [value]),
    /partial initialization failed/,
  );
  assert.equal(disposed, 1);
  assert.equal(renderer.status().state, "LOST");
});
'''
        text = text.rstrip() + addition + "\n"
        path.write_text(text, encoding="utf-8")
        print("added renderer aggregate-preflight and initialization-cleanup regressions")
    else:
        print("JS regressions already present")


def main() -> None:
    patch_gaussian_gltf()
    patch_renderer()
    patch_python_test()
    patch_js_tests()


if __name__ == "__main__":
    main()
