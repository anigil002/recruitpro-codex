from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

engine_kwargs: Dict[str, object] = {"future": True, "pool_pre_ping": True}
database_url = settings.database_url
url = make_url(database_url)

if url.get_backend_name() == "sqlite":
    connect_args: Dict[str, object] = {"check_same_thread": False}
    database_path = url.database or ""
    if database_path not in ("", ":memory:"):
        raw_path = Path(database_path)
        if not raw_path.is_absolute():
            raw_path = (Path.cwd() / raw_path).resolve()
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        url = url.set(database=str(raw_path))
    engine_kwargs["connect_args"] = connect_args

engine = create_engine(str(url), **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
Base = declarative_base()


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create database tables based on the current SQLAlchemy metadata."""

    # Import models lazily so that Base is defined before the mappings are
    # registered, preventing circular-import issues during application start.
    from . import models  # noqa: F401  (imported for side effects)

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
