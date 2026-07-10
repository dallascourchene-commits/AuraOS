// Aura Human Agent Arena — frontend logic (Intelligence Layer V1.2)
// Improvements: layoutSpread, zoom range, label modes, Node Inspector panel,
// click/inspect behavior, lazy expansion, CODEMAP-projected terminology.

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

// Intelligence Layer state (additive V1.2)
let conceptWorkspace = null;
let projectedNodes = [];      // CODEMAP-projected nodes (real, visual projection only)
let projectedLinks = [];      // links between projected nodes
let nodeInspectorData = null; // NodeIntelligencePacket for selected node
let layoutSpread = 2.8;       // default spread factor
let labelMode = 'selected';   // 'selected' | 'highlighted' | 'all' | 'off'
let zoomSpeed = 0.14;         // configurable wheel zoom speed
let lastClickTime = 0;        // for double-click detection
let lastClickedNode = null;

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
  demo: 'Demo',
  doc: 'Docs'
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
    // Re-merge locally cached projected nodes after state refresh so they
    // don't flash and disappear. The server topology may already contain
    // them (since _show_concept_workspace merges into self.topology), but
    // if a poll arrives between command and state update, this ensures
    // projected nodes persist visually.
    if (projectedNodes && projectedNodes.length > 0) {
      const existingIds = new Set(topology.nodes.map(n => n.id));
      projectedNodes.forEach(sn => {
        if (!existingIds.has(sn.id)) {
          topology.nodes.push(sn);
        }
      });
      if (projectedLinks) {
        const existingLinkKeys = new Set(topology.links.map(l => `${l.source}|${l.target}`));
        projectedLinks.forEach(sl => {
          const key = `${sl.source}|${sl.target}`;
          if (!existingLinkKeys.has(key)) {
            topology.links.push(sl);
          }
        });
      }
    }
    // Re-merge concept workspace nodes from state if available
    if (liveState.concept_workspace && liveState.concept_workspace.concept) {
      conceptWorkspace = liveState.concept_workspace;
      renderConceptWorkspace(conceptWorkspace);
    }
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
  types['__ghost'] = '#c084fc';
  types['__projected'] = '#8b5cf6';
  legend.innerHTML = Object.keys(types).sort().map(key =>
    `<span><i style="background:${types[key]}"></i>${key === '__ghost' ? 'Ghost Edges' : (key === '__projected' ? 'CODEMAP-Projected' : escapeHtml(typeNames[key] || key))}</span>`
  ).join('');
}

function updateFromState() {
  if (!liveState) return;
  highlightedNodeIds = liveState.visible_node_ids || [];
  hiddenNodeIds = liveState.hidden_node_ids || [];
  selectedNodeIds = liveState.selected_node_ids || [];
  ghostEdges = liveState.ghost_edges || [];
  if (liveState.concept_workspace && liveState.concept_workspace.concept) {
    conceptWorkspace = liveState.concept_workspace;
    renderConceptWorkspace(conceptWorkspace);
  }
  const events = liveState.event_log || [];
  if (events.length) {
    const recent = events.slice(-20);
    eventLogEl.textContent = recent.map(e =>
      `[${e.kind}] ${e.detail}`
    ).join('\n');
  }
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
    answerEl.textContent = result.answer || 'No answer.';
    truthEl.textContent = JSON.stringify(result.truth_packet || {}, null, 2);
    const vu = result.visual_update || {};
    if (vu.highlighted_node_ids) highlightedNodeIds = vu.highlighted_node_ids;
    if (vu.hidden_node_ids) hiddenNodeIds = vu.hidden_node_ids;
    if (vu.selected_node_ids) selectedNodeIds = vu.selected_node_ids;
    if (vu.ghost_edges) ghostEdges = vu.ghost_edges;
    if (vu.labels) labels = vu.labels;
    // Merge CODEMAP-projected nodes into local topology for rendering
    if (vu.synthetic_nodes && vu.synthetic_nodes.length > 0) {
      projectedNodes = vu.synthetic_nodes;
      projectedLinks = vu.links || [];
      const existingIds = new Set(topology.nodes.map(n => n.id));
      projectedNodes.forEach(sn => {
        if (!existingIds.has(sn.id)) {
          topology.nodes.push(sn);
        }
      });
      projectedLinks.forEach(sl => topology.links.push(sl));
    }
    // Also handle additional_nodes from expansion
    if (vu.additional_nodes && vu.additional_nodes.length > 0) {
      const existingIds = new Set(topology.nodes.map(n => n.id));
      vu.additional_nodes.forEach(sn => {
        if (!existingIds.has(sn.id)) {
          topology.nodes.push(sn);
        }
      });
      if (vu.additional_links) {
        vu.additional_links.forEach(sl => topology.links.push(sl));
      }
    }
    if (vu.concept_workspace) {
      conceptWorkspace = vu.concept_workspace;
      renderConceptWorkspace(conceptWorkspace);
    }
    // Node Intelligence Packet from inspect/explain commands
    if (result.node_intelligence) {
      nodeInspectorData = result.node_intelligence;
      renderNodeInspector(nodeInspectorData);
    }
    renderNextActions(result.next_actions || []);
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
  nextActionsList.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      commandInput.value = btn.dataset.action;
      runCommand(btn.dataset.action);
    });
  });
}

