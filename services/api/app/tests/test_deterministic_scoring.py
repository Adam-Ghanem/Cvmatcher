from __future__ import annotations

from typing import cast

from app.services.deterministic_scoring import SCORING_VERSION, calculate_deterministic_score


def components_by_key(result: dict[str, object]) -> dict[object, dict[str, object]]:
    return {
        component["key"]: component
        for component in cast(list[dict[str, object]], result["components"])
    }


def test_deterministic_score_reports_exact_evidence_and_missing_terms_transparently() -> None:
    result = calculate_deterministic_score(
        "Candidate@example.com\nExperience\n5 years Python and PostgreSQL engineering\n"
        "Education\nBachelor of Science\nSkills",
        "Staff engineer with 5+ years of Python, PostgreSQL, Docker, and AWS experience. "
        "Bachelor degree required.",
    )

    components = components_by_key(result)
    assert result["scoringVersion"] == SCORING_VERSION
    assert components["skills"]["matchedTerms"] == ["postgresql", "python"]
    assert components["skills"]["notFoundTerms"] == ["aws", "docker"]
    gaps = cast(list[dict[str, object]], result["gaps"])
    assert {gap["term"] for gap in gaps} >= {"aws", "docker"}
    assert all(gap["state"] == "NOT_FOUND_IN_PROVIDED_CV" for gap in gaps)


def test_deterministic_score_marks_absent_target_signals_not_applicable_without_weight_shift(
) -> None:
    result = calculate_deterministic_score(
        "candidate@example.com\nExperience\nSkills\nEducation",
        "A role focused on collaboration and customer outcomes.",
    )

    components = components_by_key(result)
    assert components["skills"]["state"] == "NOT_APPLICABLE"
    assert components["experience"]["state"] == "NOT_APPLICABLE"
    assert components["education"]["state"] == "NOT_APPLICABLE"
    assert cast(int, result["overallScore"]) >= 0


def test_keyword_evidence_uses_only_normalized_source_controlled_terms() -> None:
    result = calculate_deterministic_score(
        "Python experience",
        "Build reliable platform services with Python and Docker.",
    )

    keywords = components_by_key(result)["keywords"]
    assert keywords["matchedTerms"] == ["python"]
    assert keywords["notFoundTerms"] == ["docker"]
    assert {gap["term"] for gap in cast(list[dict[str, object]], result["gaps"])}.isdisjoint(
        {"build", "platform", "reliable", "services", "docker."}
    )
