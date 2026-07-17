"""Apply final manual integrity hardening to the SCO Construction completion slice."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected one hardening anchor: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, sentinel: str, content: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if sentinel in text:
        return
    target.write_text(text.rstrip() + "\n\n" + content.rstrip() + "\n", encoding="utf-8")


def patch_profile() -> None:
    path = "aura_construction_human_agent.py"
    replace_once(
        path,
        "from dataclasses import asdict, dataclass\nfrom typing import Any, Iterable\n",
        "from dataclasses import asdict, dataclass\nimport re\nfrom typing import Any, Iterable\n",
    )
    replace_once(
        path,
        ")\n\n\ndef _text(value: Any, name: str, *, allow_empty: bool = False) -> str:\n",
        ")\n_CHECKPOINT_ID = re.compile(r\"^CHK-[0-9a-f]{40}$\")\n\n\ndef _text(value: Any, name: str, *, allow_empty: bool = False) -> str:\n",
    )
    replace_once(
        path,
        "def _strings(values: Iterable[Any], name: str) -> tuple[str, ...]:\n",
        "def _checkpoint_id(value: Any) -> str:\n"
        "    text = _text(value, \"checkpoint_id\", allow_empty=True)\n"
        "    if text and not _CHECKPOINT_ID.fullmatch(text):\n"
        "        raise ValueError(\"checkpoint_id must be CHK- followed by 40 lowercase hex characters\")\n"
        "    return text\n\n\n"
        "def _strings(values: Iterable[Any], name: str) -> tuple[str, ...]:\n",
    )
    replace_once(
        path,
        '''        for field_name in (
            "recommended_candidate_id",
            "next_authority_route",
            "checkpoint_id",
        ):
            if getattr(self, field_name) != _text(
                getattr(self, field_name), field_name, allow_empty=True
            ):
                raise ValueError(f"{field_name} must be canonical text")
        if type(self.evaluated_at) is not float:
''',
        '''        for field_name in (
            "recommended_candidate_id",
            "next_authority_route",
        ):
            if getattr(self, field_name) != _text(
                getattr(self, field_name), field_name, allow_empty=True
            ):
                raise ValueError(f"{field_name} must be canonical text")
        _checkpoint_id(self.checkpoint_id)
        if type(self.synthetic) is not bool:
            raise ValueError("synthetic must be boolean")
        if type(self.evaluated_at) is not float:
''',
    )
    replace_once(
        path,
        '            "inspect proposal evidence references",\n',
        '            "inspect the bounded proposal record",\n',
    )
    replace_once(
        path,
        '''            "physical_work_authorized": False,
            "payment_released": False,
            "patch_authority": PATCH_AUTHORITY,
''',
        '''            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "professional_certification_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
''',
    )
    replace_once(
        path,
        '''    if not candidate_items or not all(
        type(item) is ConstructionCoordinationCandidate for item in candidate_items
    ):
        raise ValueError("candidates must contain exact Construction candidates")
    candidate_by_id = {item.candidate_id: item for item in candidate_items}
''',
        '''    if not candidate_items or not all(
        type(item) is ConstructionCoordinationCandidate for item in candidate_items
    ):
        raise ValueError("candidates must contain exact Construction candidates")
    for item in candidate_items:
        item.__post_init__()
    candidate_by_id = {item.candidate_id: item for item in candidate_items}
''',
    )
    replace_once(
        path,
        '        "checkpoint_id": _text(checkpoint_id, "checkpoint_id", allow_empty=True),\n',
        '        "checkpoint_id": _checkpoint_id(checkpoint_id),\n',
    )
    replace_once(
        path,
        '''            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "patch_authority": PATCH_AUTHORITY,
''',
        '''            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "professional_certification_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
''',
    )
    replace_once(
        path,
        '''            "physical_work_authorized": False,
            "payment_released": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def prepare_handoff''',
        '''            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "professional_certification_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def prepare_handoff''',
    )


def patch_server() -> None:
    path = "aura_human_agent_arena_server.py"
    replace_once(
        path,
        "from pathlib import Path\nimport time\n",
        "from pathlib import Path\nimport subprocess\nimport time\n",
    )
    replace_once(
        path,
        "def _error(message: str, code: int = 400) -> tuple[int, dict[str, Any]]:\n",
        '''def _current_repo_head(repo_root: Path) -> str:
    """Return the exact local Git HEAD when repository metadata is available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    head = result.stdout.strip()
    if not 7 <= len(head) <= 64 or any(ch not in "0123456789abcdef" for ch in head):
        return ""
    return head


def _error(message: str, code: int = 400) -> tuple[int, dict[str, Any]]:
''',
    )
    replace_once(
        path,
        '''        if not repo_head:
            return _error("repo_head is required")
        try:
