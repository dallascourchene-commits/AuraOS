'use strict';

window.Showcase = {
  INITIAL_MAP_ZOOM: 11,
  DEFAULT_MAP_CENTER: {lon: -97.152, lat: 49.895},
  TEST_COMMUNITY_CENTER: {lon: -97.165, lat: 49.8865},
  DEFAULT_TILE_URL_TEMPLATE: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  tileUrlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  guide: null,
  sessionId: '',
  mapZoom: 11,
  mapCenter: {lon: -97.152, lat: 49.895},
  mapProjection: null,
  mapFeatures: [],
  hitRegions: [],
  basemapLoaded: false,
  basemapFailed: false,
  handoff: null,
  workflow: null,
  humanGuide: null,
  intentTrace: null,
  intentStage: 0,
};

const S = window.Showcase;
S.$ = id => document.getElementById(id);
S.esc = value => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');

S.api = async (path, body) => {
  const options = body === undefined ? {} : {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const payload = await response.json();
  payload.http_status = response.status;
  return payload;
};

S.activateTab = name => {
  document.querySelectorAll('.tab').forEach(node => node.classList.toggle('is-active', node.dataset.tab === name));
  S.$('civic-view')?.classList.toggle('is-active', name === 'civic');
  S.$('human-view')?.classList.toggle('is-active', name === 'human');
  S.$('learning-view')?.classList.toggle('is-active', name === 'learning');
  if (name === 'civic' && S.resizeMap) setTimeout(S.resizeMap, 20);
  if (name === 'human' && S.resizeTopology) setTimeout(S.resizeTopology, 20);
  if (name === 'learning' && S.resizeLearningTopology) setTimeout(S.resizeLearningTopology, 20);
};

S.applyGuide = guide => {
  S.guide = guide;
  S.sessionId = guide.session?.session_id || '';
  if (S.renderCivicGuide) S.renderCivicGuide();
  if (S.refreshMap) S.refreshMap();
};

S.restartProject = async () => {
  const result = await S.api('/api/showcase/projects/winnipeg_pathways/start', {});
  if (!result.ok) throw new Error(result.error || 'Unable to start project');
  S.mapZoom = S.INITIAL_MAP_ZOOM;
  S.mapCenter = {...S.DEFAULT_MAP_CENTER};
  S.basemapLoaded = false;
  S.basemapFailed = false;
  S.handoff = null;
  S.workflow = null;
  S.humanGuide = null;
  S.applyGuide(result);
  if (S.renderHandoff) S.renderHandoff();
  if (S.renderWorkflow) S.renderWorkflow();
  if (S.renderHumanGuide) S.renderHumanGuide();
};

S.advance = async () => {
  if (!S.sessionId) return;
  const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/advance`, {});
  if (!result.ok) return S.showCivicError(result.error || 'Step execution failed');
  S.applyGuide(result);
};

S.back = async () => {
  if (!S.sessionId) return;
  const result = await S.api(`/api/showcase/sessions/${encodeURIComponent(S.sessionId)}/back`, {});
  if (result.ok) S.applyGuide(result);
};

S.showCivicError = message => {
  if (S.$('truth-notice')) S.$('truth-notice').textContent = message;
};

S.initialize = async () => {
  document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => S.activateTab(button.dataset.tab)));
  S.$('return-civic')?.addEventListener('click', () => S.activateTab('civic'));
  S.$('restart-project')?.addEventListener('click', S.restartProject);
  S.$('advance-step')?.addEventListener('click', S.advance);
  S.$('back-step')?.addEventListener('click', S.back);
  const status = await S.api('/api/showcase/status');
  S.tileUrlTemplate = status.basemap_tile_url_template || S.DEFAULT_TILE_URL_TEMPLATE;
  const intentInput = S.$('bulk-intent-input');
  if (intentInput && !intentInput.value.trim()) intentInput.value = status.default_bulk_intent || '';
  if (status.guide?.ok) S.applyGuide(status.guide);
  else await S.restartProject();
};

window.addEventListener('DOMContentLoaded', () => S.initialize().catch(error => S.showCivicError(error.message)));
