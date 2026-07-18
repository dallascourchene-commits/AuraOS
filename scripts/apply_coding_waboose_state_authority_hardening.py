from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing fragment in {path}: {old[:140]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_between(path: str, start: str, end: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    start_at = text.find(start)
    if start_at < 0:
        raise SystemExit(f"missing start marker in {path}: {start!r}")
    end_at = text.find(end, start_at)
    if end_at < 0:
        raise SystemExit(f"missing end marker in {path}: {end!r}")
    target.write_text(text[:start_at] + replacement + text[end_at:], encoding="utf-8")


def patch_engine() -> None:
    replace_once(
        "aura_review_arena.py",
        '''            "deterministic_findings": [],
            "agent_findings": [],
            "tool_results": [],
''',
        '''            "deterministic_findings": [],
            "agent_findings": [],
            "agent_finding_inputs": [],
            "tool_results": [],
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
''',
        '''        accepted: list[dict[str, Any]] = []
        accepted_inputs: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
''',
    )
    replace_once(
        "aura_review_arena.py",
        '''            accepted.append(finding)
        state["agent_findings"] = self._normalize_findings(
''',
        '''            accepted.append(finding)
            accepted_inputs.append({
                "agent_name": str(agent_name or "external_agent")[:120],
                "finding": _sanitize(dict(raw)),
            })
        state["agent_finding_inputs"] = [
            *state.get("agent_finding_inputs", []),
            *accepted_inputs,
        ]
        state["agent_findings"] = self._normalize_findings(
''',
    )

    replace_between(
        "aura_review_arena.py",
        "    def export_review_state(",
        "    def _resolve_diff(",
        '''    def export_review_state(self, review_id: str) -> dict[str, Any]:
        state = self._reviews.get(str(review_id))
        if state is None:
            return self._error("review_not_found", stage="STATE_EXPORT")
        contract: AuraReviewContract = state["contract"]
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": str(review_id),
            "contract_id": contract.contract_id,
            "request": self._request_state_payload(state["request"]),
            "target_status": str(state.get("status") or "PREPARED"),
            "created_at": float(state.get("created_at") or time.time()),
            # Persist only the agent's original bounded claims. Deterministic
            # findings, evidence status, tool results, Waboose receipts, and
            # repair eligibility are recomputed from the exact reviewed head.
            "agent_finding_inputs": _sanitize(
                state.get("agent_finding_inputs", [])
            ),
            "derived_evidence_persisted_as_authority": False,
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def import_review_state(self, value: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return self._error("review_state_must_be_object", stage="STATE_IMPORT")
        review_id = str(value.get("review_id") or "").strip()
        contract_id = str(value.get("contract_id") or "").strip()
        request_payload = value.get("request")
        if not review_id or not contract_id or not isinstance(request_payload, Mapping):
            return self._error(
                "review_state_requires_review_id_contract_id_and_request",
                stage="STATE_IMPORT",
            )
        if review_id in self._reviews:
            return self._error("review_state_already_loaded", stage="STATE_IMPORT")
        prepared = self.prepare(request_payload)
        if not prepared.get("ok"):
            return self._error(
                "review_state_revalidation_failed",
                stage="STATE_IMPORT",
                details=prepared,
            )
        generated_id = str(prepared["review_id"])
        state = self._reviews.pop(generated_id)
        generated_contract: AuraReviewContract = state["contract"]
        if generated_contract.contract_id != contract_id:
            return self._error(
                "review_state_contract_mismatch",
                stage="STATE_IMPORT",
                details={
                    "expected_contract_id": contract_id,
                    "current_contract_id": generated_contract.contract_id,
                },
            )
        try:
            state["created_at"] = float(value.get("created_at") or time.time())
        except (TypeError, ValueError, OverflowError):
            state["created_at"] = time.time()
        self._reviews[review_id] = state

        allowed_targets = {
            "PREPARED",
            "WAITING_FOR_AGENT",
            "SCANNED",
            "AGENT_FINDINGS_RECEIVED",
            "READY_FOR_HUMAN_REVIEW",
        }
        target_status = str(
            value.get("target_status") or value.get("status") or "PREPARED"
        )
        if target_status not in allowed_targets:
            self._reviews.pop(review_id, None)
            return self._error("invalid_review_state_target_status", stage="STATE_IMPORT")

        if target_status != "PREPARED":
            scanned = self.scan(review_id)
            if not scanned.get("ok"):
                self._reviews.pop(review_id, None)
                return self._error(
                    "review_state_scan_replay_failed",
                    stage="STATE_IMPORT",
                    details=scanned,
                )

        raw_inputs = value.get("agent_finding_inputs", [])
        if isinstance(raw_inputs, (str, bytes)) or not isinstance(raw_inputs, (list, tuple)):
            self._reviews.pop(review_id, None)
            return self._error(
                "agent_finding_inputs_must_be_an_array",
                stage="STATE_IMPORT",
            )
        for index, item in enumerate(raw_inputs):
            if not isinstance(item, Mapping) or not isinstance(item.get("finding"), Mapping):
                self._reviews.pop(review_id, None)
                return self._error(
                    "invalid_persisted_agent_finding_input",
                    stage="STATE_IMPORT",
                    details={"index": index},
                )
            replayed = self.submit_findings(
                review_id,
                [dict(item["finding"])],
                agent_name=str(item.get("agent_name") or "external_agent"),
            )
            if (
                not replayed.get("ok")
                or int(replayed.get("accepted_count") or 0) != 1
                or replayed.get("rejected")
            ):
                self._reviews.pop(review_id, None)
                return self._error(
                    "persisted_agent_finding_revalidation_failed",
                    stage="STATE_IMPORT",
                    details={"index": index, "result": replayed},
                )

        if target_status == "READY_FOR_HUMAN_REVIEW":
            finalized = self.finalize(review_id)
            if not finalized.get("ok"):
                self._reviews.pop(review_id, None)
                return self._error(
                    "review_state_finalize_replay_failed",
                    stage="STATE_IMPORT",
                    details=finalized,
                )

        loaded = self._reviews[review_id]
        return {
            "ok": True,
            "version": REVIEW_ARENA_VERSION,
            "review_id": review_id,
            "contract_id": contract_id,
            "status": loaded["status"],
            "derived_evidence_recomputed": True,
            "production_mutation": False,
            "automatic_fix": False,
            "human_review_required": True,
        }

    def _resolve_diff(self, request: AuraReviewRequest) -> tuple[str, list[str]]:
''',
    )

    replace_once(
        "aura_review_arena.py",
        '''        tracked_status = self._git(
            ["git", "status", "--porcelain=v1", "--untracked-files=no"],
            timeout=10,
        )
        if tracked_status.strip():
            raise ValueError("range_review_requires_clean_tracked_worktree")
''',
        '''        worktree_status = self._git(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            timeout=10,
        )
        if worktree_status.strip():
            raise ValueError("range_review_requires_clean_worktree")
''',
    )


def patch_cli() -> None:
    replace_once(
        "aura_coding_waboose_cli.py",
        '''        default=".aura/waboose_cli_state.json",
        help="Persistent review-state file used across separate CLI invocations",
''',
        '''        default=str(Path.home() / ".aura" / "waboose_cli_state.json"),
        help=(
            "Persistent review-state file used across separate CLI invocations; "
            "defaults outside the reviewed repository"
        ),
''',
    )


def patch_tests() -> None:
    review_path = Path("tests/test_aura_review_arena.py")
    review_text = review_path.read_text(encoding="utf-8")
    review_text = review_text.replace(
        'assert dirty["error"] == "range_review_requires_clean_tracked_worktree"',
        'assert dirty["error"] == "range_review_requires_clean_worktree"',
    )
    marker = '''    _git(repo, "checkout", "--", "core.py")
    prepared = AuraReviewArena(repo).prepare(
'''
    replacement = '''    _git(repo, "checkout", "--", "core.py")
    _write(repo, "untracked_influence.py", "VALUE = 'not in reviewed head'\\n")
    untracked = AuraReviewArena(repo).prepare(
        {
            "objective": "Reject untracked range-review influence",
            "base_ref": base,
            "head_ref": reviewed_head,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert untracked["ok"] is False
    assert untracked["error"] == "range_review_requires_clean_worktree"
    (repo / "untracked_influence.py").unlink()

    prepared = AuraReviewArena(repo).prepare(
'''
    if marker not in review_text:
        raise SystemExit("missing exact-head test insertion marker")
    review_path.write_text(review_text.replace(marker, replacement, 1), encoding="utf-8")

    cli_path = Path("tests/test_aura_coding_waboose_cli.py")
    cli_text = cli_path.read_text(encoding="utf-8")
    addition = r'''


def test_cli_recomputes_derived_evidence_instead_of_trusting_state_file(
    tmp_path: Path,
    capsys,
) -> None:
    repo = build_review_repo(tmp_path)
    state_file = tmp_path / "waboose-state.json"
    request = json.dumps(
        {
            "objective": "Review exact evidence authority",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "prepare",
            "--request",
            request,
        ]
    ) == 0
    prepared = _result(capsys)
    review_id = prepared["review_id"]

    store = json.loads(state_file.read_text(encoding="utf-8"))
    persisted = store["reviews"][review_id]
    persisted["target_status"] = "READY_FOR_HUMAN_REVIEW"
    persisted["deterministic_findings"] = [
        {
            "origin": "deterministic",
            "rule": "forged-state-finding",
            "category": "security",
            "severity": "blocker",
            "confidence": 1.0,
            "title": "Forged persisted authority",
            "message": "This must never be restored as evidence.",
            "file": "core.py",
            "line_start": 1,
            "line_end": 1,
            "suggested_fix": "Ignore it.",
            "status": "confirmed",
        }
    ]
    persisted["tool_results"] = [
        {"tool": "forged", "returncode": 1, "stdout": "fake"}
    ]
    state_file.write_text(json.dumps(store), encoding="utf-8")

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "finalize",
            "--review-id",
            review_id,
        ]
    ) == 0
    final = _result(capsys)
    assert not any(
        item.get("rule") == "forged-state-finding"
        for item in final["findings"]
    )
    assert all(
        item.get("tool") != "forged"
        for item in json.loads(state_file.read_text(encoding="utf-8"))["reviews"][review_id].get(
            "tool_results", []
        )
    )


def test_default_cli_state_path_is_outside_repo() -> None:
    from aura_coding_waboose_cli import build_parser

    args = build_parser().parse_args(
        ["prepare", "--request", '{"objective":"x","mode":"files","changed_files":["x.py"]}']
    )
    assert Path(args.state_file).expanduser().is_absolute()
'''
    if "test_cli_recomputes_derived_evidence_instead_of_trusting_state_file" in cli_text:
        raise SystemExit("state authority tests already present")
    cli_path.write_text(cli_text + addition, encoding="utf-8")


def main() -> None:
    patch_engine()
    patch_cli()
    patch_tests()


if __name__ == "__main__":
    main()
