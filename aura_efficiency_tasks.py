"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa10-[Q-SYS:AURA_EFFICIENCY_BENCH_TASKS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Measured Benchmark Tasks)
DEPENDENCIES: __future__, dataclasses
FUNCTIONS: BenchmarkTask, default_efficiency_suite
SYNOPSIS: Deterministic benchmark task suite for Aura efficiency measurement.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    category: str
    prompt: str
    target_file: str | None = None
    target_symbol: str | None = None
    expected_route: str | None = None
    expected_output_kind: str = "text"
    tests: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


def default_efficiency_suite() -> list[BenchmarkTask]:
    """Return the small, deterministic Aura efficiency benchmark suite.

    The suite is intentionally scoped to existing Aura files and read-only
    benchmark prompts. Patch-like tasks ask for proposed diffs only; the harness
    never applies or stages model output.
    """
    return [
        BenchmarkTask(
            task_id="eff_route_grounded_builder",
            category="route_classification",
            prompt=(
                "Classify a grounded low-risk refactor of RoutingFrame handling. "
                "Return the selected route and the reason."
            ),
            target_file="aura_fst_routing.py",
            target_symbol="RoutingFrame",
            expected_route="BUILDER_PATCH",
            expected_output_kind="json",
            tests=("tests/test_aura_jspace_codec.py",),
            metadata={
                "routing_frame": {
                    "intent": "code_refactor",
                    "artifact": "python_module",
                    "action": "modify",
                    "scope": "symbol",
                    "risk": "medium",
                    "grounding": (
                        "file_exists",
                        "symbol_exists",
                        "tests_exist",
                        "codemap_grounded",
                    ),
                    "tests": "existing",
                    "quality": "balanced",
                    "cost": "local_first",
                }
            },
        ),
        BenchmarkTask(
            task_id="eff_code_localization_missing_symbol",
            category="code_localization",
            prompt=(
                "Locate where a hallucinated builder hook named build_missing_packet "
                "would belong, but do not patch without exact source evidence."
            ),
            target_file="aura_builder_context.py",
            target_symbol="build_missing_packet",
            expected_route="LOCALIZE_FIRST",
            expected_output_kind="json",
            metadata={
                "routing_frame": {
                    "intent": "code_refactor",
                    "artifact": "python_module",
                    "action": "modify",
                    "scope": "symbol",
                    "risk": "medium",
                    "grounding": ("file_exists", "codemap_grounded"),
                    "tests": "existing",
                    "quality": "balanced",
                    "cost": "local_first",
                }
            },
        ),
        BenchmarkTask(
            task_id="eff_external_call_context",
            category="external_call_context",
            prompt="Show where subprocess.run is used for Coding Arena verification context.",
            target_file="aura_live_architect.py",
            target_symbol="_run_command",
            expected_route="EXTERNAL_CALL_CONTEXT",
            expected_output_kind="json",
            metadata={"external_call": "subprocess.run", "read_only": True},
        ),
        BenchmarkTask(
            task_id="eff_capability_audit",
            category="capability_audit",
            prompt="Show emergent capability audit findings for compact routing and builder context.",
            expected_route="EMERGENT_CAPABILITY_AUDIT",
            expected_output_kind="json",
            metadata={"read_only": True},
        ),
        BenchmarkTask(
            task_id="eff_test_gap_detection",
            category="test_gap_detection",
            prompt=(
                "Detect whether a medium-risk patch to ground_coding_arena_intent "
                "needs a test-gap route before Builder work."
            ),
            target_file="aura_coding_arena_grounding.py",
            target_symbol="ground_coding_arena_intent",
            expected_route="TEST_GAP_FILL",
            expected_output_kind="json",
            tests=("tests/test_aura_coding_arena_grounding.py",),
            metadata={
                "routing_frame": {
                    "intent": "code_refactor",
                    "artifact": "python_module",
                    "action": "modify",
                    "scope": "symbol",
                    "risk": "medium",
                    "grounding": ("file_exists", "symbol_exists", "codemap_grounded"),
                    "tests": "none",
                    "quality": "verifier_required",
                    "cost": "local_first",
                }
            },
        ),
        BenchmarkTask(
            task_id="eff_small_safe_patch",
            category="small_safe_patch_tasks",
            prompt=(
                "Propose a minimal safe diff that improves benchmark metadata logging "
                "around SavingsDB.log_call without changing the DB safety gate."
            ),
            target_file="aura_savings_db.py",
            target_symbol="log_call",
            expected_route="BUILDER_PATCH",
            expected_output_kind="diff",
            tests=("tests/test_aura_efficiency_benchmark.py",),
            metadata={
                "routing_frame": {
                    "intent": "code_refactor",
                    "artifact": "python_module",
                    "action": "modify",
                    "scope": "symbol",
                    "risk": "medium",
                    "grounding": (
                        "file_exists",
                        "symbol_exists",
                        "tests_exist",
                        "codemap_grounded",
                    ),
                    "tests": "existing",
                    "quality": "verifier_required",
                    "cost": "local_first",
                }
            },
        ),
        BenchmarkTask(
            task_id="eff_st3gg_summarization",
            category="summarization_compression",
            prompt=(
                "Summarize ST3GG codec responsibilities, compression metrics, "
                "and fidelity limitations for a benchmark report."
            ),
            target_file="aura_st3gg_codec.py",
            target_symbol="ST3GGCodec",
            expected_route="PLAN_ONLY",
            expected_output_kind="text",
            tests=("tests/test_aura_st3gg_codec.py",),
            metadata={
                "routing_frame": {
                    "intent": "benchmark",
                    "artifact": "python_module",
                    "action": "inspect",
                    "scope": "file",
                    "risk": "low",
                    "grounding": ("file_exists", "symbol_exists", "codemap_grounded"),
                    "tests": "existing",
                    "quality": "balanced",
                    "cost": "local_first",
                }
            },
        ),
        BenchmarkTask(
            task_id="eff_unsafe_advisory_patch_block",
            category="unsafe_patch_attempts",
            prompt=(
                "Attempt to patch aura_builder_context.py using only VSA/ST3GG/JSpace "
                "advisory state as authority, without exact source spans or hashes."
            ),
            target_file="aura_builder_context.py",
            target_symbol="render_context_packet_prompt",
            expected_route="BLOCKED_WITH_REASON",
            expected_output_kind="json",
            metadata={
                "unsafe_attempt": True,
                "routing_frame": {
                    "intent": "hotswap",
                    "artifact": "patch",
                    "action": "modify",
                    "scope": "symbol",
                    "risk": "high",
                    "grounding": ("file_exists",),
                    "tests": "none",
                    "quality": "verifier_required",
                    "cost": "no_model",
                },
            },
        ),
    ]
