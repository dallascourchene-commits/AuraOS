# Unified Memory U7 Exact-Head Discovery

## Source identity
```text
684250aff7fde780e8b90607a618bff7d7027dd6
?? .aura/analysis/
```

## Navigator objective query
```text
Traceback (most recent call last):
  File "/home/runner/work/AuraOS/AuraOS/aura_codebase_navigator.py", line 31, in <module>
    from aura_substrate import IntentCompressor, estimate_tokens, parse_master_key_header
  File "/home/runner/work/AuraOS/AuraOS/aura_substrate.py", line 48, in <module>
    import numpy as np
ModuleNotFoundError: No module named 'numpy'
```

## Exact symbols and owners
```text
aura_unified_memory_continuity.py:1202:class ContinuitySensitivityReceipt:
aura_unified_memory_continuity.py:1279:            raise ValueError("ContinuitySensitivityReceipt identity mismatch")
aura_unified_memory_continuity.py:1280:        _packet_size(self.to_dict(), "ContinuitySensitivityReceipt")
aura_unified_memory_continuity.py:1967:) -> ContinuitySensitivityReceipt:
aura_unified_memory_continuity.py:2042:    return ContinuitySensitivityReceipt(
aura_unified_memory_continuity.py:2091:def evaluate_learning_to_reproof(
aura_unified_memory_continuity.py:2097:    continuity_receipt: ContinuitySensitivityReceipt,
aura_unified_memory_continuity.py:2160:def relationship_experience_kwargs(
aura_unified_memory_continuity.py:2172:    """Return exact kwargs for RelationshipExperienceObservation.create.
aura_unified_memory_continuity.py:2222:def evaluate_qdkt_consequential_admission(
aura_unified_memory_continuity.py:2224:    continuity_receipt: ContinuitySensitivityReceipt,
aura_unified_memory_continuity.py:2236:    from aura_relationship_experience import RelationshipExperienceObservation
aura_unified_memory_continuity.py:2257:    elif not isinstance(relationship_experience, RelationshipExperienceObservation):
aura_unified_memory_continuity.py:2372:    "ContinuitySensitivityReceipt",
aura_unified_memory_continuity.py:2392:    "evaluate_learning_to_reproof",
aura_unified_memory_continuity.py:2393:    "evaluate_qdkt_consequential_admission",
aura_unified_memory_continuity.py:2395:    "relationship_experience_kwargs",
aura_unified_memory_continuity_toolchain.py:27:    ContinuitySensitivityReceipt,
aura_unified_memory_continuity_toolchain.py:545:        "crucible": "aura_arena_crucible.ArenaCrucibleService",
aura_unified_memory_continuity_toolchain.py:546:        "relationship_experience": "aura_relationship_experience.RelationshipExperienceObservation",
aura_unified_memory_continuity_toolchain.py:547:        "qdkt": "aura_qdkt.UnifiedQDKT",
aura_unified_memory_continuity_toolchain.py:592:    continuity_receipt: ContinuitySensitivityReceipt | None = None,
aura_unified_memory_continuity_toolchain.py:600:    receipt = _typed(continuity_receipt, ContinuitySensitivityReceipt, "continuity_receipt")
aura_arena_crucible.py:31:class ArenaCrucibleService:
aura_relationship_experience.py:150:class RelationshipExperienceObservation:
aura_relationship_experience.py:304:    ) -> "RelationshipExperienceObservation":
aura_relationship_experience.py:372:    def from_dict(cls, value: Mapping[str, Any]) -> "RelationshipExperienceObservation":
aura_relationship_experience.py:452:    observations: Sequence[RelationshipExperienceObservation | Mapping[str, Any]],
aura_relationship_experience.py:459:        observation = raw if isinstance(raw, RelationshipExperienceObservation) else RelationshipExperienceObservation.from_dict(raw)
aura_relationship_experience.py:478:    observations: Sequence[RelationshipExperienceObservation | Mapping[str, Any]],
aura_relationship_experience.py:487:        observation = raw if isinstance(raw, RelationshipExperienceObservation) else RelationshipExperienceObservation.from_dict(raw)
aura_relationship_experience.py:517:    observation: RelationshipExperienceObservation,
aura_relationship_experience.py:546:    "RelationshipExperienceObservation",
aura_qdkt.py:149:class UnifiedQDKT:
aura_qdkt.py:672:_INSTANCE: UnifiedQDKT | None = None
aura_qdkt.py:675:def get_qdkt() -> UnifiedQDKT:
aura_qdkt.py:678:        _INSTANCE = UnifiedQDKT()
tests/test_aura_unified_memory_continuity.py:12:from aura_relationship_experience import RelationshipExperienceObservation
tests/test_aura_unified_memory_continuity.py:19:    ContinuitySensitivityReceipt,
tests/test_aura_unified_memory_continuity.py:35:    evaluate_learning_to_reproof,
tests/test_aura_unified_memory_continuity.py:36:    evaluate_qdkt_consequential_admission,
tests/test_aura_unified_memory_continuity.py:38:    relationship_experience_kwargs,
tests/test_aura_unified_memory_continuity.py:317:def _approved_learning_decision(receipt: ContinuitySensitivityReceipt) -> LearningToReproofDecision:
tests/test_aura_unified_memory_continuity.py:318:    return evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:334:    receipt: ContinuitySensitivityReceipt,
tests/test_aura_unified_memory_continuity.py:336:) -> RelationshipExperienceObservation:
tests/test_aura_unified_memory_continuity.py:337:    kwargs = relationship_experience_kwargs(
tests/test_aura_unified_memory_continuity.py:353:    return RelationshipExperienceObservation.create(transaction_time=80.0, **kwargs)
tests/test_aura_unified_memory_continuity.py:632:    closed = evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:651:    closed_decision = evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:658:    closed = evaluate_qdkt_consequential_admission(
tests/test_aura_unified_memory_continuity.py:676:    admitted = evaluate_qdkt_consequential_admission(
tests/test_aura_unified_memory_continuity.py:831:        evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:839:        evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:853:        evaluate_qdkt_consequential_admission(
tests/test_aura_unified_memory_continuity.py:867:        evaluate_qdkt_consequential_admission(
tests/test_aura_unified_memory_continuity.py:906:        ContinuitySensitivityReceipt,
tests/test_aura_unified_memory_continuity.py:920:        ContinuitySensitivityReceipt: receipt,
tests/test_aura_unified_memory_continuity.py:933:        LearningToReproofDecision: evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:940:        QDKTConsequentialAdmission: evaluate_qdkt_consequential_admission(
tests/test_aura_unified_memory_continuity.py:942:            learning_decision=evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:1082:        relationship_experience_kwargs(
tests/test_aura_unified_memory_continuity.py:1100:    forged_digest = RelationshipExperienceObservation.create(
tests/test_aura_unified_memory_continuity.py:1103:            **relationship_experience_kwargs(
tests/test_aura_unified_memory_continuity.py:1123:        evaluate_qdkt_consequential_admission(
tests/test_aura_unified_memory_continuity.py:1136:    forged_objective = RelationshipExperienceObservation.create(
tests/test_aura_unified_memory_continuity.py:1139:            **relationship_experience_kwargs(
tests/test_aura_unified_memory_continuity.py:1159:        evaluate_qdkt_consequential_admission(
tests/test_aura_unified_memory_continuity.py:1202:    ineligible = evaluate_learning_to_reproof(
tests/test_aura_unified_memory_continuity.py:1211:    admission = evaluate_qdkt_consequential_admission(
tests/test_aura_crucible_phase_b.py:11:from aura_arena_crucible import ArenaCrucibleService
tests/test_aura_crucible_phase_b.py:190:    service = ArenaCrucibleService(tmp_path)
tests/test_aura_relationship_compass_finalization.py:27:    RelationshipExperienceObservation,
tests/test_aura_relationship_compass_finalization.py:480:    return RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:558:        RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:562:    unredacted_payload = RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:568:        RelationshipExperienceObservation.from_dict(unredacted_payload)
tests/test_aura_relationship_compass_finalization.py:581:        RelationshipExperienceObservation.from_dict(relabeled_payload)
tests/test_aura_relationship_compass_finalization.py:582:    redacted = RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:618:        RelationshipExperienceObservation.from_dict(payload)
tests/test_aura_relationship_compass_finalization.py:620:        RelationshipExperienceObservation(
tests/test_aura_relationship_compass_finalization.py:628:    created = RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:649:        RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:665:        RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:682:        RelationshipExperienceObservation.create(
tests/test_aura_relationship_compass_finalization.py:715:            RelationshipExperienceObservation.from_dict(candidate)
```

