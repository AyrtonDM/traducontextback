# Contexto para Claude Code: Sprint 4 de TraduContext

Pega este archivo en Claude Code (o guárdalo en el repo como `docs/sprint4_contexto.md`) al empezar a programar.

## Proyecto
TraduContext es un asistente inteligente de traducción contextual (proyecto académico, Scrum, sprints de 3 semanas).

**Stack:** FastAPI (Python) en el back-end, Angular en la web, Flutter en móvil, PostgreSQL con migraciones, OpenAI API y DeepL API, Docker.

**Reglas del equipo:**
- No trabajar sobre `main`: una rama por funcionalidad e integración mediante Pull Request.
- Migraciones para todo cambio de base de datos.
- Credenciales y claves de API solo en variables de entorno.
- Pruebas de endpoints en FastAPI para cada HU.
- Definition of Done: implementación, pruebas, revisión de código, criterios de aceptación, integración y documentación.

**Ya existe de sprints anteriores:** autenticación y roles (HU-01, 03, 04), traducción contextual con idioma, contexto, tono y variante regional (HU-12 a 18), historial (HU-42, 43, 45), documentos (HU-19 a 22), perfil (HU-02), conversaciones en tiempo real con transcripción, traducción bidireccional, participantes, voz y asistencia (HU-23 a 31) y glosarios (HU-32).

## Sprint 4 (71 puntos)
Objetivo: integrar TraduContext con Google Meet y Zoom, personalizar la traducción por usuario y completar el módulo administrativo. El módulo de planes quedó fuera del alcance.

| HU | Nombre | Prioridad | PHU |
|---|---|---|---|
| HU-05 | Administración de usuarios | Media | 5 |
| HU-46 | Dashboard administrativo | Media | 5 |
| HU-47 | Reportes administrativos | Baja | 5 |
| HU-48 | Exportación de reportes | Baja | 3 |
| HU-33 | Preferencias de traducción | Media | 3 |
| HU-34 | Aprendizaje de preferencias | Media | 8 |
| HU-44 | Reutilización de traducciones | Media | 5 |
| HU-35 | Conexión con plataformas | Media | 5 |
| HU-36 | Configuración de sesión externa | Media | 3 |
| HU-37 | Captura de sesión externa | Media | 8 |
| HU-38 | Traducción de sesiones externas | Media | 8 |
| HU-39 | Traducción visible en integraciones | Media | 5 |
| HU-40 | Participantes de sesión externa | Baja | 5 |
| HU-41 | Control de traducción externa | Media | 3 |

## Orden sugerido para empezar (de lo más fácil a lo más difícil)
1. **HU-33 Preferencias de traducción** (3 pts). Es un CRUD simple, no depende de servicios externos y la usan HU-36 y otras.
2. **HU-05 Administración de usuarios** (5 pts). Es un CRUD sobre la tabla de usuarios que ya existe, más el control por rol.
3. **HU-46 Dashboard y HU-47 Reportes**. Son consultas con agregaciones sobre datos que ya existen.
4. **HU-48 Exportación**. Requiere tener lista la HU-47.
5. **HU-44 y HU-34**. Se apoyan en el historial y en la traducción existentes.
6. **HU-35 a HU-41 (Meet y Zoom)**. Son las más difíciles: OAuth, captura de audio y tiempo real. Conviene revisar antes los límites de las API de Meet y Zoom.

## Detalle de cada HU
### HU-05 Administración de usuarios (Media, 5 pts)
Como Administrador, quiero consultar y gestionar las cuentas registradas en la plataforma, para controlar los usuarios de la plataforma y su estado.

Implementar el módulo de administración de usuarios, accesible solo para el rol Administrador. Permitirá listar las cuentas registradas, buscarlas, consultar su detalle, cambiar su rol y activar o suspender su acceso, sin eliminar la información asociada.

Criterios de aceptación:
- El sistema debe mostrar el listado paginado de usuarios con nombre, correo, rol, estado y fecha de registro.
- El administrador debe poder buscar usuarios por nombre o correo y filtrarlos por rol y estado.
- El administrador debe poder consultar el detalle de una cuenta.
- El administrador debe poder suspender y reactivar una cuenta, con confirmación previa.
- Un usuario suspendido no debe poder iniciar sesión y sus sesiones activas deben invalidarse.
- El administrador debe poder cambiar el rol de un usuario.
- El administrador no debe poder suspender su propia cuenta ni quitarse el rol de Administrador.
- Solo el rol Administrador debe acceder a este módulo; el resto recibe HTTP 403.

