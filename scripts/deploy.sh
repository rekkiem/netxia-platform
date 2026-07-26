#!/bin/bash
# =====================================================================
# deploy.sh — Actualiza y redepliega los servicios en el VPS.
# Uso: bash scripts/deploy.sh [servicio1 servicio2 ...]
# Sin argumentos, redepliega todos los servicios que tengan cambios.
# =====================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== NETXIA - DEPLOY ==="

echo "[1/4] Obteniendo últimos cambios del repositorio..."
git pull origin main

echo "[2/4] Validando configuración de docker-compose..."
docker compose config > /dev/null

SERVICES=("$@")

echo "[3/4] Reconstruyendo y desplegando..."
if [[ ${#SERVICES[@]} -eq 0 ]]; then
  docker compose up -d --build
else
  docker compose up -d --build "${SERVICES[@]}"
fi

echo "[4/4] Verificando salud de los servicios..."
sleep 5
FAILED=0
for service in gateway conversation-engine llm-service whatsapp-service voice-service spam-filter; do
  container_id=$(docker compose ps -q "$service" 2>/dev/null || true)
  if [[ -z "$container_id" ]]; then
    echo "  [SKIP] $service no está definido o no corriendo"
    continue
  fi
  status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "sin healthcheck")
  echo "  $service: $status"
  if [[ "$status" == "unhealthy" ]]; then
    FAILED=1
  fi
done

if [[ $FAILED -eq 1 ]]; then
  echo "ALERTA: uno o más servicios reportan estado unhealthy. Revisa 'docker compose logs'." >&2
  exit 1
fi

echo "=== DEPLOY COMPLETO ==="
