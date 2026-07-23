import assert from "node:assert/strict";
import test from "node:test";

import { createWebGL2GaussianPass } from "../../aura_spatial_web/webgl2_gaussian_pass.js";

function covarianceTestGl() {
  let nextId = 1;
  const calls = {
    shaderSources: [],
    bufferUploads: [],
    deletedBuffers: 0,
    deletedPrograms: 0,
    deletedVaos: 0,
    drawInstances: [],
  };
  return {
    calls,
    VERTEX_SHADER: 1,
    FRAGMENT_SHADER: 2,
    COMPILE_STATUS: 3,
    LINK_STATUS: 4,
    ARRAY_BUFFER: 5,
    STATIC_DRAW: 6,
    FLOAT: 7,
    BLEND: 8,
    SRC_ALPHA: 9,
    ONE_MINUS_SRC_ALPHA: 10,
    DEPTH_TEST: 11,
    TRIANGLE_STRIP: 12,
    createShader(type) {
      return { id: nextId++, type };
    },
    shaderSource(shader, source) {
      calls.shaderSources.push({ type: shader.type, source });
    },
    compileShader() {},
    getShaderParameter: () => true,
    getShaderInfoLog: () => "",
    deleteShader() {},
    createProgram: () => ({ id: nextId++ }),
    attachShader() {},
    linkProgram() {},
    getProgramParameter: () => true,
    getProgramInfoLog: () => "",
    deleteProgram() {
      calls.deletedPrograms += 1;
    },
    createVertexArray: () => ({ id: nextId++ }),
    bindVertexArray() {},
    deleteVertexArray() {
      calls.deletedVaos += 1;
    },
    createBuffer: () => ({ id: nextId++ }),
    bindBuffer() {},
    bufferData(_target, data) {
      calls.bufferUploads.push(Array.from(data));
    },
    deleteBuffer() {
      calls.deletedBuffers += 1;
    },
    getAttribLocation: (_program, name) => ({
      a_corner: 0,
      a_position: 1,
      a_rotation: 2,
      a_scale: 3,
      a_color: 4,
    })[name],
    enableVertexAttribArray() {},
    vertexAttribPointer() {},
    vertexAttribDivisor() {},
    useProgram() {},
    getUniformLocation: (_program, name) => name,
    uniformMatrix4fv() {},
    enable() {},
    blendFunc() {},
    depthMask() {},
    drawArraysInstanced(_mode, _first, _vertices, instances) {
      calls.drawInstances.push(instances);
    },
    isContextLost: () => false,
  };
}

test("WebGL2 Gaussian shader projects all three covariance axes", async () => {
  const gl = covarianceTestGl();
  const pass = createWebGL2GaussianPass({ gl });
  const handle = await pass({
    positions: new Float32Array([0, 0, 0]),
    rotations_xyzw: new Float32Array([0, Math.SQRT1_2, 0, Math.SQRT1_2]),
    scales_xyz: new Float32Array([1, 2, 7]),
    opacities: new Float32Array([1]),
    colors_rgba: new Uint8Array([255, 255, 255, 255]),
    sorted_indices: new Uint32Array([0]),
  }, {
    asset_id: "asset:anisotropic-splat",
    sh_degree: 0,
  });

  const vertexShader = gl.calls.shaderSources.find(
    ({ type }) => type === gl.VERTEX_SHADER,
  )?.source;
  assert.ok(vertexShader, "vertex shader source should be compiled");
  assert.match(vertexShader, /localAxisZ[\s\S]*positiveScale\.z/);
  assert.match(vertexShader, /projectedAxisZ\.x \* projectedAxisZ\.x/);
  assert.match(vertexShader, /projectedAxisZ\.x \* projectedAxisZ\.y/);
  assert.match(vertexShader, /projectedAxisZ\.y \* projectedAxisZ\.y/);
  assert.match(vertexShader, /principalAxis/);
  assert.doesNotMatch(vertexShader, /a_scale\.xy/);
  assert.ok(
    gl.calls.bufferUploads.some(
      (values) => values.length === 3 && values[0] === 1 && values[1] === 2 && values[2] === 7,
    ),
    "the complete anisotropic scale vector should reach the GPU",
  );
  assert.deepEqual(gl.calls.drawInstances, [1]);

  handle.dispose();
  handle.dispose();
  assert.equal(gl.calls.deletedBuffers, 5);
  assert.equal(gl.calls.deletedPrograms, 1);
  assert.equal(gl.calls.deletedVaos, 1);
});
