"""Testes dos extratores (arquivos sintéticos) e do banco construído (dados reais).

Os valores de referência vêm das Tabelas 1 e 4 do artigo anteprojeto.
"""
import sqlite3
import textwrap

import pandas as pd
import pytest

from vacina_sarampo import config
from vacina_sarampo.etl import extratores as ex

# ----------------------------------------------------------------------------
# extratores (arquivos mínimos)
# ----------------------------------------------------------------------------


def test_cobertura_tabnet_total_vira_brasil(tmp_path):
    p = tmp_path / "cv_UF_2019.csv"
    p.write_bytes('"Unidade da Federação";"D1";"D2";"Tetra"\n"11 Rondônia";"109,00";"94,61";"94,63"\n"Total";"93,12";"81,55";"1"\n'
                  .encode("latin1"))
    df = ex.ler_cobertura_tabnet(p, "UF")
    assert df.cod_ibge.tolist() == ["11", "00"]
    assert df.cobertura_d1.tolist() == [109.0, 93.12]
    assert (df.ano == 2019).all()


def test_cobertura_tabnet_total_rs(tmp_path):
    p = tmp_path / "cv_RS_2019.csv"
    p.write_bytes('"Município";"D1";"D2";"T"\n"430003 ACEGUA";"150,00";"130,77";"1,0"\n"Total";"91,23";"87,60";"1,0"\n'.encode("latin1"))
    df = ex.ler_cobertura_tabnet(p, "RS")
    assert df.cod_ibge.tolist() == ["430003", "43"]
    assert df.nome.iloc[0] == "ACEGUA"


def test_sinan_exantema_derrete_e_filtra(tmp_path):
    conteudo = textwrap.dedent('''\
        SARAMPO e RUBÉOLA - Casos
        casos notificados por UF de residência e Ano(s) de início do exantema
        Class. Final: SARAMPO
        Período:2015-2026
        "UF de residência";"Em Branco/ign";"2014";"2015";"2019";"Total"
        "11 Rondônia";-;2;-;5;7
        "00 Ignorado/exterior";1;-;3;-;4
        "Total";1;2;3;5;11

         Fonte: Ministério da Saúde
        ''')
    p = tmp_path / "sarampo_inicio_exantema_UF_2015_2026.csv"
    p.write_bytes(conteudo.encode("latin1"))
    log = []
    df = ex.ler_sarampo_exantema(p, "UF", log)
    assert set(df.ano) == {2015, 2019}                     # 2014 e "Em Branco" descartados
    assert df.query("cod_ibge == '11' and ano == 2019").casos.item() == 5
    assert df.query("cod_ibge == '11' and ano == 2015").casos.item() == 0   # '-' vira 0
    assert not df.nome.eq("Total").any()
    assert any("2014" in d for _, d, _ in log) and any("branco" in d.lower() for _, d, _ in log)


@pytest.mark.parametrize("valor,esperado", [("-", 0), ("14,221", 14221), (3.0, 3), (None, 0), (float("nan"), 0), ("7", 7), (" - ", 0)])
def test_para_inteiro(valor, esperado):
    assert ex._para_inteiro(valor) == esperado


def test_populacao_municipio_trunca_codigo(tmp_path):
    p = tmp_path / "pop.csv"
    p.write_text("ano,sigla_uf,id_municipio,populacao\n2019,RS,4314902,1483771\n2019,SP,3550308,12000000\n"
                 "2019,RS,4309209,\n2019,,,5\n", encoding="utf-8")
    log = []
    df = ex.ler_populacao_municipio(p, log=log)
    assert df.cod_ibge.tolist() == ["431490"] and df.populacao.tolist() == [1483771]
    assert log[0][2] == 2  # linhas descartadas (sem população / sem UF)


def test_populacao_uf_descarta_linha_sem_sigla(tmp_path):
    p = tmp_path / "pop_uf.csv"
    p.write_text("ano,sigla_uf,populacao\n2025,,5877\n2025,RS,11233263\n", encoding="utf-8")
    df = ex.ler_populacao_uf(p, [])
    assert df.cod_ibge.tolist() == ["43"]


# ----------------------------------------------------------------------------
# banco construído com os dados reais
# ----------------------------------------------------------------------------
def test_contagens_batem_com_o_artigo(con):
    n = lambda t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: E731
    assert n("LOCALIDADE") == 525                        # 1 país + 27 UFs + 497 municípios do RS
    assert n("VACINACAO_ANUAL") == 6300                  # 525 x 12 anos
    assert n("NOTIFICACAO_SARAMPO") == 6300
    assert n("VACINACAO_MENSAL") == 48208                # 46 meses x 2 doses x 524
    assert n("FONTE_ARQUIVO") == 70                      # os 70 arquivos do artigo


def test_integridade_referencial(con):
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


