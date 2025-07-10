#!/bin/bash

# Wait for MinIO to be ready and create bucket
echo "Waiting for MinIO to be ready..."
until curl -f http://minio:9000/minio/health/live; do
  echo "MinIO not ready yet, waiting..."
  sleep 2
done

echo "Creating snapshots bucket..."
aws --endpoint-url http://minio:9000 s3 mb s3://snapshots || echo "Bucket already exists"

echo "Setup complete!"
