"""Fase 4: proponer fechas nuevas cuando un plan se reagenda.

Sin modelo de lenguaje: el backend manda las franjas en las que el grupo está
libre, ya con fecha, y aquí se elige entre ellas con una puntuación sencilla
que se puede explicar en una frase. No gasta cuota de Gemini y no falla
cuando Gemini está saturado.
"""
from datetime import date, time

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from app.token import exigir_token

router = APIRouter(dependencies=[Depends(exigir_token)])

# Cuánto pesa cada cosa frente a un punto de disponibilidad (0-100).
PESO_HORA_DE_DISTANCIA = 4
PESO_DIA_DE_ESPERA = 1.5
# Una franja donde el plan no cabe entero: castigo fijo más lo que le falte
# (una hora libre para un plan de tres no sirve casi de nada).
CASTIGO_NO_CABE = 20
CASTIGO_POR_FRACCION_QUE_FALTA = 60


class Candidata(BaseModel):
    fecha: date
    horaInicio: time
    horaFin: time
    disponibilidadPorcentaje: int = Field(ge=0, le=100)
    miembrosDisponibles: int = Field(ge=0, le=1000)
    totalMiembros: int = Field(ge=1, le=1000)

    @model_validator(mode="after")
    def termina_despues_de_empezar(self):
        if self.horaFin <= self.horaInicio:
            raise ValueError("horaFin debe ser posterior a horaInicio")
        return self


class PeticionSugerencias(BaseModel):
    duracionMinutos: int = Field(ge=15, le=720)
    # Hora del plan original: volver a la misma hora es lo que menos cuesta.
    horaPreferida: time | None = None
    candidatas: list[Candidata] = Field(max_length=100)
    maximo: int = Field(default=3, ge=2, le=5)


class Sugerencia(BaseModel):
    fecha: date
    horaInicio: time
    horaFin: time
    disponibilidadPorcentaje: int
    razon: str


class RespuestaSugerencias(BaseModel):
    sugerencias: list[Sugerencia]


def _minutos(hora: time) -> int:
    return hora.hour * 60 + hora.minute


def _hora(minutos: int) -> time:
    return time(minutos // 60, minutos % 60)


def _encajar(c: Candidata, duracion: int, preferida: int | None) -> tuple[int, int, bool]:
    """Dónde empieza y termina el plan dentro de la franja, y si cabe entero."""
    inicio, fin = _minutos(c.horaInicio), _minutos(c.horaFin)
    if fin - inicio < duracion:
        return inicio, fin, False
    if preferida is not None:
        inicio = min(max(preferida, inicio), fin - duracion)
    return inicio, inicio + duracion, True


def _razon(c: Candidata, inicio: int, preferida: int | None, mas_cercana: bool) -> str:
    if c.miembrosDisponibles >= c.totalMiembros:
        partes = ["todo el grupo está libre"]
    else:
        partes = [f"{c.miembrosDisponibles} de {c.totalMiembros} están libres"]
    if preferida is not None and inicio == preferida:
        partes.append("a la misma hora que el plan original")
    elif mas_cercana:
        partes.append("es la fecha libre más cercana")
    return " y ".join(partes)


def sugerir(peticion: PeticionSugerencias) -> RespuestaSugerencias:
    if not peticion.candidatas:
        return RespuestaSugerencias(sugerencias=[])
    preferida = _minutos(peticion.horaPreferida) if peticion.horaPreferida else None
    primera = min(c.fecha for c in peticion.candidatas)

    puntuadas = []
    for orden, c in enumerate(peticion.candidatas):
        inicio, fin, cabe = _encajar(c, peticion.duracionMinutos, preferida)
        puntos = c.disponibilidadPorcentaje - PESO_DIA_DE_ESPERA * (c.fecha - primera).days
        if preferida is not None:
            puntos -= PESO_HORA_DE_DISTANCIA * abs(inicio - preferida) / 60
        if not cabe:
            falta = 1 - (fin - inicio) / peticion.duracionMinutos
            puntos -= CASTIGO_NO_CABE + CASTIGO_POR_FRACCION_QUE_FALTA * falta
        puntuadas.append((-puntos, c.fecha, inicio, orden, c, fin))
    puntuadas.sort(key=lambda p: p[:4])

    # Una por día: tres horas distintas del mismo martes no son tres opciones.
    elegidas, dias = [], set()
    for _, fecha, inicio, _, c, fin in puntuadas:
        if fecha in dias:
            continue
        dias.add(fecha)
        elegidas.append(Sugerencia(
            fecha=fecha, horaInicio=_hora(inicio), horaFin=_hora(fin),
            disponibilidadPorcentaje=c.disponibilidadPorcentaje,
            razon=_razon(c, inicio, preferida, fecha == primera)))
        if len(elegidas) == peticion.maximo:
            break
    return RespuestaSugerencias(sugerencias=elegidas)


@router.post("/v1/reagendar/sugerencias", response_model=RespuestaSugerencias)
def sugerencias(peticion: PeticionSugerencias):
    return sugerir(peticion)
