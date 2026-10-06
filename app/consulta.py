"""Lo común a todo endpoint que pregunta al modelo: caché, llamada y validación."""
from typing import TypeVar

from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError

from app.llm import ErrorDelModelo, Gemini

TAMANO_CACHE = 512

R = TypeVar("R", bound=BaseModel)


def consultar(request: Request, llm: Gemini, peticion: BaseModel, prompt: str,
              esquema: dict, tipo: type[R]) -> R:
    """Pregunta al modelo y valida la respuesta contra `tipo`.

    La misma petición devuelve lo mismo sin volver a llamar: el grupo no debe
    ver cambiar un veredicto por recargar, y se ahorra cuota gratuita.
    """
    cache: dict = request.app.state.cache
    clave = (request.url.path, peticion.model_dump_json())
    if clave in cache:
        return cache[clave]

    try:
        resultado = tipo.model_validate(llm.generar_json(prompt, esquema))
    except ErrorDelModelo as ex:
        raise HTTPException(503 if ex.sin_clave else 502, str(ex)) from ex
    except ValidationError as ex:
        raise HTTPException(502, "El modelo devolvió una respuesta ilegible") from ex

    if len(cache) >= TAMANO_CACHE:
        cache.pop(next(iter(cache)))
    cache[clave] = resultado
    return resultado


def razon_legible(valor: str) -> str:
    """La razón se muestra tal cual al grupo: ni vacía ni de tres letras."""
    valor = valor.strip()
    if len(valor) <= 8:
        raise ValueError("Razón demasiado corta")
    return valor
