#!/bin/bash
set -e

echo "Starting services..."

# Start MinIO in the background
mkdir -p /data/minio
echo "Starting MinIO..."
minio server /data/minio --address ":9000" --console-address ":9001" > /var/log/minio.log 2>&1 &

# Wait for MinIO to be ready
echo "Waiting for MinIO to start..."
MAX_RETRIES=30
COUNT=0
until curl -s http://localhost:9000/minio/health/live || [ $COUNT -eq $MAX_RETRIES ]; do
  sleep 1
  COUNT=$((COUNT + 1))
done

if [ $COUNT -eq $MAX_RETRIES ]; then
  echo "MinIO failed to start"
  exit 1
fi

echo "MinIO is ready."

# Configure mc
echo "Configuring MinIO client..."
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/videos --ignore-existing

# Start Temporal Dev Server if requested or as default
# Note: In a production environment on vast.ai, you might want a persistent Temporal cluster,
# but for standalone Docker, start-dev is useful.
echo "Starting Temporal dev server..."
temporal server start-dev --ip 0.0.0.0 > /var/log/temporal.log 2>&1 &

# Wait for Temporal
echo "Waiting for Temporal..."
COUNT=0
until temporal operator cluster health || [ $COUNT -eq $MAX_RETRIES ]; do
  sleep 1
  COUNT=$((COUNT + 1))
done

echo "Services started successfully."

# Execute the main command
exec "$@"
