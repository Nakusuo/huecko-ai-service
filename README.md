<p align="center">
  <a href="https://github.com/Nakusuo"><img src="https://raw.githubusercontent.com/Nakusuo/Nakusuo/main/assets/covers/huecko-ai-service.svg" width="100%" alt="huecko-ai-service — Nakusu"/></a>
</p>

# huecko-ai-service

Servicio de IA de Huecko: predicciones de horarios y tiempos, y ayuda para
decidir en las votaciones. El plan completo está en [docs/plan.md](docs/plan.md).

No guarda nada en disco ni en base de datos: el backend le manda lo que
necesita, y solo se recuerdan en memoria las últimas respuestas para no
repetir llamadas a Gemini. Si el servicio falla o tarda, el backend sigue con
sus reglas.

## Correr en local

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000 --env-file .env
```

Copia `.env.example` como `.env` y pon tu clave (`.env` no se sube).
`GET http://localhost:8000/salud` debe responder `{"estado": "ok", ...}`.

## Con Docker, junto al backend

Clona este repo al lado de `huecko-backend` y, desde el backend:

```bash
docker compose --profile ia up -d
```

## Variables

| Variable | Para qué |
|---|---|
| `GEMINI_API_KEY` | Clave gratuita de Google AI Studio. Nunca se sube al repo. |
| `HUECKO_IA_TOKEN` | Secreto compartido con el backend; `/v1` exige la cabecera `X-Huecko-Token`. Sin él, `/v1` responde 503. |
| `GEMINI_MODELO` | Modelo de Gemini. Por defecto `gemini-3.5-flash-lite` (~1,5 s). Mejor una versión fija: los alias `-latest` cambian solos y los modelos que razonan tardan más que `GEMINI_TIEMPO_MAXIMO`. |
| `GEMINI_TIEMPO_MAXIMO` | Segundos de espera a Gemini. Por defecto `3`; el backend debe esperar más (`HUECKO_IA_TIEMPO_MAXIMO_MS`, 3500). |
| `HUECKO_IA_DOCS` | `true` abre `/docs` y `/openapi.json`. Cerrados por defecto, porque desplegado el servicio está en internet. |
| `PORT` | Puerto en el que escucha la imagen Docker. Por defecto `8000`; Render pone el suyo. |

## Endpoints

| Ruta | Qué hace |
|---|---|
| `GET /salud` | Estado y si hay clave de Gemini. Con `X-Huecko-Token`, también si el token coincide (`"token": true/false`). |
| `POST /v1/criticidad` | RF-16: lee el motivo de una ausencia y dice si es crítica. 503 sin clave, 502 si Gemini falla. |
| `POST /v1/votacion-expres/recomendacion` | Sugiere CANCELAR, REAGENDAR o MANTENER con la razón. Se calcula con los hechos del aviso, no con los votos. |
| `POST /v1/reagendar/sugerencias` | Fase 4: elige 2–5 fechas nuevas entre las franjas libres del grupo (una por día, cerca de la hora original). Estadística, sin Gemini. |
| `POST /v1/retrasos/prediccion` | Fase 5: probabilidad de que cada miembro llegue tarde y minutos típicos, con un supuesto previo de 1 de cada 4. Sin Gemini. |
| `POST /v1/ventanas/ranking` | Fase 6: ordena las ventanas de un plan por asistencia esperada (votos + disponibilidad). Sin Gemini. |
| `POST /v1/votacion/prediccion-cierre` | Fase 6: probabilidad de que vote la mayoría antes del plazo (binomial con la participación histórica). Sin Gemini. |
| `POST /v1/planes/duracion` | Fase 7: estima la duración de un plan por su título y los planes anteriores del grupo. Con Gemini; 503/502 como criticidad. |
