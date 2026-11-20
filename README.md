# traducontextback

API de TraduContext (FastAPI + SQLAlchemy + Alembic + PostgreSQL). La consumen la web
(`traducontextfront`) y la app móvil (`traducontextmovil`).

Orden recomendado para levantar todo el sistema: **PostgreSQL → backend → web y/o móvil**.

## Requisitos

| Herramienta | Versión | Notas |
|-------------|---------|-------|
| Python | 3.12 | Es la versión del `venv` actual (torch, onnxruntime y fasttext tienen ruedas para ella). |
| PostgreSQL | 14 o superior | Crear una base vacía (p. ej. `traducontext`). |
| Espacio en disco | ~5 GB | torch y el modelo NLLB-200 (`facebook/nllb-200-distilled-600M`, ~2,5 GB), que se descarga de Hugging Face la primera vez que se usa. |

## 1. Instalación

```powershell
cd traducontextback
py -3.12 -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

## 2. Variables de entorno

```powershell
copy .env.example .env
```

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Sí | Conexión a PostgreSQL (p. ej. `localhost`, `5432`). |
| `DB_ECHO` | Sí | `true` imprime el SQL en consola. |
| `GMAIL_USUARIO`, `GMAIL_PASSWORD`, `GMAIL_REMITENTE` | Sí | Cuenta Gmail para los códigos de verificación y recuperación. `GMAIL_PASSWORD` es una **contraseña de aplicación** de Google (requiere verificación en dos pasos), no la contraseña normal. |
| `OPENAI_API_KEY` | Sí (puede ir vacía) | Traducción con LLM, asistencia y transcripción con Whisper. Vacía: esas funciones fallan. |
| `CLAVE_CIFRADO_TOKENS`, `GOOGLE_*`, `ZOOM_*` | No | Integraciones con Meet y Zoom. Sin ellas aparecen como «no configuradas». |
| `FRONTEND_URL` | No | A dónde vuelve el navegador tras el OAuth de Meet/Zoom. Por defecto `http://localhost:4200`. |
| `FIREBASE_CREDENCIALES` | No | Push (web y móvil). Ver el apartado 5. Vacía: las notificaciones solo se guardan en la base de datos. |

**Nunca** se suben `.env` ni la carpeta `credenciales/` (están en `.gitignore`). En
[`CREDENCIALES.md`](CREDENCIALES.md) se explica dónde obtener cada credencial del sistema
(backend, web y móvil), dónde va y cómo circula.

## 3. Base de datos

Al arrancar, el backend crea las tablas que falten (`create_all`) y siembra los datos iniciales:
roles (`ADMINISTRADOR`, `USUARIO`) y sus permisos, idiomas, contextos, tonos, variantes regionales
y entornos.

**Base nueva (primera vez):**

```powershell
uvicorn app.main:app --port 8000   # crea tablas y datos iniciales; luego Ctrl+C
alembic stamp head                 # marca la base como migrada hasta la última versión
```

No ejecutes `alembic upgrade head` sobre una base vacía: la primera migración supone que las
tablas base ya existen.

**Base existente (al traer cambios de otros):**

```powershell
alembic upgrade head
```

**Nueva migración tras cambiar un modelo:**

```powershell
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

**Primer administrador:** regístrate desde la web o el móvil y luego, en PostgreSQL:

```sql
UPDATE usuario SET id_rol = (SELECT id FROM rol WHERE nombre = 'ADMINISTRADOR')
WHERE correo = 'tu_correo@ejemplo.com';
```

`tablas_bd.md` documenta todas las tablas y relaciones.

## 4. Ejecutar

```powershell
.\venv\Scripts\Activate
uvicorn app.main:app --reload --port 8000
```

- API: `http://127.0.0.1:8000/api/v1`. Documentación interactiva: `http://127.0.0.1:8000/docs`.
- Así basta para la web y para el móvil por USB (`adb reverse`).
- Para el móvil por Wi-Fi, el backend tiene que escuchar en toda la red:
  `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`. Además hay que permitir el puerto 8000
  en el firewall de Windows (red privada).

## 5. Notificaciones push (opcional)

1. Firebase Console → proyecto → Configuración → **Cuentas de servicio** → «Generar nueva clave privada».
2. Guarda el JSON como `credenciales/firebase-adminsdk.json`.
3. En `.env`: `FIREBASE_CREDENCIALES=credenciales/firebase-adminsdk.json` (la ruta es relativa a
   la raíz del backend; también se acepta el JSON completo en una sola línea).
4. Reinicia el backend.

Los dispositivos se registran solos con `POST /api/v1/dispositivos` al iniciar sesión en la web o
el móvil (tabla `dispositivo_push`). Los tokens que FCM rechaza se marcan como inactivos.

## Pruebas manuales

`pruebas/` contiene scripts sueltos para probar el detector de idioma, NLLB, el motor contextual
y la traducción:

```powershell
python -m pruebas.probar_nllb
```

## Formato de respuesta

Todas las respuestas, incluidos los errores, tienen esta forma:

```json
{ "mensaje": "Usuario obtenido correctamente", "resultado": { "id": 15, "nombre": "Elizabeth" } }
```

## Estructura (`app/`)

| Carpeta | Contenido |
|---------|-----------|
| `api/routes/` | Endpoints de FastAPI. Reciben la petición, llaman al servicio y devuelven la respuesta, sin lógica de negocio. `api/rutas.py` los reúne. |
| `services/` | Lógica de negocio (autenticación, traducción, chats, documentos, notificaciones, push FCM...). |
| `models/` | Modelos SQLAlchemy (tablas), agrupados por módulo. |
| `schemas/` | Esquemas Pydantic de entrada y salida de la API (no son tablas). |
| `database/` | Conexión, sesión, clase `Base` e inicialización (tablas + seeds). |
| `seeds/` | Datos iniciales del sistema. Las migraciones cambian la estructura; los seeds insertan datos. |
| `core/` | Configuración (`.env`), seguridad (hash de contraseñas, tokens de sesión, permisos) y cifrado Fernet. |
| `constants/` | Constantes (p. ej. códigos de idioma NLLB). |
| `models_ia/` | Modelo de detección de idioma (`lid.176.ftz`, fastText). |
| `utilities/` | Funciones auxiliares reutilizables (correo, códigos...). |
| `main.py` | Crea la app, CORS, rutas y `/documentos` (archivos subidos y traducidos, en `documentos/`, que no se versiona). |

Flujo: `cliente → api/routes → services → models/database → PostgreSQL`.
