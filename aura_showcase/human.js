'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;
  const HUMAN_STAGE_COUNT = 7;
  const HUMAN_STAGES = [
    {
      key: 'INTAKE',
      title: 'Choose a bounded entry point',
      note: 'Begin with a presenter-safe task, a Civic issue, or an Observatory handoff. Aura keeps the objective ordinary-language while establishing an explicit boundary.',
    },
    {
      key: 'FRAME',
      title: 'Frame the human objective',
      note: 'Aura records the objective as evidence, clears stale workflow state, and exposes the current six-slot gate without granting an agent authority.',
    },
    {
      key: 'GROUND',
      title: 'Ground exact files, symbols, and tests',
      note: 'The topology inspector localizes exact repository evidence. The bounded 3D view is orientation-only; source spans and hashes remain authoritative.',
    },
    {
      key: 'PLAN',
      title: 'Prepare the Arena capsule and worker handoff',
      note: 'Aura compiles leases, constraints, acceptance criteria, target files, and tests into a bounded capsule before any candidate change is staged.',
    },
    {
      key: 'ACT',
      title: 'Stage a candidate without mutating production',
      note: 'Paste or generate a candidate unified diff. Aura validates the declared boundary and stages it through the Arena bridge; the working source remains unchanged.',
    },
    {
      key: 'PROVE',
      title: 'Run the ephemeral test lab and verifier',
      note: 'Focused tests produce measured evidence inside an ephemeral environment. Verification is independent of the worker that proposed the change.',
    },
    {
      key: 'DECIDE',
      title: 'Check readiness and preserve human authority',
      note: 'Aura explains remaining evidence gaps, records review-only human judgment, and exports a review packet. It does not commit, push, merge, or promote learning.',
    },
  ];
  const HUMAN_STAGE_SECTIONS = [
    ['.spatial-task-panel'],
    ['.human-route-console', '.human-guide-assistant', '.human-grid'],
    ['.topology-card', '.human-route-console'],
    ['.human-grid', '.human-route-console'],
    ['.human-grid', '.evidence-card'],
    ['.human-route-console', '.human-grid', '.evidence-card'],
    ['.human-grid', '.evidence-card', '.human-guide-assistant'],
  ];
  const MANAGED_HUMAN_SELECTORS = [...new Set(HUMAN_STAGE_SECTIONS.flat())];

  S.humanWorkspace = S.humanWorkspace || {
    tourActive: false,
    overviewActive: false,
    stage: 0,
    activeTask: null,
    candidateDiff: '',
    busy: false,
    status: 'Free workspace mode · choose any entry point',
  };

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
    $('human-guide-summary').textContent = guide.summary || 'Import a handoff or frame a bounded task to load the current gate rules.';
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
    if (!S.handoff) {
      $('handoff-summary').textContent = 'No handoff imported.';
      $('handoff-packet').textContent = '{}';
      return;
    }
    const p = S.handoff;
    const title = p.issue?.title || p.title || p.objective || 'Bounded Arena handoff';
    const question = p.issue?.question || p.question || p.objective || '';
    $('handoff-summary').innerHTML = `<strong>${esc(title)}</strong><p>${esc(question)}</p>`;
    $('handoff-packet').textContent = JSON.stringify({
      objective: p.objective,
      grounding: p.grounding,
      six_slot_packet: p.six_slot_packet,
      machine_route: p.machine_route,
      candidate_options: p.candidate_options,
      recommended_option: p.recommended_option,
      test_targets: p.test_targets,
      authority: {
        production_mutation: p.production_mutation,
        automatic_commit: p.automatic_commit,
        automatic_push: p.automatic_push,
        automatic_merge: p.automatic_merge,
      },
    }, null, 2);
  };

  S.renderWorkflow = () => {
    const host = $('workflow-actions');
    if (!S.workflow?.actions) {
      $('workflow-phase').textContent = 'Not started';
      host.innerHTML = '<p class="muted">Open a bounded handoff or use the suggested Human Agent tour to begin.</p>';
      S.renderHumanRoutes();
      S.renderHumanGuide();
      renderHumanTour();
      return;
    }
    $('workflow-phase').textContent = S.workflow.current_phase || 'FRAME';
    host.innerHTML = S.workflow.actions.map((action, index) => `<button class="workflow-action" data-action="${esc(action.action_id)}" data-status="${esc(action.status)}" ${action.status === 'BLOCKED' ? 'disabled' : ''}><span class="workflow-index">${index + 1}</span><span><strong>${esc(action.title)}</strong><small>${esc(action.purpose)}</small>${(action.missing_evidence || []).length ? `<small>Missing: ${esc(action.missing_evidence.join(' · '))}</small>` : ''}</span><span class="gate">${esc(action.status)}</span></button>`).join('');
    host.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => runAction(button.dataset.action)));
    S.renderHumanRoutes();
    S.renderHumanGuide();
    renderHumanTour();
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
    S.humanWorkspace.tourActive = true;
    S.humanWorkspace.stage = inferHumanStage();
    S.activateTab('human');
    renderHumanTour();
  }

  async function runAction(id, payload = {}) {
    const resolvedPayload = id === 'human_review'
      ? {approved: false, reviewer: 'showcase_human', note: 'Reviewed for demonstration only. No merge requested.', ...payload}
      : {...payload};
    setHumanBusy(true, `Running ${id.replaceAll('_', ' ')}…`);
    try {
      const result = await S.api('/api/human-agent/workflow/action', {action_id: id, payload: resolvedPayload});
      await refreshWorkflow();
      const ok = Boolean(result.ok);
      $('workflow-result').innerHTML = `<p><span class="${ok ? 'allowed' : 'denied'}">${ok ? 'ALLOWED' : 'DENIED'}</span> · ${esc(result.action_id || id || '')}</p><p>${esc(result.message || result.error || '')}</p>${(result.missing_evidence || []).length ? `<p><strong>Missing evidence:</strong> ${result.missing_evidence.map(esc).join(' · ')}</p>` : ''}${(result.remediation || []).length ? `<p><strong>Remediation:</strong> ${result.remediation.map(item => esc(item.label || item.action)).join(' → ')}</p>` : ''}<details><summary>Exact guarded result</summary><pre>${esc(JSON.stringify(result, null, 2))}</pre></details>`;
      S.humanWorkspace.status = ok
        ? `${id.replaceAll('_', ' ')} completed through the guarded workflow`
        : `${id.replaceAll('_', ' ')} was denied; the missing evidence is shown below`;
      return result;
    } catch (error) {
      S.humanWorkspace.status = error.message;
      $('workflow-result').innerHTML = `<p class="denied">${esc(error.message)}</p>`;
      return {ok: false, error: error.message};
    } finally {
      setHumanBusy(false);
      renderHumanTour();
    }
  }
  S.runHumanAction = runAction;
  S.refreshHumanWorkflow = refreshWorkflow;

  async function askGuide(question) {
    const text = String(question || $('human-guide-input').value || '').trim();
    if (!text) return;
    $('human-guide-input').value = text;
    const result = await S.api('/api/human-agent/guide/ask', {question: text});
    $('human-guide-answer').innerHTML = result.ok
      ? `<p><strong>${esc(result.kind || 'guidance')}</strong></p><p>${esc(result.answer || '')}</p>${(result.recommended_actions || []).length ? `<p class="muted">Recommended: ${esc(result.recommended_actions.map(item => item.label).join(' · '))}</p>` : ''}`
      : `<p class="denied">${esc(result.error || 'Guidance unavailable')}</p>`;
  }

  function activeSpatialTask() {
    const id = S.spatialTaskId || S.humanWorkspace.activeTask?.task_id;
    return (S.spatialTasks || []).find(task => task.task_id === id) || S.humanWorkspace.activeTask || null;
  }

  function buildTaskObjective(task) {
    if (!task) return String(S.handoff?.objective || S.workflow?.objective || '').trim();
    const criteria = (task.acceptance_criteria || []).join('; ');
    const prohibited = (task.prohibited_actions || []).join(', ');
    return `${task.title}. ${task.summary} Acceptance criteria: ${criteria}. Constraints: preserve exact-source authority; review only; prohibited actions: ${prohibited}.`;
  }

  function hasEvidence(key) {
    const value = S.workflow?.evidence?.[key];
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return Boolean(value.trim());
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === 'object') return Object.keys(value).length > 0;
    return Boolean(value);
  }

  function stageComplete(stage) {
    switch (stage) {
      case 0: return Boolean(activeSpatialTask() || S.handoff || S.workflow?.objective);
      case 1: return Boolean(S.workflow?.objective || hasEvidence('objective'));
      case 2: return hasEvidence('grounding');
      case 3: return hasEvidence('plan_phase_hash') && hasEvidence('act_capsules');
      case 4: return hasEvidence('staged_patch');
      case 5: return hasEvidence('test_evidence') && hasEvidence('verification_packet');
      case 6: return hasEvidence('human_review') || hasEvidence('review_packet');
      default: return false;
    }
  }

  function inferHumanStage() {
    for (let stage = 0; stage < HUMAN_STAGE_COUNT; stage += 1) {
      if (!stageComplete(stage)) return stage;
    }
    return HUMAN_STAGE_COUNT - 1;
  }

  function setHumanBusy(busy, status = '') {
    S.humanWorkspace.busy = Boolean(busy);
    if (status) S.humanWorkspace.status = status;
    const primary = $('human-tour-primary');
    const back = $('human-tour-back');
    const next = $('human-tour-next');
    if (primary) primary.disabled = Boolean(busy);
    if (back) back.disabled = Boolean(busy) || S.humanWorkspace.stage === 0;
    if (next) next.disabled = Boolean(busy) || S.humanWorkspace.stage === HUMAN_STAGE_COUNT - 1;
  }

  function installHumanStyles() {
    if ($('human-tour-styles')) return;
    const style = document.createElement('style');
    style.id = 'human-tour-styles';
    style.textContent = `
      .human-tour-card{margin-bottom:18px}.human-tour-toolbar,.human-tour-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}.human-tour-toolbar{margin:12px 0}.human-tour-status{margin-left:auto}.human-tour-tool{margin-top:14px;padding:14px;border:1px solid rgba(45,212,191,.18);border-radius:14px;background:rgba(5,13,17,.55)}.human-tour-tool textarea{width:100%;min-height:180px;margin-top:10px;font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}.human-tour-proof{display:flex;flex-wrap:wrap;gap:8px}.human-tour-proof span{padding:7px 9px;border-radius:999px;background:rgba(148,163,184,.1);font-size:12px}.human-tour-proof span[data-complete="true"]{background:rgba(45,212,191,.14);color:#7ff4df}.human-tour-selected{display:grid;gap:5px}.human-tour-selected strong{font-size:16px}.human-tour-card .learning-rail button.is-blocked{opacity:.62}.human-tour-card .learning-rail button.is-complete:not(.is-active)::after{content:' ✓';color:#2dd4bf}.human-tour-actions{margin-top:14px}.human-tour-actions .left,.human-tour-actions .right{display:flex;flex-wrap:wrap;gap:10px}.human-tour-card[data-overview="true"] .human-tour-note::before{content:'Overview · ';font-weight:700}.human-tour-note{margin-top:10px;color:#b8cbd2}.human-tour-path{font-size:12px;color:#92aab3}.human-tour-authority{padding:9px 11px;border-left:3px solid #2dd4bf;background:rgba(45,212,191,.07);margin-top:10px}
    `;
    document.head.appendChild(style);
  }

  function installHumanTour() {
    const view = $('human-view');
    const hero = view?.querySelector('.human-hero');
    if (!view || !hero || $('human-tour-card')) return;
    installHumanStyles();
    const card = document.createElement('section');
    card.id = 'human-tour-card';
    card.className = 'learning-rail-card human-tour-card';
    card.innerHTML = `
      <div class="section-head">
        <div><p class="eyebrow">Human Agent Arena · usable workspace with optional demo rails</p><h2 id="human-tour-title">Suggested investigation tour</h2></div>
        <span id="human-tour-phase" class="pill">free workspace</span>
      </div>
      <div class="human-tour-toolbar">
        <div>
          <button id="human-tour-start" type="button" class="primary">Start suggested demo</button>
          <button id="human-tour-exit" type="button" class="secondary" hidden>Exit tour</button>
          <button id="human-tour-overview" type="button" class="secondary">View complete workspace</button>
        </div>
        <span id="human-tour-status" class="pill human-tour-status">Free workspace mode · choose any entry point</span>
      </div>
      <div id="human-tour-rail" class="learning-rail" aria-label="Human Agent Arena guided stages">
        ${HUMAN_STAGES.map((stage, index) => `<button type="button" data-human-tour-stage="${index}">${index + 1}. ${stage.key}</button>`).join('')}
      </div>
      <p id="human-tour-note" class="human-tour-note"></p>
      <div id="human-tour-tool" class="human-tour-tool"></div>
      <div class="human-tour-authority">Agent output remains a proposal. Exact source, verifier evidence, and the human review gate retain authority.</div>
      <div class="human-tour-actions">
        <div class="left"><button id="human-tour-back" type="button" class="secondary">Previous stop</button><button id="human-tour-next" type="button" class="secondary">Next stop</button></div>
        <div class="right"><button id="human-tour-secondary" type="button" class="secondary"></button><button id="human-tour-primary" type="button" class="primary"></button></div>
      </div>`;
    hero.insertAdjacentElement('afterend', card);

    $('human-tour-start').addEventListener('click', () => {
      S.humanWorkspace.tourActive = true;
      S.humanWorkspace.overviewActive = false;
      S.humanWorkspace.stage = inferHumanStage();
      S.humanWorkspace.status = 'Suggested demo active · every action uses the real guarded workflow';
      renderHumanTour(true);
    });
    $('human-tour-exit').addEventListener('click', () => {
      S.humanWorkspace.tourActive = false;
      S.humanWorkspace.overviewActive = false;
      S.humanWorkspace.status = 'Free workspace mode · every Arena surface is visible';
      renderHumanTour();
    });
    $('human-tour-overview').addEventListener('click', () => {
      S.humanWorkspace.overviewActive = !S.humanWorkspace.overviewActive;
      renderHumanTour();
    });
    $('human-tour-back').addEventListener('click', () => showHumanStage(S.humanWorkspace.stage - 1));
    $('human-tour-next').addEventListener('click', () => showHumanStage(S.humanWorkspace.stage + 1));
    $('human-tour-primary').addEventListener('click', runHumanTourPrimary);
    $('human-tour-secondary').addEventListener('click', runHumanTourSecondary);
    $('human-tour-rail').querySelectorAll('[data-human-tour-stage]').forEach(button => button.addEventListener('click', () => {
      if (!S.humanWorkspace.tourActive) S.humanWorkspace.tourActive = true;
      S.humanWorkspace.overviewActive = false;
      showHumanStage(Number(button.dataset.humanTourStage));
    }));
    renderHumanTour();
  }

  function applyHumanFocus() {
    const view = $('human-view');
    const focused = S.humanWorkspace.tourActive && !S.humanWorkspace.overviewActive;
    MANAGED_HUMAN_SELECTORS.forEach(selector => {
      view?.querySelectorAll(`:scope > ${selector}`).forEach(node => { node.hidden = focused; });
    });
    if (focused) {
      (HUMAN_STAGE_SECTIONS[S.humanWorkspace.stage] || []).forEach(selector => {
        view?.querySelectorAll(`:scope > ${selector}`).forEach(node => { node.hidden = false; });
      });
    }
  }

  function showHumanStage(rawStage, scroll = true) {
    S.humanWorkspace.stage = Math.max(0, Math.min(HUMAN_STAGE_COUNT - 1, Number(rawStage) || 0));
    renderHumanTour();
    if (scroll && S.humanWorkspace.tourActive) $('human-tour-card')?.scrollIntoView({behavior: 'smooth', block: 'start'});
  }
  S.showHumanStage = showHumanStage;

  function tourToolHtml(stage) {
    const task = activeSpatialTask();
    const evidence = S.workflow?.evidence || {};
    if (stage === 0) {
      return task
        ? `<div class="human-tour-selected"><span class="pill">selected bounded task</span><strong>${esc(task.title)}</strong><span>${esc(task.summary)}</span><code>${esc(slotText(task.intent_slots))}</code></div>`
        : '<p class="muted">No task selected. Load the recommended Civic-map investigation or choose any task below.</p>';
    }
    if (stage === 1) {
      const objective = S.workflow?.objective || buildTaskObjective(task) || 'No objective framed yet.';
      return `<div class="human-tour-selected"><span class="pill">objective preview</span><strong>${esc(objective)}</strong><span class="human-tour-path">Ordinary intent → explicit objective evidence → six-slot guarded state</span></div>`;
    }
    if (stage === 2) {
      const grounding = evidence.grounding || {};
      const files = grounding.localized_files || [];
      const symbols = grounding.localized_symbols || [];
      const tests = evidence.test_targets || grounding.tests || [];
      return `<div class="human-tour-proof"><span data-complete="${files.length > 0}">files ${files.length}</span><span data-complete="${symbols.length > 0}">symbols ${symbols.length}</span><span data-complete="${tests.length > 0}">tests ${tests.length}</span><span data-complete="${Boolean(grounding.tool_run_id)}">dissolution receipt ${grounding.dissolution_receipt ? 'present' : 'pending'}</span></div>`;
    }
    if (stage === 3) {
      const capsules = evidence.act_capsules || [];
      return `<div class="human-tour-proof"><span data-complete="${Boolean(evidence.plan_phase_hash)}">plan hash ${esc(String(evidence.plan_phase_hash || 'pending').slice(0, 14))}</span><span data-complete="${capsules.length > 0}">capsules ${capsules.length}</span><span data-complete="${hasEvidence('affected_files')}">bounded files ${(evidence.affected_files || []).length}</span><span data-complete="${hasEvidence('test_targets')}">focused tests ${(evidence.test_targets || []).length}</span></div><details><summary>Inspect bounded worker packet</summary><pre>${esc(JSON.stringify(capsules, null, 2))}</pre></details>`;
    }
    if (stage === 4) {
      return `<label for="human-candidate-diff"><strong>Candidate unified diff</strong></label><textarea id="human-candidate-diff" placeholder="Paste a worker-generated unified diff here. It will be staged through the Arena boundary; production will not be mutated.">${esc(S.humanWorkspace.candidateDiff)}</textarea><p class="muted">Required before ACT: candidate diff + exact affected files + prepared plan hash.</p>`;
    }
    if (stage === 5) {
      return `<div class="human-tour-proof"><span data-complete="${hasEvidence('staged_patch')}">staged patch</span><span data-complete="${hasEvidence('test_evidence')}">measured tests</span><span data-complete="${hasEvidence('verification_packet')}">verification packet</span><span data-complete="${Boolean(evidence.test_evidence?.dissolution_receipt)}">sandbox dissolution</span></div>`;
    }
    return `<div class="human-tour-proof"><span data-complete="${hasEvidence('hotswap_status')}">readiness checked</span><span data-complete="${hasEvidence('human_review')}">human review recorded</span><span data-complete="${hasEvidence('review_packet')}">review packet exported</span><span data-complete="false">automatic merge blocked</span></div>`;
  }

  function primaryActionState(stage) {
    const task = activeSpatialTask();
    if (stage === 0) return {label: task ? 'Continue with selected task' : 'Load recommended demo task', disabled: false};
    if (stage === 1) return {label: stageComplete(1) ? 'Objective framed' : 'Frame selected objective', disabled: stageComplete(1) || (!task && !S.handoff?.objective)};
    if (stage === 2) return {label: stageComplete(2) ? 'Exact context grounded' : 'Ground exact context', disabled: stageComplete(2) || !stageComplete(1)};
    if (stage === 3) return {label: stageComplete(3) ? 'Arena capsule prepared' : 'Prepare bounded capsule', disabled: stageComplete(3) || !stageComplete(2)};
    if (stage === 4) return {label: stageComplete(4) ? 'Candidate staged' : 'Stage candidate patch', disabled: stageComplete(4) || !stageComplete(3) || !S.humanWorkspace.candidateDiff.trim()};
    if (stage === 5) {
      if (!hasEvidence('test_evidence')) return {label: 'Run focused tests', disabled: !stageComplete(4)};
      if (!hasEvidence('verification_packet')) return {label: 'Verify measured evidence', disabled: false};
      return {label: 'Proof gates complete', disabled: true};
    }
    if (!hasEvidence('hotswap_status')) return {label: 'Check review readiness', disabled: !hasEvidence('verification_packet')};
    if (!hasEvidence('human_review')) return {label: 'Record review-only decision', disabled: false};
    if (!hasEvidence('review_packet')) return {label: 'Export review packet', disabled: false};
    return {label: 'Review packet ready', disabled: true};
  }

  function secondaryActionState(stage) {
    if (stage === 0) return {label: 'Open Aura Observatory', hidden: false};
    if (stage === 1) return {label: 'Ask Aura what comes next', hidden: false};
    if (stage === 2) return {label: 'Fit topology', hidden: false};
    if (stage === 3) return {label: 'Copy worker packet', hidden: false};
    if (stage === 4) return {label: 'Clear candidate', hidden: false};
    if (stage === 5) return {label: 'Inspect exact evidence', hidden: false};
    return {label: 'Open Learning Arena', hidden: false};
  }

  function renderHumanTour(scroll = false) {
    if (!$('human-tour-card')) return;
    const stage = S.humanWorkspace.stage;
    const definition = HUMAN_STAGES[stage];
    const phase = S.workflow?.current_phase || definition.key;
    $('human-tour-card').dataset.overview = String(S.humanWorkspace.overviewActive);
    $('human-tour-title').textContent = S.humanWorkspace.tourActive
      ? `${stage + 1}. ${definition.title}`
      : 'Suggested investigation tour';
    $('human-tour-phase').textContent = S.humanWorkspace.tourActive ? `workflow ${phase}` : 'free workspace';
    $('human-tour-status').textContent = S.humanWorkspace.status;
    $('human-tour-note').textContent = S.humanWorkspace.overviewActive
      ? 'Every Human Agent surface is visible. Return to the focused tour to follow the governed path one gate at a time.'
      : definition.note;
    $('human-tour-tool').innerHTML = tourToolHtml(stage);
    const diffInput = $('human-candidate-diff');
    if (diffInput) diffInput.addEventListener('input', event => {
      S.humanWorkspace.candidateDiff = event.target.value;
      const state = primaryActionState(stage);
      $('human-tour-primary').disabled = S.humanWorkspace.busy || state.disabled;
    });

    $('human-tour-rail').querySelectorAll('[data-human-tour-stage]').forEach(button => {
      const index = Number(button.dataset.humanTourStage);
      button.classList.toggle('is-active', S.humanWorkspace.tourActive && index === stage && !S.humanWorkspace.overviewActive);
      button.classList.toggle('is-complete', stageComplete(index));
      button.classList.toggle('is-blocked', index > 0 && !stageComplete(index - 1));
    });
    $('human-tour-start').hidden = S.humanWorkspace.tourActive;
    $('human-tour-exit').hidden = !S.humanWorkspace.tourActive;
    $('human-tour-overview').textContent = S.humanWorkspace.overviewActive ? 'Return to focused tour' : 'View complete workspace';
    $('human-tour-back').disabled = S.humanWorkspace.busy || stage === 0;
    $('human-tour-next').disabled = S.humanWorkspace.busy || stage === HUMAN_STAGE_COUNT - 1;

    const primary = primaryActionState(stage);
    $('human-tour-primary').textContent = primary.label;
    $('human-tour-primary').disabled = S.humanWorkspace.busy || primary.disabled;
    const secondary = secondaryActionState(stage);
    $('human-tour-secondary').textContent = secondary.label;
    $('human-tour-secondary').hidden = secondary.hidden;
    $('human-tour-secondary').disabled = S.humanWorkspace.busy;
    applyHumanFocus();
    if (scroll) $('human-tour-card')?.scrollIntoView({behavior: 'smooth', block: 'start'});
  }
  S.renderHumanTour = renderHumanTour;

  async function runHumanTourPrimary() {
    const stage = S.humanWorkspace.stage;
    const task = activeSpatialTask();
    if (stage === 0) {
      if (!task) {
        setHumanBusy(true, 'Loading the bounded Civic-map investigation…');
        try {
          await S.loadTopologyTask?.('civic_map_overlay', 1);
          S.humanWorkspace.activeTask = activeSpatialTask() || (S.spatialTasks || []).find(item => item.task_id === 'civic_map_overlay') || null;
          S.humanWorkspace.status = 'Bounded task loaded · no workflow authority granted yet';
        } finally {
          setHumanBusy(false);
        }
      }
      showHumanStage(1);
      return;
    }
    if (stage === 1) {
      const objective = buildTaskObjective(task);
      const result = await runAction('set_objective', {objective});
      if (result.ok) showHumanStage(2);
      return;
    }
    if (stage === 2) {
      const result = await runAction('ground_context');
      if (result.ok) showHumanStage(3);
      return;
    }
    if (stage === 3) {
      const result = await runAction('prepare_capsule', {acceptance_criteria: task?.acceptance_criteria || []});
      if (result.ok) showHumanStage(4);
      return;
    }
    if (stage === 4) {
      const evidence = S.workflow?.evidence || {};
      const result = await runAction('stage_patch', {
        candidate_diff: S.humanWorkspace.candidateDiff,
        affected_files: evidence.affected_files || evidence.grounding?.localized_files || [],
        affected_symbols: evidence.grounding?.localized_symbols || [],
      });
      if (result.ok) showHumanStage(5);
      return;
    }
    if (stage === 5) {
      if (!hasEvidence('test_evidence')) {
        await runAction('run_tests', {test_targets: S.workflow?.evidence?.test_targets || []});
      } else if (!hasEvidence('verification_packet')) {
        const result = await runAction('verify_patch');
        if (result.ok) showHumanStage(6);
      }
      return;
    }
    if (!hasEvidence('hotswap_status')) await runAction('check_hotswap');
    else if (!hasEvidence('human_review')) await runAction('human_review');
    else if (!hasEvidence('review_packet')) await runAction('export_handoff');
  }

  async function runHumanTourSecondary() {
    const stage = S.humanWorkspace.stage;
    if (stage === 0) {
      S.activateTab('learning');
      return;
    }
    if (stage === 1) {
      await askGuide('What should I do next?');
      $('human-guide-assistant')?.scrollIntoView({behavior: 'smooth', block: 'start'});
      return;
    }
    if (stage === 2) {
      $('topology-fit')?.click();
      return;
    }
    if (stage === 3) {
      await S.copyText?.(JSON.stringify(S.workflow?.evidence?.act_capsules || [], null, 2), 'Bounded worker packet copied');
      S.humanWorkspace.status = 'Bounded worker packet copied';
      renderHumanTour();
      return;
    }
    if (stage === 4) {
      S.humanWorkspace.candidateDiff = '';
      renderHumanTour();
      return;
    }
    if (stage === 5) {
      $('workflow-result')?.scrollIntoView({behavior: 'smooth', block: 'start'});
      return;
    }
    S.activateTab('crucible');
  }

  function installObservatoryNavigationRepair() {
    const originalShow = S.showLearningStage;
    if (!originalShow || S.observatoryNavigationRepaired) return;
    S.observatoryNavigationRepaired = true;

    function syncNextButton() {
      const next = $('learning-next');
      const back = $('learning-back');
      if (!next || !back) return;
      const stage = Math.max(0, Math.min(5, Number(S.intentStage) || 0));
      const hasInput = Boolean(String($('bulk-intent-input')?.value || '').trim());
      const labels = [
        S.intentTrace ? 'Show lexical addresses' : 'Compile and show lexical addresses',
        'Show routing tags',
        'Show six-slot packet',
        'Show FST hard gate',
        'Show bounded handoff',
        'Bounded handoff ready',
      ];
      next.textContent = labels[stage];
      next.disabled = stage === 5 || (!S.intentTrace && (stage > 0 || !hasInput));
      back.disabled = stage === 0;
    }

    S.showLearningStage = rawStage => {
      originalShow(rawStage);
      syncNextButton();
    };

    document.addEventListener('click', async event => {
      const target = event.target instanceof Element ? event.target : null;
      const next = target?.closest('#learning-next');
      const back = target?.closest('#learning-back');
      if (!next && !back) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      if (back) {
        S.showLearningStage(Math.max(0, (Number(S.intentStage) || 0) - 1));
        return;
      }
      if (!S.intentTrace) {
        if (!String($('bulk-intent-input')?.value || '').trim()) return;
        S.learningWorkspace.tourActive = true;
        await S.compileIntent?.();
        if (S.intentTrace) S.showLearningStage(1);
        return;
      }
      S.showLearningStage(Math.min(5, (Number(S.intentStage) || 0) + 1));
    }, true);

    $('bulk-intent-input')?.addEventListener('input', syncNextButton);
    window.setTimeout(syncNextButton, 0);
  }

  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target.closest('[data-spatial-task]') : null;
    if (!target) return;
    const task = (S.spatialTasks || []).find(item => item.task_id === target.dataset.spatialTask);
    if (task) {
      S.humanWorkspace.activeTask = task;
      S.spatialTaskId = task.task_id;
      S.humanWorkspace.status = `${task.title} selected · topology projection has no patch authority`;
      renderHumanTour();
    }
  });

  $('investigate-issue')?.addEventListener('click', investigate);
  $('human-guide-ask')?.addEventListener('click', () => askGuide());
  $('human-guide-input')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); askGuide(); }
  });
  document.querySelectorAll('[data-guide-question]').forEach(button => button.addEventListener('click', () => askGuide(button.dataset.guideQuestion)));

  installHumanTour();
  installObservatoryNavigationRepair();
  S.renderHumanRoutes();
  S.renderHumanGuide();
  renderHumanTour();
})();
