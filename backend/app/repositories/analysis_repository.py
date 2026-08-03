import logging
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import AnalysisNotFoundError, AnalysisStorageError
from app.models.analysis_record import AnalysisRecord
from app.schemas.analysis import AnnouncementAnalysis
from app.schemas.history import AnalysisHistoryItem, StoredAnalysisResponse

logger = logging.getLogger(__name__)


class AnalysisRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, analysis: AnnouncementAnalysis) -> StoredAnalysisResponse:
        record = AnalysisRecord(
            id=str(uuid4()),
            company_name=analysis.source.company_name,
            exchange=analysis.source.exchange,
            symbol=analysis.source.symbol,
            security_code=analysis.source.security_code,
            announcement_id=analysis.source.announcement_id,
            announcement_title=analysis.title,
            category=analysis.announcement_category,
            announcement_published_at=analysis.source.published_at,
            result_json=analysis.model_dump_json(),
            created_at=datetime.now(UTC),
        )
        with self._session_factory() as session:
            try:
                session.add(record)
                session.commit()
            except SQLAlchemyError as error:
                session.rollback()
                logger.exception("Failed to save analysis history")
                raise AnalysisStorageError("Completed analysis could not be saved") from error
        return StoredAnalysisResponse(
            id=record.id,
            created_at=_as_utc(record.created_at),
            analysis=analysis,
        )

    def list_recent(self, limit: int) -> list[AnalysisHistoryItem]:
        with self._session_factory() as session:
            try:
                records = session.scalars(
                    select(AnalysisRecord).order_by(desc(AnalysisRecord.created_at)).limit(limit)
                ).all()
            except SQLAlchemyError as error:
                logger.exception("Failed to list analysis history")
                raise AnalysisStorageError("Analysis history is unavailable") from error
        return [_to_history_item(record) for record in records]

    def get(self, analysis_id: str) -> StoredAnalysisResponse:
        with self._session_factory() as session:
            try:
                record = session.get(AnalysisRecord, analysis_id)
            except SQLAlchemyError as error:
                logger.exception("Failed to retrieve analysis history item")
                raise AnalysisStorageError("Analysis history is unavailable") from error
        if record is None:
            raise AnalysisNotFoundError("Saved analysis was not found")
        try:
            analysis = AnnouncementAnalysis.model_validate_json(record.result_json)
        except ValidationError as error:
            logger.error("Stored analysis failed validation", extra={"analysis_id": record.id})
            raise AnalysisStorageError(
                "Saved analysis is invalid and cannot be reopened"
            ) from error
        return StoredAnalysisResponse(
            id=record.id,
            created_at=_as_utc(record.created_at),
            analysis=analysis,
        )


def _to_history_item(record: AnalysisRecord) -> AnalysisHistoryItem:
    try:
        return AnalysisHistoryItem(
            id=record.id,
            company_name=record.company_name,
            exchange=record.exchange,
            symbol=record.symbol,
            security_code=record.security_code,
            announcement_title=record.announcement_title,
            announcement_category=record.category,
            announcement_published_at=(
                _as_utc(record.announcement_published_at)
                if record.announcement_published_at
                else None
            ),
            created_at=_as_utc(record.created_at),
        )
    except ValidationError as error:
        logger.error("Stored history metadata failed validation", extra={"analysis_id": record.id})
        raise AnalysisStorageError("Saved analysis metadata is invalid") from error


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
