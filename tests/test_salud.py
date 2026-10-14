from fastapi.testclient import TestClient

from app.main import crear_app


def test_salud_responde_ok_y_dice_si_hay_clave_de_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    respuesta = TestClient(crear_app()).get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "version": "0.6.0", "gemini": False}


def test_salud_detecta_la_clave_sin_mostrarla(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secreta")
    cuerpo = TestClient(crear_app()).get("/salud").json()

    assert cuerpo["gemini"] is True
    assert "secreta" not in str(cuerpo)


def test_la_documentacion_de_la_api_esta_cerrada_por_defecto(monkeypatch):
    monkeypatch.delenv("HUECKO_IA_DOCS", raising=False)
    cliente = TestClient(crear_app())

    assert cliente.get("/docs").status_code == 404
    assert cliente.get("/openapi.json").status_code == 404


def test_la_documentacion_se_abre_con_huecko_ia_docs(monkeypatch):
    monkeypatch.setenv("HUECKO_IA_DOCS", "true")
    cliente = TestClient(crear_app())

    assert cliente.get("/docs").status_code == 200
    assert cliente.get("/openapi.json").status_code == 200


def test_salud_dice_si_el_token_del_backend_coincide():
    # Sin esto, un token mal copiado pasaba por «activa» y todo salía por reglas.
    cliente = TestClient(crear_app())

    assert cliente.get("/salud", headers={"X-Huecko-Token": "token-de-prueba"}).json()["token"] is True
    assert cliente.get("/salud", headers={"X-Huecko-Token": "otro"}).json()["token"] is False


def test_salud_sin_cabecera_no_habla_del_token():
    assert "token" not in TestClient(crear_app()).get("/salud").json()


def test_salud_con_token_pero_sin_configurar_lo_da_por_invalido(monkeypatch):
    monkeypatch.delenv("HUECKO_IA_TOKEN")
    cuerpo = TestClient(crear_app()).get("/salud", headers={"X-Huecko-Token": "x"}).json()

    assert cuerpo["token"] is False
