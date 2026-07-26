FROM python:3.12-slim

WORKDIR /srv

# Dependencias del sistema mínimas (compilación de asyncpg/httptools, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# IMPORTANTE: instalar PyTorch CPU-only ANTES de requirements.txt.
# sentence-transformers (usado para embeddings de RAG) depende de
# torch, y por defecto pip instala la variante CUDA (arrastra ~2GB de
# paquetes nvidia-* que nunca se usan: los LLMs corren en el contenedor
# de Ollama, no aquí). Al instalar la rueda CPU-only primero, pip ya
# encuentra la dependencia satisfecha y no descarga la versión GPU.
RUN pip install --no-cache-dir --break-system-packages torch --index-url https://download.pytorch.org/whl/cpu

COPY conversation-engine/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Código compartido primero (cambia poco -> mejor cacheo de capas)
COPY shared/ /srv/shared/
COPY conversation-engine/app/ /srv/app/

ENV PYTHONPATH=/srv
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
