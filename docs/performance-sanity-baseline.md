# Performance Sanity Baseline

**Author:** Manus AI

## Measurement scope

This phase measured the existing backend regression suite with pytest duration reporting before proposing any optimization. The run completed **107 tests in 145.39 seconds** on the development environment. The 20 slowest tests accounted for **72.15 seconds** of accumulated test duration.

The slowest observed tests exercise owner-isolation, deterministic analysis creation/reuse, action-plan concurrency, and bounded document extraction. These are security- and correctness-sensitive paths that deliberately use a real local PostgreSQL service, Argon2 password work, request/session setup, transaction locks, and isolated extraction behavior. The result is a development verification profile, not a production latency benchmark or an end-user service-level objective.

| Observation | Evidence-based interpretation | Decision |
|---|---|---|
| Full regression suite takes about 2 minutes 25 seconds | It is acceptable for the current focused CI gate but should be watched as coverage grows. | No parallelization or test weakening added. |
| Owner/isolation and deterministic-analysis tests dominate the measured list | Their cost is consistent with real database and authentication boundaries under test. | Preserve real integration coverage. |
| Extraction tests appear among the slower cases | They intentionally exercise isolated process and resource-limit behavior. | Do not weaken document-safety limits for test speed. |
| No representative production load/trace data exists in the repository | An endpoint latency or capacity claim would be speculative. | No production performance optimization is justified. |

## Follow-up measurement prerequisites

A later operational phase should collect privacy-safe, aggregate endpoint duration/error data from an approved monitoring design, establish capacity assumptions and traffic mix, run authenticated load tests against a disposable environment with synthetic data, and profile verified bottlenecks before changing pool sizes, indexes, or request-processing architecture. Any resulting work must preserve deterministic scoring, owner isolation, private document boundaries, and the existing extraction resource limits.

This baseline adds no runtime instrumentation, dependency, test-data fixture, database index, cache, queue, Redis deployment, or infrastructure claim. The temporary timing output was removed after summarization and was not committed.
