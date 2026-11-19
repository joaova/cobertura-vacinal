"""Testes das consultas SQL (CB1-CB4, CA1-CA2) e da estatística."""
import pandas as pd
import pytest

from vacina_sarampo import config, consultas, estatistica


def test_cb1_serie_tem_12_anos_por_localidade(con):
    df = consultas.cb1_serie_cobertura(con, ["431490", "43", "00"])
    assert df.groupby("cod_ibge").size().eq(12).all()
    assert set(df.nome_localidade) == {"Porto Alegre", "Rio Grande do Sul", "Brasil"}


def test_cb1_filtra_periodo(con):
    df = consultas.cb1_serie_cobertura(con, ["00"], ano_ini=2018, ano_fim=2020)
    assert df.ano.tolist() == [2018, 2019, 2020]


def test_cb2_27_ufs_e_diferenca(con):
    df = consultas.cb2_d1_vs_d2_por_uf(con, ano_ini=2015, ano_fim=2025)
    assert len(df) == 27
    assert ((df.media_d1 - df.media_d2).round(2) - df.diferenca).abs().max() < 0.02
    assert set(df.regiao) == {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}


def test_cb3_ordenado_por_incidencia_e_so_com_casos(con):
    df = consultas.cb3_ranking_casos(con, "MUNICIPIO", 2019, 2019, min_casos=1)
    assert (df.casos_inicio_exantema > 0).all() and df.incidencia_100k.is_monotonic_decreasing
    # Tabela 1/Seção 5.3: Carlos Gomes (1 caso, ~72/100 mil) lidera a incidência de 2019
    assert df.iloc[0].nome_localidade == "Carlos Gomes" and round(df.iloc[0].incidencia_100k, 1) == 72.6


def test_cb3_rs_total_de_casos_municipais(con):
    # artigo: 189 casos do RS (2015-2026) por início do exantema; municípios devem somar o mesmo
    mun = consultas.cb3_ranking_casos(con, "MUNICIPIO", 2015, 2026, 1).casos_inicio_exantema.sum()
    uf = consultas.cb3_ranking_casos(con, "UF", 2015, 2026, 1)
    rs = uf[uf.cod_ibge == "43"].casos_inicio_exantema.sum()
    assert mun == rs == 189


def test_cb4_totais_497_municipios(con):
    for dose in ("D1", "D2"):
        df = consultas.cb4_municipios_na_meta(con, dose)
        assert df.municipios_total.eq(497).all()
        assert (df.municipios_na_meta + df.municipios_abaixo_meta + df.municipios_sem_dado).eq(497).all()
        assert (df.municipios_na_meta + df.municipios_abaixo_meta == df.municipios_com_dado).all()
        # 4 CSVs do TABNET (2015, 2016, 2021, 2022) omitem 1 município cada
        sem_dado = dict(zip(df.ano, df.municipios_sem_dado))
        assert {a for a, n in sem_dado.items() if n > 0} == {2015, 2016, 2021, 2022}
        assert df.ano.tolist() == config.ANOS


def test_cb4_tabela_de_um_ano(con):
    df = consultas.cb4_tabela_municipios(con, 2024)
    assert len(df) == 497 and df.ano.eq(2024).all()


def test_ca1_cruzamento_traz_casos_e_cobertura(con):
    df = consultas.ca1_cruzamento(con, ["431490"], ano_ini=2018, ano_fim=2019)
    assert df.casos.tolist() == [39, 22]
    assert df.cobertura_d1.round(2).tolist() == [81.45, 81.07]


def test_ca2_soma_dos_meses_confere(con):
    df = consultas.ca2_doses_mensais(con, "MUNICIPIO_RS", anos=[2024], doses=["D1"])
    assert df.mes.tolist() == list(range(1, 13)) and df.n_localidades.eq(497).all()
    esperado = con.execute("""SELECT SUM(doses_aplicadas) FROM VACINACAO_MENSAL m JOIN LOCALIDADE l USING(id_localidade)
                              WHERE l.tipo_localidade='MUNICIPIO' AND m.ano=2024 AND m.dose='D1'""").fetchone()[0]
    assert df.total_doses.sum() == esperado


def test_ca2_separa_por_ano(con):
    df = consultas.ca2_doses_mensais(con, "UF")
    assert set(df.ano) == {2023, 2024, 2025, 2026}
    assert df[df.ano == 2026].mes.max() == 10 and df[df.ano == 2025].mes.max() == 12


def test_ca2_localidades_exige_codigos(con):
    with pytest.raises(ValueError):
        consultas.ca2_doses_mensais(con, "LOCALIDADES")
    df = consultas.ca2_doses_mensais(con, "LOCALIDADES", cods=["431490"], anos=[2025])
    assert df.n_localidades.eq(1).all()


def test_relacao_defasagem_usa_ano_anterior(con):
    df = consultas.relacao_cobertura_incidencia(con, "UF", "D1", lag=1, ano_ini=2018, ano_fim=2019)
    assert (df.ano_cobertura == df.ano_incidencia - 1).all() and len(df) == 54


def test_metodos_de_cobertura_diferem_apenas_apos_2022(con):
    a = consultas.cb1_serie_cobertura(con, ["43"], "media_mensal")
    b = consultas.cb1_serie_cobertura(con, ["43"], "ponderada")
    ate22 = a.ano <= 2022
    assert (a[ate22].cobertura_d1.values == b[ate22].cobertura_d1.values).all()
    assert (a[~ate22].cobertura_d1.values != b[~ate22].cobertura_d1.values).any()


def test_metodo_invalido_e_rejeitado(con):
    with pytest.raises(ValueError):
        consultas.cb1_serie_cobertura(con, ["00"], "inexistente")


def test_sql_injection_em_codigos_nao_executa(con):
    df = consultas.cb1_serie_cobertura(con, ["00' OR '1'='1"])
    assert df.empty
    assert con.execute("SELECT COUNT(*) FROM LOCALIDADE").fetchone()[0] == 525


def test_conexao_somente_leitura(con):
    import sqlite3
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM LOCALIDADE")


def test_comparacao_criterios(con):
    df = consultas.comparacao_criterios_casos(con, "00")
    assert df.ano.tolist() == config.ANOS
    assert df.loc[df.ano == 2019, "casos_exantema"].item() == 21797


# --------------------------------------------------------------------------- estatística
def test_spearman_monotono_perfeito():
    r = estatistica.spearman(pd.Series([1, 2, 3, 4, 5, 6]), pd.Series([10, 20, 30, 40, 50, 60]))
    assert r.rho == pytest.approx(1.0) and r.n == 6


def test_spearman_negativa_e_forca():
    r = estatistica.spearman(pd.Series(range(20)), pd.Series(range(20, 0, -1)))
    assert r.rho == pytest.approx(-1.0) and estatistica.descreve_forca(r.rho) == "forte negativa"


def test_spearman_dados_insuficientes():
    assert estatistica.spearman(pd.Series([1, 1, 1]), pd.Series([1, 2, 3])).rho is None
    assert estatistica.spearman(pd.Series([1.0]), pd.Series([2.0])).rho is None


def test_spearman_ignora_nulos():
    r = estatistica.spearman(pd.Series([1, 2, None, 4, 5]), pd.Series([1, 2, 3, None, 5]))
    assert r.n == 3
