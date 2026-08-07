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


# Adapter registry: portable implementation identity, identity-based redeclaration,
# and explicit result success/failure status.
path = "aura_ephemeral_adapter_registry.py"
text = read(path)
text = replace_once(text, "import json\nimport marshal\n", "import json\n", "remove marshal")
text = replace_block(
    text,
    "def _callable_digest(implementation: Callable[..., Any]) -> str:\n",
    "def _strict_mapping(value: Any, name: str) -> dict[str, Any]:\n",
    '''def _callable_digest(implementation: Callable[..., Any]) -> str:
    """Bind a Python implementation to portable source identity."""
    try:
        source = inspect.getsource(implementation).encode("utf-8")
    except (OSError, TypeError) as exc:
        raise ValueError(
            "adapter implementation source is unavailable for stable identity"
        ) from exc
    identity = {
        "module": str(getattr(implementation, "__module__", "")),
        "qualname": str(getattr(implementation, "__qualname__", "")),
        "source_sha256": hashlib.sha256(source).hexdigest(),
    }
    return _digest(identity)''',
    "portable callable digest",
)
text = replace_block(
    text,
    "    def declare(\n",
    "    def get(self, adapter_id: str) -> dict[str, Any]:\n",
    '''    def declare(
        self,
        meta: AdapterMetadata,
        *,
        implementation: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if type(meta) is not AdapterMetadata:
            raise ValueError("meta must be an exact AdapterMetadata record")
        meta.operational_status = "OPERATIONAL" if implementation is not None else "DECLARED"
        meta.finalize_identity(implementation)
        if meta.adapter_id in self._adapters:
            existing = self._adapters[meta.adapter_id]
            if existing.adapter_digest != meta.adapter_digest:
                return {"ok": False, "error": f"adapter_already_declared: {meta.adapter_id}"}
        self._adapters[meta.adapter_id] = meta
        if implementation is not None:
            self._implementations[meta.adapter_id] = implementation
        return {
            "ok": True,
            "adapter_id": meta.adapter_id,
            "status": meta.operational_status,
            "adapter_digest": meta.adapter_digest,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }''',
    "adapter declare",
)
text = replace_block(
    text,
    "    def execute(self, adapter_id: str, *, params: dict[str, Any] | None = None,\n",
    "    def list_adapters(self) -> dict[str, Any]:\n",
    '''    def execute(self, adapter_id: str, *, params: dict[str, Any] | None = None,
                lease_active: bool = True) -> dict[str, Any]:
        params = {} if params is None else _strict_mapping(params, "params")
        meta = self._adapters.get(adapter_id)
        if not meta:
            return {"ok": False, "error": f"unknown_adapter: {adapter_id}", "status": "DENIED",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if meta.revocation_state == "REVOKED" or meta.operational_status == "DENIED":
            return {"ok": False, "error": f"adapter_revoked: {adapter_id}", "status": "DENIED",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if meta.operational_status != "OPERATIONAL":
            return {"ok": False, "error": f"adapter_not_operational: {adapter_id} ({meta.operational_status})",
                    "status": meta.operational_status,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if lease_active is not True:
            return {"ok": False, "error": "lease_revoked: adapter calls blocked",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        impl = self._implementations.get(adapter_id)
        if impl is None:
            return {"ok": False, "error": f"no_implementation: {adapter_id}", "status": "NOT_OPERATIONAL",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        try:
            result = impl(**params)
        except Exception as exc:
            return {"ok": False, "error": f"adapter_callback_failed: {type(exc).__name__}: {exc}",
                    "adapter": adapter_id, "failure_class": "environment",
                    "adapter_digest": meta.adapter_digest,
                    "implementation_digest": meta.implementation_digest,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if not isinstance(result, Mapping):
            return {"ok": False, "error": "adapter_result_must_be_mapping", "adapter": adapter_id,
                    "failure_class": "structural",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        detached = dict(result)
        if type(detached.get("ok")) is not bool:
            return {"ok": False, "error": "adapter_result_missing_status", "adapter": adapter_id,
                    "failure_class": "structural",
                    "adapter_digest": meta.adapter_digest,
                    "implementation_digest": meta.implementation_digest,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        detached["adapter"] = adapter_id
        detached["operational_status"] = "OPERATIONAL"
        detached["adapter_digest"] = meta.adapter_digest
        detached["implementation_digest"] = meta.implementation_digest
        detached["patch_authority"] = PATCH_AUTHORITY
        detached["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return detached''',
    "adapter execute",
)
write(path, text)


