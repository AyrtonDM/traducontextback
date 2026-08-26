from fastapi import FastAPI


aplicacion = FastAPI(
    title="Asistente Inteligente de Traduccion Contextual"
)


@aplicacion.get("/")
def inicio():
    return {
        "mensaje": "Backend funcionando"
    }