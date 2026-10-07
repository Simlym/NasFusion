#!/bin/bash
# ==============================================================================
# NasFusion Backend Entrypoint Script
# Waits for database -> Run migrations -> Start application
# ==============================================================================

set -eu

DEFAULT_PUID=1024
DEFAULT_PGID=100
TARGET_UID="${PUID:-$DEFAULT_PUID}"
TARGET_GID="${PGID:-$DEFAULT_PGID}"

validate_id() {
  value="$1"
  name="$2"
  case "$value" in
    ''|*[!0-9]*)
      echo "ERROR: $name must be a non-negative integer, got: $value"
      exit 1
      ;;
  esac
  if [ "$value" -gt 2147483647 ]; then
    echo "ERROR: $name is outside the supported range: $value"
    exit 1
  fi
}

validate_id "$TARGET_UID" "PUID"
validate_id "$TARGET_GID" "PGID"

run_as_app() {
  if [ "$(id -u)" -eq 0 ] && { [ "$TARGET_UID" -ne 0 ] || [ "$TARGET_GID" -ne 0 ]; }; then
    gosu "${TARGET_UID}:${TARGET_GID}" "$@"
  else
    "$@"
  fi
}

check_writable_as_app() {
  run_as_app sh -c 'test -w "$1"' sh "$1"
}

fix_ownership() {
  path="$1"
  if ! chown -hR "${TARGET_UID}:${TARGET_GID}" "$path"; then
    echo "WARNING: Unable to set ${TARGET_UID}:${TARGET_GID} ownership on $path"
    echo "The writable check will determine whether the filesystem permissions are already sufficient."
  fi
}

echo "======================================"
echo "NasFusion Backend Starting..."
echo "======================================"

# 显示关键环境变量（用于调试）
echo "=== 环境变量检查 ==="
echo "DB_TYPE: ${DB_TYPE:-未设置}"
echo "Runtime UID:GID: ${TARGET_UID}:${TARGET_GID}"
if [ "${DB_TYPE:-}" = "postgresql" ]; then
    echo "DB_POSTGRES_SERVER: ${DB_POSTGRES_SERVER:-未设置}"
    echo "DB_POSTGRES_USER: ${DB_POSTGRES_USER:-未设置}"
    echo "DB_POSTGRES_DB: ${DB_POSTGRES_DB:-未设置}"
fi
echo "========================"

# Wait for PostgreSQL to be ready
if [ "${DB_TYPE:-}" = "postgresql" ]; then
    echo "Waiting for PostgreSQL to be ready..."

    max_attempts=30
    attempt=0

    while ! nc -z "${DB_POSTGRES_SERVER:-postgres}" "${DB_POSTGRES_PORT:-5432}"; do
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

# 注：Redis 当前版本未启用，已移除等待逻辑

# Create necessary data directories. These are application-owned paths only;
# storage mounts such as /mnt/volumeN are deliberately never chowned here.
echo "Creating data directories..."
APP_WRITE_DIRS="/app/data/torrents /app/data/logs /app/data/cache /app/data/media /app/data/agent /app/data/home /app/uploads"

if [ "$(id -u)" -eq 0 ]; then
  mkdir -p /app/data/torrents /app/data/logs /app/data/cache/images \
           /app/data/media /app/data/agent /app/data/home /app/uploads

  echo "Preparing application directories for ${TARGET_UID}:${TARGET_GID}..."
  # Only adjust the data root itself and the explicitly listed application
  # directories. Other children (for example postgres) must retain their owner.
  chown -h "${TARGET_UID}:${TARGET_GID}" /app/data || true
  for dir in $APP_WRITE_DIRS; do
    fix_ownership "$dir"
  done
else
  echo "Running with an externally supplied non-root user; ownership changes are skipped."
  mkdir -p /app/data/torrents /app/data/logs /app/data/cache/images \
           /app/data/media /app/data/agent /app/data/home /app/uploads
  TARGET_UID="$(id -u)"
  TARGET_GID="$(id -g)"
fi

export HOME=/app/data/home

# Check and verify directory permissions
echo "Checking directory permissions..."

for dir in $APP_WRITE_DIRS; do
  if [ -d "$dir" ]; then
    # Check directory ownership
    DIR_UID=$(stat -c '%u' "$dir" 2>/dev/null || echo "0")
    DIR_GID=$(stat -c '%g' "$dir" 2>/dev/null || echo "0")
    if [ "$DIR_UID" != "$TARGET_UID" ] || [ "$DIR_GID" != "$TARGET_GID" ]; then
      echo "WARNING: $dir ownership mismatch (current: $DIR_UID:$DIR_GID, expected: $TARGET_UID:$TARGET_GID)"
    fi

    if ! check_writable_as_app "$dir"; then
      echo "ERROR: $dir is not writable by runtime user ${TARGET_UID}:${TARGET_GID}"
      echo "Set PUID/PGID to the host directory owner, or fix the host path permissions."
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
    run_as_app alembic upgrade head || {
        echo "WARNING: Database migration failed (continuing anyway)"
    }
else
    echo "No alembic.ini found, skipping migrations"
fi

echo "======================================"
echo "Starting Uvicorn server..."
echo "======================================"

# Execute the command as the configured unprivileged UID/GID.
if [ "$(id -u)" -eq 0 ] && { [ "$TARGET_UID" -ne 0 ] || [ "$TARGET_GID" -ne 0 ]; }; then
  exec gosu "${TARGET_UID}:${TARGET_GID}" "$@"
fi
exec "$@"
