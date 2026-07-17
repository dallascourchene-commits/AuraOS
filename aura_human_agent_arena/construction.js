// SCO Construction Human Agent surface — read-only proposal review.
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  async function constructionApi(path, body) {
    const options = body === undefined ? {} : {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    };
    const response = await fetch(path, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `${response.status} ${response.statusText}`);
    return payload;
  }

  function authorityBanner(profile) {
    const host = $('construction-authority');
    if (!host) return;
    host.innerHTML = `
      <strong>Human decision required</strong>
      <span>Read-only · proposal-only · no physical, payment, access, safety, engineering, legal, or regulatory authority</span>
      <small>State ${escape(profile.state_digest || '')}</small>`;
  }

  function renderCandidate(candidate) {
    const blockers = candidate.blockers || [];
    const status = candidate.admissible ? 'REVIEWABLE' : 'BLOCKED';
    const role = candidate.option_role || 'NOT DISPLAYED';
    return `<article class="construction-card" data-status="${escape(status)}">
      <div class="construction-card-head">
        <span class="construction-status">${escape(status)}</span>
        <span>${escape(role)}</span>
      </div>
      <h3>${escape(candidate.title)}</h3>
      <p>${escape(candidate.summary)}</p>
      <dl>
        <div><dt>Authority route</dt><dd>${escape(candidate.authority_route)}</dd></div>
        <div><dt>Time delta</dt><dd>${escape(candidate.projected_time_delta_hours)} h</dd></div>
        <div><dt>Cost delta</dt><dd>CAD ${escape(candidate.projected_cost_delta_cad)}</dd></div>
        <div><dt>Idle delta</dt><dd>${escape(candidate.projected_idle_delta_hours)} h</dd></div>
      </dl>
      ${blockers.length ? `<div class="construction-blockers"><strong>Hard blockers</strong>${blockers.map(item => `<span>${escape(item)}</span>`).join('')}</div>` : ''}
      <button type="button" data-construction-candidate="${escape(candidate.candidate_id)}">Inspect bounded record</button>
      ${candidate.recommended ? '<div class="construction-recommendation">Recommended for human review — not authorized for execution</div>' : ''}
    </article>`;
  }

  function renderProfile(profile) {
    authorityBanner(profile);
    const status = $('construction-status');
    if (status) status.textContent = `${profile.mode} · ${profile.lane} · ${profile.route_class}`;
    const summary = $('construction-summary');
    if (summary) {
      summary.innerHTML = `
        <article><span>Project</span><strong>${escape(profile.project_id)}</strong></article>
        <article><span>Evaluation</span><strong>${escape(profile.evaluation_id)}</strong></article>
        <article><span>Recommended</span><strong>${escape(profile.recommended_candidate_id || 'none')}</strong></article>
        <article><span>Next gate</span><strong>${escape(profile.next_authority_route || 'owner review')}</strong></article>`;
    }
    const host = $('construction-candidates');
    if (host) {
      host.innerHTML = (profile.candidates || []).map(renderCandidate).join('') || '<p class="placeholder">No candidates projected.</p>';
      host.querySelectorAll('[data-construction-candidate]').forEach(button => {
        button.addEventListener('click', () => inspectCandidate(button.dataset.constructionCandidate));
      });
    }
  }

  async function inspectCandidate(candidateId) {
    const host = $('construction-inspector');
    if (host) host.innerHTML = '<p class="placeholder">Loading bounded candidate record…</p>';
    try {
      const result = await constructionApi(`/api/human-agent/construction/candidates/${encodeURIComponent(candidateId)}`);
      if (host) host.innerHTML = `<pre>${escape(JSON.stringify(result, null, 2))}</pre>`;
    } catch (error) {
      if (host) host.textContent = `Candidate unavailable: ${error.message}`;
    }
  }

  async function loadObservatory() {
    const host = $('construction-observatory');
    try {
      const result = await constructionApi('/api/human-agent/construction/observatory');
      if (host) host.innerHTML = `<pre>${escape(JSON.stringify(result, null, 2))}</pre>`;
    } catch (error) {
      if (host) host.textContent = `Observatory unavailable: ${error.message}`;
    }
  }

  async function prepareHandoff() {
    const host = $('construction-handoff-result');
    try {
      const result = await constructionApi('/api/human-agent/construction/handoff', {
        target_arena_id: $('construction-handoff-target')?.value || 'agent_bridge_arena',
      });
      if (host) host.innerHTML = `<pre>${escape(JSON.stringify(result, null, 2))}</pre>`;
    } catch (error) {
      if (host) host.textContent = `Handoff unavailable: ${error.message}`;
    }
  }

  async function loadConstructionProfile() {
    const status = $('construction-status');
    if (status) status.textContent = 'Loading exact synthetic profile…';
    try {
      const result = await constructionApi('/api/human-agent/construction/profile');
      renderProfile(result.profile || {});
      await loadObservatory();
    } catch (error) {
      if (status) status.textContent = `Unavailable: ${error.message}`;
      const host = $('construction-candidates');
      if (host) host.innerHTML = '<p class="placeholder">Start the Human Agent server in demo mode or load an exact reviewed Construction state. No state is invented.</p>';
    }
  }

  $('construction-refresh')?.addEventListener('click', loadConstructionProfile);
  $('construction-handoff')?.addEventListener('click', prepareHandoff);
  document.querySelector('[data-surface="construction-workspace"]')?.addEventListener('click', loadConstructionProfile);
})();
