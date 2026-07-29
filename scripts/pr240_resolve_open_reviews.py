#!/usr/bin/env python3
"""Apply the still-current Codex findings for PR #240 and fail closed on drift."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement site, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, addition: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + addition.strip() + "\n", encoding="utf-8")


# Sanitize packet metadata before digesting and reject scalar obligation collections.
replace_once(
    "aura_bilateral_live_repair_foundry_capture.py",
    '''        self.identity = identity
        self.release_id = _required_text(release_id, "release_id", limit=512)
        self.environment_id = _required_text(environment_id, "environment_id", limit=512)
''',
    '''        self.identity = identity
        clean_release, release_redactions = canonical_sanitize(release_id)
        clean_environment, environment_redactions = canonical_sanitize(environment_id)
        if not isinstance(clean_release, str) or not isinstance(clean_environment, str):
            raise ValueError("release_id and environment_id must sanitize to text")
        self.release_id = _required_text(clean_release, "release_id", limit=512)
        self.environment_id = _required_text(clean_environment, "environment_id", limit=512)
        self._metadata_redactions = set(release_redactions) | set(environment_redactions)
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_capture.py",
    '''        def _obligations(values: Iterable[str], name: str, limit: int) -> tuple[str, ...]:
            normalized: set[str] = set()
            for raw in values:
''',
    '''        def _obligations(values: Iterable[str], name: str, limit: int) -> tuple[str, ...]:
            if isinstance(values, (str, bytes, bytearray, Mapping)) or not isinstance(values, Iterable):
                raise ValueError(f"{name} values must be a non-string iterable")
            normalized: set[str] = set()
            for raw in values:
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_capture.py",
    '''        asset_rows: dict[tuple[str, str], RequiredAssetIdentity] = {}
        for raw in required_assets:
''',
    '''        if (
            isinstance(required_assets, (str, bytes, bytearray, Mapping))
            or not isinstance(required_assets, Iterable)
        ):
            raise ValueError("required_assets must be a non-string iterable of objects")
        asset_rows: dict[tuple[str, str], RequiredAssetIdentity] = {}
        for raw in required_assets:
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_capture.py",
    '''                } | obligation_redactions
''',
    '''                } | obligation_redactions | self._metadata_redactions
''',
)

# Keep packets unavailable until durable archival succeeds and bound the packet cache.
replace_once(
    "aura_bilateral_live_repair_foundry_service_capture.py",
    '''    def close(self) -> None:
        with self._capture_lock:
            for timer in self._capture_timers.values():
                timer.cancel()
            self._capture_timers.clear()
            for capture in self._captures.values():
                self._scrub_capture(capture)
            self._captures.clear()
        self._packets.clear()
        self._pending_packet_archives.clear()
        self._runtime_proofs.clear()
        self._previews.clear()
        if self._owns_archive:
            self.attempt_archive.close()
''',
    '''    def close(self) -> None:
        with self._capture_lock:
            for timer in self._capture_timers.values():
                timer.cancel()
            self._capture_timers.clear()
            for capture in self._captures.values():
                self._scrub_capture(capture)
            self._captures.clear()
            self._packets.clear()
            self._pending_packet_archives.clear()
            self._runtime_proofs.clear()
            self._previews.clear()
        if self._owns_archive:
            self.attempt_archive.close()
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_service_capture.py",
    '''    def retry_packet_archive(self, packet_id: str) -> dict[str, Any]:
        resolved = _required_text(packet_id, "packet_id", limit=128)
        if resolved not in self._pending_packet_archives:
            raise BilateralLiveRepairError("pending incident replay archive not found")
        return self._archive_pending_packet(resolved)

    def _archive_pending_packet(self, packet_id: str) -> dict[str, Any]:
        entry = self._pending_packet_archives.get(packet_id)
        if entry is None:
            raise BilateralLiveRepairError(f"pending packet archive not found: {packet_id}")
        packet, contract = entry
''',
    '''    def retry_packet_archive(self, packet_id: str) -> dict[str, Any]:
        resolved = _required_text(packet_id, "packet_id", limit=128)
        with self._capture_lock:
            if resolved not in self._pending_packet_archives:
                raise BilateralLiveRepairError("pending incident replay archive not found")
        return self._archive_pending_packet(resolved)

    def _archive_pending_packet(self, packet_id: str) -> dict[str, Any]:
        with self._capture_lock:
            entry = self._pending_packet_archives.get(packet_id)
        if entry is None:
            raise BilateralLiveRepairError(f"pending packet archive not found: {packet_id}")
        packet, contract = entry
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_service_capture.py",
    '''        self._pending_packet_archives.pop(packet.packet_id, None)
        return {"ok": True, "packet": packet.to_dict(), "attempt_artifact": archive}
''',
    '''        with self._capture_lock:
            retained = self._pending_packet_archives.get(packet.packet_id)
            if retained is None or retained[0].packet_digest != packet.packet_digest:
                raise BilateralLiveRepairError(
                    "pending incident replay identity changed before durable completion"
                )
            self._pending_packet_archives.pop(packet.packet_id, None)
            self._packets[packet.packet_id] = packet
            self._packets.move_to_end(packet.packet_id)
            while len(self._packets) > 32:
                self._packets.popitem(last=False)
        return {"ok": True, "packet": packet.to_dict(), "attempt_artifact": archive}
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_service_capture.py",
    '''    def _packet(self, packet_id: str) -> IncidentReplayPacket:
        resolved = _required_text(packet_id, "packet_id", limit=128)
        item = self._packets.get(resolved)
        if item is not None:
            self._packets.move_to_end(resolved)
            return item
''',
    '''    def _packet(self, packet_id: str) -> IncidentReplayPacket:
        resolved = _required_text(packet_id, "packet_id", limit=128)
        with self._capture_lock:
            if resolved in self._pending_packet_archives:
                raise BilateralLiveRepairError(
                    "incident replay packet is pending durable archival"
                )
            item = self._packets.get(resolved)
            if item is not None:
                self._packets.move_to_end(resolved)
                return item
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_service_capture.py",
    '''                self._packets[resolved] = item
                self._packets.move_to_end(resolved)
                while len(self._packets) > 32:
                    self._packets.popitem(last=False)
                return item
''',
    '''                with self._capture_lock:
                    self._packets[resolved] = item
                    self._packets.move_to_end(resolved)
                    while len(self._packets) > 32:
                        self._packets.popitem(last=False)
                return item
''',
)

# Load runtime artifacts before filtering their decoded result fields.
replace_once(
    "aura_bilateral_live_repair_foundry_service_runtime.py",
    '''        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/runtime-replay",
            limit=0,
        ):
            if summary.get("result", {}).get("runtime_proof_digest") != proof_ref:
                continue
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            result = dict((artifact or {}).get("result") or {})
''',
    '''        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/runtime-replay",
            limit=0,
        ):
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            result = dict((artifact or {}).get("result") or {})
            if result.get("runtime_proof_digest") != proof_ref:
                continue
''',
)

# Bind every resumed U7 stage to the exact incident, bilateral identity, and candidate.
replace_once(
    "aura_bilateral_live_repair_foundry_service_preview.py",
    "from collections.abc import Callable, Mapping, Sequence\n",
    "from collections.abc import Callable, Mapping, MutableMapping, Sequence\n",
)
replace_once(
    "aura_bilateral_live_repair_foundry_service_preview.py",
    '''        session = None
        require_session = getattr(bridge, "_require_session", None)
        if callable(require_session):
            session = require_session(phase)
        retained_prediction = (
''',
    '''        session = None
        require_session = getattr(bridge, "_require_session", None)
        if callable(require_session):
            session = require_session(phase)
        binding_payload = {
            "version": "AURA_BILATERAL_LIVE_REPAIR_U7_BINDING_V1",
            "replay_packet_digest": packet.packet_digest,
            "bilateral_identity_digest": packet.identity.identity_digest,
            "candidate_digest": candidate,
            "plan_phase_hash": phase,
            "task_id": task,
        }
        binding_row = {**binding_payload, "binding_digest": digest(binding_payload)}
        if isinstance(session, MutableMapping):
            bindings = session.setdefault("bilateral_live_repair_u7_bindings", {})
            if not isinstance(bindings, MutableMapping):
                raise BilateralLiveRepairError("governed U7 binding registry is invalid")
            retained_state_exists = any(
                task in dict(session.get(name) or {})
                for name in (
                    "unified_prediction_packets",
                    "unified_p1_observations",
                    "unified_learning_results",
                    "unified_learning_finalization_claims",
                )
            )
            retained_binding = bindings.get(task)
            if retained_binding is None:
                if retained_state_exists:
                    raise BilateralLiveRepairError(
                        "retained governed U7 state lacks an incident/candidate binding"
                    )
                bindings[task] = binding_row
            elif not isinstance(retained_binding, Mapping) or dict(retained_binding) != binding_row:
                raise BilateralLiveRepairError(
                    "governed U7 task is bound to another incident or repair candidate"
                )
        elif session is not None:
            raise BilateralLiveRepairError("governed U7 bridge session is not mutable")
        retained_prediction = (
''',
)
replace_once(
    "aura_bilateral_live_repair_foundry_service_preview.py",
    '''            "task_id": task,
            "canonical_owner": "aura_unified_memory_continuity_learning",
''',
    '''            "task_id": task,
            "u7_binding_digest": binding_row["binding_digest"],
            "canonical_owner": "aura_unified_memory_continuity_learning",
''',
)

# Admit the checked-in V2 profile and namespace attempt selections by packet.
replace_once(
    "aura_showcase_live_repair_server.py",
    "from pathlib import Path\n",
    "from pathlib import Path, PurePosixPath\n",
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''        self.live_repair_attempts: dict[str, RepairCandidateResult] = {}
''',
    '''        self.live_repair_attempts: dict[tuple[str, str], RepairCandidateResult] = {}
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''def dispatch_live_repair_request(
''',
    '''def _approved_repo_relative_path(value: Any, name: str, allowed: set[str]) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "\\" in text or "\\x00" in text:
        raise ValueError(f"{name} must be a POSIX repository-relative path")
    pure = PurePosixPath(text)
    normalized = pure.as_posix()
    if pure.is_absolute() or ".." in pure.parts or normalized not in allowed:
        raise ValueError(f"{name} must be an approved repo-relative path")
    return normalized


def dispatch_live_repair_request(
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''            profile_path = str(body.get("profile_path") or "")
            output_dir = str(body.get("output_dir") or "")
            allowed_repo_relative = {
                "scripts/aura_runtime_profile_v2.json",
                "scripts/runtime_profile_v2_output",
            }
            if profile_path and not any(profile_path.endswith(allowed) for allowed in allowed_repo_relative):
                return _error("profile_path must be an approved repo-relative path", 400)
            if output_dir and not any(output_dir.endswith(allowed) for allowed in allowed_repo_relative):
                return _error("output_dir must be an approved repo-relative path", 400)
''',
    '''            profile_path = _approved_repo_relative_path(
                body.get("profile_path"),
                "profile_path",
                {".aura/runtime_profiles/construction_demo_bilateral.v2.json"},
            )
            output_dir = _approved_repo_relative_path(
                body.get("output_dir"),
                "output_dir",
                {"scripts/runtime_profile_v2_output"},
            )
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''            state.live_repair_attempts[result.attempt_id] = result
''',
    '''            state.live_repair_attempts[(result.replay_packet_digest, result.attempt_id)] = result
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''            identity = BilateralIdentity.from_mapping(body.get("current_identity") or {})
            attempt_ids = [str(item) for item in body.get("attempt_ids") or []]
            attempts = (
                [state.live_repair_attempts[item] for item in attempt_ids if item in state.live_repair_attempts]
                if attempt_ids
                else list(state.live_repair.attempts_for_packet(str(body.get("packet_id") or "")))
            )
''',
    '''            identity = BilateralIdentity.from_mapping(body.get("current_identity") or {})
            packet_id = str(body.get("packet_id") or "")
            packet = state.live_repair._packet(packet_id)
            attempt_ids = [str(item) for item in body.get("attempt_ids") or []]
            attempts = (
                [
                    state.live_repair_attempts[(packet.packet_digest, item)]
                    for item in attempt_ids
                    if (packet.packet_digest, item) in state.live_repair_attempts
                ]
                if attempt_ids
                else list(state.live_repair.attempts_for_packet(packet_id))
            )
''',
)

# Keep retryable captures alive, display canonical positives, and avoid finalize/event races.
replace_once(
    "aura_showcase/live-repair-foundry.js",
    '''    expiryTimer: null,
''',
    '''    expiryTimer: null,
    finalizing: false,
''',
)
replace_once(
    "aura_showcase/live-repair-foundry.js",
    '''      if (!target || !target.closest('#foundry-view')) return;
      void sendEvent('FOUNDRY_UI_ACTION', {
''',
    '''      if (!target || !target.closest('#foundry-view')) return;
      if (new Set(['foundry-start', 'foundry-mark', 'foundry-finalize']).has(String(target.id || ''))) return;
      void sendEvent('FOUNDRY_UI_ACTION', {
''',
)
replace_once(
    "aura_showcase/live-repair-foundry.js",
    '''  const finalize = async () => {
    const currentIdentity = identity();
    const result = await request(
''',
    '''  const finalize = async () => {
    if (!state.active || state.finalizing) return;
    state.finalizing = true;
    const currentIdentity = identity();
    let result;
    try {
      result = await request(
''',
)
replace_once(
    "aura_showcase/live-repair-foundry.js",
    '''      },
    );
    state.packet = result.packet;
''',
    '''        },
      );
    } catch (error) {
      state.finalizing = false;
      throw error;
    }
    state.packet = result.packet;
''',
)
replace_once(
    "aura_showcase/live-repair-foundry.js",
    '''    dissolveListeners();
    resetControls();
''',
    '''    dissolveListeners();
    state.finalizing = false;
    resetControls();
''',
)
replace_once(
    "aura_showcase/live-repair-foundry.js",
    '''    set('foundry-projection-intent', projection.expected_positive || projection.confirmed_intent?.positive || []);
''',
    '''    set('foundry-projection-intent', projection.confirmed_intent?.expected_positive || []);
''',
)
replace_once(
    "aura_showcase/live-repair-foundry.js",
    '''  $('foundry-finalize')?.addEventListener('click', () => finalize().catch(error => {
    dissolveListeners();
    resetControls();
    output(error.message);
  }));
''',
    '''  $('foundry-finalize')?.addEventListener('click', () => finalize().catch(error => {
    output(error.message);
  }));
''',
)

# Focused permanent regressions for the Codex root causes.
append_once(
    "tests/test_aura_bilateral_live_repair_foundry.py",
    "def test_pr240_codex_scalar_metadata_and_restart_regressions",
    r'''
def test_pr240_codex_scalar_metadata_and_restart_regressions(tmp_path):
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="Bearer metadata-secret",
        environment_id="environment api_key=metadata-secret",
        capture_authorized=True,
    )
    assert "metadata-secret" not in capture.release_id
    assert "metadata-secret" not in capture.environment_id
    capture.mark_incident("failure")
    with pytest.raises(ValueError, match="non-string iterable"):
        capture.finalize(
            expected_positive="works",
            expected_negative=["never hides"],
            preservation_claims=["source remains"],
            current_identity=item,
        )

    service, db_path, packet = service_with_packet(tmp_path, item)
    proof_ref = retain_proof(service, packet["packet_id"], item)
    service.close()
    restarted = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=db_path,
        current_identity_resolver=lambda _captured: item,
        allow_reduced_runtime_fixture=True,
    )
    retained_packet = restarted._packet(packet["packet_id"])
    retained_proof = restarted._runtime_proof(retained_packet, proof_ref)
    assert retained_proof.get("runtime_proof_digest") == proof_ref or retained_proof.get("proof_digest") == proof_ref
    restarted.close()


def test_pr240_codex_pending_packet_is_blocked_until_retry(tmp_path, monkeypatch):
    item = identity()
    service = BilateralLiveRepairService(
        tmp_path,
        attempt_archive_db_path=tmp_path / "attempts.db",
        current_identity_resolver=lambda _captured: item,
        allow_reduced_runtime_fixture=True,
    )
    started = service.start_capture({
        "identity": dataclasses.asdict(item),
        "release_id": "release",
        "environment_id": "browser",
        "capture_authorized": True,
    })
    service.mark(started["capture_id"], "failure")
    original_record = service.attempt_archive.record

    def fail_capture(*args, **kwargs):
        if kwargs.get("route") == "bilateral-live-repair/incident-capture":
            raise OSError("temporary archive failure")
        return original_record(*args, **kwargs)

    monkeypatch.setattr(service.attempt_archive, "record", fail_capture)
    with pytest.raises(BilateralLiveRepairError, match="retained in memory"):
        service.finalize_capture(started["capture_id"], {
            "expected_positive": ["works"],
            "expected_negative": ["never hides"],
            "preservation_claims": ["source remains"],
        })
    packet_id = next(iter(service._pending_packet_archives))
    with pytest.raises(BilateralLiveRepairError, match="pending durable archival"):
        service._packet(packet_id)
    monkeypatch.setattr(service.attempt_archive, "record", original_record)
    service.retry_packet_archive(packet_id)
    assert service._packet(packet_id).packet_id == packet_id
    service.close()


def test_pr240_codex_u7_resume_rejects_cross_candidate_binding(tmp_path, monkeypatch):
    session = {
        "unified_prediction_packets": {},
        "unified_p1_observations": {},
        "unified_learning_results": {},
    }

    class Bridge:
        def _require_session(self, _phase):
            return session

    class Packet:
        def __init__(self, kind):
            self.kind = kind
        def to_dict(self):
            return {"kind": self.kind}

    module = types.ModuleType("aura_unified_memory_continuity_learning")
    def commit(*_args, **kwargs):
        value = Packet("P0")
        session["unified_prediction_packets"][kwargs["task_id"]] = value
        return value
    def observe(*_args, **kwargs):
        value = Packet("P1")
        session["unified_p1_observations"][kwargs["task_id"]] = value
        return value
    def finalize(*_args, **kwargs):
        value = {"ok": True}
        session["unified_learning_results"][kwargs["task_id"]] = value
        return value
    module.commit_bridge_prediction = commit
    module.observe_bridge_prediction = observe
    module.finalize_bridge_learning = finalize
    monkeypatch.setitem(sys.modules, "aura_unified_memory_continuity_learning", module)

    item = identity()
    service, _db, packet = service_with_packet(tmp_path, item)
    common = {
        "packet_id": packet["packet_id"],
        "current_identity": item,
        "bridge": Bridge(),
        "plan_phase_hash": "phase",
        "task_id": "task",
        "prediction_contract": {},
        "observation_contract": {},
        "finalization_contract": {},
    }
    service.run_governed_u7(candidate_digest=sha("candidate-a"), **common)
    with pytest.raises(BilateralLiveRepairError, match="bound to another incident or repair candidate"):
        service.run_governed_u7(candidate_digest=sha("candidate-b"), **common)
    service.close()
''',
)
append_once(
    "tests/test_aura_showcase_live_repair_server.py",
    "def test_pr240_codex_browser_and_profile_regressions",
    r'''
def test_pr240_codex_browser_and_profile_regressions():
    source = (
        Path(__file__).resolve().parent.parent
        / "aura_showcase"
        / "live-repair-foundry.js"
    ).read_text(encoding="utf-8")
    assert "projection.confirmed_intent?.expected_positive" in source
    assert "foundry-finalize']).has" in source
    finalize_handler = source.split("$('foundry-finalize')?.addEventListener", 1)[1]
    assert "dissolveListeners();" not in finalize_handler.split("window.addEventListener", 1)[0]

    server_source = (
        Path(__file__).resolve().parent.parent
        / "aura_showcase_live_repair_server.py"
    ).read_text(encoding="utf-8")
    assert ".aura/runtime_profiles/construction_demo_bilateral.v2.json" in server_source
    assert "dict[tuple[str, str], RepairCandidateResult]" in server_source
''',
)

# The follow-up helper is intentionally inert; this script owns the complete repair.
(ROOT / "scripts/pr240_followup_review_fixes.py").write_text(
    '#!/usr/bin/env python3\n"""No-op: PR240 Codex repairs are applied by pr240_resolve_open_reviews.py."""\n',
    encoding="utf-8",
)
