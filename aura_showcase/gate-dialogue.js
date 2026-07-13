'use strict';

(() => {
  const S = window.Showcase;
  if (!S || !S.$ || S.gateDialogueInstalled) return;
  S.gateDialogueInstalled = true;
  const $ = S.$, esc = S.esc;

  const STAGES = ['INTAKE', 'FRAME', 'GROUND', 'PLAN', 'ACT', 'PROVE', 'DECIDE'];
  const DEFAULT_INTENTS = [
    'Use this selected topology evidence and explain the safest bounded entry point for the investigation.',
    'Frame the objective around this selected file or symbol while preserving exact-source and human-review authority.',
    'Ground my intent in this node, its dependencies, callers, connected tests, and any visible evidence gaps.',
    'Prepare the smallest Arena capsule that addresses this selected topology evidence and preserves rollback boundaries.',
    'Address how the candidate change should interact with this node and its dependencies without expanding the declared scope.',
    'Explain what tests and independent verifier evidence are required for this selected topology evidence before we proceed.',
    'Summarize the evidence, unresolved risk, and review-only next step for this selected node. Do not commit, push, or merge.',
  ];

  const dialogue = S.humanGateDialogue = S.humanGateDialogue || {
    nodeContext: {},
    topologyPacket: null,
    byStage: {},
    busy: false,
    notice: 'Select a topology node or use the current gate, then tell Aura what you want addressed.',
  };

  function stageIndex() {
    return Math.max(0, Math.min(STAGES.length - 1, Number(S.humanWorkspace?.stage) || 0));
  }

  function stageKey(index = stageIndex()) {
    return STAGES[index] || 'FRAME';
  }

  function stageState(index = stageIndex()) {
    if (!dialogue.byStage[index]) {
      dialogue.byStage[index] = {
        draft: DEFAULT_INTENTS[index],
        pending: null,
        decision: null,
        execution: null,
        notice: '',
      };
    }
    return dialogue.byStage[index];
  }

  function activeTask() {
    const id = S.spatialTaskId || S.humanWorkspace?.activeTask?.task_id;
    return (S.spatialTasks || []).find(task => task.task_id === id) || S.humanWorkspace?.activeTask || null;
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

  function nodeList(values) {
    return (values || []).slice(0, 12).map(item => {
      if (typeof item === 'string') return item;
      return item?.label || item?.id || item?.file_path || item?.symbol || '';
    }).filter(Boolean);
  }

  function topologyContext(packet) {
    const workspace = packet?.workspace || {};
    const nodes = workspace.nodes || [];
    const selectedId = workspace.selected_node_ids?.[0] || nodes[0]?.id || '';
    const selected = nodes.find(node => node.id === selectedId) || null;
    if (!selected) return {};
    const byId = new Map(nodes.map(node => [node.id, node]));
    const relations = (workspace.links || []).filter(link => link.source === selectedId || link.target === selectedId).slice(0, 20).map(link => {
      const otherId = link.source === selectedId ? link.target : link.source;
      const other = byId.get(otherId) || {};
      return {
        relation: link.kind || link.relation || link.type || 'connected_to',
        source: link.source,
        target: link.target,
        label: other.label || other.symbol || other.file_path || otherId,
        status: link.status || '',
      };
    });
    const dependencies = nodeList(workspace.dependencies).length
      ? nodeList(workspace.dependencies)
      : relations.filter(item => item.source === selectedId).map(item => item.label);
    const callers = nodeList(workspace.callers).length
      ? nodeList(workspace.callers)
      : relations.filter(item => item.target === selectedId).map(item => item.label);
    return {
      task_id: S.spatialTaskId || packet?.task?.task_id || '',
      selected_node: {
        id: selected.id || '',
        label: selected.label || selected.id || '',
        file_path: selected.file_path || '',
        symbol: selected.symbol || '',
        node_type: selected.node_type || '',
        line_range: selected.line_range || [],
        projection_truth: selected.projection_truth || 'EXACT_TOPOLOGY',
      },
      dependencies,
      callers,
      tests: nodeList(workspace.tests),
      relations,
      candidate_faults: (workspace.candidate_faults || []).filter(item => item.node_id === selectedId).slice(0, 8),
      full_topology_transferred: false,
      visual_topology_patch_authority: false,
    };
  }

  function captureTopology(packet) {
    if (!packet?.ok || !packet.workspace) return;
    const previous = JSON.stringify(dialogue.nodeContext || {});
    dialogue.topologyPacket = packet;
    dialogue.nodeContext = topologyContext(packet);
    const current = JSON.stringify(dialogue.nodeContext || {});
    if (previous && previous !== '{}' && previous !== current) {
      const state = stageState();
      if (state.pending) {
        state.pending = null;
        state.decision = null;
        state.notice = 'Topology selection changed. Ask Aura again so the response is anchored to the newly selected evidence.';
      }
    }
    renderGateDialogue();
  }

  const originalApi = S.api.bind(S);
  S.api = async (path, body) => {
    const result = await originalApi(path, body);
    if ((String(path).startsWith('/api/showcase/topology/tasks/') || path === '/api/showcase/topology/select') && result?.ok) {
      captureTopology(result);
    }
    return result;
  };

  function installStyles() {
    if ($('gate-dialogue-styles')) return;
    const style = document.createElement('style');
    style.id = 'gate-dialogue-styles';
    style.textContent = `
      .gate-dialogue-card{margin-top:14px;padding:16px;border:1px solid rgba(45,212,191,.24);border-radius:16px;background:linear-gradient(145deg,rgba(8,22,28,.96),rgba(5,13,17,.9));display:grid;gap:13px}
      .gate-dialogue-head,.gate-dialogue-actions,.gate-dialogue-approval{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}
      .gate-dialogue-anchor{display:grid;gap:5px;padding:11px 12px;border-radius:12px;background:rgba(45,212,191,.07);border-left:3px solid #2dd4bf}
      .gate-dialogue-anchor code{white-space:normal;overflow-wrap:anywhere}.gate-dialogue-neighbours{display:flex;gap:7px;flex-wrap:wrap}.gate-dialogue-neighbours span{font-size:11px;padding:5px 8px;border-radius:999px;background:rgba(148,163,184,.11)}
      .gate-dialogue-card textarea{width:100%;min-height:105px;resize:vertical}.gate-dialogue-response{padding:14px;border-radius:13px;background:rgba(3,10,14,.8);border:1px solid rgba(148,163,184,.16);display:grid;gap:9px}.gate-dialogue-response[data-status="PENDING_HUMAN_APPROVAL"]{border-color:rgba(250,204,21,.38)}.gate-dialogue-response[data-status^="APPROVED"]{border-color:rgba(45,212,191,.45)}
      .gate-dialogue-provenance{font-size:11px;color:#92aab3}.gate-dialogue-notice{font-size:12px;color:#b8cbd2}.gate-dialogue-warning{color:#facc15}.gate-dialogue-denied{color:#fb7185}.gate-dialogue-card button[hidden]{display:none}
    `;
    document.head.appendChild(style);
  }

  function installPanel() {
    const tool = $('human-tour-tool');
    if (!tool || $('human-gate-dialogue')) return false;
    installStyles();
    const panel = document.createElement('section');
    panel.id = 'human-gate-dialogue';
    panel.className = 'gate-dialogue-card';
    tool.insertAdjacentElement('afterend', panel);
    panel.addEventListener('input', event => {
      if (event.target?.id === 'human-gate-comment') {
        stageState().draft = event.target.value;
        syncButtons();
      }
    });
    panel.addEventListener('click', event => {
      const button = event.target instanceof Element ? event.target.closest('button') : null;
      if (!button) return;
      if (button.id === 'human-gate-address') addressIntent();
      if (button.id === 'human-gate-approve') approveIntent(true);
      if (button.id === 'human-gate-reject') approveIntent(false);
      if (button.id === 'human-gate-clear') {
        const state = stageState();
        state.draft = '';
        state.pending = null;
        state.decision = null;
        state.notice = 'Draft cleared. No workflow action was executed.';
        renderGateDialogue();
      }
    });
    return true;
  }

  function anchorHtml() {
    const context = dialogue.nodeContext || {};
    const node = context.selected_node || {};
    if (!node.id) {
      const task = activeTask();
      return `<div class="gate-dialogue-anchor"><span class="pill">current gate</span><strong>${esc(task?.title || S.workflow?.current_phase || stageKey())}</strong><small>No topology node is selected. Aura will address the comment from the current guarded gate and task boundary.</small></div>`;
    }
    const neighbourChips = [
      ...(context.dependencies || []).slice(0, 4).map(value => `dependency · ${value}`),
      ...(context.callers || []).slice(0, 3).map(value => `caller · ${value}`),
      ...(context.tests || []).slice(0, 3).map(value => `test · ${value}`),
    ];
    return `<div class="gate-dialogue-anchor"><span class="pill">selected topology evidence</span><strong>${esc(node.label || node.id)}</strong><code>${esc(node.file_path || '—')} · ${esc(node.symbol || 'global scope')} · lines ${esc((node.line_range || []).join('–') || '—')}</code><small>${esc(node.projection_truth || 'EXACT_TOPOLOGY')} · visual selection has no patch authority</small><div class="gate-dialogue-neighbours">${neighbourChips.map(item => `<span>${esc(item)}</span>`).join('') || '<span>no bounded neighbours returned</span>'}</div></div>`;
  }

  function responseHtml(state) {
    const packet = state.pending;
    const decision = state.decision;
    if (!packet && !decision) return '<p class="muted">Aura has not addressed a gate-specific intent yet.</p>';
    if (packet) {
      const provenance = packet.response_provenance || {};
      const next = packet.recommended_action || {};
      return `<div class="gate-dialogue-response" data-status="${esc(packet.status)}"><span class="pill">${esc(packet.status)}</span><p>${esc(packet.aura_response || '')}</p>${next.action_id ? `<p><strong>Authoritative guarded next action:</strong> ${esc(next.label || next.action_id)} · ${esc(next.description || '')}</p>` : '<p class="gate-dialogue-warning">No work transition is currently admitted; approval cannot bypass the missing evidence.</p>'}<small class="gate-dialogue-provenance">${provenance.model_used ? `external voice: ${esc(provenance.provider)} · ${esc(provenance.model)}` : `deterministic local response · ${esc(provenance.fallback_reason || 'no external model required')}`} · route authority remains deterministic</small></div>`;
    }
    return `<div class="gate-dialogue-response" data-status="${esc(decision.status || '')}"><span class="pill">${esc(decision.status || '')}</span><p>${decision.approved ? 'Your approval was recorded for this exact gate and topology selection. The guarded workflow then attempted the next stage.' : 'You rejected the proposal. No workflow action was executed.'}</p></div>`;
  }

  function renderGateDialogue() {
    if (!installPanel()) return;
    const index = stageIndex();
    const state = stageState(index);
    const phase = S.workflow?.current_phase || stageKey(index);
    const panel = $('human-gate-dialogue');
    panel.innerHTML = `
      <div class="gate-dialogue-head"><div><p class="eyebrow">Gate dialogue · topology-anchored human intent</p><h3>Tell Aura what to address before ${esc(stageKey(index))} advances</h3></div><span class="pill">workflow ${esc(phase)}</span></div>
      ${anchorHtml()}
      <label for="human-gate-comment"><strong>Your intent, concern, correction, or question</strong></label>
      <textarea id="human-gate-comment" maxlength="6000" placeholder="Tell Aura what you want addressed about this gate or selected topology node…">${esc(state.draft)}</textarea>
      <div class="gate-dialogue-actions"><span class="gate-dialogue-notice">Aura may explain, reframe, identify evidence, or propose the safest admitted action. It may not advance without your approval.</span><div><button id="human-gate-clear" type="button" class="secondary">Clear</button> <button id="human-gate-address" type="button" class="primary">Ask Aura to address this</button></div></div>
      ${responseHtml(state)}
      <div class="gate-dialogue-approval"><span class="gate-dialogue-notice ${state.notice?.includes('denied') ? 'gate-dialogue-denied' : ''}">${esc(state.notice || dialogue.notice)}</span><div><button id="human-gate-reject" type="button" class="secondary" ${state.pending ? '' : 'hidden'}>Reject and revise</button> <button id="human-gate-approve" type="button" class="primary" ${state.pending ? '' : 'hidden'}>Approve response and continue</button></div></div>`;
    syncButtons();
  }

  function syncButtons() {
    const state = stageState();
    const ask = $('human-gate-address');
    const approve = $('human-gate-approve');
    const reject = $('human-gate-reject');
    if (ask) ask.disabled = dialogue.busy || !String(state.draft || '').trim();
    if (approve) approve.disabled = dialogue.busy || !state.pending;
    if (reject) reject.disabled = dialogue.busy || !state.pending;
    const next = $('human-tour-next');
    if (next && S.humanWorkspace?.tourActive) {
      next.disabled = dialogue.busy || stageIndex() === STAGES.length - 1 || !state.decision?.approved;
      next.title = state.decision?.approved ? 'Inspect the next approved gate' : 'Address and approve the current gate before advancing';
    }
  }

  function setBusy(value, notice = '') {
    dialogue.busy = Boolean(value);
    if (notice) stageState().notice = notice;
    renderGateDialogue();
  }

  async function addressIntent() {
    const index = stageIndex();
    const state = stageState(index);
    const comment = String(state.draft || '').trim();
    if (!comment) return;
    setBusy(true, 'Aura is parsing the new intent and grounding its response in this gate and topology selection…');
    try {
      const result = await S.api('/api/showcase/human/gate/address', {
        comment,
        stage_hint: stageKey(index),
        node_context: dialogue.nodeContext || {},
        prefer_model: true,
      });
      if (!result.ok) throw new Error(result.reason || result.error || 'Gate dialogue was denied');
      state.pending = result;
      state.decision = null;
      state.execution = null;
      state.notice = 'Aura has addressed this exact gate and selection. Review the response before approving continuation.';
    } catch (error) {
      state.pending = null;
      state.notice = `Gate dialogue denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function approveIntent(approved) {
    const index = stageIndex();
    const state = stageState(index);
    if (!state.pending) return;
    setBusy(true, approved ? 'Recording your approval against the exact gate and selected node…' : 'Recording rejection…');
    try {
      const result = await S.api('/api/showcase/human/gate/approve', {
        proposal_id: state.pending.proposal_id,
        approved: Boolean(approved),
        stage_hint: stageKey(index),
        current_node_context: dialogue.nodeContext || {},
        reviewer: 'showcase_human',
        note: approved ? 'Approved to attempt the next existing guarded workflow gate only.' : 'Rejected for revision.',
      });
      if (!result.ok) throw new Error(result.reason || result.error || 'Gate approval was denied');
      state.decision = result.decision;
      state.pending = null;
      state.notice = result.note || '';
      if (approved) {
        S.workflow = result.workflow || S.workflow;
        await executeApprovedStage(index, state);
      }
    } catch (error) {
      state.notice = `Approval denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function action(actionId, payload = {}) {
    const result = await S.runHumanAction?.(actionId, payload);
    return result || {ok: false, error: 'guarded_workflow_unavailable'};
  }

  async function executeApprovedStage(index, state) {
    const task = activeTask();
    let result = {ok: true};
    if (index === 0) {
      if (!task) await S.loadTopologyTask?.('civic_map_overlay', 1);
    } else if (index === 1) {
      if (!hasEvidence('objective')) result = await action('set_objective', {objective: buildTaskObjective(activeTask())});
    } else if (index === 2) {
      if (!hasEvidence('grounding')) result = await action('ground_context');
    } else if (index === 3) {
      if (!hasEvidence('plan_phase_hash')) result = await action('prepare_capsule', {acceptance_criteria: (activeTask()?.acceptance_criteria || [])});
    } else if (index === 4) {
      const diff = String(S.humanWorkspace?.candidateDiff || $('human-candidate-diff')?.value || '').trim();
      if (!diff) {
        state.notice = 'Approval was recorded, but ACT remains at this gate until a candidate unified diff is provided.';
        return;
      }
      const evidence = S.workflow?.evidence || {};
      if (!hasEvidence('staged_patch')) result = await action('stage_patch', {
        candidate_diff: diff,
        affected_files: evidence.affected_files || evidence.grounding?.localized_files || [],
        affected_symbols: evidence.grounding?.localized_symbols || [],
      });
    } else if (index === 5) {
      if (!hasEvidence('test_evidence')) result = await action('run_tests', {test_targets: S.workflow?.evidence?.test_targets || []});
      if (result.ok && !hasEvidence('verification_packet')) result = await action('verify_patch');
    } else if (index === 6) {
      if (!hasEvidence('hotswap_status')) result = await action('check_hotswap');
      if (result.ok && !hasEvidence('human_review')) result = await action('human_review', {
        approved: false,
        reviewer: 'showcase_human',
        note: 'Gate dialogue approved continuation to a review packet only. No production approval or merge was granted.',
      });
      if (result.ok && !hasEvidence('review_packet')) result = await action('export_handoff');
    }
    state.execution = result;
    if (!result.ok) {
      state.notice = `Your gate approval was recorded, but the guarded action was denied: ${result.message || result.error || 'missing evidence'}`;
      return;
    }
    state.notice = index === STAGES.length - 1
      ? 'Review packet prepared. No commit, push, merge, deployment, or grammar promotion occurred.'
      : 'The approved guarded action completed. Moving to the next gate.';
    if (index < STAGES.length - 1) S.showHumanStage?.(index + 1);
  }

  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    if (target.closest('#human-tour-next') && S.humanWorkspace?.tourActive) {
      const state = stageState();
      if (!state.decision?.approved) {
        event.preventDefault();
        event.stopImmediatePropagation();
        state.notice = 'Address this gate and approve Aura’s response before moving forward.';
        renderGateDialogue();
        return;
      }
    }
    if (target.closest('[data-human-tour-stage], [data-spatial-task], #human-tour-back, #human-tour-start, #human-tour-exit, #human-tour-overview')) {
      window.setTimeout(renderGateDialogue, 0);
    }
  }, true);

  const originalRender = S.renderHumanTour;
  S.renderHumanTour = (...args) => {
    const result = originalRender?.(...args);
    window.setTimeout(renderGateDialogue, 0);
    return result;
  };

  window.addEventListener('aura:topology-selection', event => captureTopology(event.detail || {}));
  window.setTimeout(renderGateDialogue, 0);
})();
