from pathlib import Path
import re

WORKFLOW = Path(".github/workflows/sync-analysis-codemap.yml")


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_pr_validation_is_read_only_and_head_stable() -> None:
    src = text()
    assert "permissions:\n  contents: read" in src
    assert "pull_request_target" not in src
    assert "branches:\n      - main" in src
    assert "TARGET_BRANCH" not in src
    assert 'push origin HEAD:"${TARGET_BRANCH}"' not in src
    assert "MATERIALIZATION_REQUIRED" in src
    assert "PR validation never pushes" in src


def test_only_main_materializer_owns_write_permission_and_push() -> None:
    src = text()
    assert src.count("contents: write") == 1
    assert "materialize-main:" in src
    assert "github.ref == 'refs/heads/main'" in src
    assert src.count("push origin HEAD:main") == 1


def test_credential_diagnostics_are_nonpersistent() -> None:
    src = text()
    assert "set -x" not in src
    assert "codemap-push.log" not in src
    assert "| tee" not in src
    upload = src.split("Upload generated maps and generation attestation", 1)[1]
    assert "AUTH_HEADER" not in upload
    assert "GH_TOKEN" not in upload


def test_actions_are_full_sha_pinned() -> None:
    src = text()
    expected = {
        "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
        "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        "actions/download-artifact": "634f93cb2916e3fdff6788551b99b062d0335ce0",
    }
    for action, sha in expected.items():
        assert f"uses: {action}@{sha}" in src

    for match in re.findall(r"uses:\s*([^\s]+)", src):
        ref = match.rsplit("@", 1)[-1]
        assert re.fullmatch(r"[0-9a-f]{40}", ref), match


def test_generation_attestation_binds_currentness_environment_and_outputs() -> None:
    src = text()
    for field in (
        "AuraCodemapGenerationAttestationV1",
        "'head_sha':",
        "'python_version':",
        "'source_rows':",
        "'output_rows':",
        "'resolved_environment_sha256':",
        "'generated_set_sha256':",
        "'drift_class':",
        "'authority': False",
        "'quality_pass': False",
        "'effect_authorized': False",
    ):
        assert field in src


def test_drift_classes_and_supersession_contract() -> None:
    src = text()
    for drift in ("NO_DRIFT", "VOLATILE_ONLY", "MEANINGFUL_GENERATED_DRIFT"):
        assert drift in src
    assert "cancel-in-progress: true" in src


def test_existing_navigation_integrity_gates_are_retained() -> None:
    src = text()
    for gate in (
        "python scripts/aura_navigation_refresh.py --root .",
        "python scripts/aura_source_anchor_map.py --root . --check",
        "python -m aura_codemap_verify",
        "git diff --check",
        "test -s .aura/CODEMAP.json",
        "test -s .aura/SOURCE_ANCHORS.md",
    ):
        assert gate in src
