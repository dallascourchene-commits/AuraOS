from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from aura_financial_contracts import (
    FINANCIAL_ADVICE_AUTHORITY,
    FINANCIAL_EXECUTION_AUTHORITY,
    AssetValue,
    BalanceRecord,
    CashFlowRecord,
    DebtTerms,
    ExactMoney,
    ExactRate,
    FeeRecord,
    FinancialAccount,
    FinancialAccountKind,
    FinancialDirection,
    FinancialLedgerSnapshot,
    FinancialTruthClass,
    TaxAssumption,
    TransactionRecord,
)


def _account(
    account_id: str,
    kind: FinancialAccountKind,
    currency: str = "CAD",
    *,
    opened_on: str | None = "2025-01-01",
    closed_on: str | None = None,
) -> FinancialAccount:
    return FinancialAccount(
        account_id=account_id,
        kind=kind,
        currency=currency,
        authority_owner="user://fixture",
        opened_on=opened_on,
        closed_on=closed_on,
        source_refs=(f"evidence://{account_id}",),
        truth_class=FinancialTruthClass.USER_RECORDED,
    )


def _cash_account() -> FinancialAccount:
    return _account("acct-cash", FinancialAccountKind.CASH)


def _balance(
    balance_id: str = "bal-cash",
    *,
    account_id: str = "acct-cash",
    amount: str = "1200.00",
    currency: str = "CAD",
    as_of: str = "2026-07-15",
) -> BalanceRecord:
    return BalanceRecord(
        balance_id=balance_id,
        account_id=account_id,
        money=ExactMoney(amount, currency),
        as_of=as_of,
        source_refs=(f"evidence://{balance_id}",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )


def _snapshot(**overrides: object) -> FinancialLedgerSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "snapshot-2026-07-15",
        "as_of": "2026-07-15",
        "authority_owner": "user://fixture",
        "accounts": (
            _account("acct-cash", FinancialAccountKind.CASH, "CAD"),
            _account("acct-debt", FinancialAccountKind.LIABILITY, "CAD"),
            _account("acct-invest", FinancialAccountKind.INVESTMENT, "USD"),
        ),
        "balances": (
            _balance(),
            _balance(
                "bal-debt",
                account_id="acct-debt",
                amount="-4000.00",
            ),
            _balance(
                "bal-invest",
                account_id="acct-invest",
                amount="2500.50",
                currency="USD",
            ),
        ),
        "transactions": (
            TransactionRecord(
                transaction_id="txn-pay",
                account_id="acct-cash",
                money=ExactMoney("100.25", "CAD"),
                direction=FinancialDirection.INFLOW,
                effective_on="2026-07-01",
                posted_on="2026-07-02",
                source_refs=("evidence://txn-pay",),
                truth_class=FinancialTruthClass.IMPORTED_EXACT,
            ),
        ),
        "cash_flows": (
            CashFlowRecord(
                flow_id="flow-rent",
                account_id="acct-cash",
                money=ExactMoney("800", "CAD"),
                direction=FinancialDirection.OUTFLOW,
                effective_on="2026-07-05",
                source_refs=("evidence://flow-rent",),
                truth_class=FinancialTruthClass.USER_RECORDED,
            ),
        ),
        "debts": (
            DebtTerms(
                debt_id="debt-loan",
                account_id="acct-debt",
                principal=ExactMoney("4000", "CAD"),
                annual_rate=ExactRate("0.0490"),
                effective_on="2026-01-01",
                maturity_on="2028-01-01",
                payment=ExactMoney("175", "CAD"),
                source_refs=("evidence://debt-loan",),
                truth_class=FinancialTruthClass.IMPORTED_EXACT,
            ),
        ),
        "asset_values": (
            AssetValue(
                valuation_id="value-invest",
                account_id="acct-invest",
                money=ExactMoney("2500.50", "USD"),
                as_of="2026-07-15",
                source_refs=("evidence://value-invest",),
                truth_class=FinancialTruthClass.IMPORTED_EXACT,
            ),
        ),
        "fees": (
            FeeRecord(
                fee_id="fee-monthly",
                account_id="acct-cash",
                money=ExactMoney("4.95", "CAD"),
                effective_on="2026-07-10",
                source_refs=("evidence://fee-monthly",),
                truth_class=FinancialTruthClass.IMPORTED_EXACT,
            ),
        ),
        "tax_assumptions": (
            TaxAssumption(
                assumption_id="tax-estimate",
                jurisdiction_ref="jurisdiction://ca-mb",
                effective_on="2026-07-15",
                rate=ExactRate("0.20"),
                amount=None,
                source_refs=("assumption://tax-estimate",),
            ),
        ),
    }
    values.update(overrides)
    return FinancialLedgerSnapshot(**values)  # type: ignore[arg-type]


