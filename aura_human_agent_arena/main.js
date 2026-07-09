const canvas = document.getElementById('arena-canvas');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('graph-status');
const commandInput = document.getElementById('command-input');
const voiceStatus = document.getElementById('voice-status');
const modeSelect = document.getElementById('mode-select');
const answerEl = document.getElementById('answer-text');
const truthEl = document.getElementById('truth-packet');
const diagnosticsEl = document.getElementById('diagnostics-panel');
const eventLogEl = document.getElementById('event-log');
const nextActionsList = document.getElementById('next-actions-list');

let topology = { nodes: [], links: [], meta: {} };
let liveState = null;
let highlightedNodeIds = [];
let hiddenNodeIds = [];
let selectedNodeIds = [];
let ghostEdges = [];
let labels = {};
let useDemo = false;
let projected = [];
let yaw = 0.58;
let pitch = -0.34;
let zoom = 1.9;
let dragging = false;
let lastPointer = null;
let pollTimer = null;

const typeNames = {
  file: 'Files',
  class: 'Classes',
  function: 'Functions',
  method: 'Methods',
  test: 'Tests',
  router: 'Routers',
  context: 'Context',
  research: 'Research',
  verifier: 'Verifier',
  capsule: 'Capsule',
  demo: 'Demo'
};

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  };
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function loadState() {
  try {
    const data = await api('/api/human-agent/state');
    topology = data.topology || { nodes: [], links: [], meta: {} };
    liveState = data.state || {};
    statusEl.textContent = `${topology.nodes.length} nodes, ${topology.links.length} links`;
    document.getElementById('truth-policy').textContent = (topology.meta && topology.meta.truth_policy)
      ? topology.meta.truth_policy
      : 'Exact topology is source of truth. Visual is advisory only.';
    renderLegend();
    updateFromState();
    draw();
  } catch (err) {
    statusEl.textContent = `failed: ${err.message}`;
  }
}

function renderLegend() {
  const legend = document.getElementById('legend');
  const types = {};
  topology.nodes.forEach(node => {
    const key = node.node_type || 'file';
    if (!types[key]) types[key] = node.color || '#94a3b8';
  });
  // Add ghost edge legend entry
  types['__ghost'] = '#c084fc';
  legend.innerHTML = Object.keys(types).sort().map(key =>
    `<span><i style="background:${types[key]}"></i>${key === '__ghost' ? 'Ghost Edges' : (typeNames[key] || key)}</span>`
  ).join('');
}

function updateFromState() {
  if (!liveState) return;
  highlightedNodeIds = liveState.visible_node_ids || [];
  hiddenNodeIds = liveState.hidden_node_ids || [];
  selectedNodeIds = liveState.selected_node_ids || [];
  ghostEdges = liveState.ghost_edges || [];
  // Update event log
  const events = liveState.event_log || [];
  if (events.length) {
    const recent = events.slice(-20);
    eventLogEl.textContent = recent.map(e =>
      `[${e.kind}] ${e.detail}`
    ).join('\n');
  }
  // Update diagnostics
  const diags = liveState.diagnostics || [];
  if (diags.length) {
    diagnosticsEl.textContent = diags.map(d =>
      `[${d.severity}] ${d.kind}: ${d.message}`
    ).join('\n');
  }
}

async function runCommand(command) {
  if (!command || !command.trim()) return;
  statusEl.textContent = 'running command...';
  try {
    const result = await api('/api/human-agent/command', {
      command: command,
      selected_node_ids: selectedNodeIds,
      mode: modeSelect.value || 'explore'
    });
    // Update answer
    answerEl.textContent = result.answer || 'No answer.';
    // Update truth packet
    truthEl.textContent = JSON.stringify(result.truth_packet || {}, null, 2);
    // Update visual state from result
    const vu = result.visual_update || {};
    if (vu.highlighted_node_ids) highlightedNodeIds = vu.highlighted_node_ids;
    if (vu.hidden_node_ids) hiddenNodeIds = vu.hidden_node_ids;
    if (vu.selected_node_ids) selectedNodeIds = vu.selected_node_ids;
    if (vu.ghost_edges) ghostEdges = vu.ghost_edges;
    if (vu.labels) labels = vu.labels;
    // Update next actions
    renderNextActions(result.next_actions || []);
    // Refresh state from server
    await loadState();
    statusEl.textContent = `${topology.nodes.length} nodes, ${topology.links.length} links`;
  } catch (err) {
    statusEl.textContent = `command failed: ${err.message}`;
    answerEl.textContent = `Error: ${err.message}`;
  }
}

