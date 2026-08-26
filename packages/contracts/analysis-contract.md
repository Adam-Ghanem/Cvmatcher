# CVMatcher Analysis Contract Boundary

This document reserves the Phase 2+ contract boundary. It is not an implemented API endpoint.

| Contract | Required invariant |
|---|---|
| `CandidateEvidence` | Every extracted value must retain a source reference and extraction confidence. |
| `JobRequirement` | Every requirement must retain a source reference and a requirement category. |
| `ScoreBreakdown` | Every component score must include a scoring version, weight, evidence IDs, and an explainable state. |
| `Gap` | A missing-evidence state must be represented as `NOT_FOUND_IN_PROVIDED_CV`, not a factual claim about the candidate. |
| `Recommendation` | Every recommendation must cite allowed evidence IDs and cannot change deterministic scoring. |

Phase 1 deliberately creates no analysis endpoint, score, CV parser, or OpenAI call.
