"""Funções compartilhadas pelas páginas do app (acesso a dados, filtros, exportação, avisos)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from vacina_sarampo import config, consultas  # noqa: E402

COR_D1 = "#1f77b4"
COR_D2 = "#ff7f0e"
COR_META = "#2ca02c"
COR_CASOS = "#d62728"
PALETA = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#17becf", "#7f7f7f"]
SEPARADORES = ",."  # pt-BR em eixos e dicas do Plotly


# ---------------------------------------------------------------------------
# acesso a dados
# ---------------------------------------------------------------------------
VersaoBanco = tuple[str, int, int, int]


def db_versao() -> VersaoBanco:
    """Identifica atualizações e substituições do arquivo feitas pelo ETL."""
    caminho = config.CAMINHO_DB.resolve()
    try:
        info = caminho.stat()
    except FileNotFoundError:
        return (str(caminho), 0, 0, 0)
    return (str(caminho), info.st_ino, info.st_mtime_ns, info.st_size)


@st.cache_resource(show_spinner=False, max_entries=1)
def _conexao(versao: VersaoBanco):
    # A conexão também deve mudar: o ETL remove e recria o arquivo SQLite.
    return consultas.conectar(Path(versao[0]))


def get_con():
    return _conexao(db_versao())


@st.cache_data(show_spinner=False, max_entries=256)
def q(nome: str, versao: VersaoBanco, **kwargs) -> pd.DataFrame:
    """Executa ``consultas.<nome>(con, **kwargs)`` com cache."""
    return getattr(consultas, nome)(_conexao(versao), **kwargs)


def dados(nome: str, **kwargs) -> pd.DataFrame:
    return q(nome, db_versao(), **kwargs)


def metodo_atual() -> str:
    return st.session_state.get("metodo_cobertura", "media_mensal")


def exige_banco() -> None:
    if not config.CAMINHO_DB.exists():
        st.error("Banco de dados não encontrado. Gere-o executando no terminal:")
        st.code("python -m vacina_sarampo.etl", language="bash")
        st.stop()


def rotulo_localidade(row) -> str:
    sufixo = {"PAIS": "", "UF": " (UF)", "MUNICIPIO": f" ({row.sigla_uf})"}[row.tipo_localidade]
    return f"{row.nome_localidade}{sufixo}"


@st.cache_data(show_spinner=False, max_entries=1)
def mapa_localidades(versao: VersaoBanco) -> pd.DataFrame:
    df = consultas.localidades(_conexao(versao))
    df["rotulo"] = df.apply(rotulo_localidade, axis=1)
    return df


def localidades() -> pd.DataFrame:
    return mapa_localidades(db_versao())


def seletor_localidades(rotulo: str, padrao: list[str], chave: str, maximo: int | None = None,
                        tipos: tuple[str, ...] = ("PAIS", "UF", "MUNICIPIO")) -> list[str]:
    """Multiselect de localidades; devolve os códigos IBGE."""
    loc = localidades()
    loc = loc[loc.tipo_localidade.isin(tipos)]
    por_cod = dict(zip(loc.cod_ibge, loc.rotulo))
    sel = st.multiselect(rotulo, options=list(por_cod), default=[c for c in padrao if c in por_cod],
                         format_func=lambda c: por_cod[c], key=chave, max_selections=maximo)
    return sel


# ---------------------------------------------------------------------------
# formatação
# ---------------------------------------------------------------------------
def fmt_num(x, casas: int = 0) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(x, casas: int = 1) -> str:
    return "—" if x is None or pd.isna(x) else fmt_num(x, casas) + "%"


# ---------------------------------------------------------------------------
# exportação (tabelas e gráficos)
# ---------------------------------------------------------------------------
def _xlsx(df: pd.DataFrame, nome_aba: str) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=nome_aba[:31])
        ws = w.sheets[nome_aba[:31]]
        for i, col in enumerate(df.columns):
            larg = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)]) + 2
            ws.set_column(i, i, min(larg, 45))
        ws.freeze_panes(1, 0)
    return buf.getvalue()


def botoes_exportar(df: pd.DataFrame, nome_arquivo: str, chave: str) -> None:
    """Botões de download (CSV pt-BR para Excel e XLSX) para uma tabela."""
    c1, c2, _ = st.columns([1, 1, 3])
    csv = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    c1.download_button("⬇ CSV", csv, f"{nome_arquivo}.csv", "text/csv", key=f"csv_{chave}",
                       help="Separador ';' e vírgula decimal (abre direto no Excel pt-BR)")
    c2.download_button("⬇ Excel", _xlsx(df, nome_arquivo), f"{nome_arquivo}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"xlsx_{chave}")


def mostrar_tabela(df: pd.DataFrame, nome_arquivo: str, chave: str, column_config: dict | None = None,
                   altura: int | None = None) -> None:
    kwargs: dict = dict(hide_index=True, width="stretch", column_config=column_config)
    if altura is not None:
        kwargs["height"] = altura
    st.dataframe(df, **kwargs)
    botoes_exportar(df, nome_arquivo, chave)


def mostrar_figura(fig: go.Figure, nome_arquivo: str, chave: str, altura: int = 460) -> None:
    """Exibe o gráfico (com botão PNG do próprio Plotly) e oferece HTML interativo."""
    fig.update_layout(height=altura, separators=SEPARADORES, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=-0.35, x=0))
    cfg = {"toImageButtonOptions": {"format": "png", "filename": nome_arquivo, "scale": 2},
           "displaylogo": False, "locale": "pt-BR"}
    st.plotly_chart(fig, width="stretch", config=cfg, key=f"fig_{chave}")
    html = fig.to_html(include_plotlyjs="cdn", config=cfg).encode("utf-8")
    st.download_button("⬇ Gráfico interativo (HTML)", html, f"{nome_arquivo}.html", "text/html",
                       key=f"html_{chave}", help="Para imagem PNG use o ícone da câmera no canto do gráfico.")


def marca_ano_parcial(fig: go.Figure, ano_ini: int, ano_fim: int, texto: str = "2026 parcial") -> None:
    if ano_ini <= config.ANO_FINAL <= ano_fim:
        fig.add_vrect(x0=config.ANO_FINAL - 0.5, x1=config.ANO_FINAL + 0.5, fillcolor="gray", opacity=0.13,
                      line_width=0, annotation_text=texto, annotation_position="top left",
                      annotation_font_size=11)


def linha_meta(fig: go.Figure, **kw) -> None:
    fig.add_hline(y=config.META_COBERTURA, line_dash="dot", line_color=COR_META,
                  annotation_text="Meta do PNI (95%)", annotation_position="bottom right", **kw)


# ---------------------------------------------------------------------------
# avisos metodológicos (explicitam limitações das fontes — avaliações 1, 2 e 3)
# ---------------------------------------------------------------------------
AVISOS = {
    "parcial": "**2026 é um ano parcial.** A cobertura cobre janeiro–agosto, as doses mensais vão até outubro e os casos "
               "refletem o SINAN até setembro/2026 (sujeitos à revisão). Evite comparar 2026 diretamente com anos completos.",
    "pop2026": "**População de 2026 = população de 2025** (o IBGE ainda não divulgou estimativa para 2026). Se a "
               "população real mudou, a incidência de 2026 está sub ou superestimada na mesma proporção.",
    "doses": "**Doses absolutas só existem a partir de 2023.** Para 2015–2022 as fontes (TABNET/SI-PNI) trazem apenas a "
             "taxa de cobertura.",
    "exantema": "**Casos por ano de início do exantema.** O exantema (manchas na pele) é um dos sintomas do sarampo; "
                "o ano do exantema é o critério de data usado nos dados do SINAN, e não necessariamente o início de "
                "todos os sintomas.",
    "pop_censo": "Em 2022 a população do IBGE foi reestimada com o Censo, o que reduz denominadores e pode gerar "
                 "saltos artificiais entre 2021 e 2022 (cobertura e incidência).",
    "pequenos": "Municípios pequenos têm taxas instáveis: 1 caso em 1.300 habitantes equivale a ~77 casos/100 mil. "
                "Considere o número absoluto de casos e use o filtro de população mínima.",
    "metodo": "Em 2023–2026 a cobertura anual pode ser calculada de dois modos (veja a barra lateral): média simples "
              "das coberturas mensais (padrão do artigo) ou soma das doses ÷ soma da população-alvo (ponderada, "
              "recomendada em municípios pequenos por evitar distorções de meses com população-alvo = 0). Em 2015–2022 "
              "os dois métodos coincidem.",
}


def aviso(*chaves: str, expandido: bool = False, titulo: str = "⚠ Particularidades das fontes desta análise") -> None:
    with st.expander(titulo, expanded=expandido):
        for k in chaves:
            st.markdown(f"- {AVISOS[k]}")


def mostra_sql(nome: str, **extra: str) -> None:
    with st.expander("Ver consulta SQL"):
        st.code(consultas.sql_formatado(nome, metodo_atual(), **extra), language="sql")
