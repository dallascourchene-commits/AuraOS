from __future__ import annotations

import pytest

from aura_financial_contracts import (
    BalanceRecord,
    ExactMoney,
    FinancialAccount,
    FinancialAccountKind,
    FinancialDirection,
    FinancialLedgerSnapshot,
    FinancialTruthClass,
    TransactionRecord,
)


def _account(*, authority_owner: str = "user://fixture") -> FinancialAccount:
    return FinancialAccount(
        account_id="acct-cash",
        kind=FinancialAccountKind.CASH,
        currency="CAD",
        authority_owner=authority_owner,
        opened_on="2026-01-01",
        closed_on=None,
        source_refs=("evidence://acct-cash",),
        truth_class=FinancialTruthClass.USER_RECORDED,
    )


def _balance() -> BalanceRecord:
    return BalanceRecord(
        balance_id="bal-cash",
        account_id="acct-cash",
        money=ExactMoney("100", "CAD"),
        as_of="2026-07-15",
        source_refs=("evidence://bal-cash",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )


def test_distinct_records_on_one_account_use_their_own_record_ids() -> None:
    transaction = TransactionRecord(
        transaction_id="txn-cash",
        account_id="acct-cash",
        money=ExactMoney("10", "CAD"),
        direction=FinancialDirection.INFLOW,
        effective_on="2026-07-01",
        posted_on="2026-07-02",
        source_refs=("evidence://txn-cash",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )

    snapshot = FinancialLedgerSnapshot(
        snapshot_id="snapshot",
        as_of="2026-07-15",
        authority_owner="user://fixture",
        accounts=(_account(),),
        balances=(_balance(),),
        transactions=(transaction,),
    )

    assert snapshot.balances[0].balance_id == "bal-cash"
    assert snapshot.transactions[0].transaction_id == "txn-cash"
    assert snapshot.digest


def test_transaction_effective_and_posted_dates_both_obey_account_lifecycle() -> None:
    transaction = TransactionRecord(
        transaction_id="txn-before-open",
        account_id="acct-cash",
        money=ExactMoney("10", "CAD"),
        direction=FinancialDirection.INFLOW,
        effective_on="2025-12-31",
        posted_on="2026-01-02",
        source_refs=("evidence://txn-before-open",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )

    with pytest.raises(ValueError, match="precedes account opening"):
        FinancialLedgerSnapshot(
            snapshot_id="snapshot",
            as_of="2026-07-15",
            authority_owner="user://fixture",
            accounts=(_account(),),
            transactions=(transaction,),
        )


def test_snapshot_rejects_mixed_account_authority_owners() -> None:
    with pytest.raises(ValueError, match="authority owner differs"):
        FinancialLedgerSnapshot(
            snapshot_id="snapshot",
            as_of="2026-07-15",
            authority_owner="user://fixture",
            accounts=(_account(authority_owner="model://not-authorized"),),
        )
