#!/usr/bin/env bash
# deploy.sh — run on the VPS to pull latest code and rebuild production containers
#
# Usage (from the repo root on the server):
#   bash scripts/deploy.sh
#
# Requirements: Docker, Docker Compose v2, .env present at repo root
# (copy from .env.production.example and fill in secrets if first deploy)

set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"

echo "==> Pulling latest code from main..."
git pull origin main

echo "==> Rebuilding and restarting containers..."
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

echo "==> Removing dangling images to free disk space..."
docker image prune -f

echo "==> Running status check..."
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "Deploy complete. Check logs with:"
echo "  docker compose -f $COMPOSE_FILE logs -f"