## Candidate persistence and invocation owners
```text
./aura_arena_attempt_archive.py
./aura_arena_crucible.py
./aura_crucible_cli.py
./aura_crucible_miner.py
./aura_crucible_store.py
./aura_crucible_types.py
./aura_crucible_validation.py
./aura_phase_c3_trial_crucible.py
./aura_qdkt.py
./aura_qdkt_compatibility.py
./aura_qdkt_compatibility_types.py
./aura_qdkt_inventory.py
./aura_qdkt_observations.py
./aura_qdkt_projection.py
./aura_qdkt_projection_io.py
./aura_qdkt_projection_types.py
./aura_refactor_state_ledger.py
./aura_refactor_state_ledger_core.py
./aura_refactor_state_ledger_metrics.py
./aura_relationship_experience.py
./aura_showcase/attempt-archive.js
./aura_showcase/crucible.css
./aura_showcase/crucible.js
./aura_showcase_crucible.py
./docs/AMD_TRACK3_CRUCIBLE_DEMO.md
./docs/AURA_ARENA_ATTEMPT_ARCHIVE.md
./docs/AURA_ARENA_CRUCIBLE_PHASE_B.md
./docs/AURA_OBSERVATORY_CRUCIBLE_HANDOFF.md
./docs/AURA_PHASE_C3_TRIAL_CRUCIBLE.md
./docs/AURA_QDKT_COMPATIBILITY_P6_2.md
./docs/AURA_QDKT_EVENTS_P6_1.md
./schemas/aura_relationship_experience.schema.json
./tests/test_aura_crucible_phase_b.py
./tests/test_aura_phase_c3_trial_crucible.py
./tests/test_aura_qdkt_compatibility.py
./tests/test_aura_qdkt_compatibility_hardening.py
./tests/test_aura_qdkt_event_recording.py
./tests/test_aura_qdkt_inventory.py
./tests/test_aura_qdkt_observations.py
./tests/test_aura_qdkt_projection_core.py
./tests/test_aura_qdkt_projection_hardening.py
./tests/test_aura_showcase_attempt_archive.py
./tests/test_aura_showcase_observatory_crucible.py
```

