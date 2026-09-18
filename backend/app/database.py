from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()
settings.ensure_directories()

_db_filename = settings.database_url.rsplit("/", 1)[-1]
_database_url = f"sqlite:///{settings.data_path / _db_filename}"

engine = create_engine(
    _database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401 register mappers

    Base.metadata.create_all(bind=engine)
