"""Consultas SQL (CB1-CB4, CA1-CA2 do artigo e extensões) sobre o banco SQLite.

Cada consulta é um modelo SQL (``SQL[...]``) mais uma função que o executa e devolve um
DataFrame. A interface exibe o SQL ao usuário (transparência para a disciplina de BD).

Método de cobertura 2023-2026 (parâmetro ``metodo``):
  * ``"media_mensal"``  – média simples das coberturas mensais do painel SEIDIGI (padrão do
    artigo; reproduz a Tabela 4);
  * ``"ponderada"``     – soma(doses)/soma(população-alvo), comparável à taxa anual do TABNET.
Em 2015-2022 os dois métodos coincidem.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from . import config

METODOS = {
    "media_mensal": ("cobertura_d1", "cobertura_d2"),
    "ponderada": ("cobertura_d1_pond", "cobertura_d2_pond"),
}
ROTULO_METODO = {
    "media_mensal": "Média das coberturas mensais (padrão do artigo / painel)",
    "ponderada": "Soma das doses ÷ soma da população-alvo (ponderada)",
}


def conectar(caminho: Path | str = config.CAMINHO_DB) -> sqlite3.Connection:
    """Abre o banco em modo somente leitura."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(
            f"Banco não encontrado em {caminho}. Gere-o com:  python -m vacina_sarampo.etl")
    con = sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _cols(metodo: str) -> dict[str, str]:
    if metodo not in METODOS:
        raise ValueError(f"método desconhecido: {metodo}")
    d1, d2 = METODOS[metodo]
    return {"d1": d1, "d2": d2}


def _in(n: int) -> str:
    return ",".join("?" * n)


# ----------------------------------------------------------------------------
# Modelos SQL
# ----------------------------------------------------------------------------
SQL = {
    "CB1": """-- CB1: série histórica da cobertura (D1 e D2) por localidade
SELECT l.cod_ibge, l.nome_localidade, v.ano,
       v.{d1} AS cobertura_d1, v.{d2} AS cobertura_d2, v.periodo_parcial
FROM VACINACAO_ANUAL v
JOIN LOCALIDADE l ON l.id_localidade = v.id_localidade
WHERE l.cod_ibge IN ({lista}) AND v.ano BETWEEN :ano_ini AND :ano_fim
ORDER BY l.nome_localidade, v.ano;""",

    "CB2": """-- CB2: D1 x D2 por UF (média no período) e diferença D1 - D2
SELECT l.sigla_uf, l.nome_localidade, l.regiao,
       ROUND(AVG(v.{d1}), 2) AS media_d1,
       ROUND(AVG(v.{d2}), 2) AS media_d2,
       ROUND(AVG(v.{d1}) - AVG(v.{d2}), 2) AS diferenca
FROM VACINACAO_ANUAL v
JOIN LOCALIDADE l ON l.id_localidade = v.id_localidade
WHERE l.tipo_localidade = 'UF' AND v.ano BETWEEN :ano_ini AND :ano_fim
GROUP BY l.id_localidade
ORDER BY diferenca DESC;""",

    "CB3": """-- CB3: casos (por início do exantema) e incidência por 100 mil hab., em ordem decrescente
SELECT l.cod_ibge, l.nome_localidade, l.tipo_localidade, l.sigla_uf, n.ano,
       n.casos_inicio_exantema, n.populacao_ibge, n.incidencia_100k,
       n.populacao_estimada, n.periodo_parcial
FROM NOTIFICACAO_SARAMPO n
JOIN LOCALIDADE l ON l.id_localidade = n.id_localidade
WHERE l.tipo_localidade = :tipo
  AND n.ano BETWEEN :ano_ini AND :ano_fim
  AND n.casos_inicio_exantema >= :min_casos
ORDER BY n.incidencia_100k DESC, n.casos_inicio_exantema DESC;""",

    "CB4": """-- CB4: municípios do RS dentro e abaixo da meta de 95% por ano (inclui sem dado na fonte)
SELECT v.ano,
       SUM(CASE WHEN v.{dose} >= :meta THEN 1 ELSE 0 END) AS municipios_na_meta,
       SUM(CASE WHEN v.{dose} <  :meta THEN 1 ELSE 0 END) AS municipios_abaixo_meta,
       SUM(CASE WHEN v.{dose} IS NULL  THEN 1 ELSE 0 END) AS municipios_sem_dado,
       COUNT(v.{dose}) AS municipios_com_dado,
       COUNT(*) AS municipios_total,
       ROUND(100.0 * SUM(CASE WHEN v.{dose} >= :meta THEN 1 ELSE 0 END) / NULLIF(COUNT(v.{dose}), 0), 1) AS pct_na_meta
FROM VACINACAO_ANUAL v
JOIN LOCALIDADE l ON l.id_localidade = v.id_localidade
WHERE l.tipo_localidade = 'MUNICIPIO' AND l.sigla_uf = 'RS'
GROUP BY v.ano
ORDER BY v.ano;""",

    "CB4_TAB": """-- CB4 (tabela para as UBS): cobertura de cada município do RS em um ano
SELECT l.cod_ibge, l.nome_localidade, v.ano,
       v.{d1} AS cobertura_d1, v.{d2} AS cobertura_d2,
       v.doses_d1, v.doses_d2, v.periodo_parcial
FROM VACINACAO_ANUAL v
JOIN LOCALIDADE l ON l.id_localidade = v.id_localidade
WHERE l.tipo_localidade = 'MUNICIPIO' AND l.sigla_uf = 'RS' AND v.ano = :ano
ORDER BY l.nome_localidade;""",

    "CA1": """-- CA1: cruzamento cobertura x casos x incidência (JOIN das três tabelas)
SELECT l.cod_ibge, l.nome_localidade, v.ano,
       v.{d1} AS cobertura_d1, v.{d2} AS cobertura_d2, v.doses_d1, v.doses_d2,
       n.casos_inicio_exantema AS casos, n.populacao_ibge, n.incidencia_100k,
       n.populacao_estimada, v.periodo_parcial
FROM VACINACAO_ANUAL v
JOIN LOCALIDADE l ON l.id_localidade = v.id_localidade
LEFT JOIN NOTIFICACAO_SARAMPO n ON n.id_localidade = l.id_localidade AND n.ano = v.ano
WHERE l.cod_ibge IN ({lista}) AND v.ano BETWEEN :ano_ini AND :ano_fim
ORDER BY l.nome_localidade, v.ano;""",

    "CA2": """-- CA2: doses aplicadas por mês (soma e média por localidade), separadas por ano e dose
SELECT m.ano, m.mes, m.dose,
       SUM(m.doses_aplicadas) AS total_doses,
       ROUND(AVG(m.doses_aplicadas), 1) AS media_por_localidade,
       COUNT(*) AS n_localidades
FROM VACINACAO_MENSAL m
JOIN LOCALIDADE l ON l.id_localidade = m.id_localidade
WHERE {escopo} AND m.ano IN ({anos}) AND m.dose IN ({doses})
GROUP BY m.ano, m.mes, m.dose
ORDER BY m.ano, m.mes, m.dose;""",

    "CORR": """-- Relação cobertura (ano t - defasagem) x incidência (ano t) por localidade
SELECT l.cod_ibge, l.nome_localidade, n.ano AS ano_incidencia,
       v.ano AS ano_cobertura, v.{dose} AS cobertura, n.casos_inicio_exantema AS casos,
       n.populacao_ibge, n.incidencia_100k
FROM NOTIFICACAO_SARAMPO n
JOIN LOCALIDADE l ON l.id_localidade = n.id_localidade
JOIN VACINACAO_ANUAL v ON v.id_localidade = n.id_localidade AND v.ano = n.ano - :lag
WHERE l.tipo_localidade = :tipo AND n.ano BETWEEN :ano_ini AND :ano_fim
  AND v.{dose} IS NOT NULL;""",
}


