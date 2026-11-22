import math

import plotly.graph_objects as go
import streamlit as st

import common as c
from vacina_sarampo import config

c.exige_banco()
metodo = c.metodo_atual()

st.title("Cobertura vacinal da Tríplice Viral")
c.aviso("parcial", "doses", "pop_censo", "metodo")

aba1, aba2, aba3 = st.tabs(["📈 Série histórica (CB1)", "⚖ 1ª × 2ª dose por UF (CB2)", "🎯 Municípios do RS na meta (CB4)"])

# ---------------------------------------------------------------- CB1
with aba1:
    f1, f2 = st.columns([3, 2])
    with f1:
        cods = c.seletor_localidades("Localidades (Brasil, UFs ou municípios do RS)",
                                     [config.COD_POA, config.COD_RS, config.COD_BRASIL], "cb1_locs", maximo=8)
    with f2:
        ini, fim = st.slider("Período", config.ANO_INICIAL, config.ANO_FINAL,
                             (config.ANO_INICIAL, config.ANO_FINAL), key="cb1_anos")
        doses = st.multiselect("Doses", ["D1", "D2"], default=["D1", "D2"], key="cb1_doses")
    if not cods or not doses:
        st.info("Selecione ao menos uma localidade e uma dose.")
    else:
        df = c.dados("cb1_serie_cobertura", cods=cods, metodo=metodo, ano_ini=ini, ano_fim=fim)
        fig = go.Figure()
        for i, (cod, g) in enumerate(df.groupby("cod_ibge", sort=False)):
            cor = c.PALETA[i % len(c.PALETA)]
            nome = g.nome_localidade.iloc[0]
            if "D1" in doses:
                fig.add_scatter(x=g.ano, y=g.cobertura_d1, mode="lines+markers", name=f"{nome} · D1", line=dict(color=cor))
            if "D2" in doses:
                fig.add_scatter(x=g.ano, y=g.cobertura_d2, mode="lines+markers", name=f"{nome} · D2",
                                line=dict(color=cor, dash="dash"), marker_symbol="diamond")
        c.linha_meta(fig)
        c.marca_ano_parcial(fig, ini, fim)
        fig.update_layout(title="Cobertura anual da Tríplice Viral (%) — linha cheia: D1, tracejada: D2",
                          yaxis=dict(title="Cobertura (%)", rangemode="tozero"), xaxis=dict(dtick=1),
                          hovermode="x unified")
        c.mostrar_figura(fig, "cb1_serie_cobertura", "cb1")
        tab = df.rename(columns={"cod_ibge": "Cód. IBGE", "nome_localidade": "Localidade", "ano": "Ano",
                                 "cobertura_d1": "D1 (%)", "cobertura_d2": "D2 (%)", "periodo_parcial": "Ano parcial"})
        tab["Ano parcial"] = tab["Ano parcial"].map({0: "", 1: "sim"})
        c.mostrar_tabela(tab, "cb1_serie_cobertura", "cb1_t")
    c.mostra_sql("CB1")

# ---------------------------------------------------------------- CB2
with aba2:
    st.subheader("Cobertura da 1ª e da 2ª dose por UF")
    f1, f2 = st.columns([2, 3])
    with f1:
        ano2 = st.selectbox("Ano", options=config.ANOS, index=config.ANOS.index(2025), key="cb2_ano")
        st.caption("Compare a cobertura da 1ª e da 2ª dose em cada UF no ano selecionado.")
    with f2:
        regioes = st.multiselect("Regiões", ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"],
                                 default=["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"], key="cb2_reg")
        ordem = st.radio("Ordenar por", ["Diferença D1 − D2", "D1", "D2", "UF"], horizontal=True, key="cb2_ord")
    df2 = c.dados("cb2_d1_vs_d2_por_uf", metodo=metodo, ano_ini=ano2, ano_fim=ano2)
    df2 = df2[df2.regiao.isin(regioes)]
    chave = {"Diferença D1 − D2": ("diferenca", False), "D1": ("media_d1", False),
             "D2": ("media_d2", False), "UF": ("sigla_uf", True)}[ordem]
    df2 = df2.sort_values(chave[0], ascending=chave[1])
    if df2.empty:
        st.info("Nenhuma UF nas regiões selecionadas.")
    else:
        fig = go.Figure()
        fig.add_bar(x=df2.sigla_uf, y=df2.media_d1, name="D1", marker_color=c.COR_D1)
        fig.add_bar(x=df2.sigla_uf, y=df2.media_d2, name="D2", marker_color=c.COR_D2)
        c.linha_meta(fig)
        fig.update_layout(barmode="group", title=f"Cobertura da 1ª e da 2ª dose por UF — {ano2} (%)",
                          yaxis=dict(title="Cobertura (%)"))
        c.mostrar_figura(fig, "cb2_d1_vs_d2_uf", "cb2")
        if ano2 == config.ANO_FINAL:
            st.warning(c.AVISOS["parcial"])
        tab2 = df2.rename(columns={"sigla_uf": "UF", "nome_localidade": "Nome", "regiao": "Região",
                                   "media_d1": "D1 (%)", "media_d2": "D2 (%)",
                                   "diferenca": "D1 − D2 (p.p.)"})
        c.mostrar_tabela(tab2, "cb2_d1_vs_d2_uf", "cb2_t")
    c.mostra_sql("CB2")

