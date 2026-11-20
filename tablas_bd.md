# Tablas de la base de datos

Generado automáticamente el 2026-11-20 06:42:23 por SW1 (`docs/herramientas/generar_diagrama_bd.js`). Esquema `public`, sin `alembic_version`.

## Resumen

- **Número de tablas:** 27
- **Número de relaciones (claves foráneas):** 61

| Módulo | Tablas | Nº |
|---|---|---|
| Seguridad y usuarios | [usuario](#usuario), [rol](#rol), [permiso](#permiso), [rol_permiso](#rol_permiso), [sesion](#sesion), [codigo_verificacion](#codigo_verificacion) | 6 |
| Traducción e historial | [traduccion](#traduccion), [idioma](#idioma), [tono](#tono), [contexto](#contexto), [variante_regional](#variante_regional), [configuracion_traduccion](#configuracion_traduccion), [correccion_traduccion](#correccion_traduccion) | 7 |
| Documentos | [documento](#documento), [traduccion_documento](#traduccion_documento) | 2 |
| Glosarios | [glosario](#glosario), [termino_glosario](#termino_glosario) | 2 |
| Conversaciones | [conversacion](#conversacion), [entorno](#entorno), [intervencion](#intervencion), [participante_conversacion](#participante_conversacion), [conexion_plataforma](#conexion_plataforma), [sesion_externa](#sesion_externa), [participante_externo](#participante_externo), [intervencion_externa](#intervencion_externa) | 8 |
| Notificaciones | [notificacion](#notificacion), [dispositivo_push](#dispositivo_push) | 2 |

## codigo_verificacion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id | `integer` | No | `nextval('codigo_verificacion_id_seq'::regclass)` | PK |
| id_usuario | `integer` | No |  | FK |
| codigo | `character varying(6)` | No |  |  |
| expira_en | `timestamp with time zone` | No |  |  |
| utilizado | `boolean` | No |  |  |
| creado_en | `timestamp with time zone` | No | `now()` |  |

**Restricciones**

- **PK** `codigo_verificacion_pkey`: (id)
- **FK** `codigo_verificacion_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos

**Índices**

- `codigo_verificacion_pkey` (primario): `CREATE UNIQUE INDEX codigo_verificacion_pkey ON public.codigo_verificacion USING btree (id)`
- `ix_codigo_verificacion_codigo` (normal): `CREATE INDEX ix_codigo_verificacion_codigo ON public.codigo_verificacion USING btree (codigo)`
- `ix_codigo_verificacion_id` (normal): `CREATE INDEX ix_codigo_verificacion_id ON public.codigo_verificacion USING btree (id)`
- `ix_codigo_verificacion_id_usuario` (normal): `CREATE INDEX ix_codigo_verificacion_id_usuario ON public.codigo_verificacion USING btree (id_usuario)`

## conexion_plataforma

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_conexion | `integer` | No | `nextval('conexion_plataforma_id_conexion_seq'::regclass)` | PK |
| id_usuario | `integer` | No |  | FK, UK |
| plataforma | `character varying(20)` | No |  | UK |
| access_token_cifrado | `text` | No |  |  |
| refresh_token_cifrado | `text` | Sí |  |  |
| fecha_expiracion | `timestamp with time zone` | Sí |  |  |
| alcances | `text` | Sí |  |  |
| cuenta_externa | `character varying(255)` | Sí |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |

**Restricciones**

- **PK** `conexion_plataforma_pkey`: (id_conexion)
- **FK** `conexion_plataforma_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **UNIQUE** `uq_conexion_plataforma_usuario`: (id_usuario, plataforma)
- **CHECK** `ck_conexion_plataforma_plataforma`: `CHECK (((plataforma)::text = ANY ((ARRAY['google_meet'::character varying, 'zoom'::character varying])::text[])))`

**Índices**

- `conexion_plataforma_pkey` (primario): `CREATE UNIQUE INDEX conexion_plataforma_pkey ON public.conexion_plataforma USING btree (id_conexion)`
- `ix_conexion_plataforma_id_conexion` (normal): `CREATE INDEX ix_conexion_plataforma_id_conexion ON public.conexion_plataforma USING btree (id_conexion)`
- `ix_conexion_plataforma_id_usuario` (normal): `CREATE INDEX ix_conexion_plataforma_id_usuario ON public.conexion_plataforma USING btree (id_usuario)`
- `uq_conexion_plataforma_usuario` (único): `CREATE UNIQUE INDEX uq_conexion_plataforma_usuario ON public.conexion_plataforma USING btree (id_usuario, plataforma)`

## configuracion_traduccion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_configuracion_traduccion | `integer` | No | `nextval('configuracion_traduccion_id_configuracion_traduccion_seq'::regclass)` | PK |
| explicar_expresiones | `boolean` | No |  |  |
| generar_alternativas | `boolean` | No |  |  |
| id_contexto | `integer` | No |  | FK |
| id_tono | `integer` | Sí |  | FK |
| id_variante_regional | `integer` | Sí |  | FK |
| id_usuario | `integer` | Sí |  | FK, UK |
| id_idioma_destino | `integer` | Sí |  | FK |
| id_glosario | `integer` | Sí |  | FK |

**Restricciones**

- **PK** `configuracion_traduccion_pkey`: (id_configuracion_traduccion)
- **FK** `configuracion_traduccion_id_contexto_fkey`: (id_contexto) → `contexto`(id_contexto) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `configuracion_traduccion_id_tono_fkey`: (id_tono) → `tono`(id_tono) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `configuracion_traduccion_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a 1 (opcional)
- **FK** `configuracion_traduccion_id_variante_regional_fkey`: (id_variante_regional) → `variante_regional`(id_variante_regional) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `fk_configuracion_traduccion_glosario`: (id_glosario) → `glosario`(id_glosario) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `fk_configuracion_traduccion_idioma_destino`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)

**Índices**

- `configuracion_traduccion_pkey` (primario): `CREATE UNIQUE INDEX configuracion_traduccion_pkey ON public.configuracion_traduccion USING btree (id_configuracion_traduccion)`
- `ix_configuracion_traduccion_id_configuracion_traduccion` (normal): `CREATE INDEX ix_configuracion_traduccion_id_configuracion_traduccion ON public.configuracion_traduccion USING btree (id_configuracion_traduccion)`
- `ix_configuracion_traduccion_id_usuario` (único): `CREATE UNIQUE INDEX ix_configuracion_traduccion_id_usuario ON public.configuracion_traduccion USING btree (id_usuario)`

## contexto

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_contexto | `integer` | No | `nextval('contexto_id_contexto_seq'::regclass)` | PK |
| nombre | `character varying(100)` | No |  |  |
| descripcion | `text` | Sí |  |  |
| personalizado | `boolean` | No |  |  |
| activo | `boolean` | No |  |  |
| id_usuario | `integer` | Sí |  | FK |

**Restricciones**

- **PK** `contexto_pkey`: (id_contexto)
- **FK** `contexto_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)

**Índices**

- `contexto_pkey` (primario): `CREATE UNIQUE INDEX contexto_pkey ON public.contexto USING btree (id_contexto)`
- `ix_contexto_id_contexto` (normal): `CREATE INDEX ix_contexto_id_contexto ON public.contexto USING btree (id_contexto)`

## conversacion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_conversacion | `integer` | No | `nextval('conversacion_id_conversacion_seq'::regclass)` | PK |
| estado | `character varying(20)` | No | `'activa'::character varying` |  |
| fecha_inicio | `timestamp with time zone` | No | `now()` |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |
| fecha_fin | `timestamp with time zone` | Sí |  |  |
| id_usuario | `integer` | No |  | FK |
| id_idioma_origen | `integer` | No |  | FK |
| id_idioma_destino | `integer` | No |  | FK |
| id_contexto | `integer` | Sí |  | FK |
| id_entorno | `integer` | No |  | FK |
| id_tono | `integer` | Sí |  | FK |
| descripcion_contexto | `text` | Sí |  |  |
| mantener_contexto | `boolean` | No | `true` |  |
| asistencia_conversacional | `boolean` | No | `false` |  |
| id_glosario | `integer` | Sí |  | FK |

**Restricciones**

- **PK** `conversacion_pkey`: (id_conversacion)
- **FK** `conversacion_id_contexto_fkey`: (id_contexto) → `contexto`(id_contexto) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `conversacion_id_entorno_fkey`: (id_entorno) → `entorno`(id_entorno) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `conversacion_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `conversacion_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `conversacion_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **FK** `fk_conversacion_glosario`: (id_glosario) → `glosario`(id_glosario) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `fk_conversacion_id_tono_tono`: (id_tono) → `tono`(id_tono) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **CHECK** `ck_conversacion_estado`: `CHECK (((estado)::text = ANY ((ARRAY['activa'::character varying, 'pausada'::character varying, 'finalizada'::character varying])::text[])))`
- **CHECK** `ck_conversacion_idiomas_distintos`: `CHECK ((id_idioma_origen <> id_idioma_destino))`

**Índices**

- `conversacion_pkey` (primario): `CREATE UNIQUE INDEX conversacion_pkey ON public.conversacion USING btree (id_conversacion)`
- `ix_conversacion_id_conversacion` (normal): `CREATE INDEX ix_conversacion_id_conversacion ON public.conversacion USING btree (id_conversacion)`
- `ix_conversacion_id_usuario` (normal): `CREATE INDEX ix_conversacion_id_usuario ON public.conversacion USING btree (id_usuario)`

## correccion_traduccion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_correccion | `integer` | No | `nextval('correccion_traduccion_id_correccion_seq'::regclass)` | PK |
| id_usuario | `integer` | No |  | FK |
| id_idioma_origen | `integer` | No |  | FK |
| id_idioma_destino | `integer` | No |  | FK |
| texto_original | `text` | No |  |  |
| traduccion_generada | `text` | No |  |  |
| traduccion_corregida | `text` | No |  |  |
| tipo | `character varying(20)` | No |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |

**Restricciones**

- **PK** `correccion_traduccion_pkey`: (id_correccion)
- **FK** `correccion_traduccion_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `correccion_traduccion_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `correccion_traduccion_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **CHECK** `ck_correccion_traduccion_idiomas_distintos`: `CHECK ((id_idioma_origen <> id_idioma_destino))`
- **CHECK** `ck_correccion_traduccion_tipo`: `CHECK (((tipo)::text = ANY ((ARRAY['correccion'::character varying, 'alternativa'::character varying])::text[])))`

**Índices**

- `correccion_traduccion_pkey` (primario): `CREATE UNIQUE INDEX correccion_traduccion_pkey ON public.correccion_traduccion USING btree (id_correccion)`
- `ix_correccion_traduccion_id_correccion` (normal): `CREATE INDEX ix_correccion_traduccion_id_correccion ON public.correccion_traduccion USING btree (id_correccion)`
- `ix_correccion_traduccion_usuario_par` (normal): `CREATE INDEX ix_correccion_traduccion_usuario_par ON public.correccion_traduccion USING btree (id_usuario, id_idioma_origen, id_idioma_destino)`

## dispositivo_push

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_dispositivo | `integer` | No | `nextval('dispositivo_push_id_dispositivo_seq'::regclass)` | PK |
| id_usuario | `integer` | No |  | FK |
| token_fcm | `character varying(512)` | No |  | UK |
| plataforma | `character varying(20)` | No |  |  |
| activo | `boolean` | No | `true` |  |
| fecha_registro | `timestamp with time zone` | No | `now()` |  |
| fecha_ultimo_uso | `timestamp with time zone` | Sí |  |  |

**Restricciones**

- **PK** `dispositivo_push_pkey`: (id_dispositivo)
- **FK** `dispositivo_push_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **UNIQUE** `dispositivo_push_token_fcm_key`: (token_fcm)
- **CHECK** `ck_dispositivo_push_plataforma`: `CHECK (((plataforma)::text = ANY ((ARRAY['android'::character varying, 'ios'::character varying])::text[])))`

**Índices**

- `dispositivo_push_pkey` (primario): `CREATE UNIQUE INDEX dispositivo_push_pkey ON public.dispositivo_push USING btree (id_dispositivo)`
- `dispositivo_push_token_fcm_key` (único): `CREATE UNIQUE INDEX dispositivo_push_token_fcm_key ON public.dispositivo_push USING btree (token_fcm)`
- `ix_dispositivo_push_id_dispositivo` (normal): `CREATE INDEX ix_dispositivo_push_id_dispositivo ON public.dispositivo_push USING btree (id_dispositivo)`
- `ix_dispositivo_push_usuario_activo` (normal): `CREATE INDEX ix_dispositivo_push_usuario_activo ON public.dispositivo_push USING btree (id_usuario, activo)`

## documento

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_documento | `integer` | No | `nextval('documento_id_documento_seq'::regclass)` | PK |
| nombre | `character varying(255)` | No |  |  |
| tipo_mime | `character varying(100)` | No |  |  |
| extension | `character varying(20)` | No |  |  |
| tamano | `bigint` | No |  |  |
| ruta_archivo | `character varying(500)` | No |  |  |
| fecha_carga | `timestamp with time zone` | No | `now()` |  |
| id_usuario | `integer` | No |  | FK |
| id_idioma_origen | `integer` | Sí |  | FK |
| id_configuracion_traduccion | `integer` | Sí |  | FK |

**Restricciones**

- **PK** `documento_pkey`: (id_documento)
- **FK** `documento_id_configuracion_traduccion_fkey`: (id_configuracion_traduccion) → `configuracion_traduccion`(id_configuracion_traduccion) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `documento_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `documento_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos

**Índices**

- `documento_pkey` (primario): `CREATE UNIQUE INDEX documento_pkey ON public.documento USING btree (id_documento)`
- `ix_documento_id_documento` (normal): `CREATE INDEX ix_documento_id_documento ON public.documento USING btree (id_documento)`

## entorno

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_entorno | `integer` | No | `nextval('entorno_id_entorno_seq'::regclass)` | PK |
| nombre | `character varying(50)` | No |  | UK |
| descripcion | `text` | Sí |  |  |
| activo | `boolean` | No |  |  |

**Restricciones**

- **PK** `entorno_pkey`: (id_entorno)
- **UNIQUE** `entorno_nombre_key`: (nombre)

**Índices**

- `entorno_nombre_key` (único): `CREATE UNIQUE INDEX entorno_nombre_key ON public.entorno USING btree (nombre)`
- `entorno_pkey` (primario): `CREATE UNIQUE INDEX entorno_pkey ON public.entorno USING btree (id_entorno)`
- `ix_entorno_id_entorno` (normal): `CREATE INDEX ix_entorno_id_entorno ON public.entorno USING btree (id_entorno)`

## glosario

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_glosario | `integer` | No | `nextval('glosario_id_glosario_seq'::regclass)` | PK |
| nombre | `character varying(100)` | No |  |  |
| descripcion | `text` | Sí |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |
| id_usuario | `integer` | No |  | FK |
| id_idioma_origen | `integer` | No |  | FK |
| id_idioma_destino | `integer` | No |  | FK |

**Restricciones**

- **PK** `glosario_pkey`: (id_glosario)
- **FK** `glosario_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `glosario_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `glosario_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **CHECK** `ck_glosario_idiomas_distintos`: `CHECK ((id_idioma_origen <> id_idioma_destino))`

**Índices**

- `glosario_pkey` (primario): `CREATE UNIQUE INDEX glosario_pkey ON public.glosario USING btree (id_glosario)`
- `ix_glosario_id_glosario` (normal): `CREATE INDEX ix_glosario_id_glosario ON public.glosario USING btree (id_glosario)`
- `ix_glosario_id_usuario` (normal): `CREATE INDEX ix_glosario_id_usuario ON public.glosario USING btree (id_usuario)`

## idioma

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_idioma | `integer` | No | `nextval('idioma_id_idioma_seq'::regclass)` | PK |
| nombre | `character varying(50)` | No |  | UK |
| codigo | `character varying(10)` | No |  | UK |

**Restricciones**

- **PK** `idioma_pkey`: (id_idioma)
- **UNIQUE** `idioma_codigo_key`: (codigo)
- **UNIQUE** `idioma_nombre_key`: (nombre)

**Índices**

- `idioma_codigo_key` (único): `CREATE UNIQUE INDEX idioma_codigo_key ON public.idioma USING btree (codigo)`
- `idioma_nombre_key` (único): `CREATE UNIQUE INDEX idioma_nombre_key ON public.idioma USING btree (nombre)`
- `idioma_pkey` (primario): `CREATE UNIQUE INDEX idioma_pkey ON public.idioma USING btree (id_idioma)`
- `ix_idioma_id_idioma` (normal): `CREATE INDEX ix_idioma_id_idioma ON public.idioma USING btree (id_idioma)`

## intervencion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_intervencion | `integer` | No | `nextval('intervencion_id_intervencion_seq'::regclass)` | PK |
| id_conversacion | `integer` | No |  | FK, UK |
| id_participante | `integer` | Sí |  | FK |
| orden | `integer` | No |  | UK |
| texto_original | `text` | No |  |  |
| texto_traducido | `text` | Sí |  |  |
| id_idioma_origen | `integer` | No |  | FK |
| id_idioma_destino | `integer` | No |  | FK |
| estado | `character varying(20)` | No | `'procesando'::character varying` |  |
| mensaje_error | `text` | Sí |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |

**Restricciones**

- **PK** `intervencion_pkey`: (id_intervencion)
- **FK** `intervencion_id_conversacion_fkey`: (id_conversacion) → `conversacion`(id_conversacion) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **FK** `intervencion_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `intervencion_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `intervencion_id_participante_fkey`: (id_participante) → `participante_conversacion`(id_participante) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **UNIQUE** `uq_intervencion_conversacion_orden`: (id_conversacion, orden)
- **CHECK** `ck_intervencion_estado`: `CHECK (((estado)::text = ANY ((ARRAY['procesando'::character varying, 'traducida'::character varying, 'error'::character varying])::text[])))`
- **CHECK** `ck_intervencion_idiomas_distintos`: `CHECK ((id_idioma_origen <> id_idioma_destino))`

**Índices**

- `intervencion_pkey` (primario): `CREATE UNIQUE INDEX intervencion_pkey ON public.intervencion USING btree (id_intervencion)`
- `ix_intervencion_id_conversacion` (normal): `CREATE INDEX ix_intervencion_id_conversacion ON public.intervencion USING btree (id_conversacion)`
- `ix_intervencion_id_intervencion` (normal): `CREATE INDEX ix_intervencion_id_intervencion ON public.intervencion USING btree (id_intervencion)`
- `uq_intervencion_conversacion_orden` (único): `CREATE UNIQUE INDEX uq_intervencion_conversacion_orden ON public.intervencion USING btree (id_conversacion, orden)`

## intervencion_externa

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_intervencion | `integer` | No | `nextval('intervencion_externa_id_intervencion_seq'::regclass)` | PK |
| id_sesion_externa | `integer` | No |  | FK, UK |
| id_participante | `integer` | Sí |  | FK |
| orden | `integer` | No |  | UK |
| texto_original | `text` | No |  |  |
| texto_traducido | `text` | Sí |  |  |
| id_idioma_origen | `integer` | Sí |  | FK |
| id_idioma_destino | `integer` | Sí |  | FK |
| estado | `character varying(20)` | No |  |  |
| mensaje_error | `text` | Sí |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |

**Restricciones**

- **PK** `intervencion_externa_pkey`: (id_intervencion)
- **FK** `intervencion_externa_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `intervencion_externa_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `intervencion_externa_id_participante_fkey`: (id_participante) → `participante_externo`(id_participante) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `intervencion_externa_id_sesion_externa_fkey`: (id_sesion_externa) → `sesion_externa`(id_sesion_externa) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **UNIQUE** `uq_intervencion_externa_orden`: (id_sesion_externa, orden)
- **CHECK** `ck_intervencion_externa_estado`: `CHECK (((estado)::text = ANY ((ARRAY['procesando'::character varying, 'traducida'::character varying, 'error'::character varying])::text[])))`

**Índices**

- `intervencion_externa_pkey` (primario): `CREATE UNIQUE INDEX intervencion_externa_pkey ON public.intervencion_externa USING btree (id_intervencion)`
- `ix_intervencion_externa_id_intervencion` (normal): `CREATE INDEX ix_intervencion_externa_id_intervencion ON public.intervencion_externa USING btree (id_intervencion)`
- `ix_intervencion_externa_id_sesion_externa` (normal): `CREATE INDEX ix_intervencion_externa_id_sesion_externa ON public.intervencion_externa USING btree (id_sesion_externa)`
- `uq_intervencion_externa_orden` (único): `CREATE UNIQUE INDEX uq_intervencion_externa_orden ON public.intervencion_externa USING btree (id_sesion_externa, orden)`

## notificacion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_notificacion | `integer` | No | `nextval('notificacion_id_notificacion_seq'::regclass)` | PK |
| id_usuario | `integer` | No |  | FK |
| tipo | `character varying(40)` | No |  |  |
| titulo | `character varying(150)` | No |  |  |
| cuerpo | `character varying(500)` | No |  |  |
| datos | `json` | Sí |  |  |
| leida | `boolean` | No | `false` |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_lectura | `timestamp with time zone` | Sí |  |  |

**Restricciones**

- **PK** `notificacion_pkey`: (id_notificacion)
- **FK** `notificacion_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **CHECK** `ck_notificacion_tipo`: `CHECK (((tipo)::text = ANY ((ARRAY['DOCUMENTO_LISTO'::character varying, 'DOCUMENTO_ERROR'::character varying, 'SISTEMA'::character varying])::text[])))`

**Índices**

- `ix_notificacion_id_notificacion` (normal): `CREATE INDEX ix_notificacion_id_notificacion ON public.notificacion USING btree (id_notificacion)`
- `ix_notificacion_usuario_leida_fecha` (normal): `CREATE INDEX ix_notificacion_usuario_leida_fecha ON public.notificacion USING btree (id_usuario, leida, fecha_creacion)`
- `notificacion_pkey` (primario): `CREATE UNIQUE INDEX notificacion_pkey ON public.notificacion USING btree (id_notificacion)`

## participante_conversacion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_participante | `integer` | No | `nextval('participante_conversacion_id_participante_seq'::regclass)` | PK |
| id_conversacion | `integer` | No |  | FK, UK |
| nombre | `character varying(100)` | No |  |  |
| id_idioma | `integer` | No |  | FK |
| orden | `integer` | No |  | UK |

**Restricciones**

- **PK** `participante_conversacion_pkey`: (id_participante)
- **FK** `participante_conversacion_id_conversacion_fkey`: (id_conversacion) → `conversacion`(id_conversacion) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **FK** `participante_conversacion_id_idioma_fkey`: (id_idioma) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **UNIQUE** `uq_participante_conversacion_orden`: (id_conversacion, orden)
- **CHECK** `ck_participante_conversacion_orden`: `CHECK ((orden = ANY (ARRAY[1, 2])))`

**Índices**

- `ix_participante_conversacion_id_conversacion` (normal): `CREATE INDEX ix_participante_conversacion_id_conversacion ON public.participante_conversacion USING btree (id_conversacion)`
- `ix_participante_conversacion_id_participante` (normal): `CREATE INDEX ix_participante_conversacion_id_participante ON public.participante_conversacion USING btree (id_participante)`
- `participante_conversacion_pkey` (primario): `CREATE UNIQUE INDEX participante_conversacion_pkey ON public.participante_conversacion USING btree (id_participante)`
- `uq_participante_conversacion_orden` (único): `CREATE UNIQUE INDEX uq_participante_conversacion_orden ON public.participante_conversacion USING btree (id_conversacion, orden)`

## participante_externo

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_participante | `integer` | No | `nextval('participante_externo_id_participante_seq'::regclass)` | PK |
| id_sesion_externa | `integer` | No |  | FK, UK |
| nombre | `character varying(100)` | No |  |  |
| orden | `integer` | No |  | UK |
| generico | `boolean` | No | `true` |  |
| id_externo | `character varying(255)` | Sí |  |  |
| desde_plataforma | `boolean` | No | `false` |  |

**Restricciones**

- **PK** `participante_externo_pkey`: (id_participante)
- **FK** `participante_externo_id_sesion_externa_fkey`: (id_sesion_externa) → `sesion_externa`(id_sesion_externa) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **UNIQUE** `uq_participante_externo_orden`: (id_sesion_externa, orden)

**Índices**

- `ix_participante_externo_id_participante` (normal): `CREATE INDEX ix_participante_externo_id_participante ON public.participante_externo USING btree (id_participante)`
- `ix_participante_externo_id_sesion_externa` (normal): `CREATE INDEX ix_participante_externo_id_sesion_externa ON public.participante_externo USING btree (id_sesion_externa)`
- `participante_externo_pkey` (primario): `CREATE UNIQUE INDEX participante_externo_pkey ON public.participante_externo USING btree (id_participante)`
- `uq_participante_externo_orden` (único): `CREATE UNIQUE INDEX uq_participante_externo_orden ON public.participante_externo USING btree (id_sesion_externa, orden)`

## permiso

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id | `integer` | No | `nextval('permiso_id_seq'::regclass)` | PK |
| nombre | `character varying(80)` | No |  | UK |
| descripcion | `character varying(255)` | Sí |  |  |

**Restricciones**

- **PK** `permiso_pkey`: (id)
- **UNIQUE** `permiso_nombre_key`: (nombre)

**Índices**

- `ix_permiso_id` (normal): `CREATE INDEX ix_permiso_id ON public.permiso USING btree (id)`
- `permiso_nombre_key` (único): `CREATE UNIQUE INDEX permiso_nombre_key ON public.permiso USING btree (nombre)`
- `permiso_pkey` (primario): `CREATE UNIQUE INDEX permiso_pkey ON public.permiso USING btree (id)`

## rol

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id | `integer` | No | `nextval('rol_id_seq'::regclass)` | PK |
| nombre | `character varying(50)` | No |  | UK |

**Restricciones**

- **PK** `rol_pkey`: (id)
- **UNIQUE** `rol_nombre_key`: (nombre)

**Índices**

- `ix_rol_id` (normal): `CREATE INDEX ix_rol_id ON public.rol USING btree (id)`
- `rol_nombre_key` (único): `CREATE UNIQUE INDEX rol_nombre_key ON public.rol USING btree (nombre)`
- `rol_pkey` (primario): `CREATE UNIQUE INDEX rol_pkey ON public.rol USING btree (id)`

## rol_permiso

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id | `integer` | No | `nextval('rol_permiso_id_seq'::regclass)` | PK |
| id_rol | `integer` | No |  | FK, UK |
| id_permiso | `integer` | No |  | FK, UK |

**Restricciones**

- **PK** `rol_permiso_pkey`: (id)
- **FK** `rol_permiso_id_permiso_fkey`: (id_permiso) → `permiso`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `rol_permiso_id_rol_fkey`: (id_rol) → `rol`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **UNIQUE** `uq_rol_permiso`: (id_rol, id_permiso)

**Índices**

- `ix_rol_permiso_id` (normal): `CREATE INDEX ix_rol_permiso_id ON public.rol_permiso USING btree (id)`
- `rol_permiso_pkey` (primario): `CREATE UNIQUE INDEX rol_permiso_pkey ON public.rol_permiso USING btree (id)`
- `uq_rol_permiso` (único): `CREATE UNIQUE INDEX uq_rol_permiso ON public.rol_permiso USING btree (id_rol, id_permiso)`

## sesion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id | `integer` | No | `nextval('sesion_id_seq'::regclass)` | PK |
| token | `character varying(255)` | No |  | UK |
| fecha_inicio | `timestamp with time zone` | No | `now()` |  |
| fecha_expiracion | `timestamp with time zone` | No |  |  |
| fecha_cierre | `timestamp with time zone` | Sí |  |  |
| estado | `character varying(20)` | No |  |  |
| id_usuario | `integer` | No |  | FK |

**Restricciones**

- **PK** `sesion_pkey`: (id)
- **FK** `sesion_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **CHECK** `ck_sesion_estado`: `CHECK (((estado)::text = ANY ((ARRAY['ACTIVA'::character varying, 'CERRADA'::character varying, 'EXPIRADA'::character varying])::text[])))`

**Índices**

- `ix_sesion_id` (normal): `CREATE INDEX ix_sesion_id ON public.sesion USING btree (id)`
- `ix_sesion_token` (único): `CREATE UNIQUE INDEX ix_sesion_token ON public.sesion USING btree (token)`
- `sesion_pkey` (primario): `CREATE UNIQUE INDEX sesion_pkey ON public.sesion USING btree (id)`

## sesion_externa

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_sesion_externa | `integer` | No | `nextval('sesion_externa_id_sesion_externa_seq'::regclass)` | PK |
| id_usuario | `integer` | No |  | FK |
| plataforma | `character varying(20)` | No |  |  |
| enlace_reunion | `text` | No |  |  |
| referencia_reunion | `character varying(64)` | No |  |  |
| estado | `character varying(20)` | No | `'configurada'::character varying` |  |
| id_idioma_origen | `integer` | No |  | FK |
| id_idioma_destino | `integer` | No |  | FK |
| id_contexto | `integer` | Sí |  | FK |
| id_entorno | `integer` | No |  | FK |
| id_tono | `integer` | Sí |  | FK |
| id_glosario | `integer` | Sí |  | FK |
| descripcion_contexto | `text` | Sí |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_inicio | `timestamp with time zone` | Sí |  |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |
| fecha_fin | `timestamp with time zone` | Sí |  |  |

**Restricciones**

- **PK** `sesion_externa_pkey`: (id_sesion_externa)
- **FK** `sesion_externa_id_contexto_fkey`: (id_contexto) → `contexto`(id_contexto) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `sesion_externa_id_entorno_fkey`: (id_entorno) → `entorno`(id_entorno) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `sesion_externa_id_glosario_fkey`: (id_glosario) → `glosario`(id_glosario) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `sesion_externa_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `sesion_externa_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `sesion_externa_id_tono_fkey`: (id_tono) → `tono`(id_tono) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `sesion_externa_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **CHECK** `ck_sesion_externa_estado`: `CHECK (((estado)::text = ANY ((ARRAY['configurada'::character varying, 'activa'::character varying, 'pausada'::character varying, 'finalizada'::character varying])::text[])))`
- **CHECK** `ck_sesion_externa_idiomas_distintos`: `CHECK ((id_idioma_origen <> id_idioma_destino))`
- **CHECK** `ck_sesion_externa_plataforma`: `CHECK (((plataforma)::text = ANY ((ARRAY['google_meet'::character varying, 'zoom'::character varying])::text[])))`

**Índices**

- `ix_sesion_externa_id_sesion_externa` (normal): `CREATE INDEX ix_sesion_externa_id_sesion_externa ON public.sesion_externa USING btree (id_sesion_externa)`
- `ix_sesion_externa_id_usuario` (normal): `CREATE INDEX ix_sesion_externa_id_usuario ON public.sesion_externa USING btree (id_usuario)`
- `sesion_externa_pkey` (primario): `CREATE UNIQUE INDEX sesion_externa_pkey ON public.sesion_externa USING btree (id_sesion_externa)`

## termino_glosario

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_termino_glosario | `integer` | No | `nextval('termino_glosario_id_termino_glosario_seq'::regclass)` | PK |
| termino_origen | `character varying(255)` | No |  |  |
| traduccion_preferida | `character varying(255)` | Sí |  |  |
| conservar_original | `boolean` | No |  |  |
| distinguir_mayusculas | `boolean` | No |  |  |
| nota | `text` | Sí |  |  |
| id_glosario | `integer` | No |  | FK |

**Restricciones**

- **PK** `termino_glosario_pkey`: (id_termino_glosario)
- **FK** `termino_glosario_id_glosario_fkey`: (id_glosario) → `glosario`(id_glosario) · ON DELETE CASCADE · ON UPDATE NO ACTION · 1 a muchos
- **CHECK** `ck_termino_glosario_regla`: `CHECK ((conservar_original OR (traduccion_preferida IS NOT NULL)))`

**Índices**

- `ix_termino_glosario_id_glosario` (normal): `CREATE INDEX ix_termino_glosario_id_glosario ON public.termino_glosario USING btree (id_glosario)`
- `ix_termino_glosario_id_termino_glosario` (normal): `CREATE INDEX ix_termino_glosario_id_termino_glosario ON public.termino_glosario USING btree (id_termino_glosario)`
- `termino_glosario_pkey` (primario): `CREATE UNIQUE INDEX termino_glosario_pkey ON public.termino_glosario USING btree (id_termino_glosario)`

## tono

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_tono | `integer` | No | `nextval('tono_id_tono_seq'::regclass)` | PK |
| nombre | `character varying(100)` | No |  |  |
| descripcion | `text` | Sí |  |  |
| activo | `boolean` | No |  |  |

**Restricciones**

- **PK** `tono_pkey`: (id_tono)

**Índices**

- `ix_tono_id_tono` (normal): `CREATE INDEX ix_tono_id_tono ON public.tono USING btree (id_tono)`
- `tono_pkey` (primario): `CREATE UNIQUE INDEX tono_pkey ON public.tono USING btree (id_tono)`

## traduccion

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_traduccion | `integer` | No | `nextval('traduccion_id_traduccion_seq'::regclass)` | PK |
| texto_original | `text` | No |  |  |
| texto_traducido | `text` | No |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| id_configuracion_traduccion | `integer` | No |  | FK |
| id_idioma_origen | `integer` | No |  | FK |
| id_idioma_destino | `integer` | No |  | FK |
| id_usuario | `integer` | No |  | FK |
| favorito | `boolean` | No | `false` |  |
| id_glosario | `integer` | Sí |  | FK |

**Restricciones**

- **PK** `traduccion_pkey`: (id_traduccion)
- **FK** `traduccion_id_configuracion_traduccion_fkey`: (id_configuracion_traduccion) → `configuracion_traduccion`(id_configuracion_traduccion) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `traduccion_id_glosario_fkey`: (id_glosario) → `glosario`(id_glosario) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `traduccion_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `traduccion_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `traduccion_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos

**Índices**

- `ix_traduccion_id_traduccion` (normal): `CREATE INDEX ix_traduccion_id_traduccion ON public.traduccion USING btree (id_traduccion)`
- `traduccion_pkey` (primario): `CREATE UNIQUE INDEX traduccion_pkey ON public.traduccion USING btree (id_traduccion)`

## traduccion_documento

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_traduccion_documento | `integer` | No | `nextval('traduccion_documento_id_traduccion_documento_seq'::regclass)` | PK |
| nombre | `character varying(255)` | No |  |  |
| extension | `character varying(20)` | No |  |  |
| estado | `character varying(30)` | No |  |  |
| fecha | `timestamp with time zone` | No | `now()` |  |
| ruta_archivo | `character varying(500)` | No |  |  |
| id_documento | `integer` | Sí |  | FK |
| id_usuario | `integer` | No |  | FK |
| id_idioma_origen | `integer` | No |  | FK |
| id_idioma_destino | `integer` | No |  | FK |
| id_glosario | `integer` | Sí |  | FK |

**Restricciones**

- **PK** `traduccion_documento_pkey`: (id_traduccion_documento)
- **FK** `traduccion_documento_id_documento_fkey`: (id_documento) → `documento`(id_documento) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `traduccion_documento_id_glosario_fkey`: (id_glosario) → `glosario`(id_glosario) · ON DELETE SET NULL · ON UPDATE NO ACTION · 1 a muchos (opcional)
- **FK** `traduccion_documento_id_idioma_destino_fkey`: (id_idioma_destino) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `traduccion_documento_id_idioma_origen_fkey`: (id_idioma_origen) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **FK** `traduccion_documento_id_usuario_fkey`: (id_usuario) → `usuario`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos

**Índices**

- `ix_traduccion_documento_id_traduccion_documento` (normal): `CREATE INDEX ix_traduccion_documento_id_traduccion_documento ON public.traduccion_documento USING btree (id_traduccion_documento)`
- `traduccion_documento_pkey` (primario): `CREATE UNIQUE INDEX traduccion_documento_pkey ON public.traduccion_documento USING btree (id_traduccion_documento)`

## usuario

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id | `integer` | No | `nextval('usuario_id_seq'::regclass)` | PK |
| nombre | `character varying(100)` | No |  |  |
| correo | `character varying(255)` | No |  | UK |
| contrasena | `character varying(255)` | No |  |  |
| fecha_creacion | `timestamp with time zone` | No | `now()` |  |
| fecha_actualizacion | `timestamp with time zone` | Sí |  |  |
| estado | `character varying(20)` | No |  |  |
| foto_perfil | `character varying(500)` | Sí |  |  |
| id_rol | `integer` | No |  | FK |
| aprendizaje_activo | `boolean` | No | `true` |  |

**Restricciones**

- **PK** `usuario_pkey`: (id)
- **FK** `usuario_id_rol_fkey`: (id_rol) → `rol`(id) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos
- **CHECK** `ck_usuario_estado`: `CHECK (((estado)::text = ANY ((ARRAY['ACTIVO'::character varying, 'INACTIVO'::character varying, 'SUSPENDIDO'::character varying])::text[])))`

**Índices**

- `ix_usuario_correo` (único): `CREATE UNIQUE INDEX ix_usuario_correo ON public.usuario USING btree (correo)`
- `ix_usuario_id` (normal): `CREATE INDEX ix_usuario_id ON public.usuario USING btree (id)`
- `usuario_pkey` (primario): `CREATE UNIQUE INDEX usuario_pkey ON public.usuario USING btree (id)`

## variante_regional

| Columna | Tipo | Nulo | Por defecto | Claves |
|---|---|---|---|---|
| id_variante_regional | `integer` | No | `nextval('variante_regional_id_variante_regional_seq'::regclass)` | PK |
| nombre | `character varying(100)` | No |  |  |
| codigo | `character varying(20)` | No |  |  |
| activo | `boolean` | No |  |  |
| id_idioma | `integer` | No |  | FK |

**Restricciones**

- **PK** `variante_regional_pkey`: (id_variante_regional)
- **FK** `variante_regional_id_idioma_fkey`: (id_idioma) → `idioma`(id_idioma) · ON DELETE NO ACTION · ON UPDATE NO ACTION · 1 a muchos

**Índices**

- `ix_variante_regional_id_variante_regional` (normal): `CREATE INDEX ix_variante_regional_id_variante_regional ON public.variante_regional USING btree (id_variante_regional)`
- `variante_regional_pkey` (primario): `CREATE UNIQUE INDEX variante_regional_pkey ON public.variante_regional USING btree (id_variante_regional)`
