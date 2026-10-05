# huecko-ai-service

Servicio de IA de Huecko: predicciones de horarios y tiempos, y ayuda para
decidir en las votaciones. El plan completo está en [docs/plan.md](docs/plan.md).

No guarda datos. El backend le manda lo que necesita y, si el servicio falla o
tarda, sigue con sus reglas.

## Correr en local

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

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
