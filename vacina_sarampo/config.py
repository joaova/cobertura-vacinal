"""Configurações centrais do projeto (caminhos, constantes e tabelas de apoio)."""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ / "dados"
DIR_IMUNIZACAO = DIR_DADOS / "imunizacao"
DIR_NOTIFICACAO = DIR_DADOS / "notificacao"
DIR_POPULACAO = DIR_DADOS / "populacao"
DIR_DB = RAIZ / "db"
CAMINHO_DB = DIR_DB / "projeto_sarampo_vacina.db"
CAMINHO_SCHEMA = Path(__file__).resolve().parent / "schema.sql"

ANO_INICIAL = 2015
ANO_FINAL = 2026
ANOS = list(range(ANO_INICIAL, ANO_FINAL + 1))
# Último ano com população IBGE disponível; o ano seguinte replica este valor.
ANO_POP_REFERENCIA = 2025
META_COBERTURA = 95.0  # meta do PNI (%)

COD_BRASIL = "00"
COD_RS = "43"
COD_POA = "431490"
UF_MUNICIPAL = "RS"  # única UF com detalhamento municipal nos dados

# código IBGE da UF -> (sigla, nome)
UFS: dict[str, tuple[str, str]] = {
    "11": ("RO", "Rondônia"),
    "12": ("AC", "Acre"),
    "13": ("AM", "Amazonas"),
    "14": ("RR", "Roraima"),
    "15": ("PA", "Pará"),
    "16": ("AP", "Amapá"),
    "17": ("TO", "Tocantins"),
    "21": ("MA", "Maranhão"),
    "22": ("PI", "Piauí"),
    "23": ("CE", "Ceará"),
    "24": ("RN", "Rio Grande do Norte"),
    "25": ("PB", "Paraíba"),
    "26": ("PE", "Pernambuco"),
    "27": ("AL", "Alagoas"),
    "28": ("SE", "Sergipe"),
    "29": ("BA", "Bahia"),
    "31": ("MG", "Minas Gerais"),
    "32": ("ES", "Espírito Santo"),
    "33": ("RJ", "Rio de Janeiro"),
    "35": ("SP", "São Paulo"),
    "41": ("PR", "Paraná"),
    "42": ("SC", "Santa Catarina"),
    "43": ("RS", "Rio Grande do Sul"),
    "50": ("MS", "Mato Grosso do Sul"),
    "51": ("MT", "Mato Grosso"),
    "52": ("GO", "Goiás"),
    "53": ("DF", "Distrito Federal"),
}
SIGLA_PARA_COD = {sigla: cod for cod, (sigla, _) in UFS.items()}

REGIOES = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}


def regiao_da_uf(cod_uf: str) -> str:
    return REGIOES[cod_uf[0]]
