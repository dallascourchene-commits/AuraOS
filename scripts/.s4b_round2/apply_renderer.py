from pathlib import Path

path = Path("aura_spatial_web/gaussian_renderer.js")
s = path.read_text(encoding="utf-8")

s = s.replace(
    'const GAUSSIAN_DIGEST_VERSION = "AURA_GAUSSIAN_RENDER_PROJECTION_V1\\0";\nconst GAUSSIAN_DIGEST_BYTES_PER_SPLAT = 92;\n',
    'const GAUSSIAN_DIGEST_VERSION = "AURA_GAUSSIAN_RENDER_PROJECTION_V1\\0";\n'
    'const GAUSSIAN_DIGEST_PREFIX = new TextEncoder().encode(GAUSSIAN_DIGEST_VERSION);\n'
    'const GAUSSIAN_DIGEST_BYTES_PER_SPLAT = 92;\n',
    1,
)

start = s.index("function finiteVector(")
end = s.index("\nfunction digestHex(", start)
s = s[:start] + '''function assertFiniteVector(value, length, label, { nonNegative = false } = {}) {
  if (!Array.isArray(value) || value.length !== length) {
    throw new TypeError(`${label} must contain ${length} finite numbers`);
  }
  for (let index = 0; index < length; index += 1) {
    const item = value[index];
    if (typeof item !== "number" || !Number.isFinite(item) || (nonNegative && item < 0)) {
      throw new TypeError(`${label} must contain ${length} finite${nonNegative ? " non-negative" : ""} numbers`);
    }
  }
  return value;
}

function frozenVectorCopy(value, length, label, options = {}) {
  const checked = assertFiniteVector(value, length, label, options);
  return Object.freeze(Array.from({ length }, (_, index) => checked[index]));
}
''' + s[end:]

start = s.index("export async function computeGaussianRepresentationDigest(")
end = s.index("\nfunction boundedPositiveInteger(", start)
s = s[:start] + '''export async function computeGaussianRepresentationDigest(payload, { signal = null, maximumBytes = 256 * 1024 * 1024 } = {}) {
  const count = payload?.positions?.length;
  if (!Number.isInteger(count) || count < 1 || count > 2_000_000) {
    throw new RangeError("Gaussian digest count exceeds bounds");
  }
  for (const name of ["rotations_xyzw", "scales_xyz", "opacities", "colors_rgba"]) {
    if (!Array.isArray(payload[name]) || payload[name].length !== count) {
      throw new TypeError(`Gaussian ${name} count mismatch`);
    }
  }
  const byteLength = GAUSSIAN_DIGEST_PREFIX.length + 4 + count * GAUSSIAN_DIGEST_BYTES_PER_SPLAT;
  if (!Number.isSafeInteger(byteLength) || byteLength > maximumBytes) {
    throw new RangeError("Gaussian representation digest buffer exceeds admitted allocation budget");
  }
  if (signal?.aborted) throw new Error("Gaussian digest cancelled");
  if (!globalThis.crypto?.subtle) {
    throw new Error("Gaussian representation digest requires WebCrypto");
  }
  const buffer = new ArrayBuffer(byteLength);
  const bytes = new Uint8Array(buffer);
  bytes.set(GAUSSIAN_DIGEST_PREFIX, 0);
  const view = new DataView(buffer);
  let offset = GAUSSIAN_DIGEST_PREFIX.length;
  view.setUint32(offset, count, true);
  offset += 4;
  for (let index = 0; index < count; index += 1) {
    if ((index & 0x0fff) === 0 && signal?.aborted) throw new Error("Gaussian digest cancelled");
    const position = assertFiniteVector(payload.positions[index], 3, `Gaussian position ${index}`);
    const rotation = assertFiniteVector(payload.rotations_xyzw[index], 4, `Gaussian rotation ${index}`);
    const scale = assertFiniteVector(payload.scales_xyz[index], 3, `Gaussian scale ${index}`, { nonNegative: true });
    const opacity = payload.opacities[index];
    if (typeof opacity !== "number" || !Number.isFinite(opacity) || opacity < 0 || opacity > 1) {
      throw new TypeError("Gaussian opacity must be finite and normalized");
    }
    const color = payload.colors_rgba[index];
    if (
      !Array.isArray(color) ||
      color.length !== 4 ||
      color.some((channel) => !Number.isInteger(channel) || channel < 0 || channel > 255)
    ) {
      throw new TypeError("Gaussian fallback colors must be RGBA8");
    }
    for (const value of [...position, ...rotation, ...scale, opacity]) {
      view.setFloat64(offset, value, true);
      offset += 8;
    }
    for (const channel of color) bytes[offset++] = channel;
  }
  if (signal?.aborted) throw new Error("Gaussian digest cancelled");
  return digestHex(new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", buffer)));
}
''' + s[end:]

