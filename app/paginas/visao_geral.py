import plotly.graph_objects as go
import streamlit as st

import common as c
from vacina_sarampo import config

c.exige_banco()
metodo = c.metodo_atual()

st.title("Cobertura vacinal da Tríplice Viral e sarampo")
st.caption("Cruzamento de bases públicas de imunização (TABNET/SI-PNI e SEIDIGI/DEMAS), vigilância (SINAN) e "
           "população (IBGE) · Brasil, UFs e municípios do RS · 2015–2026")

c.aviso("parcial", "pop2026", "doses", "exantema", "metodo")

ano = st.select_slider("Ano de referência dos indicadores", options=config.ANOS, value=2025,
                       help="2026 é parcial; o padrão é o último ano completo.")

base = c.dados("ca1_cruzamento", cods=[config.COD_BRASIL, config.COD_RS, config.COD_POA], metodo=metodo,
               ano_ini=config.ANO_INICIAL, ano_fim=config.ANO_FINAL)
a = base[base.ano == ano].set_index("cod_ibge")
meta = c.dados("cb4_municipios_na_meta", dose="D1", metodo=metodo).set_index("ano")

col = st.columns(5)
col[0].metric("Brasil · D1", c.fmt_pct(a.loc[config.COD_BRASIL, "cobertura_d1"]),
              delta=f"{a.loc[config.COD_BRASIL, 'cobertura_d1'] - config.META_COBERTURA:+.1f} p.p. vs meta".replace(".", ","),
              delta_color="normal")
col[1].metric("Brasil · D2", c.fmt_pct(a.loc[config.COD_BRASIL, "cobertura_d2"]),
              delta=f"{a.loc[config.COD_BRASIL, 'cobertura_d2'] - config.META_COBERTURA:+.1f} p.p. vs meta".replace(".", ","))
col[2].metric("RS · D1 / D2", f"{c.fmt_pct(a.loc[config.COD_RS, 'cobertura_d1'], 1)} / {c.fmt_pct(a.loc[config.COD_RS, 'cobertura_d2'], 1)}")
col[3].metric("Porto Alegre · D1 / D2",
              f"{c.fmt_pct(a.loc[config.COD_POA, 'cobertura_d1'], 1)} / {c.fmt_pct(a.loc[config.COD_POA, 'cobertura_d2'], 1)}")
if ano in meta.index:
    col[4].metric("Municípios do RS na meta (D1)",
                  f"{int(meta.loc[ano, 'municipios_na_meta'])} de {int(meta.loc[ano, 'municipios_com_dado'])}")

col2 = st.columns(3)
col2[0].metric("Casos de sarampo no Brasil (início do exantema)", c.fmt_num(a.loc[config.COD_BRASIL, "casos"]),
               help="Inclui casos com UF de residência ignorada/exterior.")
col2[1].metric("Incidência no Brasil (por 100 mil hab.)", c.fmt_num(a.loc[config.COD_BRASIL, "incidencia_100k"] if "incidencia_100k" in a else 0, 2))
col2[2].metric("Casos no RS / Porto Alegre", f"{c.fmt_num(a.loc[config.COD_RS, 'casos'])} / {c.fmt_num(a.loc[config.COD_POA, 'casos'])}")
if ano == config.ANO_FINAL:
    st.info(c.AVISOS["parcial"])

st.subheader("Evolução: cobertura da 2ª dose, 1ª dose e casos de sarampo")
fig = go.Figure()
brasil = base[base.cod_ibge == config.COD_BRASIL]
fig.add_bar(x=brasil.ano, y=brasil.casos, name="Casos no Brasil (eixo dir.)", marker_color="rgba(214,39,40,0.35)",
            yaxis="y2", hovertemplate="%{x}: %{y:,.0f} casos<extra></extra>")
for cod, nome, cor in [(config.COD_BRASIL, "Brasil", c.PALETA[0]), (config.COD_RS, "RS", c.PALETA[2]),
                       (config.COD_POA, "Porto Alegre", c.PALETA[3])]:
    d = base[base.cod_ibge == cod]
    fig.add_scatter(x=d.ano, y=d.cobertura_d1, name=f"{nome} · D1", mode="lines+markers", line=dict(color=cor))
    fig.add_scatter(x=d.ano, y=d.cobertura_d2, name=f"{nome} · D2", mode="lines+markers", line=dict(color=cor, dash="dash"))
c.linha_meta(fig)
c.marca_ano_parcial(fig, config.ANO_INICIAL, config.ANO_FINAL)
fig.update_layout(yaxis=dict(title="Cobertura (%)", range=[0, 115]),
                  yaxis2=dict(title="Casos de sarampo", overlaying="y", side="right", showgrid=False),
                  xaxis=dict(dtick=1), hovermode="x unified", title="Cobertura (linha cheia: D1; tracejada: D2) e casos no Brasil")
c.mostrar_figura(fig, "visao_geral_cobertura_casos", "vg1", 500)

# Mensagens-chave calculadas a partir dos dados (não texto fixo)
d2_abaixo = int((brasil.cobertura_d2 < config.META_COBERTURA).sum())
anos_d1_meta = brasil[brasil.cobertura_d1 >= config.META_COBERTURA].ano.tolist()
st.subheader("Leitura rápida")
st.markdown(f"""
- A **2ª dose** ficou abaixo de 95% em **{d2_abaixo} dos {len(brasil)} anos** no Brasil.
- A **1ª dose** atingiu a meta nacional apenas em: **{', '.join(map(str, anos_d1_meta)) or 'nenhum ano'}**.
- Use as páginas ao lado para detalhar por UF, município, mês e para exportar tabelas e gráficos.
""")
st.caption("Observação: esta plataforma apresenta cruzamentos e comparações descritivas. As relações entre cobertura "
           "e incidência são exploratórias (veja a página *Cobertura × sarampo*) e não indicam causalidade.")
