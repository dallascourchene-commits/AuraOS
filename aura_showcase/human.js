'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;

  function actionId(item) {
    return item?.provenance?.action_id || item?.action_id || '';
  }

  function rankVector(item) {
    const rank = item?.rank || {};
    return [
      `risk ${rank.unresolved_risk ?? '—'}`,
      `gap ${rank.declared_evidence_gap ?? '—'}`,
      `uncertainty ${rank.empirical_uncertainty ?? '—'}`,
      `ambiguity ${rank.semantic_ambiguity ?? '—'}`,
      `switch ${rank.context_switch_cost ?? '—'}`,
      `latency ${rank.latency_cost ?? '—'}`,
      `tokens ${rank.token_cost ?? '—'}`,
      `thermal ${rank.thermal_cost ?? '—'}`,
      `user-fit ${rank.negative_user_fit === undefined ? '—' : Math.abs(Number(rank.negative_user_fit)).toFixed(2)}`,
    ].join(' · ');
  }

  function slotText(slots) {
    return ['DIR', 'ASP', 'CLASS', 'SUBJ', 'VOICE', 'STEM']
      .map(key => `${key}=${slots?.[key] || '—'}`).join(' · ');
  }

  function transitionCard(item, index, compact = false) {
    const capability = (item.requested_capabilities || []).join(', ') || 'no external tool capability';
    const requires = (item.required_evidence || []).join(', ') || 'no additional evidence';
    const produces = (item.produced_evidence || []).join(', ') || 'guidance only';
    const resolvedSlots = item.intent_slots || (S.humanGuide?.available_actions || []).find(a => actionId(a) === actionId(item))?.intent_slots;
    const slots = resolvedSlots ? `<span class="human-route-slots">${esc(slotText(resolvedSlots))}</span>` : '';
    return `<button class="human-route-action${compact ? ' is-compact' : ''}" data-human-transition="${esc(item.transition_id)}" data-human-action="${esc(actionId(item))}">
      <span class="human-route-rank">${index + 1}</span>
      <span class="human-route-copy">
        <strong>${esc(item.label || item.transition_id)}</strong>
        <small>${esc(item.description || '')}</small>
        <code>${esc(item.from_state || '')} → ${esc(item.next_state || '')} · ${esc(item.risk || 'low')} risk</code>
        ${slots}
        <span class="human-route-evidence">Requires: ${esc(requires)} · Produces: ${esc(produces)} · Capability: ${esc(capability)}</span>
        <span class="human-rank-vector">WFST rank vector: ${esc(rankVector(item))}</span>
      </span>
    </button>`;
  }

  function blockedCard(item) {
    const guards = (item.failed_guards || []).map(guard => typeof guard === 'string' ? guard : (guard.guard_id || guard.id)).filter(Boolean).join(' · ') || 'hard guard failed';
    const missing = (item.missing_evidence || []).join(' · ') || 'policy or capability requirement';
    const resolvedSlots = item.intent_slots || (S.humanGuide?.blocked_actions || []).find(b => actionId(b) === actionId(item))?.intent_slots;
    const slots = resolvedSlots ? `<small>${esc(slotText(resolvedSlots))}</small>` : '';
    return `<article class="human-blocked-route"><strong>${esc(item.label || item.transition_id)}</strong><span>${esc(guards)}</span><small>Missing: ${esc(missing)}</small>${slots}</article>`;
  }

  function bindRouteButtons(host) {
    host.querySelectorAll('[data-human-action]').forEach(button => button.addEventListener('click', () => {
      const id = button.dataset.humanAction;
      if (id) runAction(id);
    }));
  }

  function renderSlots(slots) {
    const host = $('human-six-slots');
    if (!host) return;
    const order = ['DIR', 'ASP', 'CLASS', 'SUBJ', 'VOICE', 'STEM'];
    host.innerHTML = order.map(key => `<article><span>${esc(key)}</span><strong>${esc(slots?.[key] || '—')}</strong></article>`).join('');
  }

  S.renderHumanGuide = () => {
    const guide = S.humanGuide || {};
    const gate = guide.gate || {};
    $('human-guide-summary').textContent = guide.summary || 'Import the Civic handoff to load the current gate rules.';
    renderSlots(gate.intent_slots || {});
    $('human-gate-rules').innerHTML = (gate.rules || []).length
      ? `<h3>${esc(gate.title || 'Current gate')}</h3><p>${esc(gate.purpose || '')}</p><ul>${gate.rules.map(rule => `<li>${esc(rule)}</li>`).join('')}</ul>`
      : '<p class="muted">No gate rules loaded yet.</p>';
  };

  S.renderHumanRoutes = () => {
    const workflow = S.workflow || {};
    const routing = workflow.routing || {};
    const routed = (routing.available || workflow.available || []).filter(item => !item.meta_transition && actionId(item));
    const recommended = routed.slice(0, 4);
    const available = routed.slice(4, 10);
    const blocked = (workflow.blocked || routing.blocked || []).filter(item => !item.meta_transition).slice(0, 8);
    const statePacket = workflow.state_packet || routing.state_packet || {};

    $('human-grammar').textContent = workflow.grammar_version || routing.grammar_version || 'grammar unavailable';
    $('human-phase-hash').textContent = `state ${(statePacket.phase_hash || '').slice(0, 12) || '—'}`;

    const recommendedHost = $('human-recommended-actions');
    recommendedHost.innerHTML = recommended.length
      ? recommended.map((item, index) => transitionCard(item, index)).join('')
      : '<p class="muted">No admitted non-meta transition is currently recommended. Inspect blocked transitions for the missing evidence.</p>';
    bindRouteButtons(recommendedHost);

    const availableHost = $('human-available-actions');
    availableHost.innerHTML = available.length
      ? available.map((item, index) => transitionCard(item, index, true)).join('')
      : '<p class="muted">No other state-local action is currently admitted.</p>';
    bindRouteButtons(availableHost);

    $('human-blocked-actions').innerHTML = blocked.length
      ? blocked.map(blockedCard).join('')
      : '<p class="muted">No state-local transition is blocked.</p>';
  };

  S.renderHandoff = () => {
    if (!S.handoff) { $('handoff-summary').textContent = 'No handoff imported.'; $('handoff-packet').textContent = '{}'; return; }
    const p = S.handoff;
    $('handoff-summary').innerHTML = `<strong>${esc(p.issue?.title || 'Civic issue')}</strong><p>${esc(p.issue?.question || '')}</p>`;
    $('handoff-packet').textContent = JSON.stringify({objective: p.objective, grounding: p.grounding, candidate_options: p.candidate_options, recommended_option: p.recommended_option, test_targets: p.test_targets, authority: {production_mutation: p.production_mutation, automatic_commit: p.automatic_commit, automatic_push: p.automatic_push, automatic_merge: p.automatic_merge}}, null, 2);
  };

  S.renderWorkflow = () => {
    const host = $('workflow-actions');
    if (!S.workflow?.actions) {
      $('workflow-phase').textContent = 'Not started';
      host.innerHTML = '<p class="muted">Open the Civic issue to import an exact handoff packet.</p>';
      S.renderHumanRoutes();
      S.renderHumanGuide();
      return;
    }
    $('workflow-phase').textContent = S.workflow.current_phase || 'FRAME';
    host.innerHTML = S.workflow.actions.map((action, index) => `<button class="workflow-action" data-action="${esc(action.action_id)}" data-status="${esc(action.status)}" ${action.status === 'BLOCKED' ? 'disabled' : ''}><span class="workflow-index">${index + 1}</span><span><strong>${esc(action.title)}</strong><small>${esc(action.purpose)}</small>${(action.missing_evidence || []).length ? `<small>Missing: ${esc(action.missing_evidence.join(' · '))}</small>` : ''}</span><span class="gate">${esc(action.status)}</span></button>`).join('');
    host.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => runAction(button.dataset.action)));
    S.renderHumanRoutes();
    S.renderHumanGuide();
  };

  async function refreshGuide() {
    S.humanGuide = await S.api('/api/human-agent/guide');
    S.renderHumanGuide();
    return S.humanGuide;
  }

  async function refreshWorkflow() {
    const workflow = await S.api('/api/human-agent/workflow');
    S.workflow = workflow;
    await refreshGuide();
    S.renderWorkflow();
    return workflow;
  }

  async function investigate() {
    if (!S.sessionId) return;
    const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/handoff`, {});
    if (!result.ok) return S.showCivicError(result.error || 'Handoff failed');
    S.handoff = result.handoff;
    await refreshWorkflow();
    S.renderHandoff();
    S.activateTab('human');
  }

  async function runAction(id) {
    const payload = id === 'human_review' ? {approved: false, reviewer: 'showcase_human', note: 'Reviewed for demonstration only. No merge requested.'} : {};
    const result = await S.api('/api/human-agent/workflow/action', {action_id: id, payload});
    await refreshWorkflow();
    const ok = Boolean(result.ok);
    $('workflow-result').innerHTML = `<p><span class="${ok ? 'allowed' : 'denied'}">${ok ? 'ALLOWED' : 'DENIED'}</span> · ${esc(result.action_id || id || '')}</p><p>${esc(result.message || result.error || '')}</p>${(result.missing_evidence || []).length ? `<p><strong>Missing evidence:</strong> ${result.missing_evidence.map(esc).join(' · ')}</p>` : ''}${(result.remediation || []).length ? `<p><strong>Remediation:</strong> ${result.remediation.map(item => esc(item.label || item.action)).join(' → ')}</p>` : ''}<details><summary>Exact guarded result</summary><pre>${esc(JSON.stringify(result, null, 2))}</pre></details>`;
  }

  async function askGuide(question) {
    const text = String(question || $('human-guide-input').value || '').trim();
    if (!text) return;
    $('human-guide-input').value = text;
    const result = await S.api('/api/human-agent/guide/ask', {question: text});
    $('human-guide-answer').innerHTML = result.ok
      ? `<p><strong>${esc(result.kind || 'guidance')}</strong></p><p>${esc(result.answer || '')}</p>${(result.recommended_actions || []).length ? `<p class="muted">Recommended: ${esc(result.recommended_actions.map(item => item.label).join(' · '))}</p>` : ''}`
      : `<p class="denied">${esc(result.error || 'Guidance unavailable')}</p>`;
  }

  $('investigate-issue').addEventListener('click', investigate);
  $('human-guide-ask').addEventListener('click', () => askGuide());
  $('human-guide-input').addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); askGuide(); }
  });
  document.querySelectorAll('[data-guide-question]').forEach(button => button.addEventListener('click', () => askGuide(button.dataset.guideQuestion)));
  S.renderHumanRoutes();
  S.renderHumanGuide();
})();
