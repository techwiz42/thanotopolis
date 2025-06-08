#!/bin/bash
# Production startup script for Thanotopolis backend
# Supports 100+ concurrent users

echo "Starting Thanotopolis backend in production mode..."

# Export environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application with Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn app.main:app \
    --config gunicorn_config.py \
    --log-level info \
    --access-logfile - \
    --error-logfile -