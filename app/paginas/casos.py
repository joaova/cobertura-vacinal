import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import common as c
from vacina_sarampo import config

c.exige_banco()

st.title("Casos de sarampo e incidência")
c.aviso("exantema", "pop2026", "parcial", "pop_censo", "pequenos")

NIVEIS = {"Municípios do RS": "MUNICIPIO", "Unidades da Federação": "UF", "Brasil": "PAIS"}

f1, f2, f3 = st.columns([2, 2, 3])
nivel_rot = f1.radio("Nível geográfico", list(NIVEIS), key="cb3_nivel")
nivel = NIVEIS[nivel_rot]
modo = f2.radio("Período", ["Ano específico", "Acumulado no intervalo"], key="cb3_modo")
if modo == "Ano específico":
    ano = f3.select_slider("Ano", options=config.ANOS, value=2019, key="cb3_ano")
    ini = fim = ano
else:
    ini, fim = f3.slider("Intervalo de anos", config.ANO_INICIAL, config.ANO_FINAL, (2018, 2020), key="cb3_int")

g1, g2, g3, g4 = st.columns(4)
min_casos = g1.number_input("Mínimo de casos", 1, 100000, 1, key="cb3_min")
pop_min = g2.number_input("População mínima", 0, 20_000_000, 0, step=1000, key="cb3_pop",
                          help="Exclui localidades pequenas, cuja incidência é instável.")
ordem = g3.radio("Ordenar por", ["Incidência", "Casos"], horizontal=True, key="cb3_ord")
topn = g4.slider("Mostrar as N primeiras", 5, 60, 20, key="cb3_top")

df = c.dados("cb3_ranking_casos", tipo=nivel, ano_ini=ini, ano_fim=fim, min_casos=1)
if nivel == "UF":
    regioes = st.multiselect("Regiões", ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"],
                             default=["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"], key="cb3_reg")
    uf_reg = c.localidades().set_index("cod_ibge")["regiao"]
    df = df[df.cod_ibge.map(uf_reg).isin(regioes)]

if modo == "Acumulado no intervalo" and ini != fim:
    # incidência acumulada = soma das incidências anuais (casos_t / pop_t) no intervalo;
    # ordena por ano antes para pegar a população do ano mais recente do intervalo
    agg = (df.sort_values("ano").groupby(["cod_ibge", "nome_localidade", "sigla_uf"], as_index=False)
           .agg(casos_inicio_exantema=("casos_inicio_exantema", "sum"), incidencia_100k=("incidencia_100k", "sum"),
                populacao_ibge=("populacao_ibge", "last")))
    df = agg.assign(ano=f"{ini}–{fim}")
else:
    df = df.assign(ano=df["ano"].astype(str))

df = df[(df.casos_inicio_exantema >= min_casos) & (df.populacao_ibge >= pop_min)]
chave = "incidencia_100k" if ordem == "Incidência" else "casos_inicio_exantema"
df = df.sort_values([chave, "casos_inicio_exantema"], ascending=False)
topo = df.head(topn).copy()
topo["rotulo"] = topo.nome_localidade if nivel != "PAIS" else (topo.nome_localidade + " " + topo.ano)

if df.empty:
    st.info("Nenhum registro com esses filtros.")
else:
    k = st.columns(3)
    k[0].metric("Localidades com casos", c.fmt_num(df.cod_ibge.nunique()))
    k[1].metric("Casos no filtro", c.fmt_num(df.casos_inicio_exantema.sum()))
    k[2].metric("Maior incidência (por 100 mil)", c.fmt_num(df.incidencia_100k.max(), 2))

    d = topo.iloc[::-1]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                        subplot_titles=("Casos (número absoluto)", "Incidência por 100 mil hab."))
    fig.add_bar(y=d.rotulo, x=d.casos_inicio_exantema, orientation="h", marker_color=c.COR_CASOS, name="Casos",
                row=1, col=1, hovertemplate="%{y}: %{x:,.0f} casos<extra></extra>")
    fig.add_bar(y=d.rotulo, x=d.incidencia_100k, orientation="h", marker_color=c.COR_D1, name="Incidência",
                row=1, col=2, customdata=d.populacao_ibge,
                hovertemplate="%{y}: %{x:,.2f}/100 mil<br>População: %{customdata:,.0f}<extra></extra>")
    fig.update_layout(title=f"{nivel_rot} — {topn} primeiros por {ordem.lower()} ({ini if ini == fim else f'{ini}–{fim}'})",
                      showlegend=False)
    c.mostrar_figura(fig, "cb3_casos_incidencia", "cb3", altura=max(420, 24 * len(d) + 130))
    if ini <= config.ANO_FINAL <= fim:
        st.warning(c.AVISOS["parcial"])

    tab = df.rename(columns={"cod_ibge": "Cód. IBGE", "nome_localidade": "Localidade", "sigla_uf": "UF",
                             "ano": "Ano", "casos_inicio_exantema": "Casos (início do exantema)",
                             "populacao_ibge": "População IBGE", "incidencia_100k": "Incidência /100 mil"})
    tab["Incidência /100 mil"] = tab["Incidência /100 mil"].round(2)
    cols = [x for x in ["Cód. IBGE", "Localidade", "UF", "Ano", "Casos (início do exantema)", "População IBGE",
                        "Incidência /100 mil"] if x in tab.columns]
    c.mostrar_tabela(tab[cols], "cb3_casos_incidencia", "cb3_t", altura=380)
c.mostra_sql("CB3")
