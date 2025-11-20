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


def _add_qualifications_column() -> None:
    """Add qualifications column to positions table if it doesn't exist."""

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "positions" not in existing_tables:
        return

    column_info = {column["name"]: column for column in inspector.get_columns("positions")}
    if "qualifications" in column_info:
        return

    # Add the qualifications column
    with engine.begin() as connection:
        try:
            connection.execute(text("ALTER TABLE positions ADD COLUMN qualifications JSON"))
        except Exception:
            # Column might already exist or ALTER TABLE might not be supported
            pass


def _add_screening_run_columns() -> None:
    """Add new structured screening output columns to screening_runs table if they don't exist."""

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "screening_runs" not in existing_tables:
        return

    column_info = {column["name"]: column for column in inspector.get_columns("screening_runs")}

    # Define the new columns to add
    new_columns = {
        "overall_fit": "VARCHAR",
        "recommended_roles": "JSON",
        "key_strengths": "JSON",
        "potential_gaps": "JSON",
        "notice_period": "VARCHAR",
        "compliance_table": "JSON",
        "final_recommendation": "TEXT",
        "final_decision": "VARCHAR",
    }

    # Add each column if it doesn't exist
    with engine.begin() as connection:
        for column_name, column_type in new_columns.items():
            if column_name not in column_info:
                try:
                    connection.execute(text(f"ALTER TABLE screening_runs ADD COLUMN {column_name} {column_type}"))
                except Exception:
                    # Column might already exist or ALTER TABLE might not be supported
                    pass


def _add_candidate_created_by_column() -> None:
    """Add created_by column to candidates table if it doesn't exist."""

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "candidates" not in existing_tables:
        return

    column_info = {column["name"]: column for column in inspector.get_columns("candidates")}

    if "created_by" not in column_info:
        with engine.begin() as connection:
            try:
                connection.execute(text("ALTER TABLE candidates ADD COLUMN created_by VARCHAR"))
            except Exception:
                # Column might already exist or ALTER TABLE might not be supported
                pass


def _add_candidate_soft_delete_columns() -> None:
    """Add soft delete columns to candidates table per STANDARD-DB-005.

    Adds deleted_at and deleted_by for GDPR compliance.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "candidates" not in existing_tables:
        return

    column_info = {column["name"]: column for column in inspector.get_columns("candidates")}

    with engine.begin() as connection:
        if "deleted_at" not in column_info:
            try:
                connection.execute(text("ALTER TABLE candidates ADD COLUMN deleted_at DATETIME"))
            except Exception:
                pass

        if "deleted_by" not in column_info:
            try:
                connection.execute(text("ALTER TABLE candidates ADD COLUMN deleted_by VARCHAR"))
            except Exception:
                pass


def _ensure_nullable_foreign_keys() -> None:
    """Ensure nullable foreign key columns match the SQLAlchemy models."""

    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Table -> columns that must allow NULL to match the ORM definition
    # NOTE: projects.created_by and candidates.created_by removed per STANDARD-DB-003
    nullable_columns = {
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


def _fix_nullable_foreign_keys() -> None:
    """Migration to fix nullable foreign keys per STANDARD-DB-003.

    Makes projects.created_by and candidates.created_by non-nullable.
    Sets existing NULL values to a system user.
    """
    from .utils.security import generate_id

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "users" not in existing_tables:
        return

    with engine.begin() as connection:
        # Create or get system user for orphaned records
        result = connection.execute(text("SELECT user_id FROM users WHERE email = 'system@recruitpro.internal' LIMIT 1"))
        system_user = result.fetchone()

        if not system_user:
            # Create system user
            system_user_id = f"usr_{generate_id()}"
            connection.execute(
                text(
                    "INSERT INTO users (user_id, email, password_hash, name, role, created_at) "
                    "VALUES (:user_id, :email, :password_hash, :name, :role, :created_at)"
                ),
                {
                    "user_id": system_user_id,
                    "email": "system@recruitpro.internal",
                    "password_hash": "SYSTEM_USER_NO_LOGIN",
                    "name": "System User",
                    "role": "admin",
                    "created_at": "2025-01-01 00:00:00"
                }
            )
        else:
            system_user_id = system_user[0]

        # Update NULL created_by values in projects table
        if "projects" in existing_tables:
            connection.execute(
                text("UPDATE projects SET created_by = :system_user_id WHERE created_by IS NULL"),
                {"system_user_id": system_user_id}
            )

        # Update NULL created_by values in candidates table
        if "candidates" in existing_tables:
            connection.execute(
                text("UPDATE candidates SET created_by = :system_user_id WHERE created_by IS NULL"),
                {"system_user_id": system_user_id}
            )


def init_db() -> None:
    """Create database tables based on the current SQLAlchemy metadata."""

    # Import models lazily so that Base is defined before the mappings are
    # registered, preventing circular-import issues during application start.
    from . import models  # noqa: F401  (imported for side effects)

    _ensure_nullable_foreign_keys()
    _add_qualifications_column()
    _add_screening_run_columns()
    _add_candidate_created_by_column()
    _add_candidate_soft_delete_columns()  # STANDARD-DB-005
    _fix_nullable_foreign_keys()  # Fix NULL values before creating tables
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
