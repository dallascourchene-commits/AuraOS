'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;
  if (!S || !$) return;

  function addStylesheet() {
    if (document.querySelector('link[href="crucible.css"]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'crucible.css';
    document.head.appendChild(link);
  }

  function createCrucibleSurface() {
    if ($('crucible-view')) return;
    const main = document.querySelector('main');
    if (!main) return;
    const section = document.createElement('section');
    section.id = 'crucible-view';
    section.className = 'view';
    section.innerHTML = `
      <section class="hero crucible-hero">
        <div>
          <p class="eyebrow">Learning Arena · Arena Crucible</p>
          <h1>Learn only from verified experience.</h1>
          <p class="lede">The Crucible reads complete ArenaExperience records, evaluates OutcomeVectors across TRAIN, VALIDATION, and SHADOW, and emits reviewable crystallization proposals. A prompt alone is never treated as learning.</p>
        </div>
        <div class="hero-actions">
          <button id="crucible-refresh" class="secondary">Refresh evidence</button>
          <button id="crucible-run" class="primary">Run proposal cycle</button>
        </div>
      </section>

      <section class="crucible-pipeline-card">
        <div class="section-head">
          <div><p class="eyebrow">Verified learning path</p><h2>Intention becomes learning only after proof</h2></div>
          <span id="crucible-state" class="pill">loading</span>
        </div>
        <div class="crucible-pipeline">
          <article><b>1</b><strong>Observe</strong><span>Compile and explain intent</span></article>
          <article><b>2</b><strong>Execute</strong><span>Run in a governed Arena</span></article>
          <article><b>3</b><strong>Verify</strong><span>Preserve measured evidence</span></article>
          <article><b>4</b><strong>Record</strong><span>ArenaExperience + OutcomeVector</span></article>
          <article><b>5</b><strong>Separate</strong><span>TRAIN · VALIDATION · SHADOW</span></article>
          <article><b>6</b><strong>Propose</strong><span>Verifier and human review</span></article>
        </div>
      </section>

      <section class="crucible-grid">
        <section class="crucible-main-card">
          <div id="crucible-metrics" class="learning-metrics"></div>
          <section class="crucible-intake-card">
            <div class="section-head"><div><p class="eyebrow">Current lineage intake</p><h2>Question entering the learning path</h2></div></div>
            <div id="crucible-intake"><p class="muted">No Observatory intake has been sent.</p></div>
          </section>
          <section class="crucible-records-card">
            <div class="section-head"><div><p class="eyebrow">Observable experience ledger</p><h2>Recent Arena experiences</h2></div></div>
            <div id="crucible-experiences"><p class="muted">Loading experience ledger…</p></div>
          </section>
          <section class="crucible-proposals-card">
            <div class="section-head"><div><p class="eyebrow">Proposal-only output</p><h2>Recent crystallization proposals</h2></div></div>
            <div id="crucible-proposals"><p class="muted">Loading proposals…</p></div>
          </section>
          <details class="crucible-run-details"><summary>Inspect last proposal cycle</summary><pre id="crucible-run-output">{}</pre></details>
        </section>
        <aside class="crucible-authority-card">
          <p class="eyebrow">Crucible authority boundary</p>
          <h2>Learning may propose—not promote</h2>
          <div class="guardrail-list allowed-list">
            <h3 class="allowed">Admitted</h3>
            <div class="guardrail-item">✓ Read complete observable experiences</div>
            <div class="guardrail-item">✓ Evaluate OutcomeVector dimensions</div>
            <div class="guardrail-item">✓ Split TRAIN / VALIDATION / SHADOW</div>
            <div class="guardrail-item">✓ Replay admitted alternatives</div>
            <div class="guardrail-item">✓ Store CRYSTALLIZATION_PROPOSED packets</div>
          </div>
          <div class="guardrail-list blocked-list">
            <h3 class="denied">Blocked</h3>
            <div class="guardrail-item">✕ Learn directly from a raw prompt</div>
            <div class="guardrail-item">✕ Capture hidden chain-of-thought</div>
            <div class="guardrail-item">✕ Change hard guards or capabilities</div>
            <div class="guardrail-item">✕ Promote an active grammar</div>
            <div class="guardrail-item">✕ Commit, push, or merge</div>
          </div>
          <div class="crucible-controls">
            <button id="crucible-pause" class="secondary">Pause Crucible</button>
            <button id="crucible-resume" class="secondary">Resume Crucible</button>
          </div>
          <div id="crucible-notice" class="notice">Runtime-local SQLite ledgers remain authoritative. This screen displays sanitized observable summaries only.</div>
        </aside>
      </section>`;
    main.appendChild(section);
  }

  function installNavigation() {
    const nav = document.querySelector('.topbar nav');
    const oldTab = nav?.querySelector('[data-tab="learning"]');
    if (oldTab) oldTab.textContent = 'Aura Observatory';
    if (nav && !nav.querySelector('[data-tab="crucible"]')) {
      const button = document.createElement('button');
      button.className = 'tab';
      button.dataset.tab = 'crucible';
      button.textContent = 'Learning Arena / Crucible';
      nav.appendChild(button);
    }

    const originalActivate = S.activateTab;
    S.activateTab = name => {
      if (name !== 'crucible') {
        originalActivate(name);
        $('crucible-view')?.classList.remove('is-active');
      } else {
        document.querySelectorAll('.tab').forEach(node => node.classList.toggle('is-active', node.dataset.tab === 'crucible'));
        $('civic-view')?.classList.remove('is-active');
        $('human-view')?.classList.remove('is-active');
        $('learning-view')?.classList.remove('is-active');
        $('crucible-view')?.classList.add('is-active');
        refreshCrucible();
      }
    };
  }

  function relabelObservatory() {
    const view = $('learning-view');
    if (!view) return;
    view.dataset.surfaceIdentity = 'AURA_OBSERVATORY';
    const hero = view.querySelector('.learning-hero');
    const eyebrow = hero?.querySelector('.eyebrow');
    const heading = hero?.querySelector('h1');
    const lede = hero?.querySelector('.lede');
    if (eyebrow) eyebrow.textContent = 'Aura Observatory · deterministic glass-box routing';
    if (heading) heading.textContent = 'See how Aura understood and bounded your intention.';
    if (lede) lede.textContent = 'Enter ordinary bulk intention, inspect every local routing transformation, and hand the bounded result to the Human Agent Arena or the verified Learning Arena path.';
    const reset = $('learning-reset');
    if (reset) reset.textContent = 'Clear Observatory';
    const railEyebrow = $('learning-rail')?.closest('.learning-rail-card')?.querySelector('.eyebrow');
    if (railEyebrow) railEyebrow.textContent = 'Aura Observatory · optional architecture tour';
  }

  function installObservatoryHandoffs() {
    const toolbar = document.querySelector('.learning-workspace-toolbar');
    if (!toolbar || $('observatory-open-human')) return;
    const actions = document.createElement('div');
    actions.className = 'observatory-handoff-actions';
    actions.innerHTML = `
      <button id="observatory-open-human" type="button" class="primary" disabled>Open in Human Agent Arena</button>
      <button id="observatory-open-learning" type="button" class="secondary" disabled>Send question to Learning Arena</button>`;
    toolbar.appendChild(actions);
    $('observatory-open-human').addEventListener('click', openInHumanAgent);
    $('observatory-open-learning').addEventListener('click', sendToLearningArena);
  }

  async function openInHumanAgent() {
    if (!S.intentTrace) return;
    const button = $('observatory-open-human');
    button.disabled = true;
    button.textContent = 'Opening governed workflow…';
    try {
      const result = await S.api('/api/showcase/observatory/handoff/human', {trace: S.intentTrace});
      if (!result.ok) throw new Error(result.error || result.reason || 'Human Agent handoff denied');
      S.handoff = result.handoff;
      S.workflow = result.workflow;
      S.humanGuide = result.guide;
      S.renderHandoff?.();
      S.renderWorkflow?.();
      S.renderHumanGuide?.();
      S.setLearningWorkspaceStatus('Bounded intention opened in a clean Human Agent workflow');
      S.activateTab('human');
    } catch (error) {
      S.setLearningWorkspaceStatus(error.message);
    } finally {
      button.disabled = false;
      button.textContent = 'Open in Human Agent Arena';
    }
  }

  async function sendToLearningArena() {
    if (!S.intentTrace) return;
    const button = $('observatory-open-learning');
    button.disabled = true;
    button.textContent = 'Preserving lineage…';
    try {
      const result = await S.api('/api/showcase/observatory/handoff/learning', {trace: S.intentTrace});
      if (!result.ok) throw new Error(result.error || result.reason || 'Learning intake denied');
      S.crucibleIntake = result;
      S.setLearningWorkspaceStatus('Question preserved as pre-experience lineage; verification is still required');
      S.activateTab('crucible');
    } catch (error) {
      S.setLearningWorkspaceStatus(error.message);
    } finally {
      button.disabled = false;
      button.textContent = 'Send question to Learning Arena';
    }
  }

  function metric(label, value) {
    return `<article><strong>${esc(value)}</strong><span>${esc(label)}</span></article>`;
  }

  function outcomeSummary(vector) {
    const entries = Object.entries(vector || {}).filter(([, value]) => value !== null && value !== '' && value !== undefined);
    return entries.slice(0, 5).map(([key, value]) => `<span>${esc(key.replaceAll('_', ' '))}: ${esc(typeof value === 'number' ? value.toFixed(2) : value)}</span>`).join('');
  }

  function renderCrucible(packet) {
    const service = packet.service || {};
    const ledger = packet.ledger || {};
    $('crucible-state').textContent = packet.paused ? 'paused' : 'proposal-only active';
    $('crucible-metrics').innerHTML = [
      metric('experience records', packet.experience_count || 0),
      metric('eligible verified records', packet.eligible_experience_count || 0),
      metric('legacy / incomplete', packet.legacy_experience_count || 0),
      metric('stored proposals', packet.proposal_count || 0),
    ].join('');

    const intake = packet.intake || {};
    $('crucible-intake').innerHTML = intake.ok
      ? `<article class="crucible-intake"><span class="pill">${esc(intake.status || 'intake')}</span><h3>${esc(intake.objective || 'Untitled intention')}</h3><p>${esc(intake.reason || '')}</p><div class="crucible-sequence">${(intake.required_sequence || []).map((item, index) => `<span><b>${index + 1}</b>${esc(item.replaceAll('_', ' '))}</span>`).join('')}</div><p class="muted">Eligible now: ${intake.eligible_for_crucible ? 'yes' : 'no'} · trace ${(intake.observatory_trace_digest || '').slice(0, 12)}</p></article>`
      : '<p class="muted">No Observatory intake has been sent. Existing verified experiences can still be mined.</p>';

    const experiences = packet.recent_experiences || [];
    $('crucible-experiences').innerHTML = experiences.length
      ? experiences.map(item => `<article class="crucible-record" data-eligible="${Boolean(item.eligible_for_crucible)}"><div><span class="pill">${esc(item.arena_id || 'arena')}</span><strong>${esc(item.selected_transition || item.final_outcome || 'experience')}</strong><small>${esc(item.state_before || '—')} → ${esc(item.state_after || '—')}</small></div><div class="crucible-outcome">${outcomeSummary(item.outcome_vector)}</div><small>${item.eligible_for_crucible ? 'eligible for Crucible' : 'legacy/incomplete record'} · ${esc(item.experience_id)}</small></article>`).join('')
      : '<p class="muted">No ArenaExperience records are present in this runtime-local ledger yet.</p>';

    const proposals = packet.recent_proposals || [];
    $('crucible-proposals').innerHTML = proposals.length
      ? proposals.map(item => `<article class="crucible-proposal"><span class="pill">${esc(item.status)}</span><h3>${esc(item.transition_id || item.proposal_id)}</h3><p><code>${esc(item.change_path)}</code>: ${esc(item.current_value)} → ${esc(item.proposed_value)}</p><p>${esc(item.recommendation || 'Awaiting review')}</p><small>${esc(item.required_next_gate)} · ${(item.proposal_digest || '').slice(0, 14)}</small></article>`).join('')
      : '<p class="muted">No crystallization proposal has been produced. This is expected until sufficient verified experience exists.</p>';

    $('crucible-pause').disabled = Boolean(packet.paused);
    $('crucible-resume').disabled = !packet.paused;
    $('crucible-run').disabled = Boolean(packet.paused);
    $('crucible-notice').textContent = packet.paused
      ? `Crucible paused: ${esc(service.pause_reason || 'operator pause')}`
      : `Ledger ${esc(ledger.journal_mode || 'wal')} · terminal output ${esc(packet.terminal_status)} · ${esc(packet.required_next_gate)}`;
  }

  async function refreshCrucible() {
    try {
      $('crucible-state').textContent = 'refreshing';
      const result = await S.api('/api/showcase/learning/status');
      if (!result.ok) throw new Error(result.error || result.reason || 'Learning Arena status unavailable');
      S.crucibleDashboard = result;
      renderCrucible(result);
    } catch (error) {
      $('crucible-state').textContent = 'unavailable';
      $('crucible-notice').textContent = error.message;
    }
  }
  S.refreshCrucible = refreshCrucible;

  async function runCrucible() {
    const button = $('crucible-run');
    button.disabled = true;
    button.textContent = 'Running TRAIN / VALIDATION / SHADOW…';
    try {
      const result = await S.api('/api/showcase/learning/run', {experience_limit: 1000});
      $('crucible-run-output').textContent = JSON.stringify(result.run || result, null, 2);
      if (result.dashboard) renderCrucible(result.dashboard);
      $('crucible-notice').textContent = result.run?.proposal_count
        ? `${result.run.proposal_count} reviewable proposal(s) produced; no grammar was promoted.`
        : 'Proposal cycle completed. No eligible proposal was produced; no grammar was changed.';
    } catch (error) {
      $('crucible-notice').textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = 'Run proposal cycle';
    }
  }

  async function setPaused(paused) {
    const route = paused ? '/api/showcase/learning/pause' : '/api/showcase/learning/resume';
    const result = await S.api(route, paused ? {reason: 'showcase_operator_pause'} : {});
    if (!result.ok) $('crucible-notice').textContent = result.reason || 'Crucible control denied';
    await refreshCrucible();
  }

  function installEvents() {
    $('crucible-refresh')?.addEventListener('click', refreshCrucible);
    $('crucible-run')?.addEventListener('click', runCrucible);
    $('crucible-pause')?.addEventListener('click', () => setPaused(true));
    $('crucible-resume')?.addEventListener('click', () => setPaused(false));

    const humanHero = $('human-view')?.querySelector('.human-hero .hero-actions') || $('human-view')?.querySelector('.human-hero');
    if (humanHero) {
      let button = $('human-open-learning');
      if (!button) {
        button = document.createElement('button');
        button.id = 'human-open-learning';
        button.className = 'secondary';
        button.textContent = 'Open Learning Arena';
        humanHero.appendChild(button);
      }
      button.addEventListener('click', () => S.activateTab('crucible'));
    }
  }

  const originalSetup = S.setupLearningWorkspace;
  S.setupLearningWorkspace = () => {
    originalSetup?.();
    relabelObservatory();
    installObservatoryHandoffs();
  };

  const originalUnlock = S.unlockLearningWorkspace;
  S.unlockLearningWorkspace = trace => {
    originalUnlock?.(trace);
    ['observatory-open-human', 'observatory-open-learning'].forEach(id => {
      const button = $(id);
      if (button) button.disabled = false;
    });
  };

  addStylesheet();
  createCrucibleSurface();
  installNavigation();
  installEvents();
})();
