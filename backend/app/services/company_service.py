from app.repositories.company_repository import CompanyRepository
from app.schemas.domain import CompanyMatch


class CompanyService:
    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    def search(self, query: str, limit: int = 10) -> list[CompanyMatch]:
        return self._repository.search(query, limit)

    def get_by_id(self, company_id: str) -> CompanyMatch:
        return self._repository.get_by_id(company_id)
