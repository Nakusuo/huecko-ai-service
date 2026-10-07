"""Servicio de IA de Huecko.

No guarda datos: el backend le manda lo que necesita en cada petición y se
queda con el resultado. Si este servicio cae, el backend sigue con sus reglas.
"""
import os

from fastapi import FastAPI

from app import criticidad, recomendacion

VERSION = "0.1.0"


def crear_app() -> FastAPI:
    app = FastAPI(title="Huecko IA", version=VERSION)
    app.state.cache = {}
    app.include_router(criticidad.router)
    app.include_router(recomendacion.router)

    @app.get("/salud")
    def salud() -> dict:
        # Solo se dice si hay clave, nunca cuál es.
        return {"estado": "ok", "version": VERSION, "gemini": bool(os.getenv("GEMINI_API_KEY"))}

    return app


app = crear_app()