def test_exact_money_and_rate_normalize_without_binary_float() -> None:
    assert ExactMoney("001200.5000", "CAD").to_dict() == {
        "amount": "1200.5",
        "currency": "CAD",
    }
    assert ExactMoney(0, "USD").amount == "0"
    assert ExactMoney(Decimal("-0.00"), "CAD").amount == "0"
    assert ExactRate("0.0490").value == "0.049"

    with pytest.raises(ValueError, match="binary floating-point"):
        ExactMoney(0.1, "CAD")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="binary floating-point"):
        ExactRate(0.05)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        ExactMoney("NaN", "CAD")
    with pytest.raises(ValueError, match="finite"):
        ExactMoney("Infinity", "CAD")
    with pytest.raises(ValueError, match="non-negative"):
        ExactRate("-0.01")


def test_currency_dates_sources_and_truth_classes_fail_closed() -> None:
    with pytest.raises(ValueError, match="three-letter uppercase"):
        ExactMoney("1", "cad")
    with pytest.raises(ValueError, match="calendar date"):
        _account("acct", FinancialAccountKind.CASH, opened_on="2026-02-30")
    with pytest.raises(ValueError, match="cannot precede"):
        _account(
            "acct",
            FinancialAccountKind.CASH,
            opened_on="2026-01-02",
            closed_on="2026-01-01",
        )
    with pytest.raises(ValueError, match="must not contain duplicates"):
        FinancialAccount(
            account_id="acct",
            kind=FinancialAccountKind.CASH,
            currency="CAD",
            authority_owner="user://fixture",
            opened_on=None,
            closed_on=None,
            source_refs=("evidence://one", "evidence://one"),
            truth_class=FinancialTruthClass.USER_RECORDED,
        )
    with pytest.raises(ValueError, match="user-recorded or exactly imported"):
        FinancialAccount(
            account_id="acct",
            kind=FinancialAccountKind.CASH,
            currency="CAD",
            authority_owner="user://fixture",
            opened_on=None,
            closed_on=None,
            source_refs=("evidence://acct",),
            truth_class=FinancialTruthClass.DERIVED_ARITHMETIC,
        )


def test_transaction_and_debt_local_invariants() -> None:
    with pytest.raises(ValueError, match="positive ExactMoney"):
        TransactionRecord(
            transaction_id="txn-zero",
            account_id="acct-cash",
            money=ExactMoney("0", "CAD"),
            direction=FinancialDirection.OUTFLOW,
            effective_on="2026-01-01",
            posted_on=None,
            source_refs=("evidence://txn-zero",),
            truth_class=FinancialTruthClass.USER_RECORDED,
        )
    with pytest.raises(ValueError, match="posted_on cannot precede"):
        TransactionRecord(
            transaction_id="txn-time",
            account_id="acct-cash",
            money=ExactMoney("1", "CAD"),
            direction=FinancialDirection.OUTFLOW,
            effective_on="2026-01-02",
            posted_on="2026-01-01",
            source_refs=("evidence://txn-time",),
            truth_class=FinancialTruthClass.IMPORTED_EXACT,
        )
    with pytest.raises(ValueError, match="currencies must match"):
        DebtTerms(
            debt_id="debt-mixed",
            account_id="acct-debt",
            principal=ExactMoney("100", "CAD"),
            annual_rate=ExactRate("0.05"),
            effective_on="2026-01-01",
            maturity_on=None,
            payment=ExactMoney("10", "USD"),
            source_refs=("evidence://debt-mixed",),
            truth_class=FinancialTruthClass.IMPORTED_EXACT,
        )


def test_tax_assumption_is_explicit_and_never_exact_ledger_truth() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        TaxAssumption(
            assumption_id="tax-none",
            jurisdiction_ref="jurisdiction://ca-mb",
            effective_on="2026-01-01",
            rate=None,
            amount=None,
            source_refs=("assumption://tax-none",),
        )
    with pytest.raises(ValueError, match="exactly one"):
        TaxAssumption(
            assumption_id="tax-both",
            jurisdiction_ref="jurisdiction://ca-mb",
            effective_on="2026-01-01",
            rate=ExactRate("0.2"),
            amount=ExactMoney("100", "CAD"),
            source_refs=("assumption://tax-both",),
        )
    with pytest.raises(ValueError, match="must be ASSUMPTION"):
        TaxAssumption(
            assumption_id="tax-false-exact",
            jurisdiction_ref="jurisdiction://ca-mb",
            effective_on="2026-01-01",
            rate=ExactRate("0.2"),
            amount=None,
            source_refs=("assumption://tax-false-exact",),
            truth_class=FinancialTruthClass.IMPORTED_EXACT,
        )


