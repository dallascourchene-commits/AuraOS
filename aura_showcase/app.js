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
  learningWorkspace: {
    tourActive: false,
    overviewActive: false,
    lastTrace: null,
  },
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

const LEARNING_STAGE_TITLES = [
  'Bulk intention',
  'Lexical addresses',
  'Routing and LEXC tags',
  'Six-slot packet',
  'Machine FST route',
  'Bounded worker handoff',
];

const LEARNING_TOUR_NOTES = [
  'Begin with an ordinary, complete human intention. No manual slots or prompt syntax are required.',
  'Aura assigns stable 12-bit lexical addresses locally. Unknown terms receive a deterministic fallback address.',
  'Aura exposes which words produced operation, domain, target, and output tags, plus the relevant LEXC vocabulary.',
  'The classified result is bound into DIR → ASP → CLASS → SUBJ → VOICE → STEM and a deterministic VSA digest.',
  'Hard routing gates choose the route, model policy, context class, reason, and verifier requirement before any worker is contacted.',
  'The replaceable worker receives compressed context and a bounded CODEMAP neighborhood—not unrestricted repository authority.',
];

const LEARNING_EXAMPLES = [
  {
    label: 'Coding repair',
    text: 'Find why the Civic overlay can become visually stale, localize the exact renderer and projection path, preserve privacy and existing tests, and prepare a review-only repair plan. Do not commit, push, or merge.',
  },
  {
    label: 'Learning audit',
    text: 'Audit how verified Learning Arena experiences become reusable procedures, show the verifier and human authority boundaries, and identify any missing tests without exposing private memory or changing the active grammar.',
  },
  {
    label: 'Architecture question',
    text: 'Explain how Aura routes bulk intention through the English lexicon, six-slot packet, FST hard gates, CODEMAP localization, Context Crusher, and a replaceable LLM worker while preserving exact-source authority.',
  },
];

S.setLearningWorkspaceStatus = message => {
  const node = S.$('learning-workspace-status');
  if (node) node.textContent = message;
};

S.showLearningStage = rawStage => {
  const stage = Math.max(0, Math.min(5, Number(rawStage) || 0));
  if (stage > 0 && !S.intentTrace) return;
  S.learningWorkspace.overviewActive = false;
  S.$('learning-view')?.classList.remove('is-overview');
  S.intentStage = stage;
  document.querySelectorAll('[data-learning-panel]').forEach(panel => {
    panel.classList.toggle('is-active', Number(panel.dataset.learningPanel) === stage);
  });
  document.querySelectorAll('[data-learning-stage]').forEach(button => {
    const index = Number(button.dataset.learningStage);
    button.disabled = index > 0 && !S.intentTrace;
    button.classList.toggle('is-active', index === stage);
    button.classList.toggle('is-complete', Boolean(S.intentTrace) && index !== stage);
  });
  const prefix = S.learningWorkspace.tourActive ? 'Suggested tour' : 'Workspace view';
  const title = S.$('learning-stage-title');
  if (title) title.textContent = `${prefix}: ${stage + 1}. ${LEARNING_STAGE_TITLES[stage]}`;
  const note = S.$('learning-tour-note');
  if (note) note.textContent = S.learningWorkspace.tourActive
    ? LEARNING_TOUR_NOTES[stage]
    : 'Explore any compiled view in any order, edit the intention, recompile, inspect topology, or export the trace.';
  const back = S.$('learning-back');
  const next = S.$('learning-next');
  if (back) {
    back.disabled = stage === 0;
    back.textContent = S.learningWorkspace.tourActive ? 'Previous tour stop' : 'Previous view';
  }
  if (next) {
    next.disabled = !S.intentTrace || stage === 5;
    next.textContent = S.learningWorkspace.tourActive ? 'Next tour stop' : 'Next view';
  }
  if (stage === 5 && S.resizeLearningTopology) setTimeout(S.resizeLearningTopology, 20);
};

S.unlockLearningWorkspace = trace => {
  if (!trace?.ok) return;
  S.learningWorkspace.lastTrace = trace;
  document.querySelectorAll('[data-learning-stage]').forEach(button => { button.disabled = false; });
  ['learning-tour-start', 'learning-overview', 'learning-copy-trace', 'learning-download-trace', 'learning-copy-handoff']
    .forEach(id => { const button = S.$(id); if (button) button.disabled = false; });
  S.setLearningWorkspaceStatus('Compiled workspace ready · every view is now available');
  S.showLearningStage(S.learningWorkspace.tourActive ? 0 : 4);
};

