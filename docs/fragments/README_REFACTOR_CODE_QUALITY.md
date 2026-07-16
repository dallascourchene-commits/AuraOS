## Executable Refactor Code Quality

Planning quality and executable code quality are recorded separately. The earlier planning and synthetic hybrid arms remain `CODE_QUALITY_UNAVAILABLE` because they did not independently produce and evaluate real patches. The executable fixture applies each method's unified diff in an isolated workspace and records every measured result—even when an acceptance gate fails.

| Method | Calls | Total token proxy | Visible | Hidden | Regression | API | Scope | Security | Working status | Disposition | Observed | Benchmark |
|---|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---:|
| Broad-context implementer | 1 | 131,654 | 3/3 | 1/3 | 2/2 | PASS | PASS | PASS | `PARTIALLY_WORKING` | `PARTIAL` | 80.34 | 78.33 |
| Aura-slice Surgeon | 1 | 14,868 | 3/3 | 2/3 | 2/2 | PASS | PASS | PASS | `PARTIALLY_WORKING` | `PARTIAL` | 88.89 | 86.67 |
| Council V2 + Surgeon | 18 | 158,545 | 3/3 | 3/3 | 2/2 | PASS | PASS | PASS | `WORKING` | `ACCEPTED` | 100.00 | 97.50 |
| **Selective Council V3 + Surgeon** | **12** | **106,494** | **3/3** | **3/3** | **2/2** | **PASS** | **PASS** | **PASS** | **`WORKING`** | **`ACCEPTED`** | **100.00** | **97.50** |

Performance and portability were not measured, so measurement completeness was 97.5%. The broad and sliced methods retain their passing compilation, visible tests, regression tests, API, scope, security, and maintainability evidence; they are `PARTIAL` because held-out behavior failed.

### Selective Council V3

Compared with Council V2 on the same frozen role fixture, V3 produced:

- **33.33% fewer model calls** — 12 instead of 18;
- **40.00% fewer critic reports** — 9 instead of 15;
- **33.58% lower input-token proxy**;
- **32.83% lower total-token proxy**;
- **0.0000 planning-quality delta**;
- the same substantive selected plan;
- the same executable patch digest;
- the same `ACCEPTED` disposition and code-quality scores.

This is positive evidence that selective Council calling is better on this controlled fixture. It is not yet a general claim across independent models or production AuraOS refactors.

Every executable arm emits `AURA_REFACTOR_OUTPUT_RECORD_V1`, validated by `schemas/aura_refactor_output_record.schema.json`. Estimated and provider-reported input/output tokens are stored separately. The record preserves exact test counts, failing-test IDs, JUnit digests, API, scope, security, static-analysis, maintainability, completeness, working status, failed gates, and final disposition.

Aura uses ISO/IEC 25010:2023, ISO/IEC 5055:2021, NIST SSDF 1.1, OWASP SAMM, and SWE-bench-style isolated evaluation as reference frameworks. This is not certification or an official benchmark submission.

Detailed evidence: [`docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`](docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md).  
Standard protocol: [`docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`](docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md).