# Tabela 4 do artigo: (ano) -> (D1, D2, casos, incidência)
TABELA4 = {
    "00": {
        2015: (96.07, 79.94, 200, 0.10), 2016: (95.41, 76.71, 1, 0.00), 2017: (86.24, 72.94, 4, 0.00),
        2018: (92.61, 76.89, 9333, 4.48), 2019: (93.12, 81.55, 21797, 10.37), 2020: (80.88, 64.27, 8006, 3.78),
        2021: (74.94, 53.20, 671, 0.31), 2022: (80.70, 57.64, 48, 0.02), 2023: (89.90, 69.93, 4, 0.00),
        2024: (96.04, 81.16, 8, 0.00), 2025: (93.14, 78.72, 42, 0.02), 2026: (94.97, 80.14, 46, 0.02)},
    "43": {
        2015: (87.81, 69.36, 0, 0.00), 2016: (90.45, 86.47, 0, 0.00), 2017: (83.34, 75.72, 1, 0.01),
        2018: (88.72, 83.11, 46, 0.41), 2019: (91.23, 87.60, 105, 0.92), 2020: (86.08, 78.39, 34, 0.30),
        2021: (79.88, 56.03, 0, 0.00), 2022: (88.48, 62.59, 0, 0.00), 2023: (91.61, 75.32, 0, 0.00),
        2024: (99.67, 87.44, 1, 0.01), 2025: (95.44, 84.62, 1, 0.01), 2026: (92.62, 76.65, 1, 0.01)},
    "431490": {
        2015: (75.32, 75.81, 0, 0.00), 2016: (72.40, 73.27, 0, 0.00), 2017: (71.64, 68.11, 0, 0.00),
        2018: (81.45, 81.40, 39, 2.64), 2019: (81.07, 78.79, 22, 1.48), 2020: (78.39, 67.72, 6, 0.40),
        2021: (73.27, 47.38, 0, 0.00), 2022: (85.01, 54.27, 0, 0.00), 2023: (88.99, 69.20, 0, 0.00),
        2024: (96.96, 80.34, 0, 0.00), 2025: (91.35, 77.47, 1, 0.07), 2026: (91.01, 72.41, 0, 0.00)},
}


@pytest.mark.parametrize("cod", list(TABELA4))
def test_tabela4_do_artigo_reproduzida(con, cod):
    df = pd.read_sql_query("SELECT ano, cobertura_d1, cobertura_d2, casos, incidencia_100k FROM VW_CRUZAMENTO "
                           "WHERE cod_ibge = ? ORDER BY ano", con, params=[cod])
    obtido = {r.ano: (r.cobertura_d1, r.cobertura_d2, r.casos, round(r.incidencia_100k, 2)) for r in df.itertuples()}
    for ano, (d1, d2, casos, inc) in TABELA4[cod].items():
        o = obtido[ano]
        assert o[0] == pytest.approx(d1, abs=0.005), (cod, ano, "D1")
        assert o[1] == pytest.approx(d2, abs=0.005), (cod, ano, "D2")
        assert o[2] == casos, (cod, ano, "casos")
        assert o[3] == pytest.approx(inc, abs=0.005), (cod, ano, "incidência")


@pytest.mark.parametrize("cod,ano,casos,pop,inc", [
    ("431490", 2018, 39, 1479101, 2.64), ("430920", 2019, 35, 281519, 12.43),
    ("430310", 2019, 20, 130293, 15.35), ("431490", 2025, 1, 1388794, 0.07)])
def test_tabela1_do_artigo(con, cod, ano, casos, pop, inc):
    r = con.execute("SELECT casos, populacao_ibge, incidencia_100k FROM VW_CRUZAMENTO WHERE cod_ibge=? AND ano=?",
                    [cod, ano]).fetchone()
    assert r[0] == casos and r[1] == pop and round(r[2], 2) == pytest.approx(inc, abs=0.005)


def test_doses_absolutas_so_a_partir_de_2023(con):
    antes = con.execute("SELECT COUNT(*) FROM VACINACAO_ANUAL WHERE ano < 2023 AND (doses_d1 IS NOT NULL OR doses_d2 IS NOT NULL)").fetchone()[0]
    depois = con.execute("SELECT COUNT(*) FROM VACINACAO_ANUAL WHERE ano >= 2023 AND doses_d1 IS NULL").fetchone()[0]
    assert antes == 0 and depois == 0
    # Tabela 1 do artigo: Porto Alegre 2025 -> 11.713 doses de D1
    assert con.execute("SELECT doses_d1 FROM VW_CRUZAMENTO WHERE cod_ibge='431490' AND ano=2025").fetchone()[0] == 11713


