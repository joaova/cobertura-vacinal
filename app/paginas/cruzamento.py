import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common as c
from vacina_sarampo import config, estatistica

c.exige_banco()
metodo = c.metodo_atual()

st.title("Cobertura vacinal × sarampo")
st.caption("Cruzamento (JOIN) das tabelas de vacinação e notificação por localidade e ano.")
c.aviso("exantema", "pop2026", "parcial", "pop_censo", "metodo")

aba1, aba2 = st.tabs(["📊 Cruzamento por localidade (CA1)", "🔬 Relação exploratória entre cobertura e incidência"])

# ------------------------------------------------------------------ CA1
with aba1:
    f1, f2, f3 = st.columns([3, 2, 2])
    with f1:
        cods = c.seletor_localidades("Localidades (até 4)", [config.COD_POA], "ca1_locs", maximo=4)
    with f2:
        ini, fim = st.slider("Período", config.ANO_INICIAL, config.ANO_FINAL,
                             (config.ANO_INICIAL, config.ANO_FINAL), key="ca1_anos")
    with f3:
        metrica = st.radio("Barras", ["Incidência por 100 mil", "Casos (absoluto)"], key="ca1_met")
        doses = st.multiselect("Linhas de cobertura", ["D1", "D2"], default=["D1", "D2"], key="ca1_doses")
    if not cods:
        st.info("Selecione ao menos uma localidade.")
    else:
        df = c.dados("ca1_cruzamento", cods=cods, metodo=metodo, ano_ini=ini, ano_fim=fim)
        col_barra = "incidencia_100k" if metrica.startswith("Incid") else "casos"
        for cod in cods:
            g = df[df.cod_ibge == cod]
            nome = g.nome_localidade.iloc[0]
            fig = go.Figure()
            fig.add_bar(x=g.ano, y=g[col_barra], name=metrica, marker_color="rgba(214,39,40,0.45)", yaxis="y2",
                        customdata=np.stack([g.casos, g.populacao_ibge, g.incidencia_100k], axis=-1),
                        hovertemplate="%{x}<br>Casos: %{customdata[0]:,.0f}<br>População: %{customdata[1]:,.0f}"
                                      "<br>Incidência: %{customdata[2]:.2f}/100 mil<extra></extra>")
            if "D1" in doses:
                fig.add_scatter(x=g.ano, y=g.cobertura_d1, name="Cobertura D1 (%)", mode="lines+markers",
                                line=dict(color=c.COR_D1))
            if "D2" in doses:
                fig.add_scatter(x=g.ano, y=g.cobertura_d2, name="Cobertura D2 (%)", mode="lines+markers",
                                line=dict(color=c.COR_D2, dash="dash"))
            c.linha_meta(fig)
            c.marca_ano_parcial(fig, ini, fim)
            vals = pd.concat([g.cobertura_d1, g.cobertura_d2]).dropna()
            max_y = max(120.0, float(vals.max()) * 1.1 if len(vals) else 0.0)
            fig.update_layout(title=f"{nome}: cobertura da Tríplice Viral e sarampo",
                              yaxis=dict(title="Cobertura (%)", range=[0, max_y]),
                              yaxis2=dict(title=metrica, overlaying="y", side="right", showgrid=False, rangemode="tozero"),
                              xaxis=dict(dtick=1), hovermode="x unified")
            c.mostrar_figura(fig, f"ca1_{cod}", f"ca1_{cod}", 440)
        tab = df.rename(columns={"cod_ibge": "Cód. IBGE", "nome_localidade": "Localidade", "ano": "Ano",
                                 "cobertura_d1": "D1 (%)", "cobertura_d2": "D2 (%)", "doses_d1": "Doses D1",
                                 "doses_d2": "Doses D2", "casos": "Casos", "populacao_ibge": "População IBGE",
                                 "incidencia_100k": "Incidência /100 mil", "populacao_estimada": "Pop. replicada de 2025",
                                 "periodo_parcial": "Ano parcial"})
        tab["Incidência /100 mil"] = tab["Incidência /100 mil"].round(2)
        for col in ("Pop. replicada de 2025", "Ano parcial"):
            tab[col] = tab[col].map({0: "", 1: "sim"})
        c.mostrar_tabela(tab, "ca1_cruzamento", "ca1_t", altura=360)
    c.mostra_sql("CA1")