def sql_formatado(nome: str, metodo: str = "media_mensal", **extra: str) -> str:
    """Devolve o SQL com os nomes de coluna do método escolhido (para exibição)."""
    c = _cols(metodo)
    dose = c[extra["dose"].lower()] if "dose" in extra else c["d1"]
    return SQL[nome].format(d1=c["d1"], d2=c["d2"], dose=dose,
                            lista=extra.get("lista", "?, ?, ?"), escopo=extra.get("escopo", "..."),
                            anos=extra.get("anos", "..."), doses=extra.get("doses", "'D1', 'D2'"))


def _df(con: sqlite3.Connection, sql: str, params) -> pd.DataFrame:
    return pd.read_sql_query(sql, con, params=params)


# ----------------------------------------------------------------------------
# Catálogos
# ----------------------------------------------------------------------------
def localidades(con: sqlite3.Connection) -> pd.DataFrame:
    return _df(con, "SELECT cod_ibge, nome_localidade, tipo_localidade, sigla_uf, regiao FROM LOCALIDADE "
                    "ORDER BY CASE tipo_localidade WHEN 'PAIS' THEN 0 WHEN 'UF' THEN 1 ELSE 2 END, nome_localidade", ())


# ----------------------------------------------------------------------------
# Consultas básicas
# ----------------------------------------------------------------------------
def cb1_serie_cobertura(con, cods: list[str], metodo="media_mensal", ano_ini=config.ANO_INICIAL, ano_fim=config.ANO_FINAL):
    c = _cols(metodo)
    sql = SQL["CB1"].format(d1=c["d1"], d2=c["d2"], lista=_in(len(cods)))
    return _df(con, sql.replace(":ano_ini", "?").replace(":ano_fim", "?"), [*cods, ano_ini, ano_fim])


def cb2_d1_vs_d2_por_uf(con, metodo="media_mensal", ano_ini=config.ANO_INICIAL, ano_fim=config.ANO_FINAL):
    c = _cols(metodo)
    return _df(con, SQL["CB2"].format(d1=c["d1"], d2=c["d2"]), {"ano_ini": ano_ini, "ano_fim": ano_fim})


