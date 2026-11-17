# Sprint 3: Historias de usuario y criterios de aceptación (BORRADOR)

> **Estado del documento:** borrador para verificación técnica con Claude Code.
> El documento del proyecto solo contiene, para el Sprint 3, los requisitos funcionales (RF-23 a RF-32) y las historias a nivel de Product Backlog (PB-23 a PB-32). Los criterios de abajo están **derivados de esas fuentes** y deben ser validados por el equipo y el Product Owner. Un criterio marcado con (P) es una propuesta de interpretación, no un texto oficial.

## Reglas globales del proyecto
- Backend: `traducontextback` (FastAPI + SQLAlchemy + Alembic). Frontend: `traducontextfront` (Angular). Son repos git separados.
- El usuario se obtiene del token con la dependencia existente. Nunca se envía el id de usuario en body, query ni URL.
- Respetar la estructura de carpetas existente, sobre todo las vistas del sidebar en el front.
- Las tablas se crean con Alembic (no con `create_all`). La cabeza actual de migraciones es `c3d8a9e1f2b4`.
- Una HU está **COMPLETA** solo si: (1) backend con modelo/tabla + endpoint + lógica real (sin stubs, `pass`, TODO ni datos mock); (2) frontend con vista que llama al endpoint correcto y está en `app.routes.ts` y en el sidebar si corresponde; (3) rutas, métodos y campos coinciden entre back y front. Si falta una parte: PARCIAL. Si no hay nada: FALTA.

---

## HU-23 Gestión de conversaciones (Alta) · RF-23 · PB-23
**Como** usuario **quiero** iniciar, pausar, reanudar y finalizar una sesión de conversación **para** mantener la traducción durante toda la sesión con los idiomas, contexto y configuraciones elegidos.

Criterios:
1. El sistema debe permitir iniciar una sesión estableciendo idioma de origen, idioma de destino (distintos entre sí), contexto y entorno (HU-24).
2. El sistema debe permitir pausar la sesión; mientras está en pausa no se procesan nuevas intervenciones.
3. El sistema debe permitir reanudar la sesión conservando la configuración y las intervenciones previas.
4. El sistema debe permitir finalizar la sesión; una sesión finalizada no admite nuevas intervenciones.
5. El estado de la sesión (activa, pausada, finalizada) debe persistirse y mostrarse al usuario.
6. Solo el usuario autenticado puede ver y controlar sus propias sesiones.
7. (P) El usuario debe poder consultar el listado de sus sesiones anteriores.

## HU-24 Entorno de conversación (Alta) · RF-24 · PB-24
**Como** usuario **quiero** seleccionar el entorno en el que se desarrolla la conversación **para** adaptar la interpretación y traducción a la situación.

Criterios:
1. El sistema debe permitir seleccionar el entorno: reunión, conferencia, clase, entrevista o conversación informal.
2. El entorno seleccionado debe guardarse en la sesión y usarse como parámetro al traducir e interpretar.
3. (P) El entorno debe poder cambiarse mientras la sesión no esté finalizada.
4. (P) Los entornos son un catálogo distinto de los contextos de dominio de HU-13 (Laboral, Legal, Técnico, etc.). No deben mezclarse ni sobrescribirse.

## HU-25 Transcripción en tiempo real (Alta) · RF-25 · PB-25
**Como** usuario **quiero** que mis intervenciones habladas se conviertan en texto mientras hablo **para** seguir el diálogo.

Criterios:
1. El sistema debe capturar el audio del micrófono previa autorización del usuario.
2. El sistema debe convertir el habla en texto de forma progresiva (resultados parciales y finales).
3. La transcripción debe mostrarse durante la sesión.
4. (P) El idioma de reconocimiento debe corresponder al idioma del hablante.
5. (P) Si no hay permiso de micrófono, no hay conexión o el audio no se reconoce, se muestra un mensaje claro y la sesión no se rompe.
6. (P) No se transcribe mientras la sesión está en pausa o finalizada.

## HU-31 Identificación de participantes y turnos (Media) · RF-31 · PB-31
**Como** usuario **quiero** diferenciar a los participantes y sus turnos **para** saber quién realizó cada intervención.

Criterios:
1. Cada intervención debe asociarse a un participante cuando sea posible.
2. El usuario debe poder etiquetar o nombrar a los participantes (ej. "Participante 1"), o asignar el hablante de un turno manualmente.
3. Los turnos deben distinguirse visualmente por participante.
4. (P) Si no se puede identificar al hablante, la intervención se asigna a "No identificado" sin perderse.
5. (P) Cada turno guarda su orden y marca de tiempo.

## HU-26 Traducción bidireccional (Alta) · RF-26 · PB-26
**Como** usuario **quiero** traducir conversaciones en ambos sentidos y en tiempo real **para** comunicarme con personas que hablan otro idioma.
Descripción:
Implementar el procesamiento de traducción bidireccional que permita traducir las intervenciones realizadas por los participantes durante una conversación en tiempo real. El sistema deberá reconocer el idioma de cada intervención y generar su traducción hacia el idioma correspondiente del otro participante, utilizando las funcionalidades de traducción contextual existentes y permitiendo la comunicación entre diferentes idiomas sin depender de un idioma intermediario específico.

