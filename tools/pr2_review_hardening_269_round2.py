from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_block(text: str, start: str, end: str, replacement: str, label: str) -> str:
    first = text.find(start)
    if first < 0:
        raise SystemExit(f"{label}: start marker not found")
    second = text.find(end, first + len(start))
    if second < 0:
        raise SystemExit(f"{label}: end marker not found")
    if text.find(start, first + len(start)) >= 0:
        raise SystemExit(f"{label}: start marker is not unique")
    return text[:first] + replacement.rstrip() + "\n\n" + text[second:]


# Store-side authority checks: an injected timestamp may make a check stricter,
# but it may never move authoritative time backwards.
path = "aura_ephemeral_registry_store.py"
text = read(path)
text = replace_once(
    text,
    '''SCHEMA_VERSION = 2


def _default_db_path(repo_root: str | Path = ".") -> Path:
''',
    '''SCHEMA_VERSION = 2


def _trusted_now(candidate: float | int | None = None) -> float:
    current = time.time()
    if candidate is None:
        return current
    if type(candidate) not in {int, float} or type(candidate) is bool:
        raise ValueError("now must be a finite number")
    supplied = float(candidate)
    if not math.isfinite(supplied):
        raise ValueError("now must be a finite number")
    return max(current, supplied)


def _default_db_path(repo_root: str | Path = ".") -> Path:
''',
    "store trusted clock helper",
)
text = replace_once(
    text,
    '''        current_time = time.time() if now is None else now
        if type(current_time) not in {int, float} or type(current_time) is bool:
            raise ValueError("now must be a finite number")
        current_time = float(current_time)
        if not math.isfinite(current_time):
            raise ValueError("now must be a finite number")
        expected_json = self._workspace_v2_json(expected_certificate, "expected_certificate")''',
    '''        current_time = _trusted_now(now)
        expected_json = self._workspace_v2_json(expected_certificate, "expected_certificate")''',
    "certificate trusted authority clock",
)
text = replace_once(
    text,
    '''        current_time = time.time() if now is None else now
        if type(current_time) not in {int, float}:
            raise ValueError("now must be a finite number")
        current_time = float(current_time)
        if not (current_time == current_time and abs(current_time) != float("inf")):
            raise ValueError("now must be a finite number")
        expected_receipts_json = self._workspace_v2_json(''',
    '''        current_time = _trusted_now(now)
        expected_receipts_json = self._workspace_v2_json(''',
    "node CAS trusted authority clock",
)
text = replace_once(
    text,
    '''    def is_workspace_v2_lease_active(self, workspace_id: str, *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        if type(current) not in {int, float} or type(current) is bool:
            raise ValueError("now must be a finite number")
        current = float(current)
        if not math.isfinite(current):
            raise ValueError("now must be a finite number")
        conn = self._conn''',
    '''    def is_workspace_v2_lease_active(self, workspace_id: str, *, now: float | None = None) -> bool:
        current = _trusted_now(now)
        conn = self._conn''',
    "lease trusted authority clock",
)
text = replace_once(
    text,
    '''    def list_expired_workspaces_v2(self, *, now: float | None = None) -> dict[str, Any]:
        current = time.time() if now is None else now
        if type(current) not in {int, float} or type(current) is bool:
            raise ValueError("now must be a finite number")
        current = float(current)
        if not math.isfinite(current):
            raise ValueError("now must be a finite number")
        conn = self._conn''',
    '''    def list_expired_workspaces_v2(self, *, now: float | None = None) -> dict[str, Any]:
        current = _trusted_now(now)
        conn = self._conn''',
    "expired listing trusted clock",
)
write(path, text)


