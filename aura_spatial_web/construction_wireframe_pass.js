export const CONSTRUCTION_WIREFRAME_PASS_VERSION = "AURA_CONSTRUCTION_WIREFRAME_PASS_V1";

const SVG_NS = "http://www.w3.org/2000/svg";
const EDGES = Object.freeze([
  [0, 1], [1, 3], [3, 2], [2, 0],
  [4, 5], [5, 7], [7, 6], [6, 4],
  [0, 4], [1, 5], [2, 6], [3, 7],
]);

function finiteVector(value, length, label, fallback) {
  const candidate = value ?? fallback;
  if (
    !Array.isArray(candidate) ||
    candidate.length !== length ||
    candidate.some((item) => typeof item !== "number" || !Number.isFinite(item))
  ) {
    throw new TypeError(`${label} must be a finite ${length}-vector`);
  }
  return candidate;
}

function normalizeQuaternion(value) {
  const rotation = finiteVector(value, 4, "wireframe rotation", [0, 0, 0, 1]);
  const norm = Math.hypot(...rotation);
  if (norm <= 1e-12) throw new TypeError("wireframe rotation must not be zero");
  return rotation.map((item) => item / norm);
}

function rotate(rotation, vector) {
  const [x, y, z, w] = rotation;
  const [vx, vy, vz] = vector;
  const tx = 2 * (y * vz - z * vy);
  const ty = 2 * (z * vx - x * vz);
  const tz = 2 * (x * vy - y * vx);
  return [
    vx + w * tx + (y * tz - z * ty),
    vy + w * ty + (z * tx - x * tz),
    vz + w * tz + (x * ty - y * tx),
  ];
}

function transformPoint(point, transform) {
  const translation = finiteVector(transform?.translation, 3, "wireframe translation", [0, 0, 0]);
  const scale = finiteVector(transform?.scale, 3, "wireframe scale", [1, 1, 1]);
  const rotation = normalizeQuaternion(transform?.rotation_xyzw);
  const scaled = point.map((value, index) => value * scale[index]);
  const rotated = rotate(rotation, scaled);
  return rotated.map((value, index) => value + translation[index]);
}

function projectionMatrix(camera, width, height) {
  const source = camera || { yaw: 0, pitch: 0, distance: 12, target: [0, 0, 0] };
  const target = finiteVector(source.target, 3, "wireframe camera target", [0, 0, 0]);
  const yaw = Number(source.yaw || 0);
  const pitch = Number(source.pitch || 0);
  const distance = Math.max(1, Number(source.distance || 12));
  const aspect = width / Math.max(1, height);
  const cosineYaw = Math.cos(yaw);
  const sineYaw = Math.sin(yaw);
  const cosinePitch = Math.cos(pitch);
  const sinePitch = Math.sin(pitch);
  const row0 = [cosineYaw / (distance * aspect), 0, -sineYaw / (distance * aspect)];
  const row1 = [
    (sinePitch * sineYaw) / distance,
    cosinePitch / distance,
    (sinePitch * cosineYaw) / distance,
  ];
  return {
    row0,
    row1,
    translation: [
      -row0[0] * target[0] - row0[1] * target[1] - row0[2] * target[2],
      -row1[0] * target[0] - row1[1] * target[1] - row1[2] * target[2],
    ],
  };
}

function project(point, camera, width, height) {
  const matrix = projectionMatrix(camera, width, height);
  const x = matrix.row0[0] * point[0] + matrix.row0[1] * point[1] + matrix.row0[2] * point[2] + matrix.translation[0];
  const y = matrix.row1[0] * point[0] + matrix.row1[1] * point[1] + matrix.row1[2] * point[2] + matrix.translation[1];
  return [(x * 0.5 + 0.5) * width, (1 - (y * 0.5 + 0.5)) * height];
}

function corners(bounds) {
  const minimum = finiteVector(bounds?.[0], 3, "wireframe bounds minimum", [-1, -1, -1]);
  const maximum = finiteVector(bounds?.[1], 3, "wireframe bounds maximum", [1, 1, 1]);
  return [
    [minimum[0], minimum[1], minimum[2]],
    [maximum[0], minimum[1], minimum[2]],
    [minimum[0], maximum[1], minimum[2]],
    [maximum[0], maximum[1], minimum[2]],
    [minimum[0], minimum[1], maximum[2]],
    [maximum[0], minimum[1], maximum[2]],
    [minimum[0], maximum[1], maximum[2]],
    [maximum[0], maximum[1], maximum[2]],
  ];
}

export function createConstructionWireframePass({ overlay, getCamera, getCanvas } = {}) {
  if (!overlay || overlay.namespaceURI !== SVG_NS) {
    throw new TypeError("Construction wireframe pass requires an SVG overlay");
  }
  if (typeof getCamera !== "function" || typeof getCanvas !== "function") {
    throw new TypeError("Construction wireframe pass requires camera and canvas providers");
  }

  return async function drawConstructionWireframe(resource, context) {
    const canvas = getCanvas();
    const width = Math.max(1, canvas?.width || 1280);
    const height = Math.max(1, canvas?.height || 720);
    overlay.setAttribute("viewBox", `0 0 ${width} ${height}`);
    const group = document.createElementNS(SVG_NS, "g");
    group.dataset.assetId = context.asset_id;
    group.classList.add("construction-wireframe-storey");
    const points = corners(resource?.bounds)
      .map((point) => transformPoint(point, context.presentation_transform))
      .map((point) => project(point, getCamera(), width, height));

    for (const [left, right] of EDGES) {
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("x1", String(points[left][0]));
      line.setAttribute("y1", String(points[left][1]));
      line.setAttribute("x2", String(points[right][0]));
      line.setAttribute("y2", String(points[right][1]));
      group.append(line);
    }
    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", String(points[6][0] + 6));
    label.setAttribute("y", String(points[6][1] - 6));
    label.textContent = String(context.frame_id || context.asset_id);
    group.append(label);
    overlay.append(group);

    let disposed = false;
    return {
      version: CONSTRUCTION_WIREFRAME_PASS_VERSION,
      dispose() {
        if (disposed) return;
        disposed = true;
        group.remove();
      },
    };
  };
}
