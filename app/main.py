"""Ponto de entrada do app Streamlit.

Executar (na raiz do projeto):
    streamlit run app/main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

import common  # noqa: E402
from vacina_sarampo import consultas  # noqa: E402

st.set_page_config(page_title="Cobertura vacinal × Sarampo", page_icon="💉", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
  div[data-testid="stMetricValue"] { font-size: 1.5rem; }
  .bloco-nota { font-size: 0.85rem; color: #555; }
</style>
""", unsafe_allow_html=True)

common.exige_banco()

paginas = [
    st.Page("paginas/visao_geral.py", title="Visão geral", icon="🏠", default=True, url_path="visao-geral"),
    st.Page("paginas/cobertura.py", title="Cobertura vacinal", icon="💉", url_path="cobertura"),
    st.Page("paginas/casos.py", title="Casos e incidência", icon="🦠", url_path="casos"),
    st.Page("paginas/cruzamento.py", title="Cobertura × sarampo", icon="🔀", url_path="cruzamento"),
    st.Page("paginas/municipio.py", title="Ficha do município", icon="🏥", url_path="municipio"),
    st.Page("paginas/dados.py", title="Dados e metodologia", icon="📚", url_path="dados"),
]
pg = st.navigation(paginas)

with st.sidebar:
    st.markdown("### Configuração global")
    st.radio(
        "Cálculo da cobertura anual em 2023–2026",
        options=list(consultas.METODOS),
        format_func=lambda k: consultas.ROTULO_METODO[k],
        key="metodo_cobertura",
        help="Em 2015–2022 a taxa anual vem pronta do TABNET e os dois métodos coincidem. "
             "Em 2023–2026 o painel SEIDIGI só entrega valores mensais.",
    )
    st.divider()
    st.caption("Projeto de Banco de Dados · INF/UFRGS · versão inicial. "
               "Dados: TABNET/SI-PNI, SEIDIGI/DEMAS, SINAN, IBGE.")

pg.run()
