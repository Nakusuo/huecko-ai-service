from fastapi.testclient import TestClient

from app.main import crear_app
from tests.conftest import TOKEN


def predecir(miembros):
    respuesta = TestClient(crear_app(), headers={"X-Huecko-Token": TOKEN}).post(
        "/v1/retrasos/prediccion", json={"miembros": miembros})
    assert respuesta.status_code == 200
    return {p["usuarioId"]: p for p in respuesta.json()["predicciones"]}


def test_quien_suele_llegar_tarde_tiene_mas_probabilidad_y_sus_minutos_tipicos():
    p = predecir([
        {"usuarioId": "ana", "planesPrevios": 6, "retrasos": [10, 20, 15, 15, 15]},
        {"usuarioId": "luis", "planesPrevios": 6, "retrasos": []},
    ])

    assert p["ana"]["probabilidad"] > 0.5 > p["luis"]["probabilidad"]
    assert p["ana"]["minutosEsperados"] == 15
    assert p["luis"]["minutosEsperados"] == 0
    assert "5 de 6" in p["ana"]["razon"]


def test_sin_historial_no_se_inventa_nada():
    p = predecir([{"usuarioId": "nuevo", "planesPrevios": 0, "retrasos": []}])["nuevo"]

    assert p["confianza"] == "BAJA"
    assert p["probabilidad"] == 0.25
    assert "no hay planes anteriores" in p["razon"]


def test_la_confianza_crece_con_el_historial():
    p = predecir([
        {"usuarioId": "a", "planesPrevios": 2, "retrasos": [5]},
        {"usuarioId": "b", "planesPrevios": 5, "retrasos": [5]},
        {"usuarioId": "c", "planesPrevios": 12, "retrasos": [5]},
    ])

    assert [p[x]["confianza"] for x in "abc"] == ["BAJA", "MEDIA", "ALTA"]


def test_mas_retrasos_que_planes_cuenta_los_retrasos():
    p = predecir([{"usuarioId": "x", "planesPrevios": 1, "retrasos": [5, 5, 5]}])["x"]

    assert "3 de 3" in p["razon"]


def test_rechaza_minutos_imposibles():
    respuesta = TestClient(crear_app(), headers={"X-Huecko-Token": TOKEN}).post(
        "/v1/retrasos/prediccion", json={"miembros": [{"usuarioId": "x", "planesPrevios": 1, "retrasos": [9999]}]})

    assert respuesta.status_code == 422
