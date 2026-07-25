from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def patch_compiler() -> None:
    path = Path("aura_bilateral_intent_compiler.py")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(
        index
        for index, line in enumerate(lines)
        if line == "    elif question.ambiguity_class == AmbiguityClass.CONTRADICTION.value:\n"
    )
    end = next(
        index for index in range(start + 1, len(lines))
        if lines[index].startswith("    remaining = tuple(")
    )
    current = "".join(lines[start:end])
    if "contradiction clarification must select one declared requirement" not in current:
        replacement = [
            "    elif question.ambiguity_class == AmbiguityClass.CONTRADICTION.value:\n",
            "        candidates = tuple(question.candidate_answers)\n",
            "        if len(candidates) != 2 or value not in candidates:\n",
            "            raise ValueError(\n",
            "                \"contradiction clarification must select one declared requirement\"\n",
            "            )\n",
            "        positive_candidate, negative_candidate = candidates\n",
            "        if value == positive_candidate:\n",
            "            negatives = [\n",
            "                item\n",
            "                for item in negatives\n",
            "                if item.statement != negative_candidate\n",
            "                and item.target != negative_candidate\n",
            "            ]\n",
            "        else:\n",
            "            positives = [\n",
            "                item for item in positives if item != positive_candidate\n",
            "            ]\n",
            "            if not positives:\n",
            "                positives = [\n",
            "                    \"Preserve the confirmed prohibition and locked guardrails.\"\n",
            "                ]\n",
        ]
        lines[start:end] = replacement
    path.write_text("".join(lines), encoding="utf-8")


def hardened_identity() -> str:
    return dedent(
        '''
        def _repository_identity(root: Path) -> dict[str, Any]:
            def git_text(*args: str) -> str:
                result = subprocess.run(
                    ["git", *args],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                return result.stdout.strip()

            def git_bytes(*args: str) -> bytes:
                result = subprocess.run(
                    ["git", *args],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    timeout=20,
                )
                return bytes(result.stdout)

            def content_digest(path: Path) -> tuple[str, str]:
                digest = hashlib.blake2b(digest_size=32)
                if path.is_symlink():
                    target = str(path.readlink()).encode(
                        "utf-8", errors="surrogateescape"
                    )
                    digest.update(target)
                    return "symlink", digest.hexdigest()
                with path.open("rb") as handle:
                    while True:
                        chunk = handle.read(1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                return "file", digest.hexdigest()

            head = git_text("rev-parse", "HEAD")
            status = git_text("status", "--porcelain=v1", "--untracked-files=all")
            clean = not bool(status.strip())
            tracked_diff = git_bytes("diff", "--binary", "--full-index", "HEAD", "--")
            untracked_paths = git_bytes(
                "ls-files", "--others", "--exclude-standard", "-z"
            ).split(b"\\0")
            untracked: list[dict[str, str]] = []
            for raw_path in untracked_paths:
                if not raw_path:
                    continue
                relative = raw_path.decode("utf-8", errors="surrogateescape")
                candidate = root / relative
                if not candidate.is_symlink() and not candidate.is_file():
                    continue
                kind, digest = content_digest(candidate)
                untracked.append(
                    {
                        "path": relative.replace("\\\\", "/"),
                        "kind": kind,
                        "digest": digest,
                    }
                )
            untracked.sort(key=lambda item: item["path"])
            tree_digest = stable_digest(
                {
                    "head": head,
                    "tracked_diff_digest": hashlib.blake2b(
                        tracked_diff, digest_size=32
                    ).hexdigest(),
                    "untracked": untracked,
                }
            )
            return {
                "repository_head": head,
                "source_tree_digest": tree_digest,
                "working_tree_clean": clean,
                "working_tree_clean_receipt": stable_digest(
                    {
                        "head": head,
                        "clean": clean,
                        "source_tree_digest": tree_digest,
                        "status": status.splitlines(),
                    }
                ),
            }
        '''
    ).lstrip("\n")


