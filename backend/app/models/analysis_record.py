from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(3), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(30))
    security_code: Mapped[str | None] = mapped_column(String(20))
    announcement_id: Mapped[str | None] = mapped_column(String(200))
    announcement_title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    announcement_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
