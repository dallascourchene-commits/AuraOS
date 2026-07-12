'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;

  function actionId(item) {
    return item?.provenance?.action_id || '';
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

  function transitionCard(item, index, compact = false) {
    const capability = (item.requested_capabilities || []).join(', ') || 'no external tool capability';
    const requires = (item.required_evidence || []).join(', ') || 'no additional evidence';
    const produces = (item.produced_evidence || []).join(', ') || 'guidance only';
    return `<button class="human-route-action${compact ? ' is-compact' : ''}" data-human-transition="${esc(item.transition_id)}" data-human-action="${esc(actionId(item))}">
      <span class="human-route-rank">${index + 1}</span>
      <span class="human-route-copy">
        <strong>${esc(item.label || item.transition_id)}</strong>
        <small>${esc(item.description || '')}</small>
        <code>${esc(item.from_state || '')} → ${esc(item.next_state || '')} · ${esc(item.risk || 'low')} risk</code>
        <span class="human-route-evidence">Requires: ${esc(requires)} · Produces: ${esc(produces)} · Capability: ${esc(capability)}</span>
        <span class="human-rank-vector">WFST rank vector: ${esc(rankVector(item))}</span>
      </span>
    </button>`;
  }

  function blockedCard(item) {
    const guards = (item.failed_guards || []).map(guard => guard.guard_id || guard.id).filter(Boolean).join(' · ') || 'hard guard failed';
    const missing = (item.missing_evidence || []).join(' · ') || 'policy or capability requirement';
    return `<article class="human-blocked-route"><strong>${esc(item.label || item.transition_id)}</strong><span>${esc(guards)}</span><small>Missing: ${esc(missing)}</small></article>`;
  }

  function bindRouteButtons(host) {
    host.querySelectorAll('[data-human-action]').forEach(button => button.addEventListener('click', () => {
      const id = button.dataset.humanAction;
      if (id) runAction(id);
    }));
  }

  S.renderHumanRoutes = () => {
    const workflow = S.workflow || {};
    const routing = workflow.routing || {};
    const recommended = (workflow.recommended || routing.recommended || []).filter(item => !item.meta_transition && actionId(item)).slice(0, 4);
    const recommendedIds = new Set(recommended.map(item => item.transition_id));
    const available = (workflow.available || routing.available || []).filter(item => !item.meta_transition && actionId(item) && !recommendedIds.has(item.transition_id)).slice(0, 6);
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
      return;
    }
    $('workflow-phase').textContent = S.workflow.current_phase || 'FRAME';
    host.innerHTML = S.workflow.actions.map((action, index) => `<button class="workflow-action" data-action="${esc(action.action_id)}" data-status="${esc(action.status)}" ${action.status === 'BLOCKED' ? 'disabled' : ''}><span class="workflow-index">${index + 1}</span><span><strong>${esc(action.title)}</strong><small>${esc(action.purpose)}</small>${(action.missing_evidence || []).length ? `<small>Missing: ${esc(action.missing_evidence.join(' · '))}</small>` : ''}</span><span class="gate">${esc(action.status)}</span></button>`).join('');
    host.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => runAction(button.dataset.action)));
    S.renderHumanRoutes();
  };

  async function refreshWorkflow() {
    const workflow = await S.api('/api/human-agent/workflow');
    S.workflow = workflow;
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

  $('investigate-issue').addEventListener('click', investigate);
  S.renderHumanRoutes();
})();
