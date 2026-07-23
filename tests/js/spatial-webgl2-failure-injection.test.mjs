import test from "node:test";
import assert from "node:assert/strict";

import { WebGL2Renderer } from "../../aura_spatial_web/webgl2_renderer.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

function fakeGL(options = {}) {
  let id = 0;
  let shaderAllocation = 0;
  let bufferAllocation = 0;
  let bufferUpload = 0;
  const calls = [];
  const gl = {
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
    createShader(type) {
      shaderAllocation += 1;
      calls.push(["createShader", type]);
      if (options.failShaderAllocation === shaderAllocation) return null;
      return { id: ++id, type };
    },
    shaderSource(shader) {
      calls.push(["shaderSource", shader.id]);
      if (options.throwShaderSource) throw new Error("shaderSource exploded");
    },
    compileShader(shader) {
      calls.push(["compileShader", shader.id]);
      if (options.throwCompileShader) throw new Error("compileShader exploded");
    },
    getShaderParameter(shader) {
      return options.failShaderCompileType !== shader.type;
    },
    getShaderInfoLog: () => "compile diagnostic",
    deleteShader(shader) {
      calls.push(["deleteShader", shader.id]);
      if (options.throwDeleteShader) throw new Error("deleteShader exploded");
    },
    createProgram() {
      calls.push(["createProgram"]);
      return options.failProgramAllocation ? null : { id: ++id };
    },
    attachShader(program, shader) {
      calls.push(["attachShader", program.id, shader.id]);
      if (options.throwAttachShader) throw new Error("attachShader exploded");
    },
    linkProgram(program) {
      calls.push(["linkProgram", program.id]);
      if (options.throwLinkProgram) throw new Error("linkProgram exploded");
    },
    getProgramParameter: () => !options.failProgramLink,
    getProgramInfoLog: () => "link diagnostic",
    deleteProgram(program) {
      calls.push(["deleteProgram", program.id]);
      if (options.throwDeleteProgram) throw new Error("deleteProgram exploded");
    },
    createBuffer() {
      bufferAllocation += 1;
      calls.push(["createBuffer", bufferAllocation]);
      if (options.failBufferAllocation === bufferAllocation) return null;
      return { id: ++id, allocation: bufferAllocation };
    },
    bindBuffer(_target, buffer) {
      calls.push(["bindBuffer", buffer.id]);
      if (options.throwBindBufferAt === buffer.allocation) {
        throw new Error("bindBuffer exploded");
      }
    },
    bufferData() {
      bufferUpload += 1;
      calls.push(["bufferData", bufferUpload]);
      if (options.throwBufferDataAt === bufferUpload) {
        throw new Error("bufferData exploded");
      }
    },
    deleteBuffer(buffer) {
      calls.push(["deleteBuffer", buffer.id]);
      if (options.throwDeleteBuffer) throw new Error("deleteBuffer exploded");
    },
    viewport() {},
    enable() {},
    clearColor() {},
    clear() {},
    useProgram() {},
    getAttribLocation: () => 0,
    enableVertexAttribArray() {},
    vertexAttribPointer() {},
    getUniformLocation: () => 0,
    uniformMatrix4fv() {},
    uniform4fv() {},
    uniform1f() {},
    drawArrays() {},
    getExtension() {
      if (options.noLoseContext) return null;
      return {
        loseContext() {
          calls.push(["lose"]);
          if (options.throwLoseContext) throw new Error("loseContext exploded");
        },
      };
    },
  };
  return gl;
}

function expectInitializationFailure(options, pattern) {
  const gl = fakeGL(options);
  const renderer = new WebGL2Renderer({ gl });
  assert.throws(
    () => renderer.initialize(sceneFixture(), planFixture("WEBGL2")),
    pattern,
  );
  assert.equal(renderer.status().state, "LOST");
  return { gl, renderer };
}

test("WebGL2 releases a first buffer when the second allocation fails", () => {
  const { gl, renderer } = expectInitializationFailure(
    { failBufferAllocation: 2 },
    /unable to allocate buffer/,
  );
  assert.equal(gl.calls.filter(([name]) => name === "deleteBuffer").length, 1);
  assert.equal(gl.calls.filter(([name]) => name === "deleteProgram").length, 1);
  assert.equal(gl.calls.filter(([name]) => name === "lose").length, 1);
  assert.equal(renderer.status().resource_count, 0);
});

test("WebGL2 releases a buffer whose upload throws", () => {
  const { gl, renderer } = expectInitializationFailure(
    { throwBufferDataAt: 1 },
    /bufferData exploded/,
  );
  assert.equal(gl.calls.filter(([name]) => name === "deleteBuffer").length, 1);
  assert.equal(renderer.status().resource_count, 0);
});

test("WebGL2 releases earlier shaders when fragment allocation fails", () => {
  const { gl } = expectInitializationFailure(
    { failShaderAllocation: 2 },
    /unable to allocate shader/,
  );
  assert.equal(gl.calls.filter(([name]) => name === "deleteShader").length, 1);
  assert.equal(gl.calls.filter(([name]) => name === "lose").length, 1);
});

test("WebGL2 releases shaders when program allocation or linking fails", () => {
  for (const options of [
    { failProgramAllocation: true },
    { failProgramLink: true },
    { throwAttachShader: true },
    { throwLinkProgram: true },
  ]) {
    const { gl, renderer } = expectInitializationFailure(options, /program|attachShader|linkProgram/);
    assert.equal(gl.calls.filter(([name]) => name === "deleteShader").length, 2);
    assert.equal(renderer.status().resource_count, 0);
  }
});

test("WebGL2 preserves cleanup failures while context loss releases handles", () => {
  const { gl, renderer } = expectInitializationFailure(
    { failBufferAllocation: 2, throwDeleteBuffer: true },
    AggregateError,
  );
  assert.equal(gl.calls.filter(([name]) => name === "lose").length, 1);
  assert.equal(renderer.status().resource_count, 0);
  assert.equal(renderer.dispose().state, "DISPOSED");
});

test("WebGL2 retains failed releases for a later disposal retry", () => {
  const options = {
    failBufferAllocation: 2,
    throwDeleteBuffer: true,
    throwLoseContext: true,
  };
  const { gl, renderer } = expectInitializationFailure(options, AggregateError);
  assert.equal(renderer.status().resource_count, 1);
  options.throwDeleteBuffer = false;
  options.throwLoseContext = false;
  assert.equal(renderer.dispose().state, "DISPOSED");
  assert.equal(renderer.status().resource_count, 0);
  assert.ok(gl.calls.filter(([name]) => name === "deleteBuffer").length >= 2);
});

test("WebGL2 compile cleanup failures remain terminal and inspectable", () => {
  const { gl, renderer } = expectInitializationFailure(
    { failShaderCompileType: 1, throwDeleteShader: true },
    AggregateError,
  );
  assert.equal(renderer.status().state, "LOST");
  assert.equal(gl.calls.filter(([name]) => name === "lose").length, 1);
});

test("WebGL2 survives repeated initialize, present, and dispose cycles", () => {
  for (let index = 0; index < 64; index += 1) {
    const gl = fakeGL();
    const renderer = new WebGL2Renderer({ gl });
    renderer.initialize(sceneFixture(), planFixture("WEBGL2"));
    renderer.present({ width: 640 + (index % 3), height: 360 + (index % 5) });
    assert.equal(renderer.dispose().state, "DISPOSED");
    assert.equal(renderer.dispose().state, "DISPOSED");
    assert.equal(renderer.status().resource_count, 0);
  }
});
