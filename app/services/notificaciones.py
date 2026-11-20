"""
Notificaciones (M1): dispositivos push, bandeja del usuario y la funcion central `notificar()`.

Regla: el id_usuario siempre lo aporta el endpoint a partir del token; los servicios filtran todo
por ese id, de modo que nadie puede leer ni modificar notificaciones o dispositivos ajenos.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database.conexion import FabricaSesiones
from app.models.notificacion.dispositivo_push import DispositivoPush
from app.models.notificacion.notificacion import TIPOS_NOTIFICACION, Notificacion
from app.services import push_fcm


logger = logging.getLogger(__name__)


class NotificacionNoEncontradaError(ValueError):
    """La notificacion no existe o no pertenece al usuario autenticado."""


class DispositivoNoEncontradoError(ValueError):
    """El dispositivo no existe o no pertenece al usuario autenticado."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Dispositivos
# ---------------------------------------------------------------------------


def registrar_dispositivo(sesion: Session, id_usuario: int, token_fcm: str, plataforma: str) -> DispositivoPush:
    """
    Alta o actualizacion por token (idempotente). Si el token ya estaba registrado por otro usuario
    (mismo telefono, otra cuenta), pasa al usuario actual para que el anterior deje de recibir push.
    """
    dispositivo = sesion.scalar(select(DispositivoPush).where(DispositivoPush.token_fcm == token_fcm))
    if dispositivo is None:
        dispositivo = DispositivoPush(token_fcm=token_fcm, id_usuario=id_usuario)
        sesion.add(dispositivo)

    dispositivo.id_usuario = id_usuario
    dispositivo.plataforma = plataforma
    dispositivo.activo = True
    dispositivo.fecha_ultimo_uso = _ahora()
    sesion.commit()
    sesion.refresh(dispositivo)
    return dispositivo


def eliminar_dispositivo(sesion: Session, id_usuario: int, token_fcm: str) -> None:
    dispositivo = sesion.scalar(
        select(DispositivoPush).where(
            DispositivoPush.token_fcm == token_fcm,
            DispositivoPush.id_usuario == id_usuario,
        )
    )
    if dispositivo is None:
        raise DispositivoNoEncontradoError("El dispositivo no existe o no pertenece al usuario autenticado.")
    sesion.delete(dispositivo)
    sesion.commit()


# ---------------------------------------------------------------------------
# Bandeja de notificaciones
# ---------------------------------------------------------------------------


