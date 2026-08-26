from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

SCORING_VERSION: Final = "deterministic-v2"
COMPONENT_WEIGHTS: Final = {
    "skills": 35,
    "experience": 20,
    "keywords": 25,
    "education": 10,
    "ats": 10,
}
SKILL_VOCABULARY: Final = frozenset(
    {
        "python",
        "typescript",
        "javascript",
        "react",
        "nextjs",
        "fastapi",
        "sql",
        "postgresql",
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "terraform",
        "git",
        "linux",
        "java",
        "go",
        "csharp",
        "nodejs",
        "graphql",
        "rest",
        "analytics",
        "tableau",
        "powerbi",
    }
)
KEYWORD_VOCABULARY: Final = SKILL_VOCABULARY | frozenset(
    {
        "architecture",
        "automation",
        "compliance",
        "data",
        "design",
        "leadership",
        "management",
        "mentoring",
        "security",
        "testing",
    }
)
DEGREE_RANK: Final = {"associate": 1, "bachelor": 2, "master": 3, "doctorate": 4}
WORD_PATTERN: Final = re.compile(r"[a-z0-9+#]{2,}")
YEARS_PATTERN: Final = re.compile(r"\b(\d{1,2})\s*\+?\s*years?\b")


@dataclass(frozen=True)
class ScoreComponent:
    key: str
    label: str
    weight: int
    score: int
    state: str
    matched_terms: tuple[str, ...]
    not_found_terms: tuple[str, ...]
    explanation: str


def calculate_deterministic_score(cv_text: str, job_text: str) -> dict[str, object]:
    cv_terms = normalized_terms(cv_text)
    job_terms = normalized_terms(job_text)
    components = (
        vocabulary_component("skills", "Skills match", cv_terms, job_terms, SKILL_VOCABULARY),
        experience_component(cv_text, job_text),
        keyword_component(cv_terms, job_terms),
        education_component(cv_terms, job_terms),
        ats_component(cv_text),
    )
    overall_score = round(sum(component.score * component.weight for component in components) / 100)
    return {
        "scoringVersion": SCORING_VERSION,
        "overallScore": overall_score,
        "components": [component_to_payload(component) for component in components],
        "gaps": [
            {"term": term, "state": "NOT_FOUND_IN_PROVIDED_CV", "component": component.key}
            for component in components
            for term in component.not_found_terms
        ],
    }


def normalized_terms(value: str) -> frozenset[str]:
    normalized = value.casefold().replace("c++", "cplusplus").replace("c#", "csharp")
    normalized = normalized.replace("next.js", "nextjs").replace("node.js", "nodejs")
    return frozenset(WORD_PATTERN.findall(normalized))


def vocabulary_component(
    key: str,
    label: str,
    cv_terms: frozenset[str],
    job_terms: frozenset[str],
    vocabulary: frozenset[str],
) -> ScoreComponent:
    required = tuple(sorted(job_terms & vocabulary))
    if not required:
        return not_applicable_component(key, label)
    matched = tuple(term for term in required if term in cv_terms)
    missing = tuple(term for term in required if term not in cv_terms)
    return applicable_component(key, label, required, matched, missing)


def keyword_component(cv_terms: frozenset[str], job_terms: frozenset[str]) -> ScoreComponent:
    required = tuple(sorted(job_terms & KEYWORD_VOCABULARY))
    if not required:
        return not_applicable_component("keywords", "Keyword match")
    matched = tuple(term for term in required if term in cv_terms)
    missing = tuple(term for term in required if term not in cv_terms)
    return applicable_component("keywords", "Keyword match", required, matched, missing)


