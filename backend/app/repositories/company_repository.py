import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.core.exceptions import AmbiguousCompanyError, CompanyNotFoundError
from app.schemas.domain import CompanyMatch, Exchange

NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
DEFAULT_COMPANY_MASTER = Path(__file__).parents[1] / "data" / "company_master.json"


def normalize_company_text(value: str) -> str:
    return NON_ALPHANUMERIC.sub("", value.casefold())


class CompanyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str
    aliases: list[str]
    security_code: str
    symbol: str
    company_id: str
    exchange: Exchange

    def to_match(self) -> CompanyMatch:
        return CompanyMatch(provider="bse", **self.model_dump(exclude={"aliases"}))


@dataclass(frozen=True)
class RankedCompany:
    score: float
    record: CompanyRecord


class CompanyRepository:
    def __init__(self, records: list[CompanyRecord]) -> None:
        self._records = records

    @classmethod
    def from_json(cls, path: Path = DEFAULT_COMPANY_MASTER) -> "CompanyRepository":
        raw_records = json.loads(path.read_text(encoding="utf-8"))
        return cls([CompanyRecord.model_validate(item) for item in raw_records])

    def search(self, query: str, limit: int = 10) -> list[CompanyMatch]:
        normalized_query = normalize_company_text(query)
        if not normalized_query:
            raise ValueError("Search query cannot be empty")
        bounded_limit = min(max(limit, 1), 10)
        ranked = [
            RankedCompany(score=score, record=record)
            for record in self._records
            if (score := self._score(record, normalized_query)) is not None
        ]
        ranked.sort(key=lambda item: (-item.score, item.record.company_name))
        return [item.record.to_match() for item in ranked[:bounded_limit]]

    def get_by_id(self, company_id: str) -> CompanyMatch:
        for record in self._records:
            if record.company_id == company_id:
                return record.to_match()
        raise CompanyNotFoundError(f"Unsupported company ID: {company_id}")

    def resolve_unique(self, query: str) -> CompanyMatch:
        matches = self.search(query)
        if not matches:
            raise CompanyNotFoundError(f"No supported company matched: {query}")
        if len(matches) > 1:
            normalized_query = normalize_company_text(query)
            exact = [match for match in matches if self._is_exact(match, normalized_query)]
            if len(exact) != 1:
                raise AmbiguousCompanyError(f"Multiple companies matched: {query}")
            return exact[0]
        return matches[0]

    @staticmethod
    def _is_exact(match: CompanyMatch, query: str) -> bool:
        return query in {
            normalize_company_text(match.company_name),
            normalize_company_text(match.security_code or ""),
            normalize_company_text(match.symbol or ""),
        }

    @staticmethod
    def _score(record: CompanyRecord, query: str) -> float | None:
        names = [record.company_name, *record.aliases]
        normalized_names = [normalize_company_text(name) for name in names]
        identifiers = {
            normalize_company_text(record.security_code),
            normalize_company_text(record.symbol),
        }
        if query in identifiers or query in normalized_names:
            return 100.0
        if any(name.startswith(query) for name in normalized_names):
            return 85.0
        if any(query in name for name in normalized_names):
            return 75.0
        similarity = max(SequenceMatcher(None, query, name).ratio() for name in normalized_names)
        return similarity * 70 if similarity >= 0.72 else None
