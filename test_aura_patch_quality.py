"""
Tests for the Aura Live Architect patch-quality upgrade.

Covers all 7 required test scenarios:
1. Corrupt hunk rejection
2. Valid unified diff acceptance
3. Prose-only rejection
4. Before/after local diff generation
5. One-shot patch repair
6. Failed repair blocks hot-swap
7. Missing-test warning triggers temp regression test generation
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

import pytest

# Ensure the repo root is on the path
_REPO_ROOT = Path(__file__).parent.resolve()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_patch_quality_gate import (
    BeforeAfterReplacement,
    generate_unified_diff_from_before_after,
    parse_before_after_response,
    preflight_patch,
    PatchPreflightResult,
)
from aura_patch_repair import repair_patch_format, PatchRepairResult
from aura_test_gap_filler import (
    detect_missing_test_findings,
    fill_test_gap,
    TestGapFillerResult,
)
from aura_builder_context import (
    build_builder_context_packet,
    BuilderContextPacket,
    render_context_packet_prompt,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_repo():
    """Create a temporary repo with a simple Python file for testing."""
    temp_root = Path(tempfile.mkdtemp(prefix="aura_test_repo_"))
    target_file = temp_root / "sample_module.py"
    target_file.write_text(
        '"""Sample module for testing."""\n'
        "\n"
        "import os\n"
        "from typing import Any\n"
        "\n"
        "def greet(name: str) -> str:\n"
        '    """Greet someone."""\n'
        '    return f"Hello, {name}!"\n'
        "\n"
        "def add(a: int, b: int) -> int:\n"
        '    """Add two numbers."""\n'
        "    return a + b\n",
        encoding="utf-8",
    )
    try:
        yield temp_root
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


@pytest.fixture
def temp_repo_with_git(temp_repo):
    """Initialize a git repo in the temp directory."""
    import subprocess
    subprocess.run(["git", "init"], cwd=str(temp_repo), capture_output=True, check=False)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(temp_repo), capture_output=True, check=False)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(temp_repo), capture_output=True, check=False)
    subprocess.run(["git", "add", "-A"], cwd=str(temp_repo), capture_output=True, check=False)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(temp_repo), capture_output=True, check=False)
    return temp_repo


# ---------------------------------------------------------------------------
# Test 1: Corrupt hunk rejection
# ---------------------------------------------------------------------------

class TestCorruptHunkRejection:
    """Test that malformed hunk headers are rejected by preflight."""

    def test_corrupt_hunk_rejection(self, temp_repo_with_git):
        """A diff with a malformed @@ hunk header should be rejected."""
        corrupt_diff = (
            "diff --git a/sample_module.py b/sample_module.py\n"
            "--- a/sample_module.py\n"
            "+++ b/sample_module.py\n"
            "@@ -X,1 +1,1 @@\n"  # Malformed: X is not a number
            " def greet(name: str) -> str:\n"
            '-    return f"Hello, {name}!"\n'
            '+    return f"Hi, {name}!"\n'
        )
        result = preflight_patch(corrupt_diff, repo_root=temp_repo_with_git)
        assert not result.ok, "Corrupt hunk header should be rejected"
        assert any("Malformed hunk header" in r or "hunk" in r.lower() for r in result.rejections), \
            f"Rejections should mention malformed hunk header, got: {result.rejections}"

    def test_diff_with_file_headers_but_no_hunk_headers(self, temp_repo_with_git):
        """A diff with file headers but no @@ hunk headers should be rejected."""
        malformed_diff = (
            "diff --git a/sample_module.py b/sample_module.py\n"
            "--- a/sample_module.py\n"
            "+++ b/sample_module.py\n"
            " def greet(name: str) -> str:\n"
            '-    return f"Hello, {name}!"\n'
            '+    return f"Hi, {name}!"\n'
        )
        result = preflight_patch(malformed_diff, repo_root=temp_repo_with_git)
        assert not result.ok, "Diff without hunk headers should be rejected"
        assert any("hunk" in r.lower() for r in result.rejections), \
            f"Rejections should mention missing hunk headers, got: {result.rejections}"


# ---------------------------------------------------------------------------
# Test 2: Valid unified diff acceptance
# ---------------------------------------------------------------------------

class TestValidUnifiedDiffAcceptance:
    """Test that a well-formed unified diff passes preflight."""

    def test_valid_unified_diff_acceptance(self, temp_repo_with_git):
        """A well-formed unified diff should pass preflight."""
        valid_diff = (
            "diff --git a/sample_module.py b/sample_module.py\n"
            "--- a/sample_module.py\n"
            "+++ b/sample_module.py\n"
            "@@ -5,7 +5,7 @@ from typing import Any\n"
            " \n"
            " def greet(name: str) -> str:\n"
            '     """Greet someone."""\n'
            '-    return f"Hello, {name}!"\n'
            '+    return f"Hi, {name}!"\n'
            " \n"
            " def add(a: int, b: int) -> int:\n"
            '     """Add two numbers."""\n'
        )
        result = preflight_patch(valid_diff, repo_root=temp_repo_with_git)
        assert result.ok, f"Valid unified diff should pass preflight, rejections: {result.rejections}"


# ---------------------------------------------------------------------------
# Test 3: Prose-only rejection
# ---------------------------------------------------------------------------

class TestProseOnlyRejection:
    """Test that prose-only output (no diff markers) is rejected."""

    def test_prose_only_rejection(self, temp_repo_with_git):
        """Natural language prose with no diff markers should be rejected."""
        prose_output = (
            "I think the greet function should be updated to say Hi instead of Hello. "
            "The change is straightforward and involves modifying the return statement "
            "to use a different greeting word. This should improve the user experience."
        )
        result = preflight_patch(prose_output, repo_root=temp_repo_with_git)
        assert not result.ok, "Prose-only output should be rejected"
        assert "prose_only_output" in result.rejections, \
            f"Rejections should include prose_only_output, got: {result.rejections}"

    def test_empty_diff_rejection(self, temp_repo_with_git):
        """Empty diff should be rejected."""
        result = preflight_patch("", repo_root=temp_repo_with_git)
        assert not result.ok, "Empty diff should be rejected"
        assert "empty_diff" in result.rejections, \
            f"Rejections should include empty_diff, got: {result.rejections}"


# ---------------------------------------------------------------------------
# Test 4: Before/after local diff generation
# ---------------------------------------------------------------------------

class TestBeforeAfterLocalDiffGeneration:
    """Test that before/after replacement objects generate valid unified diffs locally."""

    def test_before_after_local_diff_generation(self, temp_repo):
        """A before/after replacement should generate a valid unified diff with correct hunk headers."""
        replacement = BeforeAfterReplacement(
            target_file="sample_module.py",
            before_text='    return f"Hello, {name}!"',
            after_text='    return f"Hi, {name}!"',
        )
        diff = generate_unified_diff_from_before_after(replacement, repo_root=temp_repo)

        assert diff.strip(), "Generated diff should not be empty"
        assert "@@" in diff, "Generated diff should contain hunk headers"
        assert "--- a/sample_module.py" in diff, "Generated diff should have from-file header"
        assert "+++ b/sample_module.py" in diff, "Generated diff should have to-file header"
        assert '-    return f"Hello, {name}!"' in diff, "Generated diff should contain the removed line"
        assert '+    return f"Hi, {name}!"' in diff, "Generated diff should contain the added line"

        # Verify the generated diff passes preflight (hunk headers are valid)
        result = preflight_patch(diff, repo_root=temp_repo, run_git_check=False)
        assert result.ok, f"Locally generated diff should pass preflight, rejections: {result.rejections}"

    def test_parse_before_after_response(self):
        """Test parsing a model response as a before/after JSON object."""
        response = '{"before_text": "old code", "after_text": "new code", "target_file": "test.py"}'
        replacement = parse_before_after_response(response)
        assert replacement is not None, "Should parse valid before/after JSON"
        assert replacement.before_text == "old code"
        assert replacement.after_text == "new code"
        assert replacement.target_file == "test.py"

    def test_parse_before_after_response_with_code_fence(self):
        """Test parsing a before/after response wrapped in a code fence."""
        response = '```json\n{"before_text": "old", "after_text": "new", "target_file": "test.py"}\n```'
        replacement = parse_before_after_response(response)
        assert replacement is not None, "Should parse before/after JSON from code fence"
        assert replacement.before_text == "old"
        assert replacement.after_text == "new"

    def test_parse_before_after_response_returns_none_for_non_json(self):
        """Test that non-JSON responses return None."""
        response = "This is just prose, not a before/after object."
        replacement = parse_before_after_response(response)
        assert replacement is None, "Non-JSON response should return None"


# ---------------------------------------------------------------------------
# Test 5: One-shot patch repair
# ---------------------------------------------------------------------------

class TestOneShotPatchRepair:
    """Test that a corrupt patch can be repaired in one shot."""

    def test_one_shot_patch_repair(self, temp_repo_with_git):
        """A corrupt diff + mock model caller should produce a valid repaired diff."""
        corrupt_diff = (
            "diff --git a/sample_module.py b/sample_module.py\n"
            "--- a/sample_module.py\n"
            "+++ b/sample_module.py\n"
            "@@ -BAD @@\n"
            " something wrong\n"
        )
        # Mock model caller that returns a valid diff
        valid_diff = (
            "diff --git a/sample_module.py b/sample_module.py\n"
            "--- a/sample_module.py\n"
            "+++ b/sample_module.py\n"
            "@@ -5,7 +5,7 @@ from typing import Any\n"
            " \n"
            " def greet(name: str) -> str:\n"
            '     """Greet someone."""\n'
            '-    return f"Hello, {name}!"\n'
            '+    return f"Hi, {name}!"\n'
            " \n"
            " def add(a: int, b: int) -> int:\n"
            '     """Add two numbers."""\n'
        )

        def mock_caller(provider: str, prompt: str, payload: dict[str, Any]) -> str:
            return valid_diff

        context_packet = BuilderContextPacket(
            target_file="sample_module.py",
            target_symbol="greet",
            source_excerpt='    return f"Hello, {name}!"',
        )

        result = asyncio.run(repair_patch_format(
            corrupt_diff,
            "error: corrupt patch",
            context_packet,
            mock_caller,
            role="worker",
            repo_root=str(temp_repo_with_git),
            rejections=["Malformed hunk header"],
        ))

        assert result.ok, f"Repair should succeed, rejections: {result.rejections_after_repair}"
        assert result.repaired_diff, "Repaired diff should not be empty"
        assert result.attempt_number == 1, "Should be exactly one attempt"
        assert "@@" in result.repaired_diff, "Repaired diff should have valid hunk headers"

    def test_repair_with_no_model_caller(self, temp_repo_with_git):
        """Repair with no model caller should return ok=False."""
        result = asyncio.run(repair_patch_format(
            "corrupt diff",
            "error",
            None,
            None,
            role="worker",
            repo_root=str(temp_repo_with_git),
        ))
        assert not result.ok, "Repair without model caller should fail"
        assert "no_model_caller" in result.rejections_after_repair


# ---------------------------------------------------------------------------
# Test 6: Failed repair blocks hot-swap
# ---------------------------------------------------------------------------

class TestFailedRepairBlocksHotswap:
    """Test that a failed repair blocks hot-swap (does not hot-swap)."""

    def test_failed_repair_blocks_hotswap(self, temp_repo_with_git):
        """When repair fails, the result should indicate failure (caller must block)."""
        corrupt_diff = (
            "diff --git a/sample_module.py b/sample_module.py\n"
            "--- a/sample_module.py\n"
            "+++ b/sample_module.py\n"
            "@@ -BAD @@\n"
            " something wrong\n"
        )

        # Mock model caller that returns another corrupt diff
        def mock_caller(provider: str, prompt: str, payload: dict[str, Any]) -> str:
            return "This is still prose, not a valid diff."

        context_packet = BuilderContextPacket(
            target_file="sample_module.py",
            target_symbol="greet",
        )

        result = asyncio.run(repair_patch_format(
            corrupt_diff,
            "error: corrupt patch",
            context_packet,
            mock_caller,
            role="worker",
            repo_root=str(temp_repo_with_git),
            rejections=["Malformed hunk header"],
        ))

        assert not result.ok, "Failed repair should return ok=False"
        assert not result.repaired_diff, "Failed repair should not produce a repaired diff"
        assert result.rejections_after_repair, "Failed repair should have rejections"
        # The caller should check result.ok and block hot-swap — we verify the contract here

    def test_failed_repair_with_empty_response(self, temp_repo_with_git):
        """Repair with an empty model response should fail."""
        def mock_caller(provider: str, prompt: str, payload: dict[str, Any]) -> str:
            return ""

        result = asyncio.run(repair_patch_format(
            "corrupt",
            "error",
            None,
            mock_caller,
            role="worker",
            repo_root=str(temp_repo_with_git),
        ))
        assert not result.ok, "Empty repair response should fail"
        assert "empty_repair_response" in result.rejections_after_repair


# ---------------------------------------------------------------------------
# Test 7: Missing-test warning triggers temp regression test generation
# ---------------------------------------------------------------------------

class TestMissingTestTriggersTempRegression:
    """Test that Shadow missing_test findings trigger temp regression test generation."""

    def test_missing_test_triggers_temp_regression_generation(self, temp_repo):
        """A missing_test Shadow finding should trigger test generation in temp workspace only."""
        shadow_findings = [
            {
                "shadow_type": "missing_test",
                "severity": "warn",
                "message": "No nearby test file was found for the target file.",
                "task_id": "A-LIVE-1",
                "target_file": "sample_module.py",
                "target_symbol": "greet",
            }
        ]

        context_packet = BuilderContextPacket(
            target_file="sample_module.py",
            target_symbol="greet",
            source_excerpt='def greet(name: str) -> str:\n    return f"Hello, {name}!"',
        )

        temp_workspace = Path(tempfile.mkdtemp(prefix="aura_test_workspace_"))
        try:
            result = asyncio.run(fill_test_gap(
                shadow_findings,
                context_packet,
                temp_workspace,
                model_caller=None,  # Use fallback test generation
                role="worker",
            ))

            assert result.ok, f"Test gap filler should succeed, error: {result.error}"
            assert result.generated_in_temp_only, "Test should be generated in temp only"
            assert result.test_file_path, "Test file path should be set"
            assert result.target_symbol == "greet", "Target symbol should be greet"

            # Verify the test file was actually written to the temp workspace
            test_path = Path(result.test_file_path)
            assert test_path.exists(), "Test file should exist in temp workspace"
            test_content = test_path.read_text(encoding="utf-8")
            assert "def test_" in test_content, "Generated test should contain test functions"
            assert "greet" in test_content, "Generated test should reference the target symbol"

            # Verify the test file is NOT in the production repo
            assert not (temp_repo / "test_sample_module_gap_filler.py").exists(), \
                "Test file should NOT be written to production repo"
        finally:
            shutil.rmtree(temp_workspace, ignore_errors=True)

    def test_no_missing_test_findings_returns_not_ok(self, temp_repo):
        """When there are no missing_test findings, fill_test_gap should return ok=False."""
        shadow_findings = [
            {
                "shadow_type": "fake_file",
                "severity": "blocker",
                "message": "Target file is absent.",
                "task_id": "A-LIVE-1",
            }
        ]

        context_packet = BuilderContextPacket(
            target_file="sample_module.py",
            target_symbol="greet",
        )

        temp_workspace = Path(tempfile.mkdtemp(prefix="aura_test_workspace_"))
        try:
            result = asyncio.run(fill_test_gap(
                shadow_findings,
                context_packet,
                temp_workspace,
                model_caller=None,
                role="worker",
            ))
            assert not result.ok, "Should return ok=False when no missing_test findings"
            assert result.error == "no_missing_test_findings"
        finally:
            shutil.rmtree(temp_workspace, ignore_errors=True)

    def test_detect_missing_test_findings(self):
        """Test that detect_missing_test_findings filters correctly."""
        findings = [
            {"shadow_type": "missing_test", "severity": "warn", "task_id": "A1"},
            {"shadow_type": "fake_file", "severity": "blocker", "task_id": "A2"},
            {"shadow_type": "missing_test", "severity": "warn", "task_id": "A3"},
        ]
        missing = detect_missing_test_findings(findings)
        assert len(missing) == 2, "Should find 2 missing_test findings"
        assert all(f["shadow_type"] == "missing_test" for f in missing)


# ---------------------------------------------------------------------------
# Additional: BuilderContextPacket tests
# ---------------------------------------------------------------------------

class TestBuilderContextPacket:
    """Test the BuilderContextPacket construction and rendering."""

    def test_build_context_packet_with_grounding(self, temp_repo):
        """Test building a context packet with grounding evidence."""
        grounding = {
            "task_id": "A-LIVE-1",
            "target_file": "sample_module.py",
            "target_symbol": "greet",
            "file_exists": True,
            "codemap_file_hit": True,
            "symbol_exists": True,
            "codemap_symbol_hits": [
                {"name": "greet", "kind": "function", "line": 6, "end_line": 8, "semantic_id": "test", "signature_hash": "abc"},
            ],
            "test_files": [],
            "neighbor_files": [],
        }

        packet = build_builder_context_packet(
            target_file="sample_module.py",
            target_symbol="greet",
            grounding_evidence=grounding,
            codemap=None,
            repo_root=temp_repo,
            objective="Update greet function",
            task_id="A-LIVE-1",
        )

        assert packet.target_file == "sample_module.py"
        assert packet.target_symbol == "greet"
        assert packet.symbol_start_line == 6
        assert packet.symbol_end_line == 8
        assert packet.source_excerpt, "Source excerpt should not be empty"
        assert "greet" in packet.source_excerpt, "Source excerpt should contain the target symbol"
        assert packet.nearby_imports, "Should extract nearby imports"
        assert packet.objective == "Update greet function"
        assert packet.task_id == "A-LIVE-1"

    def test_build_context_packet_without_grounding(self, temp_repo):
        """Test building a context packet without grounding evidence (graceful degradation)."""
        packet = build_builder_context_packet(
            target_file="sample_module.py",
            target_symbol=None,
            grounding_evidence=None,
            codemap=None,
            repo_root=temp_repo,
        )

        assert packet.target_file == "sample_module.py"
        assert packet.target_symbol is None
        assert packet.symbol_start_line == 0
        assert packet.source_excerpt == "", "Source excerpt should be empty without line range"
        assert packet.nearby_imports, "Should still extract imports from the file"

    def test_render_context_packet_prompt(self, temp_repo):
        """Test that the prompt rendering includes all key sections."""
        packet = BuilderContextPacket(
            target_file="sample_module.py",
            target_symbol="greet",
            symbol_start_line=3,
            symbol_end_line=5,
            source_excerpt="def greet(name): return f'Hello, {name}!'",
            nearby_imports=["import os"],
            callers=["other_module.py::caller"],
            neighbors=["other_module.py"],
            nearby_tests=["test_sample_module.py"],
            acceptance_criteria=["Patch applies cleanly"],
            forbidden_actions=["Do not write to production"],
        )

        prompt = render_context_packet_prompt(packet)
        assert "BUILDER CONTEXT PACKET" in prompt
        assert "sample_module.py" in prompt
        assert "greet" in prompt
        assert "source_excerpt" in prompt
        assert "nearby_imports" in prompt
        assert "callers" in prompt
        assert "neighbor_files" in prompt
        assert "nearby_tests" in prompt
        assert "acceptance_criteria" in prompt
        assert "forbidden_actions" in prompt
        assert "OUTPUT FORMAT" in prompt


# ---------------------------------------------------------------------------
# Integration: Full preflight + repair flow
# ---------------------------------------------------------------------------

class TestPreflightRepairFlow:
    """Integration tests for the preflight → repair flow."""

    def test_valid_diff_does_not_trigger_repair(self, temp_repo_with_git):
        """A valid diff should pass preflight and not need repair."""
        valid_diff = (
            "diff --git a/sample_module.py b/sample_module.py\n"
            "--- a/sample_module.py\n"
            "+++ b/sample_module.py\n"
            "@@ -5,7 +5,7 @@ from typing import Any\n"
            " \n"
            " def greet(name: str) -> str:\n"
            '     """Greet someone."""\n'
            '-    return f"Hello, {name}!"\n'
            '+    return f"Hi, {name}!"\n'
            " \n"
            " def add(a: int, b: int) -> int:\n"
            '     """Add two numbers."""\n'
        )
        result = preflight_patch(valid_diff, repo_root=temp_repo_with_git)
        assert result.ok, "Valid diff should pass preflight without repair"

    def test_before_after_then_preflight(self, temp_repo):
        """A before/after replacement should generate a diff that passes preflight."""
        replacement = BeforeAfterReplacement(
            target_file="sample_module.py",
            before_text='    return f"Hello, {name}!"',
            after_text='    return f"Greetings, {name}!"',
        )
        diff = generate_unified_diff_from_before_after(replacement, repo_root=temp_repo)
        result = preflight_patch(diff, repo_root=temp_repo, run_git_check=False)
        assert result.ok, f"Before/after generated diff should pass preflight, rejections: {result.rejections}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