# Runtime-side authority clock and cleanup race convergence.
path = "aura_ephemeral_workspace_runtime_v2.py"
text = read(path)
text = replace_once(
    text,
    '''def _exact_mapping(value: Any, name: str) -> dict[str, Any]:
''',
    '''def _trusted_now(candidate: float | int | None = None) -> float:
    """Return authoritative current time; caller input can only move it forward."""
    current = time.time()
    if candidate is None:
        return current
    return max(current, _finite(candidate, "now"))


def _exact_mapping(value: Any, name: str) -> dict[str, Any]:
''',
    "runtime trusted clock helper",
)
text = replace_once(
    text,
    '''def _require_current_recipe(recipe: EphemeralWorkspaceRecipe, now: float | None = None) -> float:
    current = time.time() if now is None else _finite(now, "now")
    if current >= recipe.expires_at_epoch_seconds:''',
    '''def _require_current_recipe(recipe: EphemeralWorkspaceRecipe, now: float | None = None) -> float:
    current = _trusted_now(now)
    if current >= recipe.expires_at_epoch_seconds:''',
    "recipe trusted clock",
)
text = replace_once(
    text,
    '''    current = time.time() if now is None else _finite(now, "now")
    nonce = _exact_string(activation_nonce, "activation_nonce", pattern=_ID)''',
    '''    current = _trusted_now(now)
    nonce = _exact_string(activation_nonce, "activation_nonce", pattern=_ID)''',
    "admission trusted clock",
)
text = replace_once(
    text,
    '''def _cleanup_workspace_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    reason: str,
) -> dict[str, Any]:
    record = _workspace(store, workspace_id)
    if record["state"] == "DISSOLVED":
        receipt = dict(record.get("cleanup_receipt", {}))
        return {"ok": bool(receipt.get("cleanup_verified", True)), **receipt, "state": "DISSOLVED"}
    if record["state"] != "DISSOLVING":
        moved = store.transition_workspace_v2(workspace_id, record["state"], "DISSOLVING",
                                              terminal_reason=reason)
        if not moved.get("ok"):
            record = _workspace(store, workspace_id)
            if record["state"] == "DISSOLVED":
                receipt = dict(record.get("cleanup_receipt", {}))
                return {"ok": bool(receipt.get("cleanup_verified", True)), **receipt,
                        "state": "DISSOLVED"}
            if record["state"] != "DISSOLVING":
                raise ValueError("workspace cleanup lost its state race")
        else:
            record = _workspace(store, workspace_id)
''',
    '''def _cleanup_workspace_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    reason: str,
) -> dict[str, Any]:
    record = _workspace(store, workspace_id)
    if record["state"] == "DISSOLVED":
        receipt = dict(record.get("cleanup_receipt", {}))
        return {"ok": bool(receipt.get("cleanup_verified", True)), **receipt, "state": "DISSOLVED"}
    if record["state"] != "DISSOLVING":
        moved = store.transition_workspace_v2(workspace_id, record["state"], "DISSOLVING",
                                              terminal_reason=reason)
        if not moved.get("ok"):
            record = _workspace(store, workspace_id)
            if record["state"] == "DISSOLVED":
                receipt = dict(record.get("cleanup_receipt", {}))
                return {"ok": bool(receipt.get("cleanup_verified", True)), **receipt,
                        "state": "DISSOLVED"}
            if record["state"] in _TERMINAL_PREP:
                retry = store.transition_workspace_v2(
                    workspace_id, record["state"], "DISSOLVING", terminal_reason=reason,
                )
                if retry.get("ok"):
                    record = _workspace(store, workspace_id)
                else:
                    record = _workspace(store, workspace_id)
                    if record["state"] == "DISSOLVED":
                        receipt = dict(record.get("cleanup_receipt", {}))
                        return {"ok": bool(receipt.get("cleanup_verified", True)), **receipt,
                                "state": "DISSOLVED"}
                    if record["state"] != "DISSOLVING":
                        raise ValueError("workspace cleanup lost its state race")
            elif record["state"] != "DISSOLVING":
                raise ValueError("workspace cleanup lost its state race")
        else:
            record = _workspace(store, workspace_id)
''',
    "terminal cleanup race convergence",
)
text = replace_once(
    text,
    '''def _expire_if_needed(workspace_id: str, *, store: EphemeralRegistryStore, now: float | None = None) -> None:
    record = _workspace(store, workspace_id)
    current = time.time() if now is None else _finite(now, "now")
    if current < record["expires_at"] or record["state"] == "DISSOLVED":''',
    '''def _expire_if_needed(workspace_id: str, *, store: EphemeralRegistryStore, now: float | None = None) -> None:
    record = _workspace(store, workspace_id)
    current = _trusted_now(now)
    if current < record["expires_at"] or record["state"] == "DISSOLVED":''',
    "expiry trusted clock",
)
text = replace_once(
    text,
    '''    started = time.time() if now is None else _finite(now, "now")
    upstream_digests = [receipts[parent]["receipt_digest"] for parent in sorted(parents[node_key])]''',
    '''    started = _trusted_now(now)
    upstream_digests = [receipts[parent]["receipt_digest"] for parent in sorted(parents[node_key])]''',
    "execution trusted clock",
)
text = replace_once(
    text,
    '''    current = time.time() if now is None else _finite(now, "now")
    expiry = _finite(expires_at, "expires_at")''',
    '''    current = _trusted_now(now)
    expiry = _finite(expires_at, "expires_at")''',
    "certificate preparation trusted clock",
)
text = replace_once(
    text,
    '''    current = time.time() if now is None else _finite(now, "now")
    if current >= value["expires_at"] and value["status"] != "CLOSED":''',
    '''    current = _trusted_now(now)
    if current >= value["expires_at"] and value["status"] != "CLOSED":''',
    "certificate validation trusted clock",
)
write(path, text)


