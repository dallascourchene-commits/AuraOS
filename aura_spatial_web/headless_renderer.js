import { AUTHORITY_ENVELOPE, RendererAdapter } from './renderer_adapter.js';
export class HeadlessRenderer extends RendererAdapter {
  constructor() { super('HEADLESS'); }
  present() {
    if (!this.scene || !this.plan) throw new Error('headless renderer is not initialized');
    this.markPresented();
    return Object.freeze({ renderer: this.kind, outcome: 'PRESENTED', evidence_class: 'CALCULATED', scene_digest: this.scene.scene_digest, render_plan_digest: this.plan.render_plan_digest, entity_count: this.scene.entities.length, link_count: this.scene.links.length, ...AUTHORITY_ENVELOPE });
  }
}