# ---------------------------------------------------------------- CB4
with aba3:
    st.markdown("Quantos dos **497 municípios do RS** alcançaram a meta de 95% a cada ano, e quais são eles.")
    dose = st.radio("Dose", ["D1", "D2"], horizontal=True, key="cb4_dose")
    cb4 = c.dados("cb4_municipios_na_meta", dose=dose, metodo=metodo)
    fig = go.Figure()
    fig.add_bar(x=cb4.ano, y=cb4.municipios_na_meta, name="Na meta (≥ 95%)", marker_color=c.COR_META)
    fig.add_bar(x=cb4.ano, y=cb4.municipios_abaixo_meta, name="Abaixo da meta", marker_color="#c7c7c7")
    if cb4.municipios_sem_dado.sum() > 0:
        fig.add_bar(x=cb4.ano, y=cb4.municipios_sem_dado, name="Sem dado na fonte", marker_color="#e377c2")
    c.marca_ano_parcial(fig, config.ANO_INICIAL, config.ANO_FINAL)
    fig.update_layout(barmode="stack", title=f"Municípios do RS por situação frente à meta — {dose}",
                      xaxis=dict(dtick=1), yaxis=dict(title="Municípios"))
    c.mostrar_figura(fig, "cb4_municipios_meta", "cb4")
    c.mostra_sql("CB4", dose=dose)

    st.subheader("Tabela de municípios")
    t1, t2, t3 = st.columns(3)
    ano4 = t1.selectbox("Ano", options=config.ANOS, index=config.ANOS.index(2025), key="cb4_ano")
    busca = t2.text_input("Buscar município", key="cb4_busca", placeholder="ex.: Porto Alegre")
    situacao = t3.radio("Situação", ["Todos", "Abaixo da meta", "Na meta", "Sem dado na fonte"],
                        horizontal=True, key="cb4_sit")
    col_cob = f"cobertura_{dose.lower()}"
    tab4 = c.dados("cb4_tabela_municipios", ano=ano4, metodo=metodo)
    max_val = tab4[col_cob].max()
    teto = max(150, int(math.ceil(max_val)) if max_val == max_val else 150)
    faixa = st.slider(f"Faixa de cobertura {dose} (%)", 0, teto, (0, teto), key=f"cb4_faixa_{ano4}_{dose}")
    if busca:
        tab4 = tab4[tab4.nome_localidade.str.contains(busca, case=False, na=False)]
    if situacao == "Sem dado na fonte":
        tab4 = tab4[tab4[col_cob].isna()]
    else:
        na_faixa = tab4[col_cob].between(*faixa)
        if situacao == "Todos" and faixa == (0, teto):
            tab4 = tab4[na_faixa | tab4[col_cob].isna()]
        else:
            tab4 = tab4[na_faixa]
            if situacao == "Abaixo da meta":
                tab4 = tab4[tab4[col_cob] < config.META_COBERTURA]
            elif situacao == "Na meta":
                tab4 = tab4[tab4[col_cob] >= config.META_COBERTURA]
    if ano4 == config.ANO_FINAL:
        st.warning(c.AVISOS["parcial"])
    contagem, _ = st.columns([1, 3])
    contagem.metric("Municípios no filtro", c.fmt_num(len(tab4)), border=True)
    st.caption("Coberturas acima de 100% podem ocorrer (doses em população-alvo "
               "estimada menor que a atendida) e em municípios pequenos oscilam bastante.")
    tab4 = tab4.rename(columns={"cod_ibge": "Cód. IBGE", "nome_localidade": "Município", "ano": "Ano",
                                "cobertura_d1": "D1 (%)", "cobertura_d2": "D2 (%)", "doses_d1": "Doses D1",
                                "doses_d2": "Doses D2", "periodo_parcial": "Ano parcial"}).drop(columns=["Ano parcial"])
    c.mostrar_tabela(tab4, f"municipios_rs_{ano4}", "cb4_t", altura=420, column_config={
        "D1 (%)": st.column_config.ProgressColumn("D1 (%)", min_value=0, max_value=120, format="%.1f"),
        "D2 (%)": st.column_config.ProgressColumn("D2 (%)", min_value=0, max_value=120, format="%.1f")})
    c.mostra_sql("CB4_TAB")