def test_incidencia_consistente_com_casos_e_populacao(con):
    df = pd.read_sql_query("SELECT casos_inicio_exantema c, populacao_ibge p, incidencia_100k i FROM NOTIFICACAO_SARAMPO", con)
    assert (df.p > 0).all()
    esperado = (df.c / df.p * 100000).round(4)
    assert (df.i - esperado).abs().max() < 1e-9


def test_populacao_2026_replica_2025_e_e_sinalizada(con):
    r = con.execute("""SELECT SUM(a.populacao_ibge <> b.populacao_ibge), MIN(b.populacao_estimada), MAX(a.populacao_estimada)
                       FROM NOTIFICACAO_SARAMPO a JOIN NOTIFICACAO_SARAMPO b
                         ON a.id_localidade = b.id_localidade AND a.ano = 2025 AND b.ano = 2026""").fetchone()
    assert r == (0, 1, 0)


def test_anos_parciais_sinalizados(con):
    parcial = dict(con.execute("SELECT ano, MAX(periodo_parcial) FROM VACINACAO_ANUAL GROUP BY ano").fetchall())
    assert parcial[2026] == 1 and all(parcial[a] == 0 for a in range(2015, 2026))
    meses = con.execute("SELECT DISTINCT meses_cobertos FROM VACINACAO_ANUAL WHERE ano = 2026 AND doses_d1 IS NOT NULL").fetchall()
    assert meses == [(8,)]


def test_flags_de_meta_coerentes(con):
    ruins = con.execute("""SELECT COUNT(*) FROM VACINACAO_ANUAL
                           WHERE cobertura_d1 IS NOT NULL AND atingiu_meta_d1 <> (cobertura_d1 >= 95)""").fetchone()[0]
    assert ruins == 0


def test_metodo_ponderado_coincide_ate_2022(con):
    dif = con.execute("""SELECT COUNT(*) FROM VACINACAO_ANUAL WHERE ano <= 2022
                         AND (cobertura_d1 IS NOT cobertura_d1_pond OR cobertura_d2 IS NOT cobertura_d2_pond)""").fetchone()[0]
    assert dif == 0


def test_brasil_casos_inclui_ignorados_e_ufs_somam(con):
    r = con.execute("""SELECT SUM(CASE WHEN l.tipo_localidade='UF' THEN n.casos_inicio_exantema END),
                              SUM(CASE WHEN l.tipo_localidade='PAIS' THEN n.casos_inicio_exantema END)
                       FROM NOTIFICACAO_SARAMPO n JOIN LOCALIDADE l USING (id_localidade) WHERE n.ano = 2019""").fetchone()
    assert r[1] >= r[0] and r[1] == 21797


def test_municipios_do_rs_tem_nome_e_codigo_de_6_digitos(con):
    df = pd.read_sql_query("SELECT cod_ibge, nome_localidade FROM LOCALIDADE WHERE tipo_localidade='MUNICIPIO'", con)
    assert len(df) == 497 and df.cod_ibge.str.fullmatch(r"43\d{4}").all()
    assert "Porto Alegre" in set(df.nome_localidade)
    assert df.nome_localidade.str.strip().ne("").all()


def test_doses_mensais_sem_nulos_e_com_zero(con):
    r = con.execute("SELECT COUNT(*), MIN(doses_aplicadas), SUM(doses_aplicadas = 0) FROM VACINACAO_MENSAL").fetchone()
    assert r[0] == 48208 and r[1] == 0 and r[2] > 0


def test_total_do_rs_nao_foi_duplicado(con):
    # o total do RS aparece nos arquivos de UF e de município: deve entrar uma só vez
    doses = con.execute("SELECT doses_d1 FROM VW_CRUZAMENTO WHERE cod_ibge='43' AND ano=2024").fetchone()[0]
    soma_mun = con.execute("""SELECT SUM(doses_d1) FROM VW_CRUZAMENTO WHERE tipo_localidade='MUNICIPIO' AND ano=2024""").fetchone()[0]
    assert abs(doses - soma_mun) / doses < 0.01


def test_manifesto_tem_hash_e_datas(con):
    df = pd.read_sql_query("SELECT * FROM FONTE_ARQUIVO", con)
    assert df.sha256.str.len().eq(64).all() and df.arquivo.is_unique
    assert set(df.fonte) == {"TABNET/SI-PNI", "SEIDIGI/DEMAS", "SINAN", "IBGE"}
    assert df[df.arquivo.str.startswith("cv_triplice")].data_extracao.eq("2026-10-23").all()


def test_banco_rejeita_dados_invalidos(con, caminho_db):
    c2 = sqlite3.connect(caminho_db)
    c2.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        c2.execute("INSERT INTO VACINACAO_ANUAL (id_localidade, ano, fonte) VALUES (99999, 2020, 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        c2.execute("INSERT INTO VACINACAO_MENSAL (id_localidade, ano, mes, dose) VALUES (1, 2023, 13, 'D1')")
    c2.close()
