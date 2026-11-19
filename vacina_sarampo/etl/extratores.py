"""Extratores (E) e transformações (T) dos arquivos brutos.

Cada função lê UM arquivo e devolve um DataFrame "longo" e padronizado. Nenhuma
função grava no banco: isso fica em ``carga.py``.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from .. import config

MESES = {m: i for i, m in enumerate(
    ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"], start=1)}


class ErroLeitura(ValueError):
    """Arquivo com layout diferente do esperado."""


def _titulo(nome: str) -> str:
    """'SAO LUIZ GONZAGA' -> 'Sao Luiz Gonzaga' (usado só como reserva de nome)."""
    peq = {"DE", "DA", "DO", "DAS", "DOS", "E"}
    return " ".join(p.capitalize() if p not in peq else p.lower() for p in nome.split())


def normaliza_texto(txt: str) -> str:
    """Remove acentos e põe em maiúsculas (comparação de nomes)."""
    txt = unicodedata.normalize("NFKD", str(txt))
    return "".join(c for c in txt if not unicodedata.combining(c)).upper().strip()


def _para_inteiro(v) -> int:
    """Converte células numéricas heterogêneas ('-', '14,221', 3.0, NaN) em int."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).strip().replace(".", "").replace(",", "")
    if s in {"", "-"}:
        return 0
    return int(s)


# ---------------------------------------------------------------------------
# 1) Cobertura vacinal TABNET/SI-PNI (2015-2022) - CSV latin1, ';', vírgula decimal
# ---------------------------------------------------------------------------
def ler_cobertura_tabnet(caminho: Path, nivel: str) -> pd.DataFrame:
    """Lê cv_UF_<ano>.csv (nivel='UF') ou cv_RS_<ano>.csv (nivel='RS').

    Retorna: cod_ibge, nome, ano, cobertura_d1, cobertura_d2. A linha "Total" vira
    Brasil ('00') no arquivo de UF e Rio Grande do Sul ('43') no arquivo do RS.
    """
    ano = int(re.search(r"(\d{4})\.csv$", caminho.name).group(1))
    df = pd.read_csv(caminho, sep=";", encoding="latin1", decimal=",", dtype={0: str})
    if df.shape[1] < 3:
        raise ErroLeitura(f"{caminho.name}: esperado >= 3 colunas, obtido {df.shape[1]}")
    df = df.iloc[:, :3]
    df.columns = ["chave", "cobertura_d1", "cobertura_d2"]
    linhas = []
    for chave, d1, d2 in df.itertuples(index=False):
        chave = str(chave).strip()
        if chave.lower() == "total":
            cod, nome = (config.COD_BRASIL, "Brasil") if nivel == "UF" else (config.COD_RS, None)
        else:
            m = re.match(r"^(\d+)\s+(.*)$", chave)
            if not m:
                raise ErroLeitura(f"{caminho.name}: linha inesperada {chave!r}")
            cod, nome = m.group(1), m.group(2)
        linhas.append((cod, nome, ano, d1, d2))
    return pd.DataFrame(linhas, columns=["cod_ibge", "nome", "ano", "cobertura_d1", "cobertura_d2"])


