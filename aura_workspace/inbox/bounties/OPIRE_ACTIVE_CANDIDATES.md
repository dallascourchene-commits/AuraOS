# Opire active-funding candidates — bounded harvest

Observed 2026-08-15 through current Opire public surfaces.

| Candidate | Stack/lane | Funding/currentness observed | Execution state |
|---|---|---|---|
| typeorm/typeorm#3357 | TypeScript / schema migrations / database | $590 shown by Opire; command available | ANALYZE — deep migration/data-loss matrix, high contention |
| strapi/strapi#11998 | TypeScript / core database / nested filters | Status Open; $70 total across 3 Available rewards; 0 paid | ANALYZE — exact query-engine path needs broader source hydration |
| storybookjs/storybook#12641 | TypeScript / controls | $263 shown; command available | ANALYZE — UI regression surface |
| qtop/qtop#433 | Python / test + CI + docs | $220 shown; command available | ANALYZE — broad CI matrix, Python 3.6 + modern jobs, GitHub/GitLab parity |

## Strapi exact provider state captured

Opire reports for `strapi/strapi#11998`:
- Status: Open
- Programming language: TypeScript
- labels include `issue: bug`, `severity: low`, `status: confirmed`, `source: core:database`
- 3 available rewards: $30 + $20 + $20
- 0 paid rewards
- 4 solvers trying / 4 claimed at observation time

Source: https://app.opire.dev/issues/01HWT2MKE4GWPJXDPMAFEAHHHE

## Promotion rule

These are not automatically READY_FOR_PR. Provider-funded currentness only opens the analysis lane; exact source reproduction, patch validation, and issue-specific acceptance evidence are still required.
