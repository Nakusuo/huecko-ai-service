import httpx
import pytest

from app.llm import ErrorDelModelo, Gemini


def respuesta(codigo, cuerpo):
    return httpx.Response(codigo, json=cuerpo, request=httpx.Request("POST", "https://x"))


def test_lee_el_json_de_la_respuesta_y_manda_temperatura_cero(monkeypatch):
    enviado = {}

    def post(url, headers, json, timeout):
        enviado.update(json)
        return respuesta(200, {"candidates": [{"content": {"parts": [{"text": '{"a": 1}'}]}}]})

    monkeypatch.setattr(httpx, "post", post)

    assert Gemini("clave", "m", 1).generar_json("hola", {}) == {"a": 1}
    assert enviado["generationConfig"]["temperature"] == 0


def test_sin_clave_no_llama_a_la_red(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("no debía llamar"))

    with pytest.raises(ErrorDelModelo) as ex:
        Gemini(None, "m", 1).generar_json("hola", {})
    assert ex.value.sin_clave


def test_un_error_de_gemini_no_expone_la_clave(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: respuesta(429, {"error": "cuota"}))

    with pytest.raises(ErrorDelModelo) as ex:
        Gemini("super-secreta", "m", 1).generar_json("hola", {})
    assert "super-secreta" not in str(ex.value)
    assert not ex.value.sin_clave
