import {
  AUTHORITY_ENVELOPE,
  RendererAdapter,
  RENDERER_STATES,
} from "./renderer_adapter.js";

const VERTEX = `#version 300 es
in vec3 a_position;
uniform mat4 u_viewProjection;
uniform float u_pointSize;
void main(){gl_Position=u_viewProjection*vec4(a_position,1.0);gl_PointSize=u_pointSize;}`;
const FRAGMENT = `#version 300 es
precision highp float;
uniform vec4 u_color;
out vec4 outColor;
void main(){outColor=u_color;}`;

export class WebGL2Renderer extends RendererAdapter {
  constructor({ canvas, gl = null } = {}) {
    super("WEBGL2");
    this.canvas = canvas || null;
    this.gl = gl;
    this.program = null;
    this.buffers = [];
    this.camera = { yaw: 0, pitch: 0, distance: 12, target: [0, 0, 0] };
    this.entityScreenPositions = new Map();
  }

  initialize(scenePayload, planPayload) {
    super.initialize(scenePayload, planPayload);
    this.gl =
      this.gl ||
      this.canvas?.getContext?.("webgl2", {
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      });
    if (!this.gl) {
      this.state = RENDERER_STATES.LOST;
      throw new Error("WebGL2 unavailable");
    }
    this.program = createProgram(this.gl, VERTEX, FRAGMENT);
    this.resources.add(this.program);
    const entityPositions = new Float32Array(
      this.scene.entities.flatMap((entity) => entity.position),
    );
    const byId = new Map(
      this.scene.entities.map((entity) => [entity.entity_id, entity.position]),
    );
    const linkPositions = new Float32Array(
      this.scene.links.flatMap((link) => [
        ...byId.get(link.source_entity_id),
        ...byId.get(link.target_entity_id),
      ]),
    );
    this.entityBuffer = createBuffer(this.gl, entityPositions);
    this.linkBuffer = createBuffer(this.gl, linkPositions);
    this.buffers.push(this.entityBuffer, this.linkBuffer);
    this.resources.add(this.entityBuffer);
    this.resources.add(this.linkBuffer);
    return this.status();
  }

  present({ width = this.canvas?.width || 800, height = this.canvas?.height || 600 } = {}) {
    if (
      this.state !== RENDERER_STATES.INITIALIZED &&
      this.state !== RENDERER_STATES.PRESENTED
    ) {
      throw new Error("WebGL2 renderer is not initialized");
    }
    if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || width > 16_384 || height > 16_384) {
      throw new RangeError("WebGL2 viewport is outside the admitted boundary");
    }
    const gl = this.gl;
    gl.viewport(0, 0, width, height);
    gl.enable(gl.DEPTH_TEST);
    gl.clearColor(0.025, 0.02, 0.08, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.useProgram(this.program);
    const matrix = orthographicViewProjection(
      this.camera,
      width / Math.max(1, height),
    );
    setMatrix(gl, this.program, "u_viewProjection", matrix);
    const position = gl.getAttribLocation(this.program, "a_position");
    gl.enableVertexAttribArray(position);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.linkBuffer);
    gl.vertexAttribPointer(position, 3, gl.FLOAT, false, 0, 0);
    setColor(gl, this.program, [0.42, 0.45, 0.85, 0.55]);
    gl.drawArrays(gl.LINES, 0, this.scene.links.length * 2);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.entityBuffer);
    gl.vertexAttribPointer(position, 3, gl.FLOAT, false, 0, 0);
    setColor(gl, this.program, [0.95, 0.35, 0.85, 1]);
    gl.uniform1f(gl.getUniformLocation(this.program, "u_pointSize"), 10);
    gl.drawArrays(gl.POINTS, 0, this.scene.entities.length);
    this.entityScreenPositions.clear();
    this.scene.entities.forEach((entity) => {
      this.entityScreenPositions.set(
        entity.entity_id,
        projectOrtho(entity.position, this.camera, width, height),
      );
    });
    if (this.state === RENDERER_STATES.INITIALIZED) this.markPresented();
    return Object.freeze({
      renderer: "WEBGL2",
      outcome: "PRESENTED",
      evidence_class: "MEASURED",
      scene_digest: this.scene.scene_digest,
      render_plan_digest: this.plan.render_plan_digest,
      entity_count: this.scene.entities.length,
      link_count: this.scene.links.length,
      width,
      height,
      ...AUTHORITY_ENVELOPE,
    });
  }

  pick(x, y, radius = 18) {
    if (![x, y, radius].every((value) => typeof value === "number" && Number.isFinite(value)) || radius < 0 || radius > 512) {
      throw new TypeError("pick coordinates and radius must be finite and bounded");
    }
    let best = null;
    let bestDistance = Infinity;
    for (const [id, point] of this.entityScreenPositions) {
      const distance = Math.hypot(point[0] - x, point[1] - y);
      if (distance <= radius && distance < bestDistance) {
        best = id;
        bestDistance = distance;
      }
    }
    return best;
  }

  orbit(deltaYaw, deltaPitch) {
    const yaw = Number(deltaYaw);
    const pitch = Number(deltaPitch);
    if (!Number.isFinite(yaw) || !Number.isFinite(pitch)) {
      throw new TypeError("orbit deltas must be finite");
    }
    this.camera.yaw = normalizeAngle(this.camera.yaw + yaw);
    this.camera.pitch = Math.max(-1.4, Math.min(1.4, this.camera.pitch + pitch));
  }

  zoom(delta) {
    const amount = Number(delta);
    if (!Number.isFinite(amount)) throw new TypeError("zoom delta must be finite");
    this.camera.distance = Math.max(1, Math.min(200, this.camera.distance + amount));
  }

  dispose() {
    if (this.gl) {
      for (const buffer of this.buffers) this.gl.deleteBuffer?.(buffer);
      if (this.program) this.gl.deleteProgram?.(this.program);
      this.gl.getExtension?.("WEBGL_lose_context")?.loseContext?.();
    }
    this.buffers = [];
    this.program = null;
    this.entityScreenPositions.clear();
    return super.dispose();
  }
}

