# Aura Financial Arena — F1 Exact-State Contract

**Version:** `AURA_FINANCIAL_EXACT_STATE_F1_V1`  
**Issue:** #126  
**Status:** Additive contract foundation

## Purpose

F1 gives Aura a deterministic, local-first way to represent user-supplied or exactly imported financial facts without turning Aura into a bank, broker, payment processor, tax filer, financial adviser, or autonomous account operator.

The contract records:

- accounts and account kinds;
- exact balances and dated transactions;
- dated cash flows;
- debt principal, rates, payments, and maturity dates;
- dated asset values;
- fees;
- explicitly labeled tax assumptions;
- source references, truth class, currency, date, and authority owner.

## Exact arithmetic

Financial amounts and rates use Python `Decimal` semantics but serialize as normalized decimal strings. Binary floating-point input is rejected. Values must be finite and remain within the bounded exact precision and exponent range declared by the contract.

The contract does not silently:

- round values;
- convert currencies;
- infer exchange rates;
- infer dates;
- infer ownership;
- infer account authority;
- convert assumptions into exact facts.

## Truth classes

| Class | Meaning |
|---|---|
| `USER_RECORDED` | The user directly supplied the fact. |
| `IMPORTED_EXACT` | An exact imported record supplied the fact. |
| `DERIVED_ARITHMETIC` | Reserved for later formula-bound indicators; not accepted as raw exact ledger evidence. |
| `ASSUMPTION` | A declared scenario or tax assumption, never exact ledger truth. |
| `UNAVAILABLE` | The information is absent and must not be invented. |

Accounts, balances, transactions, cash flows, debts, asset values, and fees accept only `USER_RECORDED` or `IMPORTED_EXACT`. Tax assumptions must remain `ASSUMPTION`.

## Snapshot invariants

`FinancialLedgerSnapshot` fails closed when it encounters:

- unsupported versions or altered ownership boundaries;
- execution, advice, or non-proposal authority;
- account authority owners that differ from the snapshot authority owner;
- empty, duplicated, or unsorted account identities;
- duplicated record identities;
- unknown account references;
- mixed record/account currencies;
- records outside an account lifecycle;
- records dated after the snapshot;
- duplicate or contradictory balances for one account and date;
- debt terms attached to a non-liability account;
- asset values attached to a non-asset/non-investment account;
- malformed dates, currencies, rates, sources, or decimals.

Every balance, transaction, flow, debt, valuation, fee, and assumption is identified by its own record ID rather than its parent account ID. For transactions, both `effective_on` and `posted_on` are checked independently against the snapshot date and account lifecycle.

Serialization is deterministic and the complete snapshot receives a stable 256-bit BLAKE2 digest through Aura's canonical event-contract serializer.

## Authority boundary

F1 is always:

```text
proposal_only = true
execution_authority = false
advice_authority = false
patch_authority = EXACT_USER_OR_IMPORTED_RECORDS_ONLY
ownership_disposition = LOCAL_USER_LEDGER_RETAINS_OWNERSHIP
```

No model, Planning Board node, DIKWP stage, QDKT record, DREAM/MUSIC score, ST3GG/JSpace representation, rationale, or generated plan can mutate financial truth or grant authority.

## Privacy boundary

Raw financial records are local and purpose-limited. They are not public-release content, general model context, CODEMAP authority truth, or unrestricted telemetry. Later indicator exports must expose only the minimum formula-bound result and its source IDs, assumptions, measurement class, and as-of date.

## Non-goals

F1 does not include:

- external bank or broker connectors;
- credential storage;
- transactions, transfers, payments, or trades;
- recommendations or portfolio decisions;
- future-return predictions;
- tax or legal conclusions;
- financial scenarios or counterfactuals;
- LifeOS quests or Aura Farming gameplay;
- live Planning Board projection.

Those remain separately reviewable future stages after the exact-state foundation is verified.

<!-- transient verification marker -->