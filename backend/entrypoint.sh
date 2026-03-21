#!/bin/bash
# ==============================================================================
# NasFusion Backend Entrypoint Script
# Waits for database -> Run migrations -> Start application
# ==============================================================================

set -e

echo "======================================"
echo "NasFusion Backend Starting..."
echo "======================================"

# 显示关键环境变量（用于调试）
echo "=== 环境变量检查 ==="
echo "DB_TYPE: ${DB_TYPE:-未设置}"
if [ "$DB_TYPE" = "postgresql" ]; then
    echo "DB_POSTGRES_SERVER: ${DB_POSTGRES_SERVER:-未设置}"
    echo "DB_POSTGRES_USER: ${DB_POSTGRES_USER:-未设置}"
    echo "DB_POSTGRES_DB: ${DB_POSTGRES_DB:-未设置}"
fi
echo "========================"

# Wait for PostgreSQL to be ready
if [ "$DB_TYPE" = "postgresql" ]; then
    echo "Waiting for PostgreSQL to be ready..."

    max_attempts=30
    attempt=0

    while ! nc -z ${DB_POSTGRES_SERVER:-postgres} ${DB_POSTGRES_PORT:-5432}; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "ERROR: PostgreSQL is not available after $max_attempts attempts"
            exit 1
        fi
        echo "PostgreSQL is unavailable - sleeping (attempt $attempt/$max_attempts)"
        sleep 2
    done

    echo "PostgreSQL is ready!"
fi

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."

max_attempts=30
attempt=0

while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "WARNING: Redis is not available after $max_attempts attempts (continuing anyway)"
        break
    fi
    echo "Redis is unavailable - sleeping (attempt $attempt/$max_attempts)"
    sleep 2
done

if nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; then
    echo "Redis is ready!"
fi

# Create necessary data directories
echo "Creating data directories..."
mkdir -p /app/data/torrents /app/data/logs /app/data/cache/images

# Check and verify directory permissions
echo "Checking directory permissions..."

for dir in /app/data/torrents /app/data/logs /app/data/cache; do
  if [ -d "$dir" ]; then
    # Check directory ownership
    DIR_UID=$(stat -c '%u' "$dir" 2>/dev/null || echo "0")
    DIR_GID=$(stat -c '%g' "$dir" 2>/dev/null || echo "0")
    CURRENT_UID=$(id -u)
    CURRENT_GID=$(id -g)

    if [ "$DIR_UID" != "$CURRENT_UID" ] || [ "$DIR_GID" != "$CURRENT_GID" ]; then
      echo "WARNING: $dir ownership mismatch (current: $DIR_UID:$DIR_GID, expected: $CURRENT_UID:$CURRENT_GID)"
      echo "Please ensure PUID/PGID matches your host user or run: chown -R ${PUID:-1024}:${PGID:-100} <host_path>"
    fi

    # Ensure writable (permissive mode)
    if [ ! -w "$dir" ]; then
      echo "ERROR: $dir is not writable by current user ($(id -un))"
      echo "Please fix permissions on host: sudo chown -R ${PUID:-1024}:${PGID:-100} <host_path>"
      exit 1
    fi
  else
    echo "Creating directory: $dir"
    mkdir -p "$dir"
  fi
done

echo "Directory permissions verified"

# Run database migrations (if using Alembic)
if [ -f "alembic.ini" ]; then
    echo "Running database migrations..."
    alembic upgrade head || {
        echo "WARNING: Database migration failed (continuing anyway)"
    }
else
    echo "No alembic.ini found, skipping migrations"
fi

echo "======================================"
echo "Starting Uvicorn server..."
echo "======================================"

# Execute the command passed to the script (default is uvicorn)
exec "$@"
