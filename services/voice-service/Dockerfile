FROM python:3.12-slim

WORKDIR /srv

# ffmpeg: requerido por faster-whisper/av para decodificar audio.
# Piper se descarga como binario standalone (no hay paquete pip oficial
# estable multiplataforma); ver docs/ADRs/ADR-005 para la justificación.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ffmpeg tar \
    && rm -rf /var/lib/apt/lists/*

ARG PIPER_VERSION=2023.11.14-2
RUN curl -L -o /tmp/piper.tar.gz \
      "https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_x86_64.tar.gz" \
    && tar -xzf /tmp/piper.tar.gz -C /usr/local/bin --strip-components=1 piper/piper \
    && rm /tmp/piper.tar.gz \
    && chmod +x /usr/local/bin/piper

COPY voice-service/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY shared/ /srv/shared/
COPY voice-service/app/ /srv/app/

ENV PYTHONPATH=/srv
ENV PYTHONUNBUFFERED=1

# 8000: healthcheck HTTP | 8090: servidor AudioSocket (streaming con Asterisk)
EXPOSE 8000 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
