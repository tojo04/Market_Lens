from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import AnalysisNotFoundError, AnalysisStorageError
from app.db.base import Base
from app.models.analysis_record import AnalysisRecord
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import REQUIRED_DISCLAIMER, AnnouncementAnalysis
from app.schemas.domain import PriceReaction


def make_analysis(title: str = "Quarterly results") -> AnnouncementAnalysis:
    return AnnouncementAnalysis(
        announcement_category="financial_results",
        title=title,
        summary="The company published quarterly results.",
        important_facts=[
            {
                "label": "Revenue",
                "value": "₹1,250 crore",
                "source_excerpt": "Revenue was ₹1,250 crore",
                "page_number": 1,
            }
        ],
        why_it_matters=["The filing updates reported performance."],
        positive_signals=["Reported revenue remained positive."],
        risks=["The filing is a point-in-time disclosure."],
        price_reaction=PriceReaction(status="unavailable", note="Market data unavailable"),
        confidence="high",
        limitations=["Only the supplied filing was analyzed."],
        source={
            "provider": "bse",
            "exchange": "BSE",
            "company_name": "Infosys Limited",
            "symbol": "INFY",
            "security_code": "500209",
            "announcement_id": "news-1",
            "announcement_url": "https://www.bseindia.com/announcement/news-1",
            "attachment_url": "https://www.bseindia.com/filing.pdf",
            "published_at": datetime(2026, 8, 3, 10, 30, tzinfo=UTC),
        },
        disclaimer=REQUIRED_DISCLAIMER,
    )


def repository_for(
    database_path: Path,
) -> tuple[AnalysisRepository, sessionmaker[Session]]:
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return AnalysisRepository(factory), factory


def test_save_list_and_retrieve_survive_new_repository(tmp_path: Path) -> None:
    database_path = tmp_path / "history.sqlite"
    repository, factory = repository_for(database_path)

    saved = repository.save(make_analysis())
    items = repository.list_recent(20)

    assert len(items) == 1
    assert items[0].id == saved.id
    assert items[0].company_name == "Infosys Limited"
    assert items[0].announcement_category == "financial_results"
    assert items[0].created_at.tzinfo is not None
    with factory() as session:
        record = session.get(AnalysisRecord, saved.id)
        assert record is not None
        assert "local_path" not in record.result_json
        assert "extraction_warnings" not in record.result_json

    reopened_repository, _ = repository_for(database_path)
    reopened = reopened_repository.get(saved.id)

    assert reopened.analysis == saved.analysis
    assert reopened.created_at.tzinfo is not None


def test_list_is_newest_first_and_bounded(tmp_path: Path) -> None:
    repository, _ = repository_for(tmp_path / "history.sqlite")
    repository.save(make_analysis("First result"))
    newest = repository.save(make_analysis("Newest result"))

    items = repository.list_recent(1)

    assert [item.id for item in items] == [newest.id]


def test_missing_analysis_id_is_controlled(tmp_path: Path) -> None:
    repository, _ = repository_for(tmp_path / "history.sqlite")

    with pytest.raises(AnalysisNotFoundError):
        repository.get("missing-id")


def test_invalid_stored_result_is_controlled_without_logging_content(
    tmp_path: Path,
) -> None:
    repository, factory = repository_for(tmp_path / "history.sqlite")
    saved = repository.save(make_analysis())
    with factory() as session:
        record = session.get(AnalysisRecord, saved.id)
        assert record is not None
        record.result_json = '{"unexpected":"content"}'
        session.commit()

    with pytest.raises(AnalysisStorageError, match="invalid"):
        repository.get(saved.id)