### HU-46 Dashboard administrativo (Media, 5 pts)
Como Administrador, quiero visualizar indicadores generales de la plataforma, para conocer su nivel de uso y actividad.

Implementar un panel para el administrador con indicadores calculados a partir de los datos registrados: usuarios, traducciones de texto y documentos, conversaciones, sesiones externas, idiomas y contextos más utilizados. Los indicadores podrán consultarse por período.

Criterios de aceptación:
- El dashboard debe mostrar el total de usuarios registrados y de usuarios activos en el período.
- Debe mostrar la cantidad de traducciones de texto, documentos traducidos, conversaciones y sesiones externas.
- Debe mostrar los idiomas y contextos más utilizados.
- Debe mostrar la evolución de las traducciones en el tiempo mediante un gráfico.
- El administrador debe poder cambiar el período de los indicadores (por ejemplo: últimos 7 días, 30 días o rango personalizado).
- Los indicadores deben calcularse con los datos reales de la plataforma.
- Solo el rol Administrador debe acceder al dashboard.

### HU-47 Reportes administrativos (Baja, 5 pts)
Como Administrador, quiero generar reportes de actividad aplicando filtros por fechas, tipo de servicio, idioma y contexto, para analizar la actividad de la plataforma.

Implementar la generación de reportes sobre la actividad registrada en la plataforma. El administrador seleccionará los filtros y el sistema mostrará el resultado en forma de tabla con sus totales.

Criterios de aceptación:
- El sistema debe permitir filtrar por rango de fechas.
- Debe permitir filtrar por tipo de servicio: texto, documento, conversación o sesión externa.
- Debe permitir filtrar por idioma de origen, idioma de destino y contexto.
- Los filtros deben poder combinarse.
- El reporte debe mostrar el detalle de las actividades y sus totales.
- El sistema debe validar que la fecha inicial no sea posterior a la final.
- El sistema debe informar cuando no existan resultados.
- Solo el rol Administrador debe generar reportes.

### HU-48 Exportación de reportes (Baja, 3 pts)
Como Administrador, quiero exportar los reportes generados, para utilizarlos fuera de la plataforma y conservar los resultados obtenidos.

Implementar la exportación de un reporte generado en la HU-47 a archivos descargables, conservando los datos y los filtros aplicados.

Criterios de aceptación:
- El sistema debe permitir exportar el reporte en PDF y en Excel (.xlsx).
- El archivo debe contener los mismos datos y totales mostrados en pantalla.
- El archivo debe indicar los filtros aplicados y la fecha de generación.
- El nombre del archivo debe incluir el tipo de reporte y la fecha.
- La exportación solo debe estar disponible cuando exista un reporte generado.
- El sistema debe informar si ocurre un error durante la exportación.

### HU-33 Preferencias de traducción (Media, 3 pts)
Como Usuario, quiero guardar mis preferencias habituales de traducción, para aplicarlas automáticamente en futuras traducciones.

Implementar la configuración de preferencias de traducción del usuario: idioma de destino preferido, tono, variante regional, contexto y glosario predeterminados. Estas preferencias se cargarán automáticamente al iniciar una traducción de texto, documento o conversación, y el usuario podrá cambiarlas para una solicitud puntual sin modificar las guardadas.

Criterios de aceptación:
- El usuario debe poder definir idioma de destino, tono, variante regional, contexto y glosario predeterminados.
- El sistema debe guardar las preferencias asociadas al usuario autenticado.
- Las preferencias deben aplicarse automáticamente al abrir una nueva traducción de texto, documento o conversación.
- El usuario debe poder cambiar un valor para una traducción puntual sin alterar sus preferencias guardadas.
- El sistema debe validar que la variante regional sea compatible con el idioma de destino.
- El usuario debe poder restablecer los valores por defecto.
- Las preferencias deben mantenerse entre sesiones.

### HU-34 Aprendizaje de preferencias (Media, 8 pts)
Como Usuario, quiero que el sistema considere mis correcciones y elecciones anteriores, para adaptar progresivamente las traducciones a mis preferencias.

Implementar el registro de las correcciones manuales que el usuario hace sobre una traducción y de las alternativas que elige (HU-18). El sistema usará estos registros como ejemplos para orientar las siguientes traducciones del mismo usuario en el mismo par de idiomas, y el usuario podrá consultar y borrar lo aprendido.