function createShader(gl, type, source) {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("unable to allocate shader");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`shader compile failed: ${log}`);
  }
  return shader;
}

function createProgram(gl, vertexSource, fragmentSource) {
  const program = gl.createProgram();
  const vertex = createShader(gl, gl.VERTEX_SHADER, vertexSource);
  const fragment = createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(`program link failed: ${log}`);
  }
  return program;
}

function createBuffer(gl, data) {
  const buffer = gl.createBuffer();
  if (!buffer) throw new Error("unable to allocate buffer");
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  return buffer;
}

function setMatrix(gl, program, name, matrix) {
  gl.uniformMatrix4fv(gl.getUniformLocation(program, name), false, matrix);
}

function setColor(gl, program, color) {
  gl.uniform4fv(gl.getUniformLocation(program, "u_color"), color);
}

function normalizeAngle(value) {
  const turn = Math.PI * 2;
  return ((value + Math.PI) % turn + turn) % turn - Math.PI;
}

function rotatedRelative(position, camera) {
  const x = position[0] - camera.target[0];
  const y = position[1] - camera.target[1];
  const z = position[2] - camera.target[2];
  const cosineYaw = Math.cos(camera.yaw);
  const sineYaw = Math.sin(camera.yaw);
  const cosinePitch = Math.cos(camera.pitch);
  const sinePitch = Math.sin(camera.pitch);
  const yawX = cosineYaw * x - sineYaw * z;
  const yawZ = sineYaw * x + cosineYaw * z;
  return [
    yawX,
    cosinePitch * y + sinePitch * yawZ,
    -sinePitch * y + cosinePitch * yawZ,
  ];
}

function orthographicViewProjection(camera, aspect) {
  const scale = Math.max(1, camera.distance);
  const cosineYaw = Math.cos(camera.yaw);
  const sineYaw = Math.sin(camera.yaw);
  const cosinePitch = Math.cos(camera.pitch);
  const sinePitch = Math.sin(camera.pitch);
  const row0 = [cosineYaw / (scale * aspect), 0, -sineYaw / (scale * aspect)];
  const row1 = [
    (sinePitch * sineYaw) / scale,
    cosinePitch / scale,
    (sinePitch * cosineYaw) / scale,
  ];
  const row2 = [
    (-cosinePitch * sineYaw) / scale,
    sinePitch / scale,
    (-cosinePitch * cosineYaw) / scale,
  ];
  const target = camera.target;
  const translation = [
    -row0[0] * target[0] - row0[1] * target[1] - row0[2] * target[2],
    -row1[0] * target[0] - row1[1] * target[1] - row1[2] * target[2],
    -row2[0] * target[0] - row2[1] * target[1] - row2[2] * target[2],
  ];
  return new Float32Array([
    row0[0], row1[0], row2[0], 0,
    row0[1], row1[1], row2[1], 0,
    row0[2], row1[2], row2[2], 0,
    translation[0], translation[1], translation[2], 1,
  ]);
}

function projectOrtho(position, camera, width, height) {
  const [x, y] = rotatedRelative(position, camera);
  const scale = Math.max(1, camera.distance);
  return [
    width / 2 + (x * width) / (2 * scale),
    height / 2 - (y * height) / (2 * scale),
  ];
}
