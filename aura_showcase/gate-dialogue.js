'use strict';

(() => {
  const S = window.Showcase;
  if (!S || !S.$ || S.gateDialogueInstalled) return;
  S.gateDialogueInstalled = true;
  const $ = S.$, esc = S.esc;

  const STAGES = ['INTAKE', 'FRAME', 'GROUND', 'PLAN', 'ACT', 'PROVE', 'DECIDE'];
  const DEFAULT_INTENTS = [
    'Use this selected topology evidence and explain the safest bounded entry point. Do not infer authority that is not explicitly declared.',
    'Frame the objective around this selected file or symbol. Do not expand scope, hide ambiguity, or grant production authority.',
    'Ground my intent in this node, its dependencies, callers, tests, definitions, and visible evidence gaps. Do not treat topology as patch authority.',
    'Prepare the smallest Arena capsule that satisfies the positive requirements and proves the negative requirements while preserving rollback boundaries.',
    'Address the candidate change inside the confirmed scope. Do not touch undeclared files, effects, or external services.',
    'Explain the positive, negative, preservation, lifecycle, and independent verifier evidence required before review.',
    'Summarize the evidence, unresolved risk, and review-only next step. Do not commit, push, merge, deploy, or promote learning.',
  ];

  const dialogue = S.humanGateDialogue = S.humanGateDialogue || {
    nodeContext: {},
    topologyPacket: null,
    byStage: {},
    busy: false,
    notice: 'Select a topology node or use the current gate, then state what Aura should and should not do.',
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
        gateCompleted: false,
        notice: '',
        clarification: '',
        addedGuardrail: '',
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
    return `${task.title}. ${task.summary} Acceptance criteria: ${criteria}. Confirmed negative requirements and guardrails remain binding. Prohibited actions: ${prohibited}.`;
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
      dependencies: nodeList(workspace.dependencies).length
        ? nodeList(workspace.dependencies)
        : relations.filter(item => item.source === selectedId).map(item => item.label),
      callers: nodeList(workspace.callers).length
        ? nodeList(workspace.callers)
        : relations.filter(item => item.target === selectedId).map(item => item.label),
      tests: nodeList(workspace.tests),
      relations,
      candidate_faults: (workspace.candidate_faults || []).filter(item => item.node_id === selectedId).slice(0, 8),
      full_topology_transferred: false,
      visual_topology_patch_authority: false,
    };
  }

  function resetCurrentApproval(message) {
    const state = stageState();
    state.pending = null;
    state.decision = null;
    state.execution = null;
    state.gateCompleted = false;
    state.notice = message;
  }

  function captureTopology(packet) {
    if (!packet?.ok || !packet.workspace) return;
    const previous = JSON.stringify(dialogue.nodeContext || {});
    dialogue.topologyPacket = packet;
    dialogue.nodeContext = topologyContext(packet);
    const current = JSON.stringify(dialogue.nodeContext || {});
    if (previous && previous !== '{}' && previous !== current) {
      resetCurrentApproval('Topology selection changed. The prior clarification, teach-back, confirmation receipt, and gate approval are stale.');
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
      .gate-dialogue-anchor,.bilateral-section{display:grid;gap:6px;padding:11px 12px;border-radius:12px;background:rgba(45,212,191,.07);border-left:3px solid #2dd4bf}
      .gate-dialogue-anchor code{white-space:normal;overflow-wrap:anywhere}.gate-dialogue-neighbours,.guardrail-list{display:flex;gap:7px;flex-wrap:wrap}
      .gate-dialogue-neighbours span,.guardrail-list span{font-size:11px;padding:5px 8px;border-radius:999px;background:rgba(148,163,184,.11)}
      .gate-dialogue-card textarea,.gate-dialogue-card input{width:100%}.gate-dialogue-card textarea{min-height:105px;resize:vertical}
      .gate-dialogue-response{padding:14px;border-radius:13px;background:rgba(3,10,14,.8);border:1px solid rgba(148,163,184,.16);display:grid;gap:9px}
      .gate-dialogue-response[data-status*="CLARIFICATION"]{border-color:rgba(251,146,60,.45)}
      .gate-dialogue-response[data-status*="CONFIRMATION"]{border-color:rgba(250,204,21,.42)}
      .gate-dialogue-response[data-status*="CONFIRMED"],.gate-dialogue-response[data-status^="APPROVED"]{border-color:rgba(45,212,191,.48)}
      .gate-dialogue-provenance,.gate-dialogue-notice{font-size:11px;color:#92aab3}.gate-dialogue-warning{color:#facc15}.gate-dialogue-denied{color:#fb7185}.gate-dialogue-success{color:#7ff4df}
      .gate-dialogue-card button[hidden]{display:none}.bilateral-section h4{margin:0}.bilateral-section ul{margin:0;padding-left:20px}.bilateral-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:9px}
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
        if (state.pending || state.decision) {
          resetCurrentApproval('The request changed. The prior refinement and confirmation are stale; ask Aura again.');
        }
      }
      if (event.target?.id === 'human-gate-clarification') state.clarification = event.target.value;
      if (event.target?.id === 'human-gate-added-guardrail') state.addedGuardrail = event.target.value;
      syncButtons();
    });
    panel.addEventListener('click', event => {
      const button = event.target instanceof Element ? event.target.closest('button') : null;
      if (!button) return;
      if (button.id === 'human-gate-address') addressIntent();
      if (button.id === 'human-gate-clarify') submitClarification();
      if (button.id === 'human-gate-confirm') confirmIntent();
      if (button.id === 'human-gate-approve') approveGate();
      if (button.id === 'human-gate-reject') rejectIntent();
      if (button.id === 'human-gate-correct') correctIntent();
      if (button.id === 'human-gate-add-guardrail') addGuardrail();
      if (button.id === 'human-gate-defer') {
        state.notice = 'Intent confirmation deferred. No workflow action executed and no authority was granted.';
        renderGateDialogue();
      }
      if (button.id === 'human-gate-clear') {
        Object.assign(state, {
          draft: '', pending: null, decision: null, execution: null,
          gateCompleted: false, clarification: '', addedGuardrail: '',
          notice: 'Draft cleared. No workflow action executed.',
        });
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
      return `<div class="gate-dialogue-anchor"><span class="pill">current gate</span><strong>${esc(task?.title || S.workflow?.current_phase || stageKey())}</strong><small>No topology node is selected. Contextual words such as “this” or “it” may require clarification.</small></div>`;
    }
    const neighbourChips = [
      ...(context.dependencies || []).slice(0, 4).map(value => `dependency · ${value}`),
      ...(context.callers || []).slice(0, 3).map(value => `caller · ${value}`),
      ...(context.tests || []).slice(0, 3).map(value => `test · ${value}`),
    ];
    return `<div class="gate-dialogue-anchor"><span class="pill">selected topology evidence</span><strong>${esc(node.label || node.id)}</strong><code>${esc(node.file_path || '—')} · ${esc(node.symbol || 'global scope')} · lines ${esc((node.line_range || []).join('–') || '—')}</code><small>${esc(node.projection_truth || 'EXACT_TOPOLOGY')} · visual selection has no patch authority</small><div class="gate-dialogue-neighbours">${neighbourChips.map(item => `<span>${esc(item)}</span>`).join('') || '<span>no bounded neighbours returned</span>'}</div></div>`;
  }

  function listHtml(items, empty = 'None projected') {
    const values = (items || []).map(item => typeof item === 'string' ? item : item?.statement || item?.question || '').filter(Boolean);
    return values.length ? `<ul>${values.map(value => `<li>${esc(value)}</li>`).join('')}</ul>` : `<p class="muted">${esc(empty)}</p>`;
  }

  function guardrailHtml(items, hard) {
    const rows = (items || []).filter(Boolean);
    if (!rows.length) return '<p class="muted">None projected</p>';
    return `<div class="guardrail-list">${rows.map(item => `<span title="${esc(item.rationale || '')}">${hard ? 'locked' : 'editable'} · ${esc(item.statement || '')}</span>`).join('')}</div>`;
  }

  function teachBackHtml(refinement) {
    const tb = refinement?.paired_teach_back || {};
    return `<div class="bilateral-grid">
      <section class="bilateral-section"><h4>Aura will do</h4>${listHtml(tb.will_do || refinement?.positive_requirements)}</section>
      <section class="bilateral-section"><h4>Aura will not do</h4>${listHtml(tb.will_not_do || refinement?.negative_requirements)}</section>
      <section class="bilateral-section"><h4>Aura will preserve</h4>${listHtml(tb.will_preserve)}</section>
      <section class="bilateral-section"><h4>Aura will stop or escalate if</h4>${listHtml(tb.will_stop_or_escalate_if)}</section>
      <section class="bilateral-section"><h4>Positive example</h4>${listHtml(tb.positive_examples)}</section>
      <section class="bilateral-section"><h4>Negative example</h4>${listHtml(tb.negative_examples)}</section>
    </div>`;
  }

  function refinementHtml(packet) {
    const refinement = packet?.refinement || {};
    const definitions = refinement.definitions || [];
    const unresolved = refinement.unresolved_ambiguities || [];
    return `<div class="bilateral-grid">
      <section class="bilateral-section"><h4>Your request</h4><p>${esc(packet?.human_comment || '')}</p></section>
      <section class="bilateral-section"><h4>What Aura thinks you want</h4>${listHtml(refinement.positive_requirements)}</section>
      <section class="bilateral-section"><h4>What Aura thinks you do not want</h4>${listHtml(refinement.negative_requirements)}</section>
      <section class="bilateral-section"><h4>Terms needing definition</h4>${definitions.length ? definitions.map(item => `<p><strong>${esc(item.term || '')}</strong><br><small>means: ${esc((item.means || []).join('; '))}<br>does not mean: ${esc((item.does_not_mean || []).join('; ') || '—')}</small></p>`).join('') : '<p class="muted">None</p>'}</section>
      <section class="bilateral-section"><h4>Proposed hard guardrails</h4>${guardrailHtml(refinement.hard_guardrails, true)}<small>These cannot be removed through Gate Dialogue.</small></section>
      <section class="bilateral-section"><h4>Proposed editable guardrails</h4>${guardrailHtml(refinement.editable_guardrails, false)}</section>
      <section class="bilateral-section"><h4>Human-added guardrails</h4>${guardrailHtml(refinement.human_added_guardrails, false)}</section>
      <section class="bilateral-section"><h4>Unresolved ambiguity</h4>${listHtml(unresolved, 'None')}</section>
    </div>${refinement.paired_teach_back ? `<section class="bilateral-section"><h4>Aura’s paired teach-back</h4>${teachBackHtml(refinement)}</section>` : ''}`;
  }

  function responseHtml(state) {
    const packet = state.pending;
    const decision = state.decision;
    if (!packet && !decision) return '<p class="muted">Aura has not compiled a gate-specific bilateral intent yet.</p>';
    if (packet) {
      const provenance = packet.response_provenance || {};
      const next = packet.recommended_action || {};
      return `<div class="gate-dialogue-response" data-status="${esc(packet.status || '')}">
        <span class="pill">${esc(packet.status || '')}</span>
        <p>${esc(packet.aura_response || '')}</p>
        ${refinementHtml(packet)}
        ${packet.confirmation_receipt ? `<section class="bilateral-section"><h4>Confirmation receipt</h4><code>${esc(packet.confirmation_receipt.confirmation_id || '')}</code><small>repository ${esc(packet.confirmation_receipt.repository_head || '')} · source tree ${esc(packet.confirmation_receipt.source_tree_digest || '')}</small></section>` : ''}
        ${next.action_id ? `<p><strong>Deterministic guarded next action:</strong> ${esc(next.label || next.action_id)} · ${esc(next.description || '')}</p>` : '<p class="gate-dialogue-warning">No work transition is currently admitted; confirmation cannot bypass missing evidence.</p>'}
        <small class="gate-dialogue-provenance">${provenance.model_used ? `external voice: ${esc(provenance.provider)} · ${esc(provenance.model)}` : `deterministic local response · ${esc(provenance.fallback_reason || 'no external model required')}`} · canonical records and deterministic route remain authoritative</small>
      </div>`;
    }
    const execution = state.execution || {};
    const executionText = state.gateCompleted
      ? 'The separately approved guarded action completed for this gate.'
      : execution.ok === false
        ? `Gate approval was recorded, but the guarded action was denied: ${execution.message || execution.error || 'missing evidence'}`
        : 'The approval was recorded. The gate still requires its declared evidence.';
    return `<div class="gate-dialogue-response" data-status="${esc(decision.status || '')}"><span class="pill">${esc(decision.status || '')}</span><p>${esc(executionText)}</p></div>`;
  }

  function actionControls(state) {
    const status = state.pending?.status || '';
    const question = state.pending?.next_clarification_question || {};
    if (status === 'PENDING_CLARIFICATION') {
      return `<div class="bilateral-section"><label for="human-gate-clarification"><strong>${esc(question.question || 'Clarification required')}</strong></label><small>${esc(question.why_it_changes_execution || '')}</small><input id="human-gate-clarification" maxlength="2000" value="${esc(state.clarification || '')}" placeholder="Provide the exact answer…"><button id="human-gate-clarify" type="button" class="primary">Record clarification</button></div>`;
    }
    if (status === 'PENDING_INTENT_CONFIRMATION') {
      return `<div class="gate-dialogue-approval"><span class="gate-dialogue-notice">Confirm the paired contract, correct the request, add a guardrail, or defer. Confirmation does not approve workflow execution.</span><div><button id="human-gate-correct" type="button" class="secondary">Correct</button> <button id="human-gate-defer" type="button" class="secondary">Defer</button> <button id="human-gate-confirm" type="button" class="primary">Confirm bilateral intent</button></div></div>`;
    }
    if (status === 'INTENT_CONFIRMED_PENDING_GATE_APPROVAL') {
      return `<div class="gate-dialogue-approval"><span class="gate-dialogue-notice">The canonical bilateral contract is confirmed. A separate gate approval is required.</span><div><button id="human-gate-reject" type="button" class="secondary">Reject gate attempt</button> <button id="human-gate-approve" type="button" class="primary">Approve confirmed intent and attempt next gate</button></div></div>`;
    }
    return '';
  }

  function renderGateDialogue() {
    if (!installPanel()) return;
    const index = stageIndex();
    const state = stageState(index);
    const phase = S.workflow?.current_phase || stageKey(index);
    const panel = $('human-gate-dialogue');
    panel.innerHTML = `
      <div class="gate-dialogue-head"><div><p class="eyebrow">Gate dialogue · bilateral human intent</p><h3>Clarify what Aura should and should not do before ${esc(stageKey(index))}</h3></div><span class="pill">workflow ${esc(phase)}</span></div>
      ${anchorHtml()}
      <label for="human-gate-comment"><strong>Your request, prohibited outcomes, correction, or question</strong></label>
      <textarea id="human-gate-comment" maxlength="6000" placeholder="Tell Aura what to do, what not to do, what to preserve, and when to stop…">${esc(state.draft)}</textarea>
      <div class="bilateral-section"><label for="human-gate-added-guardrail"><strong>Add a human guardrail</strong></label><input id="human-gate-added-guardrail" maxlength="1200" value="${esc(state.addedGuardrail || '')}" placeholder="Example: Do not touch files outside the renderer and its focused tests."><button id="human-gate-add-guardrail" type="button" class="secondary">Add Guardrail</button></div>
      <div class="gate-dialogue-actions"><span class="gate-dialogue-notice">Aura proposes clarification and canonical records. It may not advance, patch, commit, push, merge, deploy, or promote learning from this dialogue.</span><div><button id="human-gate-clear" type="button" class="secondary">Clear</button> <button id="human-gate-address" type="button" class="primary">Ask Aura to refine this</button></div></div>
      ${responseHtml(state)}
      ${actionControls(state)}
      <div class="gate-dialogue-approval"><span class="gate-dialogue-notice ${state.gateCompleted ? 'gate-dialogue-success' : state.notice?.includes('denied') ? 'gate-dialogue-denied' : ''}">${esc(state.notice || dialogue.notice)}</span></div>`;
    syncButtons();
  }

  function syncButtons() {
    const state = stageState();
    const disabled = dialogue.busy;
    const bindings = {
      'human-gate-address': disabled || !String(state.draft || '').trim(),
      'human-gate-clarify': disabled || !String(state.clarification || '').trim(),
      'human-gate-confirm': disabled || state.pending?.status !== 'PENDING_INTENT_CONFIRMATION',
      'human-gate-approve': disabled || state.pending?.status !== 'INTENT_CONFIRMED_PENDING_GATE_APPROVAL',
      'human-gate-reject': disabled || !state.pending,
      'human-gate-add-guardrail': disabled || !String(state.addedGuardrail || '').trim(),
    };
    Object.entries(bindings).forEach(([id, value]) => { const node = $(id); if (node) node.disabled = value; });
    const next = $('human-tour-next');
    if (next && S.humanWorkspace?.tourActive) {
      next.disabled = disabled || stageIndex() === STAGES.length - 1 || !state.gateCompleted;
      next.title = state.gateCompleted
        ? 'Inspect the next completed gate'
        : 'Bilateral intent must be clarified, confirmed, separately approved, and completed first';
    }
  }

  function setBusy(value, notice = '') {
    dialogue.busy = Boolean(value);
    if (notice) stageState().notice = notice;
    renderGateDialogue();
  }

  function addGuardrail() {
    const state = stageState();
    const value = String(state.addedGuardrail || '').trim();
    if (!value) return;
    const prefix = /\b(do not|never|must not|cannot|can't)\b/i.test(value) ? '' : 'Do not ';
    state.draft = `${String(state.draft || '').trim()}\nHuman-added guardrail: ${prefix}${value}`.trim();
    state.addedGuardrail = '';
    resetCurrentApproval('Human guardrail added to the request. Ask Aura to rebuild the bilateral contract.');
    renderGateDialogue();
  }

  function correctIntent() {
    const state = stageState();
    state.pending = null;
    state.decision = null;
    state.execution = null;
    state.gateCompleted = false;
    state.notice = 'Edit the request or add a guardrail, then ask Aura to rebuild the canonical refinement.';
    renderGateDialogue();
    $('human-gate-comment')?.focus();
  }

  async function addressIntent() {
    const index = stageIndex();
    const state = stageState(index);
    const comment = String(state.draft || '').trim();
    if (!comment) return;
    setBusy(true, 'Aura is extracting positive and negative requirements, definitions, ambiguities, guardrails, and paired teach-back…');
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
      state.gateCompleted = false;
      state.notice = result.status === 'PENDING_CLARIFICATION'
        ? 'Answer the targeted clarification before Aura can produce a confirmable teach-back.'
        : 'Review both intent polarities, definitions, guardrails, and teach-back before confirmation.';
    } catch (error) {
      state.pending = null;
      state.notice = `Gate dialogue denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function postApproval(note, approved = true) {
    const index = stageIndex();
    const state = stageState(index);
    if (!state.pending) return null;
    return S.api('/api/showcase/human/gate/approve', {
      proposal_id: state.pending.proposal_id,
      approved: Boolean(approved),
      stage_hint: stageKey(index),
      current_node_context: dialogue.nodeContext || {},
      reviewer: 'showcase_human',
      note,
    });
  }

  async function submitClarification() {
    const state = stageState();
    const answer = String(state.clarification || '').trim();
    if (!answer) return;
    setBusy(true, 'Recording the human clarification against the exact session and context…');
    try {
      const result = await postApproval(`CLARIFY_INTENT:${answer}`, true);
      if (!result?.ok) throw new Error(result?.reason || result?.error || 'Clarification was denied');
      state.pending = result;
      state.clarification = '';
      state.notice = result.status === 'PENDING_CLARIFICATION'
        ? 'Clarification recorded. One more targeted question remains.'
        : 'Clarification complete. Review the rebuilt paired teach-back.';
    } catch (error) {
      state.notice = `Clarification denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function confirmIntent() {
    const state = stageState();
    setBusy(true, 'Binding human confirmation to the repository head, source tree, phase, topology, definitions, guardrails, authority, and allowed paths…');
    try {
      const result = await postApproval('CONFIRM_INTENT:Confirmed after reviewing both intent polarities, definitions, guardrails, examples, and paired teach-back.', true);
      if (!result?.ok) throw new Error(result?.reason || result?.error || 'Intent confirmation was denied');
      state.pending = result;
      state.notice = 'Canonical bilateral intent confirmed. Review the receipt before separately approving the guarded gate attempt.';
    } catch (error) {
      state.notice = `Intent confirmation denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function rejectIntent() {
    const state = stageState();
    setBusy(true, 'Recording human rejection…');
    try {
      const result = await postApproval('Rejected for revision.', false);
      if (!result?.ok) throw new Error(result?.reason || result?.error || 'Rejection was denied');
      state.decision = result.decision;
      state.pending = null;
      state.notice = result.note || 'Rejected. No workflow action executed.';
    } catch (error) {
      state.notice = `Rejection denied: ${error.message}`;
    } finally {
      dialogue.busy = false;
      renderGateDialogue();
    }
  }

  async function approveGate() {
    const index = stageIndex();
    const state = stageState(index);
    setBusy(true, 'Recording a separate gate approval against the current confirmation receipt…');
    try {
      const result = await postApproval('Approved to attempt the next existing guarded workflow gate only.', true);
      if (!result?.ok) throw new Error(result?.reason || result?.error || 'Gate approval was denied');
      state.decision = result.decision;
      state.pending = null;
      state.notice = result.note || '';
      S.workflow = result.workflow || S.workflow;
      await executeApprovedStage(index, state);
    } catch (error) {
      state.notice = `Gate approval denied: ${error.message}`;
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
        result = {ok: false, message: 'A candidate unified diff is required. The confirmed intent and empty attempt remain available for revision.'};
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
        note: 'Gate Dialogue approved continuation to a review packet only. No production approval or merge was granted.',
      });
      if (result.ok && !hasEvidence('review_packet')) result = await action('export_handoff');
      state.gateCompleted = Boolean(result.ok && (hasEvidence('human_review') || hasEvidence('review_packet')));
    }
    state.execution = result;
    if (!state.gateCompleted) {
      state.notice = `The gate approval was recorded, but the guarded action did not complete: ${result.message || result.error || 'missing evidence'}. The output remains inspectable for correction.`;
      return;
    }
    state.notice = index === STAGES.length - 1
      ? 'Review packet prepared. No commit, push, merge, deployment, professional action, physical work, or learning promotion occurred.'
      : 'The separately approved guarded action completed. Moving to the next gate.';
    if (index < STAGES.length - 1) S.showHumanStage?.(index + 1);
  }

  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    if (target.closest('#human-tour-next') && S.humanWorkspace?.tourActive && !stageState().gateCompleted) {
      event.preventDefault();
      event.stopImmediatePropagation();
      stageState().notice = 'Clarify, confirm, separately approve, and complete the real guarded action before moving forward.';
      renderGateDialogue();
      return;
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