S.startLearningTour = () => {
  S.learningWorkspace.tourActive = true;
  const start = S.$('learning-tour-start');
  const exit = S.$('learning-tour-exit');
  if (start) start.hidden = true;
  if (exit) exit.hidden = false;
  S.setLearningWorkspaceStatus(S.intentTrace ? 'Suggested tour active' : 'Suggested tour ready · compile the intention to continue');
  S.showLearningStage(0);
};

S.exitLearningTour = () => {
  S.learningWorkspace.tourActive = false;
  const start = S.$('learning-tour-start');
  const exit = S.$('learning-tour-exit');
  if (start) start.hidden = false;
  if (exit) exit.hidden = true;
  S.setLearningWorkspaceStatus(S.intentTrace ? 'Free workspace mode · browse any compiled view' : 'Free workspace mode · enter any intention');
  S.showLearningStage(S.intentStage);
};

S.toggleLearningOverview = () => {
  if (!S.intentTrace) return;
  S.learningWorkspace.overviewActive = !S.learningWorkspace.overviewActive;
  const active = S.learningWorkspace.overviewActive;
  S.$('learning-view')?.classList.toggle('is-overview', active);
  const button = S.$('learning-overview');
  if (button) button.textContent = active ? 'Return to single view' : 'View all results';
  if (active) {
    document.querySelectorAll('[data-learning-panel]').forEach(panel => panel.classList.add('is-active'));
    document.querySelectorAll('[data-learning-stage]').forEach(stage => stage.classList.remove('is-active'));
    const title = S.$('learning-stage-title');
    if (title) title.textContent = 'Workspace overview: complete compiled intention trace';
    const note = S.$('learning-tour-note');
    if (note) note.textContent = 'All routing evidence is visible together. Individual views remain available from the navigation rail.';
    if (S.resizeLearningTopology) setTimeout(S.resizeLearningTopology, 20);
  } else {
    S.showLearningStage(S.intentStage);
  }
};

S.copyText = async (text, successMessage) => {
  const value = String(text || '');
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
  } catch (_error) {
    const area = document.createElement('textarea');
    area.value = value;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    document.execCommand('copy');
    area.remove();
  }
  S.setLearningWorkspaceStatus(successMessage);
};