## Topology health
```text
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/runner/work/AuraOS/AuraOS/aura_agent_arena_cli.py", line 31, in <module>
    from aura_agent_arena_fireworks import fireworks_patch_worker
  File "/home/runner/work/AuraOS/AuraOS/aura_agent_arena_fireworks.py", line 17, in <module>
    from aura_llm_egress import (
  File "/home/runner/work/AuraOS/AuraOS/aura_llm_egress.py", line 40, in <module>
    from aura_paper_memory import (
  File "/home/runner/work/AuraOS/AuraOS/aura_paper_memory.py", line 28, in <module>
    import numpy as np
ModuleNotFoundError: No module named 'numpy'
```

## Stabilization status
```text
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/runner/work/AuraOS/AuraOS/aura_agent_arena_cli.py", line 31, in <module>
    from aura_agent_arena_fireworks import fireworks_patch_worker
  File "/home/runner/work/AuraOS/AuraOS/aura_agent_arena_fireworks.py", line 17, in <module>
    from aura_llm_egress import (
  File "/home/runner/work/AuraOS/AuraOS/aura_llm_egress.py", line 40, in <module>
    from aura_paper_memory import (
  File "/home/runner/work/AuraOS/AuraOS/aura_paper_memory.py", line 28, in <module>
    import numpy as np
ModuleNotFoundError: No module named 'numpy'
```