def cb3_ranking_casos(con, tipo="MUNICIPIO", ano_ini=config.ANO_INICIAL, ano_fim=config.ANO_FINAL, min_casos=1):
    """tipo: 'MUNICIPIO' (RS) | 'UF' | 'PAIS'. Linhas por localidade e ano."""
    return _df(con, SQL["CB3"], {"tipo": tipo, "ano_ini": ano_ini, "ano_fim": ano_fim, "min_casos": min_casos})


def cb4_municipios_na_meta(con, dose="D1", metodo="media_mensal", meta=config.META_COBERTURA):
    c = _cols(metodo)
    return _df(con, SQL["CB4"].format(dose=c[dose.lower()]), {"meta": meta})


def cb4_tabela_municipios(con, ano: int, metodo="media_mensal"):
    c = _cols(metodo)
    return _df(con, SQL["CB4_TAB"].format(d1=c["d1"], d2=c["d2"]), {"ano": ano})


# ----------------------------------------------------------------------------
# Consultas avançadas
# ----------------------------------------------------------------------------
def ca1_cruzamento(con, cods: list[str], metodo="media_mensal", ano_ini=config.ANO_INICIAL, ano_fim=config.ANO_FINAL):
    c = _cols(metodo)
    sql = SQL["CA1"].format(d1=c["d1"], d2=c["d2"], lista=_in(len(cods)))
    return _df(con, sql.replace(":ano_ini", "?").replace(":ano_fim", "?"), [*cods, ano_ini, ano_fim])


def ca2_doses_mensais(con, escopo: str = "MUNICIPIO_RS", cods: list[str] | None = None,
                      anos: list[int] | None = None, doses: list[str] | None = None):
    """escopo: 'MUNICIPIO_RS' (497 municípios), 'UF' (27 UFs) ou 'LOCALIDADES' (usa ``cods``)."""
    anos = anos or [2023, 2024, 2025, 2026]
    doses = doses or ["D1", "D2"]
    params: list = []
    if escopo == "MUNICIPIO_RS":
        cond = "l.tipo_localidade = 'MUNICIPIO' AND l.sigla_uf = 'RS'"
    elif escopo == "UF":
        cond = "l.tipo_localidade = 'UF'"
    elif escopo == "LOCALIDADES":
        if not cods:
            raise ValueError("informe ``cods``")
        cond = f"l.cod_ibge IN ({_in(len(cods))})"
        params += list(cods)
    else:
        raise ValueError(escopo)
    sql = SQL["CA2"].format(escopo=cond, anos=_in(len(anos)), doses=_in(len(doses)), d1="", d2="", dose="")
    return _df(con, sql, [*params, *anos, *doses])


def relacao_cobertura_incidencia(con, tipo="MUNICIPIO", dose="D1", lag=0, metodo="media_mensal",
                                 ano_ini=config.ANO_INICIAL, ano_fim=config.ANO_FINAL):
    """Pares (cobertura em t-lag, incidência em t) por localidade/ano."""
    c = _cols(metodo)
    sql = SQL["CORR"].format(dose=c[dose.lower()])
    return _df(con, sql, {"tipo": tipo, "lag": lag, "ano_ini": ano_ini, "ano_fim": ano_fim})


# ----------------------------------------------------------------------------
# Metadados / qualidade / visão geral
# ----------------------------------------------------------------------------
def manifesto_fontes(con) -> pd.DataFrame:
    return _df(con, "SELECT fonte, arquivo, conteudo, linhas_lidas, data_extracao, modificado_em, sha256 "
                    "FROM FONTE_ARQUIVO ORDER BY fonte, arquivo", ())


def resumo_fontes(con) -> pd.DataFrame:
    return _df(con, "SELECT fonte, COUNT(*) AS arquivos, SUM(linhas_lidas) AS linhas_lidas, "
                    "MAX(data_extracao) AS data_extracao FROM FONTE_ARQUIVO GROUP BY fonte ORDER BY fonte", ())


def log_qualidade(con) -> pd.DataFrame:
    return _df(con, "SELECT etapa, descricao, valor FROM LOG_QUALIDADE ORDER BY id_log", ())


def contagens_tabelas(con) -> pd.DataFrame:
    linhas = []
    for t in ("LOCALIDADE", "VACINACAO_ANUAL", "VACINACAO_MENSAL", "NOTIFICACAO_SARAMPO",
              "NOTIFICACAO_ANO_NOTIF", "FONTE_ARQUIVO", "LOG_QUALIDADE"):
        linhas.append((t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]))
    return pd.DataFrame(linhas, columns=["tabela", "registros"])


def comparacao_criterios_casos(con, cod: str = config.COD_BRASIL) -> pd.DataFrame:
    """Casos por ano de início do exantema x por ano de notificação (cortes preliminares)."""
    return _df(con, """
        SELECT n.ano, n.casos_inicio_exantema AS casos_exantema,
               a.casos_notificados AS casos_ano_notificacao
        FROM NOTIFICACAO_SARAMPO n
        JOIN LOCALIDADE l ON l.id_localidade = n.id_localidade
        LEFT JOIN NOTIFICACAO_ANO_NOTIF a ON a.id_localidade = n.id_localidade AND a.ano_notificacao = n.ano
        WHERE l.cod_ibge = ? ORDER BY n.ano""", [cod])