def patch_gate() -> None:
    path = Path("aura_arena_gate_dialogue.py")
    text = path.read_text(encoding="utf-8")

    identity_start = text.index("def _repository_identity(root: Path) -> dict[str, Any]:")
    identity_end = text.index("\ndef _fallback_response(", identity_start)
    current_identity = text[identity_start:identity_end]
    if "tracked_diff_digest" not in current_identity:
        text = text[:identity_start] + hardened_identity() + text[identity_end + 1 :]

    lines = text.splitlines(keepends=True)
    legacy_start = next(
        index
        for index, line in enumerate(lines)
        if line.lstrip() == "elif question.candidate_answers:\n"
    )
    legacy_indent = lines[legacy_start][:-len(lines[legacy_start].lstrip())]
    legacy_end = next(
        index for index in range(legacy_start + 1, len(lines))
        if lines[index] == legacy_indent + "else:\n"
    )
    current_legacy = "".join(lines[legacy_start:legacy_end])
    if 'question.ambiguity_class == "CONTRADICTION"' not in current_legacy:
        child = legacy_indent + "    "
        grandchild = child + "    "
        lines[legacy_start:legacy_end] = [
            legacy_indent + "elif question.candidate_answers:\n",
            child + "answer = (\n",
            grandchild + "question.candidate_answers[-1]\n",
            grandchild + 'if question.ambiguity_class == "CONTRADICTION"\n',
            grandchild + "else question.candidate_answers[0]\n",
            child + ")\n",
        ]
    text = "".join(lines)

    if "confirmation_expired" not in text:
        confirmed_loop = (
            "        confirmed: list[dict[str, Any]] = []\n"
            "        for row in list(self.confirmed.values())[-10:]:\n"
        )
        if text.count(confirmed_loop) != 1:
            raise SystemExit("confirmed status loop was not found exactly once")
        text = text.replace(
            confirmed_loop,
            "        confirmed: list[dict[str, Any]] = []\n"
            "        observed_at = time.time()\n"
            "        for row in list(self.confirmed.values())[-10:]:\n",
            1,
        )
        phase_block = (
            '            if row["phase_hash"] != current_phase_hash:\n'
            '                stale_reasons.append("workflow_phase_or_evidence_changed")\n'
        )
        if text.count(phase_block) != 1:
            raise SystemExit("confirmation status phase block was not found exactly once")
        expiry_block = (
            phase_block
            + '            receipt = dict(\n'
            + '                (proposal.get("canonical_compilation") or {}).get(\n'
            + '                    "confirmation_receipt"\n'
            + '                )\n'
            + '                or {}\n'
            + '            )\n'
            + '            expires_at = float(receipt.get("expires_at") or 0.0)\n'
            + '            if expires_at and observed_at >= expires_at:\n'
            + '                stale_reasons.append("confirmation_expired")\n'
        )
        text = text.replace(phase_block, expiry_block, 1)

    path.write_text(text, encoding="utf-8")


CONTRADICTION_TEST = r'''
def test_contradiction_clarification_preserves_the_selected_side():
    from aura_bilateral_intent_compiler import (
        analyze_bilateral_request,
        apply_clarification,
    )
    from aura_intent_refinement import AmbiguityClass

    request = "Widen the selected file scope. Do not widen the selected file scope."
    positive_analysis = analyze_bilateral_request(request)
    positive_question = next(
        item
        for item in positive_analysis.questions
        if item.ambiguity_class == AmbiguityClass.CONTRADICTION.value
    )
    positive_choice, negative_choice = positive_question.candidate_answers
    positive_resolved = apply_clarification(
        positive_analysis,
        question=positive_question,
        answer=positive_choice,
    )
    assert positive_choice in positive_resolved.positive_requirements
    assert all(
        item.statement != negative_choice and item.target != negative_choice
        for item in positive_resolved.negative_requirements
    )

    negative_analysis = analyze_bilateral_request(request)
    negative_question = next(
        item
        for item in negative_analysis.questions
        if item.ambiguity_class == AmbiguityClass.CONTRADICTION.value
    )
    positive_choice, negative_choice = negative_question.candidate_answers
    negative_resolved = apply_clarification(
        negative_analysis,
        question=negative_question,
        answer=negative_choice,
    )
    assert positive_choice not in negative_resolved.positive_requirements
    assert any(
        item.statement == negative_choice or item.target == negative_choice
        for item in negative_resolved.negative_requirements
    )
    assert negative_resolved.teach_back is not None
'''