Criterios:
1. El sistema debe traducir las intervenciones en ambos sentidos entre los dos idiomas de la sesión.
2. No debe depender de un idioma intermedio fijo (pivote).
3. (P) El sentido de la traducción se decide según el idioma del hablante (detectado o asignado).
4. (P) Debe reutilizar el servicio de traducción existente respetando contexto, región, tono y glosario cuando estén configurados, sin duplicar lógica.
5. (P) Un error de traducción en una intervención no detiene la sesión y se informa al usuario.
6. (P) La interfaz indica cuando una traducción está en proceso.
7. El sistema debe reutilizar las funcionalidades de traducción contextual disponibles.
8. La traducción bidireccional no debe depender de un idioma intermediario específico.

## HU-27 Visualización de la conversación (Alta) · RF-27 · PB-27
**Como** usuario **quiero** ver las intervenciones originales junto con sus traducciones **para** seguir el desarrollo de la conversación.

Criterios:
1. El sistema debe mostrar cada intervención transcrita junto a su traducción.
2. El usuario debe poder distinguir el contenido original del traducido.
3. Las intervenciones se muestran en orden cronológico y la vista avanza al último mensaje (auto-scroll).
4. (P) Se muestra el participante de cada turno cuando existe (HU-31).
5. (P) Al abrir o reanudar una sesión se cargan las intervenciones previas.

## HU-29 Contexto de conversación (Alta) · RF-29 · PB-29
**Como** usuario **quiero** que el sistema recuerde información relevante de intervenciones anteriores **para** interpretar correctamente mensajes posteriores.

Criterios:
1. El sistema debe mantener información relevante de las intervenciones anteriores de la sesión.
2. El sistema debe usarla para interpretar referencias, términos y expresiones cuyo significado dependa del contexto acumulado.
3. (P) El contexto pertenece solo a la sesión actual y no se mezcla con otras sesiones ni usuarios.
4. (P) El contexto acumulado se limita (por ejemplo, las intervenciones recientes) para controlar latencia y costo.
5. (P) Se combina con el contexto configurado (HU-13) y el entorno (HU-24).

## HU-28 Reproducción por voz (Media) · RF-28 · PB-28
**Como** usuario **quiero** escuchar mediante voz sintetizada las traducciones **para** facilitar la comunicación oral.

Criterios:
1. El sistema debe permitir reproducir la traducción con voz sintetizada en el idioma de destino.
2. La voz debe corresponder al idioma de destino, con pronunciación clara y natural.
3. (P) El usuario puede reproducir y detener una traducción, y activar o desactivar la reproducción automática.
4. (P) Si no existe voz disponible para el idioma, se informa al usuario.
5. (P) No se reproduce audio en una sesión pausada o finalizada.

## HU-30 Asistencia conversacional (Media) · RF-30 · PB-30
**Como** usuario **quiero** recibir explicaciones y sugerencias de respuesta durante una conversación **para** comunicarme adecuadamente según la situación.

Criterios:
1. El sistema debe ofrecer explicaciones contextuales de lo dicho (expresiones, referencias).
2. El sistema debe sugerir posibles respuestas.
3. El sistema debe recomendar cómo expresar una idea según la situación (entorno de HU-24).
4. (P) La asistencia es bajo demanda y no interrumpe la sesión.
5. (P) La asistencia se distingue visualmente de la traducción principal.

## HU-32 Glosarios personalizados (Media) · RF-32 · PB-32
**Como** usuario **quiero** crear y administrar glosarios personalizados **para** definir cómo deben traducirse o conservarse determinados términos.

Criterios:
1. El sistema debe permitir crear, consultar, modificar y eliminar glosarios (nombre, descripción, idioma de origen y de destino distintos).
2. El sistema debe permitir añadir términos con una traducción preferida, o marcar términos que deben conservarse en su idioma original.
3. Solo el usuario autenticado puede ver y modificar sus glosarios.
4. (P) El glosario seleccionado se aplica al traducir texto y documentos, y debe poder aplicarse también en conversaciones.
5. (P) No se permiten términos duplicados dentro de un mismo glosario.
6. (P) Eliminar un glosario no rompe traducciones o documentos ya registrados que lo referencian.

---

## Decisiones técnicas pendientes del equipo (no verificables en código)
- Proveedor de voz a texto (HU-25): Whisper vía SDK de OpenAI o reconocimiento del navegador.
- Canal de tiempo real: WebSocket o SSE.
- Cómo aplica tono y región la traducción de conversaciones, dado que el modelo NLLB no admite instrucciones de tono o región (ver HU-17).
- Si las conversaciones aparecen en el historial unificado (HU-42) o usan sus propias tablas.
