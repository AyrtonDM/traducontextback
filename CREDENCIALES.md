# Credenciales de TraduContext

Qué credenciales usa el sistema (backend, web y móvil), dónde se obtiene cada una, dónde va y
cómo circula. **Ninguna se sube a git**: todas las rutas de abajo están en el `.gitignore` de su
repositorio. Se comparten entre el equipo por un canal privado, nunca en el repo, issues ni chats
públicos.

## Resumen: dónde va cada archivo

```
traducontextback/
├── .env                                  ← copia de .env.example con los valores reales
└── credenciales/
    └── firebase-adminsdk.json            ← cuenta de servicio de Firebase (push)

traducontextfront/
└── src/environments/
    └── firebase.ts                       ← copia de firebase.example.ts (app web de Firebase)

traducontextmovil/
└── android/app/
    └── google-services.json              ← app Android com.atemporal de Firebase
```

| Credencial | Repo | Archivo | ¿Obligatoria? | Se obtiene en |
|------------|------|---------|---------------|---------------|
| PostgreSQL | back | `.env` (`DB_*`) | Sí | Tu instalación local de PostgreSQL |
| Gmail (SMTP) | back | `.env` (`GMAIL_*`) | Sí | Cuenta de Google → Seguridad → Contraseñas de aplicación |
| OpenAI | back | `.env` (`OPENAI_API_KEY`) | Sí (puede ir vacía) | platform.openai.com → API keys |
| Clave Fernet | back | `.env` (`CLAVE_CIFRADO_TOKENS`) | Solo para Meet/Zoom | Se genera localmente (ver abajo) |
| Google OAuth (Meet) | back | `.env` (`GOOGLE_*`) | No | Google Cloud Console → Credenciales |
| Zoom OAuth | back | `.env` (`ZOOM_*`) | No | Zoom App Marketplace |
| Firebase Admin | back | `credenciales/firebase-adminsdk.json` + `.env` (`FIREBASE_CREDENCIALES`) | Solo para push | Firebase → Cuentas de servicio |
| Firebase web | front | `src/environments/firebase.ts` | El archivo sí (sin él no compila); los valores solo para push web | Firebase → Tus apps → Web |
| Firebase Android | móvil | `android/app/google-services.json` | Solo para push en el móvil | Firebase → Tus apps → Android `com.atemporal` |

Todo Firebase pertenece al mismo proyecto: **`atemporal-f0125`**.

---

## Backend (`traducontextback/.env`)

Se crea con `copy .env.example .env`. Lo lee `app/core/configuracion.py` al arrancar, así que
cualquier cambio exige reiniciar `uvicorn`.

### Base de datos — `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
Usuario y contraseña de tu PostgreSQL local. Las usan la API y Alembic (`migrations/env.py`
construye la URL con ellas; `alembic.ini` no guarda ninguna URL).

### Correo — `GMAIL_USUARIO`, `GMAIL_PASSWORD`, `GMAIL_REMITENTE`
Sirven para enviar los códigos de verificación de cuenta y de recuperación de contraseña.
`GMAIL_PASSWORD` **no** es la contraseña de la cuenta, sino una contraseña de aplicación de
16 caracteres. Para crearla hay que activar la verificación en dos pasos y luego ir a
myaccount.google.com → Seguridad → Contraseñas de aplicación.

### OpenAI — `OPENAI_API_KEY`
Se usa en la traducción con LLM, la asistencia conversacional y la transcripción con Whisper. La
variable tiene que existir aunque esté vacía; si está vacía, esas funciones fallan. Cada llamada
consume saldo de la cuenta de OpenAI.

### Integraciones Meet / Zoom (opcional)
- `CLAVE_CIFRADO_TOKENS`: clave Fernet. Cifra los tokens OAuth guardados en la tabla
  `conexion_plataforma` y firma el `state` del flujo OAuth. Se genera con:
  ```powershell
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  **No la cambies** con integraciones ya vinculadas: los tokens guardados dejarían de poder
  descifrarse y habría que volver a vincular.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: ID de cliente OAuth de tipo «Aplicación web». En
  Google Cloud Console, añade como URI de redirección autorizada exactamente el valor de
  `GOOGLE_REDIRECT_URI` (`http://localhost:8000/api/v1/integraciones/google_meet/callback`).
- `ZOOM_CLIENT_ID` / `ZOOM_CLIENT_SECRET`: app General (OAuth) en Zoom App Marketplace, con
  `ZOOM_REDIRECT_URI` (`http://localhost:8000/api/v1/integraciones/zoom/callback`) como
  Redirect URL.
- `FRONTEND_URL`: a dónde vuelve el navegador al terminar la autorización.

### Push — `FIREBASE_CREDENCIALES` (opcional)
1. Firebase → Configuración del proyecto → **Cuentas de servicio** → «Generar nueva clave privada».
2. Guarda el JSON como `traducontextback/credenciales/firebase-adminsdk.json`.
3. En `.env`: `FIREBASE_CREDENCIALES=credenciales/firebase-adminsdk.json`. La ruta es relativa
   a la raíz del backend; también se acepta el JSON completo en una sola línea.