// Concept workspace summary panel renderer
function renderConceptWorkspace(ws) {
  if (!ws) return;
  let panel = document.getElementById('concept-workspace-panel');
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'concept-workspace-panel';
    panel.style.cssText = [
      'background: linear-gradient(135deg, rgba(99,102,241,0.18) 0%, rgba(14,165,233,0.14) 100%)',
      'border: 1px solid rgba(139,92,246,0.45)',
      'border-radius: 10px',
      'padding: 12px 16px',
      'margin-bottom: 10px',
      'font-size: 12px',
      'color: #e2e8f0',
      'position: relative',
    ].join(';');
    const answEl = document.getElementById('answer-text');
    if (answEl && answEl.parentNode) {
      answEl.parentNode.insertBefore(panel, answEl.nextSibling);
    }
  }
  const projectedCount = ws.synthetic_node_count || 0;
  const actionBtns = (ws.action_buttons || []).map(action =>
    `<button type="button" data-action="${escapeAttr(action)}" style="font-size:11px;padding:3px 9px;border-radius:6px;background:rgba(99,102,241,0.25);border:1px solid rgba(139,92,246,0.5);color:#c4b5fd;cursor:pointer;margin:2px">${escapeHtml(action)}</button>`
  ).join('');
  panel.innerHTML = `
    <div style="font-weight:700;font-size:13px;color:#a78bfa;margin-bottom:6px">
      &#128196; Concept Workspace: <span style="color:#e2e8f0">${escapeHtml(ws.concept || '')}</span>
      <span style="float:right;font-weight:400;color:#64748b;font-size:11px">ID: ${escapeHtml((ws.workspace_id || '').substring(0,8))}</span>
    </div>
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:7px;font-size:11px;color:#94a3b8">
      <span>&#128196; <b style="color:#e2e8f0">${ws.files_count || 0}</b> files</span>
      <span>&#402; <b style="color:#e2e8f0">${ws.symbols_count || 0}</b> symbols</span>
      <span>&#129514; <b style="color:#ef5da8">${ws.tests_count || 0}</b> tests</span>
      <span>&#128196; <b style="color:#facc15">${ws.docs_count || 0}</b> docs</span>
      <span>&#128279; <b style="color:#22d3ee">${ws.neighbors_count || 0}</b> neighbors</span>
      ${projectedCount > 0 ? `<span>&#10024; <b style="color:#8b5cf6">${projectedCount}</b> CODEMAP-projected (real, visual-only)</span>` : ''}
    </div>
    <div style="margin-top:4px;font-size:11px">${actionBtns}</div>
  `;
  panel.querySelectorAll('button[data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const act = btn.dataset.action;
      const commandMap = {
        'show all functions': `show all functions related to ${ws.concept || 'concept'}`,
        'show neighbors': `show everything connected to ${ws.concept || 'concept'}`,
        'show tests': 'show tests',
        'show docs': `show ${ws.concept || 'concept'} docs`,
        'show agent handoff': 'export handoff packet',
        'prepare refactor plan': `refactor ${ws.concept || 'concept'}`,
      };
      const cmd = commandMap[act] || act;
      commandInput.value = cmd;
      runCommand(cmd);
    });
  });
}

// Node Inspector panel renderer (Intelligence Layer V1.2)
function renderNodeInspector(pkt) {
  if (!pkt) return;
  let panel = document.getElementById('node-inspector-panel');
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'node-inspector-panel';
    panel.style.cssText = [
      'background: linear-gradient(135deg, rgba(34,211,238,0.12) 0%, rgba(99,102,241,0.12) 100%)',
      'border: 1px solid rgba(34,211,238,0.4)',
      'border-radius: 10px',
      'padding: 12px 16px',
      'margin-bottom: 10px',
      'font-size: 12px',
      'color: #e2e8f0',
    ].join(';');
    const answEl = document.getElementById('answer-text');
    if (answEl && answEl.parentNode) {
      answEl.parentNode.insertBefore(panel, answEl.nextSibling);
    }
  }

  const originBadge = pkt.node_origin || 'unresolved_candidate';
  const originColors = {
    exact_topology_node: '#22d3ee',
    codemap_projected_node: '#8b5cf6',
    inferred_relationship_edge: '#f59e0b',
    ghost_hypothesis_edge: '#c084fc',
    unresolved_candidate: '#ef4444',
  };
  const originColor = originColors[originBadge] || '#94a3b8';
  const rel = pkt.relationships || {};
  const risk = pkt.risk || {};
  const riskBadges = [];
  if (risk.missing_tests) riskBadges.push('<span style="color:#f59e0b">&#9888; missing tests</span>');
  if (risk.high_fan_in) riskBadges.push('<span style="color:#ef4444">&#128293; high fan-in</span>');
  if (risk.hub_file) riskBadges.push('<span style="color:#ef4444">&#128230; hub file</span>');
  if (risk.large_file) riskBadges.push('<span style="color:#f59e0b">&#128196; large file</span>');
  if (risk.missing_grounding) riskBadges.push('<span style="color:#ef4444">&#10067; needs grounding</span>');

  const affords = (pkt.recommended_affordances || []).slice(0, 5).map(a =>
    `<div style="font-size:10px;color:#94a3b8;margin:1px 0">&#128295; ${escapeHtml(a.name || a.id || '')}</div>`
  ).join('');

  const nextBtns = (pkt.next_actions || []).slice(0, 6).map(action =>
    `<button type="button" data-action="${escapeAttr(action)}" style="font-size:10px;padding:2px 7px;border-radius:5px;background:rgba(34,211,238,0.15);border:1px solid rgba(34,211,238,0.35);color:#67e8f9;cursor:pointer;margin:2px">${escapeHtml(action)}</button>`
  ).join('');

  panel.innerHTML = `
    <div style="font-weight:700;font-size:13px;color:#67e8f9;margin-bottom:6px">
      &#128269; Node Inspector
      <span style="float:right;background:${originColor};color:#0b1117;border-radius:4px;padding:1px 7px;font-size:10px;font-weight:700">${escapeHtml(originBadge)}</span>
    </div>
    <div style="font-size:11px;margin-bottom:5px">
      <div style="color:#94a3b8">Node: <span style="color:#e2e8f0;font-family:monospace">${escapeHtml(pkt.node_id || '')}</span></div>
      ${pkt.file_path ? `<div style="color:#94a3b8">File: <span style="color:#e2e8f0">${escapeHtml(pkt.file_path)}</span></div>` : ''}
      ${pkt.symbol ? `<div style="color:#94a3b8">Symbol: <span style="color:#e2e8f0">${escapeHtml(pkt.symbol)}</span></div>` : ''}
      ${pkt.line_range && pkt.line_range.length ? `<div style="color:#94a3b8">Lines: <span style="color:#e2e8f0">${pkt.line_range[0]}–${pkt.line_range[1]}</span></div>` : ''}
      ${pkt.digest8 ? `<div style="color:#94a3b8">Digest: <span style="color:#e2e8f0;font-family:monospace">${escapeHtml(pkt.digest8)}</span></div>` : ''}
      ${pkt.signature_hash ? `<div style="color:#94a3b8">Sig: <span style="color:#e2e8f0;font-family:monospace">${escapeHtml(pkt.signature_hash.substring(0,16))}…</span></div>` : ''}
    </div>
    <div style="font-size:11px;color:#cbd5e1;margin-bottom:5px;line-height:1.4">${escapeHtml(pkt.why_here || '')}</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;font-size:10px;color:#64748b;margin-bottom:4px">
      <span>contains: <b style="color:#e2e8f0">${(rel.contains || []).length}</b></span>
      <span>calls: <b style="color:#e2e8f0">${(rel.calls || []).length}</b></span>
      <span>called_by: <b style="color:#e2e8f0">${(rel.called_by || []).length}</b></span>
      <span>neighbors: <b style="color:#e2e8f0">${(rel.neighbors || []).length}</b></span>
      <span>tests: <b style="color:#ef5da8">${(rel.tests || []).length}</b></span>
      <span>docs: <b style="color:#facc15">${(rel.docs || []).length}</b></span>
    </div>
    ${riskBadges.length ? `<div style="margin:4px 0;font-size:10px">${riskBadges.join(' ')}</div>` : ''}
    ${affords ? `<div style="margin:4px 0"><div style="font-size:10px;color:#64748b;margin-bottom:2px">Recommended Aura tools:</div>${affords}</div>` : ''}
    <div style="margin:6px 0">${nextBtns}</div>
    <div style="font-size:9px;color:#475569;margin-top:4px">patch_authority: exact_source_spans_and_hashes_only | vsa: false</div>
  `;
  panel.querySelectorAll('button[data-action]').forEach(btn => {
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
  return String(text || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Label truncation helper
function truncateLabel(text, maxLen) {
  if (!text) return '';
  if (text.length <= maxLen) return text;
  return text.substring(0, maxLen - 1) + '…';
}

// Determine if a label should be shown based on label mode and zoom
function shouldShowLabel(node, isSelected, isHighlighted, scale) {
  if (labelMode === 'off') return false;
  if (labelMode === 'all') return true;
  if (labelMode === 'selected') return isSelected || isHighlighted;
  if (labelMode === 'highlighted') return isHighlighted || isSelected;
  return false;
}

// Determine label content based on zoom level
function getLabelForZoom(node, scale) {
  const baseLabel = node.label || node.id;
  const isProjected = node.metadata && node.metadata.projected_from_codemap;
  const badge = isProjected ? '[CODEMAP] ' : (labels[node.id] ? `[${labels[node.id]}] ` : '');

  if (scale > 1.2) {
    // High zoom: show full label
    return badge + baseLabel;
  } else if (scale > 0.7) {
    // Medium zoom: truncated label
    return badge + truncateLabel(baseLabel, 28);
  } else {
    // Low zoom: very short label (subsystem/file only)
    return badge + truncateLabel(baseLabel, 16);
  }
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
    const isProjected = node.metadata && node.metadata.projected_from_codemap;
    if (isHidden && !isSelected) {
      ctx.globalAlpha = 0.15;
    } else if (isSelected) {
      ctx.globalAlpha = 1;
    } else if (isHighlighted) {
      ctx.globalAlpha = 0.95;
    } else {
      ctx.globalAlpha = 0.35;
    }
    const baseRadius = isSelected ? 9 : (isHighlighted ? 6.5 : 4.6);
    // Cap visual radius growth so high zoom doesn't produce giant nodes,
    // while allowing positions to spread across the full zoom range.
    const visualScale = Math.min(item.scale, 3.0);
    const radius = baseRadius * visualScale;
    ctx.fillStyle = isSelected ? '#ffffff' : (node.color || '#94a3b8');
    ctx.strokeStyle = isSelected ? '#22d3ee' : (isProjected ? '#8b5cf6' : '#0b1117');
    ctx.lineWidth = isSelected ? 3 : (isProjected ? 2 : 1);
    ctx.beginPath();
    ctx.arc(item.x, item.y, radius * item.scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    // Badge ring for CODEMAP-projected nodes
    if (isProjected && isHighlighted) {
      ctx.globalAlpha = 0.55;
      ctx.strokeStyle = '#8b5cf6';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.arc(item.x, item.y, (radius + 4) * visualScale, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    // Label rendering with background box for readability
    if (shouldShowLabel(node, isSelected, isHighlighted, item.scale)) {
      const label = getLabelForZoom(node, item.scale);
      ctx.globalAlpha = 0.95;
      ctx.font = '12px Cascadia Code, monospace';
      // Measure text for background box
      const textMetrics = ctx.measureText(label);
      const textWidth = textMetrics.width;
      const textHeight = 14;
      const labelX = item.x + 10;
      const labelY = item.y - 10;
      // Draw background box
      ctx.globalAlpha = 0.75;
      ctx.fillStyle = '#0b1117';
      ctx.fillRect(labelX - 3, labelY - textHeight + 2, textWidth + 6, textHeight + 2);
      // Draw label text
      ctx.globalAlpha = 0.95;
      ctx.fillStyle = isProjected ? '#c4b5fd' : '#dbeafe';
      ctx.fillText(label, labelX, labelY);
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
  const scale = Math.max(0.35, Math.min(8.0, perspective * zoom));
  return {
    node,
    x: width / 2 + x1 * scale * layoutSpread,
    y: height / 2 + y1 * scale * layoutSpread,
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

// Focus selected: hide all unselected nodes
function focusSelected() {
  if (selectedNodeIds.length === 0) return;
  hiddenNodeIds = topology.nodes
    .map(n => n.id)
    .filter(id => !selectedNodeIds.includes(id));
  draw();
}

// Collapse unselected: hide all unselected, show only selected + their direct neighbors
function collapseUnselected() {
  if (selectedNodeIds.length === 0) return;
  const keepSet = new Set(selectedNodeIds);
  // Add direct neighbors
  topology.links.forEach(link => {
    if (selectedNodeIds.includes(link.source)) keepSet.add(link.target);
    if (selectedNodeIds.includes(link.target)) keepSet.add(link.source);
  });
  hiddenNodeIds = topology.nodes
    .map(n => n.id)
    .filter(id => !keepSet.has(id));
  draw();
}

// Reset view
function resetView() {
  yaw = 0.58;
  pitch = -0.34;
  zoom = 1.9;
  layoutSpread = 2.8;
  hiddenNodeIds = [];
  const spreadSlider = document.getElementById('spread-slider');
  const zoomSlider = document.getElementById('zoom-slider');
  if (spreadSlider) spreadSlider.value = layoutSpread;
  if (spreadValue) spreadValue.textContent = layoutSpread.toFixed(1);
  if (zoomSlider) zoomSlider.value = zoom;
  draw();
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
    // Shift-click: focus selected
    if (event.shiftKey) {
      selectedNodeIds = [node.id];
      focusSelected();
      return;
    }
    // Alt-click: collapse unrelated
    if (event.altKey) {
      selectedNodeIds = [node.id];
      collapseUnselected();
      return;
    }
    // Double-click detection
    const now = Date.now();
    if (lastClickedNode === node.id && (now - lastClickTime) < 350) {
      // Double-click: inspect + expand balanced
      selectedNodeIds = [node.id];
      draw();
      // Send inspect command, then expand
      await runCommand('inspect selected');
      // Expand is triggered by the user via next actions or command
      commandInput.value = 'expand selected';
      runCommand('expand selected');
      lastClickTime = 0;
      return;
    }
    // Single-click: select + inspect
    lastClickTime = now;
    lastClickedNode = node.id;
    if (selectedNodeIds.includes(node.id)) {
      selectedNodeIds = selectedNodeIds.filter(id => id !== node.id);
    } else {
      selectedNodeIds = [...selectedNodeIds, node.id];
    }
    draw();
    // Auto-inspect on single click
    await runCommand('inspect selected');
  }
});

canvas.addEventListener('wheel', event => {
  event.preventDefault();
  // Configurable zoom speed with greater range (0.4 to 8.0)
  zoom = Math.max(0.4, Math.min(8.0, zoom + (event.deltaY < 0 ? zoomSpeed : -zoomSpeed)));
  const zoomSlider = document.getElementById('zoom-slider');
  if (zoomSlider) zoomSlider.value = zoom;
  draw();
}, { passive: false });

// Layout controls (Intelligence Layer V1.2)
const spreadSlider = document.getElementById('spread-slider');
const spreadValue = document.getElementById('spread-value');
if (spreadSlider) {
  spreadSlider.addEventListener('input', () => {
    layoutSpread = parseFloat(spreadSlider.value);
    if (spreadValue) spreadValue.textContent = layoutSpread.toFixed(1);
    draw();
  });
}

const zoomSlider = document.getElementById('zoom-slider');
if (zoomSlider) {
  zoomSlider.addEventListener('input', () => {
    zoom = parseFloat(zoomSlider.value);
    draw();
  });
}

const labelModeSelect = document.getElementById('label-mode-select');
if (labelModeSelect) {
  labelModeSelect.addEventListener('change', () => {
    labelMode = labelModeSelect.value;
    draw();
  });
}

const resetBtn = document.getElementById('reset-view-btn');
if (resetBtn) {
  resetBtn.addEventListener('click', resetView);
}

const focusBtn = document.getElementById('focus-selected-btn');
if (focusBtn) {
  focusBtn.addEventListener('click', focusSelected);
}

const collapseBtn = document.getElementById('collapse-unselected-btn');
if (collapseBtn) {
  collapseBtn.addEventListener('click', collapseUnselected);
}

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