# Registry store: finite temporal fields, static evidence UPDATE, certificate CAS,
# deterministic clock injection, and terminal expiry selection.
path = "aura_ephemeral_registry_store.py"
text = read(path)
text = replace_once(text, "import json\nimport sqlite3\n", "import json\nimport math\nimport sqlite3\n", "store math import")
text = replace_once(
    text,
    '''        if set(record) - {
            *required, "lease_status", "sandbox_path", "node_receipts", "failure_records",
            "usage_json", "cleanup_receipt", "certificate_json", "terminal_reason",
        } or not required <= set(record):
            raise ValueError("workspace record fields are incomplete or unknown")
        conn = self._conn''',
    '''        if set(record) - {
            *required, "lease_status", "sandbox_path", "node_receipts", "failure_records",
            "usage_json", "cleanup_receipt", "certificate_json", "terminal_reason",
        } or not required <= set(record):
            raise ValueError("workspace record fields are incomplete or unknown")
        for name in ("created_at", "expires_at"):
            value = record[name]
            if type(value) not in {int, float} or type(value) is bool or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be a finite number")
        if float(record["expires_at"]) <= float(record["created_at"]):
            raise ValueError("workspace expiration must be after creation")
        conn = self._conn''',
    "workspace timestamp validation",
)
text = replace_block(
    text,
    "    def update_workspace_v2(self, workspace_id: str, **fields: Any) -> dict[str, Any]:\n",
    "    def commit_workspace_v2_node_execution(\n",
    '''    def update_workspace_v2(self, workspace_id: str, **fields: Any) -> dict[str, Any]:
        """Update only bounded V2 evidence fields; lifecycle state is CAS-only."""
        columns = (
            "sandbox_path", "node_receipts", "failure_records", "usage_json",
            "cleanup_receipt", "certificate_json", "lease_status", "terminal_reason",
        )
        allowed = set(columns)
        if not fields or not set(fields) <= allowed:
            raise ValueError("unknown or empty workspace evidence update")
        encoded: dict[str, Any] = {}
        for name, value in fields.items():
            encoded[name] = (
                self._workspace_v2_json(value, name)
                if name in {"node_receipts", "failure_records", "usage_json",
                            "cleanup_receipt", "certificate_json"}
                else value
            )
        params: list[Any] = []
        for name in columns:
            params.extend((1 if name in encoded else 0, encoded.get(name)))
        params.extend((time.time(), workspace_id))
        conn = self._conn
        assert conn is not None
        cur = conn.execute(
            """
            UPDATE ephemeral_workspaces_v2 SET
              sandbox_path = CASE WHEN ? THEN ? ELSE sandbox_path END,
              node_receipts = CASE WHEN ? THEN ? ELSE node_receipts END,
              failure_records = CASE WHEN ? THEN ? ELSE failure_records END,
              usage_json = CASE WHEN ? THEN ? ELSE usage_json END,
              cleanup_receipt = CASE WHEN ? THEN ? ELSE cleanup_receipt END,
              certificate_json = CASE WHEN ? THEN ? ELSE certificate_json END,
              lease_status = CASE WHEN ? THEN ? ELSE lease_status END,
              terminal_reason = CASE WHEN ? THEN ? ELSE terminal_reason END,
              updated_at = ?
            WHERE workspace_id = ?
            """,
            tuple(params),
        )
        return {"ok": cur.rowcount == 1, "workspace_id": workspace_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    def commit_workspace_v2_certificate(
        self,
        workspace_id: str,
        *,
        expected_certificate: dict[str, Any],
        certificate: dict[str, Any],
        now: float | None = None,
    ) -> dict[str, Any]:
        """CAS one certificate while the workspace retains execution authority."""
        if type(expected_certificate) is not dict or type(certificate) is not dict:
            raise ValueError("certificate CAS values must be exact objects")
        current_time = time.time() if now is None else now
        if type(current_time) not in {int, float} or type(current_time) is bool:
            raise ValueError("now must be a finite number")
        current_time = float(current_time)
        if not math.isfinite(current_time):
            raise ValueError("now must be a finite number")
        expected_json = self._workspace_v2_json(expected_certificate, "expected_certificate")
        certificate_json = self._workspace_v2_json(certificate, "certificate")
        conn = self._conn
        assert conn is not None
        cur = conn.execute(
            """
            UPDATE ephemeral_workspaces_v2
            SET certificate_json = ?, updated_at = ?
            WHERE workspace_id = ?
              AND state = 'ACTIVE'
              AND lease_status = 'ACTIVE'
              AND expires_at > ?
              AND certificate_json = ?
            """,
            (certificate_json, current_time, workspace_id, current_time, expected_json),
        )
        if cur.rowcount == 1:
            return {"ok": True, "workspace_id": workspace_id,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        current = self.get_workspace_v2(workspace_id)
        workspace = current.get("workspace", {})
        invalidated = (
            not current.get("ok")
            or workspace.get("state") != "ACTIVE"
            or workspace.get("lease_status") != "ACTIVE"
            or current_time >= workspace.get("expires_at", 0)
        )
        return {"ok": False,
                "error": "workspace_certificate_invalidated" if invalidated else "stale_workspace_certificate",
                "workspace_id": workspace_id,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY}''',
    "static evidence update and certificate CAS",
)
text = replace_block(
    text,
    "    def is_workspace_v2_lease_active(self, workspace_id: str) -> bool:\n",
    "    def close(self) -> None:\n",
    '''    def is_workspace_v2_lease_active(self, workspace_id: str, *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        if type(current) not in {int, float} or type(current) is bool:
            raise ValueError("now must be a finite number")
        current = float(current)
        if not math.isfinite(current):
            raise ValueError("now must be a finite number")
        conn = self._conn
        assert conn is not None
        row = conn.execute(
            "SELECT lease_status, expires_at, state FROM ephemeral_workspaces_v2 WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        return bool(row and row[0] == "ACTIVE" and current < row[1]
                    and row[2] not in {"DISSOLVING", "DISSOLVED"})

    def list_expired_workspaces_v2(self, *, now: float | None = None) -> dict[str, Any]:
        current = time.time() if now is None else now
        if type(current) not in {int, float} or type(current) is bool:
            raise ValueError("now must be a finite number")
        current = float(current)
        if not math.isfinite(current):
            raise ValueError("now must be a finite number")
        conn = self._conn
        assert conn is not None
        rows = conn.execute(
            "SELECT workspace_id FROM ephemeral_workspaces_v2 "
            "WHERE expires_at <= ? AND state NOT IN ('DISSOLVING', 'DISSOLVED')",
            (current,),
        ).fetchall()
        values = [row[0] for row in rows]
        return {"ok": True, "workspace_ids": values, "count": len(values),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}''',
    "lease clock and expired listing",
)
write(path, text)


