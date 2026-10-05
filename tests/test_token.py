from fastapi.testclient import TestClient

from app.main import crear_app

PETICION = {"titulo": "Cena", "rol": "MIEMBRO", "motivo": "no puedo"}


def test_sin_token_rechaza_con_401():
    respuesta = TestClient(crear_app()).post("/v1/criticidad", json=PETICION)

    assert respuesta.status_code == 401


def test_con_token_equivocado_rechaza_con_401():
    respuesta = TestClient(crear_app()).post(
        "/v1/criticidad", json=PETICION, headers={"X-Huecko-Token": "otro"})

    assert respuesta.status_code == 401


def test_si_el_servicio_no_tiene_token_no_atiende_a_nadie(monkeypatch):
    monkeypatch.delenv("HUECKO_IA_TOKEN")

    respuesta = TestClient(crear_app()).post(
        "/v1/criticidad", json=PETICION, headers={"X-Huecko-Token": ""})

    assert respuesta.status_code == 503


def test_salud_no_pide_token():
    assert TestClient(crear_app()).get("/salud").status_code == 200
