# Sprint 3: diseño objetivo de la pantalla "Conversación en tiempo real"

> Complementa a `SPRINT3_HU_CRITERIOS.md`. Describe la interfaz que el equipo definió (ver imagen `mockup-conversacion.png`, que debe estar en esta misma carpeta) y lo que el documento del equipo dice que se implementa en backend y frontend por HU.
> Este diseño tiene prioridad sobre la vista de conversaciones actual (lista + panel de detalle), que fue una primera aproximación.

## 1. Pantalla objetivo (según el mockup)
Ruta del sidebar: "Conversación" (breadcrumb: Inicio > Conversación). Título "Conversación en tiempo real", subtítulo "Traduce y comunica en distintos idiomas de forma inmediata.", botón "¿Cómo funciona?".

**Panel izquierdo "Configuración de la conversación":**
- Idiomas de la conversación: dos selects (Español ⇄ Inglés) con botón de intercambio.
- Entorno de conversación (ej. Reunión).
- Contexto / Dominio (ej. Técnico).
- Tono (ej. Neutral).
- Otras opciones (interruptores): "Mantener contexto de la conversación" y "Asistencia conversacional", cada uno con ícono de información.
- Botón principal "Iniciar conversación".

**Panel derecho "Conversación: <entorno> <dominio>" (ej. "Reunión técnica"):**
- Insignia de estado (en el mockup: "Lista para iniciar").
- Área de mensajes. Vacía: ícono, "La conversación aparecerá aquí" y "Las intervenciones se transcribirán y traducirán en tiempo real, mostrando su idioma original y su traducción."
- Barra inferior: "Participantes (2)" desplegable con "Participante 1 · Español" y "Participante 2 · Inglés"; botones micrófono, pausa y detener; botón "Asistente"; selector "Reproducción por voz".

**Interpretación acordada del diseño:**
- "Lista para iniciar" es un estado solo del frontend: todavía no existe sesión en backend. La sesión se crea al pulsar "Iniciar conversación" (POST /conversaciones) y pasa a `activa`.
- Dos participantes por sesión: el Participante 1 habla el idioma de origen y el Participante 2 el de destino. Cada intervención se traduce al idioma del otro.
- Micrófono = captura de voz activada o desactivada (frontend, HU-25). Pausa = pausar la sesión (backend). Detener = finalizar la sesión, con confirmación (backend).
- El título del panel derecho se compone con el entorno y el dominio elegidos.

## 2. Estructura de navegación propuesta
- `/conversaciones`: lista de conversaciones del usuario (HU-23): información principal, fecha, estado, filtro, botón "Nueva conversación", selección de una sesión y finalizar con confirmación.
- `/conversaciones/nueva` y `/conversaciones/:id`: la pantalla de conversación (HU-24), con opción para volver a la lista.
- El enlace "Conversación" del sidebar abre la lista y queda activo en las rutas hijas.

## 3. Lo que el documento del equipo describe por HU

### Backend
- **HU-23:** crear sesiones asociadas al usuario autenticado; id único y fecha de creación; guardar información básica y estado; consultar las conversaciones del usuario; recuperar una conversación por id; finalizar y actualizar estado; validar autorización.
- **HU-24:** acceder a una sesión ya creada; devolver información general y estado; validar existencia y autorización; datos para inicializar el entorno; gestionar solicitudes de interacción en sesión activa; integrar transcripción, traducción y demás servicios; restringir operaciones que requieran sesión activa cuando ya finalizó.
- **HU-25:** recibir fragmentos de audio de una conversación activa; procesarlos con el servicio de reconocimiento de voz; resultados parciales y finales; asociarlos a la conversación; enviarlos al front; manejar errores y fragmentos no transcribibles.
- **HU-31:** registrar participantes de una conversación; identificador por participante; recuperarlos; asociar intervenciones y transcripciones a su participante; validar que las operaciones pertenezcan a una conversación autorizada.
- **HU-26:** recibir el texto de cada intervención; determinar idiomas de origen y destino por intervención; traducir en ambos sentidos con el servicio de traducción contextual; conservar significado e intención; asociar original y traducción a la intervención; devolver resultados.
- **HU-27:** recuperar intervenciones de una conversación con contenido original y traducido, participante y orden temporal; enviar al front las nuevas intervenciones de una conversación activa.
- **HU-29:** recibir y guardar la configuración contextual de la conversación (dominio o descripción personalizada); modificarla; aplicarla a las traducciones posteriores.

