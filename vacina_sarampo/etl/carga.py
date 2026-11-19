"""Carga: monta o banco SQLite a partir dos DataFrames padronizados.

Uso:  python -m vacina_sarampo.etl            (reconstrói db/projeto_sarampo_vacina.db)
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from .. import config
from . import extratores as ex


# ----------------------------------------------------------------------------
# utilitários
# ----------------------------------------------------------------------------
def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _linhas_arquivo(p: Path) -> int:
    if p.suffix == ".csv":
        return max(sum(1 for _ in p.open("rb")) - 1, 0)
    return 0


def _data_tabnet(p: Path) -> str | None:
    """Extrai 'Dados disponibilizados no TABNET em <mês/ano>' do rodapé, se houver."""
    m = re.search(r"disponibilizados no TABNET em ([^.\r\n]+)", p.read_text(encoding="latin1"))
    return f"{m.group(1).strip()} (TABNET)" if m else None


class Manifesto:
    """Acumula as linhas da tabela FONTE_ARQUIVO."""

    def __init__(self) -> None:
        self.itens: list[tuple] = []

    def add(self, fonte: str, caminho: Path, conteudo: str, linhas: int, data_extracao: str | None = None) -> None:
        mod = datetime.fromtimestamp(caminho.stat().st_mtime).date().isoformat()
        self.itens.append((fonte, caminho.name, conteudo, int(linhas), data_extracao, mod, _sha256(caminho)))


def _deduplica(df: pd.DataFrame, chave: list[str], valores: list[str], descricao: str, log: list) -> pd.DataFrame:
    """O total do RS aparece nos arquivos de UF e de município; mantém o primeiro e
    registra no log quantas divergências existiam entre as duas cópias."""
    dup = df[df.duplicated(chave, keep=False)]
    if len(dup):
        primeiro = dup.groupby(chave, as_index=False)[valores].first()
        outro = dup.groupby(chave, as_index=False)[valores].last()
        diverg = int((~((primeiro[valores].round(2) == outro[valores].round(2)).all(axis=1))).sum())
        log.append(("ETL", f"{descricao}: {len(primeiro)} pares duplicados, {diverg} divergentes", float(diverg)))
    return df.drop_duplicates(chave, keep="first").reset_index(drop=True)


# ----------------------------------------------------------------------------
# construção dos dados (sem tocar no banco)
# ----------------------------------------------------------------------------
def montar_dados(dir_dados: Path | None = None, verbose: bool = True) -> dict:
    """Executa todas as extrações/transformações e devolve os DataFrames finais."""
    if dir_dados is None:
        dir_imun, dir_not, dir_pop = config.DIR_IMUNIZACAO, config.DIR_NOTIFICACAO, config.DIR_POPULACAO
    else:
        dir_imun, dir_not, dir_pop = dir_dados / "imunizacao", dir_dados / "notificacao", dir_dados / "populacao"

    def say(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    log: list[tuple] = []
    man = Manifesto()

    # ---- população ---------------------------------------------------------
    say("[1/6] População IBGE ...")
    p_uf_path = dir_pop / "br_ibge_populacao_uf.csv"
    p_mun_path = dir_pop / "br_ibge_populacao_municipio.csv"
    pop_uf = ex.ler_populacao_uf(p_uf_path, log)
    pop_mun = ex.ler_populacao_municipio(p_mun_path, log=log)
    man.add("IBGE", p_uf_path, "População residente por UF (1991-2025)", len(pop_uf))
    man.add("IBGE", p_mun_path, "População residente por município (1991-2025)", len(pop_mun))
    pop_br = pop_uf.groupby("ano", as_index=False)["populacao"].sum().assign(cod_ibge=config.COD_BRASIL)
    pop = pd.concat([pop_uf, pop_mun, pop_br], ignore_index=True)
    pop = pop[(pop.ano >= config.ANO_INICIAL) & (pop.ano <= config.ANO_POP_REFERENCIA)].copy()
    pop["populacao_estimada"] = 0
    ref = pop[pop.ano == config.ANO_POP_REFERENCIA].copy()
    extra = []
    for ano in range(config.ANO_POP_REFERENCIA + 1, config.ANO_FINAL + 1):
        e = ref.copy()
        e["ano"], e["populacao_estimada"] = ano, 1
        extra.append(e)
    pop = pd.concat([pop, *extra], ignore_index=True)

    # ---- cobertura TABNET 2015-2022 ---------------------------------------
    say("[2/6] Cobertura vacinal TABNET/SI-PNI (2015-2022) ...")
    cv_tab, nomes_tab = [], {}
    for nivel in ("UF", "RS"):
        for p in sorted(dir_imun.glob(f"cv_{nivel}_*.csv")):
            d = ex.ler_cobertura_tabnet(p, nivel)
            cv_tab.append(d)
            man.add("TABNET/SI-PNI", p, f"Cobertura (%) Tríplice Viral D1/D2 - {nivel}", len(d))
            nomes_tab.update({r.cod_ibge: r.nome for r in d.itertuples() if r.nome})
    cv_tab = _deduplica(pd.concat(cv_tab, ignore_index=True), ["cod_ibge", "ano"],
                        ["cobertura_d1", "cobertura_d2"], "TABNET: total do RS nos arquivos UF e RS", log)

    # ---- cobertura/doses SEIDIGI 2023-2026 --------------------------------
    say("[3/6] Painel SEIDIGI/DEMAS (2023-2026) ...")
    cv_xl = []
    for p in sorted(dir_imun.glob("cv_triplice_*_dose_*.xlsx"), key=lambda q: ("_UF_" not in q.name, q.name)):
        d, dt = ex.ler_cobertura_seidigi(p)
        cv_xl.append(d)
        man.add("SEIDIGI/DEMAS", p, "Cobertura, doses e população-alvo mensais", len(d), dt)
    cv_xl = _deduplica(pd.concat(cv_xl, ignore_index=True), ["cod_ibge", "ano", "mes", "dose"],
                       ["doses_pop_alvo", "pop_alvo"], "SEIDIGI: total do RS nos arquivos UF e RS", log)

    dm = []
    for p in sorted(dir_imun.glob("triplice_*_dose_*.xlsx")):
        d = ex.ler_doses_mensais(p)
        dm.append(d)
        man.add("SEIDIGI/DEMAS", p, "Doses aplicadas por mês (qualquer idade)", len(d))
    doses_m = pd.concat(dm, ignore_index=True)
    ign = doses_m[doses_m.cod_ibge == "IGNORADA"]
    if len(ign):
        log.append(("SEIDIGI", "Doses mensais sem UF informada (linha '-') descartadas", float(ign.doses_aplicadas.sum())))
    doses_m = doses_m[doses_m.cod_ibge != "IGNORADA"]

    # ---- localidades -------------------------------------------------------
    say("[4/6] Cadastro de localidades ...")
    nomes_mun = (doses_m[doses_m.nome.notna()].drop_duplicates("cod_ibge").set_index("cod_ibge")["nome"].to_dict())
    cods_mun = sorted(pop_mun.cod_ibge.unique())
    loc = [(config.COD_BRASIL, "Brasil", "PAIS", "BR", None)]
    for cod, (sigla, nome) in config.UFS.items():
        loc.append((cod, nome, "UF", sigla, config.regiao_da_uf(cod)))
    for cod in cods_mun:
        nome = nomes_mun.get(cod) or ex._titulo(nomes_tab.get(cod, cod))
        loc.append((cod, nome, "MUNICIPIO", config.UF_MUNICIPAL, config.regiao_da_uf(cod[:2])))
    localidade = pd.DataFrame(loc, columns=["cod_ibge", "nome_localidade", "tipo_localidade", "sigla_uf", "regiao"])
    localidade.insert(0, "id_localidade", range(1, len(localidade) + 1))
    cods_validos = set(localidade.cod_ibge)
    desconhecidos = (set(cv_tab.cod_ibge) | set(cv_xl.cod_ibge) | set(doses_m.cod_ibge)) - cods_validos
    if desconhecidos:
        raise ex.ErroLeitura(f"Códigos fora do cadastro: {sorted(desconhecidos)[:5]}")

    # ---- vacinação anual ---------------------------------------------------
    say("[5/6] Consolidando vacinação anual e mensal ...")
    grade = pd.MultiIndex.from_product([localidade.cod_ibge, config.ANOS], names=["cod_ibge", "ano"]).to_frame(index=False)
    a_tab = cv_tab.drop(columns="nome")
    agg = (cv_xl.groupby(["cod_ibge", "ano", "dose"])
           .agg(cob_media=("cobertura_mensal", "mean"), doses=("doses_pop_alvo", "sum"),
                pop_alvo=("pop_alvo", "sum"), meses=("mes", "nunique"))
           .reset_index())
    pivot = agg.pivot(index=["cod_ibge", "ano"], columns="dose", values=["cob_media", "doses", "pop_alvo", "meses"])
    pivot.columns = [f"{a}_{d.lower()}" for a, d in pivot.columns]
    pivot = pivot.reset_index()
    for d in ("d1", "d2"):
        # método do painel/artigo: média simples das coberturas mensais (já em %)
        pivot[f"cobertura_{d}"] = pivot[f"cob_media_{d}"].round(2)
        # método alternativo (sensibilidade): razão das somas, comparável à taxa anual do TABNET
        pivot[f"cobertura_{d}_pond"] = (pivot[f"doses_{d}"] / pivot[f"pop_alvo_{d}"].where(pivot[f"pop_alvo_{d}"] > 0) * 100).round(2)
    va = grade.merge(a_tab, on=["cod_ibge", "ano"], how="left", suffixes=("", "_t"))
    va = va.merge(pivot, on=["cod_ibge", "ano"], how="left", suffixes=("", "_x"))
    for d in ("d1", "d2"):
        va[f"cobertura_{d}"] = va[f"cobertura_{d}_x"].combine_first(va[f"cobertura_{d}"])
        # 2015-2022: a taxa do TABNET já é anual, logo os dois métodos coincidem
        va[f"cobertura_{d}_pond"] = va[f"cobertura_{d}_pond"].combine_first(va[f"cobertura_{d}"])
    va = va.drop(columns=[c for c in va.columns if c.endswith("_x")])
    va["fonte"] = va["ano"].map(lambda a: "SEIDIGI/DEMAS" if a >= 2023 else "TABNET/SI-PNI")
    va["meses_cobertos"] = va[["meses_d1", "meses_d2"]].max(axis=1).fillna(12).astype(int)
    va["periodo_parcial"] = (va.meses_cobertos < 12).astype(int)
    for d in ("d1", "d2"):
        va[f"atingiu_meta_{d}"] = va[f"cobertura_{d}"].map(
            lambda x: None if pd.isna(x) else int(x >= config.META_COBERTURA))
    vacinacao_anual = va.rename(columns={"pop_alvo_d1": "populacao_alvo_d1", "pop_alvo_d2": "populacao_alvo_d2"})
    vacinacao_anual = vacinacao_anual.merge(localidade[["cod_ibge", "id_localidade"]], on="cod_ibge")
    sem_cob = vacinacao_anual[vacinacao_anual["cobertura_d1"].isna() | vacinacao_anual["cobertura_d2"].isna()]
    if len(sem_cob):
        log.append(("TABNET", "Municípios ausentes nos CSVs anuais (cobertura mantida como NULL)", float(len(sem_cob))))
    pop_zero_xl = int((cv_xl["pop_alvo"] == 0).sum())
    if pop_zero_xl:
        log.append(("SEIDIGI", "Registros mensais com pop_alvo = 0 (painel usa sentinela 1e-06 na taxa mensal)", float(pop_zero_xl)))

    # mensal (524 localidades sem o Brasil; meses ausentes = 0)
    sem_br = localidade[localidade.cod_ibge != config.COD_BRASIL]
    meses_disp = doses_m[["ano", "mes"]].drop_duplicates()
    grade_m = (sem_br[["cod_ibge"]].merge(meses_disp, how="cross")
               .merge(pd.DataFrame({"dose": ["D1", "D2"]}), how="cross"))
    mensal = grade_m.merge(doses_m[["cod_ibge", "ano", "mes", "dose", "doses_aplicadas"]],
                           on=["cod_ibge", "ano", "mes", "dose"], how="left")
    mensal["doses_aplicadas"] = mensal["doses_aplicadas"].fillna(0).astype(int)
    mensal = mensal.merge(cv_xl, on=["cod_ibge", "ano", "mes", "dose"], how="left")
    mensal = mensal.merge(localidade[["cod_ibge", "id_localidade"]], on="cod_ibge")

    # ---- notificações ------------------------------------------------------
    say("[6/6] Casos de sarampo (SINAN) ...")
    p_ex_uf = dir_not / "sarampo_inicio_exantema_UF_2015_2026.csv"
    p_ex_rs = dir_not / "sarampo_inicio_exantema_RS_2015_2026.csv"
    cs_uf = ex.ler_sarampo_exantema(p_ex_uf, "UF", log)
    cs_rs = ex.ler_sarampo_exantema(p_ex_rs, "RS", log)
    man.add("SINAN", p_ex_uf, "Casos de sarampo por UF e ano de início do exantema", len(cs_uf), _data_tabnet(p_ex_uf))
    man.add("SINAN", p_ex_rs, "Casos de sarampo por município do RS e ano de início do exantema", len(cs_rs), _data_tabnet(p_ex_rs))
    ig = cs_uf[cs_uf.nome.str.contains("Ignorado", case=False, na=False)]
    cs_uf = cs_uf[~cs_uf.nome.str.contains("Ignorado", case=False, na=False)]
    cs_uf = cs_uf.assign(cod_ibge=cs_uf.cod_ibge.astype(str))
    ig_br = ig.groupby("ano", as_index=False)["casos"].sum().assign(cod_ibge=config.COD_BRASIL)
    # Brasil = soma das 27 UFs + casos com UF de residência ignorada/exterior
    br = (pd.concat([cs_uf[["ano", "casos"]], ig_br[["ano", "casos"]]]).groupby("ano", as_index=False)["casos"].sum()
          .assign(cod_ibge=config.COD_BRASIL))
    if len(ig_br):
        log.append(("SINAN", "Casos com UF de residência ignorada/exterior (somados ao Brasil)", float(ig_br.casos.sum())))
    casos = pd.concat([cs_uf[["cod_ibge", "ano", "casos"]], cs_rs[["cod_ibge", "ano", "casos"]], br], ignore_index=True)
    casos = casos.groupby(["cod_ibge", "ano"], as_index=False)["casos"].sum()
    fora = set(casos.cod_ibge) - cods_validos
    if fora:
        raise ex.ErroLeitura(f"Casos em localidades fora do cadastro: {sorted(fora)[:5]}")

    notif = grade.merge(pop, on=["cod_ibge", "ano"], how="left").merge(casos, on=["cod_ibge", "ano"], how="left")
    if notif.populacao.isna().any():
        raise ex.ErroLeitura("Localidade/ano sem população IBGE")
    notif["casos"] = notif["casos"].fillna(0).astype(int)
    notif["incidencia_100k"] = (notif.casos / notif.populacao * 100000).round(4)
    notif["periodo_parcial"] = (notif.ano == config.ANO_FINAL).astype(int)
    notif = notif.rename(columns={"casos": "casos_inicio_exantema", "populacao": "populacao_ibge"})
    notif = notif.merge(localidade[["cod_ibge", "id_localidade"]], on="cod_ibge")

    # por ano de notificação (comparação / atraso de registro)
    nn = []
    for p in sorted(dir_not.glob("not_sarampo_*.csv")):
        d = ex.ler_sarampo_ano_notificacao(p)
        man.add("SINAN", p, "Casos de sarampo por ano de notificação (corte preliminar)", len(d), _data_tabnet(p))
        if "_UF_" in p.name:
            br_d = d.assign(cod_ibge=d.cod_ibge.astype(str))
            d = br_d[~br_d.nome.str.contains("Ignorado", case=False, na=False)]
            tot = br_d.groupby("ano_notificacao", as_index=False)["casos"].sum().assign(cod_ibge=config.COD_BRASIL, nome="Brasil")
            d = pd.concat([d, tot], ignore_index=True)
        nn.append(d)
    notif_ano = pd.concat(nn, ignore_index=True).groupby(["cod_ibge", "ano_notificacao"], as_index=False)["casos"].sum()
    notif_ano = notif_ano.merge(localidade[["cod_ibge", "id_localidade"]], on="cod_ibge")

    return dict(localidade=localidade, vacinacao_anual=vacinacao_anual, vacinacao_mensal=mensal,
                notificacao=notif, notificacao_ano_notif=notif_ano,
                manifesto=man.itens, log=log)


# ----------------------------------------------------------------------------
# gravação
# ----------------------------------------------------------------------------
def _n(v):
    """NaN/NA -> None e numpy -> tipos nativos para o sqlite3."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    return v.item() if hasattr(v, "item") else v


