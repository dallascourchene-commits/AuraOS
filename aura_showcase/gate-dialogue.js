'use strict';

(() => {
  const S = window.Showcase;
  if (!S || !S.$ || S.gateDialogueInstalled) return;
  S.gateDialogueInstalled = true;
  const $ = S.$, esc = S.esc;

  const STAGES = ['INTAKE', 'FRAME', 'GROUND', 'PLAN', 'ACT', 'PROVE', 'DECIDE'];
  const BILATERAL_MARKER = '[AURA_BILATERAL_REFINE]';
  const DEFAULT_INTENTS = [
    'Use this selected topology evidence and explain the safest bounded entry point. Do not expand beyond the selected task or grant execution authority.',
    'Frame the objective around this selected file or symbol. Do not alter exact-source or human-review authority.',
    'Ground my intent in this node, its dependencies, callers, tests, and evidence gaps. Do not invent missing source facts.',
    'Prepare the smallest Arena capsule for this evidence. Do not expand the declared files, symbols, tools, or effects.',
    'Address how the candidate should interact with this node. Do not mutate production or bypass the isolated worktree.',
    'Explain the required tests and independent verifier evidence. Do not treat model confidence as proof.',
    'Summarize evidence, unresolved risk, and the review-only next step. Do not commit, push, merge, deploy, or promote learning.',
  ];

  const dialogue = S.humanGateDialogue = S.humanGateDialogue || {
    nodeContext: {},
    topologyPacket: null,
    byStage: {},
    busy: false,
    notice: 'Select topology evidence, state both desired and prohibited behavior, then confirm Aura’s teach-back.',
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
        clarification: '',
        pending: null,
        decision: null,
        compilation: null,
        execution: null,
        gateCompleted: false,
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
    const relations = (workspace.links || [])
      .filter(link => link.source === selectedId || link.target === selectedId)
      .slice(0, 20)
      .map(link => {
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

  function invalidate(message) {
    const state = stageState();
    state.pending = null;
    state.decision = null;
    state.compilation = null;
    state.execution = null;
    state.gateCompleted = false;
    state.clarification = '';
    state.notice = message;
  }

  function captureTopology(packet) {
    if (!packet?.ok || !packet.workspace) return;
    const previous = JSON.stringify(dialogue.nodeContext || {});
    dialogue.topologyPacket = packet;
    dialogue.nodeContext = topologyContext(packet);
    const current = JSON.stringify(dialogue.nodeContext || {});
    if (previous && previous !== '{}' && previous !== current) {
      invalidate('Topology selection changed. The prior interpretation and confirmation are stale; ask Aura again.');
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
      .gate-dialogue-anchor,.bilateral-panel{display:grid;gap:7px;padding:11px 12px;border-radius:12px;background:rgba(45,212,191,.07);border-left:3px solid #2dd4bf}
      .gate-dialogue-anchor code{white-space:normal;overflow-wrap:anywhere}.gate-dialogue-neighbours,.guardrail-tags{display:flex;gap:7px;flex-wrap:wrap}.gate-dialogue-neighbours span,.guardrail-tags span{font-size:11px;padding:5px 8px;border-radius:999px;background:rgba(148,163,184,.11)}
      .bilateral-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:10px}.bilateral-panel.negative{border-left-color:#fb7185}.bilateral-panel.hard{border-left-color:#facc15}.bilateral-panel.editable{border-left-color:#60a5fa}
      .bilateral-panel h4{margin:0}.bilateral-panel ul{margin:0;padding-left:19px}.bilateral-panel li{margin:4px 0}.bilateral-empty{font-size:12px;color:#92aab3}
      .gate-dialogue-card textarea,.gate-dialogue-card input{width:100%;box-sizing:border-box}.gate-dialogue-card textarea{min-height:105px;resize:vertical}.clarification-box{display:grid;gap:8px;padding:12px;border-radius:12px;border:1px solid rgba(250,204,21,.35);background:rgba(250,204,21,.06)}
      .gate-dialogue-response{padding:14px;border-radius:13px;background:rgba(3,10,14,.8);border:1px solid rgba(148,163,184,.16);display:grid;gap:9px}.gate-dialogue-response[data-status="CLARIFICATION_REQUIRED"]{border-color:rgba(250,204,21,.48)}.gate-dialogue-response[data-status="PENDING_HUMAN_APPROVAL"]{border-color:rgba(96,165,250,.45)}.gate-dialogue-response[data-status^="APPROVED"]{border-color:rgba(45,212,191,.45)}
      .gate-dialogue-provenance{font-size:11px;color:#92aab3}.gate-dialogue-notice{font-size:12px;color:#b8cbd2}.gate-dialogue-warning{color:#facc15}.gate-dialogue-denied{color:#fb7185}.gate-dialogue-success{color:#7ff4df}.gate-dialogue-card button[hidden]{display:none}
    `;
    document.head.appendChild(style);
  }

  function installPanel() {
    const tool = $('human-tour-tool');
    if (!tool) return false;
    if ($('human-gate-dialogue')) return true;
    installStyles();
    const panel = document.createElement('section');
    panel.id = 'human-gate-dialogue';
    panel.className = 'gate-dialogue-card';
    tool.insertAdjacentElement('afterend', panel);
    panel.addEventListener('input', event => {
      const state = stageState();
      if (event.target?.id === 'human-gate-comment') {
        state.draft = event.target.value;
        if (state.pending || state.decision) invalidate('The request changed. Ask Aura again before confirming.');
      }
      if (event.target?.id === 'human-gate-clarification') state.clarification = event.target.value;
      syncButtons();
    });
    panel.addEventListener('click', event => {
      const button = event.target instanceof Element ? event.target.closest('button') : null;
      if (!button) return;
      if (button.id === 'human-gate-address') addressIntent();
      if (button.id === 'human-gate-clarify') submitClarification();
      if (button.id === 'human-gate-approve') approveIntent(true);
      if (button.id === 'human-gate-reject') approveIntent(false);
      if (button.id === 'human-gate-add-guardrail') addGuardrail();
      if (button.id === 'human-gate-clear') {
        const state = stageState();
        state.draft = '';
        invalidate('Draft cleared. No workflow action was executed.');
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
      return `<div class="gate-dialogue-anchor"><span class="pill">current gate</span><strong>${esc(task?.title || S.workflow?.current_phase || stageKey())}</strong><small>Select an exact topology node before final confirmation so allowed paths are evidence-bound.</small></div>`;
    }
    const neighbourChips = [
      ...(context.dependencies || []).slice(0, 4).map(value => `dependency · ${value}`),
      ...(context.callers || []).slice(0, 3).map(value => `caller · ${value}`),
      ...(context.tests || []).slice(0, 3).map(value => `test · ${value}`),
    ];
    return `<div class="gate-dialogue-anchor"><span class="pill">selected topology evidence</span><strong>${esc(node.label || node.id)}</strong><code>${esc(node.file_path || '—')} · ${esc(node.symbol || 'global scope')} · lines ${esc((node.line_range || []).join('–') || '—')}</code><small>${esc(node.projection_truth || 'EXACT_TOPOLOGY')} · visual selection has no patch authority</small><div class="gate-dialogue-neighbours">${neighbourChips.map(item => `<span>${esc(item)}</span>`).join('') || '<span>no bounded neighbours returned</span>'}</div></div>`;
  }

  function listHtml(items, formatter) {
    if (!items?.length) return '<span class="bilateral-empty">None proposed yet.</span>';
    return `<ul>${items.map(item => `<li>${esc(formatter ? formatter(item) : String(item))}</li>`).join('')}</ul>`;
  }

  function bilateralHtml(packet) {
    if (!packet) return '';
    const guards = packet.proposed_guardrails || [];
    const hard = guards.filter(item => ['HARD_ARCHITECTURAL', 'HARD_AUTHORITY', 'DOMAIN_REQUIRED'].includes(item.hardness));
    const editable = guards.filter(item => !hard.includes(item));
    const teach = packet.paired_teach_back || {};
    return `<div class="bilateral-grid">
      <section class="bilateral-panel"><h4>What Aura thinks you want</h4>${listHtml(packet.positive_requirements)}</section>
      <section class="bilateral-panel negative"><h4>What Aura thinks you do not want</h4>${listHtml(packet.negative_requirements, item => item.statement || item.target || '')}</section>
      <section class="bilateral-panel hard"><h4>Locked hard guardrails</h4>${listHtml(hard, item => item.statement)}</section>
      <section class="bilateral-panel editable"><h4>Proposed editable guardrails</h4>${listHtml(editable.slice(0, 8), item => item.statement)}</section>
      <section class="bilateral-panel"><h4>What Aura will preserve</h4>${listHtml(teach.will_preserve)}</section>
      <section class="bilateral-panel negative"><h4>When Aura will stop or escalate</h4>${listHtml(teach.will_stop_or_escalate_if)}</section>
      <section class="bilateral-panel"><h4>Positive example</h4>${listHtml(teach.positive_examples)}</section>
      <section class="bilateral-panel negative"><h4>Negative example</h4>${listHtml(teach.negative_examples)}</section>
    </div>`;
  }

  function clarificationHtml(packet, state) {
    if (packet?.status !== 'CLARIFICATION_REQUIRED') return '';
    const question = packet.next_clarification_question || {};
    const candidates = question.candidate_answers || [];
    return `<div class="clarification-box"><span class="pill">clarification required</span><strong>${esc(question.question || 'Clarification is required.')}</strong><small>${esc(question.why_it_changes_execution || '')}</small>${candidates.length ? `<div class="guardrail-tags">${candidates.map(item => `<span>${esc(item)}</span>`).join('')}</div>` : ''}<label for="human-gate-clarification">Your answer</label><input id="human-gate-clarification" value="${esc(state.clarification || '')}" placeholder="Give the exact outcome, boundary, or decision…"><button id="human-gate-clarify" type="button" class="primary">Submit clarification</button></div>`;
  }

  function responseHtml(state) {
    const packet = state.pending;
    const decision = state.decision;
    if (!packet && !decision) return '<p class="muted">Aura has not compiled a bilateral interpretation for this gate yet.</p>';
    if (packet) {
      const provenance = packet.response_provenance || {};
      const next = packet.recommended_action || {};
      return `<div class="gate-dialogue-response" data-status="${esc(packet.status)}"><span class="pill">${esc(packet.status)}</span><p>${esc(packet.aura_response || '')}</p>${bilateralHtml(packet)}${clarificationHtml(packet, state)}${next.action_id ? `<p><strong>Deterministic guarded next action:</strong> ${esc(next.label || next.action_id)} · ${esc(next.description || '')}</p>` : '<p class="gate-dialogue-warning">No work transition is admitted; confirmation cannot bypass missing evidence.</p>'}<small class="gate-dialogue-provenance">${provenance.model_used ? `external voice: ${esc(provenance.provider)} · ${esc(provenance.model)}` : `deterministic local response · ${esc(provenance.fallback_reason || 'no external model required')}`} · requirements and route authority remain deterministic</small></div>`;
    }
    const execution = state.execution || {};
    const compilation = state.compilation || {};
    const intent = compilation.intent_packet || {};
    const receipt = compilation.confirmation_receipt || {};
    const executionText = state.gateCompleted
      ? 'The confirmed guarded action completed for this gate.'
      : execution.ok === false
        ? `Intent was confirmed, but the guarded action was denied: ${execution.message || execution.error || 'missing evidence'}`
        : 'Intent was confirmed. The gate still requires its declared evidence before completion.';
    return `<div class="gate-dialogue-response" data-status="${esc(decision.status || '')}"><span class="pill">${esc(decision.status || '')}</span><p>${esc(executionText)}</p>${intent.intent_digest ? `<code>intent ${esc(intent.intent_digest)} · confirmation ${esc(receipt.confirmation_id || '—')}</code>` : ''}</div>`;
  }

  function renderGateDialogue() {
    if (!installPanel()) return;
    const index = stageIndex();
    const state = stageState(index);
    const phase = S.workflow?.current_phase || stageKey(index);
    const panel = $('human-gate-dialogue');
    panel.innerHTML = `
      <div class="gate-dialogue-head"><div><p class="eyebrow">Bilateral Gate Dialogue · topology-anchored intent</p><h3>Define what Aura should and should not do before ${esc(stageKey(index))}</h3></div><span class="pill">workflow ${esc(phase)}</span></div>
      ${anchorHtml()}
      <label for="human-gate-comment"><strong>Your request, prohibited outcomes, correction, or concern</strong></label>
      <textarea id="human-gate-comment" maxlength="6000" placeholder="State the desired result and what Aura must not do…">${esc(state.draft)}</textarea>
      <div class="gate-dialogue-actions"><span class="gate-dialogue-notice">Aura may clarify and compile canonical intent references. It may not advance, patch, commit, push, merge, deploy, or promote learning without the separate governed gates.</span><div><button id="human-gate-clear" type="button" class="secondary">Clear</button> <button id="human-gate-add-guardrail" type="button" class="secondary">Add guardrail</button> <button id="human-gate-address" type="button" class="primary">Ask Aura to refine this</button></div></div>
      ${responseHtml(state)}
      <div class="gate-dialogue-approval"><span class="gate-dialogue-notice ${state.gateCompleted ? 'gate-dialogue-success' : state.notice?.includes('denied') ? 'gate-dialogue-denied' : ''}">${esc(state.notice || dialogue.notice)}</span><div><button id="human-gate-reject" type="button" class="secondary" ${state.pending ? '' : 'hidden'}>Reject and correct</button> <button id="human-gate-approve" type="button" class="primary" ${state.pending?.can_confirm_intent ? '' : 'hidden'}>Confirm intent and attempt next gate</button></div></div>`;
    syncButtons();
  }

  function syncButtons() {
    const state = stageState();
    const ask = $('human-gate-address');
    const clarify = $('human-gate-clarify');
    const approve = $('human-gate-approve');
    const reject = $('human-gate-reject');
    if (ask) ask.disabled = dialogue.busy || !String(state.draft || '').trim();
    if (clarify) clarify.disabled = dialogue.busy || !String(state.clarification || '').trim();
    if (approve) approve.disabled = dialogue.busy || !state.pending?.can_confirm_intent;
    if (reject) reject.disabled = dialogue.busy || !state.pending;
    const next = $('human-tour-next');
    if (next && S.humanWorkspace?.tourActive) {
      next.disabled = dialogue.busy || stageIndex() === STAGES.length - 1 || !state.gateCompleted;
      next.title = state.gateCompleted
        ? 'Inspect the next completed gate'
        : 'Aura must refine intent, receive confirmation, and complete the guarded action first';
    }
  }

  function setBusy(value, notice = '') {
    dialogue.busy = Boolean(value);
    if (notice) stageState().notice = notice;
    renderGateDialogue();
  }

  function addGuardrail() {
    const state = stageState();
    const statement = window.prompt('Add an explicit “Do not…” guardrail:');
    if (!statement?.trim()) return;
    const text = statement.trim();
    const appended = `${String(state.draft || '').trim()}\n${/^do not\b/i.test(text) ? text : `Do not ${text}`}`.trim();
    invalidate('Human-added guardrail appended. Ask Aura to recompile the bilateral interpretation.');
    state.draft = appended;
    renderGateDialogue();
  }

  async function addressIntent() {
    const state = stageState();
    const comment = String(state.draft || '').trim();
    if (!comment) return;
    setBusy(true, 'Aura is extracting positive and negative requirements, guardrails, and execution-changing ambiguities…');
    try {
      const result = await S.api('/api/showcase/human/gate/address', {
        comment: `${BILATERAL_MARKER} ${comment}`,
        stage_hint: stageKey(),
        node_context: dialogue.nodeContext || {},
        prefer_model: true,
      });
      if (!result.ok) throw new Error(result.reason || result.error || 'Gate refinement was denied');
      state.pending = result;
      state.decision = null;
      state.compilation = null;
      state.execution = null;
      state.gateCompleted = false;
      state.clarification = '';
      state.notice = result.status === 'CLARIFICATION_REQUIRED'
        ? 'Aura found an execution-changing ambiguity. Answer it before confirming.'
        : 'Review the paired teach-back and guardrails before confirming canonical intent.';
    } catch (error) {
      state.pending = null;
      state.notice = `Gate refinement denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function submitClarification() {
    const state = stageState();
    if (!state.pending || !String(state.clarification || '').trim()) return;
    setBusy(true, 'Compiling your clarification into the same bounded refinement session…');
    try {
      const result = await S.api('/api/showcase/human/gate/address', {
        comment: `[AURA_CLARIFICATION_ANSWER:${state.pending.proposal_id}] ${state.clarification.trim()}`,
        stage_hint: stageKey(),
        node_context: dialogue.nodeContext || {},
        prefer_model: false,
      });
      if (!result.ok) throw new Error(result.reason || result.error || 'Clarification was denied');
      state.pending = result;
      state.clarification = '';
      state.notice = result.status === 'CLARIFICATION_REQUIRED'
        ? 'One more bounded ambiguity remains.'
        : 'Clarification complete. Review the paired teach-back and confirm or correct it.';
    } catch (error) {
      state.notice = `Clarification denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function approveIntent(approved) {
    const index = stageIndex();
    const state = stageState(index);
    if (!state.pending) return;
    setBusy(true, approved ? 'Binding your confirmation to the exact repository, phase, topology, requirements, and guardrails…' : 'Recording rejection…');
    try {
      const result = await S.api('/api/showcase/human/gate/approve', {
        proposal_id: state.pending.proposal_id,
        approved: Boolean(approved),
        stage_hint: stageKey(index),
        current_node_context: dialogue.nodeContext || {},
        reviewer: 'showcase_human',
        note: approved ? 'Confirmed canonical bilateral intent for the next existing guarded workflow gate only.' : 'Rejected for correction.',
      });
      if (!result.ok) throw new Error(result.reason || result.error || 'Gate confirmation was denied');
      state.decision = result.decision;
      state.compilation = result.canonical_compilation || null;
      state.pending = null;
      state.notice = result.note || '';
      if (approved) {
        S.workflow = result.workflow || S.workflow;
        await executeApprovedStage(index, state);
      }
    } catch (error) {
      state.notice = `Confirmation denied: ${error.message}`;
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
      state.gateCompleted = Boolean(activeTask() || S.handoff || S.workflow?.objective);
      if (!state.gateCompleted) result = {ok: false, message: 'A bounded task or handoff is still required.'};
    } else if (index === 1) {
      if (!hasEvidence('objective')) result = await action('set_objective', {objective: buildTaskObjective(activeTask())});
      state.gateCompleted = Boolean(result.ok && (S.workflow?.objective || hasEvidence('objective')));
    } else if (index === 2) {
      if (!hasEvidence('grounding')) result = await action('ground_context');
      state.gateCompleted = Boolean(result.ok && hasEvidence('grounding'));
    } else if (index === 3) {
      if (!hasEvidence('plan_phase_hash')) result = await action('prepare_capsule', {acceptance_criteria: activeTask()?.acceptance_criteria || []});
      state.gateCompleted = Boolean(result.ok && hasEvidence('plan_phase_hash') && hasEvidence('act_capsules'));
    } else if (index === 4) {
      const diff = String(S.humanWorkspace?.candidateDiff || $('human-candidate-diff')?.value || '').trim();
      if (!diff) {
        result = {ok: false, message: 'A candidate unified diff is required. The confirmed intent remains available for revision.'};
      } else {
        const evidence = S.workflow?.evidence || {};
        if (!hasEvidence('staged_patch')) result = await action('stage_patch', {
          candidate_diff: diff,
          affected_files: evidence.affected_files || evidence.grounding?.localized_files || [],
          affected_symbols: evidence.grounding?.localized_symbols || [],
        });
      }
      state.gateCompleted = Boolean(result.ok && hasEvidence('staged_patch'));
    } else if (index === 5) {
      if (!hasEvidence('test_evidence')) result = await action('run_tests', {test_targets: S.workflow?.evidence?.test_targets || []});
      if (result.ok && !hasEvidence('verification_packet')) result = await action('verify_patch');
      state.gateCompleted = Boolean(result.ok && hasEvidence('test_evidence') && hasEvidence('verification_packet'));
    } else if (index === 6) {
      if (!hasEvidence('hotswap_status')) result = await action('check_hotswap');
      if (result.ok && !hasEvidence('human_review')) result = await action('human_review', {
        approved: false,
        reviewer: 'showcase_human',
        note: 'Gate Dialogue confirmed continuation to a review packet only. No production approval or merge was granted.',
      });
      if (result.ok && !hasEvidence('review_packet')) result = await action('export_handoff');
      state.gateCompleted = Boolean(result.ok && (hasEvidence('human_review') || hasEvidence('review_packet')));
    }
    state.execution = result;
    if (!state.gateCompleted) {
      state.notice = `Intent was confirmed, but the guarded action did not complete: ${result.message || result.error || 'missing evidence'}. The output remains inspectable in the Attempt Archive.`;
      return;
    }
    state.notice = index === STAGES.length - 1
      ? 'Review packet prepared. No commit, push, merge, deployment, or grammar promotion occurred.'
      : 'The confirmed guarded action completed. Moving to the next gate.';
    if (index < STAGES.length - 1) S.showHumanStage?.(index + 1);
  }

  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    if (target.closest('#human-tour-next') && S.humanWorkspace?.tourActive) {
      const state = stageState();
      if (!state.gateCompleted) {
        event.preventDefault();
        event.stopImmediatePropagation();
        state.notice = 'Aura must refine and confirm bilateral intent, then complete the real guarded action before moving forward.';
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
