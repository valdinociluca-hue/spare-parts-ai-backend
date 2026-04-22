#!/usr/bin/env bash
# deploy.sh — pull latest code and restart the API stack
# Usage: bash deploy.sh [git-ref]
#   git-ref defaults to 'main'
# Run from /opt/spare-parts or anywhere with APP_DIR set.

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/spare-parts}"
GIT_REF="${1:-main}"
COMPOSE="docker compose -f $APP_DIR/deploy/docker/docker-compose.prod.yml"

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

[[ -d "$APP_DIR/.git" ]] || die "APP_DIR=$APP_DIR is not a git repo. Run setup-server.sh first."
[[ -f "$APP_DIR/.env" ]] || die "$APP_DIR/.env missing. Copy .env.production and fill secrets."

cd "$APP_DIR"

# ── Pull latest code ────────────────────────────────────────────────────────
log "Fetching $GIT_REF from origin..."
git fetch origin "$GIT_REF"
git checkout "$GIT_REF"
git pull origin "$GIT_REF"
log "Now at: $(git log -1 --oneline)"

# ── Build new image ─────────────────────────────────────────────────────────
log "Building Docker image..."
$COMPOSE build --no-cache api

# ── Apply DB migrations ─────────────────────────────────────────────────────
log "Running Alembic migrations..."
$COMPOSE run --rm api alembic upgrade head

# ── Rolling restart ─────────────────────────────────────────────────────────
log "Restarting services..."
$COMPOSE up -d --remove-orphans

# ── Health check ────────────────────────────────────────────────────────────
log "Waiting for health check..."
MAX_WAIT=60
ELAPSED=0
until curl -sf http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        log "Health check timed out after ${MAX_WAIT}s"
        log "Recent logs:"
        $COMPOSE logs --tail=30 api
        die "Deployment failed — API did not become healthy"
    fi
done

log ""
log "======================================================"
log " Deploy complete! API is healthy."
log "======================================================"
log " Commit: $(git log -1 --oneline)"
log " Time:   $(date)"
log ""
