from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from scripts import aura_architecture_harness as harness


def _git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def _init_repo(tmp_path: Path, files: dict[str, bytes | str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Harness Test")
    _git(root, "config", "user.email", "harness-test@local.invalid")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            target.write_bytes(body)
        else:
            target.write_text(body, encoding="utf-8", newline="\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "fixture")
    return root


def _manifest(output: Path) -> dict:
    return json.loads((output / "ai_handoff_manifest.json").read_text(encoding="utf-8"))


def test_digest_is_order_stable() -> None:
    assert harness._digest({"b": 2, "a": 1}) == harness._digest({"a": 1, "b": 2})


def test_default_venv_is_outside_repository() -> None:
    root = Path("/tmp/AuraOS")
    result = harness._default_venv(root)
    assert result.parent == root.parent
    assert result != root / ".venv"


def test_parser_defaults_to_bounded_minimal_atlas() -> None:
    args = harness._parser().parse_args(["--repo-root", ".", "run"])
    assert args.atlas_profile == "MINIMAL"
    assert args.allow_expansive_atlas is False
    assert args.allow_dirty is False
    assert args.pair_limit == 5_000_000
    assert args.resume is False
    assert args.reference_file == []
    assert args.watchdog_checkin_seconds == 10 * 60
    assert args.watchdog_pause_seconds == 20 * 60


def test_handoff_parser_defaults_are_bounded() -> None:
    args = harness._parser().parse_args(["--repo-root", ".", "handoff"])
    assert args.inline_max_bytes == 256 * 1024
    assert args.allow_dirty is False
    assert args.no_archive is False


def test_reference_manifest_binds_external_specification(tmp_path: Path) -> None:
    reference = tmp_path / "architecture.txt"
    reference.write_text("bounded architecture specification\n", encoding="utf-8")

    manifest = harness._reference_manifest([reference])

    assert manifest == [
        {
            "name": "architecture.txt",
            "path": str(reference.resolve()),
            "size_bytes": reference.stat().st_size,
            "sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        }
    ]


def test_reference_manifest_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="reference file is missing"):
        harness._reference_manifest([tmp_path / "missing.txt"])


def test_streaming_sha256_matches_hashlib(tmp_path: Path) -> None:
    target = tmp_path / "fixture.bin"
    body = b"0123456789" * 1000
    target.write_bytes(body)
    assert harness._stream_sha256(target, chunk_bytes=37) == hashlib.sha256(body).hexdigest()


def test_required_surfaces_cover_requested_architecture() -> None:
    required = set(harness.REQUIRED_REPOSITORY_FILES)
    assert "aura_capability_connectome.py" in required
    assert "aura_relational_synthesis.py" in required
    assert "aura_relationship_atlas.py" in required
    assert "aura_emergent_potential_repl.py" in required
    assert "aura_architect_loop.py" in required


def test_harness_is_proposal_only() -> None:
    assert harness.PATCH_AUTHORITY == "exact_source_spans_and_hashes_only"
    assert harness.AUTHORITY_CONTRACT == {
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "provider_execution_authorized": False,
        "human_review_required": True,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }


def test_task_watchdog_policy_checks_then_pauses() -> None:
    policy = harness._task_watchdog_policy()
    assert policy["version"] == harness.TASK_WATCHDOG_VERSION
    assert policy["enabled"] is True
    assert policy["checkin_seconds"] == 10 * 60
    assert policy["pause_seconds"] == 20 * 60
    assert policy["resume_required"] is True
    assert policy["production_mutation"] is False
    assert policy["human_review_required"] is True

    healthy = harness._assess_watchdog_progress(
        elapsed_seconds=600,
        progress_age_seconds=120,
        checkin_seconds=600,
        progress_changed=True,
        status_present=True,
        last_phase="relationship_atlas",
        last_state="running",
        completed_artifacts=[{"path": "connectome.json", "size_bytes": 1}],
    )
    assert healthy["assessment"] == "HEALTHY_CONTINUE"
    assert healthy["progress_healthy"] is True
    assert healthy["needs_reassessment_now"] is False

    slow = harness._assess_watchdog_progress(
        elapsed_seconds=600,
        progress_age_seconds=600,
        checkin_seconds=600,
        progress_changed=False,
        status_present=True,
        last_phase="relationship_atlas",
        last_state="running",
        completed_artifacts=[],
    )
    assert slow["assessment"] == "SLOW_BUT_PROGRESSING"

    stalled = harness._assess_watchdog_progress(
        elapsed_seconds=1200,
        progress_age_seconds=1200,
        checkin_seconds=600,
        progress_changed=False,
        status_present=True,
        last_phase="relationship_atlas",
        last_state="running",
        completed_artifacts=[],
    )
    assert stalled["assessment"] == "STALLED_REASSESS"
    assert stalled["progress_healthy"] is False
    assert stalled["needs_reassessment_now"] is True

def test_task_watchdog_emits_checkins_and_hard_pause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "watchdog-run"
    monkeypatch.setattr(harness, "WATCHDOG_POLL_SECONDS", 0.01)
    script = tmp_path / "long_task.py"
    script.write_text(
        """
import json
import sys
import time
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
for index in range(100):
    (out / "watchdog_status.json").write_text(
        json.dumps({"progress_sequence": index + 1, "phase": f"phase-{index}", "state": "running"}),
        encoding="utf-8",
    )
    time.sleep(0.04)
""".lstrip(),
        encoding="utf-8",
    )
    result = harness._run_with_watchdog(
        [sys.executable, str(script), str(output)],
        tmp_path,
        output_dir=output,
        checkin_seconds=0.20,
        pause_seconds=1.20,
        resume_command="python harness.py run --output-dir checkpoint --resume",
    )

    assert result.paused is True
    assert len(result.checkins) >= 3
    assert any(row["progress_healthy"] for row in result.checkins)
    assert result.pause_receipt is not None
    assert result.pause_receipt["resume_required"] is True
    assert result.pause_receipt["recommended_next_action"] == "review_then_resume_same_plan"
    assert result.pause_receipt["resume_command"].endswith("--resume")
    assert "terminated_returncode" in result.pause_receipt
    assert "stdout_truncation" in result.pause_receipt
    assert "stderr_truncation" in result.pause_receipt
    assert (output / harness.WATCHDOG_PAUSE_FILE).is_file()
    events = [
        json.loads(line)
        for line in (output / harness.WATCHDOG_EVENTS_FILE).read_text(encoding="utf-8").splitlines()
    ]
    assert sum(row["event"] == "watchdog_checkin" for row in events) >= 3
    assert events[-1]["event"] == "watchdog_hard_pause"


def test_watchdog_event_log_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.jsonl"
    outside.write_text("", encoding="utf-8")
    output = tmp_path / "watchdog-symlink"
    output.mkdir()
    link = output / harness.WATCHDOG_EVENTS_FILE
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(RuntimeError, match="watchdog event symlink"):
        harness._append_json_line(link, {"event": "test"})
    assert outside.read_text(encoding="utf-8") == ""


def test_task_watchdog_marks_missing_progress_as_possible_stall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "watchdog-stalled"
    monkeypatch.setattr(harness, "WATCHDOG_POLL_SECONDS", 0.01)
    result = harness._run_with_watchdog(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        tmp_path,
        output_dir=output,
        checkin_seconds=0.05,
        pause_seconds=0.16,
    )
    assert result.paused is True
    assert any(
        row["assessment"] in {"STALLED_REASSESS", "UNKNOWN_REASSESS"}
        for row in result.checkins
    )
    assert result.pause_receipt is not None
    assert (
        result.pause_receipt["recommended_next_action"]
        == "reassess_scope_or_strategy_before_resume"
    )


@pytest.mark.parametrize(
    "path",
    [
        ".aura/CODEMAP.json",
        ".aura/CODEMAP.md",
        "topology_map.json",
        "Aura_Memory/live_topology_ast.json",
        "docs/aura_substrate_manifest.v1.json",
        "docs/aura_substrate_manifest.files.01.json",
        "docs/aura_substrate_manifest.phases.09.json",
        "docs/aura_substrate_release_index.v1.json",
    ],
)
def test_known_generated_paths_are_regenerate_even_when_small(path: str) -> None:
    disposition, reason = harness._classify_tracked_file(
        path,
        size_bytes=2,
        binary=False,
        symlink=False,
        inline_max_bytes=256,
    )
    assert disposition == harness.REGENERATE_FROM_FINAL_TREE
    assert reason == "generated_reproducible_artifact"


def test_unknown_text_above_threshold_is_digest_only() -> None:
    assert harness._classify_tracked_file(
        "oversized.txt",
        size_bytes=257,
        binary=False,
        symlink=False,
        inline_max_bytes=256,
    ) == (harness.DIGEST_ONLY, "exceeds_inline_max_bytes")


def test_binary_probe_reads_only_bounded_prefix(tmp_path: Path) -> None:
    target = tmp_path / "binary.dat"
    target.write_bytes(b"abc\x00" + b"z" * 1000)
    binary, inspected = harness._binary_probe(target, max_bytes=16)
    assert binary is True
    assert inspected == 16


def test_generated_body_never_appears_in_manifest_or_archive(tmp_path: Path) -> None:
    marker = "GENERATED_BODY_MUST_NOT_APPEAR"
    root = _init_repo(
        tmp_path,
        {
            ".aura/CODEMAP.json": marker,
            "source.py": "print('source')\n",
        },
    )
    output = tmp_path / "handoff"
    harness.create_ai_handoff(root, output_dir=output, inline_max_bytes=256)
    manifest_text = (output / "ai_handoff_manifest.json").read_text(encoding="utf-8")
    assert marker not in manifest_text
    manifest = json.loads(manifest_text)
    generated = next(row for row in manifest["digest_only_files"] if row["path"] == ".aura/CODEMAP.json")
    assert generated["disposition"] == harness.REGENERATE_FROM_FINAL_TREE
    assert generated["git_blob_sha256"] == hashlib.sha256(marker.encode()).hexdigest()
    with zipfile.ZipFile(output / "ai_source_review.zip") as archive:
        assert ".aura/CODEMAP.json" not in archive.namelist()
        assert "source.py" in archive.namelist()


def test_binary_and_oversized_files_are_digest_only(tmp_path: Path) -> None:
    root = _init_repo(
        tmp_path,
        {
            "binary.dat": b"abc\x00def",
            "large.txt": "x" * 257,
            "small.txt": "review me\n",
        },
    )
    output = tmp_path / "handoff"
    harness.create_ai_handoff(root, output_dir=output, inline_max_bytes=256)
    rows = {row["path"]: row for row in _manifest(output)["digest_only_files"]}
    assert rows["binary.dat"]["reason"] == "binary_content"
    assert rows["large.txt"]["reason"] == "exceeds_inline_max_bytes"
    assert (output / "ai_review_files.txt").read_text().splitlines() == ["small.txt"]


def test_file_list_manifest_and_archive_are_deterministic(tmp_path: Path) -> None:
    root = _init_repo(tmp_path, {"b.txt": "b\n", "a.txt": "a\n"})
    first = tmp_path / "first"
    second = tmp_path / "second"
    harness.create_ai_handoff(root, output_dir=first)
    harness.create_ai_handoff(root, output_dir=second)
    for name in ("ai_handoff_manifest.json", "ai_review_files.txt", "ai_source_review.zip"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    assert (first / "ai_review_files.txt").read_text().splitlines() == ["a.txt", "b.txt"]


def test_dirty_repository_fails_closed_and_can_be_marked(tmp_path: Path) -> None:
    root = _init_repo(tmp_path, {"source.txt": "committed\n"})
    (root / "source.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="repository is dirty"):
        harness.create_ai_handoff(root, output_dir=tmp_path / "rejected")
    output = tmp_path / "allowed"
    harness.create_ai_handoff(root, output_dir=output, allow_dirty=True)
    manifest = _manifest(output)
    assert manifest["source"]["clean"] is False
    assert manifest["warnings"]
    with zipfile.ZipFile(output / "ai_source_review.zip") as archive:
        assert archive.read("source.txt") == b"committed\n"


def test_synthetic_repository_requires_exact_source_sha(tmp_path: Path) -> None:
    root = _init_repo(tmp_path, {"source.txt": "committed\n"})
    _git(root, "config", "aura.harnessSyntheticIdentity", "true")
    _git(root, "config", "aura.harnessSourceSha", "UNSPECIFIED")
    with pytest.raises(RuntimeError, match="canonical source commit"):
        harness.create_ai_handoff(root, output_dir=tmp_path / "handoff")


def test_dirty_status_is_compact_and_does_not_leak_path(tmp_path: Path) -> None:
    root = _init_repo(tmp_path, {"source.txt": "committed\n"})
    secret_name = "private-customer-name.env"
    (root / secret_name).write_text("TOKEN=value\n", encoding="utf-8")
    output = tmp_path / "handoff"
    harness.create_ai_handoff(root, output_dir=output, allow_dirty=True)
    text = (output / "ai_handoff_manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(text)
    assert secret_name not in text
    assert manifest["source"]["dirty_entry_count"] == 1
    assert manifest["source"]["status_digest"]


def test_crlf_worktree_cannot_masquerade_as_git_blob(tmp_path: Path) -> None:
    root = _init_repo(tmp_path, {"source.txt": "line one\nline two\n"})
    (root / "source.txt").write_bytes(b"line one\r\nline two\r\n")
    output = tmp_path / "handoff"
    harness.create_ai_handoff(root, output_dir=output, allow_dirty=True)
    variance = _manifest(output)["working_tree_variances"]
    assert [row["path"] for row in variance] == ["source.txt"]
    row = variance[0]
    assert row["git_blob_sha256"] == hashlib.sha256(b"line one\nline two\n").hexdigest()
    assert row["working_tree_sha256"] == hashlib.sha256(b"line one\r\nline two\r\n").hexdigest()
    assert row["git_blob_oid"] != row["working_tree_sha256"]


def test_symlink_escape_is_digest_only_and_not_archived(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("outside secret\n", encoding="utf-8")
    root = _init_repo(tmp_path, {"inside.txt": "inside\n"})
    link = root / "escape-link"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    _git(root, "add", "escape-link")
    _git(root, "commit", "-q", "-m", "symlink")
    output = tmp_path / "handoff"
    harness.create_ai_handoff(root, output_dir=output)
    row = next(row for row in _manifest(output)["digest_only_files"] if row["path"] == "escape-link")
    assert row["reason"] == "symlink_not_archived"
    with zipfile.ZipFile(output / "ai_source_review.zip") as archive:
        assert "escape-link" not in archive.namelist()


@pytest.mark.parametrize("value", ["../escape", "/absolute", "C:/escape", "a\\b", "a/../b"])
def test_path_traversal_and_windows_paths_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        harness._validate_repo_path(value)


def test_output_directory_inside_repository_is_rejected(tmp_path: Path) -> None:
    root = _init_repo(tmp_path, {"source.txt": "ok\n"})
    with pytest.raises(ValueError, match="outside the repository"):
        harness.create_ai_handoff(root, output_dir=root / "handoff")


def test_worktree_change_during_handoff_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _init_repo(tmp_path, {"source.txt": "stable\n"})
    original = harness._read_git_blob
    changed = False

    def mutate_after_read(*args, **kwargs):
        nonlocal changed
        payload = original(*args, **kwargs)
        if not changed:
            changed = True
            (root / "source.txt").write_text("changed during run\n", encoding="utf-8")
        return payload

    monkeypatch.setattr(harness, "_read_git_blob", mutate_after_read)
    with pytest.raises(RuntimeError, match="status changed"):
        harness.create_ai_handoff(root, output_dir=tmp_path / "handoff")


def test_bounded_subprocess_output_reports_omissions(tmp_path: Path) -> None:
    code = (
        "import sys;"
        "sys.stdout.write('stdout-line\\n'*10000);"
        "sys.stderr.write('stderr-line\\n'*10000)"
    )
    result = harness._run(
        [sys.executable, "-c", code],
        tmp_path,
        max_output_bytes=1024,
        max_output_lines=20,
    )
    assert result.returncode == 0
    assert result.stdout_truncation["truncated"] is True
    assert result.stderr_truncation["truncated"] is True
    assert result.stdout_truncation["omitted_bytes"] > 0
    assert result.stderr_truncation["omitted_lines"] > 0
    assert len(result.stdout.encode()) <= 1024
    assert len(result.stderr.encode()) <= 1024


def test_doctor_metadata_is_streamed_without_deserializing_body(tmp_path: Path) -> None:
    target = tmp_path / "codemap.json"
    target.write_text(
        '{"file_count": 12, "body": "' + ("x" * 5000) + '", "symbol_count": 34}',
        encoding="utf-8",
    )
    result = harness._stream_json_integer_metadata(target, ("file_count", "symbol_count"))
    assert result["file_count"] == 12
    assert result["symbol_count"] == 34
    assert result["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()


def test_init_git_force_adds_ignored_archive_files(tmp_path: Path) -> None:
    root = tmp_path / "export"
    (root / ".aura").mkdir(parents=True)
    (root / ".gitignore").write_text(".aura/CODEMAP.json\n", encoding="utf-8")
    (root / ".aura/CODEMAP.json").write_text("{}\n", encoding="utf-8")
    harness._init_git(root, "source-sha")
    assert ".aura/CODEMAP.json" in _git(root, "ls-files").splitlines()
    assert _git(root, "config", "--get", "aura.harnessSourceSha") == "source-sha"


def test_workflow_publishes_full_and_ai_first_artifacts() -> None:
    workflow = Path(".github/workflows/aura-architecture-harness-export.yml").read_text(
        encoding="utf-8"
    )
    assert "AuraOS-full-repository.zip" in workflow
    assert "AuraOS-ai-review-first-" in workflow
    assert "ai_handoff_manifest.json" in workflow
    assert "ai_review_files.txt" in workflow
    assert "ai_source_review.zip" in workflow
    assert "PYTHONDONTWRITEBYTECODE" in workflow


def test_run_architecture_accepts_serialized_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "run"

    class _ConnectomeModule:
        @staticmethod
        def build_capability_connectome(_root):
            return {"nodes": [], "edges": []}

    class _ConnectomeV2Module:
        @staticmethod
        def enrich_connectome(graph):
            return {**graph, "node_count": 0, "edge_count": 0, "graph_digest": "g"}

    class _IndexModule:
        @staticmethod
        def build_relational_index(*_args, **_kwargs):
            return {"participant_count": 0, "index": {"participants": [], "relationships": []}}

    class _Snapshot:
        snapshot_digest = "a"
        assessments = []
        missing_configurations = []
        prohibitions = []

        def to_dict(self):
            return {"snapshot_digest": "a", "assessments": [], "missing_configurations": [], "prohibitions": []}

    atlas_calls: list[dict] = []

    class _AtlasModule:
        @staticmethod
        def build_relationship_atlas(**kwargs):
            atlas_calls.append(kwargs)
            return _Snapshot()

    class _Report:
        verifier_summary = "ok"

        def to_dict(self):
            return {"summary": {}, "verifier_summary": "ok", "connections": []}

    class _EmergentModule:
        @staticmethod
        def audit_emergent_potential(*_args, **_kwargs):
            return _Report()

    class _Prepared:
        def to_dict(self):
            return {"plan": {}, "shadow_report": {}, "arena": {}}

    class _FusionLoop:
        def __init__(self, repo_root):
            self.repo_root = repo_root

        def prepare(self, *_args, **_kwargs):
            return _Prepared()

    class _ArchitectModule:
        ArchitectFusionLoop = _FusionLoop

    modules = {
        "aura_capability_connectome": _ConnectomeModule,
        "aura_capability_connectome_v2": _ConnectomeV2Module,
        "aura_relational_index": _IndexModule,
        "aura_relationship_atlas": _AtlasModule,
        "aura_emergent_potential_repl": _EmergentModule,
        "aura_architect_loop": _ArchitectModule,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(harness, "_git_info", lambda _root: {"available": True, "clean": True})

    result = harness.run_architecture(
        root,
        objective="test",
        combine_with=[],
        profile="MINIMAL",
        top=1,
        pair_limit=1,
        allow_expansive=False,
        output_dir=str(output),
        resume=False,
        enforce_clean=True,
        reference_files=[],
    )

    assert result["ok"] is True
    assert (output / "harness_summary.json").is_file()
    assert result["task_watchdog"]["checkin_seconds"] == 10 * 60
    assert result["task_watchdog"]["pause_seconds"] == 20 * 60
    watchdog_status = json.loads(
        (output / harness.WATCHDOG_STATUS_FILE).read_text(encoding="utf-8")
    )
    assert watchdog_status["phase"] == "complete"
    assert watchdog_status["state"] == "completed"
    assert result["ai_handoff"]["generated_artifact_disposition"] == harness.REGENERATE_FROM_FINAL_TREE
    assert atlas_calls[0]["persist"] is False
    assert atlas_calls[0]["relational_index_data"] == {
        "participants": [],
        "relationships": [],
    }


def test_watchdog_assesses_unknown_progress_without_status() -> None:
    unknown = harness._assess_watchdog_progress(
        elapsed_seconds=600,
        progress_age_seconds=600,
        checkin_seconds=600,
        progress_changed=False,
        status_present=False,
        last_phase="",
        last_state="",
        completed_artifacts=[],
    )
    assert unknown["assessment"] == "UNKNOWN_REASSESS"
    assert unknown["action"] == "inspect_child_and_output_state"
    assert unknown["needs_reassessment_now"] is True

def test_watchdog_rejects_invalid_thresholds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="check-in interval must be positive"):
        harness._run_with_watchdog(
            [sys.executable, "-c", "pass"],
            tmp_path,
            output_dir=tmp_path / "output-a",
            checkin_seconds=0,
            pause_seconds=1,
        )
    with pytest.raises(ValueError, match="pause threshold must be at least"):
        harness._run_with_watchdog(
            [sys.executable, "-c", "pass"],
            tmp_path,
            output_dir=tmp_path / "output-b",
            checkin_seconds=2,
            pause_seconds=1,
        )


def test_watchdog_checks_in_then_pauses_with_resume_receipt(tmp_path: Path) -> None:
    output = tmp_path / "watchdog-run"
    output.mkdir()
    harness._write_watchdog_progress(
        output,
        phase="long_phase",
        state="running",
        started_monotonic=0.0,
    )
    resume = "python harness.py run --output-dir watchdog-run --resume"
    result = harness._run_with_watchdog(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        tmp_path,
        output_dir=output,
        checkin_seconds=0.1,
        pause_seconds=0.6,
        resume_command=resume,
    )
    assert result.paused is True
    assert result.pause_receipt is not None
    assert result.pause_receipt["resume_required"] is True
    assert result.pause_receipt["resume_command"] == resume
    assert result.pause_receipt["last_phase"] == "long_phase"
    assert result.checkins
    assert (output / harness.WATCHDOG_PAUSE_FILE).is_file()
    events = [json.loads(line) for line in (output / harness.WATCHDOG_EVENTS_FILE).read_text().splitlines()]
    assert any(row["event"] == "watchdog_checkin" for row in events)
    assert events[-1]["event"] == "watchdog_hard_pause"


def test_run_resume_command_preserves_runtime_contract(tmp_path: Path) -> None:
    args = harness._parser().parse_args(
        [
            "--repo-root",
            ".",
            "run",
            "--objective",
            "bounded objective",
            "--combine-with",
            "Connectome",
            "Atlas",
            "--reference-file",
            "evidence.txt",
            "--watchdog-checkin-seconds",
            "600",
            "--watchdog-pause-seconds",
            "1200",
        ]
    )
    command = harness._run_resume_command(
        tmp_path / "repo",
        tmp_path / "venv",
        tmp_path / "run",
        args,
    )
    assert "bounded objective" in command
    assert "evidence.txt" in command
    assert "--watchdog-checkin-seconds 600.0" in command
    assert "--watchdog-pause-seconds 1200.0" in command
    assert command.endswith("--reference-file evidence.txt") or "--reference-file evidence.txt" in command
    assert "--resume" in command