REPOSITORY_IDENTITY_TEST = r'''
def test_repository_identity_detects_same_path_content_drift(tmp_path):
    from aura_arena_gate_dialogue import _repository_identity

    def git(*args):
        subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init")
    git("config", "user.name", "Aura Test")
    git("config", "user.email", "aura-test@example.invalid")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    git("add", "tracked.txt")
    git("commit", "-m", "base")

    tracked.write_text("candidate one\n", encoding="utf-8")
    first = _repository_identity(tmp_path)
    tracked.write_text("candidate two\n", encoding="utf-8")
    second = _repository_identity(tmp_path)
    assert first["source_tree_digest"] != second["source_tree_digest"]

    untracked = tmp_path / "new.txt"
    untracked.write_text("untracked one\n", encoding="utf-8")
    third = _repository_identity(tmp_path)
    untracked.write_text("untracked two\n", encoding="utf-8")
    fourth = _repository_identity(tmp_path)
    assert third["source_tree_digest"] != fourth["source_tree_digest"]
'''

LEGACY_CONTRADICTION_TEST = r'''
def test_legacy_one_turn_contradiction_preserves_prohibition(workflow):
    from aura_arena_gate_dialogue import ArenaGateDialogueService

    service = ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment="Widen the selected file scope. Do not widen the selected file scope.",
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    assert proposal["status"] == "PENDING_HUMAN_APPROVAL"
    assert any(
        item.get("target") == "widen the selected file scope"
        for item in proposal["negative_requirements"]
    )
    assert "Widen the selected file scope." not in proposal["positive_requirements"]
'''

EXPIRY_TEST = r'''
def test_confirmation_status_reports_expired_receipt(workflow, monkeypatch):
    import aura_arena_gate_dialogue as gate_module

    now = 1_800_000_000.0
    monkeypatch.setattr(gate_module.time, "time", lambda: now)
    service = gate_module.ArenaGateDialogueService(REPO_ROOT, workflow)
    proposal = service.address(
        comment=(
            f"{gate_module.BILATERAL_MARKER} "
            "Frame this selected renderer. Do not widen its scope."
        ),
        node_context=NODE_CONTEXT,
        stage_hint="FRAME",
        prefer_model=False,
    )
    approved = service.approve(
        proposal_id=proposal["proposal_id"],
        approved=True,
        current_node_context=NODE_CONTEXT,
        stage_hint="FRAME",
    )
    assert approved["ok"] is True

    monkeypatch.setattr(
        gate_module.time,
        "time",
        lambda: now + gate_module.SESSION_TTL_SECONDS + 1.0,
    )
    status = service.status()
    assert status["confirmed"][0]["confirmation_currency"] == "STALE"
    assert "confirmation_expired" in status["confirmed"][0]["stale_reasons"]
'''


def patch_tests() -> None:
    path = Path("tests/test_aura_bilateral_gate_dialogue.py")
    text = path.read_text(encoding="utf-8")
    if "import subprocess\n" not in text:
        text = text.replace("import json\n", "import json\nimport subprocess\n", 1)

    marker = "\ndef test_affordance_map_declares_current_review_learning_extension():\n"
    additions: list[str] = []
    candidates = (
        ("def test_contradiction_clarification_preserves_the_selected_side", CONTRADICTION_TEST),
        ("def test_repository_identity_detects_same_path_content_drift", REPOSITORY_IDENTITY_TEST),
        ("def test_legacy_one_turn_contradiction_preserves_prohibition", LEGACY_CONTRADICTION_TEST),
        ("def test_confirmation_status_reports_expired_receipt", EXPIRY_TEST),
    )
    for function_marker, block in candidates:
        if function_marker not in text:
            additions.append(block.strip("\n") + "\n\n")
    if additions:
        if text.count(marker) != 1:
            raise SystemExit("test insertion marker was not found exactly once")
        text = text.replace(marker, "\n" + "".join(additions) + marker, 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_compiler()
    patch_gate()
    patch_tests()


if __name__ == "__main__":
    main()
