'use strict';

(() => {
  const S = window.Showcase, $ = S.$, esc = S.esc;
  const TILE_SIZE = 256;
  const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  const list = (items, formatter) => !items?.length
    ? '<p class="muted">Evidence has not been produced at this step.</p>'
    : `<ul class="result-list">${items.slice(0, 10).map(item => `<li>${formatter(item)}</li>`).join('')}</ul>`;

  function slotText(action) {
    const slots = action.intent_slots || {};
    return ['DIR', 'ASP', 'CLASS', 'SUBJ', 'VOICE', 'STEM']
      .map(key => `${key}:${slots[key] || '—'}`).join(' · ');
  }

  function renderRouteMenu() {
    const actions = S.guide?.available_actions || [];
    $('route-notice').textContent = S.guide?.route_notice || '';
    $('route-actions').innerHTML = actions.map((action, index) => {
      const activates = action.activates?.length ? `Activates: ${action.activates.join(', ')}` : 'Client-side governed interaction';
      return `<button class="route-action" data-route-index="${index}" data-effect="${esc(action.effect)}">
        <span class="route-rank">${index + 1}</span>
        <span class="route-copy"><strong>${esc(action.label)}</strong><small>${esc(action.why_available)}</small><code>${esc(slotText(action))}</code></span>
        <span class="route-score"><b>${Math.round(Number(action.route_weight || 0) * 100)}</b><small>route</small></span>
        <span class="route-activates">${esc(activates)}</span>
      </button>`;
    }).join('') || '<p class="muted">No actions are admitted at this gate.</p>';

    $('blocked-actions').innerHTML = (S.guide?.blocked_actions || []).map(item => `<article class="blocked-action"><strong>${esc(item.label)}</strong><span>${esc(item.reason)}</span></article>`).join('');
    $('route-actions').querySelectorAll('[data-route-index]').forEach(button => button.addEventListener('click', () => {
      const action = actions[Number(button.dataset.routeIndex)];
      if (action) executeRouteAction(action);
    }));
  }

  async function executeRouteAction(action) {
    const args = action.args || {};
    switch (action.effect) {
      case 'ADVANCE':
        return S.advance();
      case 'BACK':
        return S.back();
      case 'INSPECT_EVIDENCE': {
        const details = $('evidence-details');
        details.open = true;
        details.scrollIntoView({behavior: 'smooth', block: 'center'});
        return;
      }
      case 'FOCUS_TEST_COMMUNITY':
        S.mapCenter = {lon: Number(args.center?.[0] ?? S.TEST_COMMUNITY_CENTER.lon), lat: Number(args.center?.[1] ?? S.TEST_COMMUNITY_CENTER.lat)};
        S.mapZoom = Number(args.zoom || 14);
        return S.refreshMap();
      case 'REVEAL_CANDIDATE':
        S.mapCenter = {lon: Number(args.center?.[0] ?? -97.176), lat: Number(args.center?.[1] ?? 49.889)};
        S.mapZoom = Number(args.zoom || 12);
        return S.refreshMap();
      case 'PREFILL_RESPONSE':
        $('response-type').value = args.response_type || 'CONSENT_WITH_RESERVATION';
        $('response-statement').value = args.statement || '';
        $('response-statement').focus();
        $('response-statement').scrollIntoView({behavior: 'smooth', block: 'center'});
        return;
      case 'OPEN_HANDOFF':
        return $('investigate-issue').click();
      default:
        return S.showCivicError(`Unknown guided action: ${action.effect}`);
    }
  }

  S.renderCivicGuide = () => {
    const g = S.guide, summary = g.summary || {}, session = g.session || {};
    $('step-title').textContent = g.current_step?.title || 'Guided project';
    $('step-purpose').textContent = g.current_step?.purpose || '';
    $('human-question').textContent = g.current_step?.human_question || 'What should people decide next?';
    $('truth-notice').textContent = g.truth_notice || '';
    $('step-count').textContent = `Step ${Number(g.current_step_index || 0) + 1} of ${g.timeline?.length || 0}`;
    $('back-step').disabled = !g.can_go_back;
    $('advance-step').disabled = !g.can_advance;
    const advanceAction = (g.available_actions || []).find(action => action.effect === 'ADVANCE');
    $('advance-step').textContent = advanceAction?.label || (g.can_advance ? 'Run next governed stage' : 'Project complete');
    $('timeline').innerHTML = (g.timeline || []).map(item => `<div class="timeline-step" data-status="${esc(item.status)}"><strong>${esc(item.title)}</strong><span>${esc(item.status)}</span></div>`).join('');
    $('needs-count').textContent = summary.needs_count || 0;
    $('offers-count').textContent = summary.offers_count || 0;
    $('workstreams-count').textContent = summary.workstream_count || 0;
    $('scenarios-count').textContent = summary.scenario_count || 0;
    $('needs-assets').innerHTML = list([...(session.needs || []), ...(session.offers || [])], item => esc(item.description || item.name || 'record'));
    $('workstreams').innerHTML = list(session.workstreams || [], item => esc(item.title || item.workstream_id || 'workstream'));
    $('scenarios').innerHTML = list(session.scenarios || [], item => `<strong>${esc(item.title || item.scenario_id)}</strong><br><span class="muted">${esc(item.description || '')}</span>`);
    $('consent').innerHTML = list([...(session.representation_gaps || []).map(description => ({description})), ...(session.objections || []), ...(session.guide_responses || [])], item => esc(item.description || item.reason || item.statement || 'response'));
    $('pilot').innerHTML = `<p>${esc(session.pilot?.authority_status || 'NOT_STARTED')}</p><p class="muted">Simulation evidence appears after the What-If step.</p>`;
    $('decision').innerHTML = Object.keys(session.decision_packet || {}).length ? '<p><strong>Decision packet ready</strong></p><p class="muted">Non-binding · human review required</p>' : '<p class="muted">The packet is assembled only after evidence, objections, and pilot constraints are visible.</p>';
    $('guide-evidence').textContent = JSON.stringify({current_step: g.current_step, available_actions: g.available_actions, blocked_actions: g.blocked_actions, summary, session, authority: {patch_authority: g.patch_authority, vsa_patch_authority: g.vsa_patch_authority}}, null, 2);
    const issue = g.demo_issue || {};
    $('issue-card').hidden = !g.demo_issue_available;
    $('issue-title').textContent = issue.title || 'Map presentation issue';
    $('issue-observed').textContent = issue.observed || '';
    renderRouteMenu();
  };

  function mapGateOpen() {
    const explore = (S.guide?.timeline || []).find(item => item.step_id === 'EXPLORE_MAP');
    return explore ? Number(S.guide?.current_step_index || 0) >= Number(explore.index) : false;
  }

  function updateMapStatus() {
    if (!mapGateOpen()) {
      $('map-status').textContent = `${S.basemapLoaded ? 'Winnipeg street basemap ready' : 'Winnipeg street basemap loading'} · governed Civic overlay locked until Explore Map`;
      return;
    }
    const result = S.mapProjection || {};
    const suppressed = Object.values(result.suppressed_counts || {}).reduce((sum, value) => sum + Number(value || 0), 0);
    const basemap = S.basemapLoaded ? 'OpenStreetMap streets loaded' : (S.basemapFailed ? 'offline governed-grid fallback' : 'street basemap loading');
    $('map-status').textContent = `${result.visible_feature_count || 0} visible synthetic features · ${suppressed} policy-filtered · ${basemap}`;
  }

  S.refreshMap = async () => {
    $('zoom-label').textContent = `Zoom ${S.mapZoom}`;
    renderBasemap();
    if (!S.sessionId || !mapGateOpen()) {
      S.mapProjection = null;
      S.mapFeatures = [];
      S.drawMap();
      updateMapStatus();
      return;
    }
    const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/map?zoom=${encodeURIComponent(S.mapZoom)}`);
    if (!result.ok) {
      $('map-status').textContent = result.error || 'Map projection unavailable.';
      S.mapProjection = null;
      S.mapFeatures = [];
    } else {
      S.mapProjection = result;
      S.mapFeatures = result.geojson?.features || [];
    }
    S.drawMap();
    updateMapStatus();
  };

  function worldPoint(lon, lat, zoom) {
    const scale = TILE_SIZE * (2 ** zoom);
    const boundedLat = Math.max(-85.05112878, Math.min(85.05112878, lat));
    const sin = Math.sin(boundedLat * Math.PI / 180);
    return {
      x: ((lon + 180) / 360) * scale,
      y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * scale,
    };
  }

  function screenPoint(lon, lat, rect) {
    const center = worldPoint(S.mapCenter.lon, S.mapCenter.lat, S.mapZoom);
    const point = worldPoint(lon, lat, S.mapZoom);
    return [rect.width / 2 + point.x - center.x, rect.height / 2 + point.y - center.y];
  }

  function renderBasemap() {
    const host = $('basemap-tiles');
    const shell = $('map-shell');
    const rect = shell.getBoundingClientRect();
    host.innerHTML = '';
    if (!rect.width || !rect.height || navigator.onLine === false) {
      S.basemapFailed = true;
      S.basemapLoaded = false;
      updateMapStatus();
      return;
    }
    const zoom = Math.max(3, Math.min(18, Math.round(S.mapZoom)));
    const tileCount = 2 ** zoom;
    const center = worldPoint(S.mapCenter.lon, S.mapCenter.lat, zoom);
    const left = center.x - rect.width / 2;
    const top = center.y - rect.height / 2;
    const minX = Math.floor(left / TILE_SIZE);
    const maxX = Math.floor((left + rect.width) / TILE_SIZE);
    const minY = Math.max(0, Math.floor(top / TILE_SIZE));
    const maxY = Math.min(tileCount - 1, Math.floor((top + rect.height) / TILE_SIZE));
    let pending = 0;
    let loaded = 0;
    for (let tileY = minY; tileY <= maxY; tileY += 1) {
      for (let tileX = minX; tileX <= maxX; tileX += 1) {
        pending += 1;
        const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
        const image = document.createElement('img');
        image.alt = '';
        image.setAttribute('aria-hidden', 'true');
        image.decoding = 'async';
        image.loading = 'eager';
        image.src = OSM_TILE_URL.replace('{z}', zoom).replace('{x}', wrappedX).replace('{y}', tileY);
        image.style.left = `${tileX * TILE_SIZE - left}px`;
        image.style.top = `${tileY * TILE_SIZE - top}px`;
        image.addEventListener('load', () => {
          loaded += 1;
          S.basemapLoaded = true;
          S.basemapFailed = false;
          if (loaded === pending || loaded === 1) updateMapStatus();
        });
        image.addEventListener('error', () => {
          if (!loaded) {
            S.basemapFailed = true;
            S.basemapLoaded = false;
            updateMapStatus();
            S.drawMap();
          }
        });
        host.appendChild(image);
      }
    }
  }

  function polygonRings(feature) {
    if (feature.geometry?.type === 'Polygon') return feature.geometry.coordinates || [];
    if (feature.geometry?.type === 'MultiPolygon') return (feature.geometry.coordinates || []).flat();
    return [];
  }

  S.resizeMap = () => {
    const canvas = $('map-canvas'), rect = canvas.getBoundingClientRect(), ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    canvas.getContext('2d').setTransform(ratio, 0, 0, ratio, 0, 0);
    renderBasemap();
    S.drawMap();
  };

  S.drawMap = () => {
    const canvas = $('map-canvas'), context = canvas.getContext('2d'), rect = canvas.getBoundingClientRect();
    context.clearRect(0, 0, rect.width, rect.height);
    if (!S.basemapLoaded) {
      context.fillStyle = '#061015'; context.fillRect(0, 0, rect.width, rect.height);
      context.strokeStyle = 'rgba(45,212,191,.10)';
      for (let x = 0; x < rect.width; x += 48) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, rect.height); context.stroke(); }
      for (let y = 0; y < rect.height; y += 48) { context.beginPath(); context.moveTo(0, y); context.lineTo(rect.width, y); context.stroke(); }
    }
    if (!mapGateOpen()) {
      context.fillStyle = 'rgba(7,16,20,.72)'; context.fillRect(0, 0, rect.width, rect.height);
      context.fillStyle = '#d8edf0'; context.font = '600 16px system-ui'; context.textAlign = 'center';
      context.fillText('Winnipeg basemap available', rect.width / 2, rect.height / 2 - 10);
      context.fillStyle = '#92aab3'; context.font = '13px system-ui';
      context.fillText('Advance to Explore Map to admit the synthetic Civic overlay.', rect.width / 2, rect.height / 2 + 18);
      return;
    }

    S.hitRegions = [];
    S.mapFeatures.filter(feature => /Polygon/.test(feature.geometry?.type || '')).forEach(feature => {
      const type = feature.properties?.type || 'boundary';
      polygonRings(feature).forEach(ring => {
        context.beginPath();
        ring.forEach((coord, index) => {
          const [x, y] = screenPoint(coord[0], coord[1], rect);
          index ? context.lineTo(x, y) : context.moveTo(x, y);
        });
        context.closePath();
        context.fillStyle = type === 'neighbourhood' ? 'rgba(251,191,36,.16)' : 'rgba(45,212,191,.08)';
        context.strokeStyle = type === 'neighbourhood' ? 'rgba(251,191,36,.95)' : 'rgba(45,212,191,.75)';
        context.lineWidth = type === 'neighbourhood' ? 3 : 2;
        context.fill(); context.stroke();
      });
      const coords = polygonRings(feature)[0] || [];
      if (coords.length) {
        const center = coords.reduce((sum, coord) => [sum[0] + coord[0], sum[1] + coord[1]], [0, 0]).map(value => value / coords.length);
        const [x, y] = screenPoint(center[0], center[1], rect);
        context.fillStyle = '#fff4c2'; context.font = '700 12px system-ui'; context.textAlign = 'center';
        context.fillText(feature.properties?.name || type, x, y);
      }
    });

    S.mapFeatures.filter(feature => feature.geometry?.type === 'Point').forEach(feature => {
      const [x, y] = screenPoint(feature.geometry.coordinates[0], feature.geometry.coordinates[1], rect);
      if (x < -30 || y < -30 || x > rect.width + 30 || y > rect.height + 30) return;
      const type = feature.properties?.type || 'feature';
      const color = type === 'candidate' ? '#fbbf24' : type === 'transit' ? '#a78bfa' : type === 'service' ? '#5ee6a8' : '#38bdf8';
      context.beginPath(); context.arc(x, y, type === 'candidate' ? 10 : 8, 0, Math.PI * 2); context.fillStyle = color; context.shadowColor = color; context.shadowBlur = 18; context.fill(); context.shadowBlur = 0;
      context.fillStyle = '#071014'; context.strokeStyle = '#ecf8fa'; context.lineWidth = 3; context.stroke();
      context.fillStyle = '#ffffff'; context.font = '700 12px system-ui'; context.textAlign = 'left'; context.shadowColor = '#071014'; context.shadowBlur = 4;
      context.fillText(feature.properties?.name || type, x + 13, y + 4); context.shadowBlur = 0;
      S.hitRegions.push({x, y, radius: 20, feature});
    });
  };

  $('map-canvas').addEventListener('click', event => {
    const rect = event.currentTarget.getBoundingClientRect(), x = event.clientX - rect.left, y = event.clientY - rect.top;
    const hit = S.hitRegions.find(item => Math.hypot(item.x - x, item.y - y) <= item.radius); if (!hit) return;
    const p = hit.feature.properties || {};
    $('feature-inspector').innerHTML = `<p class="eyebrow">Selected synthetic feature</p><h3>${esc(p.name || 'Unnamed')}</h3><div class="inspector-grid"><span>Type: ${esc(p.type)}</span><span>Truth: ${esc(p.truth_class)}</span><span>Jurisdiction: ${esc(p.jurisdiction_id)}</span><span>Privacy: ${esc(p.privacy_class)}</span><span>Location: ${esc(p.location_class)}</span><span>Source: ${esc(p.source_ref)}</span></div>`;
  });
  $('zoom-in').addEventListener('click', () => { S.mapZoom = Math.min(18, S.mapZoom + 1); S.refreshMap(); });
  $('zoom-out').addEventListener('click', () => { S.mapZoom = Math.max(3, S.mapZoom - 1); S.refreshMap(); });
  $('focus-community').addEventListener('click', () => { S.mapCenter = {...S.TEST_COMMUNITY_CENTER}; S.mapZoom = 14; S.refreshMap(); });
  $('reveal-candidate').addEventListener('click', () => { S.mapCenter = {lon: -97.176, lat: 49.889}; S.mapZoom = 12; S.refreshMap(); });
  $('record-response').addEventListener('click', async () => {
    const statement = $('response-statement').value.trim(); if (!statement || !S.sessionId) return;
    const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/respond`, {response_type: $('response-type').value, statement});
    if (result.ok) { $('response-statement').value = ''; S.applyGuide(result); }
  });
  window.addEventListener('online', () => { S.basemapFailed = false; S.refreshMap(); });
  window.addEventListener('offline', () => { S.basemapFailed = true; S.basemapLoaded = false; S.drawMap(); updateMapStatus(); });
  window.addEventListener('resize', S.resizeMap);
  S.resizeMap();
})();
