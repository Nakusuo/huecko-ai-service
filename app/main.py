"""Servicio de IA de Huecko.

No guarda datos: el backend le manda lo que necesita en cada petición y se
queda con el resultado. Si este servicio cae, el backend sigue con sus reglas.
"""
import os

from fastapi import FastAPI

VERSION = "0.1.0"


def crear_app() -> FastAPI:
    app = FastAPI(title="Huecko IA", version=VERSION)

    @app.get("/salud")
    def salud() -> dict:
        # Solo se dice si hay clave, nunca cuál es.
        return {"estado": "ok", "version": VERSION, "gemini": bool(os.getenv("GEMINI_API_KEY"))}

    return app


app = crear_app()
