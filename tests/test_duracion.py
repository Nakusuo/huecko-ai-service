from fastapi.testclient import TestClient

from app.llm import ErrorDelModelo, obtener_llm
from app.main import crear_app
from tests.conftest import TOKEN
from tests.test_criticidad import LlmFalso

PETICION = {"titulo": "Cine", "lugar": "Larcomar",
            "anteriores": [{"titulo": "Cine en el Jockey", "lugar": None, "minutos": 150}]}


def cliente_con(llm):
    app = crear_app()
    app.dependency_overrides[obtener_llm] = lambda: llm
    return TestClient(app, headers={"X-Huecko-Token": TOKEN})


def test_estima_la_duracion_con_los_planes_anteriores_del_grupo():
    llm = LlmFalso({"minutos": 150, "razon": "el último cine del grupo duró dos horas y media"})

    respuesta = cliente_con(llm).post("/v1/planes/duracion", json=PETICION)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"minutos": 150, "razon": "el último cine del grupo duró dos horas y media"}
    assert llm.llamadas[0][1]["anteriores"][0]["minutos"] == 150


def test_redondea_a_cuartos_de_hora_y_acota():
    def minutos(valor):
        llm = LlmFalso({"minutos": valor, "razon": "un plan de este tipo suele durar eso"})
        return cliente_con(llm).post("/v1/planes/duracion", json=PETICION).json()["minutos"]

    assert minutos(97) == 90
    assert minutos(5000) == 480
    assert minutos(1) == 30


def test_sin_titulo_no_hay_nada_que_estimar():
    respuesta = cliente_con(LlmFalso({})).post("/v1/planes/duracion", json={**PETICION, "titulo": "  "})

    assert respuesta.status_code == 422


def test_si_gemini_falla_responde_502():
    respuesta = cliente_con(LlmFalso(error=ErrorDelModelo("caída"))).post("/v1/planes/duracion", json=PETICION)

    assert respuesta.status_code == 502


def test_una_razon_con_enlace_se_descarta():
    respuesta = cliente_con(LlmFalso({"minutos": 60, "razon": "mira www.cine.com para saberlo"})).post(
        "/v1/planes/duracion", json=PETICION)

    assert respuesta.status_code == 502