start = s.index("async function validateGaussianAsset(")
end = s.index("\nexport class GaussianRenderer", start)
s = s[:start] + r'''function canonicalManifestDigestRefs(sceneAsset) {
  const receiptRefs = sceneAsset.source_refs.filter((value) => value.startsWith("import-receipt:"));
  const representationRefs = sceneAsset.source_refs.filter((value) => value.startsWith("render-representation:"));
  if (receiptRefs.length !== 1 || representationRefs.length !== 1) {
    throw new TypeError("Gaussian manifest must contain exactly one canonical import and representation digest reference");
  }
  const receiptDigest = receiptRefs[0].split("#").at(-1);
  const representationDigest = representationRefs[0].slice("render-representation:".length);
  if (!DIGEST.test(String(receiptDigest || "")) || !DIGEST.test(String(representationDigest || ""))) {
    throw new TypeError("Gaussian manifest digest references must be lowercase sha256");
  }
  return Object.freeze({ receiptDigest, representationDigest });
}

function preflightGaussianAsset(payload, sceneAsset, limits) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new TypeError("Gaussian asset payload must be an object");
  }
  const expected = new Set([
    "asset_id",
    "source_digest",
    "import_receipt_digest",
    "render_representation_digest",
    "positions",
    "rotations_xyzw",
    "scales_xyz",
    "opacities",
    "colors_rgba",
  ]);
  exactKeys(payload, expected, "Gaussian asset payload");
  if (payload.asset_id !== sceneAsset.asset_id) throw new TypeError("Gaussian payload asset id is stale or ambiguous");
  const expectedSourceDigest = String(sceneAsset.content_digest || "").split(":").at(-1);
  if (!DIGEST.test(String(expectedSourceDigest || "")) || payload.source_digest !== expectedSourceDigest) {
    throw new TypeError("Gaussian asset digest is stale or ambiguous");
  }
  if (!DIGEST.test(String(payload.import_receipt_digest || ""))) {
    throw new TypeError("Gaussian import_receipt_digest must be lowercase sha256");
  }
  if (!DIGEST.test(String(payload.render_representation_digest || ""))) {
    throw new TypeError("Gaussian render_representation_digest must be lowercase sha256");
  }
  const manifestDigests = canonicalManifestDigestRefs(sceneAsset);
  if (payload.import_receipt_digest !== manifestDigests.receiptDigest) {
    throw new TypeError("Gaussian import receipt digest is stale or ambiguous");
  }
  if (payload.render_representation_digest !== manifestDigests.representationDigest) {
    throw new TypeError("Gaussian representation digest is stale or ambiguous");
  }
  const count = payload.positions?.length;
  if (!Number.isInteger(count) || count < 1) throw new TypeError("Gaussian positions must be a non-empty array");
  if (count > limits.maxVisibleSplats) throw new RangeError("Gaussian visible-splat budget exceeded");
  for (const name of ["rotations_xyzw", "scales_xyz", "opacities", "colors_rgba"]) {
    if (!Array.isArray(payload[name]) || payload[name].length !== count) {
      throw new TypeError(`Gaussian ${name} count mismatch`);
    }
  }
  const gpuBytes = count * GPU_BYTES_PER_SPLAT;
  const sortBytes = count * SORT_BYTES_PER_SPLAT;
  const digestBytes = GAUSSIAN_DIGEST_PREFIX.length + 4 + count * GAUSSIAN_DIGEST_BYTES_PER_SPLAT;
  const allocationBytes = count * JS_PEAK_BYTES_PER_SPLAT + gpuBytes + sortBytes + digestBytes;
  for (const [value, label] of [
    [gpuBytes, "GPU"],
    [sortBytes, "sort"],
    [digestBytes, "digest"],
    [allocationBytes, "allocation"],
  ]) {
    if (!Number.isSafeInteger(value)) throw new RangeError(`Gaussian ${label} byte estimate is not a safe integer`);
  }
  if (gpuBytes > limits.maxGpuBytes || gpuBytes > limits.maxDecodedBytes) {
    throw new RangeError("Gaussian GPU/decoded byte budget exceeded before buffer creation");
  }
  if (sortBytes > limits.maxSortBytes) throw new RangeError("Gaussian sort byte budget exceeded before sorting");
  if (allocationBytes > limits.maxAllocationBytes) {
    throw new RangeError("Gaussian allocation budget exceeded before buffer creation");
  }
  return Object.freeze({
    payload,
    sceneAsset,
    count,
    gpu_bytes: gpuBytes,
    sort_bytes: sortBytes,
    digest_bytes: digestBytes,
    allocation_bytes: allocationBytes,
  });
}

function checkedBudgetAdd(total, value, label) {
  const next = total + value;
  if (!Number.isSafeInteger(next)) throw new RangeError(`Gaussian aggregate ${label} is not a safe integer`);
  return next;
}

function assertAggregateBudgets(preflights, limits) {
  let visibleSplats = 0;
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
}

async function materializeGaussianAsset(preflight, { signal = null } = {}) {
  if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
  const { payload, count } = preflight;
  const positions = new Array(count);
  const rotations = new Array(count);
  const scales = new Array(count);
  const opacities = new Array(count);
  const colors = new Array(count);
  for (let index = 0; index < count; index += 1) {
    if ((index & 0x0fff) === 0 && signal?.aborted) throw new Error("Gaussian initialization cancelled");
    positions[index] = frozenVectorCopy(payload.positions[index], 3, `Gaussian position ${index}`);
    rotations[index] = frozenVectorCopy(payload.rotations_xyzw[index], 4, `Gaussian rotation ${index}`);
    scales[index] = frozenVectorCopy(payload.scales_xyz[index], 3, `Gaussian scale ${index}`, { nonNegative: true });
    const opacity = payload.opacities[index];
    if (typeof opacity !== "number" || !Number.isFinite(opacity) || opacity < 0 || opacity > 1) {
      throw new TypeError("Gaussian opacity must be finite and normalized");
    }
    opacities[index] = opacity;
    const color = payload.colors_rgba[index];
    if (
      !Array.isArray(color) ||
      color.length !== 4 ||
      color.some((channel) => !Number.isInteger(channel) || channel < 0 || channel > 255)
    ) {
      throw new TypeError("Gaussian fallback colors must be RGBA8");
    }
    colors[index] = Object.freeze(Array.from({ length: 4 }, (_, channel) => color[channel]));
  }
  for (const name of ["positions", "rotations_xyzw", "scales_xyz", "opacities", "colors_rgba"]) {
    if (payload[name].length !== count) throw new TypeError(`Gaussian ${name} changed during materialization`);
  }
  const canonical = Object.freeze({
    positions: Object.freeze(positions),
    rotations_xyzw: Object.freeze(rotations),
    scales_xyz: Object.freeze(scales),
    opacities: Object.freeze(opacities),
    colors_rgba: Object.freeze(colors),
  });
  const observedRepresentationDigest = await computeGaussianRepresentationDigest(canonical, {
    signal,
    maximumBytes: preflight.digest_bytes,
  });
  if (observedRepresentationDigest !== payload.render_representation_digest) {
    throw new TypeError("Gaussian decoded representation does not match its admitted digest");
  }
  return Object.freeze({
    asset_id: payload.asset_id,
    source_digest: payload.source_digest,
    import_receipt_digest: payload.import_receipt_digest,
    render_representation_digest: payload.render_representation_digest,
    count,
    ...canonical,
    gpu_bytes: preflight.gpu_bytes,
    sort_bytes: preflight.sort_bytes,
    allocation_bytes: preflight.allocation_bytes,
  });
}
''' + s[end:]

