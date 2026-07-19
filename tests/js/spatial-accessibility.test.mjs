import test from "node:test";
import assert from "node:assert/strict";
import { Accessible2DRenderer, buildAccessibleSceneModel } from "../../aura_spatial_web/accessibility.js";
import { planFixture, sceneFixture } from "./spatial-fixture.mjs";

class FakeElement {
  constructor(ownerDocument, tagName = "div") {
    this.ownerDocument = ownerDocument;
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.listeners = new Map();
    this.innerHTML = "";
    this.tabIndex = -1;
  }
  setAttribute(name, value) { this[name] = value; }
  append(...children) { this.children.push(...children); }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  replaceChildren(...children) { this.children = [...children]; }
}

class FakeDocument {
  createElement(tagName) { return new FakeElement(this, tagName); }
}

test("accessible model has deterministic parity", () => {
  const model = buildAccessibleSceneModel(sceneFixture());
  assert.deepEqual(model.rows.map((item) => item.entity_id), ["entity:a", "entity:b"]);
  assert.equal(model.rows[0].outbound_links, 1);
  assert.equal(model.rows[1].inbound_links, 1);
  assert.equal(model.production_mutation, false);
});

test("accessible renderer accepts the validated scene retained by the adapter", () => {
  const document = new FakeDocument();
  const container = new FakeElement(document);
  const interactions = [];
  const renderer = new Accessible2DRenderer({
    container,
    onInteraction: (packet) => interactions.push(packet),
  });
  renderer.initialize(sceneFixture(), planFixture("ACCESSIBLE_2D"));
  const receipt = renderer.present();
  assert.equal(receipt.renderer, "ACCESSIBLE_2D");
  assert.equal(receipt.renderer_authority, false);
  assert.equal(renderer.model.rows.length, 2);
  assert.equal(container.children[0].tagName, "table");
  renderer.dispose();
  assert.equal(container.children.length, 0);
  assert.deepEqual(interactions, []);
});
