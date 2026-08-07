from pathlib import Path


path = Path("aura_ephemeral_adapter_registry.py")
text = path.read_text(encoding="utf-8")
old = '''    def execute(self, adapter_id: str, *, params: dict[str, Any] | None = None,
                lease_active: bool = True) -> dict[str, Any]:
        params = {} if params is None else _strict_mapping(params, "params")
        meta = self._adapters.get(adapter_id)'''
new = '''    def execute(self, adapter_id: str, *, params: dict[str, Any] | None = None,
                lease_active: bool = True) -> dict[str, Any]:
        try:
            params = {} if params is None else _strict_mapping(params, "params")
        except ValueError as exc:
            return {"ok": False, "error": f"invalid_adapter_params: {exc}",
                    "failure_class": "structural",
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        meta = self._adapters.get(adapter_id)'''
if text.count(old) != 1:
    raise SystemExit("adapter params normalization marker mismatch")
path.write_text(text.replace(old, new, 1), encoding="utf-8")


test_path = Path("tests/test_aura_ephemeral_workspace_runtime_v2.py")
tests = test_path.read_text(encoding="utf-8")
marker = '''    assert result["error"] == "adapter_result_missing_status"
    assert result["failure_class"] == "structural"
'''
addition = '''    assert result["error"] == "adapter_result_missing_status"
    assert result["failure_class"] == "structural"

    malformed = registry.execute("adapter.redeclare", params={1: "bad"})  # type: ignore[dict-item]
    assert malformed["ok"] is False
    assert malformed["failure_class"] == "structural"
    assert malformed["error"].startswith("invalid_adapter_params:")
'''
if tests.count(marker) != 1:
    raise SystemExit("adapter params regression marker mismatch")
tests = tests.replace(marker, addition, 1)
test_path.write_text(tests.rstrip() + "\n", encoding="utf-8")

# Trigger the already-installed validated helper workflow.