function renderNextActions(actions) {
  if (!actions || !actions.length) {
    nextActionsList.innerHTML = '<span style="color:var(--muted);font-size:12px">No suggestions.</span>';
    return;
  }
  nextActionsList.innerHTML = actions.map(action =>
    `<button type="button" data-action="${escapeAttr(action)}">${escapeHtml(action)}</button>`
  ).join('');
  // Wire up action buttons
  nextActionsList.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      commandInput.value = btn.dataset.action;
      runCommand(btn.dataset.action);
    });
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = String(text || '');
  return div.innerHTML;
}

function escapeAttr(text) {
  return String(text || '').replace(/&/g, '&').replace(/"/g, '"').replace(/</g, '<').replace(/>/g, '>');
}

function draw() {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.save();
  ctx.fillStyle = '#071014';
  ctx.fillRect(0, 0, rect.width, rect.height);

  const visibleSet = new Set(highlightedNodeIds);
  const selectedSet = new Set(selectedNodeIds);
  const hiddenSet = new Set(hiddenNodeIds);

  projected = topology.nodes.map(node => project(node, rect.width, rect.height));
  const byId = new Map(projected.map(item => [item.node.id, item]));

  // Draw topology links
  topology.links.forEach(link => {
    const source = byId.get(link.source);
    const target = byId.get(link.target);
    if (!source || !target) return;
    const sourceVisible = visibleSet.has(link.source) && !hiddenSet.has(link.source);
    const targetVisible = visibleSet.has(link.target) && !hiddenSet.has(link.target);
    const inArena = sourceVisible && targetVisible;
    ctx.globalAlpha = link.status === 'missing' ? 0.9 : (inArena ? 0.72 : 0.12);
    ctx.strokeStyle = link.status === 'missing' ? '#ff6b6b' : (inArena ? '#22d3ee' : '#42515f');
    ctx.lineWidth = link.status === 'missing' ? 2.3 : (inArena ? 1.7 : 0.8);
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
  });

  // Draw ghost edges (hypothesis edges)
  ghostEdges.forEach(ghost => {
    const source = byId.get(ghost.source);
    const target = byId.get(ghost.target);
    if (!source || !target) return;
    ctx.globalAlpha = 0.85;
    ctx.strokeStyle = '#c084fc';
    ctx.lineWidth = 2.0;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
    ctx.setLineDash([]);
  });

  // Draw nodes
  projected.sort((a, b) => a.depth - b.depth).forEach(item => {
    const node = item.node;
    const isSelected = selectedSet.has(node.id);
    const isHighlighted = visibleSet.has(node.id);
    const isHidden = hiddenSet.has(node.id);
    if (isHidden && !isSelected) {
      ctx.globalAlpha = 0.15;
    } else if (isSelected) {
      ctx.globalAlpha = 1;
    } else if (isHighlighted) {
      ctx.globalAlpha = 0.95;
    } else {
      ctx.globalAlpha = 0.35;
    }
    const radius = isSelected ? 9 : (isHighlighted ? 6.5 : 4.6);
    ctx.fillStyle = isSelected ? '#ffffff' : (node.color || '#94a3b8');
    ctx.strokeStyle = isSelected ? '#22d3ee' : '#0b1117';
    ctx.lineWidth = isSelected ? 3 : 1;
    ctx.beginPath();
    ctx.arc(item.x, item.y, radius * item.scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    // Label
    if (isSelected || (isHighlighted && item.scale > 0.72)) {
      ctx.globalAlpha = 0.95;
      ctx.fillStyle = '#dbeafe';
      ctx.font = '12px Cascadia Code, monospace';
      const label = labels[node.id] ? `[${labels[node.id]}] ${node.label || node.id}` : (node.label || node.id);
      ctx.fillText(label, item.x + 10, item.y - 10);
    }
  });
  ctx.restore();
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
  const perspective = 620 / (620 + z2);
  const scale = Math.max(0.35, Math.min(1.8, perspective * zoom));
  return {
    node,
    x: width / 2 + x1 * scale,
    y: height / 2 + y1 * scale,
    depth: z2,
    scale
  };
}

function hitTest(x, y) {
  let best = null;
  let bestDist = Infinity;
  projected.forEach(item => {
    const dist = Math.hypot(item.x - x, item.y - y);
    if (dist < bestDist && dist < 16) {
      best = item.node;
      bestDist = dist;
    }
  });
  return best;
}

// Canvas interaction
canvas.addEventListener('pointerdown', event => {
  dragging = true;
  lastPointer = { x: event.clientX, y: event.clientY };
});

canvas.addEventListener('pointermove', event => {
  if (!dragging || !lastPointer) return;
  yaw += (event.clientX - lastPointer.x) * 0.006;
  pitch += (event.clientY - lastPointer.y) * 0.006;
  pitch = Math.max(-1.25, Math.min(1.25, pitch));
  lastPointer = { x: event.clientX, y: event.clientY };
  draw();
});

canvas.addEventListener('pointerup', async event => {
  const moved = lastPointer && Math.hypot(event.clientX - lastPointer.x, event.clientY - lastPointer.y);
  dragging = false;
  const rect = canvas.getBoundingClientRect();
  const node = moved < 3 ? hitTest(event.clientX - rect.left, event.clientY - rect.top) : null;
  if (node) {
    // Toggle selection
    if (selectedNodeIds.includes(node.id)) {
      selectedNodeIds = selectedNodeIds.filter(id => id !== node.id);
    } else {
      selectedNodeIds = [...selectedNodeIds, node.id];
    }
    draw();
  }
});

canvas.addEventListener('wheel', event => {
  event.preventDefault();
  zoom = Math.max(0.55, Math.min(5.5, zoom + (event.deltaY < 0 ? 0.14 : -0.14)));
  draw();
}, { passive: false });

// Run button
document.getElementById('run-button').addEventListener('click', () => {
  runCommand(commandInput.value);
});

// Enter key in command input
commandInput.addEventListener('keydown', event => {
  if (event.key === 'Enter') {
    event.preventDefault();
    runCommand(commandInput.value);
  }
});

// Demo toggle
document.getElementById('demo-toggle').addEventListener('click', async () => {
  useDemo = !useDemo;
  // Reload the page with demo state by fetching state again
  // The server state is already loaded; we just need to refresh
  await loadState();
});

// Mic button (optional Web Speech API)
document.getElementById('mic-button').addEventListener('click', () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceStatus.textContent = 'Voice unsupported here. Type a command and press Run.';
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.onstart = () => { voiceStatus.textContent = 'Listening...'; };
  recognition.onerror = () => { voiceStatus.textContent = 'Voice failed. Type a command instead.'; };
  recognition.onresult = event => {
    const text = event.results[0][0].transcript || '';
    commandInput.value = text;
    voiceStatus.textContent = `Heard: ${text}`;
    runCommand(text);
  };
  recognition.start();
});

// Polling: refresh state every 800ms
function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const data = await api('/api/human-agent/state');
      liveState = data.state || {};
      updateFromState();
      draw();
    } catch (err) {
      // Silently ignore polling errors
    }
  }, 800);
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();
loadState().then(() => {
  startPolling();
}).catch(err => {
  statusEl.textContent = `failed: ${err.message}`;
});