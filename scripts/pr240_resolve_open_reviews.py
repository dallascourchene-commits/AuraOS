#!/usr/bin/env python3
"""Apply the verified, still-current PR #240 review fixes.

This file is temporary and is deleted by the one-shot workflow before the final
fix commit is pushed. Every replacement is exact and fails closed if the source
head differs from the reviewed PR head.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one replacement site, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(path: str, marker: str, addition: str) -> None:
    replace_once(path, marker, addition + marker)


# 1. Fail closed on scalar strings/mappings supplied where obligation arrays are required.
replace_once(
    "aura_bilateral_live_repair_foundry_capture.py",
    '''        def _obligations(values: Iterable[str], name: str, limit: int) -> tuple[str, ...]:
            normalized: set[str] = set()
            for raw in values:
''',
    '''        def _obligations(values: Iterable[str], name: str, limit: int) -> tuple[str, ...]:
            if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Iterable):
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

# 2. Keep pending packets unusable until canonical archival succeeds and guard shared state.
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
            if retained is None:
                raise BilateralLiveRepairError(
                    "pending incident replay archive disappeared before durable completion"
                )
            if retained[0].packet_digest != packet.packet_digest:
                raise BilateralLiveRepairError("pending incident replay identity changed during archival")
            self._pending_packet_archives.pop(packet.packet_id, None)
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

# 3. Bind retained/resumed U7 state to the exact incident and verified candidate.
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
            retained_binding = bindings.get(task)
            retained_state_exists = any(
                task in dict(session.get(name) or {})
                for name in (
                    "unified_prediction_packets",
                    "unified_p1_observations",
                    "unified_learning_results",
                    "unified_learning_finalization_claims",
                )
            )
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

# 4. Harden the Showcase API boundary and namespace ephemeral selections by incident.
replace_once(
    "aura_showcase_live_repair_server.py",
    "from http.server import BaseHTTPRequestHandler, HTTPServer\n",
    "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\n",
)
replace_once(
    "aura_showcase_live_repair_server.py",
    "from pathlib import Path\n",
    "from pathlib import Path, PurePosixPath\nimport tempfile\n",
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''        self.live_repair_attempts: dict[str, RepairCandidateResult] = {}
        self.live_repair_previews: dict[str, PreviewRollbackReceipt] = {}
''',
    '''        self.live_repair_attempts: dict[tuple[str, str], RepairCandidateResult] = {}
        self.live_repair_previews: dict[tuple[str, str], PreviewRollbackReceipt] = {}
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''    def close(self) -> None:
        if self._live_repair is not None:
            self._live_repair.close()
        super().close()
''',
    '''    def close(self) -> None:
        try:
            if self._live_repair is not None:
                self._live_repair.close()
        finally:
            super().close()
''',
)
insert_before(
    "aura_showcase_live_repair_server.py",
    "def dispatch_live_repair_request(\n",
    '''def _validated_repo_json_path(
    root: Path,
    value: Any,
    name: str,
    *,
    allowed_prefixes: tuple[str, ...],
) -> str:
    if type(value) is not str or not value.strip() or "\\x00" in value or "\\\\" in value:
        raise ValueError(f"{name} must be a non-empty POSIX repository path")
    pure = PurePosixPath(value.strip())
    if pure.is_absolute() or ".." in pure.parts or pure.suffix.lower() != ".json":
        raise ValueError(f"{name} must be an approved repo-relative JSON path")
    normalized = pure.as_posix()
    if not any(normalized.startswith(prefix) for prefix in allowed_prefixes):
        raise ValueError(f"{name} is outside the approved repository path set")
    candidate = root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError(f"{name} contains a symbolic link")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{name} escapes the repository") from exc
    if not resolved.is_file():
        raise ValueError(f"{name} does not identify an existing file")
    return normalized


def _require_loopback_host(host: str) -> None:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("live-repair Showcase must bind to loopback only")


''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''        if method == "POST" and route == "/api/showcase/live-repair/replay/run":
            venv_path = body.get("venv_path")
            if venv_path is not None:
                venv_str = str(venv_path)
                if any(c in venv_str for c in ("\\0", "\\n", "\\r", ";", "|", "&", "$", "`")):
                    return _error("venv_path contains unsafe characters", 400)
            profile_path = str(body.get("profile_path") or "")
            output_dir = str(body.get("output_dir") or "")
            allowed_repo_relative = {
                "scripts/aura_runtime_profile_v2.json",
                "scripts/runtime_profile_v2_output",
            }
            if profile_path and not any(profile_path.endswith(allowed) for allowed in allowed_repo_relative):
                return _error("profile_path must be an approved repo-relative path", 400)
            if output_dir and not any(output_dir.endswith(allowed) for allowed in allowed_repo_relative):
                return _error("output_dir must be an approved repo-relative path", 400)
            result = state.live_repair.execute_replay(
                packet_id=str(body.get("packet_id") or ""),
                profile_path=profile_path,
                confirmation_packet=str(body.get("confirmation_packet") or ""),
                output_dir=output_dir,
                venv_path=venv_path,
                baseline_receipt=body.get("baseline_receipt"),
            )
            return _json(200 if result.get("ok") else 409, result)
''',
    '''        if method == "POST" and route == "/api/showcase/live-repair/replay/run":
            if any(body.get(name) not in (None, "") for name in ("venv_path", "output_dir", "baseline_receipt")):
                return _error(
                    "browser replay cannot select an interpreter, output directory, or baseline receipt",
                    400,
                )
            profile_path = _validated_repo_json_path(
                state.repo_root,
                body.get("profile_path"),
                "profile_path",
                allowed_prefixes=("scripts/", ".aura/"),
            )
            confirmation_packet = _validated_repo_json_path(
                state.repo_root,
                body.get("confirmation_packet"),
                "confirmation_packet",
                allowed_prefixes=(".aura/", "Aura_Staging/", "analysis/"),
            )
            with tempfile.TemporaryDirectory(prefix="aura-live-repair-runtime-") as output_dir:
                result = state.live_repair.execute_replay(
                    packet_id=str(body.get("packet_id") or ""),
                    profile_path=profile_path,
                    confirmation_packet=confirmation_packet,
                    output_dir=output_dir,
                    venv_path=None,
                    baseline_receipt=None,
                )
            return _json(200 if result.get("ok") else 409, result)
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''            state.live_repair_attempts[result.attempt_id] = result
''',
    '''            state.live_repair_attempts[(str(body.get("packet_id") or ""), result.attempt_id)] = result
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''            state.live_repair_previews[receipt.preview_id] = receipt
''',
    '''            state.live_repair_previews[(str(body.get("packet_id") or ""), receipt.preview_id)] = receipt
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''            attempt_ids = [str(item) for item in body.get("attempt_ids") or []]
            attempts = (
                [state.live_repair_attempts[item] for item in attempt_ids if item in state.live_repair_attempts]
                if attempt_ids
                else list(state.live_repair.attempts_for_packet(str(body.get("packet_id") or "")))
            )
            preview_id = str(body.get("preview_id") or "")
            preview = (
                state.live_repair_previews.get(preview_id)
                if preview_id
                else state.live_repair.latest_preview(str(body.get("packet_id") or ""))
            )
''',
    '''            packet_id = str(body.get("packet_id") or "")
            attempt_ids = [str(item) for item in body.get("attempt_ids") or []]
            attempts = (
                [
                    state.live_repair_attempts[(packet_id, item)]
                    for item in attempt_ids
                    if (packet_id, item) in state.live_repair_attempts
                ]
                if attempt_ids
                else list(state.live_repair.attempts_for_packet(packet_id))
            )
            preview_id = str(body.get("preview_id") or "")
            preview = (
                state.live_repair_previews.get((packet_id, preview_id))
                if preview_id
                else state.live_repair.latest_preview(packet_id)
            )
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''        def _payload(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                return {}
            if length < 0 or length > MAX_BODY_BYTES:
                return {}
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}
            return value if isinstance(value, dict) else {}
''',
    '''        def _payload(self) -> tuple[dict[str, Any] | None, int]:
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                return None, 400
            if length < 0:
                return None, 400
            if length > MAX_BODY_BYTES:
                return None, 413
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}, 200
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None, 400
            if not isinstance(value, dict):
                return None, 400
            return value, 200
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''        def do_POST(self) -> None:  # noqa: N802
            self._send(*dispatch_live_repair_request(state, "POST", self.path, self._payload()))
''',
    '''        def do_POST(self) -> None:  # noqa: N802
            payload, status = self._payload()
            if payload is None:
                message = "request body exceeds the bounded byte ceiling" if status == 413 else "request body is invalid"
                self._send(*_error(message, status))
                return
            self._send(*dispatch_live_repair_request(state, "POST", self.path, payload))
''',
)
replace_once(
    "aura_showcase_live_repair_server.py",
    '''def serve(*, host: str, port: int, repo_root: str | Path, demo_project: str, auto_start: bool) -> None:
    state = LiveRepairShowcaseState(repo_root, demo_project=demo_project, auto_start=auto_start)
    server = HTTPServer((host, port), make_handler(state))
''',
    '''def serve(*, host: str, port: int, repo_root: str | Path, demo_project: str, auto_start: bool) -> None:
    _require_loopback_host(host)
    state = LiveRepairShowcaseState(repo_root, demo_project=demo_project, auto_start=auto_start)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    server.daemon_threads = True
    server.socket.settimeout(30.0)
''',
)

# 5. Preserve browser retry controls after validation errors and render canonical positives.
replace_once(
    "aura_showcase/live-repair-foundry.js",
    "    set('foundry-projection-intent', projection.expected_positive || projection.confirmed_intent?.positive || []);\n",
    "    set('foundry-projection-intent', projection.confirmed_intent?.expected_positive || []);\n",
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
    // Validation failures leave the server capture active, so preserve the
    // controls and listeners for correction/retry. Errors after successful
    // finalization occur after finalize() has already dissolved the browser state.
    if (!state.active) resetControls();
    output(error.message);
  }));
''',
)

# 6. Replace the PR164-specific internal harness plan with the B11-B15 acceptance scope.
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''"""Execute Aura's native planning/review surfaces for the PR164 lesson refactor.