Criterios de aceptación:
- El usuario debe poder editar el resultado de una traducción y guardar su corrección.
- El sistema debe registrar la corrección con el texto original, la traducción generada, la versión corregida y el par de idiomas.
- El sistema debe registrar la alternativa seleccionada cuando el usuario elige una (HU-18).
- Las siguientes traducciones del mismo usuario y par de idiomas deben considerar las correcciones registradas.
- El aprendizaje debe aplicarse solo al usuario que lo generó.
- El usuario debe poder activar o desactivar el aprendizaje.
- El usuario debe poder consultar y eliminar las correcciones registradas.

### HU-44 Reutilización de traducciones (Media, 5 pts)
Como Usuario, quiero recibir sugerencias basadas en traducciones anteriores similares, para mantener la consistencia en términos y expresiones.

Implementar la búsqueda de traducciones similares en el historial del usuario (HU-42) al momento de traducir un contenido nuevo. Cuando encuentre coincidencias en el mismo par de idiomas, el sistema las mostrará como referencia para que el usuario pueda reutilizarlas.

Criterios de aceptación:
- Al ingresar un texto, el sistema debe buscar traducciones similares en el historial del usuario para el mismo par de idiomas.
- El sistema debe mostrar como máximo 3 sugerencias, ordenadas por similitud.
- Cada sugerencia debe mostrar el texto original, su traducción y la fecha.
- El usuario debe poder usar una sugerencia como resultado o ignorarla.
- Solo deben considerarse traducciones del usuario autenticado.
- Si no hay coincidencias, el sistema debe traducir normalmente sin mostrar sugerencias.
- Las traducciones eliminadas del historial no deben sugerirse.

### HU-35 Conexión con plataformas (Media, 5 pts)
Como Usuario, quiero vincular y desvincular mi cuenta de Google Meet y de Zoom, para utilizar las funciones de traducción durante llamadas o reuniones.

Implementar la vinculación de la cuenta del usuario con Google Meet y Zoom mediante la autorización OAuth de cada plataforma. El sistema guardará de forma segura los tokens de acceso y mostrará el estado de cada conexión.

Criterios de aceptación:
- El sistema debe mostrar las plataformas compatibles: Google Meet y Zoom.
- El usuario debe poder vincular cada plataforma mediante su pantalla de autorización oficial (OAuth).
- El sistema debe solicitar solo los permisos necesarios y mostrarlos antes de autorizar.
- Los tokens deben almacenarse cifrados y asociados al usuario.
- El sistema debe mostrar el estado de cada conexión (vinculada, no vinculada, expirada).
- El usuario debe poder desvincular una plataforma, y el sistema debe revocar y eliminar sus tokens.
- Si la autorización falla o se cancela, el sistema debe informarlo sin vincular la cuenta.

### HU-36 Configuración de sesión externa (Media, 3 pts)
Como Usuario, quiero configurar idiomas, contexto y preferencias para una reunión externa, para adaptar el servicio de traducción a la sesión.

Implementar la configuración de una sesión de traducción asociada a una reunión de Google Meet o Zoom. El usuario indicará la reunión (enlace o identificador), los idiomas, el contexto, el entorno, el tono y el glosario, partiendo de sus preferencias guardadas (HU-33).

Criterios de aceptación:
- El usuario debe poder elegir la plataforma vinculada e indicar la reunión mediante su enlace o identificador.
- El sistema debe validar que el enlace corresponda a la plataforma elegida.
- El usuario debe poder definir los idiomas de los participantes, el contexto, el entorno, el tono y el glosario.
- La configuración debe cargarse inicialmente con las preferencias del usuario.
- El usuario debe poder modificar la configuración antes y durante la reunión.
- Los cambios durante la reunión deben aplicarse a las intervenciones siguientes.
- No debe permitirse configurar una sesión con una plataforma no vinculada.

### HU-37 Captura de sesión externa (Media, 8 pts)
Como Usuario, quiero que el sistema obtenga el audio o las transcripciones de una reunión de Google Meet o Zoom, para procesarlos mediante las funciones de traducción.

Implementar la obtención del contenido de la reunión mediante los mecanismos que ofrezca cada plataforma (API de medios o transcripción) o, como alternativa, la captura del audio desde el dispositivo del usuario. El contenido obtenido se enviará al servicio de transcripción del Sprint 3.

