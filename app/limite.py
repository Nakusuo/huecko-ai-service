"""Tope al tamaño del cuerpo de las peticiones.

FastAPI lee y parsea el cuerpo antes de resolver las dependencias, también la
del token, así que sin esto cualquiera podía mandar JSON enorme a /v1 y tumbar
la instancia (512 MB en el plan gratuito) sin conocer el token. Lo que el
backend manda de verdad cabe de sobra en unos pocos KB.
"""
import json

MAX_BYTES = 16 * 1024

_RESPUESTA = json.dumps({"detail": "Petición demasiado grande"}).encode()


class _Demasiado(Exception):
    pass


class LimiteDeCuerpo:
    def __init__(self, app, max_bytes: int = MAX_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declarado = dict(scope.get("headers") or []).get(b"content-length")
        if declarado is not None and declarado.isdigit() and int(declarado) > self.max_bytes:
            await self._rechazar(send)
            return

        # Sin Content-Length (envío por trozos) se cuenta según llega.
        leidos = 0

        async def recibir_contando():
            nonlocal leidos
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                leidos += len(mensaje.get("body", b""))
                if leidos > self.max_bytes:
                    raise _Demasiado()
            return mensaje

        try:
            await self.app(scope, recibir_contando, send)
        except _Demasiado:
            await self._rechazar(send)

    @staticmethod
    async def _rechazar(send):
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(_RESPUESTA)).encode())]})
        await send({"type": "http.response.body", "body": _RESPUESTA})
