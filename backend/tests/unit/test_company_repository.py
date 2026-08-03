import pytest

from app.core.exceptions import AmbiguousCompanyError
from app.repositories.company_repository import CompanyRepository


@pytest.fixture
def repository() -> CompanyRepository:
    return CompanyRepository.from_json()


@pytest.mark.parametrize(
    ("query", "expected_symbol"),
    [
        ("Infosys Limited", "INFY"),
        ("infosys limited", "INFY"),
        ("500209", "INFY"),
        ("INFY", "INFY"),
        ("Airtel", "BHARTIARTL"),
        ("Infosis", "INFY"),
    ],
)
def test_search_match_types(
    repository: CompanyRepository,
    query: str,
    expected_symbol: str,
) -> None:
    matches = repository.search(query)

    assert matches[0].symbol == expected_symbol


def test_search_returns_no_match(repository: CompanyRepository) -> None:
    assert repository.search("Not A Listed Company") == []


def test_ambiguous_name_is_not_auto_resolved(repository: CompanyRepository) -> None:
    matches = repository.search("Tata")

    assert len(matches) > 1
    with pytest.raises(AmbiguousCompanyError):
        repository.resolve_unique("Tata")


def test_result_limit_is_enforced(repository: CompanyRepository) -> None:
    assert len(repository.search("Limited", limit=100)) <= 10


def test_empty_query_is_rejected(repository: CompanyRepository) -> None:
    with pytest.raises(ValueError, match="empty"):
        repository.search("   ")