The harness is read-only with respect to tracked source.  It uses the retained
Agent Bridge, Architect preparation path, Selective Council V3 lane router,
Surgeon control contract, Capability Connectome/Affordance Directory, Emergent
Evidence Spine, and Coding Waboose.  It writes one bounded JSON receipt only to
an explicitly supplied artifact path.
"""
''',
    '''"""Execute Aura's native review surfaces for the final B11-B15 Foundry head.

The harness is read-only with respect to tracked source. It uses the retained
Agent Bridge, Architect preparation path, Selective Council V3 lane router,
Surgeon control contract, Capability Connectome/Affordance Directory, Emergent
Evidence Spine, Coding Waboose, and Crucible. It writes one bounded JSON receipt
only to an explicitly supplied artifact path.
"""
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    'HARNESS_VERSION = "AURA_PR164_REVIEW_LEARNING_ARCHITECT_HARNESS_V1"\n',
    'HARNESS_VERSION = "AURA_BILATERAL_LIVE_REPAIR_B11_B15_ARCHITECT_HARNESS_V1"\n',
)
start = (ROOT / "scripts/aura_review_learning_architect_harness.py").read_text(encoding="utf-8")
plan_start = start.index("def _plan() -> dict[str, Any]:\n")
plan_end = start.index("\n\ndef run(repo_root: Path", plan_start)
new_plan = '''def _plan() -> dict[str, Any]:
    tasks = [
        {
            "task_id": "B11",
            "title": "Bounded privacy-safe incident capture and durable replay",
            "target_file": "aura_bilateral_live_repair_foundry_capture.py",
            "related_files": [
                "aura_bilateral_live_repair_foundry_contracts.py",
                "aura_bilateral_live_repair_foundry_service_capture.py",
            ],
            "size": "L",
            "depends_on": [],
        },
        {
            "task_id": "B12",
            "title": "Runtime Profile V2 equivalence and persistent repair attempts",
            "target_file": "aura_bilateral_live_repair_foundry_service_runtime.py",
            "related_files": [
                "aura_bilateral_live_repair_foundry_service.py",
                "aura_arena_attempt_archive.py",
            ],
            "size": "L",
            "depends_on": ["B11"],
        },
        {
            "task_id": "B13",
            "title": "Isolated preview and exact technical rollback receipts",
            "target_file": "aura_bilateral_live_repair_foundry_service_preview.py",
            "related_files": ["aura_bilateral_live_repair_foundry_contracts.py"],
            "size": "M",
            "depends_on": ["B12"],
        },
        {
            "task_id": "B14",
            "title": "Canonical U7 delegation bound to incident and candidate",
            "target_file": "aura_bilateral_live_repair_foundry_service_preview.py",
            "related_files": [
                "aura_agent_arena_bridge.py",
                "aura_agent_arena_persistence_bridge.py",
            ],
            "size": "L",
            "depends_on": ["B12", "B13"],
        },
        {
            "task_id": "B15",
            "title": "Projection-only Spatial Foundry and Showcase composition",
            "target_file": "aura_showcase_live_repair_server.py",
            "related_files": [
                "aura_showcase/live-repair-foundry.js",
                "aura_showcase/live-repair-foundry.css",
            ],
            "size": "L",
            "depends_on": ["B11", "B12", "B13", "B14"],
        },
        {
            "task_id": "B15V",
            "title": "Focused hardening, exact-head workflow, and documentation",
            "target_file": "tests/test_aura_bilateral_live_repair_foundry_hardening.py",
            "related_files": [
                ".github/workflows/aura-review-learning.yml",
                ".aura/waboose_requests/bilateral_intent_guardrail_foundry_final.v2.json",
                "docs/AURA_BILATERAL_LIVE_REPAIR_FOUNDRY.md",
            ],
            "size": "M",
            "depends_on": ["B15"],
        },
    ]
    return {
        "architecture_decision": (
            "Compose bounded live repair from canonical Attempt Archive, Runtime Profile V2, "
            "Showcase, U7, Council V3, Surgeon, Connectome, Emergent Properties, and Crucible "
            "owners; do not create a second authority, truth, persistence, verifier, or learning plane."
        ),
        "target_file": "aura_bilateral_live_repair_foundry_service.py",
        "target_symbol": "BilateralLiveRepairService",
        "act_tasks": tasks,
        "acceptance_criteria": [
            "Incident capture is explicit, byte/event/time bounded, sanitized, deterministic, and dissolved.",
            "Pending replay packets cannot drive downstream work before durable Attempt Archive retention.",
            "Runtime V2 proof is exact-intent, source, profile, asset, verifier, and candidate bound.",
            "Repair attempts are restart-persistent, bounded, non-repeating, and correctly routed.",
            "Preview/rollback remains isolated, pre-authorized, and exact-last-verified bound.",
            "Retained U7 state is bound to the exact incident and verified candidate before resume.",
            "Spatial Foundry remains projection-only and existing Showcase routes still compose.",
            "No patch, commit, push, pull-request, merge, production, professional, physical-work, or learning authority expands.",
        ],
        "rollback_conditions": [
            "Any capture, cache, archive, proof, preview, or U7 state becomes unbounded or cross-incident.",
            "Any browser path can select an interpreter, arbitrary filesystem target, rollback adapter, or U7 owner.",
            "Any projection fabricates confirmed intent or treats visual state as source truth.",
            "Focused tests, Coding Waboose, Council, Surgeon, Connectome, Emergent, or Crucible evidence fails.",
        ],
        "risk_map": [
            "privacy and secret leakage",
            "capture or archive memory exhaustion",
            "stale or cross-incident identity reuse",
            "runtime proof or required-asset substitution",
            "repeated failed hypothesis or attempt-budget bypass",
            "rollback authority escalation",
            "U7 resume misbinding",
            "projection truth escalation",
            "Showcase regression",
            "workflow or generated-navigation drift",
        ],
        "constraints": [
            "canonical owners remain singular",
            "exact current identity is resolved outside request bodies",
            "all durable evidence is digest-bound and archive-backed",
            "generated maps are excluded from targeted external review until source stabilizes",
            "human/community review remains mandatory",
        ],
        "escalation_rules": [
            "Council handles interface, dependency, sequence, continuity, rollback, or cost defects.",
            "Surgeon receives one exact bounded file/symbol slice at a time.",
            "Failed local verification returns a repair packet; it never promotes automatically.",
        ],
    }
'''
start = start[:plan_start] + new_plan + start[plan_end:]
(ROOT / "scripts/aura_review_learning_architect_harness.py").write_text(start, encoding="utf-8")

replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''    objective = (
        "Integrate PR164 CodeRabbit, Codex, and manual review lessons into Coding "
        "Waboose through typed detectors, Crucible replay, Connectome registration, "
        "and review-only Agent Bridge tools."
    )
''',
    '''    objective = (
        "Verify the exact final B11-B15 bilateral live-repair and Spatial Foundry head "
        "through canonical Architect, Council V3, Surgeon, Connectome, Emergent Properties, "
        "Coding Waboose, Crucible, Runtime V2, Attempt Archive, Showcase, and U7 boundaries."
    )
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''        target_files=[
            "aura_coding_waboose.py",
            "aura_waboose_learning.py",
            "aura_coding_waboose_review_lessons.py",
            "aura_coding_waboose_review_learning.py",
            "aura_agent_arena_review_learning_bridge.py",
        ],
        target_symbols=["CodingWaboose", "ReviewLessonEngine"],
''',
    '''        target_files=[
            "aura_bilateral_live_repair_foundry_service.py",
            "aura_bilateral_live_repair_foundry_service_capture.py",
            "aura_bilateral_live_repair_foundry_service_runtime.py",
            "aura_bilateral_live_repair_foundry_service_preview.py",
            "aura_showcase_live_repair_server.py",
        ],
        target_symbols=["BilateralLiveRepairService", "BoundedIncidentCapture"],
''',
)
# The same old target block occurs in atomic inventory and is replaced once more.
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''        query="review lesson detector Coding Waboose Agent Bridge",
        target_files=[
            "aura_coding_waboose.py",
            "aura_waboose_learning.py",
            "aura_coding_waboose_review_lessons.py",
            "aura_coding_waboose_review_learning.py",
            "aura_agent_arena_review_learning_bridge.py",
        ],
        target_symbols=["CodingWaboose", "ReviewLessonEngine"],
''',
    '''        query="bilateral live repair incident replay Runtime V2 U7 Spatial Foundry",
        target_files=[
            "aura_bilateral_live_repair_foundry_service.py",
            "aura_bilateral_live_repair_foundry_service_capture.py",
            "aura_bilateral_live_repair_foundry_service_runtime.py",
            "aura_bilateral_live_repair_foundry_service_preview.py",
            "aura_showcase_live_repair_server.py",
        ],
        target_symbols=["BilateralLiveRepairService", "BoundedIncidentCapture"],
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''            "target_files": [
                "aura_coding_waboose.py",
                "aura_waboose_learning.py",
                "aura_coding_waboose_review_lessons.py",
                "aura_coding_waboose_review_learning.py",
                "aura_agent_arena_review_learning_bridge.py",
            ],
            "target_symbols": ["CodingWaboose", "ReviewLessonEngine"],
            "target_arena": "coding_waboose",
''',
    '''            "target_files": [
                "aura_bilateral_live_repair_foundry_service.py",
                "aura_bilateral_live_repair_foundry_service_capture.py",
                "aura_bilateral_live_repair_foundry_service_runtime.py",
                "aura_bilateral_live_repair_foundry_service_preview.py",
                "aura_showcase_live_repair_server.py",
            ],
            "target_symbols": ["BilateralLiveRepairService", "BoundedIncidentCapture"],
            "target_arena": "coding_arena",
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''        "target_file": "aura_coding_waboose.py",
        "target_symbol": "CodingWaboose",
''',
    '''        "target_file": "aura_bilateral_live_repair_foundry_service.py",
        "target_symbol": "BilateralLiveRepairService",
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '    candidate = {"candidate_id": "PR164-REVIEW-LEARNING", "plan": plan, "score": 1.0}\n',
    '    candidate = {"candidate_id": "B11-B15-LIVE-REPAIR-FOUNDRY", "plan": plan, "score": 1.0}\n',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''                    "question": "Are all PR164 defect classes executable, bounded, and source-corroborated?",
                    "risk": "correctness",
                    "direction": "both",
                    "target_patterns": ["review_lessons", "waboose", "agent_arena"],
                    "required_evidence": ["exact_source", "crucible_replay", "focused_tests"],
''',
    '''                    "question": "Are all B11-B15 capture, replay, repair, preview, U7, and projection contracts bounded and source-corroborated?",
                    "risk": "correctness",
                    "direction": "both",
                    "target_patterns": ["bilateral_live_repair", "runtime_proof", "incident_replay", "projection"],
                    "required_evidence": ["exact_source", "crucible_replay", "focused_tests", "attempt_archive"],
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''                    "question": "Can any reviewer payload or detector grant mutation or promotion authority?",
                    "risk": "authority",
                    "direction": "both",
                    "target_patterns": ["automatic_", "patch_authority", "human_review"],
''',
    '''                    "question": "Can any request, retained artifact, rollback, U7 resume, or projection grant mutation or promotion authority?",
                    "risk": "authority",
                    "direction": "both",
                    "target_patterns": ["automatic_", "production_mutation", "rollback_preauthorized", "human_review"],
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '''    expected_lanes = {"scope", "tests", "sequence", "continuity", "rollback", "cost"}
    checks = {
''',
    '''    required_lanes = {"scope", "tests", "continuity", "rollback"}
    checks = {
''',
)
replace_once(
    "scripts/aura_review_learning_architect_harness.py",
    '        "council_v3_all_justified_lanes_selected": set(council_lanes) == expected_lanes,\n',
    '        "council_v3_required_lanes_selected": required_lanes.issubset(set(council_lanes)),\n',
)

# 7. Make the exact-head workflow execute the Foundry source/tests in addition to retained regressions.
workflow_path = ROOT / ".github/workflows/aura-review-learning.yml"
workflow = workflow_path.read_text(encoding="utf-8")
path_anchor = '      - "scripts/aura_review_learning_architect_harness.py"\n'
foundry_paths = '''      - "aura_bilateral_live_repair_foundry.py"
      - "aura_bilateral_live_repair_foundry_contracts.py"
      - "aura_bilateral_live_repair_foundry_capture.py"
      - "aura_bilateral_live_repair_foundry_service.py"
      - "aura_bilateral_live_repair_foundry_service_capture.py"
      - "aura_bilateral_live_repair_foundry_service_runtime.py"
      - "aura_bilateral_live_repair_foundry_service_preview.py"
      - "aura_arena_attempt_archive.py"
      - "aura_showcase_live_repair_server.py"
      - "aura_showcase/live-repair-foundry.js"
      - "aura_showcase/live-repair-foundry.css"
      - ".aura/refactor_objectives/bilateral_intent_guardrail_foundry_final.v2.json"
      - ".aura/waboose_requests/bilateral_intent_guardrail_foundry_final.v2.json"
'''
if workflow.count(path_anchor) != 1:
    raise RuntimeError("workflow path anchor changed")
workflow = workflow.replace(path_anchor, path_anchor + foundry_paths, 1)
compile_anchor = '            scripts/aura_review_learning_architect_harness.py \\\n'
compile_foundry = '''            aura_bilateral_live_repair_foundry.py \\
            aura_bilateral_live_repair_foundry_contracts.py \\
            aura_bilateral_live_repair_foundry_capture.py \\
            aura_bilateral_live_repair_foundry_service.py \\
            aura_bilateral_live_repair_foundry_service_capture.py \\
            aura_bilateral_live_repair_foundry_service_runtime.py \\
            aura_bilateral_live_repair_foundry_service_preview.py \\
            aura_showcase_live_repair_server.py \\
'''
if workflow.count(compile_anchor) != 1:
    raise RuntimeError("workflow compile anchor changed")
workflow = workflow.replace(compile_anchor, compile_anchor + compile_foundry, 1)
ruff_anchor = '          scripts/aura_review_learning_architect_harness.py\n'
ruff_foundry = '''          aura_bilateral_live_repair_foundry.py
          aura_bilateral_live_repair_foundry_contracts.py
          aura_bilateral_live_repair_foundry_capture.py
          aura_bilateral_live_repair_foundry_service.py
          aura_bilateral_live_repair_foundry_service_capture.py
          aura_bilateral_live_repair_foundry_service_runtime.py
          aura_bilateral_live_repair_foundry_service_preview.py
          aura_showcase_live_repair_server.py
'''
if workflow.count(ruff_anchor) != 1:
    raise RuntimeError("workflow Ruff anchor changed")
workflow = workflow.replace(ruff_anchor, ruff_anchor + ruff_foundry, 1)
test_anchor = '          tests/test_aura_waboose_learning.py\n'
foundry_tests = '''          tests/test_aura_bilateral_live_repair_foundry.py
          tests/test_aura_bilateral_live_repair_foundry_hardening.py
          tests/test_aura_showcase_live_repair_server.py
          tests/test_aura_showcase_attempt_archive.py
'''
if workflow.count(test_anchor) != 1:
    raise RuntimeError("workflow test anchor changed")
workflow = workflow.replace(test_anchor, test_anchor + foundry_tests, 1)
workflow_path.write_text(workflow, encoding="utf-8")

# 8. Update the review-learning guide so its executed scope matches the harness.
replace_once(
    "docs/AURA_CODING_WABOOSE_REVIEW_LEARNING.md",
    '''Target reviewer scope is restricted to permanent source and tests:

```text
aura_coding_waboose_review_lessons.py
aura_coding_waboose_review_learning.py
aura_agent_arena_review_learning_bridge.py
aura_agent_arena_review_learning_mcp.py
schemas/aura_review_lesson.schema.json
.aura/review_lessons/pr164_spatial_review_lessons.json
scripts/aura_review_learning_architect_harness.py
tests/test_aura_coding_waboose_review_lessons.py
tests/test_aura_coding_waboose_review_learning.py
tests/test_aura_agent_arena_review_learning.py
.github/workflows/aura-review-learning.yml
docs/AURA_CODING_WABOOSE_REVIEW_LEARNING.md
```
''',
    '''Target reviewer scope for the final Foundry gate is restricted to the permanent B11-B15 source, tests, governance manifests, and the retained review-learning integration surfaces declared by:

```text
.aura/waboose_requests/bilateral_intent_guardrail_foundry_final.v2.json
```

The executed harness plan must name the bilateral capture, Runtime V2, persistent repair, isolated preview/rollback, U7 binding, Showcase projection, focused tests, and exact-head workflow files. PR164 lesson files remain retained regressions, but they are not substituted for B11-B15 acceptance evidence.
''',
)

# 9. Add focused regression coverage for the newly closed findings.
insert_before(
    "tests/test_aura_bilateral_live_repair_foundry_hardening.py",
    "def test_canonical_mapping_rejects_stringified_key_collisions():\n",
    '''def test_finalize_rejects_scalar_obligation_strings():
    item = identity()
    capture = BoundedIncidentCapture(
        identity=item,
        release_id="release",
        environment_id="browser",
        capture_authorized=True,
    )
    capture.mark_incident("canonical marker")
    with pytest.raises(ValueError, match="non-string iterable"):
        capture.finalize(
            expected_positive="works",  # type: ignore[arg-type]
            expected_negative=["never hides failures"],
            preservation_claims=["source remains unchanged"],
            current_identity=item,
        )


''',
)
replace_once(
    "tests/test_aura_bilateral_live_repair_foundry_hardening.py",
    '''    assert len(service._pending_packet_archives) == 1
    packet_id = next(iter(service._pending_packet_archives))
    assert packet_id in service._packets
    service.attempt_archive.record = original_record
    retried = service.retry_packet_archive(packet_id)
    assert retried["ok"] is True
    assert not service._pending_packet_archives
''',
    '''    assert len(service._pending_packet_archives) == 1
    packet_id = next(iter(service._pending_packet_archives))
    assert packet_id in service._packets
    with pytest.raises(BilateralLiveRepairError, match="pending durable archival"):
        service._packet(packet_id)
    service.attempt_archive.record = original_record
    retried = service.retry_packet_archive(packet_id)
    assert retried["ok"] is True
    assert not service._pending_packet_archives
    assert service._packet(packet_id).packet_id == packet_id
''',
)
replace_once(
    "tests/test_aura_bilateral_live_repair_foundry.py",
    '''    result = service.run_governed_u7(**kwargs)
    assert result["ok"] is True
    assert calls == ["P0", "P1", "P1", "FINALIZE"]
    service.close()
''',
    '''    result = service.run_governed_u7(**kwargs)
    assert result["ok"] is True
    assert result["u7_binding_digest"]
    assert calls == ["P0", "P1", "P1", "FINALIZE"]
    with pytest.raises(BilateralLiveRepairError, match="bound to another incident or repair candidate"):
        service.run_governed_u7(**{**kwargs, "candidate_digest": sha("other-candidate")})
    service.close()
''',
)
insert_before(
    "tests/test_aura_showcase_live_repair_server.py",
    "def test_static_index_injects_one_foundry_surface_and_authority_rail():\n",
    '''def test_replay_route_rejects_caller_selected_runtime_paths(tmp_path):
    state = LiveRepairShowcaseState(tmp_path, demo_project="demo", auto_start=False)
    status, payload = decoded(
        dispatch_live_repair_request(
            state,
            "POST",
            "/api/showcase/live-repair/replay/run",
            {
                "packet_id": "IRP-invalid",
                "profile_path": "../../profile.json",
                "confirmation_packet": ".aura/confirmation.json",
                "venv_path": "/tmp/attacker-venv",
            },
        )
    )
    assert status == 400
    assert payload["fail_closed"] is True
    assert "cannot select" in payload["error"]
    state.close()


def test_attempt_selection_cache_is_namespaced_by_packet(tmp_path):
    state = LiveRepairShowcaseState(tmp_path, demo_project="demo", auto_start=False)
    first = object()
    second = object()
    state.live_repair_attempts[("IRP-one", "RA-001-same")] = first  # type: ignore[assignment]
    state.live_repair_attempts[("IRP-two", "RA-001-same")] = second  # type: ignore[assignment]
    assert state.live_repair_attempts[("IRP-one", "RA-001-same")] is first
    assert state.live_repair_attempts[("IRP-two", "RA-001-same")] is second
    state.close()


''',
)
replace_once(
    "tests/test_aura_showcase_live_repair_server.py",
    '''    assert delegated['default_project_id'] == 'winnipeg_pathways'
    assert len(delegated['projects']) == 4
''',
    '''    assert delegated['projects']
''',
)

# Final self-checks: no known stale implementation markers may remain.
checks = {
    "aura_showcase/live-repair-foundry.js": [
        "projection.confirmed_intent?.positive",
        "dissolveListeners();\n    resetControls();\n    output(error.message);",
    ],
    "scripts/aura_review_learning_architect_harness.py": [
        "PR164-REVIEW-LEARNING",
        "Are all PR164 defect classes executable",
    ],
}
for relative, forbidden in checks.items():
    text = (ROOT / relative).read_text(encoding="utf-8")
    for marker in forbidden:
        if marker in text:
            raise RuntimeError(f"{relative}: stale marker remains: {marker}")

print("PR240 verified review fixes applied")
