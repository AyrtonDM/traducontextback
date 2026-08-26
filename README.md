# Para realizar migraciones
alembic revision --autogenerate -m "agregar telefono a usuario"
alembic upgrade head

app/
??? api/
??? core/
??? database/
??? models/
??? schemas/
??? seeds/
??? services/
??? utilities/
??? __init__.py
??? main.py

# api/

Contiene las rutas o endpoints de la API.

Aquí se define cómo el frontend u otros clientes pueden comunicarse con el backend mediante HTTP.

Contiene
Routers de FastAPI.
Endpoints.
Parámetros recibidos por las rutas.
Dependencias necesarias para las rutas.
Respuestas HTTP.
Ejemplos
api/
??? __init__.py
??? autenticacion.py
??? usuarios.py
??? roles.py
??? permisos.py

Un archivo de esta carpeta puede contener endpoints como:

POST /autenticacion/registrar
POST /autenticacion/iniciar-sesion
POST /autenticacion/verificar-codigo

GET /usuarios
GET /usuarios/{id}
Importante

La carpeta api no debe contener la lógica de negocio compleja.

La ruta debe encargarse principalmente de recibir la solicitud, llamar al servicio correspondiente y devolver la respuesta.

Flujo:

Frontend
   ?
API
   ?
Service
   ?
Database

# core/

Contiene la configuración y componentes centrales del sistema.

Son elementos utilizados por diferentes partes del backend y que forman parte de la configuración general de la aplicación.

Contiene
Configuración mediante variables de entorno.
Configuraciones generales de FastAPI.
Configuraciones de seguridad.
Configuraciones de autenticación.
Constantes globales relacionadas con la infraestructura.
Dependencias centrales de la aplicación.
Ejemplos
core/
??? __init__.py
??? configuracion.py
??? seguridad.py
??? excepciones.py

Por ejemplo, configuracion.py puede encargarse de leer:

.env
    ?
Configuracion
    ?
Aplicacion

Aquí también pueden ubicarse elementos relacionados con JWT, hashing o manejo general de excepciones si son utilizados por diferentes módulos.

# database/

Contiene todo lo relacionado con la conexión y acceso técnico a la base de datos.

Contiene
Conexión a PostgreSQL.
Motor de SQLAlchemy.
Sesiones de base de datos.
Clase Base de SQLAlchemy.
Dependencias para obtener una sesión.
Configuraciones específicas de la base de datos.
Ejemplos
database/
??? __init__.py
??? conexion.py
??? base.py

La responsabilidad de esta carpeta es proporcionar la conexión:

Aplicación
     ?
database
     ?
SQLAlchemy
     ?
PostgreSQL
Importante

Aquí no se colocan las consultas específicas de Usuario, Rol, Permiso, etc.

La conexión pertenece a database.

Las operaciones específicas sobre entidades deben estar en los servicios/repositorios que correspondan.

# models/

Contiene los modelos de SQLAlchemy que representan las tablas de la base de datos.

Cada modelo representa una entidad persistente del sistema.

Ejemplos
models/
??? __init__.py
??? usuario.py
??? rol.py
??? permiso.py
??? rol_permiso.py
??? sesion.py
??? token_verificacion.py

Por ejemplo:

Usuario
Rol
Permiso
Sesion
TokenVerificacion

Estos modelos definen:

Columnas.
Tipos de datos.
Claves primarias.
Claves foráneas.
Relaciones entre tablas.
Restricciones relacionadas con la base de datos.
Ejemplo conceptual
models/usuario.py
        ?
Tabla usuario
        ?
PostgreSQL

Los modelos de esta carpeta son utilizados posteriormente por SQLAlchemy y Alembic.

# schemas/

Contiene los esquemas Pydantic utilizados para validar y estructurar los datos que entran y salen de la API.

Los schemas no representan directamente tablas de la base de datos.

Su función principal es definir la estructura de los datos de comunicación.

Ejemplos
schemas/
??? __init__.py
??? usuario.py
??? autenticacion.py
??? sesion.py
??? token_verificacion.py