### Frontend
- **HU-23:** vista de lista con información, fecha y estado; botón "Nueva conversación" que crea la sesión y entra al entorno; seleccionar una conversación existente; "Finalizar conversación" con mensaje de confirmación.
- **HU-24:** pantalla principal de la sesión con información y estado; área de intervenciones; controles (ingreso de contenido y opciones de traducción); opción para volver a la lista.
- **HU-25:** botón de micrófono (iniciar y detener captura); área de texto reconocido que se actualiza; indicadores de micrófono activo, detenido o procesando; mensajes de error por falta de permisos o fallo de transcripción.
- **HU-31:** sección de participantes con nombre o identificador; indicar quién interviene; cada mensaje muestra su participante; vista con datos básicos de los participantes.
- **HU-26:** controles de idiomas de los participantes; mostrar original y traducción de cada intervención; indicadores de traducción en proceso o con error.
- **HU-27:** panel con intervenciones en orden temporal; diferenciación visual por participante; texto original y traducción; incorporación de nuevas intervenciones; desplazamiento para ver las anteriores.
- **HU-29:** sección para elegir dominio predefinido o describir el contexto; campo de texto para situación, audiencia o terminología; editar el contexto; enviarlo al backend para las intervenciones posteriores.
- **HU-28:** botón de reproducción junto a cada traducción; controles de iniciar y detener; indicador de reproducción; mensajes de error si no se puede reproducir.

## 4. Brechas entre lo ya implementado y este diseño
Ya existe (backend): tablas `entorno` y `conversacion` (estados activa, pausada y finalizada; idiomas, contexto opcional, entorno), endpoints de iniciar, listar, consultar, cambiar entorno, pausar, reanudar y finalizar, y `exigir_conversacion_activa`. Ya existe (frontend): modelo, servicio y una vista con lista y panel de detalle, y `VozService`.

Falta para cumplir este diseño:
1. Frontend: separar lista y pantalla de conversación, y construir la pantalla del mockup (la lista y el modal de confirmación se reutilizan; el modal "Nueva conversación" se sustituye por el panel de configuración).
2. `conversacion` necesita guardar: tono, descripción personalizada del contexto, y los dos interruptores (mantener contexto y asistencia conversacional). Hoy solo guarda id_contexto y id_entorno, y el PATCH solo cambia el entorno (HU-29 pide poder modificar el contexto).
3. Tabla de participantes (HU-31): 2 por sesión, con nombre y idioma.
4. Tabla de intervenciones (HU-26, HU-27, HU-25): participante, texto original, traducción, idiomas, estado (procesando, traducida, error), fecha y orden; con FK en cascada a la conversación.
5. Función central de traducción reutilizable (tono, región, contexto, glosario) para HU-26.
6. Canal de tiempo real (WebSocket o SSE) y proveedor de voz a texto (HU-25), decisiones pendientes del equipo.

## 5. Etapas sugeridas
- **Etapa 1 (sin audio ni tiempo real):** rutas y pantalla del mockup, formulario de configuración completo, creación de sesión al pulsar "Iniciar conversación", dos participantes y panel vacío con controles. Backend: columnas nuevas, ampliar el PATCH y tabla de participantes. Micrófono y asistente visibles pero deshabilitados.
- **Etapa 2:** intervenciones escritas con traducción bidireccional y visualización (HU-26 y HU-27), sobre la función central de traducción.
- **Etapa 3:** audio y tiempo real (HU-25), voz por mensaje (HU-28), contexto acumulado (HU-29) y asistente (HU-30).

## 6. Reglas del proyecto (siguen vigentes)
- Convenciones tomadas del módulo de glosarios (nombres, capas, errores, migraciones) y de las vistas existentes del frontend.
- El usuario sale del token; nunca se envía su id.
- Tablas solo con Alembic; la cabeza actual de migraciones es `d4f1a2b3c5e6`.
- Sin datos mock ni UI ficticia.
