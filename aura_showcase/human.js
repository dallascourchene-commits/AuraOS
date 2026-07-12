'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;

  S.renderHandoff = () => {
    if (!S.handoff) { $('handoff-summary').textContent = 'No handoff imported.'; $('handoff-packet').textContent = '{}'; return; }
    const p = S.handoff;
    $('handoff-summary').innerHTML = `<strong>${esc(p.issue?.title || 'Civic issue')}</strong><p>${esc(p.issue?.question || '')}</p>`;
    $('handoff-packet').textContent = JSON.stringify({objective: p.objective, grounding: p.grounding, candidate_options: p.candidate_options, recommended_option: p.recommended_option, test_targets: p.test_targets, authority: {production_mutation: p.production_mutation, automatic_commit: p.automatic_commit, automatic_push: p.automatic_push, automatic_merge: p.automatic_merge}}, null, 2);
  };

  S.renderWorkflow = () => {
    const host = $('workflow-actions');
    if (!S.workflow?.actions) { $('workflow-phase').textContent = 'Not started'; host.innerHTML = '<p class="muted">Open the Civic issue to import an exact handoff packet.</p>'; return; }
    $('workflow-phase').textContent = S.workflow.current_phase || 'FRAME';
    host.innerHTML = S.workflow.actions.map((action, index) => `<button class="workflow-action" data-action="${esc(action.action_id)}" data-status="${esc(action.status)}" ${action.status === 'BLOCKED' ? 'disabled' : ''}><span class="workflow-index">${index + 1}</span><span><strong>${esc(action.title)}</strong><small>${esc(action.purpose)}</small></span><span class="gate">${esc(action.status)}</span></button>`).join('');
    host.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => runAction(button.dataset.action)));
  };

  async function investigate() {
    if (!S.sessionId) return;
    const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/handoff`, {});
    if (!result.ok) return S.showCivicError(result.error || 'Handoff failed');
    S.handoff = result.handoff; S.workflow = result.workflow;
    S.renderHandoff(); S.renderWorkflow(); S.activateTab('human');
  }

  async function runAction(actionId) {
    const payload = actionId === 'human_review' ? {approved: false, reviewer: 'showcase_human', note: 'Reviewed for demonstration only. No merge requested.'} : {};
    const result = await S.api('/api/human-agent/workflow/action', {action_id: actionId, payload});
    S.workflow = result.workflow || await S.api('/api/human-agent/workflow');
    S.renderWorkflow();
    const ok = Boolean(result.ok);
    $('workflow-result').innerHTML = `<p><span class="${ok ? 'allowed' : 'denied'}">${ok ? 'ALLOWED' : 'DENIED'}</span> · ${esc(result.action_id || '')}</p><p>${esc(result.message || result.error || '')}</p>${(result.missing_evidence || []).length ? `<p><strong>Missing evidence:</strong> ${result.missing_evidence.map(esc).join(' · ')}</p>` : ''}${(result.remediation || []).length ? `<p><strong>Remediation:</strong> ${result.remediation.map(item => esc(item.label || item.action)).join(' → ')}</p>` : ''}<details><summary>Exact result</summary><pre>${esc(JSON.stringify(result, null, 2))}</pre></details>`;
  }

  $('investigate-issue').addEventListener('click', investigate);
})();