''',
        '''        if not repo_head:
            return _error("repo_head is required")
        current_repo_head = _current_repo_head(state.repo_root)
        if current_repo_head and repo_head != current_repo_head:
            return _error("repo_head does not match current repository HEAD", 409)
        try:
''',
    )


def patch_completion_status() -> None:
    path = "aura_construction_refactor_completion.py"
    replace_once(
        path,
        '''    payload = {
        "version": CONSTRUCTION_REFACTOR_COMPLETION_VERSION,
''',
        '''    node_status = {node.node_id: node.status for node in nodes}
    human_surface_failures = [
        item
        for item in marker_failures
        if any(
            owner in item
            for owner in (
                "aura_human_agent_arena_server.py",
                "aura_human_agent_arena/index.html",
                "aura_human_agent_arena/construction.js",
            )
        )
    ]
    observatory_failures = [
        item for item in human_surface_failures if "observatory" in item
    ]
    construction_human_agent_integrated = (
        node_status.get("E9") == "INTEGRATED" and not human_surface_failures
    )
    payload = {
        "version": CONSTRUCTION_REFACTOR_COMPLETION_VERSION,
''',
    )
    replace_once(
        path,
        '''        "construction_human_agent_integrated": any(
            node.node_id == "E9" and node.status == "INTEGRATED" for node in nodes
        ),
        "observatory_read_only": not any(
            item.startswith("missing_marker:aura_human_agent_arena")
            for item in marker_failures
        ),
''',
        '''        "construction_human_agent_integrated": construction_human_agent_integrated,
        "observatory_read_only": (
            construction_human_agent_integrated and not observatory_failures
        ),
''',
    )


def patch_tests() -> None:
    append_once(
        "tests/test_aura_construction_human_agent.py",
        "def test_profile_revalidates_source_candidate_identity_and_checkpoint_format",
        '''def test_profile_revalidates_source_candidate_identity_and_checkpoint_format():
    fixture, evaluation = _profile_inputs()
    tampered = fixture.candidates[0]
    object.__setattr__(tampered, "summary", "tampered after identity creation")

    with pytest.raises(ValueError, match="candidate digest"):
        build_construction_human_agent_profile(
            fixture.state,
            evaluation,
            candidates=fixture.candidates,
            synthetic=True,
        )

    fixture, evaluation = _profile_inputs()
    with pytest.raises(ValueError, match="checkpoint_id must be CHK-"):
        build_construction_human_agent_profile(
            fixture.state,
            evaluation,
            candidates=fixture.candidates,
            checkpoint_id="CHK-not-an-exact-checkpoint",
            synthetic=True,
        )
''',
    )
    append_once(
        "tests/test_aura_construction_human_agent_server.py",
        "def test_checkpoint_endpoint_rejects_head_that_disagrees_with_local_git",
        '''def test_checkpoint_endpoint_rejects_head_that_disagrees_with_local_git(tmp_path: Path):
    import subprocess

    state = HumanAgentArenaServerState(tmp_path, demo=True)
    try:
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "tests@example.invalid"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "AuraOS Tests"],
            cwd=tmp_path,
            check=True,
        )
        marker = tmp_path / "tracked.txt"
        marker.write_text("exact head\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "seed exact head"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        actual_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        status, mismatch = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/construction/checkpoint",
            {"repo_head": "b" * 40},
        )
        assert status == 409
        assert mismatch["error"] == "repo_head does not match current repository HEAD"

        status, stored = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/construction/checkpoint",
            {"repo_head": actual_head},
        )
        assert status == 200
        assert stored["checkpoint"]["repo_head"] == actual_head
    finally:
        state.close()
''',
    )
    append_once(
        "tests/test_aura_construction_refactor_completion.py",
        "def test_observatory_status_requires_e9_owner_not_only_surface_markers",
        '''def test_observatory_status_requires_e9_owner_not_only_surface_markers(tmp_path: Path, monkeypatch):
    (tmp_path / "owner.py").write_text("def other():\n    return True\n", encoding="utf-8")
    (tmp_path / "surface.txt").write_text("observatory", encoding="utf-8")
    monkeypatch.setattr(
        completion,
        "_REQUIRED_SYMBOLS",
        {"E9": {"owner.py": ("required_profile",)}},
    )
    monkeypatch.setattr(
        completion,
        "_REQUIRED_MARKERS",
        {"surface.txt": ("observatory",)},
    )

    result = completion.validate_construction_refactor_completion(tmp_path)

    assert result["construction_human_agent_integrated"] is False
    assert result["observatory_read_only"] is False
''',
    )


def main() -> None:
    patch_profile()
    patch_server()
    patch_completion_status()
    patch_tests()


if __name__ == "__main__":
    main()
