#!/usr/bin/env bash
set -e

echo "=== Esperando a que PostgreSQL (${DB_HOST:-db}:${DB_PORT:-5432}) este disponible... ==="
python - <<'EOF'
import os
import time
import psycopg2

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "5432"))
user = os.environ.get("DB_USER", "postgres")
password = os.environ.get("DB_PASSWORD", "postgres")
dbname = os.environ.get("DB_NAME", "traducontext")

for intento in range(1, 31):
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=3,
        )
        conn.close()
        print("PostgreSQL conectado correctamente.")
        break
    except Exception as exc:
        print(f"Intento {intento}/30: PostgreSQL aun no responde ({exc}). Reintentando en 2s...")
        time.sleep(2)
else:
    raise RuntimeError("No se pudo conectar a PostgreSQL despues de 30 intentos.")
EOF

echo "=== Inicializando tablas y semillas de la base de datos... ==="
python -c "from app.database.inicializacion import inicializar_base_datos; inicializar_base_datos(); print('Base de datos inicializada y sembrada correctamente.')"
alembic stamp head || true

echo "=== Iniciando servidor FastAPI (Uvicorn)... ==="
exec "$@"
