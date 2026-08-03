import json
import re
from argparse import ArgumentParser
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from app.schemas.analysis import (
    PROHIBITED_RECOMMENDATIONS,
    REQUIRED_DISCLAIMER,
    AnnouncementAnalysis,
    AnnouncementCategory,
)
from app.schemas.domain import DomainModel, Exchange

CASES_PATH = Path(__file__).with_name("cases.json")
NUMERIC_TOKEN = re.compile(r"\d[\d,.]*(?:%|:\d+)?")


class EvaluationPage(DomainModel):
    page_number: int = Field(ge=1)
    text: str = Field(min_length=1)


class EvaluationCase(DomainModel):
    case_id: str = Field(min_length=1)
    expected_category: AnnouncementCategory
    expected_company_name: str = Field(min_length=1)
    expected_announcement_date: date
    expected_exchange: Exchange
    expected_announcement_id: str = Field(min_length=1)
    source_pages: list[EvaluationPage] = Field(min_length=1)
    analysis: AnnouncementAnalysis

    @model_validator(mode="after")
    def page_numbers_are_unique(self) -> Self:
        page_numbers = [page.page_number for page in self.source_pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("evaluation page numbers must be unique")
        return self


class CheckResult(DomainModel):
    name: str
    passed: bool
    detail: str | None = None


class CaseResult(DomainModel):
    case_id: str
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def load_cases(path: Path = CASES_PATH) -> list[EvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationCase.model_validate(raw_case) for raw_case in raw_cases]


def evaluate_case(case: EvaluationCase) -> CaseResult:
    analysis = case.analysis
    source_by_page = {page.page_number: page.text for page in case.source_pages}
    source_text = "\n".join(source_by_page.values())
    checks = [
        CheckResult(name="schema_valid", passed=True),
        _check(
            "required_disclaimer",
            analysis.disclaimer == REQUIRED_DISCLAIMER,
            "Required educational disclaimer is missing or changed",
        ),
        _check(
            "no_trade_recommendation",
            not PROHIBITED_RECOMMENDATIONS.search(_user_facing_text(analysis)),
            "Prohibited buy/sell/hold language was detected",
        ),
        _price_arithmetic_check(analysis),
        _fact_citation_check(analysis, source_by_page),
        _numeric_grounding_check(analysis, source_text),
        _duplicate_bullet_check(analysis),
        _nonempty_section_check(analysis),
        _check(
            "category_correct",
            analysis.announcement_category == case.expected_category,
            "Category does not match the reviewed expectation",
        ),
        _check(
            "company_correct",
            analysis.source.company_name == case.expected_company_name,
            "Company does not match the reviewed expectation",
        ),
        _check(
            "date_correct",
            analysis.source.published_at is not None
            and analysis.source.published_at.date() == case.expected_announcement_date,
            "Announcement date does not match the reviewed expectation",
        ),
        _check(
            "source_attribution_correct",
            analysis.source.exchange == case.expected_exchange
            and analysis.source.announcement_id == case.expected_announcement_id
            and bool(analysis.source.provider),
            "Provider, exchange, or announcement ID is missing or incorrect",
        ),
    ]
    return CaseResult(case_id=case.case_id, checks=checks)


def evaluate_cases(cases: Iterable[EvaluationCase]) -> list[CaseResult]:
    return [evaluate_case(case) for case in cases]


def _check(name: str, passed: bool, failure_detail: str) -> CheckResult:
    return CheckResult(name=name, passed=passed, detail=None if passed else failure_detail)


def _price_arithmetic_check(analysis: AnnouncementAnalysis) -> CheckResult:
    price = analysis.price_reaction
    if price.status == "unavailable":
        return _check(
            "price_arithmetic_correct",
            price.percentage_change is None,
            "Unavailable price reaction contains a calculated percentage",
        )
    if price.previous_close in (None, 0) or price.next_close is None:
        return _check(
            "price_arithmetic_correct",
            False,
            "Available price reaction lacks usable closes",
        )
    expected = round(((price.next_close - price.previous_close) / price.previous_close) * 100, 2)
    return _check(
        "price_arithmetic_correct",
        price.percentage_change is not None and abs(price.percentage_change - expected) <= 0.01,
        f"Expected {expected:.2f}% from the stored closes",
    )


def _fact_citation_check(
    analysis: AnnouncementAnalysis,
    source_by_page: dict[int, str],
) -> CheckResult:
    valid = bool(analysis.important_facts)
    for fact in analysis.important_facts:
        page_text = source_by_page.get(fact.page_number or -1, "")
        valid = valid and bool(fact.source_excerpt) and fact.source_excerpt in page_text
    return _check(
        "fact_citations_present",
        valid,
        "Every important fact must cite an excerpt on its stated page",
    )


def _numeric_grounding_check(
    analysis: AnnouncementAnalysis,
    source_text: str,
) -> CheckResult:
    evidence_text = "\n".join(
        [
            analysis.title,
            analysis.summary,
            *(fact.value for fact in analysis.important_facts),
            *analysis.why_it_matters,
            *analysis.positive_signals,
            *analysis.risks,
            *analysis.limitations,
        ]
    )
    tokens = set(NUMERIC_TOKEN.findall(evidence_text))
    missing = sorted(token for token in tokens if token not in source_text)
    return _check(
        "numeric_values_grounded",
        not missing,
        f"Numeric tokens absent from source pages: {', '.join(missing)}",
    )


def _duplicate_bullet_check(analysis: AnnouncementAnalysis) -> CheckResult:
    sections = {
        "why_it_matters": analysis.why_it_matters,
        "positive_signals": analysis.positive_signals,
        "risks": analysis.risks,
        "limitations": analysis.limitations,
    }
    duplicate_sections = [
        name
        for name, items in sections.items()
        if len({item.casefold().strip() for item in items}) != len(items)
    ]
    return _check(
        "no_duplicate_bullets",
        not duplicate_sections,
        f"Duplicate bullets found in: {', '.join(duplicate_sections)}",
    )


def _nonempty_section_check(analysis: AnnouncementAnalysis) -> CheckResult:
    empty_sections = [
        name
        for name, items in {
            "important_facts": analysis.important_facts,
            "why_it_matters": analysis.why_it_matters,
            "positive_signals": analysis.positive_signals,
            "risks": analysis.risks,
            "limitations": analysis.limitations,
        }.items()
        if not items
    ]
    return _check(
        "required_sections_nonempty",
        not empty_sections,
        f"Empty sections found: {', '.join(empty_sections)}",
    )


def _user_facing_text(analysis: AnnouncementAnalysis) -> str:
    return "\n".join(
        [
            analysis.title,
            analysis.summary,
            *(fact.value for fact in analysis.important_facts),
            *analysis.why_it_matters,
            *analysis.positive_signals,
            *analysis.risks,
            *analysis.limitations,
        ]
    )


def main() -> int:
    parser = ArgumentParser(description="Run deterministic MarketLens evaluation checks")
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--json", action="store_true", dest="json_output")
    arguments = parser.parse_args()
    results = evaluate_cases(load_cases(arguments.cases))
    passed_cases = sum(result.passed for result in results)
    total_checks = sum(len(result.checks) for result in results)
    passed_checks = sum(check.passed for result in results for check in result.checks)
    report = {
        "status": "passed" if passed_cases == len(results) else "failed",
        "cases_passed": passed_cases,
        "cases_total": len(results),
        "checks_passed": passed_checks,
        "checks_total": total_checks,
        "results": [result.model_dump() | {"passed": result.passed} for result in results],
    }
    if arguments.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Evaluation {report['status']}: {passed_cases}/{len(results)} cases, "
            f"{passed_checks}/{total_checks} checks"
        )
        for result in results:
            failures = [check for check in result.checks if not check.passed]
            if failures:
                print(f"- {result.case_id}")
                for failure in failures:
                    print(f"  {failure.name}: {failure.detail}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
