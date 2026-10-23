import base64

from fastapi.testclient import TestClient

from app.horario import MAX_BLOQUES, RUTA
from app.llm import ErrorDelModelo, obtener_llm_imagen
from app.main import crear_app
from tests.conftest import TOKEN
from tests.test_criticidad import LlmFalso

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def foto(contenido: bytes = PNG, tipo: str = "image/png") -> dict:
    return {"tipo": tipo, "imagen": base64.b64encode(contenido).decode()}


def cliente_con(llm):
    app = crear_app()
    app.dependency_overrides[obtener_llm_imagen] = lambda: llm
    return TestClient(app, headers={"X-Huecko-Token": TOKEN})


def bloque(dia=1, inicio="08:00", fin="10:00", titulo="Cálculo", dudoso=False):
    return {"diaSemana": dia, "horaInicio": inicio, "horaFin": fin, "titulo": titulo, "dudoso": dudoso}


def test_devuelve_los_bloques_leidos_en_orden_de_la_semana():
    llm = LlmFalso({"bloques": [bloque(3, "14:00", "16:00", "Física"), bloque(1, "08:00", "10:00", "Cálculo")]})

    respuesta = cliente_con(llm).post(RUTA, json=foto())

    assert respuesta.status_code == 200
    assert [b["titulo"] for b in respuesta.json()["bloques"]] == ["Cálculo", "Física"]


def test_la_foto_va_como_imagen_y_no_como_texto():
    llm = LlmFalso({"bloques": []})

    cliente_con(llm).post(RUTA, json=foto(JPEG, "image/jpeg"))

    assert llm.llamadas[0][1] is None
    assert llm.imagenes[0].tipo == "image/jpeg"
    assert base64.b64decode(llm.imagenes[0].base64) == JPEG


def test_corrige_horas_sin_cero_y_titulos_con_espacios():
    llm = LlmFalso({"bloques": [bloque(2, "8:00", "9.30", "  Taller   de  Redes ")]})

    leido = cliente_con(llm).post(RUTA, json=foto()).json()["bloques"][0]

    assert (leido["horaInicio"], leido["horaFin"], leido["titulo"]) == ("08:00", "09:30", "Taller de Redes")


def test_descarta_bloques_sin_sentido_sin_tumbar_la_lectura():
    llm = LlmFalso({"bloques": [
        bloque(8, titulo="Día inexistente"),
        bloque(1, "10:00", "09:00", "Al revés"),
        bloque(1, "4pm", "6pm", "Sin formato"),
        bloque(1, titulo="   "),
        {"titulo": "Sin día ni horas"},
        "no soy un bloque",
        bloque(5, "18:00", "20:00", "Inglés", dudoso=True),
    ]})

    bloques = cliente_con(llm).post(RUTA, json=foto()).json()["bloques"]

    assert bloques == [bloque(5, "18:00", "20:00", "Inglés", dudoso=True)]


def test_quita_repetidos_y_acota_la_cantidad():
    repetidos = [bloque(1, titulo="Cálculo"), bloque(1, titulo="CÁLCULO")]
    muchos = [bloque(1 + i % 7, f"{8 + i // 7:02d}:00", f"{9 + i // 7:02d}:00", f"Curso {i}") for i in range(80)]
    llm = LlmFalso({"bloques": repetidos + muchos})

    bloques = cliente_con(llm).post(RUTA, json=foto()).json()["bloques"]

    assert len(bloques) == MAX_BLOQUES
    assert sum(1 for b in bloques if b["titulo"].lower() == "cálculo") == 1


def test_una_foto_que_no_es_un_horario_devuelve_lista_vacia():
    respuesta = cliente_con(LlmFalso({"bloques": []})).post(RUTA, json=foto())

    assert respuesta.status_code == 200
    assert respuesta.json() == {"bloques": []}


def test_una_respuesta_sin_lista_responde_502():
    respuesta = cliente_con(LlmFalso({"bloques": "lunes de 8 a 10"})).post(RUTA, json=foto())

    assert respuesta.status_code == 502


def test_sin_clave_responde_503():
    llm = LlmFalso(error=ErrorDelModelo("sin clave", sin_clave=True))

    assert cliente_con(llm).post(RUTA, json=foto()).status_code == 503


def test_la_misma_foto_no_vuelve_a_llamar_al_modelo():
    llm = LlmFalso({"bloques": [bloque()]})
    cliente = cliente_con(llm)

    cliente.post(RUTA, json=foto())
    cliente.post(RUTA, json=foto())

    assert len(llm.llamadas) == 1


def test_rechaza_lo_que_no_es_la_imagen_que_dice_ser():
    llm = LlmFalso({"bloques": []})
    cliente = cliente_con(llm)

    for cuerpo in [foto(b"GIF89a" + b"\x00" * 32, "image/png"),   # bytes de GIF con tipo PNG
                   foto(PNG, "image/gif"),                         # tipo no admitido
                   {"tipo": "image/png", "imagen": "esto no es base64!"},
                   {"tipo": "image/png", "imagen": ""}]:
        assert cliente.post(RUTA, json=cuerpo).status_code == 422, cuerpo

    assert llm.llamadas == []


def test_acepta_una_foto_grande_con_token():
    llm = LlmFalso({"bloques": []})
    grande = foto(PNG + b"\x00" * 2_000_000)

    assert cliente_con(llm).post(RUTA, json=grande).status_code == 200


def test_sin_token_una_foto_grande_se_corta_antes_de_leerla():
    grande = foto(PNG + b"\x00" * 2_000_000)

    sin_token = TestClient(crear_app()).post(RUTA, json=grande)
    token_falso = TestClient(crear_app()).post(RUTA, json=grande, headers={"X-Huecko-Token": "otro"})

    assert sin_token.status_code == 413
    assert token_falso.status_code == 413


def test_el_margen_de_la_foto_no_se_extiende_a_otras_rutas():
    cliente = TestClient(crear_app(), headers={"X-Huecko-Token": TOKEN})

    respuesta = cliente.post("/v1/criticidad", content="x" * 100_000,
                             headers={"Content-Type": "application/json"})

    assert respuesta.status_code == 413
