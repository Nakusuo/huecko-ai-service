import pytest

TOKEN = "token-de-prueba"


@pytest.fixture(autouse=True)
def token_configurado(monkeypatch):
    monkeypatch.setenv("HUECKO_IA_TOKEN", TOKEN)