def _inserir(con: sqlite3.Connection, tabela: str, df: pd.DataFrame, colunas: list[str]) -> None:
    sql = f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})"
    con.executemany(sql, [tuple(_n(v) for v in row) for row in df[colunas].itertuples(index=False, name=None)])


def construir_banco(caminho_db: Path = config.CAMINHO_DB, dir_dados: Path | None = None, verbose: bool = True) -> Path:
    dados = montar_dados(dir_dados, verbose)
    caminho_db.parent.mkdir(parents=True, exist_ok=True)
    if caminho_db.exists():
        caminho_db.unlink()
    con = sqlite3.connect(caminho_db)
    try:
        con.executescript(config.CAMINHO_SCHEMA.read_text(encoding="utf-8"))
        con.execute("PRAGMA foreign_keys = ON")
        with con:
            _inserir(con, "LOCALIDADE", dados["localidade"],
                     ["id_localidade", "cod_ibge", "nome_localidade", "tipo_localidade", "sigla_uf", "regiao"])
            va = dados["vacinacao_anual"].sort_values(["ano", "id_localidade"])
            _inserir(con, "VACINACAO_ANUAL", va,
                     ["id_localidade", "ano", "cobertura_d1", "cobertura_d2", "cobertura_d1_pond", "cobertura_d2_pond",
                      "doses_d1", "doses_d2",
                      "populacao_alvo_d1", "populacao_alvo_d2", "atingiu_meta_d1", "atingiu_meta_d2",
                      "meses_cobertos", "periodo_parcial", "fonte"])
            vm = dados["vacinacao_mensal"].sort_values(["ano", "mes", "dose", "id_localidade"])
            _inserir(con, "VACINACAO_MENSAL", vm,
                     ["id_localidade", "ano", "mes", "dose", "doses_aplicadas", "cobertura_mensal",
                      "doses_pop_alvo", "pop_alvo"])
            nt = dados["notificacao"].sort_values(["ano", "id_localidade"])
            _inserir(con, "NOTIFICACAO_SARAMPO", nt,
                     ["id_localidade", "ano", "casos_inicio_exantema", "populacao_ibge", "incidencia_100k",
                      "populacao_estimada", "periodo_parcial"])
            nn = dados["notificacao_ano_notif"].rename(columns={"casos": "casos_notificados"})
            _inserir(con, "NOTIFICACAO_ANO_NOTIF", nn, ["id_localidade", "ano_notificacao", "casos_notificados"])
            con.executemany("INSERT INTO FONTE_ARQUIVO (fonte, arquivo, conteudo, linhas_lidas, data_extracao, modificado_em, sha256) "
                            "VALUES (?,?,?,?,?,?,?)", dados["manifesto"])
            con.executemany("INSERT INTO LOG_QUALIDADE (etapa, descricao, valor) VALUES (?,?,?)", dados["log"])
        violacoes = con.execute("PRAGMA foreign_key_check").fetchall()
        if violacoes:
            raise sqlite3.IntegrityError(f"{len(violacoes)} violações de chave estrangeira")
        con.execute("VACUUM")
    finally:
        con.close()
    if verbose:
        resumo_banco(caminho_db)
    return caminho_db


def resumo_banco(caminho_db: Path) -> None:
    con = sqlite3.connect(caminho_db)
    try:
        print("\nBanco gerado:", caminho_db, f"({caminho_db.stat().st_size / 1e6:.1f} MB)")
        for t in ("LOCALIDADE", "VACINACAO_ANUAL", "VACINACAO_MENSAL", "NOTIFICACAO_SARAMPO",
                  "NOTIFICACAO_ANO_NOTIF", "FONTE_ARQUIVO", "LOG_QUALIDADE"):
            print(f"  {t:<24}{con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>8} registros")
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    construir_banco()
    return 0


if __name__ == "__main__":
    sys.exit(main())
