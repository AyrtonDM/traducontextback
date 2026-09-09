from app.services.analizador_contextual import AnalizadorContextual


class MotorContextual:

    def __init__(self):
        self.analizador = AnalizadorContextual()

    def analizar(
        self,
        contexto: str,
        texto: str
    ):

        contexto = contexto.strip()
        texto = texto.strip()

        if not contexto:
            raise ValueError(
                "El contexto no puede estar vacio."
            )

        if not texto:
            raise ValueError(
                "El texto no puede estar vacio."
            )

        return self.analizador.analizar(
            contexto=contexto,
            texto=texto
        )