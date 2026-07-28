'use strict';

(() => {
  const S = window.Showcase;
  if (!S) return;

  const state = {
    captureId: '',
    packet: null,
    active: false,
    eventCount: 0,
    listeners: [],
    expiryTimer: null,
  };

  const $ = id => document.getElementById(id);
  const lines = value => String(value || '').split('\n').map(item => item.trim()).filter(Boolean);
  const output = value => {
    const node = $('foundry-output');
    if (node) node.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  };
  const appendEvent = (label, detail = '') => {
    const node = $('foundry-events');
    if (!node) return;
    const row = document.createElement('div');
    row.className = 'foundry-event';
    row.innerHTML = `<strong>${S.esc(label)}</strong><span>${S.esc(detail)}</span>`;
    node.prepend(row);
  };

  const request = async (path, body) => {
    const result = await S.api(path, body);
    if (!result.ok) throw new Error(result.error || `Live Repair request failed (${result.http_status})`);
    return result;
  };

  const identity = () => {
    const raw = $('foundry-identity')?.value || '';
    return JSON.parse(raw);
  };

  const resetControls = () => {
    if ($('foundry-mark')) $('foundry-mark').disabled = true;
    if ($('foundry-finalize')) $('foundry-finalize').disabled = true;
    if ($('foundry-start')) $('foundry-start').disabled = false;
  };

  const sendEvent = async (eventType, payload) => {
    if (!state.active || !state.captureId) return;
    const result = await request(
      `/api/showcase/live-repair/capture/${encodeURIComponent(state.captureId)}/event/v1`,
      {event_type: eventType, payload},
    );
    state.eventCount += 1;
    appendEvent(eventType, `sequence ${result.event?.sequence ?? state.eventCount - 1}`);
  };

  const addBoundedListeners = () => {
    const onError = event => {
      void sendEvent('BROWSER_ERROR', {
        message: String(event.message || ''),
        filename: String(event.filename || ''),
        line: Number(event.lineno || 0),
        column: Number(event.colno || 0),
      }).catch(error => output(error.message));
    };
    const onRejection = event => {
      void sendEvent('UNHANDLED_REJECTION', {reason: String(event.reason || '')})
        .catch(error => output(error.message));
    };
    const onClick = event => {
      const target = event.target?.closest?.('button, input, textarea, select');
      if (!target || !target.closest('#foundry-view')) return;
      void sendEvent('FOUNDRY_UI_ACTION', {
        element_id: String(target.id || ''),
        element_type: String(target.tagName || ''),
      }).catch(error => output(error.message));
    };
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    document.addEventListener('click', onClick);
    state.listeners = [
      [window, 'error', onError],
      [window, 'unhandledrejection', onRejection],
      [document, 'click', onClick],
    ];
  };

  const dissolveListeners = () => {
    state.listeners.forEach(([target, type, handler]) => target.removeEventListener(type, handler));
    state.listeners = [];
    if (state.expiryTimer !== null) window.clearTimeout(state.expiryTimer);
    state.expiryTimer = null;
    state.active = false;
  };

  const expireBoundedCapture = () => {
    if (!state.active) return;
    void sendEvent('CAPTURE_WINDOW_EXPIRED', {})
      .catch(() => {})
      .finally(() => {
        dissolveListeners();
        resetControls();
        appendEvent('CAPTURE_DISSOLVED', 'bounded retention window expired');
        output({ok: false, status: 'CAPTURE_EXPIRED_AND_DISSOLVED', fail_closed: true});
      });
  };

  const start = async () => {
    if (state.active) throw new Error('A bounded capture is already active.');
    const contract = {
      identity: identity(),
      release_id: 'showcase-current-release',
      environment_id: 'showcase-loopback-browser',
      capture_authorized: true,
      max_events: 256,
      retention_seconds: 120,
    };
    const result = await request('/api/showcase/live-repair/capture/start', contract);
    state.captureId = result.capture_id;
    state.active = true;
    state.eventCount = 0;
    state.packet = null;
    addBoundedListeners();
    const retentionMilliseconds = Math.max(1, Number(result.retention_seconds || contract.retention_seconds)) * 1000;
    state.expiryTimer = window.setTimeout(expireBoundedCapture, retentionMilliseconds + 50);
    $('foundry-mark').disabled = false;
    $('foundry-finalize').disabled = false;
    $('foundry-start').disabled = true;
    appendEvent('CAPTURE_STARTED', state.captureId);
    output(result);
  };

  const mark = async () => {
    const marker = window.prompt('What exactly went wrong?');
    if (!marker) return;
    const result = await request(
      `/api/showcase/live-repair/capture/${encodeURIComponent(state.captureId)}/mark/v1`,
      {marker, payload: {voice_transcript: marker}},
    );
    appendEvent('INCIDENT_MARKER', marker);
    output(result);
  };

  const finalize = async () => {
    const currentIdentity = identity();
    const result = await request(
      `/api/showcase/live-repair/capture/${encodeURIComponent(state.captureId)}/finalize/v1`,
      {
        current_identity: currentIdentity,
        expected_positive: lines($('foundry-positive')?.value),
        expected_negative: lines($('foundry-negative')?.value),
        preservation_claims: lines($('foundry-preservation')?.value),
        required_assets: [],
        arena_id: 'construction',
        objective: 'Compile an exact privacy-safe deterministic field replay',
      },
    );
    state.packet = result.packet;
    dissolveListeners();
    resetControls();
    appendEvent('CAPTURE_DISSOLVED', result.packet?.packet_id || '');
    const projection = await projectCurrentIncident(currentIdentity);
    output({...result, projection});
  };

  const renderProjection = projection => {
    const set = (id, value) => {
      const node = $(id);
      if (!node) return;
      const rows = Array.isArray(value) ? value : [value];
      node.innerHTML = rows.filter(item => item !== undefined && item !== null && item !== '')
        .map(item => `<div class="foundry-chip">${S.esc(typeof item === 'string' ? item : JSON.stringify(item))}</div>`)
        .join('') || '<span class="muted">No retained evidence yet.</span>';
    };
    set('foundry-projection-intent', projection.confirmed_intent?.positive || projection.confirmed_intent || []);
    set('foundry-projection-negative', projection.negative_intent || []);
    set('foundry-projection-guardrails', projection.guardrails || []);
    set('foundry-projection-runtime', [
      `release: ${projection.live_runtime?.release_id || '—'}`,
      `environment: ${projection.live_runtime?.environment_id || '—'}`,
      `events: ${projection.live_runtime?.event_count ?? 0}/${projection.live_runtime?.total_event_count ?? 0}`,
    ]);
    set('foundry-projection-failures', projection.failures || []);
    set('foundry-projection-proof', [
      `incident: ${projection.proof?.incident_packet_digest || '—'}`,
      `projection: ${projection.projection_digest || '—'}`,
      `P0: ${projection.proof?.p0 ? 'retained' : 'pending'}`,
      `P1: ${projection.proof?.p1 ? 'retained' : 'pending'}`,
    ]);
    set('foundry-projection-disposition', projection.human_community_disposition || 'PENDING');
    set('foundry-projection-drilldown', [
      ...(projection.source_drilldown || []),
      ...(projection.receipt_drilldown || []),
    ]);
  };

  const projectCurrentIncident = async currentIdentity => {
    if (!state.packet) return null;
    const result = await request('/api/showcase/live-repair/projection', {
      packet_id: state.packet.packet_id,
      current_identity: currentIdentity,
      intent: {positive: lines($('foundry-positive')?.value)},
      plan: {status: 'INCIDENT_REPLAY_READY', next_gate: 'RUNTIME_REPLAY_AND_BOUNDED_REPAIR'},
      code_targets: [],
      attempt_ids: [],
      source_drilldown: [],
      receipt_drilldown: [
        {kind: 'incident_replay', id: state.packet.packet_id, digest: state.packet.packet_digest},
        {kind: 'confirmation', id: currentIdentity.confirmation_digest},
      ],
    });
    renderProjection(result.projection);
    return result.projection;
  };

  const originalActivate = S.activateTab;
  S.activateTab = name => {
    originalActivate(name);
    $('foundry-view')?.classList.toggle('is-active', name === 'foundry');
  };

  document.querySelectorAll('.tab').forEach(tab => {
    if (tab.dataset.tab === 'foundry') {
      tab.addEventListener('click', () => S.activateTab('foundry'));
    }
  });

  $('foundry-start')?.addEventListener('click', () => start().catch(error => output(error.message)));
  $('foundry-mark')?.addEventListener('click', () => mark().catch(error => output(error.message)));
  $('foundry-finalize')?.addEventListener('click', () => finalize().catch(error => {
    dissolveListeners();
    resetControls();
    output(error.message);
  }));

  window.addEventListener('beforeunload', dissolveListeners, {once: true});
  const template = {
    intent_digest: '<40-64 hex>',
    confirmation_digest: '<intent-confirmation_* canonical receipt id>',
    semantic_ledger_digest: '<40-64 hex>',
    guardrail_set_digest: '<40-64 hex>',
    intent_revision_id: '<current revision id or canonical no-drift status>',
    repository_head: '<40 hex commit>',
    source_tree_digest: '<40 hex tree>',
    runtime_profile_digest: '<64 hex sha256>',
    verifier_id: '<independent verifier id>',
    verifier_source_digest: '<64 hex sha256>',
  };
  if ($('foundry-identity')) $('foundry-identity').value = JSON.stringify(template, null, 2);
  if ($('foundry-positive')) $('foundry-positive').value = 'The selected Construction storey and entity remain stable.';
  if ($('foundry-negative')) $('foundry-negative').value = 'Do not select hidden storeys.\nDo not hide asset or digest failures.';
  if ($('foundry-preservation')) $('foundry-preservation').value = 'Canonical Construction state and source geometry remain unchanged.';
})();
