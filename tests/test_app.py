"""Testes de fumaça da interface: cada página deve executar sem exceção com os filtros padrão.

Usa o banco gerado em db/ (se não existir, é construído na primeira execução).
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from vacina_sarampo import config
from vacina_sarampo.etl import carga

PAGINAS = ["visao_geral", "cobertura", "casos", "cruzamento", "doses_mensais", "municipio", "dados"]
DIR = Path(__file__).resolve().parent.parent / "app" / "paginas"


@pytest.fixture(scope="module", autouse=True)
def banco_padrao():
    if not config.CAMINHO_DB.exists():
        carga.construir_banco(verbose=False)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_executa_sem_erros(pagina):
    at = AppTest.from_file(str(DIR / f"{pagina}.py"), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("pagina", ["visao_geral", "cobertura", "cruzamento", "municipio"])
def test_pagina_funciona_com_metodo_ponderado(pagina):
    at = AppTest.from_file(str(DIR / f"{pagina}.py"), default_timeout=90)
    at.session_state["metodo_cobertura"] = "ponderada"
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_casos_acumulado_e_filtros():
    at = AppTest.from_file(str(DIR / "casos.py"), default_timeout=90).run()
    at.radio(key="cb3_nivel").set_value("Unidades da Federação").run()
    assert not at.exception
    at.radio(key="cb3_modo").set_value("Acumulado no intervalo").run()
    assert not at.exception
    at.radio(key="cb3_nivel").set_value("Brasil").run()
    assert not at.exception, [e.value for e in at.exception]


def test_doses_mensais_escopos():
    at = AppTest.from_file(str(DIR / "doses_mensais.py"), default_timeout=90).run()
    for rot in ("UFs (soma das 27)", "Localidades específicas"):
        at.radio(key="ca2_esc").set_value(rot).run()
        assert not at.exception, [e.value for e in at.exception]


def test_entrypoint_main_executa():
    at = AppTest.from_file(str(DIR.parent / "main.py"), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]


def test_cobertura_filtros_cb4():
    at = AppTest.from_file(str(DIR / "cobertura.py"), default_timeout=90).run()
    at.select_slider(key="cb4_ano").set_value(2015).run()
    assert not at.exception, [e.value for e in at.exception]
    at.radio(key="cb4_dose").set_value("D2").run()
    at.text_input(key="cb4_busca").set_value("Porto Alegre").run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("1 município" in c.value for c in at.caption)


def test_cruzamento_relacao_municipios():
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    at.radio(key="rel_nivel").set_value("Municípios do RS").run()
    at.selectbox(key="rel_lag").set_value(1).run()
    assert not at.exception, [e.value for e in at.exception]


def test_municipio_sem_dado_no_tabnet():
    at = AppTest.from_file(str(DIR / "municipio.py"), default_timeout=90).run()
    at.selectbox(key="mun_sel").set_value("431795").run()  # Santo Expedito do Sul
    at.select_slider(key="mun_ano").set_value(2015).run()
    assert not at.exception, [e.value for e in at.exception]
