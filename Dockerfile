FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Dependencias del sistema para compilacion (fasttext, psycopg2) y utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    gcc \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias de Python
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel && \
    pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copiar el codigo fuente del proyecto
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Asegurar modelo FastText lid.176.ftz y estructura de carpetas de archivos
RUN mkdir -p /app/app/models_ia/detector_idioma \
    /app/archivos/fotos_perfil \
    /app/archivos/original \
    /app/archivos/traducido \
    /app/archivos/audio \
    /app/credenciales \
    /app/.cache/huggingface && \
    if [ ! -f /app/app/models_ia/detector_idioma/lid.176.ftz ]; then \
        curl -fSL https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz \
        -o /app/app/models_ia/detector_idioma/lid.176.ftz; \
    fi && \
    sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
