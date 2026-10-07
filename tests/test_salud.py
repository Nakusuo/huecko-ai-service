from fastapi.testclient import TestClient

from app.main import crear_app


def test_salud_responde_ok_y_dice_si_hay_clave_de_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    respuesta = TestClient(crear_app()).get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "version": "0.1.0", "gemini": False}


def test_salud_detecta_la_clave_sin_mostrarla(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secreta")
    cuerpo = TestClient(crear_app()).get("/salud").json()

    assert cuerpo["gemini"] is True
    assert "secreta" not in str(cuerpo)