# ------------------------------------------------------------------ relação exploratória
with aba2:
    st.markdown("""
Esta aba **explora** a associação entre a cobertura vacinal e a incidência de sarampo. É uma análise
**descritiva e ecológica** (unidades = localidades/anos): não estabelece causalidade e deve ser lida com as
ressalvas abaixo.
""")
    r1, r2, r3, r4 = st.columns(4)
    nivel_r = r1.radio("Unidades", ["UFs", "Municípios do RS"], key="rel_nivel")
    dose_r = r2.radio("Dose", ["D1", "D2"], horizontal=True, key="rel_dose")
    lag = r3.selectbox("Defasagem da cobertura (anos)", [0, 1, 2], key="rel_lag",
                       help="0 = cobertura e incidência no mesmo ano. 1 = cobertura do ano anterior.")
    ini_r, fim_r = r4.slider("Anos da incidência", config.ANO_INICIAL + 2, config.ANO_FINAL, (2018, 2025), key="rel_anos")
    tipo_r = "UF" if nivel_r == "UFs" else "MUNICIPIO"
    df = c.dados("relacao_cobertura_incidencia", tipo=tipo_r, dose=dose_r, lag=lag, metodo=metodo,
                 ano_ini=ini_r, ano_fim=fim_r)
    if tipo_r == "MUNICIPIO":
        pop_min = st.number_input("População mínima do município", 0, 2_000_000, 5000, step=1000, key="rel_pmin",
                                  help="Municípios pequenos geram incidências muito instáveis.")
        df = df[df.populacao_ibge >= pop_min]
    res = estatistica.spearman(df["cobertura"], df["incidencia_100k"])
    com_casos = df[df.casos > 0]
    res_c = estatistica.spearman(com_casos["cobertura"], com_casos["incidencia_100k"])

    k = st.columns(4)
    k[0].metric("Pares localidade-ano", c.fmt_num(res.n))
    k[1].metric("ρ de Spearman (todos)", c.fmt_num(res.rho, 3) if res.rho is not None else "—",
                help="Correlação de postos entre cobertura e incidência (inclui os pares sem casos).")
    k[2].metric("ρ (apenas com casos)", c.fmt_num(res_c.rho, 3) if res_c.rho is not None else "—",
                help=f"n = {res_c.n}")
    k[3].metric("p-valor (todos)", "—" if res.p_valor is None else ("< 0,001" if res.p_valor < 0.001 else c.fmt_num(res.p_valor, 3)))
    if res.rho is not None:
        ic = f" (IC95% aprox. {c.fmt_num(res.ic95[0], 2)} a {c.fmt_num(res.ic95[1], 2)})" if res.ic95 else ""
        st.markdown(f"Associação **{estatistica.descreve_forca(res.rho)}** entre a cobertura {dose_r} "
                    f"(ano t−{lag}) e a incidência (ano t){ic}.")
    else:
        st.info("Dados insuficientes para calcular a correlação.")

    if not df.empty:
        df = df.assign(ano_inc=df.ano_incidencia.astype(str))
        fig = px.scatter(df, x="cobertura", y="incidencia_100k", color="ano_inc", hover_name="nome_localidade",
                         hover_data={"casos": True, "populacao_ibge": ":,.0f", "ano_inc": False},
                         labels={"cobertura": f"Cobertura {dose_r} (%) no ano t−{lag}", "incidencia_100k": "Incidência /100 mil",
                                 "ano_inc": "Ano da incidência"}, log_y=False)
        fig.add_vline(x=config.META_COBERTURA, line_dash="dot", line_color=c.COR_META)
        fig.update_layout(title="Cobertura × incidência (cada ponto = localidade-ano)")
        c.mostrar_figura(fig, "relacao_dispersao", "rel_sc", 480)

        faixas = pd.cut(df.cobertura, [-np.inf, 70, 80, 90, 95, np.inf],
                        labels=["< 70%", "70–80%", "80–90%", "90–95%", "≥ 95%"], right=False)
        resumo = (df.assign(faixa=faixas).groupby("faixa", observed=True)
                  .agg(pares=("casos", "size"), com_casos=("casos", lambda s: int((s > 0).sum())),
                       casos=("casos", "sum"), incidencia_media=("incidencia_100k", "mean")).reset_index())
        resumo["pct_com_casos"] = (100 * resumo.com_casos / resumo.pares).round(1)
        resumo["incidencia_media"] = resumo.incidencia_media.round(2)
        fig2 = go.Figure(go.Bar(x=resumo.faixa.astype(str), y=resumo.pct_com_casos, marker_color=c.COR_CASOS,
                                text=resumo.pct_com_casos.map(lambda v: f"{v:.1f}%".replace(".", ",")),
                                textposition="outside"))
        fig2.update_layout(title="% de localidades-ano com ao menos 1 caso, por faixa de cobertura",
                           yaxis_title="% com casos", xaxis_title=f"Faixa de cobertura {dose_r}")
        c.mostrar_figura(fig2, "relacao_faixas", "rel_bar", 380)
        c.mostrar_tabela(resumo.rename(columns={"faixa": "Faixa de cobertura", "pares": "Pares", "com_casos": "Com casos",
                                                "casos": "Casos", "incidencia_media": "Incidência média /100 mil",
                                                "pct_com_casos": "% com casos"}), "relacao_faixas", "rel_t")
    with st.expander("⚠ Como interpretar (limitações)"):
        st.markdown("""
- **Ecológico, não causal:** compara localidades inteiras; não informa o estado vacinal de quem adoeceu.
- **Surtos são eventos raros e concentrados:** a maioria dos pares tem zero caso (muitos empates em postos), e um único
  surto (ex.: SP em 2019) pode dominar o resultado.
- **Importação e circulação regional:** casos podem ter sido adquiridos fora da localidade; a cobertura local não explica tudo.
- **Coortes diferentes:** a cobertura refere-se à população-alvo infantil do ano, enquanto a incidência considera todas as idades.
- **Defasagem:** a imunidade coletiva reflete coberturas acumuladas de vários anos; teste defasagens de 1 e 2 anos.
- **Municípios pequenos e 2026 parcial** distorcem taxas; use a população mínima e evite incluir 2026.
- Os p-valores desconsideram a dependência entre anos da mesma localidade e devem ser lidos apenas como referência.
""")
    c.mostra_sql("CORR", dose=dose_r)
