FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# Sin privilegios de root dentro del contenedor.
RUN useradd --create-home huecko
USER huecko

EXPOSE 8000
# Render (y otras plataformas) dicen en qué puerto escuchar con PORT; en local, 8000.
# `exec` para que uvicorn sea el PID 1 y reciba las señales de parada.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
