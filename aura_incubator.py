"""
Legacy Aura incubator quarantine.

Live Architect mode no longer writes model output directly into this module.
Generated refactor work is staged through Aura_Staging/architect_live_transaction.json,
then promoted only after Refactor Arena, temporary workspace, verifier, hot-swap,
rollback, and ledger gates agree.
"""

INCUBATOR_STATUS = "legacy_quarantine"


def incubator_status() -> dict[str, str]:
    """Return the current legacy-incubator status for older Aura commands."""
    return {
        "status": INCUBATOR_STATUS,
        "live_architect_stage": "Aura_Staging/architect_live_transaction.json",
        "policy": "do_not_write_model_output_directly_here",
    }
