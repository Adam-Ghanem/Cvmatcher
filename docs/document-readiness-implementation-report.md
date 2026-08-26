# Document Readiness UX Implementation Report

**Status:** Implemented and locally verified

**Scope:** Deterministic presentation and eligibility refinement over the existing private PDF/DOCX extraction metadata.

**Out of scope:** OCR, AI/LLM calls, scoring changes, job-requirement extraction, storage changes, retention/lifecycle work, queues, and migrations.

## Purpose

This phase makes the private extraction result actionable without exposing document content or parser internals. A user can now distinguish between a document that is ready to compare, one that can be compared with limitations, and one that must be replaced before analysis. The experience follows the product progression from document state to recovery action, while retaining the deterministic matcher as the only scoring authority.

| Readiness state | Deterministic source condition | Analysis eligibility | User-facing outcome |
|---|---|---:|---|
| `ready` | Extraction succeeded, quality is `usable`, and no bounded warnings are present. | Yes | The CV is presented as **Ready**. |
| `warning` | Extraction succeeded with `limited` quality or a bounded limited-content warning. | Yes | The CV is presented as **Ready with limitations**, with concise recovery guidance. |
| `blocked` | Extraction is incomplete/failed, quality is not usable or limited, or no extractable content is found. | No | The CV is presented as **Blocked**, with a safe upload recovery action. |

## Deterministic Domain Model

Readiness is a pure, derived domain decision in `services/api/app/services/cv_extraction.py`. It consumes only the existing extraction `status`, `quality`, and warning identifiers. It is **not persisted**, so this phase adds no migration and does not introduce a parallel extraction-quality model.

A non-empty extraction below `MINIMUM_RECOMMENDED_EXTRACTED_CHARACTERS` (20 characters) remains technically analyzable but receives `quality="limited"` and `LIMITED_EXTRACTABLE_TEXT`. The threshold is a product-quality warning, not a claim about the candidate or a scoring change. Empty extraction behavior remains `quality="low"` with `NO_EXTRACTABLE_TEXT` and is blocked.

Only the two allowlisted warning identifiers are returned, in a deterministic order and without duplicates. Unknown stored values cannot appear in the readiness response.

## API and Analysis Boundary

The owner-scoped extraction endpoints now return existing safe metadata plus a nested `readiness` object:

```json
{
  "readiness": {
    "state": "warning",
    "explanation": "This document can be compared, but the available content may be limited.",
    "recoveryGuidance": "For more complete results, upload a fuller text-based PDF or DOCX."
  }
}
```

The contract intentionally excludes extracted text, raw source files, storage keys, parser diagnostics, process data, and internal failure details. Existing session-derived ownership and CSRF enforcement are unchanged.

The protected analysis service now derives the same readiness state on the server before calling deterministic scoring. A `blocked` document returns the existing safe `409 CV_TEXT_NOT_READY` response. A separate private-text integrity check remains in place, so a malformed or inconsistent record cannot enter analysis merely because its metadata appears eligible.

## Frontend Experience

`CvExtractionControl` uses the server-derived readiness state directly and presents explicit **Ready**, **Ready with limitations**, or **Blocked** labels. It shows only safe explanation and recovery copy. The analysis selector includes both ready and warning CVs, excludes blocked CVs, and repeats a selected warning’s limitation guidance beside the comparison input. When no eligible CV exists, it explains the recovery path instead of leaving the user with a generic empty state.

The change preserves keyboard-native controls, labels, focus styles, status/error roles, responsive layout behavior, and reduced visual complexity. No CV content is rendered in the readiness UI.

## Verification

| Check | Result |
|---|---|
| Backend Ruff | Passed |
| Backend mypy | Passed with no issues in 55 source files |
| Backend pytest | 56 passed; one pre-existing Starlette/httpx deprecation warning |
| Frontend ESLint | Passed |
| Frontend TypeScript | Passed |
| Frontend Vitest | 12 passed across 3 test files |
| Frontend production build | Passed |
| Alembic current | `20260826_0006 (head)`; no migration added |
| `pnpm audit --audit-level high` | No known vulnerabilities found |
| `pip3 check` | All installed packages compatible |

The test coverage includes ready, warning, and blocked derivation; safe API payloads that exclude private content; deduplicated allowlisted warnings; owner-scoped extraction behavior; warning-state analysis selection; blocked-state recovery and disabled selection; and server-side prevention of analysis for an empty successful extraction.

## Deliberate Limitations

This remains a text-extraction readiness signal. It does not perform OCR, judge factual CV quality, infer qualifications, or guarantee comparison completeness. Scanned/image-only documents remain blocked until a text-based PDF or DOCX is provided. The next product phase may build on this safe private-text foundation, but must retain these ownership, metadata-only, and server-enforced eligibility boundaries.
