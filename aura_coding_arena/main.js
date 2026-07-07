const canvas = document.getElementById('arena-canvas');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('graph-status');
const selectedEl = document.getElementById('selected-node');
const capsuleEl = document.getElementById('capsule-json');
const commandInput = document.getElementById('command-input');
const voiceStatus = document.getElementById('voice-status');

let graph = { nodes: [], links: [], meta: {} };
let microArena = null;
let selectedNodeId = null;
let projected = [];
let yaw = 0.58;
let pitch = -0.34;
let zoom = 1.9;
let dragging = false;
let lastPointer = null;
let useDemo = false;

const typeNames = {
  file: 'Files',
  class: 'Classes',
  function: 'Functions',
  method: 'Methods',
  test: 'Tests',
  router: 'Routers',
  context: 'Context',
  research: 'Research',
  verifier: 'Verifier'
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

async function loadTopology() {
  statusEl.textContent = 'loading topology';
  graph = await api(`/api/topology${useDemo ? '?demo=1' : ''}`);
  selectedNodeId = graph.nodes[0] ? graph.nodes[0].id : null;
  statusEl.textContent = `${graph.nodes.length} nodes, ${graph.links.length} links`;
  document.getElementById('truth-policy').textContent = graph.meta && graph.meta.truth_policy
    ? graph.meta.truth_policy
    : 'Exact topology is source of truth.';
  renderLegend();
  if (selectedNodeId) await selectNode(selectedNodeId, 1);
  draw();
}

function renderLegend() {
  const legend = document.getElementById('legend');
  const types = {};
  graph.nodes.forEach(node => {
    const key = node.node_type || 'file';
    if (!types[key]) types[key] = node.color || '#94a3b8';
  });
  legend.innerHTML = Object.keys(types).sort().map(key =>
    `<span><i style="background:${types[key]}"></i>${typeNames[key] || key}</span>`
  ).join('');
}

async function selectNode(nodeId, depth = 1) {
  selectedNodeId = nodeId;
  const command = commandInput.value || 'select';
  microArena = await api('/api/select', {
    node_ids: [nodeId],
    depth,
    human_instruction: command
  });
  updatePanel();
  draw();
}

function updatePanel() {
  const selected = microArena && microArena.selected_nodes && microArena.selected_nodes[0];
  if (!selected) {
    selectedEl.textContent = 'No node selected';
    return;
  }
  selectedEl.textContent = JSON.stringify({
    id: selected.id,
    type: selected.node_type,
    file_path: selected.file_path,
    symbol: selected.symbol,
    line_range: selected.line_range
  }, null, 2);
  setList('dependencies', microArena.dependencies, 'id');
  setList('callers', microArena.callers, 'id');
  setList('tests', microArena.tests);
  setList('faults', microArena.candidate_faults, 'kind');
  const cost = microArena.token_cost || {};
  document.getElementById('raw-tokens').textContent = fmt(cost.raw_repo_tokens);
  document.getElementById('micro-tokens').textContent = fmt(cost.micro_arena_tokens);
  document.getElementById('capsule-tokens').textContent = fmt(cost.capsule_tokens);
  document.getElementById('saved-pct').textContent = `${cost.savings_vs_raw_pct || 0}%`;
}

function setList(id, values, key) {
  const el = document.getElementById(id);
  const items = Array.isArray(values) ? values : [];
  if (!items.length) {
    el.textContent = '-';
    return;
  }
  el.textContent = items.slice(0, 8).map(item => {
    if (typeof item === 'string') return item;
    return item[key] || item.id || item.message || JSON.stringify(item);
  }).join('\n');
}

function fmt(value) {
  return Number(value || 0).toLocaleString();
}

function draw() {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.save();
  ctx.fillStyle = '#071014';
  ctx.fillRect(0, 0, rect.width, rect.height);
  const selectedSet = new Set(microArena ? microArena.nodes.map(node => node.id) : []);
  projected = graph.nodes.map(node => project(node, rect.width, rect.height));
  const byId = new Map(projected.map(item => [item.node.id, item]));

  graph.links.forEach(link => {
    const source = byId.get(link.source);
    const target = byId.get(link.target);
    if (!source || !target) return;
    const inArena = selectedSet.has(link.source) && selectedSet.has(link.target);
    ctx.globalAlpha = link.status === 'missing' ? 0.9 : (inArena ? 0.72 : 0.16);
    ctx.strokeStyle = link.status === 'missing' ? '#ff6b6b' : (inArena ? '#22d3ee' : '#42515f');
    ctx.lineWidth = link.status === 'missing' ? 2.3 : (inArena ? 1.7 : 0.8);
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
  });

  projected.sort((a, b) => a.depth - b.depth).forEach(item => {
    const node = item.node;
    const inArena = selectedSet.has(node.id);
    const selected = node.id === selectedNodeId;
    const radius = selected ? 9 : (inArena ? 6.5 : 4.6);
    ctx.globalAlpha = selected ? 1 : (inArena ? 0.95 : 0.52);
    ctx.fillStyle = node.status === 'selected' || selected ? '#ffffff' : (node.color || '#94a3b8');
    ctx.strokeStyle = node.status === 'failed' ? '#ff6b6b' : (selected ? '#22d3ee' : '#0b1117');
    ctx.lineWidth = selected ? 3 : 1;
    ctx.beginPath();
    ctx.arc(item.x, item.y, radius * item.scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    if (selected || (inArena && item.scale > 0.72)) {
      ctx.globalAlpha = 0.95;
      ctx.fillStyle = '#dbeafe';
      ctx.font = '12px Cascadia Code, monospace';
      ctx.fillText(node.label || node.id, item.x + 10, item.y - 10);
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
  if (node) await selectNode(node.id, 1);
});

canvas.addEventListener('wheel', event => {
  event.preventDefault();
  zoom = Math.max(0.55, Math.min(5.5, zoom + (event.deltaY < 0 ? 0.14 : -0.14)));
  draw();
}, { passive: false });

document.getElementById('expand-button').addEventListener('click', () => {
  if (selectedNodeId) selectNode(selectedNodeId, 2);
});

document.getElementById('compile-button').addEventListener('click', async () => {
  if (!selectedNodeId) return;
  const capsule = await api('/api/compile-capsule', {
    node_ids: [selectedNodeId],
    human_instruction: commandInput.value || 'compile capsule',
    depth: 1
  });
  capsuleEl.textContent = JSON.stringify(capsule, null, 2);
  document.getElementById('capsule-tokens').textContent = fmt(capsule.capsule_tokens_est);
});

document.getElementById('route-button').addEventListener('click', async () => {
  if (!selectedNodeId) return;
  const capsule = await api('/api/compile-capsule', {
    node_ids: selectedNodeId ? [selectedNodeId] : [],
    human_instruction: commandInput.value || 'simulate route',
    depth: 1
  });
  const route = await api('/api/simulate-route', { capsule });
  capsuleEl.textContent = JSON.stringify({
    action: 'simulate_route',
    capsule_version: capsule.capsule_version,
    capsule_tokens_est: capsule.capsule_tokens_est,
    route_decision: route
  }, null, 2);
});

document.getElementById('mark-button').addEventListener('click', async () => {
  if (!selectedNodeId || !microArena || microArena.nodes.length < 2) return;
  const target = microArena.nodes.find(node => node.id !== selectedNodeId);
  if (!target) return;
  const result = await api('/api/mark-edge', {
    source: selectedNodeId,
    target: target.id,
    kind: 'candidate_missing_route',
    status: 'missing'
  });
  graph = result.topology;
  draw();
});

document.getElementById('demo-toggle').addEventListener('click', async () => {
  useDemo = !useDemo;
  await loadTopology();
});

document.getElementById('voice-button').addEventListener('click', () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceStatus.textContent = 'Voice unsupported here. Type a command and use the buttons.';
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.onstart = () => { voiceStatus.textContent = 'Listening...'; };
  recognition.onerror = () => { voiceStatus.textContent = 'Voice failed. Type a command instead.'; };
  recognition.onresult = async event => {
    const text = event.results[0][0].transcript || '';
    commandInput.value = text;
    voiceStatus.textContent = `Heard: ${text}`;
    const result = await api('/api/voice-intent', {
      node_ids: selectedNodeId ? [selectedNodeId] : [],
      command: text
    });
    capsuleEl.textContent = JSON.stringify(result, null, 2);
    if (result.selection) {
      microArena = result.selection;
      updatePanel();
      draw();
    }
  };
  recognition.start();
});

window.addEventListener('resize', resizeCanvas);
resizeCanvas();
loadTopology().catch(err => {
  statusEl.textContent = `failed: ${err.message}`;
});
