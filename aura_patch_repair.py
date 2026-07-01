"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b4-[Q-SYS:PATCH_REPAIR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Bounded Self-Repair)
DEPENDENCIES: __future__, dataclasses, json, typing, aura_builder_context, aura_patch_quality_gate
FUNCTIONS: PatchRepairResult, repair_patch_format, _build_repair_prompt
SYNOPSIS: Bounded one-shot patch format repair. When preflight rejects a corrupt patch, this module constructs a repair prompt using the stderr and source context, calls the model exactly once, and returns the repaired diff. If repair fails, the caller escalates or blocks — never hot-swaps.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import json
from typing import Any

from aura_builder_context import BuilderContextPacket
from aura_patch_quality_gate import (
    BeforeAfterReplacement,
    generate_unified_diff_from_before_after,
    parse_before_after_response,
    preflight_patch,
)

ModelCaller = Callable[[str, str, dict[str, Any]], Any]


@dataclass
class PatchRepairResult:
    """Result of a bounded one-shot patch format repair attempt."""
    ok: bool
    repaired_diff: str = ""
    repair_prompt: str = ""
    attempt_number: int = 1  # Always 1 — we only try once
    stderr_used: str = ""
    rejections_after_repair: list[str] = field(default_factory=list)
    original_rejections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _build_repair_prompt(
    original_diff: str,
    stderr: str,
    context_packet: BuilderContextPacket | None,
    rejections: list[str],
) -> str:
    """Construct a repair prompt using the stderr and source context.

    Research basis: Self-Refine's single-iteration repair; Reflexion's
    stderr-grounded feedback; SWE-agent's format repair loop (bounded to 1).
    """
    lines: list[str] = [
        "You are an Aura patch format repair agent. A previous patch was rejected by the preflight quality gate.",
        "Fix the patch format so it passes validation. Return ONLY the corrected unified diff or a before/after JSON object.",
        "",
        "=== REJECTION REASONS ===",
    ]
    for rejection in rejections:
        lines.append(f"  - {rejection}")
    lines.append("")

    if stderr:
        lines.append("=== GIT APPLY STDERR ===")
        lines.append(stderr[:2000])
        lines.append("")

    lines.append("=== ORIGINAL (REJECTED) PATCH ===")
    lines.append(original_diff[:4000])
    lines.append("=== END ORIGINAL PATCH ===")
    lines.append("")

    if context_packet:
        lines.append(context_packet.to_prompt_section())
        lines.append("")

    lines.append("=== REPAIR INSTRUCTIONS ===")
    lines.append("1. Fix all malformed @@ hunk headers to match the format: @@ -start,count +start,count @@")
    lines.append("2. Ensure file headers (--- /+++ ) are present and correct.")
    lines.append("3. Ensure the diff applies cleanly to the source excerpt shown above.")
    lines.append("4. Do NOT include prose, explanations, or commentary.")
    lines.append("5. Return EITHER a valid unified diff OR a JSON object: {\"before_text\": \"...\", \"after_text\": \"...\"}")
    lines.append("=== END REPAIR INSTRUCTIONS ===")

    return "\n".join(lines)


async def repair_patch_format(
    original_diff: str,
    stderr: str,
    context_packet: BuilderContextPacket | None,
    model_caller: ModelCaller | None,
    *,
    role: str = "worker",
    repo_root: str = ".",
    rejections: list[str] | None = None,
    intensity: int = 0,
) -> PatchRepairResult:
    """Run exactly one PATCH_FORMAT_REPAIR attempt.

    Constructs a repair prompt using the stderr and source context, calls the
    model exactly once, validates the repaired diff with preflight, and returns
    the result. If the model caller is None or the repair fails preflight,
    returns ok=False — the caller must escalate or block, never hot-swap.

    Research basis: Self-Refine (bounded to 1 iteration); Reflexion (stderr-grounded
    feedback); SWE-agent (format repair with bounded retries).
    """
    original_rejections = list(rejections or [])

    if model_caller is None:
        return PatchRepairResult(
            ok=False,
            repaired_diff="",
            repair_prompt="",
            stderr_used=stderr,
            original_rejections=original_rejections,
            rejections_after_repair=["no_model_caller"],
        )

    repair_prompt = _build_repair_prompt(original_diff, stderr, context_packet, original_rejections)

    try:
        result = model_caller(role, repair_prompt, {"repair_phase": "PATCH_FORMAT_REPAIR", "attempt": 1})
        # Handle awaitable results
        import inspect
        if inspect.isawaitable(result):
            result = await result
    except Exception as exc:
        return PatchRepairResult(
            ok=False,
            repaired_diff="",
            repair_prompt=repair_prompt,
            stderr_used=stderr,
            original_rejections=original_rejections,
            rejections_after_repair=[f"model_call_error: {exc}"],
        )

    response_text = str(result) if result is not None else ""
    if not response_text.strip():
        return PatchRepairResult(
            ok=False,
            repaired_diff="",
            repair_prompt=repair_prompt,
            stderr_used=stderr,
            original_rejections=original_rejections,
            rejections_after_repair=["empty_repair_response"],
        )

    # Try to parse as before/after first
    before_after = parse_before_after_response(response_text)
    if before_after is not None:
        repaired_diff = generate_unified_diff_from_before_after(before_after, repo_root=repo_root)
        if not repaired_diff.strip():
            return PatchRepairResult(
                ok=False,
                repaired_diff="",
                repair_prompt=repair_prompt,
                stderr_used=stderr,
                original_rejections=original_rejections,
                rejections_after_repair=["before_after_diff_generation_failed"],
            )
    else:
        # Treat as a unified diff directly
        # Strip code fences if present
        import re
        fenced = re.search(r"```(?:diff|patch)?\s*(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
        if fenced:
            repaired_diff = fenced.group(1).strip()
        else:
            # Find the start of the diff
            marker_positions = [
                pos for pos in (
                    response_text.find("diff --git "),
                    response_text.find("--- "),
                    response_text.find("@@ "),
                )
                if pos >= 0
            ]
            if marker_positions:
                repaired_diff = response_text[min(marker_positions):].strip()
            else:
                repaired_diff = response_text.strip()

    # Validate the repaired diff with preflight
    preflight = preflight_patch(repaired_diff, repo_root=repo_root, run_git_check=True)

    return PatchRepairResult(
        ok=preflight.ok,
        repaired_diff=repaired_diff if preflight.ok else "",
        repair_prompt=repair_prompt,
        stderr_used=stderr,
        original_rejections=original_rejections,
        rejections_after_repair=preflight.rejections if not preflight.ok else [],
    )