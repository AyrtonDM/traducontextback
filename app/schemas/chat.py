from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.chat.chat import LONGITUD_MAXIMA_DESCRIPCION_CONTEXTO_CHAT
from app.models.chat.mensaje_chat import LONGITUD_MAXIMA_MENSAJE


# Como ve un usuario un mensaje del chat:
# - propio: lo escribio el; se muestra el original
# - pendiente: la traduccion a su idioma de lectura aun no esta; se muestra el original
# - traducido: se muestra la traduccion
# - sin_traduccion: ya estaba en su idioma; se muestra el original
# - error: no se pudo traducir; se muestra el original
EstadoLectura = Literal["propio", "pendiente", "traducido", "sin_traduccion", "error"]


class UsuarioChatResumen(BaseModel):
    """Datos publicos de otro usuario: solo id y nombre (sin correo ni foto)."""

    id_usuario: int
    nombre: str


class BuscarUsuariosRespuesta(BaseModel):
    mensaje: str
    resultado: list[UsuarioChatResumen]


class IdiomaResumen(BaseModel):
    id_idioma: int
    codigo: str
    nombre: str


def _limpiar_texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    return valor.strip() or None


class CrearChatSolicitud(BaseModel):
    id_usuario: int = Field(..., gt=0, description="Usuario con el que se quiere chatear")
    codigo_idioma_lectura: str | None = Field(
        default=None,
        min_length=2,
        max_length=10,
        description=(
            "Idioma en el que quieres leer este chat (solo al crearlo). Por defecto: tu idioma de "
            "destino preferido o espanol."
        ),
    )
    id_contexto: int | None = Field(
        default=None,
        description=(
            "Contexto de dominio de la conversacion (global o personal tuyo). Si el chat ya existia, "
            "se aplica solo si lo envias."
        ),
    )
    descripcion_contexto: str | None = Field(
        default=None,
        max_length=LONGITUD_MAXIMA_DESCRIPCION_CONTEXTO_CHAT,
        description="Situacion, audiencia o terminologia de la conversacion (opcional)",
    )

    @field_validator("descripcion_contexto")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)


class ActualizarContextoChatSolicitud(BaseModel):
    """Solo se cambian los campos enviados; null quita el contexto o la descripcion."""

    id_contexto: int | None = Field(default=None, description="Nuevo contexto (null lo quita)")
    descripcion_contexto: str | None = Field(
        default=None,
        max_length=LONGITUD_MAXIMA_DESCRIPCION_CONTEXTO_CHAT,
        description="Nueva descripcion del contexto (null la quita)",
    )

    @field_validator("descripcion_contexto")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar_texto_opcional(valor)

    @model_validator(mode="after")
    def validar_campos(self):
        if not self.model_fields_set:
            raise ValueError("Debe enviar id_contexto o descripcion_contexto.")
        return self


class CambiarIdiomaLecturaSolicitud(BaseModel):
    codigo_idioma: str = Field(..., min_length=2, max_length=10, examples=["es"])


class EnviarMensajeSolicitud(BaseModel):
    texto: str = Field(..., min_length=1, max_length=LONGITUD_MAXIMA_MENSAJE)

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise ValueError("El mensaje no puede estar vacio.")
        return valor_limpio


class MarcarLeidoSolicitud(BaseModel):
    id_mensaje: int = Field(..., gt=0, description="Ultimo mensaje leido; los anteriores tambien quedan leidos")


class MensajeChatDetalle(BaseModel):
    id_mensaje: int
    id_chat: int
    id_remitente: int
    es_mio: bool
    # Texto que debe mostrarse a quien consulta (traduccion u original segun estado_lectura)
    texto: str
    texto_original: str
    # Codigo del idioma detectado del original; None mientras se procesa
    idioma_original: str | None
    # Codigo del idioma en que esta `texto`; None si se desconoce
    idioma_texto: str | None
    estado_lectura: EstadoLectura
    fecha_envio: datetime


class ContextoChatResumen(BaseModel):
    id_contexto: int
    nombre: str


class ChatDetalle(BaseModel):
    id_chat: int
    otro_usuario: UsuarioChatResumen
    mi_idioma_lectura: IdiomaResumen
    contexto: ContextoChatResumen | None = None
    descripcion_contexto: str | None = None
    ultimo_mensaje: MensajeChatDetalle | None
    no_leidos: int
    fecha_creacion: datetime
    fecha_ultimo_mensaje: datetime | None


class RespuestaChat(BaseModel):
    mensaje: str
    resultado: ChatDetalle


class ListaChatsRespuesta(BaseModel):
    mensaje: str
    resultado: list[ChatDetalle]


class RespuestaMensaje(BaseModel):
    mensaje: str
    resultado: MensajeChatDetalle


class PaginaMensajes(BaseModel):
    # Orden ascendente por id_mensaje (del mas antiguo al mas nuevo)
    elementos: list[MensajeChatDetalle]
    hay_mas: bool


class ListaMensajesRespuesta(BaseModel):
    mensaje: str
    resultado: PaginaMensajes


class ResultadoLeido(BaseModel):
    id_ultimo_mensaje_leido: int | None
    no_leidos: int


class RespuestaLeido(BaseModel):
    mensaje: str
    resultado: ResultadoLeido
