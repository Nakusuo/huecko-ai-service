"""El servicio está en internet: lo que entra tiene que tener tamaño acotado.

Sin límites, un título de 2 MB se mandaba entero a Gemini (cuota y coste), y
cualquiera, sin token, podía mandar cuerpos enormes y tumbar la instancia de
512 MB: FastAPI lee el cuerpo antes de comprobar el token.
"""
from fastapi.testclient import TestClient

from app.main import crear_app
from tests.conftest import TOKEN
from tests.test_criticidad import LlmFalso, cliente_con
from tests.test_recomendacion import PETICION as RECOMENDACION

CRITICIDAD = {"titulo": "Cena", "rol": "MIEMBRO", "motivo": "no puedo"}


def test_un_cuerpo_enorme_se_rechaza_sin_leerlo_aunque_no_haya_token():
    cliente = TestClient(crear_app())
    enorme = "x" * 100_000

    respuesta = cliente.post("/v1/criticidad", content=enorme,
                             headers={"Content-Type": "application/json"})

    assert respuesta.status_code == 413


def test_titulo_demasiado_largo_se_rechaza_en_criticidad():
    llm = LlmFalso({"criticidad": "CRITICA", "razon": "tiene las entradas de todos"})

    respuesta = cliente_con(llm).post("/v1/criticidad", json={**CRITICIDAD, "titulo": "t" * 500})

    assert respuesta.status_code == 422
    assert llm.llamadas == []


def test_campos_de_recomendacion_acotados():
    llm = LlmFalso({"opcion": "MANTENER", "razon": "falta mucho para el plan"})
    cliente = cliente_con(llm)

    for campo, valor in [("razonCriticidad", "r" * 1000), ("lugar", "l" * 1000),
                         ("inicio", "i" * 200), ("miembrosQueVotan", -5),
                         ("horasHastaElPlan", -1000)]:
        respuesta = cliente.post("/v1/votacion-expres/recomendacion",
                                 json={**RECOMENDACION, campo: valor})
        assert respuesta.status_code == 422, campo

    assert llm.llamadas == []