def test_comprehensive_snapshot_is_deterministic_and_non_authorizing() -> None:
    first = _snapshot()
    second = _snapshot()

    assert first == second
    assert first.digest == second.digest
    assert len(first.digest) == 64
    assert first.to_dict()["proposal_only"] is True
    assert first.to_dict()["execution_authority"] is FINANCIAL_EXECUTION_AUTHORITY is False
    assert first.to_dict()["advice_authority"] is FINANCIAL_ADVICE_AUTHORITY is False

    changed_balances = (
        replace(first.balances[0], money=ExactMoney("1200.01", "CAD")),
        *first.balances[1:],
    )
    changed = replace(first, balances=changed_balances)
    assert changed.digest != first.digest


def test_snapshot_requires_unique_sorted_accounts_and_global_record_ids() -> None:
    with pytest.raises(ValueError, match="unique and sorted"):
        _snapshot(accounts=tuple(reversed(_snapshot().accounts)))

    duplicate_id = TransactionRecord(
        transaction_id="bal-cash",
        account_id="acct-cash",
        money=ExactMoney("1", "CAD"),
        direction=FinancialDirection.OUTFLOW,
        effective_on="2026-07-01",
        posted_on=None,
        source_refs=("evidence://duplicate",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )
    with pytest.raises(ValueError, match="globally unique"):
        _snapshot(transactions=(duplicate_id,))


def test_snapshot_rejects_unknown_accounts_mixed_currency_and_future_records() -> None:
    with pytest.raises(ValueError, match="unknown account"):
        _snapshot(balances=(_balance(account_id="acct-missing"),))

    with pytest.raises(ValueError, match="currency does not match"):
        _snapshot(balances=(_balance(currency="USD"),))

    future = TransactionRecord(
        transaction_id="txn-future",
        account_id="acct-cash",
        money=ExactMoney("1", "CAD"),
        direction=FinancialDirection.OUTFLOW,
        effective_on="2026-07-16",
        posted_on=None,
        source_refs=("evidence://txn-future",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )
    with pytest.raises(ValueError, match="after snapshot.as_of"):
        _snapshot(transactions=(future,))


def test_snapshot_rejects_duplicate_and_contradictory_balances() -> None:
    duplicate = _balance("bal-second", amount="1200")
    with pytest.raises(ValueError, match="duplicate balances"):
        _snapshot(balances=(_balance(), duplicate))

    contradictory = _balance("bal-second", amount="1199.99")
    with pytest.raises(ValueError, match="contradictory balances"):
        _snapshot(balances=(_balance(), contradictory))


def test_snapshot_enforces_account_lifecycle_and_domain_roles() -> None:
    opened_late = _account(
        "acct-cash",
        FinancialAccountKind.CASH,
        opened_on="2026-07-10",
    )
    with pytest.raises(ValueError, match="precedes account opening"):
        _snapshot(
            accounts=(
                opened_late,
                _account("acct-debt", FinancialAccountKind.LIABILITY),
                _account("acct-invest", FinancialAccountKind.INVESTMENT, "USD"),
            ),
            balances=(_balance(as_of="2026-07-09"),),
            transactions=(),
            cash_flows=(),
            debts=(),
            asset_values=(),
            fees=(),
            tax_assumptions=(),
        )

    wrong_debt_account = DebtTerms(
        debt_id="debt-wrong-kind",
        account_id="acct-cash",
        principal=ExactMoney("100", "CAD"),
        annual_rate=ExactRate("0.05"),
        effective_on="2026-01-01",
        maturity_on=None,
        payment=None,
        source_refs=("evidence://debt-wrong-kind",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )
    with pytest.raises(ValueError, match="LIABILITY"):
        _snapshot(debts=(wrong_debt_account,))

    wrong_asset_account = AssetValue(
        valuation_id="value-wrong-kind",
        account_id="acct-cash",
        money=ExactMoney("100", "CAD"),
        as_of="2026-07-15",
        source_refs=("evidence://value-wrong-kind",),
        truth_class=FinancialTruthClass.IMPORTED_EXACT,
    )
    with pytest.raises(ValueError, match="ASSET or INVESTMENT"):
        _snapshot(asset_values=(wrong_asset_account,))


def test_snapshot_cannot_be_forged_into_advice_or_execution_authority() -> None:
    with pytest.raises(ValueError, match="cannot grant execution or advice authority"):
        _snapshot(execution_authority=True)
    with pytest.raises(ValueError, match="cannot grant execution or advice authority"):
        _snapshot(advice_authority=True)
    with pytest.raises(ValueError, match="cannot grant execution or advice authority"):
        _snapshot(proposal_only=False)
    with pytest.raises(ValueError, match="ownership boundary changed"):
        _snapshot(ownership_disposition="MODEL_OWNS_LEDGER")
    with pytest.raises(ValueError, match="patch authority changed"):
        _snapshot(patch_authority="MODEL_OUTPUT")
