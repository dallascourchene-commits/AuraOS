// Aura Jarvis Surface — additive workflow, tool dock, and Civic map interface.
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  let workflowState = null;
  let toolDefinitions = [];
  let civicProjection = null;
  let civicProjectedFeatures = [];
  let civicHitRegions = [];

  async function jarvisApi(path, body) {
    const options = body === undefined ? {} : {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    };
    const response = await fetch(path, options);
    const data = await response.json();
    data.http_status = response.status;
    return data;
  }

  function activateSurface(surfaceId) {
    document.querySelectorAll('.surface').forEach(node => node.classList.toggle('is-active', node.id === surfaceId));
    document.querySelectorAll('.surface-tab').forEach(node => node.classList.toggle('is-active', node.dataset.surface === surfaceId));
    if (surfaceId === 'civic-workspace') {
      resizeCivicCanvas();
      refreshCivicProjection();
    }
  }

  document.querySelectorAll('.surface-tab').forEach(button => {
    button.addEventListener('click', () => activateSurface(button.dataset.surface));
  });

  function workflowPayloadFor(actionId) {
    const evidence = workflowState?.evidence || {};
    if (actionId === 'set_objective') {
      return { objective: $('workflow-objective')?.value || $('command-input')?.value || '' };
    }
    if (actionId === 'run_tests') return { test_targets: evidence.test_targets || [] };
    if (actionId === 'verify_patch') return { test_evidence: evidence.test_evidence || {} };
    if (actionId === 'check_hotswap') return {};
    if (actionId === 'human_review') {
      return { approved: false, note: 'Evidence reviewed in the Human Agent Arena. No merge requested.' };
    }
    return {};
  }

  async function confirmedWorkflowPayload(actionId, payload, intentText) {
    const phase = String(workflowState?.current_phase || 'FRAME');
    const proposal = await jarvisApi('/api/human-agent/gate/address', {
      comment: `${intentText || `Run ${actionId} with the displayed inputs.`} Do not widen the payload, bypass workflow guards, or grant commit, push, merge, deployment, or production authority.`,
      node_context: {},
      stage_hint: phase,
      prefer_model: false,
    });
    if (!proposal.ok || !proposal.can_confirm_intent) {
      throw new Error(proposal.reason || 'The bilateral intent requires clarification before execution.');
    }
    const teachBack = proposal.paired_teach_back || {};
    const summary = [
      `Will do: ${(teachBack.will_do || []).join('; ')}`,
      `Will not do: ${(teachBack.will_not_do || []).join('; ')}`,
      `Guardrails: ${(teachBack.guardrails || []).map(item => item.statement || item).join('; ')}`,
    ].join('\n\n');
    if (!window.confirm(`Confirm this exact guarded action?\n\n${summary}`)) {
      await jarvisApi('/api/human-agent/gate/approve', {
        proposal_id: proposal.proposal_id,
        approved: false,
        current_node_context: {},
        stage_hint: phase,
        note: 'Rejected in the standalone Human Agent Arena.',
      });
      throw new Error('Human confirmation was rejected.');
    }
    const approved = await jarvisApi('/api/human-agent/gate/approve', {
      proposal_id: proposal.proposal_id,
      approved: true,
      current_node_context: {},
      stage_hint: phase,
      reviewer: 'standalone_human',
      note: 'Confirmed the exact guarded action payload only.',
      action_payload: payload,
    });
    if (!approved.ok) throw new Error(approved.reason || 'Confirmation was denied.');
    const compilation = approved.canonical_compilation || {};
    const receipt = compilation.confirmation_receipt || {};
    const decision = approved.decision || {};
    return {
      ...payload,
      confirmation_id: receipt.confirmation_id || decision.confirmation_id || '',
      confirmation_receipt_id: receipt.confirmation_id || decision.confirmation_id || '',
      intent_digest: compilation.intent_packet?.intent_digest || decision.intent_digest || '',
      semantic_ledger_digest: compilation.semantic_ledger?.ledger_digest || decision.semantic_ledger_digest || '',
      repository_head: receipt.repository_head || '',
      source_tree_digest: receipt.source_tree_digest || '',
      workflow_id: decision.workflow_id || workflowState?.workflow_id || '',
      phase_hash: decision.phase_hash || '',
      node_digest: decision.node_digest || '',
    };
  }

  async function loadWorkflow() {
    try {
      workflowState = await jarvisApi('/api/human-agent/workflow');
      renderWorkflow(workflowState);
      if ($('workflow-objective') && workflowState.objective && !$('workflow-objective').value) {
        $('workflow-objective').value = workflowState.objective;
      }
    } catch (error) {
      if ($('workflow-status')) $('workflow-status').textContent = `Unavailable: ${error.message}`;
    }
  }

  function renderWorkflow(state) {
    const status = $('workflow-status');
    if (status) status.textContent = `${state.current_phase || 'FRAME'} · ${state.evidence_keys?.length || 0} evidence objects`;
    const host = $('workflow-actions');
    if (!host) return;
    const actions = state.actions || [];
    let previousPhase = '';
    host.innerHTML = actions.map((action, index) => {
      const phase = action.phase || '';
      const phaseLabel = phase !== previousPhase ? `<div class="workflow-phase">${escape(phase)}</div>` : '';
      previousPhase = phase;
      const missing = (action.missing_evidence || []).join(', ');
      return `${phaseLabel}<button type="button" class="workflow-action" data-workflow-action="${escape(action.action_id)}" data-status="${escape(action.status)}" title="${escape(missing ? `Missing: ${missing}` : action.purpose)}">
        <span class="step-index">${index + 1}</span>
        <span><strong>${escape(action.title)}</strong><small>${escape(action.purpose)}</small></span>
        <span class="gate-status">${escape(action.status)}</span>
      </button>`;
    }).join('');
    host.querySelectorAll('[data-workflow-action]').forEach(button => {
      button.addEventListener('click', () => executeWorkflowAction(button.dataset.workflowAction));
    });
  }

  async function executeWorkflowAction(actionId) {
    const evidence = $('workflow-evidence');
    if (evidence) evidence.innerHTML = '<p class="placeholder">Running grounded action…</p>';
    let result;
    try {
      const payload = workflowPayloadFor(actionId);
      const confirmedPayload = await confirmedWorkflowPayload(
        actionId,
        payload,
        `Run ${actionId} with the exact displayed payload.`
      );
      result = await jarvisApi('/api/human-agent/workflow/action', {
        action_id: actionId,
        payload: confirmedPayload,
      });
    } catch (error) {
      result = {ok: false, error: error.message || 'Confirmation failed.'};
    }
    renderWorkflowResult(result);
    workflowState = result.workflow || await jarvisApi('/api/human-agent/workflow');
    renderWorkflow(workflowState);
  }

  function renderWorkflowResult(result) {
    const transcript = $('command-transcript');
    if (transcript) transcript.innerHTML = `<span class="transcript-speaker">Aura</span><p>${escape(result.message || result.error || 'Action completed.')}</p>`;
    const host = $('workflow-evidence');
    if (!host) return;
    const missing = result.missing_evidence || [];
    const remediation = result.remediation || [];
    const produced = result.produced_evidence || {};
    const details = result.details || {};
    host.innerHTML = `
      <div class="evidence-head"><strong class="${result.ok ? 'evidence-allowed' : 'evidence-denied'}">${result.ok ? 'ALLOWED' : 'DENIED'}</strong><span>${escape(result.action_id || '')}</span></div>
      <div class="evidence-list">
        ${missing.length ? `<div class="evidence-item"><strong>Missing evidence</strong><div>${missing.map(escape).join(' · ')}</div></div>` : ''}
        ${remediation.length ? `<div class="evidence-item"><strong>Remediation</strong><div>${remediation.map(item => escape(item.label || item.action)).join(' → ')}</div></div>` : ''}
        ${Object.keys(produced).length ? `<div class="evidence-item"><strong>Produced</strong><pre>${escape(JSON.stringify(produced, null, 2))}</pre></div>` : ''}
        ${Object.keys(details).length ? `<details class="evidence-item"><summary>Exact result</summary><pre>${escape(JSON.stringify(details, null, 2))}</pre></details>` : ''}
      </div>`;
  }

  async function submitWorkflowCommand(command) {
    if (!command?.trim()) return;
    const transcript = $('command-transcript');
    if (transcript) transcript.innerHTML = `<span class="transcript-speaker">You</span><p>${escape(command)}</p>`;
    let result;
    try {
      const preview = await jarvisApi('/api/human-agent/workflow/command/preview', {
        command,
        payload: {},
      });
      if (preview.meta_transition) {
        result = await jarvisApi('/api/human-agent/workflow/command', {command, payload: {}});
      } else if (!preview.ok) {
        result = preview;
      } else {
        const confirmedPayload = await confirmedWorkflowPayload(
          preview.action_id,
          preview.execution_payload || {},
          `Run the command “${command}” as ${preview.action_id}.`
        );
        result = await jarvisApi('/api/human-agent/workflow/command', {
          command,
          payload: confirmedPayload,
        });
      }
    } catch (error) {
      result = {ok: false, error: error.message || 'Confirmation failed.'};
    }
    renderWorkflowResult(result);
    workflowState = result.workflow || await jarvisApi('/api/human-agent/workflow');
    renderWorkflow(workflowState);
    const objectiveInput = $('workflow-objective');
    if (objectiveInput && workflowState.objective) objectiveInput.value = workflowState.objective;
    // Preserve Aura's existing contextual buttons and topology commands as an optional lens.
    if (typeof window.runCommand === 'function') {
      try { await window.runCommand(command); } catch (_) { /* workflow remains authoritative */ }
    }
  }

  $('run-button')?.addEventListener('click', event => {
    event.stopImmediatePropagation();
    submitWorkflowCommand($('command-input')?.value || '');
  });
  $('command-input')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      event.stopImmediatePropagation();
      submitWorkflowCommand(event.currentTarget.value);
    }
  });
  $('workflow-objective-btn')?.addEventListener('click', () => executeWorkflowAction('set_objective'));
  $('mic-button')?.addEventListener('click', event => {
    event.stopImmediatePropagation();
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if ($('voice-status')) $('voice-status').textContent = 'Voice unsupported here. Type a command and press Send.';
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.onstart = () => { if ($('voice-status')) $('voice-status').textContent = 'Listening…'; };
    recognition.onerror = () => { if ($('voice-status')) $('voice-status').textContent = 'Voice failed. Type the command instead.'; };
    recognition.onresult = resultEvent => {
      const text = resultEvent.results[0][0].transcript || '';
      if ($('command-input')) $('command-input').value = text;
      if ($('voice-status')) $('voice-status').textContent = `Heard: ${text}`;
      submitWorkflowCommand(text);
    };
    recognition.start();
  });
  $('jarvis-mic-button')?.addEventListener('click', () => $('mic-button')?.click());

  async function loadTools() {
    try {
      const result = await jarvisApi('/api/human-agent/tools');
      toolDefinitions = result.tools || [];
      renderTools();
    } catch (error) {
      if ($('tool-dock')) $('tool-dock').textContent = `Tool runtime unavailable: ${error.message}`;
    }
  }

  function renderTools() {
    const host = $('tool-dock');
    if (!host) return;
    host.innerHTML = toolDefinitions.map(tool => `
      <button type="button" class="tool-card" data-tool-id="${escape(tool.tool_id)}">
        <span class="tool-runtime">${escape(tool.mode || 'trusted_builtin')} · ${escape(tool.capability || '')}</span>
        <strong>${escape(tool.title)}</strong>
        <small>${escape(tool.purpose)}</small>
      </button>`).join('');
    host.querySelectorAll('[data-tool-id]').forEach(button => {
      button.addEventListener('click', () => runTool(button.dataset.toolId));
    });
  }

  async function runTool(toolId) {
    const evidence = workflowState?.evidence || {};
    const inputs = {};
    if (toolId === 'test_lab') inputs.test_targets = evidence.test_targets || [];
    if (toolId === 'verifier') inputs.test_evidence = evidence.test_evidence || {};
    if (toolId === 'hotswap_gate') {
      inputs.staged_patch = evidence.staged_patch || null;
      inputs.test_evidence = evidence.test_evidence || null;
      inputs.verification_packet = evidence.verification_packet || null;
    }
    if (toolId === 'wasm_lab') inputs.component_ref = { kind: 'wasm_component', source: 'arena_request' };
    const result = await jarvisApi('/api/human-agent/tools/run', {
      tool_id: toolId,
      objective: workflowState?.objective || $('command-input')?.value || '',
      inputs,
    });
    renderWorkflowResult({
      ok: result.status === 'COMPLETED' && result.outputs?.ok !== false,
      action_id: toolId,
      message: result.status === 'DENIED'
        ? result.denial?.reason || 'Tool denied.'
        : `${toolId} finished with status ${result.status}.`,
      missing_evidence: result.denial?.missing || result.outputs?.missing_evidence || [],
      remediation: result.denial?.remediation || [],
      produced_evidence: result.outputs || {},
      details: result,
    });
    await loadWorkflow();
  }

  function currentCivicSessionId() {
    const text = $('civic-session-info')?.textContent || '';
    const match = text.match(/Session:\s*([A-Za-z0-9_-]+)/i);
    return match ? match[1] : '';
  }

  function civicZoom() {
    return Number($('civic-map-zoom')?.value || 11);
  }

  async function refreshCivicProjection() {
    const sessionId = currentCivicSessionId();
    if (!sessionId) {
      drawCivicEmpty('Create or run a Civic session to project governed data.');
      return;
    }
    const jurisdiction = $('civic-jurisdiction')?.value || '';
    const params = new URLSearchParams({ zoom: String(civicZoom()), viewer_scope: 'community' });
    if (jurisdiction) params.set('jurisdiction', jurisdiction);
    try {
      const result = await jarvisApi(`/api/civic/sessions/${encodeURIComponent(sessionId)}/map-projection?${params.toString()}`);
      if (!result.ok) {
        drawCivicEmpty(result.error || 'Map projection unavailable.');
        return;
      }
      civicProjection = result;
      civicProjectedFeatures = result.geojson?.features || [];
      populateJurisdictions(result.available_jurisdictions || [], result.jurisdiction_id || '');
      renderLayerChips(result.visible_layer_types || []);
      renderAccessibleMapData(result.accessible_rows || []);
      if ($('civic-map-scope')) {
        $('civic-map-scope').textContent = `${result.visible_feature_count} visible features · zoom ${result.zoom} · jurisdiction ${result.jurisdiction_id || 'none'} · ${Object.values(result.suppressed_counts || {}).reduce((a,b) => a + Number(b || 0), 0)} policy-filtered`;
      }
      drawCivicProjection();
    } catch (error) {
      drawCivicEmpty(`Map projection failed: ${error.message}`);
    }
  }

  function populateJurisdictions(items, active) {
    const select = $('civic-jurisdiction');
    if (!select) return;
    const previous = select.value;
    select.innerHTML = items.map(item => `<option value="${escape(item.jurisdiction_id)}">${escape(item.label || item.jurisdiction_id)}</option>`).join('') || '<option value="">Active session jurisdiction</option>';
    select.value = previous || active || '';
  }

  function renderLayerChips(types) {
    const host = $('civic-layer-chips');
    if (host) host.innerHTML = types.map(type => `<span>${escape(type)}</span>`).join('');
  }

  function renderAccessibleMapData(rows) {
    const host = $('civic-map-data');
    if (host) host.textContent = JSON.stringify(rows, null, 2);
  }

  function resizeCivicCanvas() {
    const canvas = $('civic-map-canvas');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const context = canvas.getContext('2d');
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    drawCivicProjection();
  }

  function coordinatePairs(value, output = []) {
    if (!Array.isArray(value)) return output;
    if (value.length >= 2 && typeof value[0] === 'number' && typeof value[1] === 'number') {
      output.push([value[0], value[1]]);
      return output;
    }
    value.forEach(child => coordinatePairs(child, output));
    return output;
  }

  function mapBounds(features) {
    const pairs = [];
    features.forEach(feature => coordinatePairs(feature.geometry?.coordinates, pairs));
    if (!pairs.length) return null;
    const xs = pairs.map(pair => pair[0]);
    const ys = pairs.map(pair => pair[1]);
    return { west: Math.min(...xs), east: Math.max(...xs), south: Math.min(...ys), north: Math.max(...ys) };
  }

  function drawCivicEmpty(message) {
    const canvas = $('civic-map-canvas');
    if (!canvas) return;
    const context = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    context.clearRect(0, 0, rect.width, rect.height);
    context.fillStyle = 'rgba(148,163,184,.75)';
    context.font = '14px system-ui';
    context.textAlign = 'center';
    context.fillText(message, rect.width / 2, rect.height / 2);
  }

  function drawCivicProjection() {
    const canvas = $('civic-map-canvas');
    if (!canvas) return;
    const context = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    context.clearRect(0, 0, rect.width, rect.height);
    const features = civicProjectedFeatures || [];
    if (!features.length) {
      drawCivicEmpty(civicProjection ? 'No data is visible at this jurisdiction and zoom.' : 'No Civic map projection loaded.');
      return;
    }
    const bounds = mapBounds(features);
    if (!bounds) return;
    const padding = 90;
    const spanX = Math.max(.00001, bounds.east - bounds.west);
    const spanY = Math.max(.00001, bounds.north - bounds.south);
    const project = ([lon, lat]) => [
      padding + ((lon - bounds.west) / spanX) * Math.max(1, rect.width - padding * 2),
      rect.height - padding - ((lat - bounds.south) / spanY) * Math.max(1, rect.height - padding * 2),
    ];
    civicHitRegions = [];

    context.strokeStyle = 'rgba(34,211,238,.08)';
    context.lineWidth = 1;
    for (let x = 0; x < rect.width; x += 48) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, rect.height); context.stroke(); }
    for (let y = 0; y < rect.height; y += 48) { context.beginPath(); context.moveTo(0, y); context.lineTo(rect.width, y); context.stroke(); }

    features.filter(feature => /Polygon/.test(feature.geometry?.type || '')).forEach(feature => {
      const rings = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates : feature.geometry.coordinates.flat();
      rings.forEach(ring => {
        context.beginPath();
        ring.forEach((coord, index) => {
          const [x, y] = project(coord);
          index ? context.lineTo(x, y) : context.moveTo(x, y);
        });
        context.closePath();
        context.fillStyle = 'rgba(34,211,238,.08)';
        context.strokeStyle = 'rgba(34,211,238,.62)';
        context.lineWidth = 2;
        context.fill(); context.stroke();
      });
    });

    features.filter(feature => feature.geometry?.type === 'Point').forEach(feature => {
      const [x, y] = project(feature.geometry.coordinates);
      const type = feature.properties?.type || 'feature';
      const radius = type === 'candidate' || type === 'scenario' ? 8 : 6;
      context.beginPath(); context.arc(x, y, radius, 0, Math.PI * 2);
      context.fillStyle = type === 'transit' ? '#a78bfa' : type === 'candidate' ? '#fbbf24' : '#22d3ee';
      context.shadowColor = context.fillStyle; context.shadowBlur = 16; context.fill(); context.shadowBlur = 0;
      context.fillStyle = '#e6fbff'; context.font = '11px system-ui'; context.textAlign = 'left';
      context.fillText(feature.properties?.name || type, x + 11, y + 4);
      civicHitRegions.push({ x, y, radius: 15, feature });
    });
  }

  function inspectCivicFeature(feature) {
    const props = feature?.properties || {};
    const host = $('civic-feature-inspector');
    if (!host) return;
    host.innerHTML = `<p class="eyebrow">Selected feature</p><h3>${escape(props.name || 'Unnamed feature')}</h3>
      <div class="evidence-list">
        <div class="evidence-item">Type: ${escape(props.type || 'feature')}</div>
        <div class="evidence-item">Truth: ${escape(props.truth_class || 'UNKNOWN')}</div>
        <div class="evidence-item">Jurisdiction: ${escape(props.jurisdiction_id || '')}</div>
        <div class="evidence-item">Privacy: ${escape(props.privacy_class || '')}</div>
        <div class="evidence-item">Location: ${escape(props.location_class || '')}</div>
        <div class="evidence-item">Source: ${escape(props.source_ref || '')}</div>
      </div>`;
  }

  $('civic-map-canvas')?.addEventListener('click', event => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left, y = event.clientY - rect.top;
    const hit = civicHitRegions.find(item => Math.hypot(item.x - x, item.y - y) <= item.radius);
    if (hit) inspectCivicFeature(hit.feature);
  });
  $('civic-map-zoom')?.addEventListener('input', refreshCivicProjection);
  $('civic-jurisdiction')?.addEventListener('change', refreshCivicProjection);
  $('civic-zoom-in')?.addEventListener('click', () => { $('civic-map-zoom').value = Math.min(18, civicZoom() + 1); refreshCivicProjection(); });
  $('civic-zoom-out')?.addEventListener('click', () => { $('civic-map-zoom').value = Math.max(3, civicZoom() - 1); refreshCivicProjection(); });
  $('civic-fit-map')?.addEventListener('click', refreshCivicProjection);

  const sessionInfo = $('civic-session-info');
  if (sessionInfo) {
    new MutationObserver(() => {
      if (currentCivicSessionId()) setTimeout(refreshCivicProjection, 50);
    }).observe(sessionInfo, { childList: true, characterData: true, subtree: true });
  }

  document.querySelector('.spatial-lens')?.addEventListener('toggle', event => {
    if (event.currentTarget.open && typeof window.resizeCanvas === 'function') {
      window.resizeCanvas();
    }
  });

  window.addEventListener('resize', resizeCivicCanvas);
  loadWorkflow();
  loadTools();
  resizeCivicCanvas();
})();
