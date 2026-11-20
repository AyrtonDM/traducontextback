from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

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


class ChatDetalle(BaseModel):
    id_chat: int
    otro_usuario: UsuarioChatResumen
    mi_idioma_lectura: IdiomaResumen
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
