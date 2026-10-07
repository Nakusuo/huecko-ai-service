# Plan: integrar la IA en Huecko

Fecha: 2026-10-05

## Qué hará la IA

Predicción:
- **Mejores ventanas**: ordenar las ventanas de un plan según la probabilidad de que todos asistan.
- **Retrasos esperados**: minutos que suele tardar cada miembro (de `alertas_retraso`).
- **Cierre de votación**: probabilidad de llegar al quórum antes del plazo.
- **Duración del plan**: minutos estimados según título, lugar y planes parecidos.

Votación:
- **Criticidad (RF-16)**: implementar `EvaluadorCriticidad` con IA (`origen = IA`).
- **Recomendar opción** en la votación exprés: CANCELAR, REAGENDAR o MANTENER, con la razón.
- **Sugerir fechas al reagendar**: de 2 a 5 ventanas nuevas a partir del mapa de disponibilidad.

## Decisiones

- **Servicio**: Python 3.12 con FastAPI, en Docker, dentro del `docker-compose` del backend.
- **Modelo de lenguaje**: Gemini con plan gratuito (cumple RNF-09). La clave va en la variable `GEMINI_API_KEY` y nunca se sube al repo.
- **Sin estado**: el servicio no toca la base de datos. El backend le manda los datos que necesita y guarda los resultados. Así los datos tienen un solo dueño.
- **Estadística primero**: retrasos, cierre, ranking y sugerencias de fechas se calculan con estadística sencilla. El modelo de lenguaje se usa solo donde hay texto que interpretar (criticidad, recomendación, duración) y para redactar las razones.
- **Siempre hay respuesta**: el backend llama con un tiempo límite de 2 s. Si la IA falla o tarda, usa las reglas y marca `REGLAS_POR_FALLO`, como pide el contrato de RF-16.

## Contrato HTTP (v1)

| Método | Ruta | Uso |
|---|---|---|
| GET | `/salud` | Comprobar que el servicio vive |
| POST | `/v1/criticidad` | RF-16 |
| POST | `/v1/votacion-expres/recomendacion` | Recomendar opción |
| POST | `/v1/reagendar/sugerencias` | Proponer ventanas nuevas |
| POST | `/v1/retrasos/prediccion` | Estimar retrasos por miembro |
| POST | `/v1/ventanas/ranking` | Ordenar ventanas |
| POST | `/v1/votacion/prediccion-cierre` | Predecir el quórum |
| POST | `/v1/planes/duracion` | Estimar la duración |

## Fases (una rama corta por fase)

0. **Preparar**: llevar las copias locales del backend y del frontend a `origin/develop` y traer el parche de «volver a proponer fechas».
1. **Esqueleto del servicio**: FastAPI, `/salud`, Dockerfile, pruebas con pytest y el servicio sumado al compose.
2. **Criticidad con IA**: `/v1/criticidad` en el servicio, `EvaluadorPorIA` en el backend (activo con `HUECKO_IMPREVISTOS_EVALUADOR=ia`) y que pase `EvaluadorCriticidadContractTest`.
3. **Recomendación en la votación exprés**: el servicio, el campo en el DTO y su vista en `VotacionExpresPanel`.
4. **Sugerencias al reagendar**: el servicio, un endpoint en el backend y que el formulario de reagendar se rellene solo.
5. **Retrasos esperados**: el servicio, el backend y la vista en el detalle del plan.
6. **Ranking de ventanas y predicción del cierre**: el servicio, el backend y las marcas en la votación de ventanas.
7. **Duración del plan**: el servicio, el backend y una sugerencia al crear el plan.
