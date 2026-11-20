/*
 * SW1_DiagramaBaseDatos.js  -  Script JScript para Enterprise Architect
 * -----------------------------------------------------------------------
 * Crea el paquete "SW1 - Base de Datos" con UN diagrama de clases de
 * TraduContext que contiene todas las clases (tablas de la base de datos)
 * con sus atributos y las relaciones entre ellas:
 *     - Diagrama de Clases - Base de Datos
 *
 * Las clases solo tienen atributos (nombre : tipo), sin metodos.
 * Cada relacion es una asociacion con su multiplicidad:
 *     1     ---- 0..*   (1 a muchos)
 *     0..1  ---- ...    (la clave foranea admite nulos: relacion opcional)
 *     ...   ---- 0..1   (clave foranea unica: 1 a 1)
 * El nombre de cada asociacion es el atributo que la origina (p. ej. id_usuario).
 *
 * Fuente de los datos: modelos SQLAlchemy de traducontextback/app/models
 * (31 tablas, sin alembic_version).
 *
 * COMO USARLO
 *   1. En EA: Start > Explore > Script (o Ctrl+Shift+A), "Scripting".
 *   2. Boton "New Script" > Group: JScript > Name: SW1_BD > OK.
 *   3. Pegar TODO este archivo (reemplaza el contenido de ejemplo).
 *   4. En el Project Browser selecciona el paquete donde quieres que
 *      quede el paquete (si no seleccionas ninguno, se usa el primer modelo).
 *   5. Con el cursor dentro del script, boton Run (o F5).
 */

// ---------------------------------------------------------------------------
// 1) MODELO DE DATOS
// ---------------------------------------------------------------------------
var PAQUETE = "SW1 - Base de Datos";
var DIAGRAMA = "Diagrama de Clases - Base de Datos";

// Orden de los grupos en el diagrama (cada grupo empieza en una fila nueva)
var GRUPOS = ["seguridad", "traduccion", "documentos", "glosarios", "conversaciones", "notificaciones", "chats"];

