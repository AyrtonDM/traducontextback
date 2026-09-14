import logging
from typing import Optional
from fastapi import HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.configuracion import configuracion
from app.models.traduccion.contexto import Contexto
from app.models.traduccion.idioma import Idioma
from app.models.traduccion.traduccion import Traduccion
from app.models.usuario.usuario import Usuario
from app.schemas.traduccion import (
    TraduccionSolicitud,
    TraduccionResultado,
    TraduccionItemHistorial,
    IdiomaItem,
    ContextoItem,
)

logger = logging.getLogger(__name__)


class TraduccionIAEstructurada(BaseModel):
    texto_traducido: str = Field(..., description="Traduccion final contextualizada")
    dominio_detectado: str = Field(default="General", description="Dominio detectado o aplicado")
    alternativas: list[str] = Field(default_factory=list, description="Alternativas de traduccion si fueron solicitadas")
    explicacion_modismos: Optional[str] = Field(default=None, description="Explicacion de modismos si fueron solicitados")


class ServicioTraduccion:

    def __init__(self):
        self.cliente = OpenAI(api_key=configuracion.openai_api_key)

    def traducir_con_ia(self, datos: TraduccionSolicitud) -> TraduccionIAEstructurada:
        """Llama a OpenAI estructurado para traducir con contexto, dominio y tono."""
        prompt_sistema = (
            "Eres TraduContext, un sistema de traduccion contextual inteligente de ultima generacion.\n"
            "Tu funcion es traducir el texto adaptandolo con precision al significado deseado segun el contexto, tono y dominio.\n\n"
            "REGLAS OBLIGATORIAS:\n"
            "1. Respeta el DOMINIO o CONTEXTO indicado (ej. Tecnico, Legal, Medico, Profesional, Academico, Comercial, Coloquial, General).\n"
            "   Usa el vocabulario y jerga exacta del dominio indicado.\n"
            "2. Respeta el TONO solicitado (ej. Neutral, Formal, Informal, Profesional).\n"
            "3. Respeta la VARIANTE REGIONAL solicitada (ej. Espanol de Latinoamerica, Espanol de Espana).\n"
            "4. Si 'mostrar_alternativas' es True, incluye 2 o 3 alternativas viables con ligeros matices.\n"
            "5. Si 'explicar_modismos' es True y el texto tiene modismos, expresiones idiomaticas o frases culturales, explicalas brevemente.\n"
            "6. Si 'adaptar_formato_local' es True, adapta convenciones de fecha, moneda o puntuacion a la region destino."
        )

        prompt_usuario = (
            f"TEXTO A TRADUCIR:\n{datos.texto}\n\n"
            f"PARAMETROS:\n"
            f"- Idioma origen: {datos.idioma_origen}\n"
            f"- Idioma destino: {datos.idioma_destino}\n"
            f"- Dominio/Contexto: {datos.dominio or 'General'}\n"
            f"- Descripcion adicional del contexto: {datos.contexto_adicional or 'Ninguna'}\n"
            f"- Tono: {datos.tono or 'Neutral'}\n"
            f"- Variante regional: {datos.variante_regional or 'Espanol (Latinoamerica)'}\n"
            f"- Mostrar alternativas: {'Si' if datos.mostrar_alternativas else 'No'}\n"
            f"- Explicar modismos: {'Si' if datos.explicar_modismos else 'No'}\n"
            f"- Adaptar formato local: {'Si' if datos.adaptar_formato_local else 'No'}\n"
        )

        try:
            respuesta = self.cliente.responses.parse(
                model="gpt-5.6-luna",
                input=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario},
                ],
                text_format=TraduccionIAEstructurada,
            )
            return respuesta.output_parsed
        except Exception as error:
            logger.warning(f"Fallo llamada estructurada con gpt-5.6-luna: {error}. Intentando fallback.")
            # Fallback en caso de que el modelo devuelva error puntual
            return TraduccionIAEstructurada(
                texto_traducido=f"[Error al procesar con IA: {error}]",
                dominio_detectado=datos.dominio or "General",
                alternativas=[],
                explicacion_modismos=None,
            )

    def ejecutar_traduccion(
        self,
        sesion: Session,
        datos: TraduccionSolicitud,
        usuario: Usuario,
    ) -> TraduccionResultado:
        """Realiza la traduccion con IA y la persiste en la base de datos."""

        # 1. Obtener idiomas - solo desde los registros existentes en la BD
        idioma_orig = sesion.scalar(
            select(Idioma).where(Idioma.codigo == datos.idioma_origen.lower())
        )
        if not idioma_orig:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El idioma de origen '{datos.idioma_origen}' no está disponible en el sistema.",
            )

        idioma_dest = sesion.scalar(
            select(Idioma).where(Idioma.codigo == datos.idioma_destino.lower())
        )
        if not idioma_dest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El idioma de destino '{datos.idioma_destino}' no está disponible en el sistema.",
            )

        # 2. Obtener o resolver contexto para el usuario
        nombre_contexto = (datos.dominio or "General").strip()
        contexto = sesion.scalar(
            select(Contexto).where(
                Contexto.id_usuario == usuario.id,
                Contexto.nombre.ilike(nombre_contexto),
            )
        )
        if not contexto:
            contexto = Contexto(
                nombre=nombre_contexto,
                descripcion=datos.contexto_adicional or f"Contexto {nombre_contexto}",
                id_usuario=usuario.id,
            )
            sesion.add(contexto)
            sesion.flush()

        # 3. Realizar traduccion contextual con OpenAI
        resultado_ia = self.traducir_con_ia(datos)

        # 4. Persistir registro de traduccion
        nueva_traduccion = Traduccion(
            texto_original=datos.texto,
            texto_traducido=resultado_ia.texto_traducido,
            id_contexto=contexto.id,
            id_idioma_origen=idioma_orig.id,
            id_idioma_destino=idioma_dest.id,
        )
        sesion.add(nueva_traduccion)
        sesion.commit()
        sesion.refresh(nueva_traduccion)

        fecha_str = (
            nueva_traduccion.fecha_creacion.isoformat()
            if nueva_traduccion.fecha_creacion
            else ""
        )

        return TraduccionResultado(
            id=nueva_traduccion.id,
            texto_original=nueva_traduccion.texto_original,
            texto_traducido=nueva_traduccion.texto_traducido,
            idioma_origen=idioma_orig.codigo,
            idioma_destino=idioma_dest.codigo,
            dominio=resultado_ia.dominio_detectado or nombre_contexto,
            alternativas=resultado_ia.alternativas,
            explicacion_modismos=resultado_ia.explicacion_modismos,
            fecha_creacion=fecha_str,
        )

    def obtener_recientes(
        self,
        sesion: Session,
        usuario_id: int,
        limite: int = 20,
    ) -> list[TraduccionItemHistorial]:
        """Obtiene las ultimas traducciones del usuario autenticado."""
        stmt = (
            select(Traduccion, Contexto, Idioma)
            .join(Contexto, Traduccion.id_contexto == Contexto.id)
            .where(Contexto.id_usuario == usuario_id)
            .order_by(desc(Traduccion.fecha_creacion))
            .limit(limite)
        )
        traducciones = sesion.scalars(
            select(Traduccion)
            .join(Contexto, Traduccion.id_contexto == Contexto.id)
            .where(Contexto.id_usuario == usuario_id)
            .order_by(desc(Traduccion.fecha_creacion))
            .limit(limite)
        ).all()

        resultado = []
        for t in traducciones:
            cod_orig = t.idioma_origen.codigo if t.idioma_origen else str(t.id_idioma_origen)
            cod_dest = t.idioma_destino.codigo if t.idioma_destino else str(t.id_idioma_destino)
            nom_orig = t.idioma_origen.nombre if t.idioma_origen else cod_orig
            nom_dest = t.idioma_destino.nombre if t.idioma_destino else cod_dest
            nom_ctx = t.contexto.nombre if t.contexto else None

            resultado.append(
                TraduccionItemHistorial(
                    id=t.id,
                    texto_original=t.texto_original,
                    texto_traducido=t.texto_traducido,
                    fecha_creacion=t.fecha_creacion.strftime("%Y-%m-%d %H:%M") if t.fecha_creacion else "",
                    id_idioma_origen=t.id_idioma_origen,
                    id_idioma_destino=t.id_idioma_destino,
                    codigo_idioma_origen=cod_orig,
                    codigo_idioma_destino=cod_dest,
                    nombre_idioma_origen=nom_orig,
                    nombre_idioma_destino=nom_dest,
                    contexto=nom_ctx,
                )
            )

        return resultado

    def obtener_idiomas(self, sesion: Session) -> list[IdiomaItem]:
        """Obtiene la lista de todos los idiomas disponibles."""
        idiomas = sesion.scalars(select(Idioma).order_by(Idioma.nombre)).all()
        return [
            IdiomaItem(id=i.id, codigo=i.codigo, nombre=i.nombre)
            for i in idiomas
        ]

    def obtener_contextos(self, sesion: Session, usuario_id: int) -> list[ContextoItem]:
        """Obtiene la lista de contextos del usuario."""
        contextos = sesion.scalars(
            select(Contexto)
            .where(Contexto.id_usuario == usuario_id)
            .order_by(Contexto.nombre)
        ).all()
        return [
            ContextoItem(id=c.id, nombre=c.nombre, descripcion=c.descripcion)
            for c in contextos
        ]


servicio_traduccion = ServicioTraduccion()
