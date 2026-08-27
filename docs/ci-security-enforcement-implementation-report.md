# CI Security Enforcement Implementation Report

**Author:** Manus AI

**Scope:** CI and repository-security support files only
**Commit target:** `ci: enforce dependency and secret security checks`

## Purpose

This bounded phase converts the repository's existing local dependency checks into required continuous-integration checks and adds a small repository-owned credential-candidate scanner. It does not change application routes, authentication, extraction, target-role intake, deterministic scoring, job requirements, analyses, action plans, database schema, migrations, manifests, lockfiles, or frontend application behavior.

> The security job is designed as a blocking quality gate. A pull request or push cannot pass its workflow while a high-severity JavaScript dependency finding, broken installed Python requirement, failing scanner test, or detected credential candidate remains unresolved.

## Audit baseline and implementation

The pre-change workflow already used least-privilege `contents: read` permissions and had separate web and API quality jobs. The web job used frozen JavaScript installation, while the API job installed the declared development dependency group and ran linting, strict typing, migration setup, and tests. However, it did not enforce the established `pnpm audit --audit-level high` policy, `pip check`, or any repository secret scan.

| Area | Implemented control | Deliberate boundary |
|---|---|---|
| Workflow permissions | The existing workflow-level `contents: read` permission is retained for all jobs, including the new `security` job. | The job receives no write permission and no credential input. |
| JavaScript dependencies | The job uses Node 22, pnpm 11.21.0, `pnpm install --frozen-lockfile`, then the established blocking command `pnpm audit --audit-level high`. | The manifest, lockfile, and audit threshold remain unchanged. `pnpm-workspace.yaml` approves only the reviewed existing `unrs-resolver` postinstall required by the locked resolver package; no broad build-script approval is enabled. |
| Python dependencies | The job uses Python 3.12, installs `services/api[dev]`, then runs `python -m pip check`. | It deliberately reuses the existing compatibility validation mechanism rather than adding another vulnerability-scanning dependency. |
| Secret enforcement | `scripts/scan_secrets.py` enumerates only `git ls-files -z` paths and scans selected, textual tracked source/configuration/documentation files. It rejects ignored local environment files, `.git` paths, generated directories, non-files, and files over 2 MiB. | It is a deterministic candidate detector, not a replacement for a managed secret-scanning program, server-side secret management, or production incident response. |
| Detection rules | The scanner recognizes private-key markers and common OpenAI, GitHub, AWS access-key, AWS secret-access-key, Google API-key, and Slack-token formats. | It prints only `path: rule-name` and never emits a matched candidate value. Pattern-based scanning cannot identify every credential format. |
| Regression safety | A standard-library test suite verifies common credential detection, `.env.local` exclusion, private-key detection, and redacted failure output. | Test fixtures construct non-production candidate strings only inside temporary files. |

## Scanner design

The command-line scanner derives its candidates from Git's tracked-file list rather than walking the working tree. This ensures ignored local environment files, untracked test artifacts, build output, the Git internal directory, and other generated files are outside the CI scan scope. The scanner independently enforces path exclusions as a defense in depth measure.

Each scannable file is opened with UTF-8 replacement handling after its size is bounded. The detector stores only a `SecretFinding` containing a path and rule name. The scan exit code is zero for no candidates and one for candidates; command errors return a separate nonzero code. No extracted value is preserved, returned, or printed.

## Local verification

All checks below were executed locally after implementation. The warning in the API test output is an existing Starlette/httpx deprecation warning; no dependency churn was introduced in this CI-only phase to suppress it.

| Validation | Result |
|---|---|
| `python3 scripts/test_scan_secrets.py` | Passed: 3 focused scanner tests. |
| `python3 scripts/scan_secrets.py` | Passed: no candidate credentials found in tracked source files. |
| `ruff check ../../scripts/scan_secrets.py ../../scripts/test_scan_secrets.py` | Passed. |
| `mypy ../../scripts/scan_secrets.py ../../scripts/test_scan_secrets.py` | Passed: no issues in 2 files. |
| Local security-job equivalent: frozen pnpm install, `pnpm audit --audit-level high`, API development install, `pip check`, scanner tests, scanner | Passed. `pip check` reported no broken requirements. |
| CI workflow YAML/security-job parser validation | Passed locally. It verified the read-only permission, expected three jobs, and required security commands. |
| API quality gate: `ruff check .`, `mypy app`, `pytest` | Passed: 77 tests passed, 1 pre-existing deprecation warning. |
| Web quality gate: lint, typecheck, unit tests, production build | Passed: 12 tests passed across 3 test files; Next.js production build succeeded. |
| `alembic current` | `20260827_0010 (head)`. |

The initial CI configuration was validated locally. A later remote run identified pnpm 11's ignored-build policy for the existing locked `unrs-resolver` postinstall; its source was reviewed and only that one package was added to the workspace `onlyBuiltDependencies` policy. The remediation is validated locally with a frozen install and requires remote workflow confirmation after publication.

## Retained launch prerequisites

The new job improves repository-time protection but does not replace the documented production prerequisites. The single-process application still needs distributed abuse controls when horizontal scaling is introduced. Production also requires managed private object storage, a production secret manager, deployment-level monitoring and alerting, malware-scanning policy, backup and restore operations, and approval-gated privacy/data-lifecycle execution. Those concerns remain unchanged and intentionally out of scope for this non-destructive CI phase.

## Files in scope

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | Adds the blocking, read-only `security` CI job while preserving existing web and API jobs. |
| `scripts/scan_secrets.py` | Adds the standard-library tracked-source scanner with redacted findings. |
| `scripts/test_scan_secrets.py` | Adds focused scanner regression tests. |
| `docs/security.md` | Records the enforced CI dependency/secret controls and their scope. |
| `docs/ci-security-enforcement-implementation-report.md` | Records this implementation, validation, limitations, and the narrow pnpm build-policy remediation. |
| `pnpm-workspace.yaml` | Approves only the reviewed existing `unrs-resolver` postinstall required for a reproducible frozen install. |
