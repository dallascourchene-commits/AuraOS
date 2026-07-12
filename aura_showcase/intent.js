'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;
  const canvas = $('learning-topology-canvas');
  if (!canvas) return;
  const context = canvas.getContext('2d');
  const STAGE_TITLES = [
    '1. Give Aura bulk intention',
    '2. Address words in the 4,096-primitive codebook',
    '3. Extract local routing and LEXC tags',
    '4. Bind the canonical six-slot packet',
    '5. Apply the machine FST hard gate',
    '6. Prepare the bounded worker handoff',
  ];
  const NEXT_LABELS = [
    'Compile the intention first',
    'Show routing tags',
    'Show six-slot packet',
    'Show FST hard gate',
    'Show bounded handoff',
    'Worker handoff ready',
  ];

  let maxStage = 0;
  let graph = {nodes: [], links: []};
  let selectedNodeId = '';
  let projected = [];
  let yaw = 0.52;
  let pitch = -0.28;
  let zoom = 1.8;
  let dragging = false;
  let dragOrigin = null;
  let lastPointer = null;

  function metric(label, value) {
    return `<article><strong>${esc(value)}</strong><span>${esc(label)}</span></article>`;
  }

  function applyStage(rawStage) {
    const stage = Math.max(0, Math.min(5, Number(rawStage) || 0));
    if (stage > maxStage) return;
    if (S.applyStage) {
      S.applyStage(stage);
    } else {
      S.intentStage = stage;
      document.querySelectorAll('[data-learning-panel]').forEach(panel => {
        panel.classList.toggle('is-active', Number(panel.dataset.learningPanel) === stage);
      });
      document.querySelectorAll('[data-learning-stage]').forEach(button => {
        const index = Number(button.dataset.learningStage);
        button.disabled = index > maxStage;
        button.classList.toggle('is-active', index === stage);
        button.classList.toggle('is-complete', index < stage && index <= maxStage);
      });
      $('learning-stage-title').textContent = STAGE_TITLES[stage];
      $('learning-back').disabled = stage === 0;
      $('learning-next').disabled = !S.intentTrace || stage === 5;
      $('learning-next').textContent = NEXT_LABELS[stage];
      if (stage === 5) setTimeout(resizeTopology, 20);
    }
  }

  async function compileIntent() {
    const text = String($('bulk-intent-input').value || '').trim();
    if (!text) {
      $('learning-truth-notice').textContent = 'Enter a bulk intention before compiling.';
      return;
    }
    const button = $('learning-compile');
    button.disabled = true;
    button.textContent = 'Compiling locally…';
    $('learning-model-count').textContent = 'model calls: 0';
    try {
      const result = await S.api('/api/showcase/intent/compile', {
        text,
        include_grounding: true,
        include_topology: true,
        depth: 1,
      });
      if (!result.ok) throw new Error(result.error || 'Intent compilation failed');
      S.intentTrace = result;
      maxStage = 1;
      renderTrace(result);
      if (S.unlockLearningWorkspace) {
        S.unlockLearningWorkspace(result);
      } else {
        applyStage(1);
      }
    } catch (error) {
      S.intentTrace = null;
      maxStage = 0;
      $('learning-truth-notice').textContent = error.message;
      applyStage(0);
    } finally {
      button.disabled = false;
      button.textContent = 'Compile intention without an LLM';
    }
  }

  function resetDemo() {
    S.intentTrace = null;
    maxStage = 0;
    graph = {nodes: [], links: []};
    selectedNodeId = '';
    clearOutputs();
    applyStage(0);
    drawTopology();
    $('bulk-intent-input').focus();
  }

  function clearOutputs() {
    [
      'lexicon-metrics', 'lexicon-token-trace', 'intent-tag-groups', 'compressed-intent',
      'lexc-trace', 'compiled-six-slots', 'vsa-binding', 'machine-route-summary',
      'machine-input-symbols', 'machine-output-symbols', 'machine-jspace', 'handoff-metrics',
      'intent-localization', 'intent-handoff-preview', 'learning-admitted', 'learning-blocked',
    ].forEach(id => { const node = $(id); if (node) node.innerHTML = ''; });
    $('learning-exact-trace').textContent = '{}';
    $('learning-topology-status').textContent = 'not compiled';
    $('learning-topology-inspector').innerHTML = '<span class="muted">Compile the intention to project exact CODEMAP nodes.</span>';
    $('learning-model-count').textContent = 'model calls: 0';
  }

  function renderTrace(trace) {
    $('learning-model-count').textContent = `model calls: ${trace.model_calls_made ?? 0}`;
    $('learning-truth-notice').textContent = trace.truth_notice || '';
    renderLexicon(trace.lexical_codebook || {});
    renderTags(trace);
    renderSlots(trace.six_slot_packet || {});
    renderMachineRoute(trace);
    renderHandoff(trace);
    renderGuardrails(trace.guardrails || {});
    applyTopology(trace.topology_packet || {});
    const exact = {...trace};
    if (exact.topology_packet?.workspace) {
      exact.topology_packet = {
        ok: exact.topology_packet.ok,
        task: exact.topology_packet.task,
        bounds: exact.topology_packet.bounds,
        truth_policy: exact.topology_packet.truth_policy,
        workspace: {
          returned_node_count: exact.topology_packet.workspace.returned_node_count,
          returned_link_count: exact.topology_packet.workspace.returned_link_count,
          selected_node_ids: exact.topology_packet.workspace.selected_node_ids,
          truncated: exact.topology_packet.workspace.truncated,
        },
      };
    }
    $('learning-exact-trace').textContent = JSON.stringify(exact, null, 2);
  }

  function renderLexicon(lexical) {
    $('lexicon-metrics').innerHTML = [
      metric('stored primitives', Number(lexical.primitive_count || 0).toLocaleString()),
      metric('address width', `${lexical.address_width_bits || 0} bits`),
      metric('recognized unique words', lexical.recognized_unique_tokens || 0),
      metric('lexical coverage', `${Math.round(Number(lexical.coverage_ratio || 0) * 100)}%`),
    ].join('');
    $('lexicon-token-trace').innerHTML = (lexical.tokens || []).map(item =>
      `<span class="token-chip" data-known="${Boolean(item.known)}"><b>${esc(item.token)}</b><small>${esc(item.address)} · ${esc(item.source)}</small></span>`
    ).join('') || '<p class="muted">No lexical tokens were emitted.</p>';
  }

  function renderTags(trace) {
    const groups = trace.tag_trace || {};
    const ordered = ['operation', 'domain', 'target', 'output'];
    $('intent-tag-groups').innerHTML = ordered.map(group => {
      const records = groups[group] || [];
      return `<section class="intent-tag-group"><h3>${esc(group)}</h3>${records.length
        ? records.map(item => `<div class="intent-tag-record"><strong>${esc(item.tag)}</strong><small>matched: ${esc((item.matched_text || []).join(' · '))}</small></div>`).join('')
        : '<p class="muted">default route tag applied</p>'}</section>`;
    }).join('');
    const compressed = String(trace.compressed_objective || '');
    const tags = compressed.match(/\[[^\]]+\]/g) || [];
    $('compressed-intent').innerHTML = tags.map(tag => `<span class="compiled-tag">${esc(tag)}</span>`).join('');
    renderLexc(trace.lexc_trace || {});
  }

  function renderLexc(lexc) {
    if (!lexc.available) {
      $('lexc-trace').innerHTML = `<p class="muted">LEXC trace unavailable: ${esc(lexc.reason || 'unknown')}</p>`;
      return;
    }
    const candidate = lexc.candidate_route;
    const route = candidate?.slots
      ? `<div class="lexc-route">${Object.entries(candidate.slots).map(([slot, symbol]) => `<span>${esc(slot)}=${esc(symbol)}</span>`).join('')}</div>`
      : '<p class="muted">No exact classified-intent symbol selected a complete legacy LEXC route.</p>';
    const layers = lexc.slot_layers || {};
    $('lexc-trace').innerHTML = `<p>${esc(lexc.lexicon_layer_count || 0)} lexicon layers · ${esc(lexc.arc_count || 0)} arcs · ${esc(lexc.complete_route_count_bounded || 0)} complete routes inspected</p>
      ${route}
      <p class="muted">${esc(lexc.note || '')}</p>
      <div class="lexc-layer-grid">${['DIR', 'ASP', 'CLASS', 'SUBJ', 'VOICE', 'STEM'].map(slot => `<article><strong>${slot}</strong>${(layers[slot] || []).slice(0, 6).map(item => `<code>${esc(item.symbol)} · ${esc(item.source_layer)}→${esc(item.target_layer)}</code>`).join('')}</article>`).join('')}</div>`;
  }

  function renderSlots(packet) {
    const slots = packet.slots || {};
    const derivation = packet.derivation || {};
    $('compiled-six-slots').innerHTML = ['DIR', 'ASP', 'CLASS', 'SUBJ', 'VOICE', 'STEM'].map(slot =>
      `<article class="compiled-slot"><span>${slot}</span><strong>${esc(slots[slot] || '—')}</strong><small>${esc(derivation[slot] || '')}</small></article>`
    ).join('');
    const binding = packet.vsa_binding || {};
    $('vsa-binding').innerHTML = binding.vector_digest
      ? `<strong>Deterministic VSA binding</strong><br>packet ${esc(binding.packet_digest)}<br>vector ${esc(binding.vector_digest)}<br>routing authority: ${esc(binding.routing_authority || 'advisory_after_hard_guards')}`
      : `<strong>VSA binding unavailable</strong><br>${esc(binding.reason || 'not produced')}`;
  }

  function renderMachineRoute(trace) {
    const route = trace.machine_route || {};
    $('machine-route-summary').innerHTML = [
      ['hard rule', route.rule_name],
      ['selected route', route.route],
      ['model policy', route.model],
      ['context', route.context],
      ['reason', route.reason],
      ['verifier', route.verifier_required ? 'required' : 'not required at this gate'],
    ].map(([label, value]) => `<article><span>${esc(label)}</span><strong>${esc(value || '—')}</strong></article>`).join('');
    const symbolTrace = trace.machine_symbol_trace || {};
    $('machine-input-symbols').innerHTML = renderSymbols(symbolTrace.input || []);
    $('machine-output-symbols').innerHTML = renderSymbols(symbolTrace.output || []);
    $('machine-jspace').textContent = symbolTrace.jspace_packet || '';
  }

  function renderSymbols(records) {
    return records.map(item => `<span class="symbol-chip"><b>${esc(item.symbol)}</b><small>${esc(item.meaning)}</small></span>`).join('')
      || '<p class="muted">No symbols emitted.</p>';
  }

  function renderHandoff(trace) {
    const handoff = trace.agent_handoff || {};
    const crush = trace.context_crush_summary || {};
    const topology = trace.topology_packet || {};
    const workspace = topology.workspace || {};
    $('handoff-metrics').innerHTML = [
      metric('model calls so far', trace.model_calls_made ?? 0),
      metric('raw objective tokens est.', trace.raw_objective_tokens_est || 0),
      metric('compressed tokens est.', handoff.compressed_tokens_est || trace.compressed_tokens_est || 0),
      metric('bounded topology nodes', workspace.returned_node_count || 0),
    ].join('');
    const files = trace.likely_files || [];
    const symbols = trace.likely_symbols || [];
    $('intent-localization').innerHTML = `<p><strong>Files</strong></p>${files.length ? `<ul class="result-list">${files.map(item => `<li>${esc(item)}</li>`).join('')}</ul>` : '<p class="muted">No file candidate grounded.</p>'}
      <p><strong>Symbols</strong></p>${symbols.length ? `<ul class="result-list">${symbols.map(item => `<li>${esc(item)}</li>`).join('')}</ul>` : '<p class="muted">No symbol candidate grounded.</p>'}
      <p class="muted">Context Crusher: ${esc(crush.original_tokens_est || 0)} → ${esc(crush.compressed_tokens_est || 0)} estimated tokens</p>`;
    $('intent-handoff-preview').textContent = handoff.compressed_context || 'No worker handoff prepared.';
  }

  function renderGuardrails(guardrails) {
    $('learning-admitted').innerHTML = `<h3 class="allowed">Admitted</h3>${(guardrails.admitted || []).map(item => `<div class="guardrail-item">✓ ${esc(item)}</div>`).join('')}`;
    $('learning-blocked').innerHTML = `<h3 class="denied">Blocked</h3>${(guardrails.blocked || []).map(item => `<div class="guardrail-item">✕ ${esc(item)}</div>`).join('')}`;
  }

  function applyTopology(packet) {
    if (!packet.ok || !packet.workspace) {
      graph = {nodes: [], links: []};
      selectedNodeId = '';
      $('learning-topology-status').textContent = packet.error || 'no grounded topology';
      $('learning-topology-inspector').innerHTML = '<span class="muted">The routing trace is still valid, but no bounded CODEMAP node matched this intention.</span>';
      drawTopology();
      return;
    }
    graph = packet.workspace;
    selectedNodeId = graph.selected_node_ids?.[0] || graph.nodes?.[0]?.id || '';
    $('learning-topology-status').textContent = `${graph.returned_node_count || graph.nodes?.length || 0} nodes · ${graph.returned_link_count || graph.links?.length || 0} links`;
    renderTopologyInspector();
    resizeTopology();
  }

  function resizeTopology() {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    drawTopology();
  }
  S.resizeLearningTopology = resizeTopology;

  function drawTopology() {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    context.clearRect(0, 0, rect.width, rect.height);
    context.fillStyle = '#050d11';
    context.fillRect(0, 0, rect.width, rect.height);
    context.strokeStyle = 'rgba(45,212,191,.07)';
    for (let x = 0; x < rect.width; x += 50) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, rect.height); context.stroke(); }
    for (let y = 0; y < rect.height; y += 50) { context.beginPath(); context.moveTo(0, y); context.lineTo(rect.width, y); context.stroke(); }
    if (!(graph.nodes || []).length) {
      context.fillStyle = '#92aab3';
      context.font = '13px system-ui';
      context.textAlign = 'center';
      context.fillText('Compile bulk intention to localize a bounded CODEMAP workspace.', rect.width / 2, rect.height / 2);
      return;
    }
    const seeds = new Set(graph.selected_node_ids || []);
    projected = graph.nodes.map(node => project(node, rect.width, rect.height));
    const byId = new Map(projected.map(item => [item.node.id, item]));
    (graph.links || []).forEach(link => {
      const source = byId.get(link.source), target = byId.get(link.target);
      if (!source || !target) return;
      const touches = seeds.has(link.source) || seeds.has(link.target);
      context.globalAlpha = touches ? .8 : .27;
      context.strokeStyle = link.status === 'missing' ? '#fb7185' : (touches ? '#2dd4bf' : '#405662');
      context.lineWidth = link.status === 'missing' ? 2.2 : (touches ? 1.6 : .8);
      context.beginPath(); context.moveTo(source.x, source.y); context.lineTo(target.x, target.y); context.stroke();
    });
    projected.sort((a, b) => a.depth - b.depth).forEach(item => {
      const node = item.node;
      const selected = node.id === selectedNodeId, seed = seeds.has(node.id);
      const radius = selected ? 9 : (seed ? 6.8 : 4.7);
      context.globalAlpha = selected ? 1 : (seed ? .96 : .68);
      context.fillStyle = selected ? '#ffffff' : (node.color || '#94a3b8');
      context.strokeStyle = selected ? '#2dd4bf' : '#071014';
      context.lineWidth = selected ? 3 : 1.2;
      context.beginPath(); context.arc(item.x, item.y, radius * item.scale, 0, Math.PI * 2); context.fill(); context.stroke();
      if (selected || seed) {
        context.fillStyle = '#e7f7fa'; context.globalAlpha = .96; context.font = '10px ui-monospace, monospace'; context.textAlign = 'left';
        context.fillText(node.label || node.id, item.x + 9, item.y - 8);
      }
    });
    context.globalAlpha = 1;
  }

  function project(node, width, height) {
    const x0 = Number(node.x || 0), y0 = Number(node.y || 0), z0 = Number(node.z || 0);
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const x1 = x0 * cy - z0 * sy, z1 = x0 * sy + z0 * cy;
    const y1 = y0 * cp - z1 * sp, z2 = y0 * sp + z1 * cp;
    const perspective = 620 / Math.max(180, 620 + z2);
    const scale = Math.max(.35, Math.min(1.9, perspective * zoom));
    return {node, x: width / 2 + x1 * scale, y: height / 2 + y1 * scale, depth: z2, scale};
  }

  function hitTest(x, y) {
    let best = null, distance = Infinity;
    projected.forEach(item => {
      const current = Math.hypot(item.x - x, item.y - y);
      if (current < distance && current < 18) { best = item.node; distance = current; }
    });
    return best;
  }

  function renderTopologyInspector() {
    const node = (graph.nodes || []).find(item => item.id === selectedNodeId);
    if (!node) return;
    $('learning-topology-inspector').innerHTML = `<strong>${esc(node.label || node.id)}</strong><span>${esc(node.file_path || '—')} · ${esc(node.symbol || 'global scope')} · lines ${esc((node.line_range || []).join('–') || '—')}</span><span>${esc(node.projection_truth || 'EXACT_TOPOLOGY')} · visual node has no patch authority</span>`;
  }

  canvas.addEventListener('pointerdown', event => {
    dragging = true; dragOrigin = {x: event.clientX, y: event.clientY}; lastPointer = {...dragOrigin};
    canvas.setPointerCapture?.(event.pointerId);
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging || !lastPointer) return;
    yaw += (event.clientX - lastPointer.x) * .006;
    pitch = Math.max(-1.25, Math.min(1.25, pitch + (event.clientY - lastPointer.y) * .006));
    lastPointer = {x: event.clientX, y: event.clientY};
    drawTopology();
  });
  canvas.addEventListener('pointerup', event => {
    const moved = dragOrigin ? Math.hypot(event.clientX - dragOrigin.x, event.clientY - dragOrigin.y) : 0;
    dragging = false; lastPointer = null;
    const rect = canvas.getBoundingClientRect();
    const node = moved < 4 ? hitTest(event.clientX - rect.left, event.clientY - rect.top) : null;
    if (node) { selectedNodeId = node.id; renderTopologyInspector(); drawTopology(); }
  });
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    zoom = Math.max(.55, Math.min(5.5, zoom + (event.deltaY < 0 ? .14 : -.14)));
    drawTopology();
  }, {passive: false});

  if (!S.setupLearningWorkspace) {
    $('learning-compile').addEventListener('click', compileIntent);
    $('learning-reset').addEventListener('click', resetDemo);
    $('learning-back').addEventListener('click', () => applyStage(S.intentStage - 1));
    $('learning-next').addEventListener('click', () => {
      if (!S.intentTrace || S.intentStage >= 5) return;
      maxStage = Math.max(maxStage, S.intentStage + 1);
      applyStage(S.intentStage + 1);
    });
    document.querySelectorAll('[data-learning-stage]').forEach(button => button.addEventListener('click', () => applyStage(Number(button.dataset.learningStage))));
  }
  S.compileIntent = compileIntent;
  $('bulk-intent-input').addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); compileIntent(); }
  });
  window.addEventListener('keydown', event => {
    if (event.key !== 'Enter' || event.ctrlKey || event.metaKey || event.altKey) return;
    const tag = document.activeElement?.tagName?.toLowerCase();
    if (['textarea', 'input', 'select', 'button'].includes(tag)) return;
    if (!$('learning-view').classList.contains('is-active') || !S.intentTrace || S.intentStage >= 5) return;
    event.preventDefault();
    maxStage = Math.max(maxStage, S.intentStage + 1);
    applyStage(S.intentStage + 1);
  });
  window.addEventListener('resize', resizeTopology);
  applyStage(0);
  drawTopology();
})();
