import { AUTHORITY_ENVELOPE } from "./renderer_adapter.js";

export const WEBGL2_GAUSSIAN_PASS_VERSION = "AURA_WEBGL2_GAUSSIAN_PASS_V1";

const VERTEX = `#version 300 es
precision highp float;
in vec2 a_corner;
in vec3 a_position;
in vec4 a_rotation;
in vec3 a_scale;
in vec4 a_color;
uniform mat4 u_viewProjection;
uniform mat4 u_model;
out vec2 v_corner;
out vec4 v_color;

vec3 rotateByQuaternion(vec4 rotation, vec3 vector) {
  return vector + 2.0 * cross(
    rotation.xyz,
    cross(rotation.xyz, vector) + rotation.w * vector
  );
}

void main() {
  vec4 normalizedRotation = normalize(a_rotation);
  vec3 localAxis = rotateByQuaternion(
    normalizedRotation,
    vec3(a_corner * max(a_scale.xy, vec2(0.00001)), 0.0)
  );
  vec3 center = (u_model * vec4(a_position, 1.0)).xyz;
  vec3 transformedAxis = mat3(u_model) * localAxis;
  gl_Position = u_viewProjection * vec4(center + transformedAxis, 1.0);
  v_corner = a_corner;
  v_color = a_color;
}`;

const FRAGMENT = `#version 300 es
precision highp float;
in vec2 v_corner;
in vec4 v_color;
out vec4 outColor;
void main() {
  float radius2 = dot(v_corner, v_corner);
  if (radius2 > 1.0) discard;
  float weight = exp(-2.0 * radius2);
  outColor = vec4(v_color.rgb, v_color.a * weight);
}`;

const IDENTITY = Object.freeze([
  1, 0, 0, 0,
  0, 1, 0, 0,
  0, 0, 1, 0,
  0, 0, 0, 1,
]);

function boundedInteger(value, label, maximum) {
  if (!Number.isInteger(value) || value < 1 || value > maximum) {
    throw new RangeError(`${label} must be an integer in [1, ${maximum}]`);
  }
  return value;
}

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

function normalizedQuaternion(value, label) {
  const rotation = finiteVector(value, 4, label, [0, 0, 0, 1]);
  const norm = Math.hypot(...rotation);
  if (norm <= 1e-12) throw new TypeError(`${label} must not be a zero quaternion`);
  return rotation.map((item) => item / norm);
}