Criterios de aceptación:
- El sistema debe obtener el audio o la transcripción de la reunión configurada.
- Si la plataforma no permite el acceso por API, el sistema debe permitir capturar el audio desde el dispositivo del usuario, previa autorización del navegador.
- El audio capturado debe enviarse al servicio de transcripción en fragmentos durante la reunión.
- El sistema debe indicar al usuario que la captura está activa.
- El sistema debe informar cuando se pierda la conexión con la reunión o falle la captura.
- El sistema no debe capturar contenido sin que el usuario haya iniciado el servicio.

### HU-38 Traducción de sesiones externas (Media, 8 pts)
Como Usuario, quiero utilizar la traducción contextual y bidireccional durante reuniones de Google Meet o Zoom, para comunicarme con participantes que hablan otros idiomas.

Aplicar a las intervenciones capturadas (HU-37) la traducción bidireccional y contextual desarrollada en el Sprint 3, usando la configuración de la sesión externa (HU-36) y el contexto acumulado de la conversación.

Criterios de aceptación:
- El sistema debe traducir cada intervención transcrita al idioma correspondiente según la configuración de la sesión.
- La traducción debe funcionar en ambos sentidos.
- Debe aplicar el contexto, entorno, tono y glosario configurados.
- Debe considerar las intervenciones anteriores de la misma reunión.
- Las traducciones deben generarse conforme avanza la reunión, sin esperar a que termine.
- El sistema debe informar cuando una intervención no pueda traducirse, sin detener el servicio.
- Al finalizar, la sesión debe registrarse en el historial del usuario.

### HU-39 Traducción visible en integraciones (Media, 5 pts)
Como Usuario, quiero visualizar o escuchar las traducciones producidas durante una reunión externa, para seguir la conversación desde la aplicación.

Implementar la presentación de las traducciones de la reunión externa en TraduContext: un panel de subtítulos en tiempo real y la reproducción por voz (HU-28), que el usuario puede usar en paralelo a la ventana de Meet o Zoom.

Criterios de aceptación:
- El sistema debe mostrar las traducciones como subtítulos conforme se generan.
- Cada subtítulo debe mostrar el participante, el texto original y la traducción.
- El usuario debe poder elegir ver solo la traducción o ambos textos.
- El usuario debe poder activar la reproducción por voz de las traducciones.
- El usuario debe poder ajustar el tamaño del texto.
- El panel debe permitir desplazarse para consultar intervenciones anteriores.
- El sistema debe informar cuando no haya traducciones disponibles o la sesión esté pausada.

### HU-40 Participantes de sesión externa (Baja, 5 pts)
Como Usuario, quiero identificar a los participantes y sus intervenciones en una reunión externa, para seguir correctamente conversaciones con varias personas.

Asociar cada intervención de la reunión con su participante usando la información que entregue la plataforma (nombre del participante o hablante activo). Cuando la plataforma no la entregue, se usará la identificación de participantes del Sprint 3 (HU-31).

Criterios de aceptación:
- El sistema debe obtener la lista de participantes cuando la plataforma la proporcione.
- Cada intervención debe asociarse con el nombre del participante cuando sea posible.
- Si la plataforma no informa el hablante, el sistema debe usar etiquetas genéricas (Participante 1, 2…).
- El usuario debe poder renombrar una etiqueta genérica.
- El sistema no debe asignar una identidad incorrecta cuando no pueda determinar el hablante.
- La identificación debe mostrarse en los subtítulos (HU-39) y en el historial.

### HU-41 Control de traducción externa (Media, 3 pts)
Como Usuario, quiero iniciar, pausar, reanudar y finalizar la traducción de una reunión externa, para controlar el servicio sin finalizar la llamada.

Implementar los controles del servicio de traducción de una sesión externa. Pausar detiene la captura y la traducción sin afectar la reunión en Meet o Zoom; finalizar cierra la sesión y la guarda en el historial.

Criterios de aceptación:
- El usuario debe poder iniciar el servicio en una sesión configurada.
- El usuario debe poder pausar el servicio; mientras esté pausado no debe capturarse ni traducirse contenido.
- El usuario debe poder reanudar el servicio manteniendo la configuración y el contexto acumulado.
- El usuario debe poder finalizar el servicio con confirmación previa.
- Ninguna acción debe cortar ni afectar la llamada en la plataforma externa.
- El sistema debe mostrar en todo momento el estado del servicio (activo, pausado, finalizado).
- Al finalizar, la sesión debe quedar registrada en el historial.