old = '''    const seen = new Set();
    const assets = [];
    for (const payload of gaussianPayloads) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      if (seen.has(payload?.asset_id)) throw new TypeError("Gaussian asset payload is duplicated");
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("Gaussian payload is not admitted by the scene");
      assets.push(await validateGaussianAsset(payload, manifest, this.limits));
    }
    const aggregate = aggregateBudgets(assets, this.limits);
'''
new = '''    const seen = new Set();
    const preflights = [];
    for (const payload of gaussianPayloads) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      if (seen.has(payload?.asset_id)) throw new TypeError("Gaussian asset payload is duplicated");
      seen.add(payload?.asset_id);
      const manifest = manifests.get(payload?.asset_id);
      if (!manifest) throw new TypeError("Gaussian payload is not admitted by the scene");
      preflights.push(preflightGaussianAsset(payload, manifest, this.limits));
    }
    const aggregate = assertAggregateBudgets(preflights, this.limits);
    const assets = [];
    for (const preflight of preflights) {
      if (signal?.aborted) throw new Error("Gaussian initialization cancelled");
      assets.push(await materializeGaussianAsset(preflight, { signal }));
    }
'''
if old not in s:
    raise SystemExit("initialize fragment not found")
s = s.replace(old, new, 1)
path.write_text(s, encoding="utf-8")
