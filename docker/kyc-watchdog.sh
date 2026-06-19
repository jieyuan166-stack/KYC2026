#!/bin/sh
set -eu

PROJECT_DIR="/volume1/docker/Triton KYC/docker"
APP_HEALTH_URL="http://127.0.0.1:3000/api/health"
PUBLIC_HEALTH_URL="https://kyc.tritonwealth.ca/api/health"
SECRETS_DIR="/volume1/docker/kyc-cloudflared"
SECRETS_BACKUP_DIR="/volume1/docker/kyc-cloudflared-secure-backup"
TUNNEL_ID="d6596ab1-4853-4816-900c-b6e7ef52fbfc"
CREDENTIAL_FILE="$TUNNEL_ID.json"
LOG_DIR="/volume1/docker/Triton KYC/logs"
LOG_FILE="$LOG_DIR/kyc-watchdog.log"
LOCK_DIR="/tmp/triton-kyc-watchdog.lock"

mkdir -p "$LOG_DIR"

log() {
  printf "%s %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE"
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT INT TERM

restore_secret() {
  name="$1"
  src="$SECRETS_BACKUP_DIR/$name"
  dest="$SECRETS_DIR/$name"
  if [ ! -s "$dest" ] && [ -s "$src" ]; then
    mkdir -p "$SECRETS_DIR"
    cp "$src" "$dest"
    log "restored missing $name from secure backup"
  fi
}

restore_secret "config.yml"
restore_secret "$CREDENTIAL_FILE"
chmod 644 "$SECRETS_DIR/config.yml" 2>/dev/null || true
chmod 600 "$SECRETS_DIR/$CREDENTIAL_FILE" 2>/dev/null || true

if [ ! -s "$SECRETS_DIR/config.yml" ] || [ ! -s "$SECRETS_DIR/$CREDENTIAL_FILE" ]; then
  log "ERROR missing cloudflared config or credential after restore attempt"
  exit 1
fi

if ! grep -q "credentials-file: /etc/cloudflared/$CREDENTIAL_FILE" "$SECRETS_DIR/config.yml"; then
  log "ERROR cloudflared config points to wrong credentials-file"
  exit 1
fi

if ! grep -q "service: http://triton-kyc-app:3000" "$SECRETS_DIR/config.yml"; then
  log "ERROR cloudflared config points to wrong app service"
  exit 1
fi

# Keep real tunnel secrets outside the project so app deploys/backups cannot delete or publish them.
rm -f "$PROJECT_DIR/cloudflared/config.yml" "$PROJECT_DIR/cloudflared/$CREDENTIAL_FILE" 2>/dev/null || true

cd "$PROJECT_DIR"
docker compose up -d triton-kyc-app triton-kyc-tunnel triton-kyc-tunnel-backup >/dev/null 2>&1 || {
  log "docker compose up failed"
  exit 1
}

if ! curl -fsS --max-time 8 "$APP_HEALTH_URL" >/dev/null 2>&1; then
  log "local app health failed; restarting app"
  docker compose restart triton-kyc-app >/dev/null 2>&1 || true
  sleep 8
fi

for service in triton-kyc-app triton-kyc-tunnel triton-kyc-tunnel-backup; do
  state="$(docker inspect -f '{{.State.Running}}' "$service" 2>/dev/null || echo false)"
  if [ "$state" != "true" ]; then
    log "$service not running; bringing it up"
    docker compose up -d "$service" >/dev/null 2>&1 || true
  fi
done

running_tunnels="$(docker ps --filter 'name=triton-kyc-tunnel' --filter 'status=running' --format '{{.Names}}' | wc -l | tr -d ' ')"
if [ "$running_tunnels" -lt 2 ]; then
  log "less than two KYC tunnel containers running; restarting both tunnels"
  docker compose restart triton-kyc-tunnel triton-kyc-tunnel-backup >/dev/null 2>&1 || true
  sleep 8
fi

if ! curl -fsS --max-time 12 "$PUBLIC_HEALTH_URL" >/dev/null 2>&1; then
  log "public health failed; restarting tunnels"
  docker compose restart triton-kyc-tunnel triton-kyc-tunnel-backup >/dev/null 2>&1 || true
  sleep 12
  if ! curl -fsS --max-time 12 "$PUBLIC_HEALTH_URL" >/dev/null 2>&1; then
    log "public health still failed; restarting app and tunnels"
    docker compose restart triton-kyc-app triton-kyc-tunnel triton-kyc-tunnel-backup >/dev/null 2>&1 || true
  fi
fi

if [ -f "$LOG_FILE" ] && [ "$(wc -c < "$LOG_FILE" | tr -d ' ')" -gt 1048576 ]; then
  tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
