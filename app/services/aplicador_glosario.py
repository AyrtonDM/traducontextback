"""
Aplicacion de glosarios personalizados durante la traduccion.

Estrategia (independiente del motor de traduccion):
1. Se buscan en el texto de origen los terminos del glosario (palabra completa,
   priorizando los terminos mas largos) y se reemplazan por marcadores (__G0__, __G1__...).
2. Se traduce el texto con marcadores; el motor los conserva sin traducirlos.
3. Cada marcador se sustituye por la traduccion preferida o por el termino original
   (si la regla indica conservarlo).
Si el motor llegara a perder algun marcador, se traduce de nuevo insertando
directamente el resultado esperado del termino en el texto de origen.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.models.glosario.glosario import Glosario
from app.schemas.glosario import TerminoAplicado


FuncionTraducir = Callable[[str, str, str], str]


@dataclass(frozen=True)
class ReglaGlosario:
    termino_origen: str
    traduccion_preferida: str | None
    conservar_original: bool
    distinguir_mayusculas: bool

    def patron(self) -> re.Pattern[str]:
        flags = 0 if self.distinguir_mayusculas else re.IGNORECASE
        return re.compile(
            rf"(?<!\w){re.escape(self.termino_origen)}(?!\w)",
            flags,
        )

    def resultado(self, texto_encontrado: str) -> str:
        if self.conservar_original:
            # Se conserva tal como aparece en el texto del usuario
            return texto_encontrado
        return self.traduccion_preferida or texto_encontrado


def construir_reglas(glosario: Glosario | None) -> list[ReglaGlosario]:
    """Convierte los terminos de un glosario en reglas ordenadas por longitud (mayor primero)."""
    if glosario is None:
        return []
    reglas = [
        ReglaGlosario(
            termino_origen=t.termino_origen,
            traduccion_preferida=t.traduccion_preferida,
            conservar_original=t.conservar_original,
            distinguir_mayusculas=t.distinguir_mayusculas,
        )
        for t in glosario.terminos
        if t.termino_origen and t.termino_origen.strip()
    ]
    reglas.sort(key=lambda r: len(r.termino_origen), reverse=True)
    return reglas


def _marcador(indice: int) -> str:
    return f"__G{indice}__"


def _patron_restauracion(indice: int) -> re.Pattern[str]:
    # Tolera espacios o guiones bajos alterados por el motor: "__G0__", "__ G0 __", "_G0_", "G0"
    return re.compile(
        rf"(?<![A-Za-z0-9])(?:_{{1,2}}\s*)?G\s*{indice}(?!\d)(?:\s*_{{1,2}})?"
    )


def traducir_con_glosario(
    texto: str,
    idioma_origen: str,
    idioma_destino: str,
    reglas: list[ReglaGlosario],
    traducir: FuncionTraducir,
) -> tuple[str, list[TerminoAplicado]]:
    """
    Traduce `texto` aplicando las reglas del glosario.
    Retorna la traduccion y la lista de terminos que se aplicaron.
    """
    if not reglas or not texto or not texto.strip():
        return traducir(texto, idioma_origen, idioma_destino), []

    reemplazos: list[str] = []
    aplicados: dict[str, TerminoAplicado] = {}
    texto_marcado = texto

    for regla in reglas:

        def _sustituir(coincidencia: re.Match[str], regla: ReglaGlosario = regla) -> str:
            encontrado = coincidencia.group(0)
            resultado = regla.resultado(encontrado)
            reemplazos.append(resultado)
            aplicados.setdefault(
                regla.termino_origen.lower(),
                TerminoAplicado(
                    termino_origen=regla.termino_origen,
                    resultado=resultado,
                    conservar_original=regla.conservar_original,
                ),
            )
            return _marcador(len(reemplazos) - 1)

        texto_marcado = regla.patron().sub(_sustituir, texto_marcado)

    if not reemplazos:
        return traducir(texto, idioma_origen, idioma_destino), []

    traduccion = traducir(texto_marcado, idioma_origen, idioma_destino)

    marcadores_ok = True
    # Se restaura del indice mayor al menor para no confundir G1 con G10
    for indice in range(len(reemplazos) - 1, -1, -1):
        patron = _patron_restauracion(indice)
        if not patron.search(traduccion):
            marcadores_ok = False
            break
        traduccion = patron.sub(lambda _m, i=indice: reemplazos[i], traduccion, count=1)

    if not marcadores_ok:
        # Respaldo: insertar el resultado esperado directamente en el texto de origen
        texto_directo = texto_marcado
        for indice in range(len(reemplazos) - 1, -1, -1):
            texto_directo = texto_directo.replace(_marcador(indice), reemplazos[indice])
        traduccion = traducir(texto_directo, idioma_origen, idioma_destino)

    return traduccion, list(aplicados.values())


def respeta_terminos_glosario(
    texto_adaptado: str,
    texto_base: str,
    terminos_aplicados: list[TerminoAplicado],
) -> bool:
    """
    Verifica que un texto reescrito (p. ej. adaptado a una variante regional) conserve tal cual
    los terminos del glosario que ya aparecian en la traduccion base.
    """
    base = texto_base.lower()
    adaptado = texto_adaptado.lower()
    for termino in terminos_aplicados:
        esperado = termino.resultado.lower()
        if esperado and esperado in base and esperado not in adaptado:
            return False
    return True


def describir_reglas(reglas: list[ReglaGlosario]) -> list[str]:
    """Descripcion legible de las reglas (para indicarlas a modelos de lenguaje)."""
    descripciones = []
    for regla in reglas:
        if regla.conservar_original:
            descripciones.append(f"'{regla.termino_origen}' -> conservar sin traducir")
        else:
            descripciones.append(
                f"'{regla.termino_origen}' -> traducir siempre como '{regla.traduccion_preferida}'"
            )
    return descripciones