Esta es la credencial **más sensible**: permite enviar push a todos los usuarios. Si se filtra,
revócala en Firebase (Cuentas de servicio → Administrar permisos) y genera otra.

---

## Web (`traducontextfront/src/environments/firebase.ts`)

```powershell
copy src\environments\firebase.example.ts src\environments\firebase.ts
```

- `firebaseConfig`: sale de Firebase → Configuración del proyecto → Tus apps → **Web**. No son los
  valores de `google-services.json`, que pertenecen a la app Android.
- `vapidKey`: Firebase → Cloud Messaging → Certificados web push → par de claves.
- Con los valores vacíos la web compila y funciona, pero sin push.
- Estos valores **no son secretos** en sentido estricto: acaban dentro del JavaScript que
  descarga el navegador. Aun así no se versionan, para que cada entorno use los suyos.
- La URL del backend (`environment*.ts`) no es una credencial y sí está en git.

## Móvil (`traducontextmovil/android/app/google-services.json`)

- Firebase → Configuración del proyecto → Tus apps → Android **`com.atemporal`** → descargar
  `google-services.json` y copiarlo en `android/app/`.
- El `applicationId` de la app es `com.atemporal` para reutilizar ese registro. Si el archivo
  falta o es de otro paquete, Gradle no aplica el plugin y la app funciona sin push.
- Igual que en la web, no es un secreto fuerte (va dentro del APK), pero no se versiona.
- No se usan `firebase_options.dart`, `firebase.json` (FlutterFire) ni `GoogleService-Info.plist`
  (iOS no está configurado).
- Firma: los APK se firman con la clave de depuración de Android. Si algún día se firma para
  publicar, `android/key.properties` y el `*.jks` tampoco se versionan.

---

## Flujo en tiempo de ejecución

### Inicio de sesión (web y móvil)

```
Usuario ──correo + contraseña──► POST /autenticacion/iniciar-sesion
                                  │ compara con el hash PBKDF2-SHA256 de la tabla usuario
                                  │ cierra las sesiones ACTIVAS anteriores de ese usuario
                                  │ crea una fila en `sesion` con un token aleatorio (válido 7 días)
                                  ▼
                           token de sesión ──► Web: localStorage['auth_token']
                                           └─► Móvil: flutter_secure_storage (cifrado por el sistema)

Cada petición:  Authorization: Bearer <token>  ──►  el backend busca la sesión ACTIVA y no expirada
```

- No es un JWT: el token es opaco y solo vale mientras su fila de `sesion` esté ACTIVA. Un 401
  devuelve al usuario al login.
- **Un usuario solo puede tener una sesión activa.** Si inicias sesión con la misma cuenta en el
  móvil, se cierra la de la web, y al revés. Para probar los dos a la vez usa cuentas distintas.

### Notificaciones push

```
Firebase (proyecto atemporal-f0125)
  │  1. al iniciar sesión, la app (google-services.json) o la web (firebase.ts + vapidKey)
  │     piden a Firebase un token FCM del dispositivo
  ▼
Web / móvil ──POST /dispositivos {token_fcm, plataforma}──► tabla dispositivo_push (por usuario)
                                                            │
  2. evento (mensaje de chat, documento listo...)           │
     → notificacion en BD → push_fcm.py ──firebase-adminsdk.json──► FCM ──► dispositivo
```

- Al cerrar sesión, la app llama a `DELETE /dispositivos/{token}`.
- Los tokens que FCM rechaza se marcan como `activo = false`.

### Integraciones Meet / Zoom (OAuth)

```
Web ──POST /integraciones/{plataforma}/autorizar──► URL de Google/Zoom (state firmado con Fernet)
Navegador ──el usuario acepta──► /integraciones/{plataforma}/callback (backend, CLIENT_SECRET)
Backend ──tokens OAuth cifrados con CLAVE_CIFRADO_TOKENS──► tabla conexion_plataforma
Backend ──redirección──► FRONTEND_URL
```

---

## Si una credencial se filtra

| Credencial | Qué hacer |
|------------|-----------|
| Contraseña de aplicación de Gmail | Revocarla en Contraseñas de aplicación y crear otra. |
| `OPENAI_API_KEY` | Revocarla en platform.openai.com y crear otra. |
| `firebase-adminsdk.json` | Borrar esa clave en Google Cloud → IAM → Cuentas de servicio y generar otra. |
| `GOOGLE_CLIENT_SECRET` / `ZOOM_CLIENT_SECRET` | Rotarlo en la consola de cada plataforma. |
| `CLAVE_CIFRADO_TOKENS` | Cambiarla obliga a que los usuarios vuelvan a vincular Meet/Zoom. |
| Contraseña de PostgreSQL | `ALTER USER ... PASSWORD '...'` y actualizar `.env`. |

Si se subió a git por error, borrarla del repo **no basta**: queda en el historial. Hay que
rotarla siempre.
