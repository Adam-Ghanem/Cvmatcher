# CVMatcher Deterministic Analysis Contract

This document describes the implemented Phase 5 public boundary for deterministic evidence matching. The authoritative transport endpoints are `POST /api/v1/match-analyses` and `GET /api/v1/match-analyses/{analysisId}`.

## Input contract

Creation accepts a strict, owner-neutral payload. Ownership is derived exclusively from the validated server session.

```ts
interface CreateMatchAnalysisInput {
  cvDocumentVersionId: string;
  jobTargetId: string;
}
```

The selected CV version must be owned by the authenticated user and have a successful non-empty private extraction. The selected target role must be owned by the same authenticated user. Unknown fields are rejected. Creation requires a valid CSRF token.

## Result contract

```ts
type MatchComponentState =
  | "MATCHED"
  | "PARTIAL"
  | "EVIDENCE_NOT_FOUND"
  | "NOT_APPLICABLE";

interface MatchScoreComponent {
  key: "skills" | "experience" | "keywords" | "education" | "ats";
  label: string;
  weight: number;
  score: number;
  state: MatchComponentState;
  matchedTerms: string[];
  notFoundTerms: string[];
  explanation: string;
}

interface MatchGap {
  term: string;
  state: "NOT_FOUND_IN_PROVIDED_CV";
  component: MatchScoreComponent["key"];
}

interface MatchAnalysis {
  id: string;
  scoringVersion: "deterministic-v2" | string;
  overallScore: number;
  components: MatchScoreComponent[];
  gaps: MatchGap[];
  createdAt: string;
}
```

## Contract invariants

| Area | Invariant |
|---|---|
| Scope | An analysis is private and owner-scoped. An absent and another user’s resource both return `404 RESOURCE_NOT_FOUND`. |
| Readiness | An owned version without succeeded private text returns `409 CV_TEXT_NOT_READY`; no source text is returned. |
| Idempotency | The same CV version, target role, and scoring version reuse one persisted result. A scoring-version change intentionally permits a new result. |
| Scores | `overallScore` and component scores are inclusive integers from `0` to `100`. Components retain fixed documented weights. |
| Evidence | `matchedTerms`, `notFoundTerms`, and gaps contain only bounded normalized terms produced by fixed source-controlled rules. |
| Missing evidence | A missing term uses `NOT_FOUND_IN_PROVIDED_CV`; it does not claim the person lacks a qualification. |
| Privacy | Responses never contain raw CV text, raw job-description text, document/target IDs, user IDs, opaque storage keys, or document URLs. |
| Non-prediction | The score is not a prediction or guarantee of interviews, employment, ATS outcome, or suitability. |
| AI exclusion | No LLM, embedding, semantic service, external API, prompt, or model output participates in this contract. |

## Versioning policy

The scorer exposes a named version in every persisted response. A change that could materially affect a score, matched term, gap, or explanation must create a new scoring version. This preserves the interpretation of existing analyses and permits explicit re-analysis under a revised deterministic rule set.
