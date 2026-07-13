'use strict';

(() => {
  const S = window.Showcase;
  if (!S || !S.$ || S.attemptArchiveInstalled) return;
  S.attemptArchiveInstalled = true;
  const $ = S.$, esc = S.esc;
  const ARCHIVED_ROUTES = new Set([
    '/api/human-agent/workflow/action',
    '/api/human-agent/workflow/command',
    '/api/human-agent/tools/run',
    '/api/coding-workbench/action',
    '/api/coding-workbench/command',
  ]);
  const STAGES = ['INTAKE', 'FRAME', 'GROUND', 'PLAN', 'ACT', 'PROVE', 'DECIDE'];

  const archive = S.attemptArchive = S.attemptArchive || {
    attempts: [],
    failuresOnly: false,
    selected: null,
    busy: false,
    notice: 'Every coding attempt is preserved, including denied patches and failed verification.',
  };

  function currentStageIndex() {
    return Math.max(0, Math.min(STAGES.length - 1, Number(S.humanWorkspace?.stage) || 0));
  }

  function currentDialogue() {
    const index = currentStageIndex();
    const state = S.humanGateDialogue?.byStage?.[index] || {};
    const pending = state.pending || {};
    const decision = state.decision || {};
    return {
      proposal_id: pending.proposal_id || decision.proposal_id || '',
      status: pending.status || decision.status || '',
      human_comment: pending.human_comment || state.draft || '',
      aura_response: pending.aura_response || '',
      decision,
    };
  }

  function archiveContext() {
    return {
      stage_hint: STAGES[currentStageIndex()],
      objective: S.workflow?.objective || S.handoff?.objective || '',
      node_context: S.humanGateDialogue?.nodeContext || {},
      gate_dialogue: currentDialogue(),
      captured_from: 'aura_showcase_attempt_archive_ui',
    };
  }

  const originalApi = S.api.bind(S);
  S.api = async (path, body) => {
    let outbound = body;
    if (body !== undefined && ARCHIVED_ROUTES.has(String(path))) {
      outbound = {...body, _arena_archive_context: archiveContext()};
    }
    const result = await originalApi(path, outbound);
    if (result?.attempt_artifact) {
      archive.notice = result.attempt_artifact.ok
        ? `Attempt preserved as ${result.attempt_artifact.artifact_id}. It remains unverified refactoring evidence.`
        : 'The attempt completed, but the human-facing archive could not persist its artifact.';
      window.setTimeout(loadAttempts, 0);
    }
    return result;
  };

  function installStyles() {
    if ($('attempt-archive-styles')) return;
    const style = document.createElement('style');
    style.id = 'attempt-archive-styles';
    style.textContent = `
      .attempt-archive-card{margin-top:14px;padding:16px;border:1px solid rgba(96,165,250,.24);border-radius:16px;background:linear-gradient(145deg,rgba(7,17,30,.96),rgba(5,11,18,.9));display:grid;gap:12px}
      .attempt-archive-head,.attempt-archive-toolbar,.attempt-actions{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}.attempt-archive-list{display:grid;gap:9px}.attempt-row{padding:12px;border-radius:12px;border:1px solid rgba(148,163,184,.16);background:rgba(3,9,16,.72);display:grid;gap:7px}.attempt-row[data-ok="false"]{border-color:rgba(251,113,133,.34)}.attempt-row[data-ok="true"]{border-color:rgba(45,212,191,.24)}.attempt-meta,.attempt-node{font-size:11px;color:#94a9b4;overflow-wrap:anywhere}.attempt-failure{font-size:12px;color:#fda4af;white-space:pre-wrap}.attempt-actions{justify-content:flex-start}.attempt-actions button{font-size:11px;padding:7px 9px}.attempt-detail{max-height:430px;overflow:auto;padding:12px;border-radius:10px;background:#03090d;border:1px solid rgba(148,163,184,.15);white-space:pre-wrap}.attempt-empty{color:#94a9b4}.attempt-archive-notice{font-size:12px;color:#b8cbd2}.attempt-authority{padding:9px 11px;border-left:3px solid #60a5fa;background:rgba(96,165,250,.07);font-size:12px}
    `;
    document.head.appendChild(style);
  }

  function installPanel() {
    if ($('human-attempt-archive')) return true;
    const anchor = $('human-gate-dialogue') || $('human-tour-tool') || $('human-tour-card');
    if (!anchor) return false;
    installStyles();
    const panel = document.createElement('section');
    panel.id = 'human-attempt-archive';
    panel.className = 'attempt-archive-card';
    anchor.insertAdjacentElement('afterend', panel);
    panel.addEventListener('click', event => {
      const button = event.target instanceof Element ? event.target.closest('button') : null;
      if (!button) return;
      if (button.id === 'attempt-refresh') loadAttempts();
      if (button.id === 'attempt-filter') {
        archive.failuresOnly = !archive.failuresOnly;
        loadAttempts();
      }
      const artifactId = button.dataset.artifactId;
      if (!artifactId) return;
      if (button.dataset.attemptAction === 'inspect') inspectAttempt(artifactId);
      if (button.dataset.attemptAction === 'copy') copyAttempt(artifactId, false);
      if (button.dataset.attemptAction === 'copy-diff') copyAttempt(artifactId, true);
    });
    return true;
  }

  function formatDate(value) {
    const date = new Date(Number(value || 0) * 1000);
    return Number.isNaN(date.getTime()) ? 'unknown time' : date.toLocaleString();
  }

  function rowHtml(item) {
    const node = item.selected_node || {};
    const nodeText = node.file_path
      ? `${node.file_path}${node.symbol ? ` · ${node.symbol}` : ''}`
      : 'No selected topology node recorded';
    return `<article class="attempt-row" data-ok="${item.ok ? 'true' : 'false'}">
      <div class="attempt-archive-head"><strong>${esc(item.action_id || item.route || 'Arena attempt')}</strong><span class="pill">${esc(item.status || (item.ok ? 'COMPLETED' : 'FAILED'))}</span></div>
      <div class="attempt-meta">${esc(item.artifact_id)} · ${esc(item.arena_id)} · gate ${esc(item.phase || '—')} · ${esc(formatDate(item.created_at))}</div>
      <div class="attempt-node">Topology: ${esc(nodeText)}</div>
      ${item.failure_summary ? `<div class="attempt-failure">${esc(item.failure_summary)}</div>` : '<div class="attempt-meta">Observed output preserved for comparison and later refactoring.</div>'}
      <div class="attempt-actions"><button type="button" class="secondary" data-attempt-action="inspect" data-artifact-id="${esc(item.artifact_id)}">Inspect</button><button type="button" class="secondary" data-attempt-action="copy" data-artifact-id="${esc(item.artifact_id)}">Copy full artifact</button><button type="button" class="secondary" data-attempt-action="copy-diff" data-artifact-id="${esc(item.artifact_id)}">Copy diff</button></div>
      ${archive.selected?.artifact_id === item.artifact_id ? `<pre class="attempt-detail">${esc(JSON.stringify(archive.selected, null, 2))}</pre>` : ''}
    </article>`;
  }

  function render() {
    if (!installPanel()) return;
    const panel = $('human-attempt-archive');
    panel.innerHTML = `
      <div class="attempt-archive-head"><div><p class="eyebrow">Arena attempt archive · successful, denied, and failed work</p><h3>Inspectable refactoring artifacts</h3></div><span class="pill">${archive.attempts.length} shown</span></div>
      <div class="attempt-authority">Stored output can be inspected, copied, compared, or pasted into a future refactor. Storage does not verify it or grant patch, commit, push, merge, or learning authority.</div>
      <div class="attempt-archive-toolbar"><span class="attempt-archive-notice">${esc(archive.notice)}</span><div><button id="attempt-filter" type="button" class="secondary">${archive.failuresOnly ? 'Show all attempts' : 'Show failed only'}</button> <button id="attempt-refresh" type="button" class="secondary">Refresh archive</button></div></div>
      <div class="attempt-archive-list">${archive.attempts.length ? archive.attempts.map(rowHtml).join('') : '<p class="attempt-empty">No archived attempts yet. The next workflow action, denial, failed test, or verifier result will appear here automatically.</p>'}</div>`;
  }

  async function loadAttempts() {
    if (archive.busy) return;
    archive.busy = true;
    try {
      const suffix = archive.failuresOnly ? '&failures_only=true' : '';
      const result = await originalApi(`/api/showcase/human/attempts?limit=12${suffix}`);
      if (!result.ok) throw new Error(result.error || 'Attempt archive unavailable');
      archive.attempts = result.attempts || [];
    } catch (error) {
      archive.notice = `Attempt archive unavailable: ${error.message}`;
    } finally {
      archive.busy = false;
      render();
    }
  }

  async function inspectAttempt(artifactId) {
    try {
      const result = await originalApi(`/api/showcase/human/attempts/${encodeURIComponent(artifactId)}`);
      if (!result.ok) throw new Error(result.error || 'Artifact not found');
      archive.selected = archive.selected?.artifact_id === artifactId ? null : result.artifact;
      archive.notice = archive.selected
        ? `Inspecting ${artifactId}. The full sanitized request, result, diff, output, topology anchor, and gate dialogue are visible.`
        : 'Artifact inspection closed.';
    } catch (error) {
      archive.notice = error.message;
    }
    render();
  }

  async function writeClipboard(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const area = document.createElement('textarea');
    area.value = text;
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    document.execCommand('copy');
    area.remove();
  }

  async function copyAttempt(artifactId, diffOnly) {
    try {
      const result = await originalApi(`/api/showcase/human/attempts/${encodeURIComponent(artifactId)}`);
      if (!result.ok) throw new Error(result.error || 'Artifact not found');
      const artifact = result.artifact || {};
      const text = diffOnly ? artifact.copy_diff : artifact.copy_text;
      if (!String(text || '').trim()) throw new Error(diffOnly ? 'This attempt has no candidate diff.' : 'This artifact has no copyable content.');
      await writeClipboard(String(text));
      archive.notice = diffOnly
        ? `Candidate diff from ${artifactId} copied for human inspection or a future refactor.`
        : `Full sanitized artifact ${artifactId} copied.`;
    } catch (error) {
      archive.notice = `Copy failed: ${error.message}`;
    }
    render();
  }

  const originalRender = S.renderHumanTour;
  S.renderHumanTour = (...args) => {
    const result = originalRender?.(...args);
    window.setTimeout(render, 0);
    return result;
  };

  window.setTimeout(() => {
    render();
    loadAttempts();
  }, 0);
})();
