'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;
  const list = (items, formatter) => !items?.length
    ? '<p class="muted">Evidence has not been produced at this step.</p>'
    : `<ul class="result-list">${items.slice(0, 10).map(item => `<li>${formatter(item)}</li>`).join('')}</ul>`;

  S.renderCivicGuide = () => {
    const g = S.guide, summary = g.summary || {}, session = g.session || {};
    $('step-title').textContent = g.current_step?.title || 'Guided project';
    $('step-purpose').textContent = g.current_step?.purpose || '';
    $('human-question').textContent = g.current_step?.human_question || 'What should people decide next?';
    $('truth-notice').textContent = g.truth_notice || '';
    $('step-count').textContent = `Step ${Number(g.current_step_index || 0) + 1} of ${g.timeline?.length || 0}`;
    $('back-step').disabled = !g.can_go_back;
    $('advance-step').disabled = !g.can_advance;
    $('advance-step').textContent = g.can_advance ? 'Continue' : 'Project complete';
    $('timeline').innerHTML = (g.timeline || []).map(item => `<div class="timeline-step" data-status="${esc(item.status)}"><strong>${esc(item.title)}</strong><span>${esc(item.status)}</span></div>`).join('');
    $('needs-count').textContent = summary.needs_count || 0;
    $('offers-count').textContent = summary.offers_count || 0;
    $('workstreams-count').textContent = summary.workstream_count || 0;
    $('scenarios-count').textContent = summary.scenario_count || 0;
    $('needs-assets').innerHTML = list([...(session.needs || []), ...(session.offers || [])], item => esc(item.description || item.name || 'record'));
    $('workstreams').innerHTML = list(session.workstreams || [], item => esc(item.title || item.workstream_id || 'workstream'));
    $('scenarios').innerHTML = list(session.scenarios || [], item => `<strong>${esc(item.title || item.scenario_id)}</strong><br><span class="muted">${esc(item.description || '')}</span>`);
    $('consent').innerHTML = list([...(session.representation_gaps || []).map(description => ({description})), ...(session.objections || [])], item => esc(item.description || item.reason || 'response'));
    $('pilot').innerHTML = `<p>${esc(session.pilot?.authority_status || 'NOT_STARTED')}</p><p class="muted">Simulation evidence appears after the What-If step.</p>`;
    $('decision').innerHTML = Object.keys(session.decision_packet || {}).length ? '<p><strong>Decision packet ready</strong></p><p class="muted">Non-binding · human review required</p>' : '<p class="muted">The packet is assembled only after evidence, objections, and pilot constraints are visible.</p>';
    $('guide-evidence').textContent = JSON.stringify({current_step: g.current_step, summary, session, authority: {patch_authority: g.patch_authority, vsa_patch_authority: g.vsa_patch_authority}}, null, 2);
    const issue = g.demo_issue || {};
    $('issue-card').hidden = !g.demo_issue_available;
    $('issue-title').textContent = issue.title || 'Map presentation issue';
    $('issue-observed').textContent = issue.observed || '';
  };

  S.refreshMap = async () => {
    if (!S.sessionId) return;
    $('zoom-label').textContent = `Zoom ${S.mapZoom}`;
    const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/map?zoom=${encodeURIComponent(S.mapZoom)}`);
    if (!result.ok) {
      $('map-status').textContent = result.error || 'Map projection unavailable.';
      S.mapFeatures = [];
    } else {
      S.mapProjection = result;
      S.mapFeatures = result.geojson?.features || [];
      const suppressed = Object.values(result.suppressed_counts || {}).reduce((sum, value) => sum + Number(value || 0), 0);
      $('map-status').textContent = `${result.visible_feature_count} visible features · ${suppressed} policy-filtered · ${result.heatmap_visible ? 'safe aggregate heatmap available' : 'heatmap hidden at this scale'}`;
    }
    S.drawMap();
  };

  function coordinatePairs(value, output = []) {
    if (!Array.isArray(value)) return output;
    if (value.length >= 2 && typeof value[0] === 'number' && typeof value[1] === 'number') { output.push([value[0], value[1]]); return output; }
    value.forEach(child => coordinatePairs(child, output));
    return output;
  }

  function bounds(features) {
    const pairs = [];
    features.forEach(feature => coordinatePairs(feature.geometry?.coordinates, pairs));
    if (!pairs.length) return null;
    const xs = pairs.map(pair => pair[0]), ys = pairs.map(pair => pair[1]);
    return {west: Math.min(...xs), east: Math.max(...xs), south: Math.min(...ys), north: Math.max(...ys)};
  }

  S.resizeMap = () => {
    const canvas = $('map-canvas'), rect = canvas.getBoundingClientRect(), ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    canvas.getContext('2d').setTransform(ratio, 0, 0, ratio, 0, 0);
    S.drawMap();
  };

  S.drawMap = () => {
    const canvas = $('map-canvas'), context = canvas.getContext('2d'), rect = canvas.getBoundingClientRect();
    context.clearRect(0, 0, rect.width, rect.height); context.fillStyle = '#061015'; context.fillRect(0, 0, rect.width, rect.height);
    if (!S.mapFeatures.length) { context.fillStyle = '#92aab3'; context.font = '14px system-ui'; context.textAlign = 'center'; context.fillText('Advance to the governed map step to reveal synthetic civic infrastructure.', rect.width / 2, rect.height / 2); return; }
    const box = bounds(S.mapFeatures); if (!box) return;
    const padding = 70, spanX = Math.max(.00001, box.east - box.west), spanY = Math.max(.00001, box.north - box.south);
    const project = ([lon, lat]) => [padding + ((lon - box.west) / spanX) * Math.max(1, rect.width - padding * 2), rect.height - padding - ((lat - box.south) / spanY) * Math.max(1, rect.height - padding * 2)];
    S.hitRegions = [];
    context.strokeStyle = 'rgba(45,212,191,.08)';
    for (let x = 0; x < rect.width; x += 48) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, rect.height); context.stroke(); }
    for (let y = 0; y < rect.height; y += 48) { context.beginPath(); context.moveTo(0, y); context.lineTo(rect.width, y); context.stroke(); }
    S.mapFeatures.filter(f => /Polygon/.test(f.geometry?.type || '')).forEach(feature => {
      const rings = feature.geometry.type === 'Polygon' ? feature.geometry.coordinates : feature.geometry.coordinates.flat();
      rings.forEach(ring => { context.beginPath(); ring.forEach((coord, index) => { const [x, y] = project(coord); index ? context.lineTo(x, y) : context.moveTo(x, y); }); context.closePath(); context.fillStyle = 'rgba(45,212,191,.07)'; context.strokeStyle = 'rgba(45,212,191,.7)'; context.lineWidth = 2; context.fill(); context.stroke(); });
    });
    S.mapFeatures.filter(f => f.geometry?.type === 'Point').forEach(feature => {
      const [x, y] = project(feature.geometry.coordinates), type = feature.properties?.type || 'feature';
      const color = type === 'candidate' ? '#fbbf24' : type === 'transit' ? '#a78bfa' : type === 'service' ? '#5ee6a8' : '#38bdf8';
      context.beginPath(); context.arc(x, y, type === 'candidate' ? 9 : 7, 0, Math.PI * 2); context.fillStyle = color; context.shadowColor = color; context.shadowBlur = 18; context.fill(); context.shadowBlur = 0;
      context.fillStyle = '#ecf8fa'; context.font = '12px system-ui'; context.textAlign = 'left'; context.fillText(feature.properties?.name || type, x + 12, y + 4);
      S.hitRegions.push({x, y, radius: 18, feature});
    });
  };

  $('map-canvas').addEventListener('click', event => {
    const rect = event.currentTarget.getBoundingClientRect(), x = event.clientX - rect.left, y = event.clientY - rect.top;
    const hit = S.hitRegions.find(item => Math.hypot(item.x - x, item.y - y) <= item.radius); if (!hit) return;
    const p = hit.feature.properties || {};
    $('feature-inspector').innerHTML = `<p class="eyebrow">Selected feature</p><h3>${esc(p.name || 'Unnamed')}</h3><div class="inspector-grid"><span>Type: ${esc(p.type)}</span><span>Truth: ${esc(p.truth_class)}</span><span>Jurisdiction: ${esc(p.jurisdiction_id)}</span><span>Privacy: ${esc(p.privacy_class)}</span><span>Location: ${esc(p.location_class)}</span><span>Source: ${esc(p.source_ref)}</span></div>`;
  });
  $('zoom-in').addEventListener('click', () => { S.mapZoom = Math.min(18, S.mapZoom + 1); S.refreshMap(); });
  $('zoom-out').addEventListener('click', () => { S.mapZoom = Math.max(3, S.mapZoom - 1); S.refreshMap(); });
  $('reveal-candidate').addEventListener('click', () => { S.mapZoom = 12; S.refreshMap(); });
  $('record-response').addEventListener('click', async () => {
    const statement = $('response-statement').value.trim(); if (!statement || !S.sessionId) return;
    const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/respond`, {response_type: $('response-type').value, statement});
    if (result.ok) { $('response-statement').value = ''; S.applyGuide(result); }
  });
  window.addEventListener('resize', S.resizeMap);
  S.resizeMap();
})();
