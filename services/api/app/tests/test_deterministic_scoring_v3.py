from __future__ import annotations

from typing import Any

from app.services.deterministic_scoring_v3 import (
    SCORING_VERSION_V3,
    ReviewedRequirement,
    calculate_deterministic_v3,
)


def reviewed_requirement(
    requirement_id: str,
    *,
    category: str,
    normalized_skill: str | None,
    priority: int = 100,
    review_state: str = "reviewed",
) -> ReviewedRequirement:
    return ReviewedRequirement(
        requirement_id=requirement_id,
        requirement="Private manual requirement text",
        category=category,
        normalized_skill=normalized_skill,
        priority=priority,
        review_state=review_state,
        normalization_version="manual-v1",
    )


def requirement_by_id(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        requirement["requirementId"]: requirement
        for requirement in result["requirements"]
    }


def test_v3_is_pure_and_applies_explicit_category_weights_with_evidence_references() -> None:
    requirements = (
        reviewed_requirement("must-python", category="must-have", normalized_skill="python"),
        reviewed_requirement("should-docker", category="should-have", normalized_skill="docker"),
        reviewed_requirement(
            "nice-terraform",
            category="nice-to-have",
            normalized_skill="terraform",
        ),
    )

    first = calculate_deterministic_v3(frozenset({"python"}), requirements)
    second = calculate_deterministic_v3(frozenset({"python"}), requirements)
    by_id = requirement_by_id(first)

    assert first == second
    assert first["scoringVersion"] == SCORING_VERSION_V3
    assert first["overallScore"] == 60
    assert first["calculationMetadata"]["categoryBaseWeights"] == {
        "must-have": 60,
        "should-have": 30,
        "nice-to-have": 10,
    }
    assert by_id["must-python"]["state"] == "MATCHED"
    assert by_id["must-python"]["evidence"] == {
        "source": "CV_NORMALIZED_SKILL",
        "term": "python",
    }
    assert by_id["should-docker"]["state"] == "NOT_FOUND_IN_PROVIDED_CV"
    assert by_id["should-docker"]["evidence"] is None
    assert "does not have" not in by_id["should-docker"]["message"]
    assert "Not found in the provided CV" in by_id["should-docker"]["message"]
    assert "Private manual requirement text" not in str(first)


def test_v3_handles_duplicate_and_noncomparable_requirements_deterministically() -> None:
    requirements = (
        reviewed_requirement("must-python", category="must-have", normalized_skill="python"),
        reviewed_requirement("should-python", category="should-have", normalized_skill="python"),
        reviewed_requirement(
            "unreviewed-sql",
            category="should-have",
            normalized_skill="sql",
            review_state="unreviewed",
        ),
        reviewed_requirement("no-skill", category="nice-to-have", normalized_skill=None),
    )

    result = calculate_deterministic_v3(frozenset({"python", "sql"}), requirements)
    by_id = requirement_by_id(result)

    assert result["overallScore"] == 100
    assert by_id["must-python"]["state"] == "MATCHED"
    assert by_id["should-python"]["state"] == "DUPLICATE_SUPERSEDED"
    assert by_id["unreviewed-sql"]["state"] == "NOT_REVIEWED"
    assert by_id["no-skill"]["state"] == "NOT_COMPARABLE"
    assert result["calculationMetadata"]["eligibleRequirementCount"] == 1


def test_v3_returns_a_safe_empty_result_when_no_requirements_are_eligible() -> None:
    result = calculate_deterministic_v3(
        frozenset({"python"}),
        (
            reviewed_requirement(
                "unreviewed",
                category="must-have",
                normalized_skill="python",
                review_state="unreviewed",
            ),
            reviewed_requirement("missing-skill", category="nice-to-have", normalized_skill=None),
        ),
    )

    assert result["overallScore"] == 0
    assert result["gaps"] == []
    assert result["calculationMetadata"]["eligibleRequirementCount"] == 0
