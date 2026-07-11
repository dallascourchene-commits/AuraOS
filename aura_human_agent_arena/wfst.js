// Aura guarded-WFST projection — contextual buttons derived from admitted transitions.
(() => {
  'use strict';

  let host = document.getElementById('wfst-route-projection');
  if (!host) {
    const panel = document.querySelector('.context-actions-panel');
    if (panel) {
      host = document.createElement('div');
      host.id = 'wfst-route-projection';
      host.className = 'wfst-route-projection';
      host.setAttribute('aria-live', 'polite');
      const legacy = document.getElementById('next-actions-list');
      panel.insertBefore(host, legacy || null);
    }
  }
  if (!host) return;

  const escape = (value) => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  let lastDigest = '';
  let timer = null;

  async function fetchRoutes() {
    const response = await fetch('/api/human-agent/routes', { cache: 'no-store' });
    const result = await response.json();
    result.http_status = response.status;
    return result;
  }

  function routeDigest(packet) {
    const routing = packet?.routing || {};
    return JSON.stringify({
      grammar: routing.grammar_version,
      state: routing.state,
      recommended: (routing.recommended || []).map(item => item.transition_id),
      blocked: (routing.blocked || []).map(item => [item.transition_id, item.missing_evidence]),
    });
  }

  function activateTransition(item) {
    const actionId = item?.provenance?.action_id || '';
    if (item?.meta_transition || !actionId) {
      const input = document.getElementById('command-input');
      if (input) input.value = item.transition_id || item.label || '';
      document.getElementById('run-button')?.click();
      return;
    }
    const existing = document.querySelector(`[data-workflow-action="${CSS.escape(actionId)}"]`);
    if (existing) {
      existing.click();
      return;
    }
    fetch('/api/human-agent/workflow/action', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ action_id: actionId, payload: {} }),
    }).catch(error => {
      console.error('Failed to activate transition:', actionId, error);
      alert(`Failed to activate transition "${actionId}": ${error.message}`);
    }).finally(() => setTimeout(refresh, 50));
  }

  function render(packet) {
    const routing = packet?.routing || {};
    const recommended = (packet?.recommended || routing.recommended || []).slice(0, 4);
    const meta = (packet?.meta || routing.meta || []).slice(0, 4);
    const blocked = (packet?.blocked || routing.blocked || []).slice(0, 5);
    const statePacket = routing.state_packet || {};

    const recommendedHtml = recommended.length
      ? recommended.map(item => `
          <button type="button" class="wfst-route-button" data-transition-id="${escape(item.transition_id)}">
            <strong>${escape(item.label || item.transition_id)}</strong>
            <small>${escape(item.description || '')}</small>
            <span>${escape(item.risk || 'low')} · ${escape(item.next_state || routing.state || '')}</span>
          </button>`).join('')
      : '<p class="placeholder">No admitted workflow transition is currently recommended.</p>';

    const metaHtml = meta.length
      ? `<div class="wfst-meta-actions">${meta.map(item => `
          <button type="button" data-transition-id="${escape(item.transition_id)}">${escape(item.label || item.transition_id)}</button>`).join('')}</div>`
      : '';

    const blockedHtml = blocked.length
      ? `<details class="wfst-blocked"><summary>${blocked.length} blocked transition${blocked.length === 1 ? '' : 's'}</summary>
          ${blocked.map(item => {
            const guards = (item.failed_guards || []).map(guard => guard.guard_id).join(' · ');
            const missing = (item.missing_evidence || []).join(' · ');
            return `<article><strong>${escape(item.label || item.transition_id)}</strong>
              <span>${escape(guards || 'hard guard failed')}</span>
              ${missing ? `<small>Missing: ${escape(missing)}</small>` : ''}</article>`;
          }).join('')}</details>`
      : '';

    host.innerHTML = `
      <div class="wfst-route-head">
        <span><strong>${escape(routing.state || packet.current_phase || 'FRAME')}</strong> · ${escape(routing.grammar_version || 'grammar unavailable')}</span>
        <small>state ${escape((statePacket.phase_hash || '').slice(0, 12))}</small>
      </div>
      <div class="wfst-recommended">${recommendedHtml}</div>
      ${metaHtml}
      ${blockedHtml}
      <p class="wfst-authority">Buttons are projections of admitted transitions. Hard guards run before weights.</p>`;

    const byId = new Map([...recommended, ...meta].map(item => [item.transition_id, item]));
    host.querySelectorAll('[data-transition-id]').forEach(button => {
      button.addEventListener('click', () => activateTransition(byId.get(button.dataset.transitionId)));
    });
  }

  async function refresh() {
    try {
      const packet = await fetchRoutes();
      const digest = routeDigest(packet);
      if (digest !== lastDigest) {
        lastDigest = digest;
        render(packet);
      }
    } catch (error) {
      host.innerHTML = `<p class="placeholder">Guarded route projection unavailable: ${escape(error.message)}</p>`;
    }
  }

  document.addEventListener('click', event => {
    if (event.target.closest('[data-workflow-action], #run-button, #workflow-objective-btn')) {
      setTimeout(refresh, 80);
    }
  });

  timer = setInterval(refresh, 1000);
  window.addEventListener('beforeunload', () => clearInterval(timer));
  refresh();
})();
