from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base


@lru_cache
def get_engine() -> Engine:
    database_url = get_settings().database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def init_database() -> None:
    from app.models.analysis_record import AnalysisRecord

    _ = AnalysisRecord
    Base.metadata.create_all(get_engine())