# Regression coverage for concurrent terminal convergence and backdated authority bypasses.
path = "tests/test_aura_ephemeral_workspace_runtime_v2.py"
text = read(path)
if "def test_cleanup_converges_when_cancellation_wins_first_transition" in text:
    raise SystemExit("second-round regressions already present")
addition = r'''


def test_cleanup_converges_when_cancellation_wins_first_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    original = store.transition_workspace_v2
    injected = {"done": False}

    def racing_transition(workspace: str, expected: Any, target: str, *, terminal_reason: str = ""):
        if not injected["done"] and expected == "ACTIVE" and target == "DISSOLVING":
            injected["done"] = True
            assert original(
                workspace, "ACTIVE", "CANCELLING", terminal_reason="concurrent_cancel",
            )["ok"]
            return {"ok": False, "error": "stale_workspace_state"}
        return original(workspace, expected, target, terminal_reason=terminal_reason)

    monkeypatch.setattr(store, "transition_workspace_v2", racing_transition)
    result = runtime.dissolve_workspace_v2(workspace_id, store=store, reason="explicit_cleanup")
    assert injected["done"] is True
    assert result["ok"] and result["state"] == "DISSOLVED"
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_backdated_now_cannot_bypass_workspace_expiry(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    assert store._conn is not None
    store._conn.execute(
        "UPDATE ephemeral_workspaces_v2 SET expires_at = ? WHERE workspace_id = ?",
        (time.time() - 1, workspace_id),
    )
    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime.execute_workspace_node_v2(
            workspace_id, graph["entry_node_ids"][0], params={}, store=store,
            adapter_registry=registry, now=time.time() - 3600,
        )
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_certificate_mutation_rejects_backdated_authority_after_expiry(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path / "prepare")
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    assert store._conn is not None
    store._conn.execute(
        "UPDATE ephemeral_workspaces_v2 SET expires_at = ? WHERE workspace_id = ?",
        (time.time() - 1, workspace_id),
    )
    with pytest.raises(ValueError, match="certificate expiry"):
        runtime.prepare_spatial_action_certificate_v2(
            workspace_id, store=store,
            principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
            subject_refs=["source:aura"], target_refs=["forge:candidate"],
            policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
            runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
            assumptions_digest=D["3"], cost_microusd=0, reversible=True,
            proof_obligations=["EXACT_SOURCE"], nonce="cert-backdated-prepare",
            expires_at=time.time() + 120, now=time.time() - 3600,
        )

    _, registry2, _, _, store2, workspace_id2 = _admitted(tmp_path / "advance")
    runtime.activate_workspace_v2(
        workspace_id2, store=store2, adapter_registry=registry2, repo_root=str(ROOT),
    )
    prepared = runtime.prepare_spatial_action_certificate_v2(
        workspace_id2, store=store2,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-backdated-advance",
        expires_at=time.time() + 120,
    )["certificate"]
    assert store2._conn is not None
    store2._conn.execute(
        "UPDATE ephemeral_workspaces_v2 SET expires_at = ? WHERE workspace_id = ?",
        (time.time() - 1, workspace_id2),
    )
    with pytest.raises(ValueError, match="workspace_certificate_invalidated"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id2, store=store2, expected_status="PREPARED",
            evidence_digest=D["4"], owner="spatial_runtime",
            timestamp=prepared["issued_at"],
        )
'''
write(path, text.rstrip() + addition + "\n")
