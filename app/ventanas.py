"""Fase 6: qué ventana conviene más y si la votación llegará a la mayoría.

Estadística, sin modelo de lenguaje. Los pesos son supuestos razonables, no
aprendidos; están aquí juntos para poder discutirlos y cambiarlos.
"""
from math import comb

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from app.token import exigir_token

router = APIRouter(dependencies=[Depends(exigir_token)])

# Probabilidad de que asista a una ventana...
ASISTE_SI_LA_VOTO = 0.95
ASISTE_SI_VOTO_OTRA = 0.6   # ...por su disponibilidad, si prefirió otra
ASISTE_SI_NO_VOTO = 0.85    # ...por su disponibilidad, si aún no votó

PARTICIPACION_POR_DEFECTO = 0.75


class VentanaVotada(BaseModel):
    id: str = Field(max_length=64)
    disponibilidadPorcentaje: int = Field(ge=0, le=100)
    votos: int = Field(ge=0, le=1000)


class PeticionRanking(BaseModel):
    totalMiembros: int = Field(ge=1, le=1000)
    # Personas que votaron alguna ventana (con voto múltiple, votos > votantes).
    votantes: int = Field(ge=0, le=1000)
    ventanas: list[VentanaVotada] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def cuentas_coherentes(self):
        if self.votantes > self.totalMiembros:
            raise ValueError("Más votantes que miembros")
        if any(v.votos > self.votantes for v in self.ventanas):
            raise ValueError("Una ventana tiene más votos que votantes")
        return self


class Puesto(BaseModel):
    id: str
    asistenciaEsperada: float
    razon: str


class RespuestaRanking(BaseModel):
    ranking: list[Puesto]


def asistencia(v: VentanaVotada, total: int, votantes: int) -> float:
    libre = v.disponibilidadPorcentaje / 100
    esperados = (v.votos * ASISTE_SI_LA_VOTO
                 + (votantes - v.votos) * libre * ASISTE_SI_VOTO_OTRA
                 + (total - votantes) * libre * ASISTE_SI_NO_VOTO)
    return round(min(1.0, esperados / total), 2)


@router.post("/v1/ventanas/ranking", response_model=RespuestaRanking)
def ranking(peticion: PeticionRanking):
    puestos = []
    for orden, v in enumerate(peticion.ventanas):
        votos = "1 voto" if v.votos == 1 else f"{v.votos} votos"
        puestos.append((asistencia(v, peticion.totalMiembros, peticion.votantes), v.votos, -orden,
                        Puesto(id=v.id, asistenciaEsperada=0, razon=f"{votos} y {v.disponibilidadPorcentaje}% del grupo libre")))
    puestos.sort(key=lambda p: p[:3], reverse=True)
    return RespuestaRanking(ranking=[p[3].model_copy(update={"asistenciaEsperada": p[0]}) for p in puestos])


class PeticionCierre(BaseModel):
    totalMiembros: int = Field(ge=1, le=1000)
    votantes: int = Field(ge=0, le=1000)
    horasTranscurridas: float = Field(ge=0, le=24 * 60)
    horasRestantes: float = Field(ge=0, le=24 * 60)
    # Qué parte del grupo votó en sus planes anteriores; null si no hay.
    participacionHistorica: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def votantes_posibles(self):
        if self.votantes > self.totalMiembros:
            raise ValueError("Más votantes que miembros")
        return self


class PrediccionCierre(BaseModel):
    probabilidadMayoria: float
    votantesEsperados: int
    razon: str


def _al_menos(n: int, p: float, k: int) -> float:
    """P(Binomial(n, p) >= k)."""
    if k <= 0:
        return 1.0
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _horas(h: float) -> str:
    if h < 1:
        return "menos de una hora"
    return "1 hora" if round(h) == 1 else f"{round(h)} horas"


@router.post("/v1/votacion/prediccion-cierre", response_model=PrediccionCierre)
def prediccion_cierre(p: PeticionCierre):
    mayoria = p.totalMiembros // 2 + 1
    pendientes = p.totalMiembros - p.votantes
    historica = p.participacionHistorica if p.participacionHistorica is not None else PARTICIPACION_POR_DEFECTO

    if p.votantes >= mayoria:
        return PrediccionCierre(probabilidadMayoria=1.0, votantesEsperados=p.votantes,
                                razon="ya votó la mayoría del grupo")

    if pendientes == 0 or p.horasRestantes <= 0:
        probabilidad, cada_uno = 0.0, 0.0
    else:
        # Lo que suele votar el grupo, repartido entre quienes faltan...
        cada_uno = min(1.0, max(0.0, historica * p.totalMiembros - p.votantes) / pendientes)
        # ...y menos cuanto menos tiempo queda: con más de la mitad del plazo
        # por delante, nada; al final, casi todo el que iba a votar ya votó.
        duracion = p.horasTranscurridas + p.horasRestantes
        cada_uno *= min(1.0, 2 * p.horasRestantes / duracion) if duracion > 0 else 1.0
        probabilidad = _al_menos(pendientes, cada_uno, mayoria - p.votantes)

    faltan = mayoria - p.votantes
    razon = f"faltan {faltan} voto{'s' if faltan != 1 else ''} para la mayoría y quedan {_horas(p.horasRestantes)}"
    if p.participacionHistorica is not None:
        razon += f"; en planes anteriores votó el {round(historica * 100)}% del grupo"
    return PrediccionCierre(probabilidadMayoria=round(probabilidad, 2),
                            votantesEsperados=round(p.votantes + pendientes * cada_uno), razon=razon)