function modelMatrix(transform) {
  const translation = finiteVector(
    transform?.translation,
    3,
    "presentation translation",
    [0, 0, 0],
  );
  const scale = finiteVector(transform?.scale, 3, "presentation scale", [1, 1, 1]);
  if (scale.some((item) => item <= 0)) {
    throw new RangeError("presentation scale must remain positive");
  }
  const [x, y, z, w] = normalizedQuaternion(
    transform?.rotation_xyzw,
    "presentation rotation",
  );
  const [sx, sy, sz] = scale;
  return Object.freeze([
    (1 - 2 * (y * y + z * z)) * sx,
    (2 * (x * y + z * w)) * sx,
    (2 * (x * z - y * w)) * sx,
    0,
    (2 * (x * y - z * w)) * sy,
    (1 - 2 * (x * x + z * z)) * sy,
    (2 * (y * z + x * w)) * sy,
    0,
    (2 * (x * z + y * w)) * sz,
    (2 * (y * z - x * w)) * sz,
    (1 - 2 * (x * x + y * y)) * sz,
    0,
    translation[0],
    translation[1],
    translation[2],
    1,
  ]);
}

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("unable to allocate Gaussian shader");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Gaussian shader compile failed: ${log}`);
  }
  return shader;
}

function createProgram(gl) {
  const vertex = compileShader(gl, gl.VERTEX_SHADER, VERTEX);
  const fragment = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT);
  const program = gl.createProgram();
  if (!program) {
    gl.deleteShader(vertex);
    gl.deleteShader(fragment);
    throw new Error("unable to allocate Gaussian program");
  }
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(`Gaussian program link failed: ${log}`);
  }
  return program;
}

function createBuffer(gl, data) {
  const buffer = gl.createBuffer();
  if (!buffer) throw new Error("unable to allocate Gaussian buffer");
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  return buffer;
}

function bindAttribute(gl, program, name, buffer, width, divisor) {
  const location = gl.getAttribLocation(program, name);
  if (location < 0) throw new Error(`Gaussian shader attribute ${name} is unavailable`);
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.enableVertexAttribArray(location);
  gl.vertexAttribPointer(location, width, gl.FLOAT, false, 0, 0);
  gl.vertexAttribDivisor(location, divisor);
}

function gather(resources, context, maximum, isVisible) {
  const count = resources.sorted_indices.length;
  const admitted = [];
  for (let orderIndex = 0; orderIndex < count && admitted.length < maximum; orderIndex += 1) {
    const sourceIndex = resources.sorted_indices[orderIndex];
    const offset = sourceIndex * 3;
    const position = [
      resources.positions[offset],
      resources.positions[offset + 1],
      resources.positions[offset + 2],
    ];
    if (!isVisible || isVisible(position, sourceIndex, context) === true) {
      admitted.push(sourceIndex);
    }
  }
  const positions = new Float32Array(admitted.length * 3);
  const rotations = new Float32Array(admitted.length * 4);
  const scales = new Float32Array(admitted.length * 3);
  const colors = new Float32Array(admitted.length * 4);
  admitted.forEach((sourceIndex, outputIndex) => {
    positions.set(resources.positions.subarray(sourceIndex * 3, sourceIndex * 3 + 3), outputIndex * 3);
    rotations.set(
      resources.rotations_xyzw.subarray(sourceIndex * 4, sourceIndex * 4 + 4),
      outputIndex * 4,
    );
    scales.set(resources.scales_xyz.subarray(sourceIndex * 3, sourceIndex * 3 + 3), outputIndex * 3);
    const colorOffset = sourceIndex * 4;
    colors[outputIndex * 4] = resources.colors_rgba[colorOffset] / 255;
    colors[outputIndex * 4 + 1] = resources.colors_rgba[colorOffset + 1] / 255;
    colors[outputIndex * 4 + 2] = resources.colors_rgba[colorOffset + 2] / 255;
    colors[outputIndex * 4 + 3] =
      (resources.colors_rgba[colorOffset + 3] / 255) * resources.opacities[sourceIndex];
  });
  return Object.freeze({ positions, rotations, scales, colors, count: admitted.length });
}

export function createWebGL2GaussianPass({
  gl,
  getViewProjection = () => IDENTITY,
  getPresentationTransform = () => null,
  isVisible = null,
  maxVisibleSplats = 250_000,
} = {}) {
  if (!gl || typeof gl.drawArraysInstanced !== "function") {
    throw new TypeError("WebGL2 Gaussian pass requires a WebGL2 context");
  }
  if (typeof getViewProjection !== "function" || typeof getPresentationTransform !== "function") {
    throw new TypeError("Gaussian transform providers must be callable");
  }
  if (isVisible !== null && typeof isVisible !== "function") {
    throw new TypeError("isVisible must be callable when supplied");
  }
  const visibleLimit = boundedInteger(maxVisibleSplats, "maxVisibleSplats", 2_000_000);

  return async function drawWebGL2GaussianPass(resources, context) {
    if (context?.signal?.aborted) throw new Error("Gaussian draw cancelled");
    if (gl.isContextLost?.()) throw new Error("WebGL2 context is lost");
    if (context?.sh_degree !== 0) {
      throw new TypeError("Construction WebGL2 Gaussian pass accepts degree-0 splats only");
    }
    const gathered = gather(resources, context, visibleLimit, isVisible);
    const presentation = getPresentationTransform(context.asset_id) || {};
    const model = modelMatrix(presentation);
    const viewProjection = finiteVector(
      Array.from(getViewProjection(context)),
      16,
      "viewProjection",
      IDENTITY,
    );

    let program = null;
    let vao = null;
    const buffers = [];
    let disposed = false;
    try {
      program = createProgram(gl);
      vao = gl.createVertexArray();
      if (!vao) throw new Error("unable to allocate Gaussian vertex array");
      gl.bindVertexArray(vao);
      const corner = createBuffer(
        gl,
        new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      );
      const position = createBuffer(gl, gathered.positions);
      const rotation = createBuffer(gl, gathered.rotations);
      const scaleBuffer = createBuffer(gl, gathered.scales);
      const color = createBuffer(gl, gathered.colors);
      buffers.push(corner, position, rotation, scaleBuffer, color);
      bindAttribute(gl, program, "a_corner", corner, 2, 0);
      bindAttribute(gl, program, "a_position", position, 3, 1);
      bindAttribute(gl, program, "a_rotation", rotation, 4, 1);
      bindAttribute(gl, program, "a_scale", scaleBuffer, 3, 1);
      bindAttribute(gl, program, "a_color", color, 4, 1);

      gl.useProgram(program);
      gl.uniformMatrix4fv(
        gl.getUniformLocation(program, "u_viewProjection"),
        false,
        new Float32Array(viewProjection),
      );
      gl.uniformMatrix4fv(
        gl.getUniformLocation(program, "u_model"),
        false,
        new Float32Array(model),
      );
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.enable(gl.DEPTH_TEST);
      gl.depthMask(false);
      gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, gathered.count);
      gl.depthMask(true);
      gl.bindVertexArray(null);
      if (context?.signal?.aborted) throw new Error("Gaussian draw cancelled");
      if (gl.isContextLost?.()) throw new Error("WebGL2 context was lost during Gaussian draw");
    } catch (error) {
      for (const buffer of buffers.reverse()) gl.deleteBuffer?.(buffer);
      if (vao) gl.deleteVertexArray?.(vao);
      if (program) gl.deleteProgram?.(program);
      throw error;
    }

    return Object.freeze({
      version: WEBGL2_GAUSSIAN_PASS_VERSION,
      visible_count: gathered.count,
      capped: gathered.count < resources.sorted_indices.length,
      source_transform_immutable: true,
      ...AUTHORITY_ENVELOPE,
      dispose() {
        if (disposed) return;
        disposed = true;
        for (const buffer of buffers.reverse()) gl.deleteBuffer?.(buffer);
        gl.deleteVertexArray?.(vao);
        gl.deleteProgram?.(program);
      },
    });
  };
}
