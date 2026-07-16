// Aura Emergent Refactor Workspace — persistent findings and bounded research UI.
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  function safeHttpUrl(value) {
    try {
      const parsed = new URL(String(value || ''), window.location.href);
      return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : '';
    } catch (_error) {
      return '';
    }
  }

  let findings = [];
  let selectedFindingIds = new Set();
  let selectedResearchEvidenceIds = new Set();

  async function api(path, body) {
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

  function setStatus(text, tone = '') {
    const node = $('emergent-status');
    if (!node) return;
    node.textContent = text;
    node.dataset.tone = tone;
  }

  function activateEmergentWorkspace() {
    document.querySelector('[data-surface="emergent-workspace"]')?.click();
  }

  async function loadRuns() {
    try {
      const result = await api('/api/human-agent/emergent/runs?limit=50');
      const runs = result.runs || [];
      const findingCount = runs.reduce((sum, run) => sum + Number(run.finding_count || 0), 0);
      setStatus(`${runs.length} stored runs · ${findingCount} projected findings`, 'ok');
      const host = $('emergent-run-list');
      if (host) {
        host.innerHTML = runs.map(run => `
          <article class="emergent-run-card">
            <strong>${escape(run.label || run.run_id)}</strong>
            <span>${escape(run.suite_version || 'emergent report')}</span>
            <small>${Number(run.finding_count || 0)} findings · ${Number(run.probe_count || 0)} probes</small>
          </article>`).join('') || '<p class="placeholder">No stored emergent runs yet.</p>';
      }
    } catch (error) {
      setStatus(`Storage unavailable: ${error.message}`, 'error');
    }
  }

  async function searchFindings() {
    const query = $('emergent-query')?.value?.trim() || $('workflow-objective')?.value?.trim() || '';
    if (!query) {
      setStatus('Enter a refactor objective or search phrase.', 'warn');
      return;
    }
    setStatus('Searching stored emergent evidence…');
    try {
      const result = await api(`/api/human-agent/emergent/search?q=${encodeURIComponent(query)}&limit=30`);
      findings = result.findings || [];
      selectedFindingIds = new Set([...selectedFindingIds].filter(id => findings.some(item => item.finding_id === id)));
      renderFindings();
      setStatus(`${findings.length} relevant findings · external research remains advisory`, 'ok');
    } catch (error) {
      setStatus(`Search failed: ${error.message}`, 'error');
    }
  }

  function renderFindings() {
    const host = $('emergent-findings');
    if (!host) return;
    host.innerHTML = findings.map((finding, index) => {
      const source = finding.source || {};
      const target = finding.target || {};
      const checked = selectedFindingIds.has(finding.finding_id) ? 'checked' : '';
      return `<article class="finding-card" data-finding-id="${escape(finding.finding_id)}">
        <label class="finding-select"><input type="checkbox" ${checked} data-select-finding="${escape(finding.finding_id)}"> include</label>
        <div class="finding-rank">${index + 1}</div>
        <div class="finding-body">
          <strong>${escape(finding.emergent_ability || 'Emergent candidate')}</strong>
          <p>${escape(source.file || '?')}:${escape(source.symbol || '?')} → ${escape(target.file || '?')}:${escape(target.symbol || '?')}</p>
          <small>${escape(finding.status || 'UNKNOWN')} · score ${Number(finding.score || 0).toFixed(3)} · ${Number(finding.evidence_count || 0)} evidence entries</small>
          <span class="missing-wire">${escape(finding.missing_wire || 'missing wire not specified')}</span>
        </div>
      </article>`;
    }).join('') || '<p class="placeholder">No stored findings match this objective.</p>';

    host.querySelectorAll('[data-select-finding]').forEach(input => {
      input.addEventListener('change', event => {
        const id = event.currentTarget.dataset.selectFinding;
        if (event.currentTarget.checked) selectedFindingIds.add(id);
        else selectedFindingIds.delete(id);
        updateSelectionCount();
      });
    });
    host.querySelectorAll('[data-finding-id]').forEach(card => {
      card.addEventListener('click', event => {
        if (event.target.matches('input')) return;
        inspectFinding(card.dataset.findingId);
      });
    });
    updateSelectionCount();
  }

  function updateSelectionCount() {
    const node = $('emergent-selection-count');
    if (node) node.textContent = `${selectedFindingIds.size} selected`;
  }

  async function inspectFinding(findingId) {
    const host = $('emergent-finding-detail');
    if (host) host.innerHTML = '<p class="placeholder">Loading complete stored finding…</p>';
    try {
      const result = await api(`/api/human-agent/emergent/findings/${encodeURIComponent(findingId)}`);
      if (!host) return;
      if (!result.ok) {
        host.textContent = result.error || 'Finding unavailable.';
        setStatus(`Finding unavailable: ${result.error || 'unknown error'}`, 'error');
        return;
      }
      const finding = result.finding || {};
      const raw = result.raw || {};
      const queryInput = $('research-query');
      if (queryInput && !queryInput.value) {
        queryInput.value = `${finding.emergent_ability || ''} ${finding.missing_wire || ''}`.trim();
      }
      host.innerHTML = `
        <div class="detail-head"><strong>${escape(finding.emergent_ability)}</strong><span>${escape(finding.status)}</span></div>
        <p><b>Missing wire:</b> ${escape(finding.missing_wire)}</p>
        <p><b>Required tests:</b> ${(finding.required_tests || []).map(escape).join(' · ') || 'not yet defined'}</p>
        <p><b>Patch authority:</b> exact local source spans and hashes only</p>
        <details><summary>Complete stored object</summary><pre>${escape(JSON.stringify(raw, null, 2))}</pre></details>`;
    } catch (error) {
      if (host) host.innerHTML = `<p class="placeholder">${escape(error.message || 'Finding request failed.')}</p>`;
      setStatus(`Finding request failed: ${error.message || 'unknown error'}`, 'error');
    }
  }

  async function compileRefactorPacket() {
    const objective = $('workflow-objective')?.value?.trim() || $('emergent-query')?.value?.trim() || '';
    if (!objective) {
      setStatus('Set the active refactor objective first.', 'warn');
      return;
    }
    const host = $('emergent-packet');
    setStatus('Compiling emergent findings into refactor evidence…');
    try {
      const result = await api('/api/human-agent/emergent/refactor-packet', {
        objective,
        finding_ids: [...selectedFindingIds],
        research_evidence_ids: [...selectedResearchEvidenceIds],
      });
      if (host) {
        const packet = result.packet || {};
        host.innerHTML = result.ok ? `
          <div class="detail-head"><strong>Refactor packet ${escape(packet.packet_id)}</strong><span>${(packet.selected_findings || []).length} findings</span></div>
          <p><b>Targets:</b> ${(packet.target_files || []).map(escape).join(' · ') || 'none'}</p>
          <p><b>Tests:</b> ${(packet.required_tests || []).map(escape).join(' · ') || 'must be defined'}</p>
          <p><b>Research gaps:</b> ${(packet.research_gaps || []).length}</p>
          <details open><summary>Acceptance criteria</summary><ul>${(packet.acceptance_criteria || []).map(item => `<li>${escape(item)}</li>`).join('')}</ul></details>
          <details><summary>Complete packet</summary><pre>${escape(JSON.stringify(packet, null, 2))}</pre></details>`
          : `<p class="placeholder">${escape(result.error || 'Packet creation failed.')}</p>`;
      }
      setStatus(result.ok ? 'Refactor evidence attached to the active Human Agent workflow.' : 'Packet creation failed.', result.ok ? 'ok' : 'error');
    } catch (error) {
      if (host) host.innerHTML = `<p class="placeholder">${escape(error.message || 'Packet request failed.')}</p>`;
      setStatus(`Packet request failed: ${error.message || 'unknown error'}`, 'error');
    }
  }

  async function runResearchSearch() {
    const provider = $('research-provider')?.value || 'arxiv';
    const query = $('research-query')?.value?.trim() || $('emergent-query')?.value?.trim() || '';
    if (!query) {
      setStatus('Enter a research query.', 'warn');
      return;
    }
    const includeSidecars = Boolean($('research-sidecars')?.checked);
    setStatus(`Searching ${provider} through the bounded research bridge…`);
    try {
      const result = await api('/api/human-agent/research/search', {
        provider,
        query,
        limit: 8,
        include_sidecars: includeSidecars,
        sidecar_limit: 2,
        finding_ids: [...selectedFindingIds],
      });
      const storedEvidenceId = result.stored_evidence?.evidence_id;
      if (storedEvidenceId) selectedResearchEvidenceIds.add(storedEvidenceId);
      renderResearchResults(result);
      setStatus(result.ok
        ? `${result.count || 0} ${provider} results stored as external evidence.`
        : `Research failed: ${result.error || 'unknown error'}`,
        result.ok ? 'ok' : 'error');
      await loadResearchEvidence();
    } catch (error) {
      renderResearchResults({ ok: false, error: error.message || 'Research request failed.' });
      setStatus(`Research request failed: ${error.message || 'unknown error'}`, 'error');
    }
  }

  function renderResearchResults(result) {
    const host = $('research-results');
    if (!host) return;
    if (!result.ok) {
      host.innerHTML = `<p class="placeholder">${escape(result.error || 'Research search failed.')}</p>`;
      return;
    }
    host.innerHTML = (result.results || []).map(item => {
      const isArxiv = item.provider === 'arxiv';
      const title = isArxiv ? item.title : item.full_name;
      const rawUrl = isArxiv ? item.entry_url : item.html_url;
      const url = safeHttpUrl(rawUrl);
      const description = isArxiv ? item.abstract : item.description;
      const metadata = isArxiv
        ? `${item.versioned_id || item.arxiv_id} · ${(item.categories || []).slice(0, 4).join(', ')}`
        : `${item.language || 'unknown language'} · ${Number(item.stargazers_count || 0)} stars · ${item.license || 'license unknown'}`;
      return `<article class="research-card">
        <strong>${escape(title)}</strong>
        <small>${escape(metadata)}</small>
        <p>${escape(description || '').slice(0, 650)}</p>
        ${url ? `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">Open canonical source</a>` : ''}
        ${item.sidecar ? `<details><summary>Untrusted sidecar excerpt</summary><pre>${escape((item.sidecar.text || '').slice(0, 4000))}</pre></details>` : ''}
      </article>`;
    }).join('') || '<p class="placeholder">No results.</p>';
  }

  async function loadResearchEvidence() {
    const host = $('research-evidence-list');
    if (!host) return;
    try {
      const result = await api('/api/human-agent/research/evidence?limit=20');
      if (!result.ok) {
        throw new Error(result.error || `HTTP ${result.http_status || 'error'}`);
      }
      host.innerHTML = (result.evidence || []).map(item => {
        const checked = selectedResearchEvidenceIds.has(item.evidence_id) ? 'checked' : '';
        return `<article class="evidence-index-card">
          <label class="finding-select"><input type="checkbox" ${checked} data-select-evidence="${escape(item.evidence_id)}"> attach</label>
          <strong>${escape(item.provider)} · ${escape(item.query)}</strong>
          <small>${Number(item.result_count || 0)} results · ${escape(item.evidence_id)}</small>
        </article>`;
      }).join('') || '<p class="placeholder">No research evidence stored yet.</p>';
      host.querySelectorAll('[data-select-evidence]').forEach(input => {
        input.addEventListener('change', event => {
          const evidenceId = event.currentTarget.dataset.selectEvidence;
          if (event.currentTarget.checked) selectedResearchEvidenceIds.add(evidenceId);
          else selectedResearchEvidenceIds.delete(evidenceId);
        });
      });
    } catch (error) {
      host.textContent = `Evidence index unavailable: ${error.message}`;
    }
  }

  // The generic tool dock cannot supply provider-specific research inputs. Route these
  // two cards into the dedicated surface before Jarvis's target-phase click handler runs.
  document.addEventListener('click', event => {
    const button = event.target.closest?.('[data-tool-id]');
    const toolId = button?.dataset?.toolId;
    if (!['emergent_refactor_workspace', 'research_forager'].includes(toolId)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    activateEmergentWorkspace();
    const objective = $('workflow-objective')?.value?.trim() || $('command-input')?.value?.trim() || '';
    if (toolId === 'emergent_refactor_workspace') {
      if ($('emergent-query') && objective) $('emergent-query').value = objective;
      searchFindings();
      return;
    }
    if ($('research-provider')) $('research-provider').value = 'arxiv';
    if ($('research-query') && objective) $('research-query').value = objective;
    setStatus('Choose arXiv or GitHub, refine the query, then search and store the evidence.', 'ok');
  }, true);

  $('emergent-search-btn')?.addEventListener('click', searchFindings);
  $('emergent-query')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') searchFindings();
  });
  $('emergent-packet-btn')?.addEventListener('click', compileRefactorPacket);
  $('research-search-btn')?.addEventListener('click', runResearchSearch);
  $('research-query')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') runResearchSearch();
  });

  loadRuns();
  loadResearchEvidence();
})();
