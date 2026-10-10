"""Lo común a todo endpoint que pregunta al modelo: caché, llamada y validación."""
import re
import threading
from typing import TypeVar

from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError

from app.llm import ErrorDelModelo, Gemini

TAMANO_CACHE = 512
_CERROJO = threading.Lock()

R = TypeVar("R", bound=BaseModel)


def consultar(request: Request, llm: Gemini, peticion: BaseModel, instrucciones: str,
              esquema: dict, tipo: type[R]) -> R:
    """Pregunta al modelo y valida la respuesta contra `tipo`.

    La misma petición devuelve lo mismo sin volver a llamar: el grupo no debe
    ver cambiar un veredicto por recargar, y se ahorra cuota gratuita.
    """
    cache: dict = request.app.state.cache
    clave = (request.url.path, peticion.model_dump_json())
    with _CERROJO:
        if clave in cache:
            return cache[clave]

    try:
        resultado = tipo.model_validate(llm.generar_json(instrucciones, peticion.model_dump(), esquema))
    except ErrorDelModelo as ex:
        raise HTTPException(503 if ex.sin_clave else 502, str(ex)) from ex
    except ValidationError as ex:
        raise HTTPException(502, "El modelo devolvió una respuesta ilegible") from ex

    # Las rutas síncronas corren en un pool de hilos: sin cerrojo, dos a la
    # vez podían sacar la misma entrada y el `pop` fallaba.
    with _CERROJO:
        while len(cache) >= TAMANO_CACHE:
            cache.pop(next(iter(cache)), None)
        cache[clave] = resultado
    return resultado


ENLACE = re.compile(r"https?://|www\.|\w+\.(com|net|org|pe|io|app|example)\b", re.IGNORECASE)


def razon_legible(valor: str) -> str:
    """La razón se muestra tal cual al grupo: ni vacía, ni un párrafo, ni enlaces.

    Si un usuario logra torcer al modelo, lo peor que llega al grupo es una
    frase corta sin enlaces, dentro de un recuadro marcado como de la IA.
    """
    valor = valor.strip()
    if len(valor) <= 8:
        raise ValueError("Razón demasiado corta")
    if len(valor) > 200:
        raise ValueError("Razón demasiado larga")
    if ENLACE.search(valor):
        raise ValueError("La razón no puede llevar enlaces")
    return valor
