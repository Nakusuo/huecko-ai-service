"""Tope al tamaño del cuerpo de las peticiones.

FastAPI lee y parsea el cuerpo antes de resolver las dependencias, también la
del token, así que sin esto cualquiera podía mandar JSON enorme a /v1 y tumbar
la instancia (512 MB en el plan gratuito) sin conocer el token. Lo que el
backend manda de verdad cabe de sobra en unos pocos KB.

La foto de un horario no cabe, así que algunas rutas tienen su propio tope.
Ese margen solo se da a quien trae el token correcto: comprobarlo aquí no
cuesta nada, y así un anónimo sigue sin poder hacer leer megas al servicio.
"""
import json

from app.token import token_valido

MAX_BYTES = 16 * 1024

_RESPUESTA = json.dumps({"detail": "Petición demasiado grande"}).encode()


class _Demasiado(Exception):
    pass


class LimiteDeCuerpo:
    def __init__(self, app, max_bytes: int = MAX_BYTES, por_ruta: dict[str, int] | None = None):
        self.app = app
        self.max_bytes = max_bytes
        self.por_ruta = por_ruta or {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cabeceras = dict(scope.get("headers") or [])
        maximo = self._maximo(scope.get("path", ""), cabeceras)
        declarado = cabeceras.get(b"content-length")
        if declarado is not None and declarado.isdigit() and int(declarado) > maximo:
            await self._rechazar(send)
            return

        # Sin Content-Length (envío por trozos) se cuenta según llega.
        leidos = 0

        async def recibir_contando():
            nonlocal leidos
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                leidos += len(mensaje.get("body", b""))
                if leidos > maximo:
                    raise _Demasiado()
            return mensaje

        try:
            await self.app(scope, recibir_contando, send)
        except _Demasiado:
            await self._rechazar(send)

    def _maximo(self, ruta: str, cabeceras: dict) -> int:
        if ruta in self.por_ruta and token_valido(cabeceras.get(b"x-huecko-token")):
            return self.por_ruta[ruta]
        return self.max_bytes

    @staticmethod
    async def _rechazar(send):
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(_RESPUESTA)).encode())]})
        await send({"type": "http.response.body", "body": _RESPUESTA})
