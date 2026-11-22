"""Gera figuras vetoriais e dados do artigo a partir do SQLite, somente para leitura.

Executar com Python e Matplotlib: python Entregas/artigo_atualizado/gerar_figuras.py
Não é necessário iniciar o Streamlit. O banco deve ter sido gerado pelo ETL do projeto.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3

os.environ.setdefault("MPLCONFIGDIR", "/tmp/projetobd-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter, MultipleLocator

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parents[1]
BANCO = RAIZ / "db" / "projeto_sarampo_vacina.db"
CORES = {"Brasil": "#17649b", "Rio Grande do Sul": "#39834c", "Porto Alegre": "#97559c"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.labelsize": 9, "axes.titlesize": 10,
                     "legend.fontsize": 8, "pdf.fonttype": 42})


def exportar_csv(nome, registros):
    if not registros:
        return
    with (PASTA / "dados" / nome).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(registros[0]))
        w.writeheader()
        w.writerows(registros)


def salvar(fig, nome):
    fig.savefig(PASTA / "figuras" / f"{nome}.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(PASTA / "figuras" / f"{nome}.png", bbox_inches="tight", pad_inches=0.04, dpi=220)
    plt.close(fig)


def main():
    (PASTA / "figuras").mkdir(exist_ok=True)
    (PASTA / "dados").mkdir(exist_ok=True)
    con = sqlite3.connect(f"file:{BANCO.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    serie = [dict(r) for r in con.execute("""
        SELECT l.cod_ibge,l.nome_localidade,v.ano,v.cobertura_d1,v.cobertura_d2,
               v.cobertura_d1_pond,v.cobertura_d2_pond,v.doses_d1,v.doses_d2,
               n.casos_inicio_exantema,n.populacao_ibge,n.incidencia_100k
        FROM VACINACAO_ANUAL v JOIN LOCALIDADE l USING(id_localidade)
        JOIN NOTIFICACAO_SARAMPO n USING(id_localidade,ano)
        WHERE l.cod_ibge IN ('00','43','431490') ORDER BY l.cod_ibge,v.ano
    """)]
    exportar_csv("serie_brasil_rs_poa.csv", serie)
    fig, axes = plt.subplots(1, 2, figsize=(6, 2.65), sharey=True)
    for ax, dose in zip(axes, ("d1", "d2")):
        for nome, cor in CORES.items():
            dados = [r for r in serie if r["nome_localidade"] == nome]
            ax.plot([r["ano"] for r in dados], [r[f"cobertura_{dose}"] for r in dados],
                    label="RS" if nome == "Rio Grande do Sul" else nome,
                    color=cor, marker={"Brasil": "o", "Rio Grande do Sul": "s", "Porto Alegre": "^"}[nome],
                    markersize=3, linewidth=1.4)
        ax.axhline(95, color="#555555", linestyle="--", linewidth=0.9)
        ax.axvline(2022.5, color="#999999", linestyle=":", linewidth=1)
        ax.axvspan(2025.5, 2026.4, color="#dddddd", alpha=0.7)
        ax.set(xlim=(2014.7, 2026.4), ylim=(40, 105), title=f"{dose.upper()} · cobertura anual", xlabel="Ano")
        ax.set_xticks([2015, 2018, 2021, 2024, 2026])
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Cobertura (%)")
    axes[1].text(2015, 96.5, "Meta de 95%", fontsize=8, color="#555555")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.015))
    fig.subplots_adjust(left=0.09, right=0.99, top=0.86, bottom=0.22, wspace=0.12)
    salvar(fig, "cobertura_historica")

    mensal = [dict(r) for r in con.execute("""
        SELECT m.ano,m.mes,m.dose,m.doses_aplicadas,m.doses_pop_alvo
        FROM VACINACAO_MENSAL m JOIN LOCALIDADE l USING(id_localidade)
        WHERE cod_ibge='431490' ORDER BY m.dose,m.ano,m.mes
    """)]
    exportar_csv("doses_mensais_poa.csv", mensal)
    fig, axes = plt.subplots(1, 2, figsize=(6, 2.55))
    cores_ano = {2023: "#17649b", 2024: "#d77e22", 2025: "#39834c", 2026: "#97559c"}
    for ax, dose in zip(axes, ("D1", "D2")):
        for ano, cor in cores_ano.items():
            d = [r for r in mensal if r["ano"] == ano and r["dose"] == dose]
            ax.plot([r["mes"] for r in d], [r["doses_aplicadas"] for r in d],
                    color=cor, marker="o", markersize=2.8,
                    linestyle="--" if ano == 2026 else "-", label=str(ano), linewidth=1.2)
        ax.set(title=dose, xlabel="Mês", xlim=(0.8, 12.2), ylim=(0, None))
        ax.set_xticks([1, 3, 5, 7, 9, 11], ["jan", "mar", "mai", "jul", "set", "nov"])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", ".")))
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Doses aplicadas (todas as idades)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.subplots_adjust(left=0.12, right=0.99, top=0.86, bottom=0.22, wspace=0.28)
    salvar(fig, "doses_mensais_poa")

    ranking = [dict(r) for r in con.execute("""
        SELECT l.nome_localidade,n.casos_inicio_exantema,n.populacao_ibge,n.incidencia_100k
        FROM NOTIFICACAO_SARAMPO n JOIN LOCALIDADE l USING(id_localidade)
        WHERE n.ano=2019 AND l.nome_localidade IN
            ('Cachoeirinha','Gravataí','Porto Alegre','Carlos Gomes','Sapucaia do Sul','Trindade do Sul')
        ORDER BY n.incidencia_100k DESC
    """)]
    exportar_csv("exemplos_municipais_2019.csv", ranking)
    fig, axes = plt.subplots(1, 2, figsize=(6, 2.65), sharey=True)
    d = list(reversed(ranking))
    nomes = [r["nome_localidade"] for r in d]
    for ax, campo, titulo, cor in zip(axes, ["casos_inicio_exantema", "incidencia_100k"],
                                     ["Número de casos", "Incidência por 100 mil"], ["#b54d4d", "#17649b"]):
        valores = [r[campo] for r in d]
        ax.barh(nomes, valores, color=cor, height=0.65)
        ax.set_title(titulo)
        ax.set_xlim(0, max(valores) * 1.22)
        ax.grid(axis="x", alpha=0.15)
        for i, v in enumerate(valores):
            txt = f"{v:.2f}".replace(".", ",") if campo == "incidencia_100k" else str(v)
            ax.text(v + max(valores) * 0.025, i, txt, va="center", fontsize=8)
    axes[0].xaxis.set_major_locator(MultipleLocator(10))
    fig.subplots_adjust(left=0.24, right=0.99, bottom=0.14, top=0.85, wspace=0.16)
    salvar(fig, "casos_incidencia_2019")

    fig, ax = plt.subplots(figsize=(6, 2.7))
    ax.set(xlim=(0, 10), ylim=(0, 4.5))
    ax.axis("off")

    def caixa(x, y, w, h, titulo, texto, cor="#f5f7fa"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.07", linewidth=0.8,
                                   edgecolor="#64748b", facecolor=cor))
        ax.text(x + w / 2, y + h - 0.28, titulo, ha="center", va="center", fontsize=9, weight="bold")
        ax.text(x + w / 2, y + h / 2 - 0.1, texto, ha="center", va="center", fontsize=8, linespacing=1.4)

    caixa(3.35, 3, 3.3, 1.3, "Localidade", "PK: id_localidade\nCódigo IBGE único · tipo · UF", "#edf4fb")
    for x, titulo, texto in [(0.1, "Vacinação anual", "FK: localidade · ano\nD1/D2 · método\nPeríodo parcial"),
                             (3.45, "Vacinação mensal", "FK: localidade\nAno · mês · dose\nAplicações · cobertura · alvo"),
                             (6.8, "Sarampo anual", "FK: localidade · ano\nCasos · população\nIncidência")]:
        caixa(x, 0.95, 3.1, 1.35, titulo, texto)
        ax.annotate("", xy=(x + 1.55, 2.35), xytext=(5, 2.95),
                    arrowprops=dict(arrowstyle="->", color="#64748b", linewidth=0.9))
        ax.text(x + 1.75, 2.5, "1:N", fontsize=8, ha="center", bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
    ax.text(5, 0.38, "Apoio: ano de notificação · manifesto de arquivos · log de qualidade",
            fontsize=8.5, ha="center", va="center")
    salvar(fig, "modelo_relacional")

    sensibilidade = [dict(r) for r in con.execute("""
        SELECT ano, SUM((cobertura_d1>=95)!=(cobertura_d1_pond>=95)) AS mudam_d1,
            SUM((cobertura_d2>=95)!=(cobertura_d2_pond>=95)) AS mudam_d2,
            SUM(cobertura_d1>=95) AS meta_d1_media, SUM(cobertura_d1_pond>=95) AS meta_d1_razao,
            SUM(cobertura_d2>=95) AS meta_d2_media, SUM(cobertura_d2_pond>=95) AS meta_d2_razao
        FROM VACINACAO_ANUAL JOIN LOCALIDADE USING(id_localidade)
        WHERE tipo_localidade='MUNICIPIO' AND ano>=2023 GROUP BY ano
    """)]
    exportar_csv("sensibilidade_metodos.csv", sensibilidade)
    grupos = [dict(r) for r in con.execute("""
        SELECT 'D2' AS dose,2019 AS ano,5000 AS populacao_minima,
            CASE WHEN v.cobertura_d2<95 THEN 'Abaixo de 95%' ELSE '95% ou mais' END AS situacao,
            COUNT(*) AS localidades,SUM(n.casos_inicio_exantema) AS casos,
            SUM(n.populacao_ibge) AS populacao,
            100000.0*SUM(n.casos_inicio_exantema)/SUM(n.populacao_ibge) AS incidencia_100k
        FROM NOTIFICACAO_SARAMPO n JOIN VACINACAO_ANUAL v USING(id_localidade,ano)
        JOIN LOCALIDADE l USING(id_localidade)
        WHERE l.tipo_localidade='MUNICIPIO' AND n.ano=2019 AND n.populacao_ibge>=5000
            AND v.cobertura_d2 IS NOT NULL
        GROUP BY situacao ORDER BY localidades DESC
    """)]
    exportar_csv("comparacao_grupos_2019.csv", grupos)
    manifesto = {
        "banco": str(BANCO.relative_to(RAIZ)), "sha256_banco": hashlib.sha256(BANCO.read_bytes()).hexdigest(),
        "data_revisao": "2026-11-22", "matplotlib_figuras": matplotlib.__version__,
        "arquivo_figuras": "gerar_figuras.py", "metodo_figura_cobertura": "media_mensal",
        "observacao": "Gráficos autorais derivados do banco; não são capturas da interface."
    }
    (PASTA / "dados" / "manifesto_figuras.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n")
    con.close()


if __name__ == "__main__":
    main()
