import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common as c
from vacina_sarampo import config

c.exige_banco()
metodo = c.metodo_atual()

st.title("Ficha do município")
st.caption("Cobertura vacinal, casos de sarampo e doses aplicadas no município selecionado, com exportação da ficha.")
c.aviso("parcial", "pop2026", "doses", "pequenos", "exantema")

loc = c.localidades()
muns = loc[loc.tipo_localidade == "MUNICIPIO"]
por_cod = dict(zip(muns.cod_ibge, muns.nome_localidade))
cod = st.selectbox("Município", list(por_cod), index=list(por_cod).index(config.COD_POA),
                   format_func=lambda x: por_cod[x], key="mun_sel")
nome = por_cod[cod]
ano = st.selectbox("Ano de referência", options=config.ANOS, index=config.ANOS.index(2025), key="mun_ano")

df = c.dados("ca1_cruzamento", cods=[cod], metodo=metodo,
             ano_ini=config.ANO_INICIAL, ano_fim=config.ANO_FINAL)
m = df[df.ano == ano].iloc[0]

st.subheader(f"{nome} · {ano}")
k = st.columns(4)
k[0].metric("Cobertura D1", c.fmt_pct(m.cobertura_d1), border=True)
k[1].metric("Cobertura D2", c.fmt_pct(m.cobertura_d2), border=True)
k[2].metric("Casos no ano (início do exantema)", c.fmt_num(m.casos), border=True)
k[3].metric("Incidência por 100 mil habitantes", c.fmt_num(m.incidencia_100k, 2), border=True)
for dose, v in (("D1", m.cobertura_d1), ("D2", m.cobertura_d2)):
    if pd.notna(v):
        (st.success if v >= config.META_COBERTURA else st.warning)(
            f"{dose}: {'dentro' if v >= config.META_COBERTURA else 'abaixo'} da meta de 95% em {ano} "
            f"({c.fmt_pct(v, 2)}).")
    else:
        st.info(f"{dose}: sem registro na fonte TABNET para {nome} em {ano}.")
if ano == config.ANO_FINAL:
    st.info(c.AVISOS["parcial"])

fig = go.Figure()
g = df
fig.add_scatter(x=g.ano, y=g.cobertura_d1, name="Cobertura D1", mode="lines+markers", line=dict(color=c.PALETA[0]))
fig.add_scatter(x=g.ano, y=g.cobertura_d2, name="Cobertura D2", mode="lines+markers", line=dict(color=c.PALETA[1], dash="dash"))
fig.add_bar(x=g.ano, y=g.casos, name=f"Casos em {nome} (eixo dir.)", marker_color="rgba(214,39,40,0.4)", yaxis="y2")
c.linha_meta(fig)
c.marca_ano_parcial(fig, config.ANO_INICIAL, config.ANO_FINAL)
vals = pd.concat([df.cobertura_d1, df.cobertura_d2]).dropna()
max_y = max(130.0, float(vals.max()) * 1.1 if len(vals) else 0.0)
fig.update_layout(title=f"Evolução da cobertura vacinal e dos casos de sarampo em {nome}", yaxis=dict(title="Cobertura (%)", range=[0, max_y]),
                  yaxis2=dict(title="Casos", overlaying="y", side="right", showgrid=False, rangemode="tozero"),
                  xaxis=dict(dtick=1), hovermode="x unified")
c.mostrar_figura(fig, f"ficha_{cod}", "mun_fig", 480)

tab = g.rename(columns={"ano": "Ano", "cobertura_d1": "D1 (%)", "cobertura_d2": "D2 (%)", "doses_d1": "Doses D1",
                        "doses_d2": "Doses D2", "casos": "Casos", "populacao_ibge": "População IBGE",
                        "incidencia_100k": "Incidência /100 mil", "populacao_estimada": "Pop. replicada de 2025",
                        "periodo_parcial": "Ano parcial"}).drop(columns=["cod_ibge", "nome_localidade"])
tab["Incidência /100 mil"] = tab["Incidência /100 mil"].round(2)
tab["Pop. replicada de 2025"] = tab["Pop. replicada de 2025"].map({0: "", 1: "sim"})
tab["Ano parcial"] = tab["Ano parcial"].map({0: "", 1: "sim"})
st.subheader("Série anual")
c.mostrar_tabela(tab, f"ficha_{cod}_anual", "mun_t", altura=300)

st.subheader("Doses aplicadas por mês (2023–2026)")
mens = c.dados("ca2_doses_mensais", escopo="LOCALIDADES", cods=[cod])
mens["mes"] = mens.mes.astype(int)
fig2 = px.line(mens.assign(ano=mens.ano.astype(str)), x="mes", y="total_doses", color="ano", facet_col="dose", markers=True,
               labels={"mes": "Mês", "total_doses": "Doses aplicadas", "ano": "Ano"})
fig2.update_xaxes(dtick=1)
fig2.for_each_annotation(lambda a: a.update(text=a.text.replace("dose=", "Dose ")))
c.mostrar_figura(fig2, f"ficha_{cod}_mensal", "mun_mens", 380)

# pacote Excel com todas as abas
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
    tab.to_excel(w, index=False, sheet_name="Anual")
    mens.rename(columns={"ano": "Ano", "mes": "Mês", "dose": "Dose", "total_doses": "Doses aplicadas"})[
        ["Ano", "Mês", "Dose", "Doses aplicadas"]].to_excel(w, index=False, sheet_name="Mensal")
st.download_button(f"⬇ Baixar ficha de {nome} (Excel, 2 abas)", buf.getvalue(), f"ficha_{cod}.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="mun_xlsx")