def experience_component(cv_text: str, job_text: str) -> ScoreComponent:
    required_years = maximum_years(job_text)
    if required_years is None:
        return not_applicable_component("experience", "Experience match")
    cv_years = maximum_years(cv_text)
    if cv_years is None:
        return ScoreComponent(
            "experience",
            "Experience match",
            20,
            0,
            "EVIDENCE_NOT_FOUND",
            (),
            (f"{required_years}+ years",),
            "No explicit qualifying years evidence was found in the provided CV.",
        )
    score = min(100, round(cv_years / required_years * 100))
    if score == 100:
        return ScoreComponent(
            "experience",
            "Experience match",
            20,
            score,
            "MATCHED",
            (f"{cv_years} years",),
            (),
            "Explicit years evidence meets the target requirement.",
        )
    return ScoreComponent(
        "experience",
        "Experience match",
        20,
        score,
        "PARTIAL",
        (f"{cv_years} years",),
        (f"{required_years}+ years",),
        "Explicit years evidence is below the target requirement.",
    )


def education_component(cv_terms: frozenset[str], job_terms: frozenset[str]) -> ScoreComponent:
    target_degree = maximum_degree(job_terms)
    if target_degree is None:
        return not_applicable_component("education", "Education match")
    cv_degree = maximum_degree(cv_terms)
    if cv_degree is None:
        return ScoreComponent(
            "education",
            "Education match",
            10,
            0,
            "EVIDENCE_NOT_FOUND",
            (),
            (target_degree,),
            "No matching degree-category evidence was found in the provided CV.",
        )
    if DEGREE_RANK[cv_degree] >= DEGREE_RANK[target_degree]:
        return ScoreComponent(
            "education",
            "Education match",
            10,
            100,
            "MATCHED",
            (cv_degree,),
            (),
            "Provided degree-category evidence meets the target requirement.",
        )
    return ScoreComponent(
        "education",
        "Education match",
        10,
        50,
        "PARTIAL",
        (cv_degree,),
        (target_degree,),
        "Provided degree-category evidence is below the target requirement.",
    )


def ats_component(cv_text: str) -> ScoreComponent:
    value = cv_text.casefold()
    signals = {
        "contact": bool(re.search(r"[\w.+-]+@[\w.-]+", value)),
        "experience": "experience" in value,
        "education": "education" in value,
        "skills": "skills" in value,
    }
    matched = tuple(signal for signal, present in signals.items() if present)
    missing = tuple(signal for signal, present in signals.items() if not present)
    score = round(len(matched) / len(signals) * 100)
    state = "MATCHED" if score == 100 else "PARTIAL" if score else "EVIDENCE_NOT_FOUND"
    return ScoreComponent(
        "ats",
        "ATS readiness",
        10,
        score,
        state,
        matched,
        missing,
        "Checks only for basic text and common section signals in the provided CV.",
    )


def applicable_component(
    key: str,
    label: str,
    required: tuple[str, ...],
    matched: tuple[str, ...],
    missing: tuple[str, ...],
) -> ScoreComponent:
    score = round(len(matched) / len(required) * 100)
    state = "MATCHED" if score == 100 else "PARTIAL" if score else "EVIDENCE_NOT_FOUND"
    return ScoreComponent(
        key,
        label,
        COMPONENT_WEIGHTS[key],
        score,
        state,
        matched,
        missing,
        "Uses exact normalized evidence terms from the provided CV and target description.",
    )


def not_applicable_component(key: str, label: str) -> ScoreComponent:
    return ScoreComponent(
        key,
        label,
        COMPONENT_WEIGHTS[key],
        100,
        "NOT_APPLICABLE",
        (),
        (),
        "No corresponding requirement was found in the provided target description.",
    )


def maximum_years(value: str) -> int | None:
    years = [int(match) for match in YEARS_PATTERN.findall(value.casefold())]
    return max(years, default=None)


def maximum_degree(terms: frozenset[str]) -> str | None:
    present = [degree for degree in DEGREE_RANK if degree in terms]
    return max(present, key=lambda degree: DEGREE_RANK[degree], default=None)


def component_to_payload(component: ScoreComponent) -> dict[str, object]:
    return {
        "key": component.key,
        "label": component.label,
        "weight": component.weight,
        "score": component.score,
        "state": component.state,
        "matchedTerms": list(component.matched_terms),
        "notFoundTerms": list(component.not_found_terms),
        "explanation": component.explanation,
    }
