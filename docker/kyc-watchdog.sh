#!/bin/sh
set -eu

PROJECT_DIR="/volume1/docker/Triton KYC/docker"
APP_HEALTH_URL="http://127.0.0.1:3000/api/health"

cd "$PROJECT_DIR"

docker compose up -d triton-kyc-app triton-kyc-tunnel triton-kyc-tunnel-backup >/dev/null

if ! curl -fsS --max-time 10 "$APP_HEALTH_URL" >/dev/null; then
  docker compose restart triton-kyc-app >/dev/null
fi

for service in triton-kyc-tunnel triton-kyc-tunnel-backup; do
  if [ "$(docker inspect -f '{{.State.Running}}' "$service" 2>/dev/null || echo false)" != "true" ]; then
    docker compose up -d "$service" >/dev/null
  fi
done

running_tunnels="$(docker ps --filter 'name=triton-kyc-tunnel' --filter 'status=running' --format '{{.Names}}' | wc -l | tr -d ' ')"
if [ "$running_tunnels" -lt 2 ]; then
  docker compose restart triton-kyc-tunnel triton-kyc-tunnel-backup >/dev/null
fi
