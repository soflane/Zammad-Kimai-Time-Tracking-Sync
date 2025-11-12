#!/bin/sh
set -e

echo "=========================================="
echo "Zammad-Kimai Sync Backend Starting..."
echo "=========================================="

# Wait for database to be ready
echo "Waiting for database to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 2
done

echo "Database is ready!"

# Check if alembic_version table exists to determine if migrations are needed
echo "Checking database migration status..."
TABLE_EXISTS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='alembic_version';" 2>/dev/null || echo "0")

if [ "$TABLE_EXISTS" = "0" ]; then
    echo "No migration history found. Running initial database migrations..."
    alembic upgrade head
    echo "Migrations completed successfully!"
else
    echo "Migration history exists. Checking for pending migrations..."
    alembic upgrade head
    echo "Database is up to date!"
fi

echo "=========================================="
echo "Starting FastAPI application..."
echo "=========================================="

# Start the application
LOG_LEVEL=$(echo ${LOG_LEVEL:-info} | tr '[:upper:]' '[:lower:]')
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level $LOG_LEVEL
