'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;
  const canvas = $('topology-canvas');
  if (!canvas) return;
  canvas.tabIndex = 0;
  const context = canvas.getContext('2d');

  let packet = null;
  let graph = {nodes: [], links: []};
  let selectedNodeId = '';
  let projected = [];
  let yaw = 0.58;
  let pitch = -0.34;
  let zoom = 1.85;
  let dragging = false;
  let dragOrigin = null;
  let lastPointer = null;

  const typeLabels = {
    file: 'Files',
    class: 'Classes',
    function: 'Functions',
    method: 'Methods',
    test: 'Tests',
    router: 'Routers',
    context: 'Context',
    research: 'Research',
    verifier: 'Verifiers',
  };

  function taskButton(task) {
    const slots = ['DIR', 'ASP', 'CLASS', 'SUBJ', 'VOICE', 'STEM']
      .map(key => `${key}=${task.intent_slots?.[key] || '—'}`).join(' · ');
    return `<button class="spatial-task" data-spatial-task="${esc(task.task_id)}">
      <span class="spatial-task-state">bounded topology</span>
      <strong>${esc(task.title)}</strong>
      <small>${esc(task.summary)}</small>
      <code>${esc(slots)}</code>
    </button>`;
  }

  async function loadTasks() {
    const result = await S.api('/api/showcase/coding-tasks');
    const tasks = result.tasks || [];
    S.spatialTasks = tasks;
    $('spatial-task-list').innerHTML = tasks.map(taskButton).join('')
      || '<p class="muted">No spatial tasks are available.</p>';
    $('spatial-task-list').querySelectorAll('[data-spatial-task]').forEach(button => {
      button.addEventListener('click', () => loadTask(button.dataset.spatialTask, 1));
    });
  }

  async function loadTask(taskId, depth = 1) {
    setStatus('Loading bounded CODEMAP workspace…');
    const result = await S.api(`/api/showcase/topology/tasks/${encodeURIComponent(taskId)}?depth=${depth}`);
    if (!result.ok) {
      setStatus(result.error || 'Topology workspace unavailable.');
      return;
    }
    S.spatialTaskId = taskId;
    applyPacket(result);
    document.querySelectorAll('[data-spatial-task]').forEach(button => {
      button.classList.toggle('is-active', button.dataset.spatialTask === taskId);
    });
  }

  async function selectNode(nodeId, depth = 1) {
    if (!nodeId) return;
    setStatus('Expanding selected exact topology node…');
    const result = await S.api('/api/showcase/topology/select', {
      node_ids: [nodeId],
      depth,
      task_id: S.spatialTaskId || '',
    });
    if (!result.ok) {
      setStatus(result.error || 'Node projection unavailable.');
      return;
    }
    applyPacket(result, nodeId);
  }

  function applyPacket(result, preferredNodeId = '') {
    packet = result;
    graph = result.workspace || {nodes: [], links: []};
    selectedNodeId = preferredNodeId
      || graph.selected_node_ids?.[0]
      || graph.nodes?.[0]?.id
      || '';
    renderTask(result.task);
    renderLegend();
    renderInspector();
    resize();
    const truncation = graph.truncated ? ' · bounded result truncated' : '';
    setStatus(`${graph.returned_node_count || graph.nodes?.length || 0} nodes · ${graph.returned_link_count || graph.links?.length || 0} links · depth ${graph.depth ?? 1}${truncation}`);
  }

  function renderTask(task) {
    const host = $('spatial-task-detail');
    if (!task) {
      host.innerHTML = '<p class="muted">Choose a task to project its exact repository neighborhood.</p>';
      return;
    }
    host.innerHTML = `<p class="eyebrow">Active investigation</p>
      <h3>${esc(task.title)}</h3>
      <p>${esc(task.summary)}</p>
      <p class="spatial-cue">${esc(task.presenter_cue || '')}</p>
      <details><summary>Acceptance criteria and prohibited actions</summary>
        <ul>${(task.acceptance_criteria || []).map(item => `<li>${esc(item)}</li>`).join('')}</ul>
        <p class="muted">Prohibited: ${esc((task.prohibited_actions || []).join(' · '))}</p>
      </details>`;
  }

  function renderLegend() {
    const types = {};
    (graph.nodes || []).forEach(node => {
      const key = node.node_type || 'file';
      if (!types[key]) types[key] = node.color || '#94a3b8';
    });
    $('topology-legend').innerHTML = Object.keys(types).sort().map(key =>
      `<span><i style="background:${esc(types[key])}"></i>${esc(typeLabels[key] || key)}</span>`
    ).join('');
  }

  function renderInspector() {
    const node = (graph.nodes || []).find(item => item.id === selectedNodeId);
    if (!node) {
      $('topology-inspector').innerHTML = '<p class="muted">Select a node to inspect exact repository information.</p>';
      return;
    }
    const dependencies = (graph.dependencies || []).slice(0, 8).map(item => item.id || item.label).filter(Boolean);
    const callers = (graph.callers || []).slice(0, 8).map(item => item.id || item.label).filter(Boolean);
    const tests = (graph.tests || []).slice(0, 8).map(item => typeof item === 'string' ? item : (item.id || item.file_path)).filter(Boolean);
    const faults = (graph.candidate_faults || []).filter(item => item.node_id === node.id).slice(0, 4);
    $('topology-inspector').innerHTML = `<p class="eyebrow">Selected topology node</p>
      <h3>${esc(node.label || node.id)}</h3>
      <div class="topology-facts">
        <span><b>Path</b>${esc(node.file_path || '—')}</span>
        <span><b>Symbol</b>${esc(node.symbol || '—')}</span>
        <span><b>Type</b>${esc(node.node_type || '—')}</span>
        <span><b>Lines</b>${esc((node.line_range || []).join('–') || '—')}</span>
        <span><b>Truth</b>${esc(node.projection_truth || 'EXACT_TOPOLOGY')}</span>
        <span><b>Tokens</b>${esc(node.tokens_est || 0)}</span>
      </div>
      <div class="topology-neighbours">
        <p><b>Dependencies:</b> ${esc(dependencies.join(' · ') || 'none in bounded slice')}</p>
        <p><b>Callers:</b> ${esc(callers.join(' · ') || 'none in bounded slice')}</p>
        <p><b>Tests:</b> ${esc(tests.join(' · ') || 'no connected test in bounded slice')}</p>
        ${faults.length ? `<p class="topology-risk"><b>Candidate risks:</b> ${esc(faults.map(item => item.message || item.kind).join(' · '))}</p>` : ''}
      </div>
      <p class="muted">The visual node has no patch authority. Exact source spans and hashes remain authoritative.</p>`;
  }

  function setStatus(text) {
    $('topology-status').textContent = text;
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }

  function draw() {
    const rect = canvas.getBoundingClientRect();
    context.clearRect(0, 0, rect.width, rect.height);
    context.fillStyle = '#050d11';
    context.fillRect(0, 0, rect.width, rect.height);
    context.strokeStyle = 'rgba(45,212,191,.07)';
    context.lineWidth = 1;
    for (let x = 0; x < rect.width; x += 52) {
      context.beginPath(); context.moveTo(x, 0); context.lineTo(x, rect.height); context.stroke();
    }
    for (let y = 0; y < rect.height; y += 52) {
      context.beginPath(); context.moveTo(0, y); context.lineTo(rect.width, y); context.stroke();
    }
    if (!(graph.nodes || []).length) {
      context.fillStyle = '#92aab3';
      context.font = '14px system-ui';
      context.textAlign = 'center';
      context.fillText('Choose a starter task to build a bounded topology workspace.', rect.width / 2, rect.height / 2);
      return;
    }

    const selectedSet = new Set(graph.selected_node_ids || []);
    projected = graph.nodes.map(node => project(node, rect.width, rect.height));
    const byId = new Map(projected.map(item => [item.node.id, item]));

    (graph.links || []).forEach(link => {
      const source = byId.get(link.source);
      const target = byId.get(link.target);
      if (!source || !target) return;
      const touchesSelection = selectedSet.has(link.source) || selectedSet.has(link.target);
      context.globalAlpha = link.status === 'missing' ? 0.95 : (touchesSelection ? 0.78 : 0.3);
      context.strokeStyle = link.status === 'missing' ? '#fb7185' : (touchesSelection ? '#2dd4bf' : '#405662');
      context.lineWidth = link.status === 'missing' ? 2.4 : (touchesSelection ? 1.8 : 0.9);
      context.beginPath();
      context.moveTo(source.x, source.y);
      context.lineTo(target.x, target.y);
      context.stroke();
    });

    projected.sort((a, b) => a.depth - b.depth).forEach(item => {
      const node = item.node;
      const selected = node.id === selectedNodeId;
      const seed = selectedSet.has(node.id);
      const radius = selected ? 9.5 : (seed ? 7 : 5);
      context.globalAlpha = selected ? 1 : (seed ? 0.95 : 0.72);
      context.fillStyle = selected ? '#ffffff' : (node.color || '#94a3b8');
      context.strokeStyle = selected ? '#2dd4bf' : (node.projection_truth === 'CODEMAP_PROJECTED' ? '#a78bfa' : '#071014');
      context.lineWidth = selected ? 3 : 1.3;
      context.beginPath();
      context.arc(item.x, item.y, radius * item.scale, 0, Math.PI * 2);
      context.fill();
      context.stroke();
      if (selected || seed || item.scale > 1.15) {
        context.globalAlpha = 0.96;
        context.fillStyle = '#e7f7fa';
        context.font = '11px ui-monospace, SFMono-Regular, Consolas, monospace';
        context.textAlign = 'left';
        context.fillText(node.label || node.id, item.x + 10, item.y - 9);
      }
    });
    context.globalAlpha = 1;
  }

  function project(node, width, height) {
    const x0 = Number(node.x || 0);
    const y0 = Number(node.y || 0);
    const z0 = Number(node.z || 0);
    const cy = Math.cos(yaw), sy = Math.sin(yaw);
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    const x1 = x0 * cy - z0 * sy;
    const z1 = x0 * sy + z0 * cy;
    const y1 = y0 * cp - z1 * sp;
    const z2 = y0 * sp + z1 * cp;
    const perspective = 620 / Math.max(180, 620 + z2);
    const scale = Math.max(0.35, Math.min(1.9, perspective * zoom));
    return {node, x: width / 2 + x1 * scale, y: height / 2 + y1 * scale, depth: z2, scale};
  }

  function hitTest(x, y) {
    let best = null;
    let bestDistance = Infinity;
    projected.forEach(item => {
      const distance = Math.hypot(item.x - x, item.y - y);
      if (distance < bestDistance && distance < 18) {
        best = item.node;
        bestDistance = distance;
      }
    });
    return best;
  }

  function clearDragState() {
    dragging = false;
    lastPointer = null;
    dragOrigin = null;
  }

  canvas.addEventListener('pointerdown', event => {
    dragging = true;
    dragOrigin = {x: event.clientX, y: event.clientY};
    lastPointer = {...dragOrigin};
    canvas.setPointerCapture?.(event.pointerId);
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging || !lastPointer) return;
    yaw += (event.clientX - lastPointer.x) * 0.006;
    pitch += (event.clientY - lastPointer.y) * 0.006;
    pitch = Math.max(-1.25, Math.min(1.25, pitch));
    lastPointer = {x: event.clientX, y: event.clientY};
    draw();
  });
  canvas.addEventListener('pointerup', event => {
    const moved = dragOrigin ? Math.hypot(event.clientX - dragOrigin.x, event.clientY - dragOrigin.y) : 0;
    clearDragState();
    const rect = canvas.getBoundingClientRect();
    const node = moved < 4 ? hitTest(event.clientX - rect.left, event.clientY - rect.top) : null;
    if (node) selectNode(node.id, 1);
  });
  canvas.addEventListener('pointercancel', () => {
    clearDragState();
  });
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    zoom = Math.max(0.55, Math.min(5.5, zoom + (event.deltaY < 0 ? 0.14 : -0.14)));
    draw();
  }, {passive: false});
  canvas.addEventListener('keydown', event => {
    const nodes = graph.nodes || [];
    if (!nodes.length) return;
    let currentIndex = nodes.findIndex(node => node.id === selectedNodeId);
    if (currentIndex < 0) currentIndex = 0;
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault();
      const nextIndex = (currentIndex + 1) % nodes.length;
      selectedNodeId = nodes[nextIndex].id;
      selectNode(selectedNodeId, 1);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault();
      const prevIndex = (currentIndex - 1 + nodes.length) % nodes.length;
      selectedNodeId = nodes[prevIndex].id;
      selectNode(selectedNodeId, 1);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (selectedNodeId) {
        selectNode(selectedNodeId, 1);
      }
    }
  });

  $('topology-depth-1').addEventListener('click', () => selectNode(selectedNodeId, 1));
  $('topology-depth-2').addEventListener('click', () => selectNode(selectedNodeId, 2));
  $('topology-fit').addEventListener('click', () => {
    yaw = 0.58; pitch = -0.34; zoom = 1.85; draw();
  });
  $('investigate-issue').addEventListener('click', () => {
    window.setTimeout(() => loadTask('civic_map_overlay', 1), 0);
  });
  document.querySelectorAll('.tab').forEach(button => {
    button.addEventListener('click', () => {
      if (button.dataset.tab === 'human') window.setTimeout(resize, 30);
    });
  });
  window.addEventListener('resize', resize);

  S.loadTopologyTask = loadTask;
  S.resizeTopology = resize;
  loadTasks().catch(error => setStatus(`Task registry unavailable: ${error.message}`));
  resize();
})();
