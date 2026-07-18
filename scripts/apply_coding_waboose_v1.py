from __future__ import annotations

from pathlib import Path


def rewrite_required(path: str, transforms: list[tuple[str, str]]) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    for old, new in transforms:
        if old not in text:
            raise SystemExit(
                f"missing Coding Waboose integration fragment in {path}: {old[:120]!r}"
            )
        text = text.replace(old, new)
    target.write_text(text, encoding="utf-8")


def rewrite_optional(path: str, transforms: list[tuple[str, str]]) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    for old, new in transforms:
        text = text.replace(old, new)
    target.write_text(text, encoding="utf-8")


def patch_persistence_bridge() -> None:
    rewrite_required(
        "aura_agent_arena_persistence_bridge.py",
        [
            (
                "from aura_review_arena import AuraReviewArena",
                "from aura_coding_waboose import CodingWaboose",
            ),
            (
                "self.review_arena = AuraReviewArena(self.repo_root)",
                "self.coding_waboose = CodingWaboose(self.repo_root)",
            ),
            ("aura_review_prepare", "aura_waboose_prepare"),
            ("aura_review_scan", "aura_waboose_scan"),
            ("aura_review_agent_packet", "aura_waboose_agent_packet"),
            ("aura_review_submit_findings", "aura_waboose_submit_findings"),
            ("aura_review_finalize", "aura_waboose_finalize"),
            ("aura_review_status", "aura_waboose_status"),
            ("self.review_arena.", "self.coding_waboose."),
        ],
    )
    rewrite_optional(
        "aura_agent_arena_persistence_bridge.py",
        [
            ("graph-guided code-review contract", "Coding Waboose diagnostic contract"),
            ("prepared review", "prepared Coding Waboose run"),
            ("coding agent", "coding agent through Coding Waboose"),
        ],
    )


def patch_mcp() -> None:
    rewrite_required(
        "aura_agent_arena_mcp.py",
        [
            ("aura_review_prepare", "aura_waboose_prepare"),
            ("aura_review_scan", "aura_waboose_scan"),
            ("aura_review_agent_packet", "aura_waboose_agent_packet"),
            ("aura_review_submit_findings", "aura_waboose_submit_findings"),
            ("aura_review_finalize", "aura_waboose_finalize"),
            ("aura_review_status", "aura_waboose_status"),
            ("_handle_review_prepare", "_handle_waboose_prepare"),
            ("_handle_review_scan", "_handle_waboose_scan"),
            ("_handle_review_agent_packet", "_handle_waboose_agent_packet"),
            ("_handle_review_submit_findings", "_handle_waboose_submit_findings"),
            ("_handle_review_finalize", "_handle_waboose_finalize"),
            ("_handle_review_status", "_handle_waboose_status"),
        ],
    )
    rewrite_optional(
        "aura_agent_arena_mcp.py",
        [
            (
                "Compile an evidence-bound review contract from a Git range, workspace, or explicit files.",
                "Compile a Coding Waboose evidence contract and diagnostic breadboard from a Git range, workspace, or explicit files.",
            ),
            (
                "Run local deterministic scans and dependency-impact checks for a prepared review.",
                "Run Coding Waboose deterministic scans and energize the applicable diagnostic breadboard components.",
            ),
            (
                "Return the bounded focus, topology, evidence, and optional exact-source packet for a coding agent.",
                "Return Coding Waboose focus, diagnostic breadboard, topology, evidence, and optional exact-source slices for a coding agent.",
            ),
            (
                "Submit structured coding-agent findings for exact-source corroboration; agent confirmation claims are ignored.",
                "Submit Coding Waboose findings for exact-source corroboration; agent confirmation claims are ignored.",
            ),
            (
                "Deduplicate and rank findings, then compile review-only Forge repair requests.",
                "Deduplicate and rank Coding Waboose findings, then compile review-only Forge repair requests.",
            ),
            (
                "Return the bounded status and finding counts for an in-process review.",
                "Return Coding Waboose status, breadboard continuity, and finding counts.",
            ),
        ],
    )


