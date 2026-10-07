"""Solo el backend de Huecko puede usar /v1: cada llamada gasta cuota de Gemini.

Comparten un secreto, `HUECKO_IA_TOKEN`. Si el servicio no lo tiene, no
atiende a nadie: es mejor que el backend caiga a sus reglas que dejar la
cuota abierta a quien encuentre el puerto.
"""
import os
import secrets

from fastapi import Header, HTTPException


def exigir_token(x_huecko_token: str | None = Header(default=None)) -> None:
    esperado = os.getenv("HUECKO_IA_TOKEN")
    if not esperado:
        raise HTTPException(503, "El servicio no tiene HUECKO_IA_TOKEN configurado")
    # En bytes: con `str`, compare_digest lanza TypeError si la cabecera trae
    # algo que no sea ASCII, y eso acababa en un 500 en vez de un 401.
    if not x_huecko_token or not secrets.compare_digest(
            x_huecko_token.encode(), esperado.encode()):
        raise HTTPException(401, "Token inválido")
