"""Immutable F1 exact-state contracts for Aura Financial Arena.

This module records user-supplied or exactly imported financial facts. It does
not provide financial advice, predictions, external account access, execution,
or authority to mutate any account or ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Any

from aura_event_contracts import stable_digest

FINANCIAL_EXACT_STATE_VERSION = "AURA_FINANCIAL_EXACT_STATE_F1_V1"
FINANCIAL_OWNERSHIP_DISPOSITION = "LOCAL_USER_LEDGER_RETAINS_OWNERSHIP"
FINANCIAL_PATCH_AUTHORITY = "EXACT_USER_OR_IMPORTED_RECORDS_ONLY"
FINANCIAL_EXECUTION_AUTHORITY = False
FINANCIAL_ADVICE_AUTHORITY = False

_CURRENCY = re.compile(r"^[A-Z]{3}$")
_MAX_DECIMAL_DIGITS = 38
_MIN_DECIMAL_EXPONENT = -18
_MAX_DECIMAL_EXPONENT = 18


class FinancialTruthClass(str, Enum):
    USER_RECORDED = "USER_RECORDED"
    IMPORTED_EXACT = "IMPORTED_EXACT"
    DERIVED_ARITHMETIC = "DERIVED_ARITHMETIC"
    ASSUMPTION = "ASSUMPTION"
    UNAVAILABLE = "UNAVAILABLE"


class FinancialAccountKind(str, Enum):
    CASH = "CASH"
    ASSET = "ASSET"
    INVESTMENT = "INVESTMENT"
    LIABILITY = "LIABILITY"
    INCOME_SOURCE = "INCOME_SOURCE"
    EXPENSE_BUCKET = "EXPENSE_BUCKET"


class FinancialDirection(str, Enum):
    INFLOW = "INFLOW"
    OUTFLOW = "OUTFLOW"


class FinancialRateBasis(str, Enum):
    FRACTION_PER_YEAR = "FRACTION_PER_YEAR"


_EXACT_TRUTH_CLASSES = frozenset(
    {FinancialTruthClass.USER_RECORDED, FinancialTruthClass.IMPORTED_EXACT}
)


def _text(value: Any, name: str, *, optional: bool = False, maximum: int = 240) -> str | None:
    if value is None and optional:
        return None
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    result = value.strip()
    if len(result) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    return result


def _strings(value: Any, name: str, *, required: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    result = tuple(_text(item, f"{name}[]") for item in value)
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result  # type: ignore[return-value]


def _enum(value: Any, enum_type: type[Enum], name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is unsupported") from exc


def _iso_date(value: Any, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    result = _text(value, name, maximum=10)
    assert isinstance(result, str)
    try:
        parsed = date.fromisoformat(result)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 calendar date") from exc
    if parsed.isoformat() != result:
        raise ValueError(f"{name} must be a normalized ISO-8601 calendar date")
    return result


def _currency(value: Any, name: str = "currency") -> str:
    result = _text(value, name, maximum=3)
    assert isinstance(result, str)
    if not _CURRENCY.fullmatch(result):
        raise ValueError(f"{name} must be a three-letter uppercase currency code")
    return result


def _decimal(value: Any, name: str, *, non_negative: bool = False, positive: bool = False) -> str:
    if type(value) is bool or isinstance(value, float):
        raise ValueError(f"{name} must not use binary floating-point")
    if not isinstance(value, (str, int, Decimal)):
        raise ValueError(f"{name} must be supplied as str, int, or Decimal")
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            raise ValueError(f"{name} must not be empty")
    else:
        candidate = value
    try:
        parsed = Decimal(candidate)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be an exact decimal") from exc
    if not parsed.is_finite():
        raise ValueError(f"{name} must be finite")
    sign, digits, exponent = parsed.as_tuple()
    if len(digits) > _MAX_DECIMAL_DIGITS:
        raise ValueError(f"{name} exceeds {_MAX_DECIMAL_DIGITS} significant digits")
    if exponent < _MIN_DECIMAL_EXPONENT or exponent > _MAX_DECIMAL_EXPONENT:
        raise ValueError(f"{name} exponent is outside the supported exact range")
    if non_negative and parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    if positive and parsed <= 0:
        raise ValueError(f"{name} must be positive")
    if not parsed:
        return "0"
    normalized = format(parsed, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if sign and normalized == "0":
        return "0"
    return normalized


def _date_value(value: str) -> date:
    return date.fromisoformat(value)


def _exact_truth(value: Any, name: str) -> FinancialTruthClass:
    result = _enum(value, FinancialTruthClass, name)
    assert isinstance(result, FinancialTruthClass)
    if result not in _EXACT_TRUTH_CLASSES:
        raise ValueError(f"{name} must identify user-recorded or exactly imported evidence")
    return result


@dataclass(frozen=True)
class ExactMoney:
    amount: str
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _decimal(self.amount, "money.amount"))
        object.__setattr__(self, "currency", _currency(self.currency, "money.currency"))

    @property
    def decimal(self) -> Decimal:
        return Decimal(self.amount)

    def to_dict(self) -> dict[str, str]:
        return {"amount": self.amount, "currency": self.currency}


@dataclass(frozen=True)
class ExactRate:
    value: str
    basis: FinancialRateBasis = FinancialRateBasis.FRACTION_PER_YEAR

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _decimal(self.value, "rate.value", non_negative=True))
        object.__setattr__(self, "basis", _enum(self.basis, FinancialRateBasis, "rate.basis"))

    @property
    def decimal(self) -> Decimal:
        return Decimal(self.value)

    def to_dict(self) -> dict[str, str]:
        return {"value": self.value, "basis": self.basis.value}


@dataclass(frozen=True)
class FinancialAccount:
    account_id: str
    kind: FinancialAccountKind
    currency: str
    authority_owner: str
    opened_on: str | None
    closed_on: str | None
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", _text(self.account_id, "account.account_id"))
        object.__setattr__(self, "kind", _enum(self.kind, FinancialAccountKind, "account.kind"))
        object.__setattr__(self, "currency", _currency(self.currency, "account.currency"))
        object.__setattr__(self, "authority_owner", _text(self.authority_owner, "account.authority_owner"))
        object.__setattr__(self, "opened_on", _iso_date(self.opened_on, "account.opened_on", optional=True))
        object.__setattr__(self, "closed_on", _iso_date(self.closed_on, "account.closed_on", optional=True))
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "account.source_refs"))
        object.__setattr__(self, "truth_class", _exact_truth(self.truth_class, "account.truth_class"))
        if self.opened_on and self.closed_on and _date_value(self.closed_on) < _date_value(self.opened_on):
            raise ValueError("account.closed_on cannot precede account.opened_on")

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "kind": self.kind.value,
            "currency": self.currency,
            "authority_owner": self.authority_owner,
            "opened_on": self.opened_on,
            "closed_on": self.closed_on,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class BalanceRecord:
    balance_id: str
    account_id: str
    money: ExactMoney
    as_of: str
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "balance_id", _text(self.balance_id, "balance.balance_id"))
        object.__setattr__(self, "account_id", _text(self.account_id, "balance.account_id"))
        if not isinstance(self.money, ExactMoney):
            raise ValueError("balance.money must be ExactMoney")
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "balance.as_of"))
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "balance.source_refs"))
        object.__setattr__(self, "truth_class", _exact_truth(self.truth_class, "balance.truth_class"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "balance_id": self.balance_id,
            "account_id": self.account_id,
            "money": self.money.to_dict(),
            "as_of": self.as_of,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class TransactionRecord:
    transaction_id: str
    account_id: str
    money: ExactMoney
    direction: FinancialDirection
    effective_on: str
    posted_on: str | None
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "transaction_id", _text(self.transaction_id, "transaction.transaction_id"))
        object.__setattr__(self, "account_id", _text(self.account_id, "transaction.account_id"))
        if not isinstance(self.money, ExactMoney) or self.money.decimal <= 0:
            raise ValueError("transaction.money must be positive ExactMoney")
        object.__setattr__(self, "direction", _enum(self.direction, FinancialDirection, "transaction.direction"))
        object.__setattr__(self, "effective_on", _iso_date(self.effective_on, "transaction.effective_on"))
        object.__setattr__(self, "posted_on", _iso_date(self.posted_on, "transaction.posted_on", optional=True))
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "transaction.source_refs"))
        object.__setattr__(self, "truth_class", _exact_truth(self.truth_class, "transaction.truth_class"))
        if self.posted_on and _date_value(self.posted_on) < _date_value(self.effective_on):
            raise ValueError("transaction.posted_on cannot precede transaction.effective_on")

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "money": self.money.to_dict(),
            "direction": self.direction.value,
            "effective_on": self.effective_on,
            "posted_on": self.posted_on,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class CashFlowRecord:
    flow_id: str
    account_id: str
    money: ExactMoney
    direction: FinancialDirection
    effective_on: str
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "flow_id", _text(self.flow_id, "cash_flow.flow_id"))
        object.__setattr__(self, "account_id", _text(self.account_id, "cash_flow.account_id"))
        if not isinstance(self.money, ExactMoney) or self.money.decimal <= 0:
            raise ValueError("cash_flow.money must be positive ExactMoney")
        object.__setattr__(self, "direction", _enum(self.direction, FinancialDirection, "cash_flow.direction"))
        object.__setattr__(self, "effective_on", _iso_date(self.effective_on, "cash_flow.effective_on"))
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "cash_flow.source_refs"))
        object.__setattr__(self, "truth_class", _exact_truth(self.truth_class, "cash_flow.truth_class"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "account_id": self.account_id,
            "money": self.money.to_dict(),
            "direction": self.direction.value,
            "effective_on": self.effective_on,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class DebtTerms:
    debt_id: str
    account_id: str
    principal: ExactMoney
    annual_rate: ExactRate
    effective_on: str
    maturity_on: str | None
    payment: ExactMoney | None
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "debt_id", _text(self.debt_id, "debt.debt_id"))
        object.__setattr__(self, "account_id", _text(self.account_id, "debt.account_id"))
        if not isinstance(self.principal, ExactMoney) or self.principal.decimal < 0:
            raise ValueError("debt.principal must be non-negative ExactMoney")
        if not isinstance(self.annual_rate, ExactRate):
            raise ValueError("debt.annual_rate must be ExactRate")
        object.__setattr__(self, "effective_on", _iso_date(self.effective_on, "debt.effective_on"))
        object.__setattr__(self, "maturity_on", _iso_date(self.maturity_on, "debt.maturity_on", optional=True))
        if self.payment is not None and (not isinstance(self.payment, ExactMoney) or self.payment.decimal < 0):
            raise ValueError("debt.payment must be non-negative ExactMoney when present")
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "debt.source_refs"))
        object.__setattr__(self, "truth_class", _exact_truth(self.truth_class, "debt.truth_class"))
        if self.maturity_on and _date_value(self.maturity_on) < _date_value(self.effective_on):
            raise ValueError("debt.maturity_on cannot precede debt.effective_on")
        if self.payment is not None and self.payment.currency != self.principal.currency:
            raise ValueError("debt payment and principal currencies must match")

    def to_dict(self) -> dict[str, Any]:
        return {
            "debt_id": self.debt_id,
            "account_id": self.account_id,
            "principal": self.principal.to_dict(),
            "annual_rate": self.annual_rate.to_dict(),
            "effective_on": self.effective_on,
            "maturity_on": self.maturity_on,
            "payment": self.payment.to_dict() if self.payment else None,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class AssetValue:
    valuation_id: str
    account_id: str
    money: ExactMoney
    as_of: str
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "valuation_id", _text(self.valuation_id, "asset.valuation_id"))
        object.__setattr__(self, "account_id", _text(self.account_id, "asset.account_id"))
        if not isinstance(self.money, ExactMoney):
            raise ValueError("asset.money must be ExactMoney")
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "asset.as_of"))
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "asset.source_refs"))
        object.__setattr__(self, "truth_class", _exact_truth(self.truth_class, "asset.truth_class"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "valuation_id": self.valuation_id,
            "account_id": self.account_id,
            "money": self.money.to_dict(),
            "as_of": self.as_of,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class FeeRecord:
    fee_id: str
    account_id: str
    money: ExactMoney
    effective_on: str
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "fee_id", _text(self.fee_id, "fee.fee_id"))
        object.__setattr__(self, "account_id", _text(self.account_id, "fee.account_id"))
        if not isinstance(self.money, ExactMoney) or self.money.decimal < 0:
            raise ValueError("fee.money must be non-negative ExactMoney")
        object.__setattr__(self, "effective_on", _iso_date(self.effective_on, "fee.effective_on"))
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "fee.source_refs"))
        object.__setattr__(self, "truth_class", _exact_truth(self.truth_class, "fee.truth_class"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "fee_id": self.fee_id,
            "account_id": self.account_id,
            "money": self.money.to_dict(),
            "effective_on": self.effective_on,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class TaxAssumption:
    assumption_id: str
    jurisdiction_ref: str
    effective_on: str
    rate: ExactRate | None
    amount: ExactMoney | None
    source_refs: tuple[str, ...]
    truth_class: FinancialTruthClass = FinancialTruthClass.ASSUMPTION

    def __post_init__(self) -> None:
        object.__setattr__(self, "assumption_id", _text(self.assumption_id, "tax.assumption_id"))
        object.__setattr__(self, "jurisdiction_ref", _text(self.jurisdiction_ref, "tax.jurisdiction_ref"))
        object.__setattr__(self, "effective_on", _iso_date(self.effective_on, "tax.effective_on"))
        if (self.rate is None) == (self.amount is None):
            raise ValueError("tax assumption must provide exactly one of rate or amount")
        if self.rate is not None and not isinstance(self.rate, ExactRate):
            raise ValueError("tax.rate must be ExactRate")
        if self.amount is not None and not isinstance(self.amount, ExactMoney):
            raise ValueError("tax.amount must be ExactMoney")
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "tax.source_refs"))
        result = _enum(self.truth_class, FinancialTruthClass, "tax.truth_class")
        if result is not FinancialTruthClass.ASSUMPTION:
            raise ValueError("tax assumption truth_class must be ASSUMPTION")
        object.__setattr__(self, "truth_class", result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "jurisdiction_ref": self.jurisdiction_ref,
            "effective_on": self.effective_on,
            "rate": self.rate.to_dict() if self.rate else None,
            "amount": self.amount.to_dict() if self.amount else None,
            "source_refs": list(self.source_refs),
            "truth_class": self.truth_class.value,
        }


def _typed_tuple(value: Any, item_type: type[Any], name: str) -> tuple[Any, ...]:
    if type(value) is not tuple or not all(isinstance(item, item_type) for item in value):
        raise ValueError(f"{name} must be a tuple of {item_type.__name__}")
    return value


def _record_id(record: Any) -> str:
    for field in (
        "account_id",
        "balance_id",
        "transaction_id",
        "flow_id",
        "debt_id",
        "valuation_id",
        "fee_id",
        "assumption_id",
    ):
        if hasattr(record, field):
            return str(getattr(record, field))
    raise ValueError("financial record has no stable identity")


def _record_date(record: Any) -> str | None:
    for field in ("as_of", "posted_on", "effective_on"):
        value = getattr(record, field, None)
        if value is not None:
            return str(value)
    return None


@dataclass(frozen=True)
class FinancialLedgerSnapshot:
    snapshot_id: str
    as_of: str
    authority_owner: str
    accounts: tuple[FinancialAccount, ...]
    balances: tuple[BalanceRecord, ...] = ()
    transactions: tuple[TransactionRecord, ...] = ()
    cash_flows: tuple[CashFlowRecord, ...] = ()
    debts: tuple[DebtTerms, ...] = ()
    asset_values: tuple[AssetValue, ...] = ()
    fees: tuple[FeeRecord, ...] = ()
    tax_assumptions: tuple[TaxAssumption, ...] = ()
    version: str = FINANCIAL_EXACT_STATE_VERSION
    ownership_disposition: str = FINANCIAL_OWNERSHIP_DISPOSITION
    patch_authority: str = FINANCIAL_PATCH_AUTHORITY
    proposal_only: bool = True
    execution_authority: bool = FINANCIAL_EXECUTION_AUTHORITY
    advice_authority: bool = FINANCIAL_ADVICE_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != FINANCIAL_EXACT_STATE_VERSION:
            raise ValueError("unsupported financial exact-state version")
        if self.ownership_disposition != FINANCIAL_OWNERSHIP_DISPOSITION:
            raise ValueError("financial ledger ownership boundary changed")
        if self.patch_authority != FINANCIAL_PATCH_AUTHORITY:
            raise ValueError("financial patch authority changed")
        if self.proposal_only is not True or self.execution_authority is not False or self.advice_authority is not False:
            raise ValueError("financial exact-state contract cannot grant execution or advice authority")
        object.__setattr__(self, "snapshot_id", _text(self.snapshot_id, "snapshot.snapshot_id"))
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "snapshot.as_of"))
        object.__setattr__(self, "authority_owner", _text(self.authority_owner, "snapshot.authority_owner"))
        object.__setattr__(self, "accounts", _typed_tuple(self.accounts, FinancialAccount, "snapshot.accounts"))
        object.__setattr__(self, "balances", _typed_tuple(self.balances, BalanceRecord, "snapshot.balances"))
        object.__setattr__(self, "transactions", _typed_tuple(self.transactions, TransactionRecord, "snapshot.transactions"))
        object.__setattr__(self, "cash_flows", _typed_tuple(self.cash_flows, CashFlowRecord, "snapshot.cash_flows"))
        object.__setattr__(self, "debts", _typed_tuple(self.debts, DebtTerms, "snapshot.debts"))
        object.__setattr__(self, "asset_values", _typed_tuple(self.asset_values, AssetValue, "snapshot.asset_values"))
        object.__setattr__(self, "fees", _typed_tuple(self.fees, FeeRecord, "snapshot.fees"))
        object.__setattr__(self, "tax_assumptions", _typed_tuple(self.tax_assumptions, TaxAssumption, "snapshot.tax_assumptions"))
        if not self.accounts:
            raise ValueError("snapshot.accounts must not be empty")
        account_ids = tuple(item.account_id for item in self.accounts)
        if account_ids != tuple(sorted(set(account_ids))):
            raise ValueError("snapshot accounts must be unique and sorted by account_id")
        records = (
            *self.balances,
            *self.transactions,
            *self.cash_flows,
            *self.debts,
            *self.asset_values,
            *self.fees,
            *self.tax_assumptions,
        )
        record_ids = tuple(_record_id(item) for item in records)
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("financial record identities must be globally unique")
        account_map = {item.account_id: item for item in self.accounts}
        snapshot_date = _date_value(self.as_of)
        balance_keys: dict[tuple[str, str], str] = {}
        for record in records:
            record_date = _record_date(record)
            if record_date and _date_value(record_date) > snapshot_date:
                raise ValueError(f"record {_record_id(record)} occurs after snapshot.as_of")
            account_id = getattr(record, "account_id", None)
            if account_id is None:
                continue
            account = account_map.get(account_id)
            if account is None:
                raise ValueError(f"record {_record_id(record)} references an unknown account")
            money = getattr(record, "money", None)
            if money is None:
                money = getattr(record, "principal", None)
            if isinstance(money, ExactMoney) and money.currency != account.currency:
                raise ValueError(f"record {_record_id(record)} currency does not match its account")
            if account.opened_on and record_date and _date_value(record_date) < _date_value(account.opened_on):
                raise ValueError(f"record {_record_id(record)} precedes account opening")
            if account.closed_on and record_date and _date_value(record_date) > _date_value(account.closed_on):
                raise ValueError(f"record {_record_id(record)} follows account closure")
        for balance in self.balances:
            key = (balance.account_id, balance.as_of)
            prior = balance_keys.get(key)
            if prior is not None:
                if prior != balance.money.amount:
                    raise ValueError("contradictory balances exist for the same account and date")
                raise ValueError("duplicate balances exist for the same account and date")
            balance_keys[key] = balance.money.amount
        for debt in self.debts:
            account = account_map[debt.account_id]
            if account.kind is not FinancialAccountKind.LIABILITY:
                raise ValueError("debt terms must reference a LIABILITY account")
            if debt.principal.currency != account.currency:
                raise ValueError("debt principal currency does not match its account")
        for asset in self.asset_values:
            account = account_map[asset.account_id]
            if account.kind not in {FinancialAccountKind.ASSET, FinancialAccountKind.INVESTMENT}:
                raise ValueError("asset valuation must reference an ASSET or INVESTMENT account")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "snapshot_id": self.snapshot_id,
            "as_of": self.as_of,
            "authority_owner": self.authority_owner,
            "accounts": [item.to_dict() for item in self.accounts],
            "balances": [item.to_dict() for item in self.balances],
            "transactions": [item.to_dict() for item in self.transactions],
            "cash_flows": [item.to_dict() for item in self.cash_flows],
            "debts": [item.to_dict() for item in self.debts],
            "asset_values": [item.to_dict() for item in self.asset_values],
            "fees": [item.to_dict() for item in self.fees],
            "tax_assumptions": [item.to_dict() for item in self.tax_assumptions],
            "ownership_disposition": self.ownership_disposition,
            "patch_authority": self.patch_authority,
            "proposal_only": True,
            "execution_authority": False,
            "advice_authority": False,
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict(), digest_size=32)


__all__ = [
    "FINANCIAL_ADVICE_AUTHORITY",
    "FINANCIAL_EXACT_STATE_VERSION",
    "FINANCIAL_EXECUTION_AUTHORITY",
    "FINANCIAL_OWNERSHIP_DISPOSITION",
    "FINANCIAL_PATCH_AUTHORITY",
    "AssetValue",
    "BalanceRecord",
    "CashFlowRecord",
    "DebtTerms",
    "ExactMoney",
    "ExactRate",
    "FeeRecord",
    "FinancialAccount",
    "FinancialAccountKind",
    "FinancialDirection",
    "FinancialLedgerSnapshot",
    "FinancialRateBasis",
    "FinancialTruthClass",
    "TaxAssumption",
    "TransactionRecord",
]