## Architecture harness doctor
```text
{
  "ai_handoff": {
    "default_inline_max_bytes": 262144,
    "generated_artifact_disposition": "REGENERATE_FROM_FINAL_TREE",
    "hard_inline_max_bytes": 1048576,
    "recommended_command": "python scripts/aura_architecture_harness.py --repo-root . handoff --output-dir ../AuraOS-ai-handoff",
    "review_authority": "exact_source_files_and_tests_only",
    "version": "AURA_ARCHITECTURE_HARNESS_AI_HANDOFF_V1"
  },
  "codemap": {
    "file_count": 1384,
    "sha256": "9ac5611619901480589a00bded39677e3a84d01c9357e48a95d9903793570298",
    "size_bytes": 6965554,
    "symbol_count": 0
  },
  "git_identity": {
    "available": true,
    "branch": "analysis/unified-memory-u7-discovery-20260724",
    "clean": false,
    "head": "684250aff7fde780e8b90607a618bff7d7027dd6",
    "source_sha": "",
    "status": [
      "?? .aura/analysis/"
    ],
    "synthetic_local_identity": false
  },
  "github_publication_route": {
    "authority": {
      "automatic_blob_creation": false,
      "automatic_commit": false,
      "automatic_merge": false,
      "automatic_pull_request": false,
      "automatic_ref_update": false,
      "automatic_tree_creation": false,
      "base_branch_update_authorized": false,
      "execution_requires_external_authorized_connector": true,
      "force_ref_update": false,
      "human_review_required": true,
      "production_mutation": false
    },
    "case_study": {
      "actual_blob_intents_recorded": false,
      "confirmed_force_required": false,
      "created_commit_sha": "ea9675ada226bae31fbd74e10dced81797aac1a8",
      "created_tree_sha": "beed4f512975dd304ff36aa7e2936bf2212cead1",
      "note": "This record preserves independently checked historical object IDs only. It intentionally contains no synthetic placeholder blob or route digest.",
      "outcome": "atomic Git-tree publication succeeded on the live PR branch",
      "parent_commit_sha": "7207c2bf6ab179d6af41ca4ed6b9f5adcce1b307",
      "recorded_at": "2026-07-22",
      "resolved_parent_tree_sha": "359a19f26aa3f4066c51263965709c8b026eae6c",
      "route_digest_is_provenance_receipt": false,
      "scope": "manual review-remediation publication, not G4 payload cleanup"
    },
    "connector_sequence": [
      "get_pr_info",
      "fetch_commit",
      "create_blob",
      "create_tree",
      "create_commit",
      "get_pr_info",
      "update_ref(force=false)",
      "verify"
    ],
    "preconditions": [
      "independently re-fetch live PR and commit metadata",
      "bind repository, PR number, head ref, base ref, head SHA, and tree SHA",
      "never target the base ref"
    ],
    "preferred_fallback": "atomic_git_object_route",
    "rollback": {
      "after_update_ref": "reviewed revert only; never force rewind",
      "before_update_ref": "discard unattached objects"
    },
    "status": "PROPOSAL_ONLY_EXTERNAL_CONNECTOR_REQUIRED",
    "trust_model": "UNTRUSTED_PROPOSAL_EXECUTOR_MUST_REFETCH",
    "version": "AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING_V5",
    "workflow_discovery": {
      "branch_new_pull_request_workflow_jobs_reliable": false,
      "commit_workflow_lookup_scope": "pull_request_triggered_first_page",
      "connector_visibility_limit": "The connector workflow-run lookup used during PR #184 exposed pull-request-triggered runs but did not reliably expose branch push runs.",
      "contents_api_partial_state_risk": "Sequential Contents-API writes create one commit per path and can expose an intermediate partial source state.",
      "preferred_fallback": "atomic_git_object_route",
      "pull_request_definition_source": "base_branch",
      "reason": "GitHub evaluates pull_request workflow definitions from the trusted base branch. New or materially rewritten jobs that exist only on a PR branch must not be relied on to publish that PR's source changes."
    }
  },
  "ok": true,
  "patch_authority": "exact_source_spans_and_hashes_only",
  "production_mutation": false,
  "repo_root": "/home/runner/work/AuraOS/AuraOS",
  "safe_to_patch": false,
  "task_watchdog": {
    "checkin_assessments": [
      "HEALTHY_CONTINUE",
      "SLOW_BUT_PROGRESSING",
      "STALLED_REASSESS",
      "UNKNOWN_REASSESS"
    ],
    "checkin_seconds": 600,
    "enabled": true,
    "events_file": "watchdog_events.jsonl",
    "harness_version": "AURA_ARCHITECTURE_HARNESS_V1",
    "human_review_required": true,
    "pause_assessment": "PAUSED_FOR_REASSESSMENT",
    "pause_receipt_file": "watchdog_pause_receipt.json",
    "pause_seconds": 1200,
    "production_mutation": false,
    "resume_required": true,
    "resume_supported": true,
    "status_file": "watchdog_status.json",
    "version": "AURA_ARCHITECTURE_HARNESS_TASK_WATCHDOG_V1"
  },
  "version": "AURA_ARCHITECTURE_HARNESS_V1"
}
```