# ---------------------------------------------------------------------------
# 2) SEIDIGI/DEMAS (2023-2026) - XLSX
# ---------------------------------------------------------------------------
def _valor(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


def ler_cobertura_seidigi(caminho: Path) -> tuple[pd.DataFrame, str | None]:
    """Lê cv_triplice_<d>_dose_<UF|RS>_<ano>.xlsx (3 linhas de cabeçalho mesclado).

    Retorna (df, data_extracao). df: cod_ibge, ano, mes, dose, cobertura_mensal (%),
    doses_pop_alvo, pop_alvo. Cada mês traz 3 colunas (Cobertura Vacinal em proporção,
    Doses Aplicadas e População-alvo); a proporção é convertida para % (x100).
    """
    m = re.match(r"cv_triplice_(\d)_dose_(UF|RS)_(\d{4})\.xlsx$", caminho.name)
    if not m:
        raise ErroLeitura(f"nome inesperado: {caminho.name}")
    dose, nivel, ano = f"D{m.group(1)}", m.group(2), int(m.group(3))
    bruto = pd.read_excel(caminho, header=None, dtype=object)

    lin_cab = next((i for i in range(min(6, len(bruto)))
                    if "Cobertura Vacinal" in bruto.iloc[i].tolist()), None)
    if lin_cab is None:
        raise ErroLeitura(f"{caminho.name}: cabeçalho 'Cobertura Vacinal' não encontrado")
    cab, meses = bruto.iloc[lin_cab].tolist(), bruto.iloc[lin_cab - 1].tolist()
    col_chave = next(i for i, c in enumerate(cab) if isinstance(c, str) and "Cód" in c)
    cols_cob = [i for i, c in enumerate(cab) if c == "Cobertura Vacinal"]
    for i in cols_cob:
        if cab[i + 1] != "Doses Aplicadas" or cab[i + 2] != "População":
            raise ErroLeitura(f"{caminho.name}: trio de colunas inesperado na coluna {i}")

    data_extracao = None
    registros = []
    for _, linha in bruto.iloc[lin_cab + 1:].iterrows():
        v = linha.tolist()
        chave = _valor(v[col_chave])
        # a data de extração fica na coluna logo antes do código (UF) ou na 1ª coluna (RS)
        for pos in (0, col_chave - 1):
            if isinstance(_valor(v[pos]), (datetime, pd.Timestamp)):
                data_extracao = pd.Timestamp(v[pos]).date().isoformat()
        if chave is None:
            # linhas sem código: Brasil (UF) / total do RS, que vem na linha da data de extração (RS)
            if nivel == "UF" and str(_valor(v[0]) or "").strip() == "Brasil":
                cod = config.COD_BRASIL
            elif nivel == "RS" and isinstance(_valor(v[0]), (datetime, pd.Timestamp)):
                cod = config.COD_RS
            else:
                continue  # linha só com a data de extração (repete os valores do Brasil)
        else:
            cod = str(chave).strip()
            if cod.endswith(".0"):
                cod = cod[:-2]
        for i in cols_cob:
            mes_dt = pd.Timestamp(meses[i])
            if mes_dt.year != ano:
                raise ErroLeitura(f"{caminho.name}: mês de outro ano ({mes_dt})")
            cob = _valor(v[i])
            registros.append((cod, ano, mes_dt.month, dose,
                              None if cob is None else round(float(cob) * 100, 4),
                              _para_inteiro(v[i + 1]), _para_inteiro(v[i + 2])))
    df = pd.DataFrame(registros, columns=["cod_ibge", "ano", "mes", "dose", "cobertura_mensal",
                                          "doses_pop_alvo", "pop_alvo"])
    return df, data_extracao


def ler_doses_mensais(caminho: Path) -> pd.DataFrame:
    """Lê triplice_<UF|RS>_<d>_dose_<ano>.xlsx (doses aplicadas por mês, qualquer idade).

    Retorna: cod_ibge (UF: 2 dígitos | município: 6), nome, ano, mes, dose, doses_aplicadas.
    Traço '-' vira 0; a linha UF='-' (UF ignorada) é descartada e contabilizada à parte.
    """
    m = re.match(r"triplice_(UF|RS)_(\d)_dose_(\d{4})\.xlsx$", caminho.name)
    if not m:
        raise ErroLeitura(f"nome inesperado: {caminho.name}")
    nivel, dose, ano = m.group(1), f"D{m.group(2)}", int(m.group(3))
    bruto = pd.read_excel(caminho, header=None, dtype=object)
    cab = [str(c).strip().lower() if c is not None else "" for c in bruto.iloc[0].tolist()]
    col_meses = {i: MESES[c] for i, c in enumerate(cab) if c in MESES}
    if not col_meses:
        raise ErroLeitura(f"{caminho.name}: colunas de mês não encontradas")
    regs = []
    for _, linha in bruto.iloc[1:].iterrows():
        v = linha.tolist()
        if nivel == "UF":
            sigla = str(_valor(v[0]) or "").strip()
            if sigla == "-" or not sigla:
                regs.append(("IGNORADA", None, ano, 0, dose, sum(_para_inteiro(v[i]) for i in col_meses)))
                continue
            cod, nome = config.SIGLA_PARA_COD[sigla], None
        else:
            txt = _valor(v[1])
            if txt is None:
                continue
            m2 = re.match(r"^(\d{6})\s*-\s*(.+)$", str(txt).strip())
            if not m2:
                raise ErroLeitura(f"{caminho.name}: município inesperado {txt!r}")
            cod, nome = m2.group(1), m2.group(2).strip()
        for i, mes in col_meses.items():
            regs.append((cod, nome, ano, mes, dose, _para_inteiro(v[i])))
    return pd.DataFrame(regs, columns=["cod_ibge", "nome", "ano", "mes", "dose", "doses_aplicadas"])


# ---------------------------------------------------------------------------
# 3) SINAN/TABNET - casos de sarampo
# ---------------------------------------------------------------------------
def _linhas_tabnet(caminho: Path) -> list[list[str]]:
    """Devolve (cabeçalho + linhas de dados) do bloco CSV de um export TABNET."""
    texto = caminho.read_text(encoding="latin1")
    linhas = texto.splitlines()
    ini = next((i for i, l in enumerate(linhas) if l.startswith('"') and "residência" in l.lower()), None)
    if ini is None:
        raise ErroLeitura(f"{caminho.name}: cabeçalho TABNET não encontrado")
    bloco = []
    for l in linhas[ini:]:
        if not l.startswith('"'):
            break
        bloco.append(l)
    return list(csv.reader(io.StringIO("\n".join(bloco)), delimiter=";"))


def ler_sarampo_exantema(caminho: Path, nivel: str, log: list | None = None) -> pd.DataFrame:
    """Lê a matriz anos-nas-colunas do SINAN (ano de início do exantema) e a "derrete".

    Retorna: cod_ibge, nome, ano, casos (apenas anos 2015-2026). Colunas pré-2015 e
    "Em Branco/ign", e a linha "Total", são descartadas (e registradas em ``log``).
    """
    linhas = _linhas_tabnet(caminho)
    cab, dados = linhas[0], linhas[1:]
    anos_cols = {i: int(c) for i, c in enumerate(cab) if c.isdigit()}
    regs = []
    for r in dados:
        chave = r[0].strip()
        if chave.lower() == "total":
            continue
        m = re.match(r"^(\d+)\s+(.*)$", chave)
        if not m:
            raise ErroLeitura(f"{caminho.name}: linha inesperada {chave!r}")
        cod, nome = m.group(1), m.group(2)
        for i, ano in anos_cols.items():
            valor = _para_inteiro(r[i])
            if config.ANO_INICIAL <= ano <= config.ANO_FINAL:
                regs.append((cod, nome, ano, valor))
            elif log is not None and valor:
                log.append(("SINAN", f"{caminho.name}: casos com exantema em {ano} descartados (fora de 2015-2026)", valor))
        if log is not None and "Em Branco/ign" in cab:
            j = cab.index("Em Branco/ign")
            if _para_inteiro(r[j]):
                log.append(("SINAN", f"{caminho.name}: {nome} com ano de exantema em branco/ignorado", _para_inteiro(r[j])))
    return pd.DataFrame(regs, columns=["cod_ibge", "nome", "ano", "casos"])


def ler_sarampo_ano_notificacao(caminho: Path) -> pd.DataFrame:
    """Lê not_sarampo_<UF|RS>_<ano>.csv (casos por ANO DE NOTIFICAÇÃO)."""
    ano = int(re.search(r"(\d{4})\.csv$", caminho.name).group(1))
    linhas = _linhas_tabnet(caminho)
    regs = []
    for r in linhas[1:]:
        chave = r[0].strip()
        if chave.lower() == "total":
            continue
        m = re.match(r"^(\d+)\s+(.*)$", chave)
        regs.append((m.group(1), m.group(2), ano, _para_inteiro(r[1])))
    return pd.DataFrame(regs, columns=["cod_ibge", "nome", "ano_notificacao", "casos"])


# ---------------------------------------------------------------------------
# 4) População IBGE (Base dos Dados)
# ---------------------------------------------------------------------------
def ler_populacao_uf(caminho: Path, log: list | None = None) -> pd.DataFrame:
    df = pd.read_csv(caminho)
    sem_uf = df["sigla_uf"].isna()
    if log is not None and sem_uf.any():
        log.append(("IBGE", "br_ibge_populacao_uf.csv: linhas sem sigla_uf descartadas", int(sem_uf.sum())))
    df = df[~sem_uf].copy()
    df["cod_ibge"] = df["sigla_uf"].map(config.SIGLA_PARA_COD)
    if df["cod_ibge"].isna().any():
        raise ErroLeitura("sigla_uf desconhecida em br_ibge_populacao_uf.csv")
    return df[["cod_ibge", "ano", "populacao"]].astype({"populacao": int})


def ler_populacao_municipio(caminho: Path, uf: str = config.UF_MUNICIPAL, log: list | None = None) -> pd.DataFrame:
    """População municipal de uma UF com código truncado de 7 para 6 dígitos."""
    df = pd.read_csv(caminho)
    nulos = df["populacao"].isna() | df["sigla_uf"].isna() | df["id_municipio"].isna()
    if log is not None:
        log.append(("IBGE", "br_ibge_populacao_municipio.csv: linhas sem população/UF/município descartadas", int(nulos.sum())))
    df = df[~nulos & (df["sigla_uf"] == uf)].copy()
    df["cod_ibge"] = df["id_municipio"].astype("int64").astype(str).str.slice(0, 6)
    return df[["cod_ibge", "ano", "populacao"]].astype({"populacao": int})
