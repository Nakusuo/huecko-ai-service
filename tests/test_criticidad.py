from fastapi.testclient import TestClient

from app.llm import ErrorDelModelo, obtener_llm
from app.main import crear_app
from tests.conftest import TOKEN


class LlmFalso:
    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas = []

    def generar_json(self, instrucciones, datos, esquema):
        self.llamadas.append((instrucciones, datos))
        if self.error:
            raise self.error
        return self.respuesta


def cliente_con(llm):
    app = crear_app()
    app.dependency_overrides[obtener_llm] = lambda: llm
    return TestClient(app, headers={"X-Huecko-Token": TOKEN})


PETICION = {
    "titulo": "Concierto",
    "lugar": "Estadio",
    "rol": "MIEMBRO",
    "motivo": "Me enfermé y yo tengo las entradas de todos",
}


def test_devuelve_el_veredicto_del_modelo():
    llm = LlmFalso({"criticidad": "CRITICA", "razon": "tiene las entradas de todo el grupo"})

    respuesta = cliente_con(llm).post("/v1/criticidad", json=PETICION)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"criticidad": "CRITICA", "razon": "tiene las entradas de todo el grupo"}
    assert llm.llamadas[0][1]["motivo"] == "Me enfermé y yo tengo las entradas de todos"


def test_la_misma_peticion_no_vuelve_a_llamar_al_modelo():
    # Determinismo (contrato 7 de RF-16): la misma ausencia da lo mismo siempre.
    llm = LlmFalso({"criticidad": "NO_CRITICA", "razon": "su ausencia no afecta al plan"})
    cliente = cliente_con(llm)
    otra = {**PETICION, "motivo": "otro motivo distinto"}

    cliente.post("/v1/criticidad", json=otra)
    cliente.post("/v1/criticidad", json=otra)

    assert len(llm.llamadas) == 1


def test_sin_clave_responde_503():
    respuesta = cliente_con(LlmFalso(error=ErrorDelModelo("sin clave", sin_clave=True))).post(
        "/v1/criticidad", json={**PETICION, "motivo": "motivo sin clave"})

    assert respuesta.status_code == 503


def test_respuesta_del_modelo_ilegible_responde_502():
    llm = LlmFalso({"criticidad": "QUIZAS", "razon": "x"})

    respuesta = cliente_con(llm).post("/v1/criticidad", json={**PETICION, "motivo": "motivo raro"})

    assert respuesta.status_code == 502


def test_rechaza_peticion_sin_motivo():
    respuesta = cliente_con(LlmFalso()).post("/v1/criticidad", json={**PETICION, "motivo": "  "})

    assert respuesta.status_code == 422
