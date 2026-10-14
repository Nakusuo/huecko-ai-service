from fastapi.testclient import TestClient

from app.main import crear_app
from tests.conftest import TOKEN


def candidata(fecha, inicio, fin, libres=4, total=4):
    return {"fecha": fecha, "horaInicio": inicio, "horaFin": fin,
            "disponibilidadPorcentaje": libres * 100 // total,
            "miembrosDisponibles": libres, "totalMiembros": total}


def sugerir(peticion):
    return TestClient(crear_app(), headers={"X-Huecko-Token": TOKEN}).post("/v1/reagendar/sugerencias", json=peticion)


def test_prefiere_la_misma_hora_del_plan_original_y_ajusta_la_duracion():
    respuesta = sugerir({
        "duracionMinutos": 120, "horaPreferida": "18:00",
        "candidatas": [candidata("2026-10-14", "14:00", "20:00")],
    })

    assert respuesta.status_code == 200
    [s] = respuesta.json()["sugerencias"]
    assert (s["fecha"], s["horaInicio"], s["horaFin"]) == ("2026-10-14", "18:00:00", "20:00:00")
    assert "misma hora" in s["razon"]


def test_si_la_hora_no_cabe_la_corre_dentro_de_la_franja():
    [s] = sugerir({
        "duracionMinutos": 120, "horaPreferida": "19:00",
        "candidatas": [candidata("2026-10-14", "14:00", "20:00")],
    }).json()["sugerencias"]

    assert (s["horaInicio"], s["horaFin"]) == ("18:00:00", "20:00:00")


def test_ordena_por_disponibilidad_y_da_una_por_dia():
    sugerencias = sugerir({
        "duracionMinutos": 60, "horaPreferida": None, "maximo": 3,
        "candidatas": [
            candidata("2026-10-14", "10:00", "12:00", libres=2),
            candidata("2026-10-15", "10:00", "12:00", libres=4),
            candidata("2026-10-15", "15:00", "17:00", libres=4),
            candidata("2026-10-16", "10:00", "12:00", libres=3),
        ],
    }).json()["sugerencias"]

    assert [s["fecha"] for s in sugerencias] == ["2026-10-15", "2026-10-16", "2026-10-14"]
    assert "todo el grupo" in sugerencias[0]["razon"]
    assert "3 de 4" in sugerencias[1]["razon"]


def test_las_franjas_demasiado_cortas_van_al_final():
    sugerencias = sugerir({
        "duracionMinutos": 180, "horaPreferida": None,
        "candidatas": [
            candidata("2026-10-14", "10:00", "11:00"),
            candidata("2026-10-15", "10:00", "14:00", libres=3),
        ],
    }).json()["sugerencias"]

    assert sugerencias[0]["fecha"] == "2026-10-15"
    assert sugerencias[0]["horaFin"] == "13:00:00"


def test_sin_candidatas_no_hay_sugerencias():
    assert sugerir({"duracionMinutos": 60, "candidatas": []}).json() == {"sugerencias": []}


def test_rechaza_una_franja_que_termina_antes_de_empezar():
    respuesta = sugerir({"duracionMinutos": 60, "candidatas": [candidata("2026-10-14", "12:00", "10:00")]})

    assert respuesta.status_code == 422


def test_exige_token():
    respuesta = TestClient(crear_app()).post("/v1/reagendar/sugerencias", json={"duracionMinutos": 60, "candidatas": []})

    assert respuesta.status_code == 401
