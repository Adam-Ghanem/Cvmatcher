from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

SCORING_VERSION_V3: Final = "deterministic-v3"
CATEGORY_BASE_WEIGHTS: Final = {
    "must-have": 60,
    "should-have": 30,
    "nice-to-have": 10,
}
ELIGIBLE_REVIEW_STATES: Final = frozenset({"reviewed", "user-confirmed"})


@dataclass(frozen=True)
class ReviewedRequirement:
    """Server-owned reviewed requirement data supplied to the pure v3 scorer."""

    requirement_id: str
    requirement: str
    category: str
    normalized_skill: str | None
    priority: int
    review_state: str
    normalization_version: str


def calculate_deterministic_v3(
    cv_terms: frozenset[str],
    requirements: tuple[ReviewedRequirement, ...],
) -> dict[str, Any]:
    ordered_requirements = tuple(
        sorted(requirements, key=lambda requirement: requirement.requirement_id)
    )
    entries: dict[str, dict[str, object]] = {}
    candidates_by_skill: dict[str, list[ReviewedRequirement]] = {}

    for requirement in ordered_requirements:
        if requirement.review_state not in ELIGIBLE_REVIEW_STATES:
            entries[requirement.requirement_id] = requirement_payload(
                requirement,
                state="NOT_REVIEWED",
                message="This requirement is not reviewed and is not included in the calculation.",
                evidence=None,
            )
            continue
        if requirement.normalized_skill is None:
            entries[requirement.requirement_id] = requirement_payload(
                requirement,
                state="NOT_COMPARABLE",
                message="This reviewed requirement has no normalized skill evidence to compare.",
                evidence=None,
            )
            continue
        candidates_by_skill.setdefault(requirement.normalized_skill, []).append(requirement)

    effective_requirements: list[ReviewedRequirement] = []
    for _skill, candidates in sorted(candidates_by_skill.items()):
        chosen = max(candidates, key=requirement_precedence)
        effective_requirements.append(chosen)
        for candidate in candidates:
            if candidate.requirement_id == chosen.requirement_id:
                continue
            entries[candidate.requirement_id] = requirement_payload(
                candidate,
                state="DUPLICATE_SUPERSEDED",
                message=(
                    "A higher-precedence reviewed requirement uses the same normalized skill and "
                    "is included instead."
                ),
                evidence=None,
            )

    matched_skills: list[str] = []
    missing_skills: list[str] = []
    gaps: list[dict[str, object]] = []
    denominator = sum(requirement_weight(requirement) for requirement in effective_requirements)
    numerator = 0
    for requirement in sorted(effective_requirements, key=lambda item: item.requirement_id):
        assert requirement.normalized_skill is not None
        skill = requirement.normalized_skill
        if skill in cv_terms:
            numerator += requirement_weight(requirement)
            matched_skills.append(skill)
            entries[requirement.requirement_id] = requirement_payload(
                requirement,
                state="MATCHED",
                message="Exact normalized evidence was found in the provided CV.",
                evidence={"source": "CV_NORMALIZED_SKILL", "term": skill},
            )
            continue
        missing_skills.append(skill)
        entries[requirement.requirement_id] = requirement_payload(
            requirement,
            state="NOT_FOUND_IN_PROVIDED_CV",
            message="Not found in the provided CV.",
            evidence=None,
        )
        gaps.append(
            {
                "term": skill,
                "state": "NOT_FOUND_IN_PROVIDED_CV",
                "component": "requirements",
                "requirementId": requirement.requirement_id,
            }
        )

    score = round(numerator / denominator * 100) if denominator else 0
    component_state = (
        "NOT_APPLICABLE"
        if not effective_requirements
        else "MATCHED"
        if score == 100
        else "PARTIAL"
        if score
        else "EVIDENCE_NOT_FOUND"
    )
    return {
        "scoringVersion": SCORING_VERSION_V3,
        "overallScore": score,
        "components": [
            {
                "key": "requirements",
                "label": "Reviewed requirements match",
                "weight": 100,
                "score": score,
                "state": component_state,
                "matchedTerms": sorted(matched_skills),
                "notFoundTerms": sorted(missing_skills),
                "explanation": (
                    "Uses only reviewed structured requirements and exact normalized evidence from "
                    "the provided CV."
                ),
            }
        ],
        "gaps": gaps,
        "requirements": [
            entries[requirement.requirement_id] for requirement in ordered_requirements
        ],
        "calculationMetadata": {
            "configurationVersion": "requirements-category-weighting-v1",
            "categoryBaseWeights": dict(CATEGORY_BASE_WEIGHTS),
            "eligibleRequirementCount": len(effective_requirements),
        },
    }


def requirement_precedence(requirement: ReviewedRequirement) -> tuple[int, int, str]:
    return (
        CATEGORY_BASE_WEIGHTS[requirement.category],
        requirement.priority,
        requirement.requirement_id,
    )


def requirement_weight(requirement: ReviewedRequirement) -> int:
    return CATEGORY_BASE_WEIGHTS[requirement.category] * requirement.priority


def requirement_payload(
    requirement: ReviewedRequirement,
    *,
    state: str,
    message: str,
    evidence: dict[str, str] | None,
) -> dict[str, object]:
    return {
        "requirementId": requirement.requirement_id,
        "category": requirement.category,
        "normalizedSkill": requirement.normalized_skill,
        "priority": requirement.priority,
        "normalizationVersion": requirement.normalization_version,
        "reviewState": requirement.review_state,
        "state": state,
        "message": message,
        "evidence": evidence,
    }
