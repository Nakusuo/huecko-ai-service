"""Solo el backend de Huecko puede usar /v1: cada llamada gasta cuota de Gemini.

Comparten un secreto, `HUECKO_IA_TOKEN`. Si el servicio no lo tiene, no
atiende a nadie: es mejor que el backend caiga a sus reglas que dejar la
cuota abierta a quien encuentre el puerto.
"""
import os
import secrets

from fastapi import Header, HTTPException


def token_valido(recibido: str | bytes | None) -> bool:
    """Si `recibido` es el secreto compartido. Sin secreto configurado, nada lo es."""
    esperado = os.getenv("HUECKO_IA_TOKEN")
    if not esperado or not recibido:
        return False
    # En bytes: con `str`, compare_digest lanza TypeError si la cabecera trae
    # algo que no sea ASCII, y eso acababa en un 500 en vez de un 401.
    if isinstance(recibido, str):
        recibido = recibido.encode()
    return secrets.compare_digest(recibido, esperado.encode())


def exigir_token(x_huecko_token: str | None = Header(default=None)) -> None:
    if not os.getenv("HUECKO_IA_TOKEN"):
        raise HTTPException(503, "El servicio no tiene HUECKO_IA_TOKEN configurado")
    if not token_valido(x_huecko_token):
        raise HTTPException(401, "Token inválido")
