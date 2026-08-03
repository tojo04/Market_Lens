import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.analysis import SUPPORTED_CATEGORIES
from evaluation.run_evaluation import (
    CASES_PATH,
    EvaluationCase,
    evaluate_case,
    evaluate_cases,
    load_cases,
)


def check_map(case: EvaluationCase) -> dict[str, bool]:
    return {check.name: check.passed for check in evaluate_case(case).checks}


def test_recorded_evaluation_set_covers_every_category_and_passes() -> None:
    cases = load_cases()
    results = evaluate_cases(cases)

    assert len(cases) == 8
    assert {case.expected_category for case in cases} == SUPPORTED_CATEGORIES
    assert all(result.passed for result in results)
    assert sum(len(result.checks) for result in results) == 96


def test_deterministic_checks_detect_corrupted_candidate_output() -> None:
    case = load_cases()[0]
    analysis = case.analysis
    corrupted_price = analysis.price_reaction.model_copy(update={"percentage_change": 99.0})
    corrupted_source = analysis.source.model_copy(
        update={
            "company_name": "Wrong Company",
            "exchange": "NSE",
            "announcement_id": "wrong-id",
            "published_at": analysis.source.published_at.replace(day=2),
        }
    )
    corrupted_fact = analysis.important_facts[0].model_copy(
        update={"source_excerpt": "Absent excerpt"}
    )
    corrupted_analysis = analysis.model_copy(
        update={
            "announcement_category": "dividend",
            "summary": "Investors should buy the stock after a fabricated 999% increase.",
            "important_facts": [corrupted_fact],
            "why_it_matters": ["Duplicate bullet", "Duplicate bullet"],
            "positive_signals": [],
            "price_reaction": corrupted_price,
            "source": corrupted_source,
            "disclaimer": "Changed disclaimer",
        }
    )
    checks = check_map(case.model_copy(update={"analysis": corrupted_analysis}))

    assert checks["required_disclaimer"] is False
    assert checks["no_trade_recommendation"] is False
    assert checks["price_arithmetic_correct"] is False
    assert checks["fact_citations_present"] is False
    assert checks["numeric_values_grounded"] is False
    assert checks["no_duplicate_bullets"] is False
    assert checks["required_sections_nonempty"] is False
    assert checks["category_correct"] is False
    assert checks["company_correct"] is False
    assert checks["date_correct"] is False
    assert checks["source_attribution_correct"] is False


def test_invalid_case_schema_is_rejected_before_evaluation(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid-cases.json"
    invalid_path.write_text(json.dumps([{"case_id": "incomplete"}]), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_cases(invalid_path)


def test_human_review_template_matches_case_ids() -> None:
    template_path = CASES_PATH.with_name("human_review_template.csv")
    lines = template_path.read_text(encoding="utf-8").splitlines()

    assert lines[0] == (
        "case_id,category_correct,facts_correct,numbers_correct,no_hallucination,"
        "neutral_language,source_correct,limitations_correct,notes"
    )
    assert {line.split(",", 1)[0] for line in lines[1:]} == {case.case_id for case in load_cases()}
