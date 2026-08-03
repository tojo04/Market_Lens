from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_analysis_repository
from app.db.base import Base
from app.main import app
from app.models.analysis_record import AnalysisRecord
from app.repositories.analysis_repository import AnalysisRepository
from tests.unit.test_analysis_repository import make_analysis

client = TestClient(app)


def make_repository(database_path: Path) -> tuple[AnalysisRepository, sessionmaker[Session]]:
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return AnalysisRepository(factory), factory


def request_with_repository(
    repository: AnalysisRepository,
    path: str,
) -> httpx.Response:
    app.dependency_overrides[get_analysis_repository] = lambda: repository
    try:
        return client.get(path)
    finally:
        app.dependency_overrides.clear()


def test_history_list_and_detail_endpoints(tmp_path: Path) -> None:
    repository, _ = make_repository(tmp_path / "history.sqlite")
    saved = repository.save(make_analysis())

    list_response = request_with_repository(repository, "/api/analyses?limit=10")
    detail_response = request_with_repository(repository, f"/api/analyses/{saved.id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == saved.id
    assert detail_response.status_code == 200
    assert detail_response.json()["analysis"]["title"] == "Quarterly results"


def test_history_limit_is_validated(tmp_path: Path) -> None:
    repository, _ = make_repository(tmp_path / "history.sqlite")

    response = request_with_repository(repository, "/api/analyses?limit=51")

    assert response.status_code == 422


def test_missing_history_id_returns_typed_error(tmp_path: Path) -> None:
    repository, _ = make_repository(tmp_path / "history.sqlite")

    response = request_with_repository(repository, "/api/analyses/missing-id")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_not_found"
    assert response.json()["error"]["request_id"]


def test_invalid_stored_analysis_returns_typed_error(tmp_path: Path) -> None:
    repository, factory = make_repository(tmp_path / "history.sqlite")
    saved = repository.save(make_analysis())
    with factory() as session:
        record = session.get(AnalysisRecord, saved.id)
        assert record is not None
        record.result_json = "not-json"
        session.commit()

    response = request_with_repository(repository, f"/api/analyses/{saved.id}")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "analysis_storage_error"
