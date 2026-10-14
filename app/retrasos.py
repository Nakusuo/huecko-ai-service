"""Fase 5: cuánto suele tardar cada miembro.

Estadística con un supuesto previo: sin historial se asume que una de cada
cuatro veces alguien llega tarde, y cada plan real va corrigiendo ese
supuesto. Así una sola tardanza no convierte a nadie en «el impuntual».
"""
from statistics import median
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.token import exigir_token

router = APIRouter(dependencies=[Depends(exigir_token)])

# Supuesto previo (Beta(1, 3)): 1 tardanza en 4 planes, una media de 25%.
PREVIO_TARDE = 1
PREVIO_PUNTUAL = 3

Minutos = Annotated[int, Field(ge=1, le=480)]


class HistorialMiembro(BaseModel):
    usuarioId: str = Field(max_length=64)
    # Planes terminados del grupo en los que estaba; las tardanzas son de esos.
    planesPrevios: int = Field(ge=0, le=10000)
    retrasos: list[Minutos] = Field(default_factory=list, max_length=200)


class PeticionRetrasos(BaseModel):
    miembros: list[HistorialMiembro] = Field(max_length=200)


class PrediccionRetraso(BaseModel):
    usuarioId: str
    probabilidad: float
    minutosEsperados: int
    confianza: Literal["BAJA", "MEDIA", "ALTA"]
    razon: str


class RespuestaRetrasos(BaseModel):
    predicciones: list[PrediccionRetraso]


def predecir(m: HistorialMiembro) -> PrediccionRetraso:
    tarde = len(m.retrasos)
    planes = max(m.planesPrevios, tarde)
    probabilidad = round((tarde + PREVIO_TARDE) / (planes + PREVIO_TARDE + PREVIO_PUNTUAL), 2)
    # La mediana y no la media: un retraso de dos horas no define a nadie.
    minutos = max(5, 5 * round(median(m.retrasos) / 5)) if tarde else 0
    confianza = "BAJA" if planes < 3 else "MEDIA" if planes < 8 else "ALTA"

    if planes == 0:
        razon = "aún no hay planes anteriores con los que comparar"
    elif tarde == 0:
        razon = "llegó a tiempo a su plan anterior" if planes == 1 else f"llegó a tiempo a sus {planes} planes anteriores"
    else:
        razon = f"llegó tarde en {tarde} de {planes} planes, unos {minutos} min"
    return PrediccionRetraso(usuarioId=m.usuarioId, probabilidad=probabilidad,
                             minutosEsperados=minutos, confianza=confianza, razon=razon)


@router.post("/v1/retrasos/prediccion", response_model=RespuestaRetrasos)
def prediccion(peticion: PeticionRetrasos):
    return RespuestaRetrasos(predicciones=[predecir(m) for m in peticion.miembros])
