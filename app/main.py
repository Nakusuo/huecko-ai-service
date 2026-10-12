"""Servicio de IA de Huecko.

No guarda nada en disco ni en base de datos: el backend le manda lo que
necesita en cada petición. Solo recuerda en memoria las últimas respuestas
(con sus datos) para no repetir llamadas a Gemini; se pierden al reiniciar. Si este servicio cae, el backend sigue con sus reglas.
"""
import os

from fastapi import FastAPI, Header

from app import criticidad, duracion, reagendar, recomendacion, retrasos, ventanas
from app.limite import LimiteDeCuerpo
from app.token import token_valido

VERSION = "0.6.0"


def crear_app() -> FastAPI:
    # /docs y /openapi.json describen la API a cualquiera: desplegado, el
    # servicio está en internet, así que solo se abren con HUECKO_IA_DOCS=true.
    docs = os.getenv("HUECKO_IA_DOCS", "").lower() == "true"
    app = FastAPI(
        title="Huecko IA",
        version=VERSION,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.cache = {}
    app.add_middleware(LimiteDeCuerpo)
    app.include_router(criticidad.router)
    app.include_router(recomendacion.router)
    app.include_router(reagendar.router)
    app.include_router(retrasos.router)
    app.include_router(ventanas.router)
    app.include_router(duracion.router)

    @app.get("/salud")
    def salud(x_huecko_token: str | None = Header(default=None)) -> dict:
        # Solo se dice si hay clave, nunca cuál es.
        cuerpo = {"estado": "ok", "version": VERSION, "gemini": bool(os.getenv("GEMINI_API_KEY"))}
        # Si el backend manda su token, se le dice si coincide: un token mal
        # copiado no se notaba y todo salía por reglas sin avisar.
        if x_huecko_token is not None:
            cuerpo["token"] = token_valido(x_huecko_token)
        return cuerpo

    return app


app = crear_app()
