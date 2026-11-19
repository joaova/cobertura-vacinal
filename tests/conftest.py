"""Fixtures compartilhadas: constrói o banco uma única vez (a partir dos dados reais em dados/)."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
for p in (RAIZ, RAIZ / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from vacina_sarampo import consultas  # noqa: E402
from vacina_sarampo.etl import carga  # noqa: E402


@pytest.fixture(scope="session")
def caminho_db(tmp_path_factory):
    destino = tmp_path_factory.mktemp("db") / "teste.db"
    carga.construir_banco(destino, verbose=False)
    return destino


@pytest.fixture(scope="session")
def con(caminho_db):
    c = consultas.conectar(caminho_db)
    yield c
    c.close()
