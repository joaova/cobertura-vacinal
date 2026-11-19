import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common as c

c.exige_banco()

st.title("Doses mensais da Tríplice Viral (2023–2026)")
st.caption("Sazonalidade e comparação **ano a ano**: identifique meses de campanha e de baixa procura.")
with st.expander("⚠ Particularidades das fontes desta análise"):
    st.markdown("""
- As doses mensais vêm das planilhas `triplice_*` do SEIDIGI/DEMAS e contam **todas as doses aplicadas no mês**
  (qualquer idade), por isso diferem das doses usadas no numerador da cobertura (população-alvo infantil).
- **2026 vai até outubro** (mês de extração: 23/10/2026): o último mês pode estar incompleto por atraso de registro.
- Meses sem aplicação (traço `-` na fonte) foram carregados como **0**.
- Doses mensais por município existem apenas para o **RS**; as demais UFs aparecem agregadas por UF.
""")

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
ESCOPOS = {"Municípios do RS (soma dos 497)": "MUNICIPIO_RS", "UFs (soma das 27)": "UF",
           "Localidades específicas": "LOCALIDADES"}

f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
esc_rot = f1.radio("Escopo", list(ESCOPOS), key="ca2_esc")
escopo = ESCOPOS[esc_rot]
anos = f2.multiselect("Anos", [2023, 2024, 2025, 2026], default=[2023, 2024, 2025, 2026], key="ca2_anos")
doses = f3.multiselect("Doses", ["D1", "D2"], default=["D1", "D2"], key="ca2_doses")
met = f4.radio("Métrica", ["Total de doses", "Média por localidade"], key="ca2_met")
cods = None
if escopo == "LOCALIDADES":
    cods = c.seletor_localidades("Localidades (UFs ou municípios do RS)", ["431490"], "ca2_locs", tipos=("UF", "MUNICIPIO"))
    if not cods:
        st.info("Selecione ao menos uma localidade.")
        st.stop()
if not anos or not doses:
    st.info("Selecione ao menos um ano e uma dose.")
    st.stop()

df = c.dados("ca2_doses_mensais", escopo=escopo, cods=cods, anos=sorted(anos), doses=sorted(doses))
col = "total_doses" if met == "Total de doses" else "media_por_localidade"
df["mes_nome"] = df.mes.map(lambda m: MESES[m - 1])
df["ano_s"] = df.ano.astype(str)

fig = px.line(df, x="mes_nome", y=col, color="ano_s", facet_col="dose", markers=True,
              category_orders={"mes_nome": MESES, "dose": ["D1", "D2"]},
              labels={"mes_nome": "Mês", col: met, "ano_s": "Ano", "dose": "Dose"})
fig.update_layout(title=f"{met} por mês — {esc_rot} (uma linha por ano)", hovermode="x unified")
fig.for_each_annotation(lambda a: a.update(text=a.text.replace("dose=", "Dose ")))
c.mostrar_figura(fig, "ca2_doses_mensais", "ca2_lin", 460)

st.subheader("Mapa de calor ano × mês")
dose_h = st.radio("Dose", sorted(doses), horizontal=True, key="ca2_dose_heat")
h = df[df.dose == dose_h].pivot(index="ano", columns="mes", values=col).reindex(columns=range(1, 13))
fig_h = go.Figure(go.Heatmap(z=h.values, x=MESES, y=[str(a) for a in h.index], colorscale="Blues",
                             hovertemplate="%{y} / %{x}: %{z:,.0f}<extra></extra>", colorbar=dict(title=met)))
fig_h.update_layout(title=f"{met} — {dose_h}", yaxis=dict(autorange="reversed"))
c.mostrar_figura(fig_h, "ca2_heatmap", "ca2_heat", 300)

st.subheader("Comparação com um ano-base")
base_ano = st.selectbox("Ano-base", sorted(anos), index=0, key="ca2_base")
pv = df[df.dose == dose_h].pivot(index="mes", columns="ano", values=col)
if base_ano in pv.columns:
    var = (pv.div(pv[base_ano], axis=0) - 1) * 100
    var = var.drop(columns=[base_ano]).replace([float("inf"), float("-inf")], pd.NA)
    var.index = [MESES[m - 1] for m in var.index]
    if var.empty:
        st.caption("Selecione outro ano além do ano-base para ver variações.")
    else:
        var.columns = [f"{a} vs {base_ano} (%)" for a in var.columns]
        st.caption("Variação percentual da métrica em cada mês em relação ao mesmo mês do ano-base.")
        out = var.round(1).reset_index(names="Mês")
        c.mostrar_tabela(out, "ca2_variacao_ano_base", "ca2_var")

st.subheader("Tabela completa")
tab = df.rename(columns={"ano": "Ano", "mes": "Mês", "dose": "Dose", "total_doses": "Total de doses",
                         "media_por_localidade": "Média por localidade", "n_localidades": "Nº de localidades"}
                ).drop(columns=["mes_nome", "ano_s"])
c.mostrar_tabela(tab, "ca2_doses_mensais", "ca2_t", altura=320)
sql_escopo = {
    "MUNICIPIO_RS": "l.tipo_localidade = 'MUNICIPIO' AND l.sigla_uf = 'RS'",
    "UF": "l.tipo_localidade = 'UF'",
    "LOCALIDADES": f"l.cod_ibge IN ({', '.join(repr(x) for x in (cods or []))})",
}[escopo]
c.mostra_sql("CA2", escopo=sql_escopo, anos=", ".join(map(str, sorted(anos))),
             doses=", ".join(repr(d) for d in sorted(doses)))