S.downloadLearningTrace = () => {
  if (!S.intentTrace) return;
  const blob = new Blob([JSON.stringify(S.intentTrace, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `aura-intent-trace-${Date.now()}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  S.setLearningWorkspaceStatus('Compiled trace exported as JSON');
};

S.watchForCompiledIntent = previousTrace => {
  let attempts = 0;
  const timer = window.setInterval(() => {
    attempts += 1;
    if (S.intentTrace && S.intentTrace !== previousTrace) {
      window.clearInterval(timer);
      S.unlockLearningWorkspace(S.intentTrace);
    } else if (attempts >= 300) {
      window.clearInterval(timer);
      S.setLearningWorkspaceStatus('Compilation did not complete. Review the visible error and try again.');
    }
  }, 50);
};

S.setupLearningWorkspace = () => {
  const view = S.$('learning-view');
  const rail = S.$('learning-rail');
  const input = S.$('bulk-intent-input');
  if (!view || !rail || !input || view.dataset.workspaceReady === 'true') return;
  view.dataset.workspaceReady = 'true';

  const hero = view.querySelector('.learning-hero');
  const eyebrow = hero?.querySelector('.eyebrow');
  const heading = hero?.querySelector('h1');
  const lede = hero?.querySelector('.lede');
  if (eyebrow) eyebrow.textContent = 'Sovereign Learning Arena · usable deterministic intent workspace';
  if (heading) heading.textContent = 'Use Aura freely—or follow the suggested tour.';
  if (lede) lede.textContent = 'Enter any bulk intention, compile it locally, then inspect lexical addresses, routing tags, six-slot structure, hard-gate decisions, CODEMAP topology, and the bounded worker handoff in any order.';
  const reset = S.$('learning-reset');
  if (reset) reset.textContent = 'Clear workspace';

  const railCard = rail.closest('.learning-rail-card');
  const railEyebrow = railCard?.querySelector('.eyebrow');
  if (railEyebrow) railEyebrow.textContent = 'Usable workspace · optional suggested tour';

  const toolbar = document.createElement('div');
  toolbar.className = 'learning-workspace-toolbar';
  toolbar.innerHTML = `
    <div class="learning-mode-actions">
      <button id="learning-tour-start" type="button" class="primary">Start suggested tour</button>
      <button id="learning-tour-exit" type="button" class="secondary" hidden>Exit tour</button>
      <button id="learning-overview" type="button" class="secondary" disabled>View all results</button>
    </div>
    <div class="learning-export-actions">
      <button id="learning-copy-handoff" type="button" disabled>Copy worker handoff</button>
      <button id="learning-copy-trace" type="button" disabled>Copy trace JSON</button>
      <button id="learning-download-trace" type="button" disabled>Export JSON</button>
    </div>
    <span id="learning-workspace-status" class="pill">Free workspace mode · enter any intention</span>`;
  railCard?.insertBefore(toolbar, rail);

  const tourNote = document.createElement('div');
  tourNote.id = 'learning-tour-note';
  tourNote.className = 'learning-tour-note';
  tourNote.textContent = 'Explore freely after compilation, or start the suggested tour for a narrated path through Aura’s routing evidence.';
  railCard?.appendChild(tourNote);

  const examples = document.createElement('div');
  examples.className = 'learning-examples';
  examples.innerHTML = `<span>Try an example:</span>${LEARNING_EXAMPLES.map((item, index) => `<button type="button" data-learning-example="${index}">${S.esc(item.label)}</button>`).join('')}`;
  input.insertAdjacentElement('afterend', examples);
  examples.querySelectorAll('[data-learning-example]').forEach(button => button.addEventListener('click', () => {
    const example = LEARNING_EXAMPLES[Number(button.dataset.learningExample)];
    if (!example) return;
    input.value = example.text;
    input.focus();
    S.setLearningWorkspaceStatus(`${example.label} example loaded · edit or compile it`);
  }));

  const replaceListenerNode = (id, handler) => {
    const oldNode = S.$(id);
    if (!oldNode) return null;
    const node = oldNode.cloneNode(true);
    oldNode.replaceWith(node);
    node.addEventListener('click', handler);
    return node;
  };

  document.querySelectorAll('[data-learning-stage]').forEach(oldButton => {
    const button = oldButton.cloneNode(true);
    oldButton.replaceWith(button);
    button.disabled = Number(button.dataset.learningStage) > 0 && !S.intentTrace;
    button.addEventListener('click', () => S.showLearningStage(Number(button.dataset.learningStage)));
  });
  replaceListenerNode('learning-back', () => S.showLearningStage(S.intentStage - 1));
  replaceListenerNode('learning-next', () => S.showLearningStage(S.intentStage + 1));

  S.$('learning-tour-start')?.addEventListener('click', S.startLearningTour);
  S.$('learning-tour-exit')?.addEventListener('click', S.exitLearningTour);
  S.$('learning-overview')?.addEventListener('click', S.toggleLearningOverview);
  S.$('learning-copy-trace')?.addEventListener('click', () => S.copyText(JSON.stringify(S.intentTrace, null, 2), 'Compiled trace copied'));
  S.$('learning-download-trace')?.addEventListener('click', S.downloadLearningTrace);
  S.$('learning-copy-handoff')?.addEventListener('click', () => S.copyText(S.intentTrace?.agent_handoff?.compressed_context, 'Bounded worker handoff copied'));

  S.$('learning-compile')?.addEventListener('click', () => {
    const previous = S.intentTrace;
    S.setLearningWorkspaceStatus('Compiling locally · no model called');
    S.watchForCompiledIntent(previous);
  });
  reset?.addEventListener('click', () => window.setTimeout(() => {
    S.learningWorkspace.tourActive = false;
    S.learningWorkspace.overviewActive = false;
    S.learningWorkspace.lastTrace = null;
    view.classList.remove('is-overview');
    S.$('learning-tour-start').hidden = false;
    S.$('learning-tour-exit').hidden = true;
    S.$('learning-overview').textContent = 'View all results';
    document.querySelectorAll('[data-learning-stage]').forEach(button => { button.disabled = Number(button.dataset.learningStage) > 0; });
    ['learning-overview', 'learning-copy-trace', 'learning-download-trace', 'learning-copy-handoff']
      .forEach(id => { const button = S.$(id); if (button) button.disabled = true; });
    S.setLearningWorkspaceStatus('Free workspace mode · enter any intention');
    S.showLearningStage(0);
  }, 0));

  if (S.intentTrace) S.unlockLearningWorkspace(S.intentTrace);
  else S.showLearningStage(0);
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
  S.setupLearningWorkspace();
  if (status.guide?.ok) S.applyGuide(status.guide);
  else await S.restartProject();
};

window.addEventListener('DOMContentLoaded', () => S.initialize().catch(error => S.showCivicError(error.message)));
