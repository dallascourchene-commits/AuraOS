'use strict';

(() => {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  const S = window.Showcase;
  if (!S || typeof S.api !== 'function') return;

  const originalApi = S.api.bind(S);
  const adapter = {
    identityHandle: '',
    identitySummary: null,
    identityBrokerAvailable: false,
  };

  const $ = id => (
    typeof document !== 'undefined' ? document.getElementById(id) : null
  );
  const setLegacyIdentityVisible = visible => {
    const legacyIdentity = $('foundry-identity');
    const card = legacyIdentity?.closest('.foundry-card');
    if (!card) return;
    card.hidden = !visible;
    card.dataset.legacyIdentityFallback = String(visible);
  };
  const renderIdentity = value => {
    const node = $('construction-foundry-identity-summary');
    if (!node) return;
    node.textContent = value
      ? JSON.stringify(value, null, 2)
      : 'Trusted server identity is unavailable; legacy B15 flow remains available.';
  };

  const loadIdentity = async () => {
    const result = await originalApi('/api/showcase/live-repair/identity/current');
    if (!result.ok) throw new Error(result.error || 'Trusted current identity is unavailable');
    adapter.identityHandle = String(result.identity_handle || '');
    adapter.identitySummary = result;
    adapter.identityBrokerAvailable = Boolean(adapter.identityHandle);
    setLegacyIdentityVisible(!adapter.identityBrokerAvailable);
    renderIdentity({
      identity_digest: result.identity_digest,
      intent_revision_id: result.intent_revision_id,
      repository_head: result.repository_head,
      source_tree_digest: result.source_tree_digest,
      runtime_profile_digest: result.runtime_profile_digest,
      verifier_id: result.verifier_id,
      currency: result.currency,
      full_identity_returned: result.full_identity_returned,
    });
    return result;
  };

  const requiredAssets = () => {
    const raw = $('construction-foundry-required-assets')?.value || '[]';
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (_error) {
      throw new Error('Required assets must contain valid JSON.');
    }
    if (!Array.isArray(parsed)) throw new Error('Required assets must be a JSON array.');
    const paths = new Map();
    return parsed.map((item, index) => {
      if (!item || typeof item !== 'object' || Array.isArray(item)) {
        throw new Error(`Required asset ${index + 1} must be an object.`);
      }
      const path = String(item.path || '').trim();
      const sha256 = String(item.sha256 || '').trim().toLowerCase();
      if (!path || !/^[0-9a-f]{64}$/.test(sha256)) {
        throw new Error(`Required asset ${index + 1} needs path and 64-character sha256.`);
      }
      if (paths.has(path)) {
        const detail = paths.get(path) === sha256 ? 'duplicate path' : 'conflicting hashes';
        throw new Error(`Required asset ${index + 1} has ${detail}: ${path}.`);
      }
      paths.set(path, sha256);
      return {path, sha256};
    });
  };

  const ensureIdentity = async () => {
    if (adapter.identityHandle) return adapter.identityHandle;
    if (!adapter.identityBrokerAvailable && adapter.identitySummary) return '';
    try {
      await loadIdentity();
    } catch (error) {
      adapter.identityHandle = '';
      adapter.identityBrokerAvailable = false;
      adapter.identitySummary = {ok: false, error: error.message, legacy_fallback: true};
      setLegacyIdentityVisible(true);
      renderIdentity(adapter.identitySummary);
      return '';
    }
    return adapter.identityHandle;
  };

  const identityHandleExpired = result => (
    result
    && result.ok === false
    && /(?:trusted identity handle is missing or expired|bilateral identity.*stale|identity handle.*stale)/i
      .test(String(result.error || ''))
  );

  S.api = async (path, body) => {
    if (body === undefined) return originalApi(path);
    const next = body && typeof body === 'object' && !Array.isArray(body) ? {...body} : body;
    if (!next || typeof next !== 'object' || Array.isArray(next)) return originalApi(path, next);

    if (path === '/api/showcase/live-repair/capture/start') {
      const identityHandle = await ensureIdentity();
      next.arena_id = 'construction';
      if (identityHandle) {
        next.identity_handle = identityHandle;
        delete next.identity;
        delete next.current_identity;
      }
    }

    if (path.includes('/api/showcase/live-repair/capture/') && path.endsWith('/finalize/v1')) {
      next.required_assets = requiredAssets();
      next.arena_id = 'construction';
      delete next.current_identity;
    }

    if ([
      '/api/showcase/live-repair/attempt',
      '/api/showcase/live-repair/preview',
      '/api/showcase/live-repair/projection',
      '/api/showcase/live-repair/replay/run',
    ].includes(path)) {
      const identityHandle = await ensureIdentity();
      if (identityHandle) {
        next.identity_handle = identityHandle;
        delete next.current_identity;
      }
    }

    if (
      path === '/api/showcase/live-repair/projection'
      && adapter.identityBrokerAvailable
    ) {
      next.projection_version = 'AURA_SPATIAL_FOUNDRY_PROJECTION_V2';
      next.domain = {
        arena_id: 'construction',
        domain_type: 'CONSTRUCTION',
        state_digest: adapter.identitySummary?.source_tree_digest || '',
        adapter_version: 'AURA_CONSTRUCTION_SPATIAL_FOUNDRY_BROWSER_V1',
        privacy_class: 'PRESENTATION_MINIMIZED',
      };
      next.domain_targets = Array.isArray(next.domain_targets) ? next.domain_targets : [];
      next.domain_artifacts = Array.isArray(next.domain_artifacts) ? next.domain_artifacts : [];
      next.presentation = next.presentation || {
        active_view: 'REPAIR_PREVIEW',
        selected_storey: '',
        selected_entity: '',
        selected_issue: '',
      };
      next.construction = next.construction || {};
      next.coordination_candidates = Array.isArray(next.coordination_candidates)
        ? next.coordination_candidates
        : [];
    }
    let result = await originalApi(path, next);
    if (next.identity_handle && identityHandleExpired(result)) {
      adapter.identityHandle = '';
      adapter.identitySummary = null;
      const refreshedHandle = await ensureIdentity();
      if (refreshedHandle) {
        next.identity_handle = refreshedHandle;
        result = await originalApi(path, next);
      }
    }
    return result;
  };

  setLegacyIdentityVisible(true);
  void loadIdentity().catch(error => {
    adapter.identityHandle = '';
    adapter.identityBrokerAvailable = false;
    adapter.identitySummary = {ok: false, error: error.message, legacy_fallback: true};
    setLegacyIdentityVisible(true);
    renderIdentity(adapter.identitySummary);
  });
})();