# Runtime: executable wall-time floor, path escape closure, cleanup race tolerance,
# explicit budget exception typing, monotonic cancellation, and certificate CAS/owner enforcement.
path = "aura_ephemeral_workspace_runtime_v2.py"
text = read(path)
text = replace_once(text, "MAX_CERTIFICATE_RECEIPTS = 5", "MAX_CERTIFICATE_RECEIPTS = 4", "certificate receipt ceiling")
text = replace_once(
    text,
    '''_CERT_TRANSITIONS = {
    "PREPARED": "OPEN",
    "OPEN": "APPROVED",
    "APPROVED": "EXECUTED",
    "EXECUTED": "CLOSED",
}
''',
    '''_CERT_TRANSITIONS = {
    "PREPARED": "OPEN",
    "OPEN": "APPROVED",
    "APPROVED": "EXECUTED",
    "EXECUTED": "CLOSED",
}


class _BudgetExceeded(ValueError):
    """Internal marker for runtime-owned resource budget exhaustion."""
''',
    "budget marker",
)
text = replace_once(
    text,
    '''    value = _recipe(recipe)
    _require_current_recipe(value, now)
    bindings = _exact_mapping(adapter_bindings, "adapter_bindings")''',
    '''    value = _recipe(recipe)
    _require_current_recipe(value, now)
    if value.budgets.wall_time_ms < 1:
        raise ValueError("wall_time_ms must be at least 1 for executable workspaces")
    bindings = _exact_mapping(adapter_bindings, "adapter_bindings")''',
    "compiler wall-time floor",
)
text = replace_once(
    text,
    '''    for name, value in budgets.items():
        _integer(value, f"budget.{name}", 0, 10_000_000_000)''',
    '''    for name, value in budgets.items():
        minimum = 1 if name == "wall_time_ms" else 0
        _integer(value, f"budget.{name}", minimum, 10_000_000_000)''',
    "validator wall-time floor",
)
text = replace_block(
    text,
    "def _validate_temp_paths(value: Any, temp_dir: str, *, key: str = \"\") -> None:\n",
    "def _approval_valid(approval: Any, *, workspace_id: str, graph_digest: str, node_id: str) -> bool:\n",
    '''def _validate_temp_paths(value: Any, temp_dir: str, *, key: str = "") -> None:
    if isinstance(value, dict):
        for child_key, child in value.items():
            _validate_temp_paths(child, temp_dir, key=child_key)
        return
    if isinstance(value, list):
        for child in value:
            _validate_temp_paths(child, temp_dir, key=key)
        return
    if type(value) is not str:
        return
    path_keys = {"path", "temp_dir", "output_path", "artifact_path"}
    parts = [part for part in re.split(r"[\\/]+", value) if part]
    windows_absolute = re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", value) is not None
    candidate = Path(value)
    path_sensitive = key in path_keys or candidate.is_absolute() or windows_absolute or ".." in parts
    if not path_sensitive:
        return
    if windows_absolute and not candidate.is_absolute():
        raise ValueError("adapter output path escapes the workspace sandbox")
    root = Path(temp_dir).resolve()
    candidate = candidate if candidate.is_absolute() else root / candidate
    if candidate.is_symlink():
        raise ValueError("adapter output contains a symlink path")
    try:
        candidate.resolve().relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("adapter output path escapes the workspace sandbox") from exc''',
    "recursive temp path validation",
)
text = replace_block(
    text,
    "def _cleanup_workspace_v2(\n",
    "def _expire_if_needed(workspace_id: str, *, store: EphemeralRegistryStore, now: float | None = None) -> None:\n",
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
    lease = store.revoke_workspace_v2_lease(workspace_id, reason=reason)
    temp_dir = record.get("sandbox_path", "")
    if temp_dir:
        destroy_sandbox(temp_dir)
    verified = verify_dissolution(temp_dir, lease.get("ok", False))
    receipt = {
        "workspace_id": workspace_id,
        "reason": reason,
        "lease_revoked": bool(lease.get("ok")),
        "temp_dir_removed": bool(verified.get("temp_dir_removed")),
        "cleanup_verified": bool(verified.get("ok")),
        "cleaned_at": time.time(),
        "cleanup_digest": "",
    }
    receipt["cleanup_digest"] = stable_digest({k: v for k, v in receipt.items() if k != "cleanup_digest"})
    store.update_workspace_v2(workspace_id, cleanup_receipt=receipt)
    if not receipt["cleanup_verified"]:
        return {"ok": False, **receipt, "state": "DISSOLVING"}
    moved = store.transition_workspace_v2(workspace_id, "DISSOLVING", "DISSOLVED",
                                          terminal_reason=reason)
    if not moved.get("ok"):
        current = _workspace(store, workspace_id)
        if current["state"] == "DISSOLVED":
            final_receipt = dict(current.get("cleanup_receipt", receipt))
            return {"ok": bool(final_receipt.get("cleanup_verified", True)), **final_receipt,
                    "state": "DISSOLVED"}
        raise ValueError("workspace cleanup could not finalize dissolution")
    return {"ok": True, **receipt, "state": "DISSOLVED"}''',
    "cleanup race tolerance",
)
text = replace_once(
    text,
    '''    if not store.is_workspace_v2_lease_active(workspace_id):
        return {"ok": False, "error": "workspace_lease_revoked"}''',
    '''    if not store.is_workspace_v2_lease_active(workspace_id, now=now):
        return {"ok": False, "error": "workspace_lease_revoked"}''',
    "lease check clock",
)
text = replace_once(
    text,
    '''            lease_active=store.is_workspace_v2_lease_active(workspace_id),''',
    '''            lease_active=store.is_workspace_v2_lease_active(workspace_id, now=started),''',
    "adapter lease clock",
)
text = replace_once(
    text,
    '''        if encoded_size > min(graph["budgets"]["output_bytes"], MAX_OUTPUT_BYTES):
            raise ValueError("adapter result exceeds output budget")''',
    '''        if encoded_size > min(graph["budgets"]["output_bytes"], MAX_OUTPUT_BYTES):
            raise _BudgetExceeded("adapter result exceeds output budget")''',
    "owned budget exception",
)
text = replace_once(
    text,
    '''        if isinstance(original, Exception):
            failure_class = "budget" if "budget" in str(original).lower() else "structural"
            return _fail_workspace_v2(''',
    '''        if isinstance(original, Exception):
            failure_class = "budget" if isinstance(original, _BudgetExceeded) else "structural"
            return _fail_workspace_v2(''',
    "budget failure classification",
)
text = replace_block(
    text,
    "def cancel_workspace_v2(workspace_id: str, *, store: EphemeralRegistryStore,\n",
    "def invalidate_workspace_v2(workspace_id: str, *, store: EphemeralRegistryStore,\n",
    '''def cancel_workspace_v2(workspace_id: str, *, store: EphemeralRegistryStore,
                        reason: str = "human_cancelled") -> dict[str, Any]:
    record = _workspace(store, workspace_id)
    if record["state"] == "DISSOLVED":
        return {"ok": False, "error": "workspace_already_dissolved"}
    if record["state"] in _TERMINAL_PREP or record["state"] == "DISSOLVING":
        terminal_reason = record.get("terminal_reason") or reason
        return _cleanup_workspace_v2(workspace_id, store=store, reason=terminal_reason)
    moved = store.transition_workspace_v2(workspace_id, record["state"], "CANCELLING",
                                          terminal_reason=reason)
    if not moved.get("ok"):
        return moved
    return _cleanup_workspace_v2(workspace_id, store=store, reason="cancelled")''',
    "monotonic cancel",
)
text = replace_once(
    text,
    '''    validate_spatial_action_certificate_v2(certificate)
    store.update_workspace_v2(workspace_id, certificate_json=certificate)
    return {"ok": True, "certificate": certificate, "authorized": False,''',
    '''    validate_spatial_action_certificate_v2(certificate)
    committed = store.commit_workspace_v2_certificate(
        workspace_id,
        expected_certificate={},
        certificate=certificate,
        now=current,
    )
    if not committed.get("ok"):
        raise ValueError(committed.get("error", "action certificate state changed"))
    return {"ok": True, "certificate": certificate, "authorized": False,''',
    "certificate prepare CAS",
)
text = replace_block(
    text,
    "def advance_spatial_action_certificate_v2(\n",
    "class WorkspaceSessionV2:\n",
    '''def advance_spatial_action_certificate_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    expected_status: str,
    evidence_digest: str,
    owner: str,
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Advance one exact receipt step under ACTIVE-state certificate CAS."""
    record = _workspace(store, workspace_id)
    if record["state"] != "ACTIVE":
        raise ValueError("action certificate advancement requires an active workspace")
    current = record["certificate_json"]
    if not current:
        raise ValueError("workspace has no action certificate")
    certificate = validate_spatial_action_certificate_v2(
        current, expected_certificate=current, workspace_record=record,
    )
    status = _exact_string(expected_status, "expected_status")
    owner_id = _exact_string(owner, "receipt owner", pattern=_ID)
    if certificate["status"] != status or status not in _CERT_TRANSITIONS:
        raise ValueError("stale or illegal certificate transition")
    next_status = _CERT_TRANSITIONS[status]
    receipt_type = {
        "PREPARED": "OPEN", "OPEN": "APPROVAL", "APPROVED": "EXECUTION",
        "EXECUTED": "OUTCOME",
    }[status]
    moment = time.time() if timestamp is None else _finite(timestamp, "timestamp")
    if moment >= certificate["expires_at"]:
        raise ValueError("certificate transition is expired")
    if certificate["receipts"] and moment < certificate["receipts"][-1]["timestamp"]:
        raise ValueError("certificate transition timestamp regressed")
    runtime_owners = {"spatial_runtime", "workspace_runtime"}
    if status in {"OPEN", "APPROVED"} and owner_id in runtime_owners:
        raise ValueError("spatial/runtime layer cannot self-authorize execution")
    if status == "EXECUTED" and owner_id in runtime_owners:
        raise ValueError("spatial/runtime layer cannot self-prove outcome")
    updated = copy.deepcopy(certificate)
    updated["status"] = next_status
    updated["receipts"].append(_receipt(
        receipt_type=receipt_type,
        certificate_id=certificate["certificate_id"],
        timestamp=moment,
        evidence_digest=evidence_digest,
        owner=owner_id,
    ))
    updated["certificate_digest"] = stable_digest(_certificate_body(updated))
    validate_spatial_action_certificate_v2(updated, workspace_record=record)
    committed = store.commit_workspace_v2_certificate(
        workspace_id,
        expected_certificate=certificate,
        certificate=updated,
        now=moment,
    )
    if not committed.get("ok"):
        raise ValueError(committed.get("error", "stale action certificate state"))
    return {"ok": True, "certificate": updated,
            "authorized": False,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}''',
    "certificate advance CAS",
)
write(path, text)


# JSON schemas mirror the executable/runtime ceilings.
path = "schemas/aura_workspace_execution_graph_v2.schema.json"
text = read(path)
text = replace_once(
    text,
    '''        "wall_time_ms": {
          "maximum": 10000000000,
          "minimum": 0,
          "type": "integer"
        }''',
    '''        "wall_time_ms": {
          "maximum": 10000000000,
          "minimum": 1,
          "type": "integer"
        }''',
    "graph schema wall-time floor",
)
write(path, text)

path = "schemas/aura_spatial_action_certificate_v2.schema.json"
text = read(path)
text = replace_once(
    text,
    '''      "maxItems": 5,
      "type": "array"
    },
    "requested_operation"''',
    '''      "maxItems": 4,
      "type": "array"
    },
    "requested_operation"''',
    "certificate schema receipt ceiling",
)
write(path, text)


# Regressions for reviewed boundary defects and positive reuse behavior.
path = "tests/test_aura_ephemeral_workspace_runtime_v2.py"
text = read(path)
if "def test_adapter_redeclaration_is_identity_based_and_status_is_explicit" in text:
    raise SystemExit("review regressions already present")
addition = r'''


def test_adapter_redeclaration_is_identity_based_and_status_is_explicit() -> None:
    registry = OperationalAdapterRegistry()
    first = AdapterMetadata(adapter_id="adapter.redeclare", implementation_ref="tests._ok_adapter")
    second = AdapterMetadata(adapter_id="adapter.redeclare", implementation_ref="tests._ok_adapter")
    assert registry.declare(first, implementation=_ok_adapter)["ok"]
    assert registry.declare(second, implementation=_ok_adapter)["ok"]
    assert first.adapter_digest == second.adapter_digest

    different = AdapterMetadata(
        adapter_id="adapter.redeclare", implementation_ref="tests._ok_adapter", version="2.0.0"
    )
    assert not registry.declare(different, implementation=_ok_adapter)["ok"]

    def missing_status(**params: Any) -> dict[str, Any]:
        return {"echo": params}

    meta = AdapterMetadata(adapter_id="adapter.missing-status", implementation_ref="tests.missing_status")
    assert registry.declare(meta, implementation=missing_status)["ok"]
    result = registry.execute("adapter.missing-status", params={})
    assert result["ok"] is False
    assert result["error"] == "adapter_result_missing_status"
    assert result["failure_class"] == "structural"


def test_compile_rejects_zero_wall_time_at_executable_boundary() -> None:
    recipe = _recipe()
    zero_budget = type(recipe.budgets)(**{**recipe.budgets.to_dict(), "wall_time_ms": 0})
    object.__setattr__(recipe, "budgets", zero_budget)
    registry, bindings = _registry(recipe)
    with pytest.raises(ValueError, match="wall_time_ms must be at least 1"):
        runtime.compile_workspace_execution_graph_v2(
            recipe, adapter_bindings=bindings, adapter_registry=registry,
        )


def test_store_rejects_nonfinite_v2_timestamps(tmp_path: Path) -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )
    store = EphemeralRegistryStore.for_tests(tmp_path)
    base = {
        "workspace_id": "workspace:v2:timestamp-test",
        "recipe_json": recipe.to_dict(),
        "recipe_digest": recipe.recipe_digest,
        "graph_json": graph,
        "graph_digest": graph["graph_digest"],
        "state": "ADMITTED",
        "created_at": time.time(),
        "expires_at": time.time() + 60,
        "activation_nonce": "timestamp-test-nonce",
    }
    for index, invalid in enumerate(("bad", float("nan"), float("inf"))):
        record = dict(base)
        record["workspace_id"] = f"workspace:v2:timestamp-test-{index}"
        record["activation_nonce"] = f"timestamp-test-nonce-{index}"
        record["created_at"] = invalid
        with pytest.raises(ValueError, match="created_at must be a finite number"):
            store.register_workspace_v2(record)


def test_arbitrary_key_absolute_and_traversal_paths_fail_closed(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]

    def hidden_absolute(**params: Any) -> dict[str, Any]:
        return {"ok": True, "untrusted": "/tmp/outside-hidden-key"}

    _, registry, _, _, store, workspace_id = _admitted(
        tmp_path / "hidden-absolute", overrides={first: hidden_absolute}
    )
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    result = runtime.execute_workspace_node_v2(
        workspace_id, first, params={}, store=store, adapter_registry=registry,
    )
    assert not result["ok"] and "escapes" in result["error"]

    def hidden_traversal(**params: Any) -> dict[str, Any]:
        return {"ok": True, "untrusted": "../outside-hidden-key"}

    _, registry2, _, _, store2, workspace_id2 = _admitted(
        tmp_path / "hidden-traversal", overrides={first: hidden_traversal}
    )
    runtime.activate_workspace_v2(
        workspace_id2, store=store2, adapter_registry=registry2, repo_root=str(ROOT),
    )
    result2 = runtime.execute_workspace_node_v2(
        workspace_id2, first, params={}, store=store2, adapter_registry=registry2,
    )
    assert not result2["ok"] and "escapes" in result2["error"]


def test_partial_reexecution_reuses_complete_unchanged_receipt_set(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    _execute_all(workspace_id, graph, store, registry)
    receipts = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["node_receipts"]
    plan = runtime.partial_reexecution_plan_v2(
        graph, prior_receipts=receipts, changed_node_ids=[],
    )
    assert plan["reexecute_node_ids"] == []
    assert set(plan["reusable_node_ids"]) == {node["node_id"] for node in graph["nodes"]}


def test_action_certificate_runtime_owner_cannot_self_approve(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-self-approve",
        expires_at=time.time() + 120,
    )
    runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="PREPARED",
        evidence_digest=D["4"], owner="spatial_runtime",
    )
    with pytest.raises(ValueError, match="self-authorize"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="OPEN",
            evidence_digest=D["5"], owner="spatial_runtime",
        )


def test_action_certificate_requires_active_state_and_uses_cas(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    prepared = runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-cas-test",
        expires_at=time.time() + 120,
    )["certificate"]
    stale = dict(prepared)
    stale["status"] = "OPEN"
    cas = store.commit_workspace_v2_certificate(
        workspace_id,
        expected_certificate=stale,
        certificate=prepared,
    )
    assert cas["ok"] is False and cas["error"] == "stale_workspace_certificate"

    moved = store.transition_workspace_v2(workspace_id, "ACTIVE", "CANCELLING")
    assert moved["ok"]
    with pytest.raises(ValueError, match="active workspace"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="PREPARED",
            evidence_digest=D["4"], owner="spatial_runtime",
        )
    cleanup = runtime.dissolve_workspace_v2(workspace_id, store=store, reason="test_cleanup")
    assert cleanup["ok"] and cleanup["state"] == "DISSOLVED"
'''
write(path, text.rstrip() + addition + "\n")