Podemos tener, por ejemplo:

UsuarioCrear
UsuarioRespuesta
InicioSesion
VerificarCodigo

Conceptualmente:

Frontend
   ?
Schema
   ?
Validación
   ?
Service
Diferencia entre models y schemas
models/
    Representan tablas de PostgreSQL.

schemas/
    Representan datos de entrada y salida de la API.

No deben confundirse.

# seeds/

Contiene los datos iniciales que deben cargarse en la base de datos para que el sistema pueda funcionar correctamente.

Los seeds se utilizan principalmente para datos predeterminados o iniciales, no para datos generados por los usuarios.

Ejemplos
seeds/
??? __init__.py
??? roles.py
??? permisos.py
??? datos_iniciales.py

Por ejemplo, el sistema podría necesitar inicialmente:

Roles:

SUPERADMIN
ADMIN
USUARIO

y permisos como:

CREAR_USUARIO
EDITAR_USUARIO
ELIMINAR_USUARIO
VER_USUARIOS

Los seeds podrían insertar esos datos cuando se prepara una base de datos nueva.

Importante

Los seeds no sustituyen a las migraciones de Alembic.

La diferencia es:

Alembic
    ? modifica la estructura de la base de datos.

Seeds
    ? inserta datos iniciales.

# services/

Contiene la lógica de negocio de la aplicación.

Esta es una de las carpetas más importantes del proyecto.

Los servicios reciben una operación que debe realizarse y coordinan las diferentes acciones necesarias para completarla.

Ejemplos
services/
??? __init__.py
??? autenticacion.py
??? usuario.py
??? correo.py
??? sesion.py

Por ejemplo, registrar un usuario podría requerir:

Registrar usuario
       ?
Validar información
       ?
Comprobar que el correo no exista
       ?
Crear usuario
       ?
Generar código
       ?
Guardar código
       ?
Enviar correo

Toda esa lógica pertenece al servicio de autenticación/usuario, no directamente a la ruta.

Flujo recomendado
API
 ?
Service
 ?
Models / Database

Los servicios contienen las reglas que determinan qué debe hacer el sistema.

# utilities/

Contiene funciones auxiliares y reutilizables que pueden ser utilizadas por diferentes módulos del sistema.

Una utilidad debe realizar una tarea específica y reutilizable, pero no debería contener lógica de negocio propia de una funcionalidad.

Ejemplos
utilities/
??? __init__.py
??? correo.py
??? codigo.py
??? fechas.py
??? validaciones.py

Por ejemplo:

correo.py

Puede contener una función genérica:

enviar_correo()

Esta función puede utilizarse para:

Código de verificación
Recuperación de contraseña
Notificaciones
Información
Confirmaciones
codigo.py

Puede contener funciones para generar códigos aleatorios:

generar_codigo_verificacion()
Diferencia entre services y utilities
services/
    Contiene lógica de negocio.

utilities/
    Contiene herramientas reutilizables.

Por ejemplo:

services/autenticacion.py
        ?
generar código
        ?
utilities/codigo.py

y:

services/autenticacion.py
        ?
enviar correo
        ?
utilities/correo.py

La utilidad no necesita saber por qué se está enviando el correo.

__init__.py

Permite que Python trate la carpeta app como un paquete y facilita las importaciones entre módulos.

Normalmente no debe contener lógica de negocio.

También puede utilizarse posteriormente para exponer determinados elementos del paquete si fuera necesario.

# main.py

Es el punto de entrada principal de FastAPI.

Aquí se crea la aplicación y se registran los routers principales.

Conceptualmente:

main.py
   ?
   ??? Crear aplicación FastAPI
   ??? Configuración general
   ??? Registrar routers
   ??? Configuraciones globales

Por ejemplo:

main.py
    ?
FastAPI
    ?
api/autenticacion.py
api/usuarios.py
api/roles.py

El archivo no debería contener toda la lógica del sistema.

Su función principal es ensamblar la aplicación.