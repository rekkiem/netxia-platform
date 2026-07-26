FROM python:3.12-slim

WORKDIR /srv

# Dependencias del sistema mínimas (compilación de asyncpg/httptools, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY crm-service/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Código compartido primero (cambia poco -> mejor cacheo de capas)
COPY shared/ /srv/shared/
COPY crm-service/app/ /srv/app/

ENV PYTHONPATH=/srv
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
