from contextlib import asynccontextmanager

from fastapi import FastAPI


app = FastAPI(
    title="Asistente Inteligente de Traduccion Contextual"
)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend funcionando",
        "resultado": None,
    }
