import test from "node:test";
import assert from "node:assert/strict";

import { WebGL2Renderer } from "../../aura_spatial_web/webgl2_renderer.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

function fakeGL() {
  let id = 0;
  const calls = [];
  return {
    calls,
    VERTEX_SHADER: 1,
    FRAGMENT_SHADER: 2,
    COMPILE_STATUS: 3,
    LINK_STATUS: 4,
    ARRAY_BUFFER: 5,
    STATIC_DRAW: 6,
    FLOAT: 7,
    LINES: 8,
    POINTS: 9,
    DEPTH_TEST: 10,
    COLOR_BUFFER_BIT: 1,
    DEPTH_BUFFER_BIT: 2,
    createShader: () => ({ id: ++id }),
    shaderSource() {},
    compileShader() {},
    getShaderParameter: () => true,
    getShaderInfoLog: () => "",
    deleteShader() {},
    createProgram: () => ({ id: ++id }),
    attachShader() {},
    linkProgram() {},
    getProgramParameter: () => true,
    getProgramInfoLog: () => "",
    deleteProgram: (program) => calls.push(["deleteProgram", program.id]),
    createBuffer: () => ({ id: ++id }),
    bindBuffer() {},
    bufferData() {},
    deleteBuffer: (buffer) => calls.push(["deleteBuffer", buffer.id]),
    viewport() {},
    enable() {},
    clearColor() {},
    clear() {},
    useProgram() {},
    getAttribLocation: () => 0,
    enableVertexAttribArray() {},
    vertexAttribPointer() {},
    getUniformLocation: () => 0,
    uniformMatrix4fv: (_location, _transpose, matrix) =>
      calls.push(["matrix", ...matrix]),
    uniform4fv() {},
    uniform1f() {},
    drawArrays: (...args) => calls.push(["draw", ...args]),
    getExtension: () => ({ loseContext: () => calls.push(["lose"]) }),
  };
}

test("webgl2 renders topology, applies orbit, and cleans resources", () => {
  const gl = fakeGL();
  const renderer = new WebGL2Renderer({ gl });
  renderer.initialize(sceneFixture(), planFixture("WEBGL2"));
  const receipt = renderer.present({ width: 400, height: 300 });
  const firstMatrix = gl.calls.find((call) => call[0] === "matrix");
  renderer.orbit(0.4, 0.2);
  renderer.present({ width: 400, height: 300 });
  const matrices = gl.calls.filter((call) => call[0] === "matrix");
  assert.notDeepEqual(matrices.at(-1), firstMatrix);
  assert.equal(receipt.link_count, 1);
  assert.equal(gl.calls.filter((call) => call[0] === "draw").length, 4);
  assert.equal(renderer.pick(180, 150, 100), "entity:a");
  renderer.dispose();
  assert.ok(gl.calls.some((call) => call[0] === "lose"));
});


test("webgl2 picking uses the same aspect-correct projection as rendering", () => {
  const renderer = new WebGL2Renderer({ gl: fakeGL() });
  renderer.initialize(sceneFixture(), planFixture("WEBGL2"));
  renderer.present({ width: 1600, height: 900 });
  assert.equal(renderer.pick(762.5, 450, 5), "entity:a");
  assert.equal(renderer.pick(733.333, 450, 5), null);
});