def patch_mcp_tests() -> None:
    rewrite_required(
        "tests/test_aura_review_arena_mcp.py",
        [
            ("FakeReviewBridge", "FakeWabooseBridge"),
            ("aura_review_prepare", "aura_waboose_prepare"),
            ("aura_review_scan", "aura_waboose_scan"),
            ("aura_review_agent_packet", "aura_waboose_agent_packet"),
            ("aura_review_submit_findings", "aura_waboose_submit_findings"),
            ("aura_review_finalize", "aura_waboose_finalize"),
            ("aura_review_status", "aura_waboose_status"),
            ("review_tools_are_advertised", "waboose_tools_are_advertised"),
            ("review_prepare_dispatches_complete_request", "waboose_prepare_dispatches_complete_request"),
            ("review_lifecycle_tools_dispatch", "waboose_lifecycle_tools_dispatch"),
            (
                "plain_ok_false_review_result_sets_mcp_is_error",
                "plain_ok_false_waboose_result_sets_mcp_is_error",
            ),
        ],
    )


def patch_docs() -> None:
    for path in ("README.md", "USER_GUIDE.md", ".aura/ARCHITECTURE.md"):
        rewrite_optional(
            path,
            [
                ("Aura Review Arena", "Coding Waboose"),
                ("AURA_REVIEW_ARENA_V1", "AURA_CODING_WABOOSE_V1"),
                ("docs/AURA_REVIEW_ARENA.md", "docs/AURA_CODING_WABOOSE.md"),
                ("aura_review_arena_cli.py", "aura_coding_waboose_cli.py"),
                ("aura_review_contract.schema.json", "aura_coding_waboose_contract.schema.json"),
                ("aura_review_prepare", "aura_waboose_prepare"),
                ("aura_review_scan", "aura_waboose_scan"),
                ("aura_review_agent_packet", "aura_waboose_agent_packet"),
                ("aura_review_submit_findings", "aura_waboose_submit_findings"),
                ("aura_review_finalize", "aura_waboose_finalize"),
                ("aura_review_status", "aura_waboose_status"),
                ("Review Arena", "Coding Waboose"),
                (
                    "  → run-specific focus directives\n  → bounded coding-agent investigation",
                    "  → run-specific focus directives\n  → diagnostic Coding Breadboard\n  → bounded coding-agent investigation",
                ),
                (
                    "Use Coding Waboose when the question is not only \"does it compile?\" but also",
                    "Use Coding Waboose when the question is not only \"does it compile?\" but also\n\"which typed diagnostic circuit should be energized, and what exact forward and backward\nproof path does it require?\" Coding Waboose uses the Planning Board/Coding Breadboard when",
                ),
                (
                    "- `aura_review_arena.py`;\n- `aura_coding_waboose_cli.py`;\n- `schemas/aura_coding_waboose_contract.schema.json`;\n- Coding Waboose tools on `aura_agent_arena_persistence_bridge.py` and `aura_agent_arena_mcp.py`;\n- `docs/AURA_CODING_WABOOSE.md`.",
                    "- `aura_coding_waboose.py` — public Coding Waboose owner;\n- `aura_coding_waboose_breadboard.py` — proposal-only diagnostic circuit compiler;\n- `aura_review_arena.py` — internal reusable scan/corroboration engine;\n- `aura_coding_waboose_cli.py`;\n- `schemas/aura_coding_waboose_contract.schema.json` and the internal `schemas/aura_review_contract.schema.json`;\n- Coding Waboose tools on `aura_agent_arena_persistence_bridge.py` and `aura_agent_arena_mcp.py`;\n- `docs/AURA_CODING_WABOOSE.md`.",
                ),
            ],
        )


def patch_cli() -> None:
    rewrite_required(
        "aura_review_arena_cli.py",
        [
            (
                '"""Command-line interface for Aura Review Arena V1."""',
                '"""Command-line interface for Coding Waboose V1."""',
            ),
            (
                "from aura_review_arena import AuraReviewArena",
                "from aura_coding_waboose import CodingWaboose",
            ),
            (
                "Run Aura's graph-guided, evidence-bound code review Arena.",
                "Run Coding Waboose, Aura's graph-guided diagnostic code-review organ.",
            ),
            ("arena = AuraReviewArena(args.repo_root)", "arena = CodingWaboose(args.repo_root)"),
            ('"version": "AURA_REVIEW_ARENA_V1"', '"version": "AURA_CODING_WABOOSE_V1"'),
        ],
    )
    source = Path("aura_review_arena_cli.py")
    target = Path("aura_coding_waboose_cli.py")
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    source.unlink()


def main() -> None:
    patch_persistence_bridge()
    patch_mcp()
    patch_mcp_tests()
    patch_docs()
    patch_cli()


if __name__ == "__main__":
    main()
