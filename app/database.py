from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import APP_ROOT, get_settings

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
            raw_path = (APP_ROOT / raw_path).resolve()
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


def _rebuild_sqlite_table(table_name: str) -> None:
    """Recreate an SQLite table using the SQLAlchemy metadata definition."""

    # Import locally to avoid circular import at module import time
    from . import models  # noqa: F401  (imported for side effects)

    table = Base.metadata.tables[table_name]
    column_names = [column.name for column in table.columns]
    column_list = ", ".join(column_names)

    temp_table = f"{table_name}_tmp_nullable_fix"

    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        try:
            connection.execute(text(f"ALTER TABLE {table_name} RENAME TO {temp_table}"))
            table.create(bind=connection)
            connection.execute(
                text(
                    f"INSERT INTO {table_name} ({column_list}) "
                    f"SELECT {column_list} FROM {temp_table}"
                )
            )
            connection.execute(text(f"DROP TABLE {temp_table}"))
        finally:
            connection.execute(text("PRAGMA foreign_keys=ON"))


def _ensure_nullable_foreign_keys() -> None:
    """Ensure nullable foreign key columns match the SQLAlchemy models."""

    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Table -> columns that must allow NULL to match the ORM definition
    nullable_columns = {
        "projects": {"created_by"},
        "project_documents": {"uploaded_by"},
        "candidate_status_history": {"changed_by"},
        "communication_templates": {"created_by"},
        "outreach_runs": {"user_id"},
        "salary_benchmarks": {"created_by"},
        "admin_migration_logs": {"user_id"},
    }

    for table_name, columns in nullable_columns.items():
        if table_name not in existing_tables:
            continue

        column_info = {column["name"]: column for column in inspector.get_columns(table_name)}
        needs_rebuild = False
        for column_name in columns:
            info = column_info.get(column_name)
            if info is None:
                continue
            if not info.get("nullable", True):
                needs_rebuild = True
                break

        if needs_rebuild:
            _rebuild_sqlite_table(table_name)


def init_db() -> None:
    """Create database tables based on the current SQLAlchemy metadata."""

    # Import models lazily so that Base is defined before the mappings are
    # registered, preventing circular-import issues during application start.
    from . import models  # noqa: F401  (imported for side effects)

    _ensure_nullable_foreign_keys()
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
