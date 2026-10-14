from fastapi.testclient import TestClient

from app.main import crear_app
from tests.conftest import TOKEN


def cliente():
    return TestClient(crear_app(), headers={"X-Huecko-Token": TOKEN})


def test_el_ranking_premia_votos_y_disponibilidad():
    respuesta = cliente().post("/v1/ventanas/ranking", json={
        "totalMiembros": 5, "votantes": 3,
        "ventanas": [
            {"id": "a", "disponibilidadPorcentaje": 60, "votos": 0},
            {"id": "b", "disponibilidadPorcentaje": 80, "votos": 3},
            {"id": "c", "disponibilidadPorcentaje": 100, "votos": 1},
        ],
    })

    assert respuesta.status_code == 200
    ranking = respuesta.json()["ranking"]
    assert [p["id"] for p in ranking] == ["b", "c", "a"]
    assert 0 < ranking[-1]["asistenciaEsperada"] < ranking[0]["asistenciaEsperada"] <= 1
    assert "3 votos" in ranking[0]["razon"]


def test_sin_votos_manda_la_disponibilidad():
    ranking = cliente().post("/v1/ventanas/ranking", json={
        "totalMiembros": 4, "votantes": 0,
        "ventanas": [{"id": "a", "disponibilidadPorcentaje": 50, "votos": 0},
                     {"id": "b", "disponibilidadPorcentaje": 100, "votos": 0}],
    }).json()["ranking"]

    assert ranking[0]["id"] == "b"


def test_rechaza_mas_votos_que_votantes():
    respuesta = cliente().post("/v1/ventanas/ranking", json={
        "totalMiembros": 4, "votantes": 1, "ventanas": [{"id": "a", "disponibilidadPorcentaje": 50, "votos": 2}]})

    assert respuesta.status_code == 422


def cierre(**campos):
    peticion = {"totalMiembros": 5, "votantes": 1, "horasTranscurridas": 2, "horasRestantes": 22,
                "participacionHistorica": None, **campos}
    respuesta = cliente().post("/v1/votacion/prediccion-cierre", json=peticion)
    assert respuesta.status_code == 200
    return respuesta.json()


def test_con_mucho_tiempo_por_delante_lo_normal_es_llegar_a_la_mayoria():
    p = cierre()

    assert p["probabilidadMayoria"] > 0.6
    assert 3 <= p["votantesEsperados"] <= 5


def test_si_ya_voto_la_mayoria_es_seguro():
    p = cierre(votantes=3)

    assert p["probabilidadMayoria"] == 1.0
    assert "ya votó la mayoría" in p["razon"]


def test_sin_tiempo_y_sin_mayoria_no_llega():
    assert cierre(horasRestantes=0)["probabilidadMayoria"] == 0.0


def test_un_grupo_que_suele_votar_poco_baja_la_probabilidad():
    activo = cierre(participacionHistorica=0.9)["probabilidadMayoria"]
    apatico = cierre(participacionHistorica=0.3)["probabilidadMayoria"]

    assert apatico < activo
    assert "30%" in cierre(participacionHistorica=0.3)["razon"]


def test_poco_tiempo_restante_baja_la_probabilidad():
    assert cierre(horasTranscurridas=23, horasRestantes=1)["probabilidadMayoria"] < cierre()["probabilidadMayoria"]
