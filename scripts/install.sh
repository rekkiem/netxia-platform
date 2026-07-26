#!/bin/bash
# =====================================================================
# install.sh — Instalación inicial de Netxia Conversational Platform
# Uso: sudo bash scripts/install.sh
# =====================================================================
set -euo pipefail

echo "=== NETXIA CONVERSATIONAL PLATFORM - INSTALL ==="

if [[ $EUID -ne 0 ]]; then
  echo "Este script debe ejecutarse como root (sudo bash scripts/install.sh)" >&2
  exit 1
fi

echo "[1/7] Actualizando el sistema..."
apt-get update -y && apt-get upgrade -y

echo "[2/7] Instalando Docker y Docker Compose..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  rm /tmp/get-docker.sh
fi
apt-get install -y docker-compose-plugin

echo "[3/7] Validando archivo .env..."
if [[ ! -f .env ]]; then
  echo "No se encontró .env. Copiando desde .env.example — DEBES editarlo antes de continuar."
  cp .env.example .env
  echo "Edita el archivo .env con tus credenciales reales y vuelve a ejecutar este script."
  exit 1
fi

echo "[4/7] Creando directorios de datos..."
mkdir -p audio models/piper logs

echo "[5/7] Descargando modelos LLM en Ollama..."
docker compose up -d ollama
sleep 5
docker compose exec -T ollama ollama pull llama3.2:3b
docker compose exec -T ollama ollama pull gemma2:2b

echo "[6/7] Descargando voz de Piper (es_ES-sharon-medium)..."
PIPER_VOICE_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharon/medium"
curl -L -o models/piper/es_ES-sharon-medium.onnx "${PIPER_VOICE_BASE}/es_ES-sharon-medium.onnx"
curl -L -o models/piper/es_ES-sharon-medium.onnx.json "${PIPER_VOICE_BASE}/es_ES-sharon-medium.onnx.json"

echo "[7/7] Levantando todos los servicios..."
docker compose up -d --build

echo ""
echo "=== INSTALACIÓN COMPLETA ==="
docker compose ps
IP_ADDR=$(hostname -I | awk '{print $1}')
echo ""
echo "Gateway API:      http://${IP_ADDR}:8000 (o https://api.netxia.cl vía Traefik)"
echo "RabbitMQ mgmt:    http://${IP_ADDR}:15672"
echo "Grafana:          http://${IP_ADDR}:3000 (o https://monitor.netxia.cl)"
echo "n8n:              http://${IP_ADDR}:5678 (o https://n8n.netxia.cl)"
echo ""
echo "Próximo paso: configurar el número SIP y la instancia de WhatsApp (ver README.md)."
