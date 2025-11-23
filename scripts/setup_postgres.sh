#!/bin/bash
# PostgreSQL Setup Script for RecruitPro
#
# This script sets up a local PostgreSQL database for development/production use.
# Run this script before migrating from SQLite.

set -e  # Exit on error

DB_NAME="${1:-recruitpro}"
DB_USER="${2:-recruitpro}"
DB_PASSWORD="${3:-password}"

echo "=========================================="
echo "PostgreSQL Setup for RecruitPro"
echo "=========================================="
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Password: $DB_PASSWORD"
echo ""

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "ERROR: PostgreSQL is not running"
    echo "Start PostgreSQL with: sudo service postgresql start"
    exit 1
fi

echo "✓ PostgreSQL is running"

# Create user if it doesn't exist
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    echo "✓ User '$DB_USER' already exists"
else
    echo "Creating user '$DB_USER'..."
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    echo "✓ User created"
fi

# Create database if it doesn't exist
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "✓ Database '$DB_NAME' already exists"
else
    echo "Creating database '$DB_NAME'..."
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo "✓ Database created"
fi

# Grant privileges
echo "Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
echo "✓ Privileges granted"

# Update .env file
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo ""
    echo "Updating $ENV_FILE..."

    # Backup existing .env
    cp "$ENV_FILE" "${ENV_FILE}.backup"

    # Update DATABASE_URL
    NEW_DB_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"

    if grep -q "^RECRUITPRO_DATABASE_URL=" "$ENV_FILE"; then
        sed -i "s|^RECRUITPRO_DATABASE_URL=.*|RECRUITPRO_DATABASE_URL=$NEW_DB_URL|" "$ENV_FILE"
        echo "✓ Updated RECRUITPRO_DATABASE_URL in $ENV_FILE"
    else
        echo "RECRUITPRO_DATABASE_URL=$NEW_DB_URL" >> "$ENV_FILE"
        echo "✓ Added RECRUITPRO_DATABASE_URL to $ENV_FILE"
    fi

    echo "✓ Backup saved to ${ENV_FILE}.backup"
else
    echo ""
    echo "⚠ No .env file found. Creating from .env.example..."
    cp .env.example .env
    NEW_DB_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
    sed -i "s|^RECRUITPRO_DATABASE_URL=.*|RECRUITPRO_DATABASE_URL=$NEW_DB_URL|" .env
    echo "✓ Created .env with PostgreSQL configuration"
fi

echo ""
echo "=========================================="
echo "✓ PostgreSQL setup complete!"
echo "=========================================="
echo ""
echo "Connection URL:"
echo "postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "Next steps:"
echo "1. Run migration: python scripts/migrate_sqlite_to_postgres.py"
echo "2. Start application: uvicorn app.main:app --reload"
echo ""
