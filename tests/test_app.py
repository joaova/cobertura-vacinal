"""Testes de fumaça da interface: cada página deve executar sem exceção com os filtros padrão.

Usa o banco gerado em db/ (se não existir, é construído na primeira execução).
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from vacina_sarampo import config
from vacina_sarampo.etl import carga

PAGINAS = ["visao_geral", "cobertura", "casos", "cruzamento", "municipio", "dados"]
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


def test_doses_mensais_permanecem_na_ficha():
    at = AppTest.from_file(str(DIR / "municipio.py"), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Doses aplicadas por mês" in s.value for s in at.subheader)
    assert len(at.get("plotly_chart")) == 2


def test_entrypoint_main_executa():
    at = AppTest.from_file(str(DIR.parent / "main.py"), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]


def test_cobertura_filtros_cb4():
    at = AppTest.from_file(str(DIR / "cobertura.py"), default_timeout=90).run()
    at.selectbox(key="cb4_ano").set_value(2015).run()
    assert not at.exception, [e.value for e in at.exception]
    at.radio(key="cb4_dose").set_value("D2").run()
    at.text_input(key="cb4_busca").set_value("Porto Alegre").run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(m.label == "Municípios no filtro" and m.value == "1" for m in at.metric)


def test_cruzamento_relacao_municipios():
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    at.radio(key="rel_nivel").set_value("RS por município").run()
    at.selectbox(key="rel_lag").set_value(1).run()
    assert not at.exception, [e.value for e in at.exception]


def test_cruzamento_grupos_do_ano_selecionado():
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    assert at.selectbox(key="rel_ano").value == 2025
    at.selectbox(key="rel_ano").set_value(2019).run()
    assert not at.exception, [e.value for e in at.exception]
    tabela = next(d.value for d in at.dataframe if "Situação da cobertura" in d.value.columns)
    assert tabela.Localidades.sum() == 27
    # Soma dos casos das 27 UFs em 2019; não inclui residência ignorada/exterior.
    assert tabela.Casos.sum() == 21_781
    assert tabela["Situação da cobertura"].tolist() == ["Abaixo de 95%", "95% ou mais"]
    assert any(e.label == "Detalhes estatísticos" and not e.proto.expanded for e in at.expander)


def test_cruzamento_ano_sem_casos_e_filtro_sem_localidades():
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    at.radio(key="rel_nivel").set_value("RS por município").run()
    at.selectbox(key="rel_ano").set_value(2023).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Nenhum caso de sarampo registrado" in i.value for i in at.info)
    tabela = next(d.value for d in at.dataframe if "Situação da cobertura" in d.value.columns)
    assert tabela.Casos.sum() == 0
    assert tabela["Incidência /100 mil"].dropna().eq(0).all()
    at.number_input(key="rel_pmin").set_value(2_000_000).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Nenhuma localidade com dados válidos" in i.value for i in at.info)


def test_cruzamento_defasagem_respeita_primeiro_ano_disponivel():
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    at.selectbox(key="rel_lag").set_value(2).run()
    at.selectbox(key="rel_ano").set_value(config.ANO_INICIAL).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key="rel_lag").value == 0


def test_cruzamento_lista_ufs_com_casos_e_situacao_por_dose():
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    tabela = next(d.value for d in at.dataframe if "Estado / DF" in d.value.columns)
    assert tabela.Casos.sum() == 42
    tocantins = tabela.set_index("UF").loc["TO"]
    assert tocantins.Casos == 26
    assert tocantins["Situação da cobertura selecionada"] == "95% ou mais"
    at.radio(key="rel_dose").set_value("D2").run()
    assert not at.exception, [e.value for e in at.exception]
    tabela = next(d.value for d in at.dataframe if "Estado / DF" in d.value.columns)
    tocantins = tabela.set_index("UF").loc["TO"]
    assert tocantins.Casos == 26
    assert tocantins["Situação da cobertura selecionada"] == "Abaixo de 95%"


def test_cruzamento_lista_municipios_com_casos_fora_do_filtro():
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    at.radio(key="rel_nivel").set_value("RS por município").run()
    at.selectbox(key="rel_ano").set_value(2019).run()
    assert not at.exception, [e.value for e in at.exception]
    tabela = next(d.value for d in at.dataframe if "Município" in d.value.columns)
    assert tabela.Casos.sum() == 105
    assert len(tabela) == 14
    carlos_gomes = tabela.set_index("Município").loc["Carlos Gomes"]
    assert carlos_gomes.Casos == 1
    assert carlos_gomes["Na comparação dos grupos"] == "Não"
    at.number_input(key="rel_pmin").set_value(0).run()
    tabela = next(d.value for d in at.dataframe if "Município" in d.value.columns)
    assert tabela.set_index("Município").loc["Carlos Gomes", "Na comparação dos grupos"] == "Sim"


def test_cruzamento_contexto_e_fontes_para_todos_os_anos():
    from vacina_sarampo.contexto_epidemiologico import CONTEXTOS

    assert set(CONTEXTOS) == set(config.ANOS)
    at = AppTest.from_file(str(DIR / "cruzamento.py"), default_timeout=90).run()
    for ano in config.ANOS:
        at.selectbox(key="rel_ano").set_value(ano).run()
        assert not at.exception, (ano, [e.value for e in at.exception])
        contexto = CONTEXTOS[ano]
        assert any(contexto.resumo in m.value for m in at.markdown)
        for fonte in contexto.fontes:
            assert fonte.url.startswith("https://www.gov.br/saude/")
            assert any(fonte.url in m.value for m in at.markdown)
        assert any(f"Contexto epidemiológico de {ano}" in s.value for s in at.subheader)


def test_municipio_sem_dado_no_tabnet():
    at = AppTest.from_file(str(DIR / "municipio.py"), default_timeout=90).run()
    at.selectbox(key="mun_sel").set_value("431795").run()  # Santo Expedito do Sul
    at.selectbox(key="mun_ano").set_value(2015).run()
    assert not at.exception, [e.value for e in at.exception]