def listar_notificaciones(
    sesion: Session,
    id_usuario: int,
    *,
    solo_no_leidas: bool,
    pagina: int,
    tamano_pagina: int,
) -> tuple[list[Notificacion], int, int]:
    """Devuelve (pagina de notificaciones, total segun filtro, total no leidas), de la mas reciente a la mas antigua."""
    filtros = [Notificacion.id_usuario == id_usuario]
    if solo_no_leidas:
        filtros.append(Notificacion.leida.is_(False))

    total = sesion.scalar(select(func.count()).select_from(Notificacion).where(*filtros)) or 0
    no_leidas = sesion.scalar(
        select(func.count())
        .select_from(Notificacion)
        .where(Notificacion.id_usuario == id_usuario, Notificacion.leida.is_(False))
    ) or 0
    elementos = sesion.scalars(
        select(Notificacion)
        .where(*filtros)
        .order_by(Notificacion.fecha_creacion.desc(), Notificacion.id_notificacion.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
    ).all()
    return list(elementos), total, no_leidas


def marcar_como_leida(sesion: Session, id_usuario: int, id_notificacion: int) -> Notificacion:
    notificacion = sesion.scalar(
        select(Notificacion).where(
            Notificacion.id_notificacion == id_notificacion,
            Notificacion.id_usuario == id_usuario,
        )
    )
    if notificacion is None:
        raise NotificacionNoEncontradaError("La notificacion no existe o no pertenece al usuario autenticado.")
    if not notificacion.leida:
        notificacion.leida = True
        notificacion.fecha_lectura = _ahora()
        sesion.commit()
        sesion.refresh(notificacion)
    return notificacion


def marcar_todas_como_leidas(sesion: Session, id_usuario: int) -> int:
    resultado = sesion.execute(
        update(Notificacion)
        .where(Notificacion.id_usuario == id_usuario, Notificacion.leida.is_(False))
        .values(leida=True, fecha_lectura=_ahora())
        .execution_options(synchronize_session=False)
    )
    sesion.commit()
    return resultado.rowcount or 0


# ---------------------------------------------------------------------------
# Funcion central
# ---------------------------------------------------------------------------


def _datos_push(notificacion: Notificacion) -> dict[str, str]:
    """FCM solo admite valores de texto en `data`."""
    datos = {clave: str(valor) for clave, valor in (notificacion.datos or {}).items() if valor is not None}
    datos["tipo"] = notificacion.tipo
    datos["id_notificacion"] = str(notificacion.id_notificacion)
    return datos


def enviar_push_notificacion(sesion: Session, id_notificacion: int) -> None:
    """
    Envia por FCM una notificacion ya guardada a los dispositivos activos de su usuario y desactiva
    los tokens invalidos. Nunca lanza excepciones: un fallo del push no debe romper el flujo.
    """
    try:
        if not push_fcm.push_disponible():
            return
        notificacion = sesion.get(Notificacion, id_notificacion)
        if notificacion is None:
            return
        tokens = list(
            sesion.scalars(
                select(DispositivoPush.token_fcm).where(
                    DispositivoPush.id_usuario == notificacion.id_usuario,
                    DispositivoPush.activo.is_(True),
                )
            )
        )
        if not tokens:
            return

        resultado = push_fcm.enviar_a_tokens(
            tokens,
            titulo=notificacion.titulo,
            cuerpo=notificacion.cuerpo,
            datos=_datos_push(notificacion),
        )
        if resultado.tokens_invalidos:
            sesion.execute(
                update(DispositivoPush)
                .where(DispositivoPush.token_fcm.in_(resultado.tokens_invalidos))
                .values(activo=False)
                .execution_options(synchronize_session=False)
            )
            sesion.commit()
    except Exception:
        sesion.rollback()
        logger.exception("No se pudo enviar la notificacion push %s.", id_notificacion)


def _enviar_push_en_segundo_plano(id_notificacion: int) -> None:
    """Tarea en segundo plano: abre su propia sesion porque la de la peticion ya esta cerrada."""
    sesion = FabricaSesiones()
    try:
        enviar_push_notificacion(sesion, id_notificacion)
    finally:
        sesion.close()


def notificar(
    sesion: Session,
    id_usuario: int,
    tipo: str,
    titulo: str,
    cuerpo: str,
    datos: dict[str, Any] | None = None,
    tareas_segundo_plano: BackgroundTasks | None = None,
) -> Notificacion:
    """
    Guarda la notificacion en la bandeja del usuario y la envia por push.

    - Con `tareas_segundo_plano` (desde un endpoint) el envio FCM se hace despues de responder.
    - Sin el (p. ej. desde una tarea que ya corre en segundo plano) se envia en el momento.
    En ambos casos un error de FCM solo se registra en el log.

    `titulo` y `cuerpo` deben ser textos genericos ("Tu documento esta listo") y `datos` solo
    identificadores: el contenido traducido nunca viaja en el push.
    """
    if tipo not in TIPOS_NOTIFICACION:
        raise ValueError(f"Tipo de notificacion no valido: {tipo}.")

    notificacion = Notificacion(
        id_usuario=id_usuario,
        tipo=tipo,
        titulo=titulo[:150],
        cuerpo=cuerpo[:500],
        datos=datos or None,
    )
    sesion.add(notificacion)
    sesion.commit()
    sesion.refresh(notificacion)

    if tareas_segundo_plano is not None:
        tareas_segundo_plano.add_task(_enviar_push_en_segundo_plano, notificacion.id_notificacion)
    else:
        enviar_push_notificacion(sesion, notificacion.id_notificacion)
    return notificacion