// Clases (tablas): [nombre, grupo, atributos]
//   atributo: [nombre, tipo, admite nulos, clave ("PK", "UK" o "")]
var TABLAS = [
    // --- Seguridad y usuarios
    ["usuario", "seguridad", [
        ["id", "integer", false, "PK"],
        ["nombre", "varchar(100)", false, ""],
        ["correo", "varchar(255)", false, "UK"],
        ["contrasena", "varchar(255)", false, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_actualizacion", "timestamptz", true, ""],
        ["estado", "varchar(20)", false, ""],
        ["foto_perfil", "varchar(500)", true, ""],
        ["id_rol", "integer", false, ""],
        ["aprendizaje_activo", "boolean", false, ""]]],
    ["rol", "seguridad", [
        ["id", "integer", false, "PK"],
        ["nombre", "varchar(50)", false, "UK"]]],
    ["permiso", "seguridad", [
        ["id", "integer", false, "PK"],
        ["nombre", "varchar(80)", false, "UK"],
        ["descripcion", "varchar(255)", true, ""]]],
    ["rol_permiso", "seguridad", [
        ["id", "integer", false, "PK"],
        ["id_rol", "integer", false, ""],
        ["id_permiso", "integer", false, ""]]],
    ["sesion", "seguridad", [
        ["id", "integer", false, "PK"],
        ["token", "varchar(255)", false, "UK"],
        ["fecha_inicio", "timestamptz", false, ""],
        ["fecha_expiracion", "timestamptz", false, ""],
        ["fecha_cierre", "timestamptz", true, ""],
        ["estado", "varchar(20)", false, ""],
        ["id_usuario", "integer", false, ""]]],
    ["codigo_verificacion", "seguridad", [
        ["id", "integer", false, "PK"],
        ["id_usuario", "integer", false, ""],
        ["codigo", "varchar(6)", false, ""],
        ["expira_en", "timestamptz", false, ""],
        ["utilizado", "boolean", false, ""],
        ["creado_en", "timestamptz", false, ""]]],

    // --- Traduccion e historial
    ["idioma", "traduccion", [
        ["id_idioma", "integer", false, "PK"],
        ["nombre", "varchar(50)", false, "UK"],
        ["codigo", "varchar(10)", false, "UK"]]],
    ["tono", "traduccion", [
        ["id_tono", "integer", false, "PK"],
        ["nombre", "varchar(100)", false, ""],
        ["descripcion", "text", true, ""],
        ["activo", "boolean", false, ""]]],
    ["contexto", "traduccion", [
        ["id_contexto", "integer", false, "PK"],
        ["nombre", "varchar(100)", false, ""],
        ["descripcion", "text", true, ""],
        ["personalizado", "boolean", false, ""],
        ["activo", "boolean", false, ""],
        ["id_usuario", "integer", true, ""]]],
    ["variante_regional", "traduccion", [
        ["id_variante_regional", "integer", false, "PK"],
        ["nombre", "varchar(100)", false, ""],
        ["codigo", "varchar(20)", false, ""],
        ["activo", "boolean", false, ""],
        ["id_idioma", "integer", false, ""]]],
    ["configuracion_traduccion", "traduccion", [
        ["id_configuracion_traduccion", "integer", false, "PK"],
        ["explicar_expresiones", "boolean", false, ""],
        ["generar_alternativas", "boolean", false, ""],
        ["id_contexto", "integer", false, ""],
        ["id_tono", "integer", true, ""],
        ["id_variante_regional", "integer", true, ""],
        ["id_usuario", "integer", true, "UK"],
        ["id_idioma_destino", "integer", true, ""],
        ["id_glosario", "integer", true, ""]]],
    ["traduccion", "traduccion", [
        ["id_traduccion", "integer", false, "PK"],
        ["texto_original", "text", false, ""],
        ["texto_traducido", "text", false, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["favorito", "boolean", false, ""],
        ["id_configuracion_traduccion", "integer", false, ""],
        ["id_idioma_origen", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""],
        ["id_usuario", "integer", false, ""],
        ["id_glosario", "integer", true, ""]]],
    ["correccion_traduccion", "traduccion", [
        ["id_correccion", "integer", false, "PK"],
        ["id_usuario", "integer", false, ""],
        ["id_idioma_origen", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""],
        ["texto_original", "text", false, ""],
        ["traduccion_generada", "text", false, ""],
        ["traduccion_corregida", "text", false, ""],
        ["tipo", "varchar(20)", false, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_actualizacion", "timestamptz", true, ""]]],

    // --- Documentos
    ["documento", "documentos", [
        ["id_documento", "integer", false, "PK"],
        ["nombre", "varchar(255)", false, ""],
        ["tipo_mime", "varchar(100)", false, ""],
        ["extension", "varchar(20)", false, ""],
        ["tamano", "bigint", false, ""],
        ["ruta_archivo", "varchar(500)", false, ""],
        ["fecha_carga", "timestamptz", false, ""],
        ["id_usuario", "integer", false, ""],
        ["id_idioma_origen", "integer", true, ""],
        ["id_configuracion_traduccion", "integer", true, ""]]],
    ["traduccion_documento", "documentos", [
        ["id_traduccion_documento", "integer", false, "PK"],
        ["nombre", "varchar(255)", false, ""],
        ["extension", "varchar(20)", false, ""],
        ["estado", "varchar(30)", false, ""],
        ["fecha", "timestamptz", false, ""],
        ["ruta_archivo", "varchar(500)", false, ""],
        ["id_documento", "integer", true, ""],
        ["id_usuario", "integer", false, ""],
        ["id_idioma_origen", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""],
        ["id_glosario", "integer", true, ""]]],

    // --- Glosarios
    ["glosario", "glosarios", [
        ["id_glosario", "integer", false, "PK"],
        ["nombre", "varchar(100)", false, ""],
        ["descripcion", "text", true, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_actualizacion", "timestamptz", true, ""],
        ["id_usuario", "integer", false, ""],
        ["id_idioma_origen", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""]]],
    ["termino_glosario", "glosarios", [
        ["id_termino_glosario", "integer", false, "PK"],
        ["termino_origen", "varchar(255)", false, ""],
        ["traduccion_preferida", "varchar(255)", true, ""],
        ["conservar_original", "boolean", false, ""],
        ["distinguir_mayusculas", "boolean", false, ""],
        ["nota", "text", true, ""],
        ["id_glosario", "integer", false, ""]]],

    // --- Conversaciones (incluye integraciones externas Meet/Zoom)
    ["entorno", "conversaciones", [
        ["id_entorno", "integer", false, "PK"],
        ["nombre", "varchar(50)", false, "UK"],
        ["descripcion", "text", true, ""],
        ["activo", "boolean", false, ""]]],
    ["conversacion", "conversaciones", [
        ["id_conversacion", "integer", false, "PK"],
        ["estado", "varchar(20)", false, ""],
        ["fecha_inicio", "timestamptz", false, ""],
        ["fecha_actualizacion", "timestamptz", true, ""],
        ["fecha_fin", "timestamptz", true, ""],
        ["id_usuario", "integer", false, ""],
        ["id_idioma_origen", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""],
        ["id_contexto", "integer", true, ""],
        ["id_entorno", "integer", false, ""],
        ["id_tono", "integer", true, ""],
        ["id_glosario", "integer", true, ""],
        ["descripcion_contexto", "text", true, ""],
        ["mantener_contexto", "boolean", false, ""],
        ["asistencia_conversacional", "boolean", false, ""]]],
    ["participante_conversacion", "conversaciones", [
        ["id_participante", "integer", false, "PK"],
        ["id_conversacion", "integer", false, ""],
        ["nombre", "varchar(100)", false, ""],
        ["id_idioma", "integer", false, ""],
        ["orden", "integer", false, ""]]],
    ["intervencion", "conversaciones", [
        ["id_intervencion", "integer", false, "PK"],
        ["id_conversacion", "integer", false, ""],
        ["id_participante", "integer", true, ""],
        ["orden", "integer", false, ""],
        ["texto_original", "text", false, ""],
        ["texto_traducido", "text", true, ""],
        ["id_idioma_origen", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""],
        ["estado", "varchar(20)", false, ""],
        ["mensaje_error", "text", true, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_actualizacion", "timestamptz", true, ""]]],
    ["conexion_plataforma", "conversaciones", [
        ["id_conexion", "integer", false, "PK"],
        ["id_usuario", "integer", false, ""],
        ["plataforma", "varchar(20)", false, ""],
        ["access_token_cifrado", "text", false, ""],
        ["refresh_token_cifrado", "text", true, ""],
        ["fecha_expiracion", "timestamptz", true, ""],
        ["alcances", "text", true, ""],
        ["cuenta_externa", "varchar(255)", true, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_actualizacion", "timestamptz", true, ""]]],
    ["sesion_externa", "conversaciones", [
        ["id_sesion_externa", "integer", false, "PK"],
        ["id_usuario", "integer", false, ""],
        ["plataforma", "varchar(20)", false, ""],
        ["enlace_reunion", "text", false, ""],
        ["referencia_reunion", "varchar(64)", false, ""],
        ["estado", "varchar(20)", false, ""],
        ["id_idioma_origen", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""],
        ["id_contexto", "integer", true, ""],
        ["id_entorno", "integer", false, ""],
        ["id_tono", "integer", true, ""],
        ["id_glosario", "integer", true, ""],
        ["descripcion_contexto", "text", true, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_inicio", "timestamptz", true, ""],
        ["fecha_actualizacion", "timestamptz", true, ""],
        ["fecha_fin", "timestamptz", true, ""]]],
    ["participante_externo", "conversaciones", [
        ["id_participante", "integer", false, "PK"],
        ["id_sesion_externa", "integer", false, ""],
        ["nombre", "varchar(100)", false, ""],
        ["orden", "integer", false, ""],
        ["generico", "boolean", false, ""],
        ["id_externo", "varchar(255)", true, ""],
        ["desde_plataforma", "boolean", false, ""]]],
    ["intervencion_externa", "conversaciones", [
        ["id_intervencion", "integer", false, "PK"],
        ["id_sesion_externa", "integer", false, ""],
        ["id_participante", "integer", true, ""],
        ["orden", "integer", false, ""],
        ["texto_original", "text", false, ""],
        ["texto_traducido", "text", true, ""],
        ["id_idioma_origen", "integer", true, ""],
        ["id_idioma_destino", "integer", true, ""],
        ["estado", "varchar(20)", false, ""],
        ["mensaje_error", "text", true, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_actualizacion", "timestamptz", true, ""]]],

    // --- Notificaciones
    ["dispositivo_push", "notificaciones", [
        ["id_dispositivo", "integer", false, "PK"],
        ["id_usuario", "integer", false, ""],
        ["token_fcm", "varchar(512)", false, "UK"],
        ["plataforma", "varchar(20)", false, ""],
        ["activo", "boolean", false, ""],
        ["fecha_registro", "timestamptz", false, ""],
        ["fecha_ultimo_uso", "timestamptz", true, ""]]],
    ["notificacion", "notificaciones", [
        ["id_notificacion", "integer", false, "PK"],
        ["id_usuario", "integer", false, ""],
        ["tipo", "varchar(40)", false, ""],
        ["titulo", "varchar(150)", false, ""],
        ["cuerpo", "varchar(500)", false, ""],
        ["datos", "json", true, ""],
        ["leida", "boolean", false, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_lectura", "timestamptz", true, ""]]],

    // --- Chats entre usuarios (chat 1 a 1; distinto de conversacion)
    ["chat", "chats", [
        ["id_chat", "integer", false, "PK"],
        ["id_usuario_menor", "integer", false, ""],
        ["id_usuario_mayor", "integer", false, ""],
        ["fecha_creacion", "timestamptz", false, ""],
        ["fecha_ultimo_mensaje", "timestamptz", true, ""]]],
    ["participante_chat", "chats", [
        ["id_chat", "integer", false, "PK"],
        ["id_usuario", "integer", false, "PK"],
        ["id_idioma_lectura", "integer", false, ""],
        ["id_ultimo_mensaje_leido", "integer", true, ""],
        ["fecha_union", "timestamptz", false, ""],
        ["fecha_ultimo_acceso", "timestamptz", true, ""]]],
    ["mensaje_chat", "chats", [
        ["id_mensaje", "integer", false, "PK"],
        ["id_chat", "integer", false, ""],
        ["id_remitente", "integer", false, ""],
        ["texto_original", "varchar(2000)", false, ""],
        ["id_idioma_detectado", "integer", true, ""],
        ["confianza_deteccion", "double precision", true, ""],
        ["idioma_por_respaldo", "boolean", false, ""],
        ["estado", "varchar(20)", false, ""],
        ["fecha_envio", "timestamptz", false, ""]]],
    ["traduccion_mensaje_chat", "chats", [
        ["id_traduccion", "integer", false, "PK"],
        ["id_mensaje", "integer", false, ""],
        ["id_destinatario", "integer", false, ""],
        ["id_idioma_destino", "integer", false, ""],
        ["texto_traducido", "text", true, ""],
        ["estado", "varchar(20)", false, ""],
        ["error", "varchar(300)", true, ""],
        ["fecha_actualizacion", "timestamptz", false, ""]]]
];

// Relaciones (claves foraneas): [clase, atributo, clase referenciada, atributo referenciado, ON DELETE]
var FKS = [
    ["usuario", "id_rol", "rol", "id", "NO ACTION"],
    ["rol_permiso", "id_rol", "rol", "id", "NO ACTION"],
    ["rol_permiso", "id_permiso", "permiso", "id", "NO ACTION"],
    ["sesion", "id_usuario", "usuario", "id", "NO ACTION"],
    ["codigo_verificacion", "id_usuario", "usuario", "id", "NO ACTION"],
    ["contexto", "id_usuario", "usuario", "id", "NO ACTION"],
    ["variante_regional", "id_idioma", "idioma", "id_idioma", "NO ACTION"],
    ["configuracion_traduccion", "id_contexto", "contexto", "id_contexto", "NO ACTION"],
    ["configuracion_traduccion", "id_tono", "tono", "id_tono", "NO ACTION"],
    ["configuracion_traduccion", "id_variante_regional", "variante_regional", "id_variante_regional", "NO ACTION"],
    ["configuracion_traduccion", "id_usuario", "usuario", "id", "NO ACTION"],
    ["configuracion_traduccion", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["configuracion_traduccion", "id_glosario", "glosario", "id_glosario", "SET NULL"],
    ["traduccion", "id_configuracion_traduccion", "configuracion_traduccion", "id_configuracion_traduccion", "NO ACTION"],
    ["traduccion", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["traduccion", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["traduccion", "id_usuario", "usuario", "id", "NO ACTION"],
    ["traduccion", "id_glosario", "glosario", "id_glosario", "SET NULL"],
    ["correccion_traduccion", "id_usuario", "usuario", "id", "CASCADE"],
    ["correccion_traduccion", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["correccion_traduccion", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["documento", "id_usuario", "usuario", "id", "NO ACTION"],
    ["documento", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["documento", "id_configuracion_traduccion", "configuracion_traduccion", "id_configuracion_traduccion", "NO ACTION"],
    ["traduccion_documento", "id_documento", "documento", "id_documento", "SET NULL"],
    ["traduccion_documento", "id_usuario", "usuario", "id", "NO ACTION"],
    ["traduccion_documento", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["traduccion_documento", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["traduccion_documento", "id_glosario", "glosario", "id_glosario", "SET NULL"],
    ["glosario", "id_usuario", "usuario", "id", "CASCADE"],
    ["glosario", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["glosario", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["termino_glosario", "id_glosario", "glosario", "id_glosario", "CASCADE"],
    ["conversacion", "id_usuario", "usuario", "id", "CASCADE"],
    ["conversacion", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["conversacion", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["conversacion", "id_contexto", "contexto", "id_contexto", "SET NULL"],
    ["conversacion", "id_entorno", "entorno", "id_entorno", "NO ACTION"],
    ["conversacion", "id_tono", "tono", "id_tono", "SET NULL"],
    ["conversacion", "id_glosario", "glosario", "id_glosario", "SET NULL"],
    ["participante_conversacion", "id_conversacion", "conversacion", "id_conversacion", "CASCADE"],
    ["participante_conversacion", "id_idioma", "idioma", "id_idioma", "NO ACTION"],
    ["intervencion", "id_conversacion", "conversacion", "id_conversacion", "CASCADE"],
    ["intervencion", "id_participante", "participante_conversacion", "id_participante", "SET NULL"],
    ["intervencion", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["intervencion", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["conexion_plataforma", "id_usuario", "usuario", "id", "CASCADE"],
    ["sesion_externa", "id_usuario", "usuario", "id", "CASCADE"],
    ["sesion_externa", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["sesion_externa", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["sesion_externa", "id_contexto", "contexto", "id_contexto", "SET NULL"],
    ["sesion_externa", "id_entorno", "entorno", "id_entorno", "NO ACTION"],
    ["sesion_externa", "id_tono", "tono", "id_tono", "SET NULL"],
    ["sesion_externa", "id_glosario", "glosario", "id_glosario", "SET NULL"],
    ["participante_externo", "id_sesion_externa", "sesion_externa", "id_sesion_externa", "CASCADE"],
    ["intervencion_externa", "id_sesion_externa", "sesion_externa", "id_sesion_externa", "CASCADE"],
    ["intervencion_externa", "id_participante", "participante_externo", "id_participante", "SET NULL"],
    ["intervencion_externa", "id_idioma_origen", "idioma", "id_idioma", "NO ACTION"],
    ["intervencion_externa", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"],
    ["dispositivo_push", "id_usuario", "usuario", "id", "CASCADE"],
    ["notificacion", "id_usuario", "usuario", "id", "CASCADE"],
    ["chat", "id_usuario_menor", "usuario", "id", "CASCADE"],
    ["chat", "id_usuario_mayor", "usuario", "id", "CASCADE"],
    ["participante_chat", "id_chat", "chat", "id_chat", "CASCADE"],
    ["participante_chat", "id_usuario", "usuario", "id", "CASCADE"],
    ["participante_chat", "id_idioma_lectura", "idioma", "id_idioma", "NO ACTION"],
    ["mensaje_chat", "id_chat", "chat", "id_chat", "CASCADE"],
    ["mensaje_chat", "id_remitente", "usuario", "id", "CASCADE"],
    ["mensaje_chat", "id_idioma_detectado", "idioma", "id_idioma", "SET NULL"],
    ["traduccion_mensaje_chat", "id_mensaje", "mensaje_chat", "id_mensaje", "CASCADE"],
    ["traduccion_mensaje_chat", "id_destinatario", "usuario", "id", "CASCADE"],
    ["traduccion_mensaje_chat", "id_idioma_destino", "idioma", "id_idioma", "NO ACTION"]
];

// ---------------------------------------------------------------------------
// 2) UTILIDADES
// ---------------------------------------------------------------------------
function log(msg) { Session.Output(msg); }

// Busca una fila [id, ...] en un arreglo y la devuelve (o null)
function findRow(arr, id) {
    for (var i = 0; i < arr.length; i++) {
        if (arr[i][0] === id) { return arr[i]; }
    }
    return null;
}

function inList(arr, id) {
    for (var i = 0; i < arr.length; i++) {
        if (arr[i] === id) { return true; }
    }
    return false;
}

// Atributo de una clase: [nombre, tipo, nulo, clave] (o null)
function findColumna(tabla, col) {
    var t = findRow(TABLAS, tabla);
    return t ? findRow(t[2], col) : null;
}

// Comprueba que cada relacion apunta a clases y atributos existentes
function validarModelo() {
    var ok = true, i;
    for (i = 0; i < FKS.length; i++) {
        if (!findColumna(FKS[i][0], FKS[i][1]) || !findColumna(FKS[i][2], FKS[i][3])) {
            log("  ! Relacion invalida: " + FKS[i].join(" / "));
            ok = false;
        }
    }
    for (i = 0; i < TABLAS.length; i++) {
        if (!inList(GRUPOS, TABLAS[i][1])) { log("  ! Grupo desconocido en " + TABLAS[i][0]); ok = false; }
    }
    return ok;
}

// Clave foranea unica (1 a 1): el atributo es UK o es la unica PK de la clase
function fkEsUnica(fk) {
    var t = findRow(TABLAS, fk[0]), c = findColumna(fk[0], fk[1]), nPk = 0, k;
    for (k = 0; k < t[2].length; k++) { if (t[2][k][3] === "PK") { nPk++; } }
    return c[3] === "UK" || (c[3] === "PK" && nPk === 1);
}

// ---------------------------------------------------------------------------
// 3) PROGRAMA PRINCIPAL
// ---------------------------------------------------------------------------
function main() {
    Repository.EnsureOutputVisible("Script");
    log("== Generando paquete " + PAQUETE + " ==");

    if (!validarModelo()) {
        log("El modelo de datos del script tiene errores (ver arriba). No se creo nada.");
        return;
    }

    // --- Paquete padre: el seleccionado en el Project Browser o el 1er modelo
    var parent = Repository.GetTreeSelectedPackage();
    if (parent == null) { parent = Repository.Models.GetAt(0); }

    // Evita duplicar si ya existe
    for (var p = 0; p < parent.Packages.Count; p++) {
        if (parent.Packages.GetAt(p).Name === PAQUETE) {
            log("El paquete '" + PAQUETE + "' ya existe en '" + parent.Name +
                "'. Eliminalo (o renombralo) y vuelve a ejecutar el script.");
            return;
        }
    }

    var pkg = parent.Packages.AddNew(PAQUETE, "");
    pkg.Update();
    parent.Packages.Refresh();
    log("Paquete '" + PAQUETE + "' creado en '" + parent.Name + "'.");

    // --- Clases con sus atributos (sin metodos)
    var el = {};   // nombre -> Element
    var i;
    for (i = 0; i < TABLAS.length; i++) {
        el[TABLAS[i][0]] = crearClase(pkg, TABLAS[i]);
    }
    pkg.Elements.Refresh();
    log("Clases creadas: " + TABLAS.length);

    // --- Asociaciones
    var creadas = 0;
    for (i = 0; i < FKS.length; i++) {
        if (crearAsociacion(el, FKS[i])) { creadas++; }
    }
    log("Relaciones creadas: " + creadas + " de " + FKS.length);

    // --- Diagrama unico
    crearDiagrama(pkg, el);

    Repository.RefreshModelView(pkg.PackageID);
    Repository.ReloadPackage(pkg.PackageID);
    log("== Listo: " + TABLAS.length + " clases y " + creadas + " relaciones en '" + DIAGRAMA + "' ==");
}

// Crea una clase con un atributo por columna
function crearClase(pkg, fila) {
    var c = pkg.Elements.AddNew(fila[0], "Class");
    c.Update();
    for (var i = 0; i < fila[2].length; i++) {
        var col = fila[2][i];
        var a = c.Attributes.AddNew(col[0], col[1]);
        a.Pos = i;
        if (!a.Update()) { log("  ! Atributo " + fila[0] + "." + col[0] + ": " + a.GetLastError()); }
    }
    c.Attributes.Refresh();
    return c;
}

// Asociacion de la clase que tiene la clave foranea (origen) con la referenciada (destino)
function crearAsociacion(el, fk) {
    var opcional = findColumna(fk[0], fk[1])[2];   // admite nulos
    var unica = fkEsUnica(fk);                     // 1 a 1

    var con = el[fk[0]].Connectors.AddNew(fk[1], "Association");
    con.SupplierID = el[fk[2]].ElementID;
    if (!con.Update()) {
        log("  ! No se pudo crear la relacion " + fk[0] + "." + fk[1] + ": " + con.GetLastError());
        return false;
    }
    con.ClientEnd.Cardinality = unica ? "0..1" : "0..*";
    con.ClientEnd.Update();
    con.SupplierEnd.Cardinality = opcional ? "0..1" : "1";
    con.SupplierEnd.Update();
    con.Update();
    return true;
}

// ---------------------------------------------------------------------------
// 4) DIAGRAMA Y LAYOUT
// ---------------------------------------------------------------------------
var ANCHO = 260, SEP_X = 60, SEP_Y = 60, LINEA = 15, POR_FILA = 6;

// Alto aproximado de una clase: cabecera + un renglon por atributo
function altoClase(nombre) {
    return 40 + LINEA * findRow(TABLAS, nombre)[2].length + 15;
}

function crearDiagrama(pkg, el) {
    var diag = pkg.Diagrams.AddNew(DIAGRAMA, "Logical");
    diag.Notes = "Diagrama de clases de la base de datos de TraduContext: " +
        TABLAS.length + " clases y " + FKS.length + " relaciones.";
    diag.Update();
    pkg.Diagrams.Refresh();

    // Rejilla de POR_FILA columnas; cada grupo empieza en una fila nueva
    var y = 30, g, i;
    for (g = 0; g < GRUPOS.length; g++) {
        var nombres = [];
        for (i = 0; i < TABLAS.length; i++) { if (TABLAS[i][1] === GRUPOS[g]) { nombres.push(TABLAS[i][0]); } }
        i = 0;
        while (i < nombres.length) {
            var altoFila = 0;
            for (var c = 0; c < POR_FILA && i < nombres.length; c++, i++) {
                var h = altoClase(nombres[i]);
                var x = 40 + c * (ANCHO + SEP_X);
                colocar(diag, el[nombres[i]], x, x + ANCHO, y, y + h);
                if (h > altoFila) { altoFila = h; }
            }
            y += altoFila + SEP_Y;
        }
    }
    diag.DiagramObjects.Refresh();
    Repository.ReloadDiagram(diag.DiagramID);
    log("Diagrama '" + DIAGRAMA + "' generado.");
}

// Agrega un elemento al diagrama con una posicion dada.
// EA usa Y negativo hacia abajo: t = -top, b = -bottom.
function colocar(diag, elemento, l, r, top, bottom) {
    var pos = "l=" + Math.round(l) + ";r=" + Math.round(r) +
        ";t=" + Math.round(-top) + ";b=" + Math.round(-bottom) + ";";
    var o = diag.DiagramObjects.AddNew(pos, "");
    o.ElementID = elemento.ElementID;
    o.Update();
}

main();
