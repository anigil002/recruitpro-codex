#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

This script migrates all data from an existing SQLite database to PostgreSQL.
It handles all tables, preserves relationships, and validates the migration.

Usage:
    python scripts/migrate_sqlite_to_postgres.py \
        --sqlite sqlite:///./data/recruitpro.db \
        --postgres postgresql://recruitpro:password@localhost:5432/recruitpro \
        [--skip-existing]

Prerequisites:
    1. PostgreSQL database must exist and be accessible
    2. Run: createdb -U postgres recruitpro
    3. Or: CREATE DATABASE recruitpro;

Options:
    --sqlite: SQLite database URL (source)
    --postgres: PostgreSQL database URL (target)
    --skip-existing: Skip tables that already exist in PostgreSQL
    --dry-run: Show what would be migrated without actually migrating
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base


def get_table_order() -> List[str]:
    """
    Return tables in dependency order (parents before children).
    This ensures foreign key constraints are satisfied during migration.
    """
    return [
        "users",
        "projects",
        "positions",
        "candidates",
        "candidate_status_history",
        "screening_runs",
        "project_documents",
        "communication_templates",
        "outreach_runs",
        "salary_benchmarks",
        "admin_migration_logs",
        "activity_logs",
    ]


def count_records(engine: Engine, table_name: str) -> int:
    """Count records in a table."""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar() or 0


def migrate_table(
    source_engine: Engine,
    target_engine: Engine,
    table_name: str,
    batch_size: int = 500,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Migrate a single table from source to target database.

    Returns migration stats (count, errors, etc.)
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating table: {table_name}")

    # Get column names
    inspector = inspect(source_engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    column_list = ", ".join(columns)
    placeholders = ", ".join([f":{col}" for col in columns])

    # Count source records
    source_count = count_records(source_engine, table_name)
    print(f"  Source records: {source_count}")

    if source_count == 0:
        print(f"  ✓ Skipped (empty table)")
        return {"table": table_name, "migrated": 0, "errors": 0}

    if dry_run:
        print(f"  [DRY RUN] Would migrate {source_count} records")
        return {"table": table_name, "migrated": 0, "errors": 0}

    # Fetch all records from source
    with source_engine.connect() as source_conn:
        result = source_conn.execute(text(f"SELECT {column_list} FROM {table_name}"))
        rows = result.fetchall()

    # Insert records into target in batches
    migrated = 0
    errors = 0

    with target_engine.begin() as target_conn:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            for row in batch:
                try:
                    # Convert row to dict
                    row_dict = dict(zip(columns, row))

                    # Insert into target
                    target_conn.execute(
                        text(f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"),
                        row_dict
                    )
                    migrated += 1
                except Exception as e:
                    errors += 1
                    print(f"  ✗ Error migrating row: {e}")
                    if errors > 10:
                        print(f"  ✗ Too many errors, stopping migration for {table_name}")
                        return {"table": table_name, "migrated": migrated, "errors": errors}

    # Verify target count
    target_count = count_records(target_engine, table_name)
    print(f"  Target records: {target_count}")

    if target_count == source_count:
        print(f"  ✓ Migration successful ({migrated} records)")
    else:
        print(f"  ⚠ Count mismatch: source={source_count}, target={target_count}")
        errors += 1

    return {"table": table_name, "migrated": migrated, "errors": errors}


def create_target_schema(target_engine: Engine):
    """Create all tables in the target database using SQLAlchemy models."""
    print("\nCreating target database schema...")

    # Import all models so they're registered with Base.metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=target_engine)
    print("✓ Schema created successfully")


def verify_migration(source_engine: Engine, target_engine: Engine, table_names: List[str]):
    """Verify that all data was migrated successfully."""
    print("\n" + "=" * 80)
    print("MIGRATION VERIFICATION")
    print("=" * 80)

    all_ok = True

    for table_name in table_names:
        source_count = count_records(source_engine, table_name)
        target_count = count_records(target_engine, table_name)

        status = "✓" if source_count == target_count else "✗"
        print(f"{status} {table_name:30} source={source_count:6} target={target_count:6}")

        if source_count != target_count:
            all_ok = False

    print("=" * 80)
    if all_ok:
        print("✓ All tables migrated successfully!")
    else:
        print("✗ Migration verification failed - some tables have mismatched counts")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite database to PostgreSQL")
    parser.add_argument(
        "--sqlite",
        default="sqlite:///./data/recruitpro.db",
        help="SQLite database URL (source)"
    )
    parser.add_argument(
        "--postgres",
        default="postgresql://recruitpro:password@localhost:5432/recruitpro",
        help="PostgreSQL database URL (target)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip tables that already have data in PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("SQLite to PostgreSQL Migration Tool")
    print("=" * 80)
    print(f"Source: {args.sqlite}")
    print(f"Target: {args.postgres}")
    print(f"Skip existing: {args.skip_existing}")
    print(f"Dry run: {args.dry_run}")

    # Create engines
    print("\nConnecting to databases...")
    try:
        source_engine = create_engine(args.sqlite)
        target_engine = create_engine(args.postgres)

        # Test connections
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Connected to SQLite")

        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"\n✗ Failed to connect to database: {e}")
        return 1

    # Create target schema
    if not args.dry_run:
        try:
            create_target_schema(target_engine)
        except Exception as e:
            print(f"\n✗ Failed to create schema: {e}")
            return 1

    # Get tables to migrate
    table_names = get_table_order()

    # Check which tables exist in source
    source_inspector = inspect(source_engine)
    existing_source_tables = set(source_inspector.get_table_names())

    tables_to_migrate = [t for t in table_names if t in existing_source_tables]

    print(f"\nTables to migrate: {len(tables_to_migrate)}")
    for table in tables_to_migrate:
        print(f"  - {table}")

    # Migrate each table
    results = []
    for table_name in tables_to_migrate:
        if args.skip_existing:
            target_count = count_records(target_engine, table_name)
            if target_count > 0:
                print(f"\nSkipping {table_name} (already has {target_count} records)")
                continue

        result = migrate_table(source_engine, target_engine, table_name, dry_run=args.dry_run)
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)

    if args.dry_run:
        print("[DRY RUN] No data was actually migrated")

    total_migrated = sum(r["migrated"] for r in results)
    total_errors = sum(r["errors"] for r in results)

    print(f"Tables processed: {len(results)}")
    print(f"Total records migrated: {total_migrated}")
    print(f"Total errors: {total_errors}")

    # Verify migration
    if not args.dry_run and total_errors == 0:
        success = verify_migration(source_engine, target_engine, tables_to_migrate)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
