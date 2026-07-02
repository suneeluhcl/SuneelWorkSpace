#!/usr/bin/env bash
# hands/scripts/dev/dev_stack.sh
# Multi-service dev orchestration: brings local databases/caches up or down for
# a Java/Node service. Uses the project's compose file when present, otherwise
# manages standalone dev containers (postgres/mysql/redis) with standard ports.
#
# Usage: dev-stack up|down|status|logs [postgres|mysql|redis ...] [--dir DIR]
set -uo pipefail

ACTION="${1:-status}"
shift || true

DIR="."
SERVICES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="$2"; shift 2 ;;
    *) SERVICES+=("$1"); shift ;;
  esac
done
[ ${#SERVICES[@]} -eq 0 ] && SERVICES=(postgres redis)

command -v docker >/dev/null || { echo "dev-stack: docker not installed"; exit 1; }
docker info >/dev/null 2>&1 || { echo "dev-stack: docker daemon not running — start Docker Desktop/colima first"; exit 1; }

# Prefer the project's own compose file.
COMPOSE=""
for f in docker-compose.yml docker-compose.yaml compose.yaml compose.yml; do
  [ -f "$DIR/$f" ] && COMPOSE="$DIR/$f" && break
done

if [ -n "$COMPOSE" ]; then
  echo "dev-stack: using $COMPOSE"
  case "$ACTION" in
    up)     docker compose -f "$COMPOSE" up -d ;;
    down)   docker compose -f "$COMPOSE" down ;;
    status) docker compose -f "$COMPOSE" ps ;;
    logs)   docker compose -f "$COMPOSE" logs --tail 50 ;;
    *) echo "dev-stack: unknown action '$ACTION' (up|down|status|logs)"; exit 2 ;;
  esac
  exit $?
fi

# Standalone dev containers — dev-only credentials, local ports.
container_args() {
  case "$1" in
    postgres) echo "-p 5432:5432 -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=devdb postgres:16" ;;
    mysql)    echo "-p 3306:3306 -e MYSQL_ROOT_PASSWORD=devpass -e MYSQL_DATABASE=devdb mysql:8" ;;
    redis)    echo "-p 6379:6379 redis:7" ;;
    *) return 1 ;;
  esac
}

for svc in "${SERVICES[@]}"; do
  NAME="sw-dev-$svc"
  ARGS="$(container_args "$svc")" || { echo "dev-stack: unknown service '$svc' (postgres|mysql|redis)"; continue; }
  case "$ACTION" in
    up)
      if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
        echo "  $NAME already running"
      elif docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
        docker start "$NAME" >/dev/null && echo "  $NAME started (existing container)"
      else
        # shellcheck disable=SC2086
        docker run -d --name "$NAME" $ARGS >/dev/null && echo "  $NAME created + started"
      fi
      ;;
    down)
      if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
        docker stop --time 20 "$NAME" >/dev/null && echo "  $NAME stopped gracefully"
      else
        echo "  $NAME not running"
      fi
      ;;
    status)
      docker ps -a --filter "name=$NAME" --format '  {{.Names}}: {{.Status}} ({{.Ports}})' | grep . || echo "  $NAME: not created"
      ;;
    logs)
      echo "--- $NAME ---"; docker logs --tail 30 "$NAME" 2>&1 || true
      ;;
    *) echo "dev-stack: unknown action '$ACTION' (up|down|status|logs)"; exit 2 ;;
  esac
done
