from fastapi.testclient import TestClient

from app.llm import obtener_llm
from app.main import crear_app
from tests.conftest import TOKEN
from tests.test_criticidad import LlmFalso

PETICION = {
    "titulo": "Concierto",
    "lugar": "Estadio",
    "inicio": "2026-10-10T20:00",
    "horasHastaElPlan": 2.5,
    "motivo": "Me enfermé y tengo las entradas",
    "razonCriticidad": "tiene las entradas de todo el grupo",
    "miembrosQueVotan": 4,
    "resultadoPorDefecto": "MANTENER",
}


def cliente_con(llm):
    app = crear_app()
    app.dependency_overrides[obtener_llm] = lambda: llm
    return TestClient(app, headers={"X-Huecko-Token": TOKEN})


def test_recomienda_una_opcion_con_su_razon():
    llm = LlmFalso({"opcion": "REAGENDAR", "razon": "sin las entradas no se puede entrar al concierto"})

    respuesta = cliente_con(llm).post("/v1/votacion-expres/recomendacion", json=PETICION)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"opcion": "REAGENDAR", "razon": "sin las entradas no se puede entrar al concierto"}
    assert "2.5" in llm.llamadas[0] and "Me enfermé" in llm.llamadas[0]


def test_acepta_un_aviso_sin_motivo_ni_fecha():
    llm = LlmFalso({"opcion": "MANTENER", "razon": "el grupo puede seguir sin esa persona"})
    peticion = {**PETICION, "motivo": None, "inicio": None, "horasHastaElPlan": None}

    respuesta = cliente_con(llm).post("/v1/votacion-expres/recomendacion", json=peticion)

    assert respuesta.status_code == 200


def test_una_opcion_que_no_existe_responde_502():
    llm = LlmFalso({"opcion": "POSPONER", "razon": "no es una opción válida"})

    respuesta = cliente_con(llm).post("/v1/votacion-expres/recomendacion", json=PETICION)

    assert respuesta.status_code == 502


def test_exige_token():
    respuesta = TestClient(crear_app()).post("/v1/votacion-expres/recomendacion", json=PETICION)

    assert respuesta.status_code == 401
