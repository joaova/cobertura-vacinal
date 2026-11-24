import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common as c
from vacina_sarampo import config, estatistica
from vacina_sarampo.contexto_epidemiologico import CONTEXTOS, DATA_CONSULTA

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
Compare a incidência de sarampo entre localidades **abaixo da meta de cobertura de 95%** e localidades
com **95% ou mais**, no ano selecionado. Esta comparação é descritiva e não demonstra causalidade.
""")
    r1, r2, r3 = st.columns(3)
    nivel_r = r1.radio("Recorte geográfico", ["Brasil por UF", "RS por município"], key="rel_nivel")
    dose_r = r2.radio("Dose", ["D1", "D2"], horizontal=True, key="rel_dose")
    ano_r = r3.selectbox("Ano dos casos", config.ANOS, index=config.ANOS.index(2025), key="rel_ano")
    tipo_r = "UF" if nivel_r == "Brasil por UF" else "MUNICIPIO"
    with st.expander("Opções da comparação"):
        lag = st.selectbox("Defasagem da cobertura (anos)",
                           [d for d in (0, 1, 2) if ano_r - d >= config.ANO_INICIAL], key="rel_lag",
                           help="0 = cobertura e casos no mesmo ano. 1 ou 2 = cobertura de um ou dois anos antes.")
        pop_min = 0
        if tipo_r == "MUNICIPIO":
            pop_min = st.number_input("População mínima do município", 0, 2_000_000, 5000, step=1000, key="rel_pmin",
                                      help="Restringe a comparação aos municípios com pelo menos esta população.")
    ano_cobertura = ano_r - lag
    df = c.dados("relacao_cobertura_incidencia", tipo=tipo_r, dose=dose_r, lag=lag, metodo=metodo,
                 ano_ini=ano_r, ano_fim=ano_r)
    df = df.dropna(subset=["cobertura", "casos", "populacao_ibge"])
    df = df[(df.populacao_ibge > 0) & (df.populacao_ibge >= pop_min)]
    st.caption(f"Cobertura {dose_r} de {ano_cobertura} e casos por início do exantema em {ano_r}. "
               "São consideradas apenas localidades com cobertura, casos e população válida informados.")
    if ano_r == config.ANO_FINAL:
        st.warning(c.AVISOS["parcial"])

    if df.empty:
        st.info("Nenhuma localidade com dados válidos para os filtros selecionados.")
    else:
        resumo = estatistica.resumo_por_meta(df, config.META_COBERTURA)
        grupos = resumo.situacao.tolist()
        cores = {grupos[0]: c.COR_CASOS, grupos[1]: c.COR_META}
        k = st.columns(3)
        k[0].metric("Localidades analisadas", c.fmt_num(len(df)), border=True)
        k[1].metric("Casos no ano", c.fmt_num(df.casos.sum()), border=True)
        k[2].metric("Localidades com casos", c.fmt_num((df.casos > 0).sum()), border=True)

        st.subheader(f"Incidência por situação de cobertura · {ano_r}")
        st.caption("Incidência do grupo = total de casos ÷ população total × 100 mil. "
                   "O cálculo considera o tamanho da população de cada localidade.")
        if df.casos.sum() == 0:
            st.info(f"Nenhum caso de sarampo registrado nas localidades selecionadas em {ano_r}. "
                    "Não há variação de incidência para avaliar sua relação com a cobertura neste recorte.")
        else:
            fig = go.Figure(go.Bar(
                x=resumo.situacao, y=resumo.incidencia_100k,
                marker_color=[cores[g] for g in grupos],
                text=[c.fmt_num(v, 2) if pd.notna(v) else "" for v in resumo.incidencia_100k],
                textposition="outside", cliponaxis=False,
                customdata=resumo[["localidades", "populacao", "casos", "localidades_com_casos"]].to_numpy(),
                hovertemplate="%{x}<br>Incidência: %{y:.2f}/100 mil<br>Localidades: %{customdata[0]:,.0f}"
                              "<br>População: %{customdata[1]:,.0f}<br>Casos: %{customdata[2]:,.0f}"
                              "<br>Localidades com casos: %{customdata[3]:,.0f}<extra></extra>"))
            fig.update_layout(title=f"Casos por 100 mil habitantes, segundo a cobertura {dose_r} de {ano_cobertura}",
                              xaxis_title="Situação da cobertura", yaxis_title="Casos por 100 mil habitantes",
                              yaxis=dict(rangemode="tozero"), showlegend=False)
            c.mostrar_figura(fig, f"relacao_por_meta_{ano_r}_{dose_r}_cob{ano_cobertura}", "rel_bar", 400)
        sem_localidades = resumo.loc[resumo.localidades == 0, "situacao"].tolist()
        if sem_localidades:
            st.caption(f"Sem localidades no grupo: {', '.join(sem_localidades)}. "
                       "A incidência desse grupo não pode ser calculada; não é possível comparar os dois grupos.")

        st.subheader("Dados dos grupos")
        tabela = resumo.rename(columns={"situacao": "Situação da cobertura", "localidades": "Localidades",
                                         "populacao": "População", "casos": "Casos",
                                         "localidades_com_casos": "Localidades com casos",
                                         "incidencia_100k": "Incidência /100 mil"})
        tabela["Incidência /100 mil"] = tabela["Incidência /100 mil"].round(2)
        c.mostrar_tabela(tabela, f"relacao_por_meta_{ano_r}_{dose_r}_cob{ano_cobertura}", "rel_t")

        with st.expander("Detalhes estatísticos"):
            res = estatistica.spearman(df.cobertura, df.incidencia_100k)
            com_casos = df[df.casos > 0]
            res_c = estatistica.spearman(com_casos.cobertura, com_casos.incidencia_100k)
            k = st.columns(4)
            k[0].metric("Localidades com dados para correlação", c.fmt_num(res.n), border=True)
            k[1].metric("ρ de Spearman (todos)", c.fmt_num(res.rho, 3) if res.rho is not None else "—", border=True)
            k[2].metric("ρ (apenas com casos)", c.fmt_num(res_c.rho, 3) if res_c.rho is not None else "—",
                        help=f"n = {res_c.n}; considera somente localidades com ao menos um caso.", border=True)
            k[3].metric("p-valor (todos)", "—" if res.p_valor is None else (
                "< 0,001" if res.p_valor < 0.001 else c.fmt_num(res.p_valor, 3)), border=True)
            if res.rho is None:
                st.info("Dados insuficientes ou sem variação para calcular a correlação.")
            elif res.ic95:
                st.caption(f"IC95% aproximado de Spearman: {c.fmt_num(res.ic95[0], 2)} a "
                           f"{c.fmt_num(res.ic95[1], 2)}.")
            if df.casos.sum() > 0:
                pontos = df.assign(situacao=np.where(df.cobertura < config.META_COBERTURA, grupos[0], grupos[1]))
                fig = px.scatter(pontos, x="cobertura", y="incidencia_100k", color="situacao",
                                 color_discrete_map=cores, category_orders={"situacao": grupos},
                                 hover_name="nome_localidade", hover_data={"casos": True, "populacao_ibge": ":,.0f"},
                                 labels={"cobertura": f"Cobertura {dose_r} em {ano_cobertura} (%)",
                                         "incidencia_100k": f"Incidência em {ano_r} /100 mil",
                                         "situacao": "Situação da cobertura"})
                fig.add_vline(x=config.META_COBERTURA, line_dash="dot", line_color=c.COR_META)
                fig.update_layout(title="Cobertura × incidência (cada ponto = uma localidade)")
                c.mostrar_figura(fig, "relacao_dispersao", "rel_sc", 480)

    st.subheader(f"{'Municípios do RS' if tipo_r == 'MUNICIPIO' else 'UFs'} com casos em {ano_r}")
    casos_locais = c.dados("cb3_ranking_casos", tipo=tipo_r, ano_ini=ano_r, ano_fim=ano_r, min_casos=1)
    if casos_locais.empty:
        st.info(f"Nenhuma localidade com casos registrada na base para este recorte em {ano_r}.")
    else:
        coberturas = c.dados("cb1_serie_cobertura", cods=casos_locais.cod_ibge.tolist(), metodo=metodo,
                             ano_ini=ano_cobertura, ano_fim=ano_cobertura)
        casos_locais = casos_locais.merge(coberturas[["cod_ibge", "cobertura_d1", "cobertura_d2"]],
                                          on="cod_ibge", how="left")
        casos_locais["Situação da cobertura selecionada"] = "Sem dado de cobertura"
        cobertura_dose = casos_locais[f"cobertura_{dose_r.lower()}"]
        casos_locais.loc[cobertura_dose < config.META_COBERTURA, "Situação da cobertura selecionada"] = "Abaixo de 95%"
        casos_locais.loc[cobertura_dose >= config.META_COBERTURA, "Situação da cobertura selecionada"] = "95% ou mais"
        casos_locais["Na comparação dos grupos"] = casos_locais.cod_ibge.isin(df.cod_ibge).map({True: "Sim", False: "Não"})
        casos_locais["Ano da cobertura"] = ano_cobertura
        casos_locais = casos_locais.sort_values(["casos_inicio_exantema", "nome_localidade"], ascending=[False, True])
        tabela_casos = casos_locais.rename(columns={
            "nome_localidade": "Município" if tipo_r == "MUNICIPIO" else "Estado / DF", "sigla_uf": "UF",
            "ano": "Ano dos casos", "casos_inicio_exantema": "Casos", "incidencia_100k": "Incidência /100 mil",
            "populacao_ibge": "População", "cobertura_d1": "D1 (%)", "cobertura_d2": "D2 (%)",
        })
        tabela_casos["Incidência /100 mil"] = tabela_casos["Incidência /100 mil"].round(2)
        tabela_casos = tabela_casos[["Município" if tipo_r == "MUNICIPIO" else "Estado / DF", "UF", "Ano dos casos",
                                     "Casos", "Incidência /100 mil", "População", "Ano da cobertura", "D1 (%)", "D2 (%)",
                                     "Situação da cobertura selecionada", "Na comparação dos grupos"]]
        st.caption(f"Situação calculada para {dose_r} em {ano_cobertura}. A lista inclui todas as localidades "
                   "com casos no recorte geográfico, inclusive aquelas sem cobertura informada ou fora do filtro "
                   "de população mínima; a última coluna indica quais participam da comparação acima.")
        c.mostrar_tabela(tabela_casos, f"localidades_com_casos_{tipo_r}_{ano_r}_{dose_r}_cob{ano_cobertura}", "rel_casos_t",
                         column_config={"Ano dos casos": None, "Ano da cobertura": None})
    if tipo_r == "UF":
        st.caption("Para consultar cidades, selecione ‘RS por município’. A base possui detalhamento municipal "
                   "apenas para o Rio Grande do Sul; nas demais UFs, os registros estão agregados por estado.")

    contexto = CONTEXTOS[ano_r]
    st.subheader(f"Contexto epidemiológico de {ano_r} · Ministério da Saúde")
    st.markdown(f"**{contexto.titulo}**")
    fontes = " · ".join(f"[{f.titulo}]({f.url})" for f in contexto.fontes)
    st.markdown(f"{contexto.resumo} Fontes: {fontes}.")
    st.caption(f"Contexto nacional, com eventos investigados nas fontes citadas. Não determina a origem "
               f"de cada caso da tabela nem muda com os filtros de dose, defasagem ou população. "
               f"Fontes consultadas em {DATA_CONSULTA}.")
    with st.expander("Comparar os totais do painel e do Ministério da Saúde"):
        brasil = c.dados("ca1_cruzamento", cods=[config.COD_BRASIL], metodo=metodo, ano_ini=ano_r, ano_fim=ano_r)
        total_painel = int(brasil.casos.sum())
        st.caption(f"Brasil · {ano_r}")
        painel, ministerio = st.columns(2)
        painel.metric("Casos no banco do projeto", c.fmt_num(total_painel), border=True)
        ministerio.metric("Casos confirmados · Ministério da Saúde", c.fmt_num(contexto.total_confirmado_brasil), border=True)
        st.markdown(f"[Balanço do Ministério da Saúde]({contexto.fonte_total}) · {contexto.recorte_total}.")
        if total_painel != contexto.total_confirmado_brasil:
            st.info("Os totais divergem e ainda não foram reconciliados. A tabela usa os arquivos do projeto; "
                    "o contexto cita o balanço oficial. A diferença, por si só, não permite concluir sua causa.")
        if ano_r == config.ANO_FINAL:
            st.caption("Os casos de 2026 do projeto têm extração até setembro; o balanço citado foi publicado em 17 de novembro. "
                       "Os dois recortes são parciais e têm datas de corte diferentes.")

    with st.expander("⚠ Como interpretar (limitações)"):
        st.markdown("""
- **Ecológico, não causal:** compara localidades inteiras; não informa o estado vacinal de quem adoeceu.
- **Surtos são eventos raros e concentrados:** a maioria dos pares tem zero caso (muitos empates em postos), e um único
  surto (ex.: SP em 2019) pode dominar o resultado.
- **Importação e circulação regional:** casos podem ter sido adquiridos fora da localidade; a cobertura local não explica tudo.
- **Coortes diferentes:** a cobertura refere-se à população-alvo infantil do ano, enquanto a incidência considera todas as idades.
- **Defasagem:** a imunidade coletiva reflete coberturas acumuladas de vários anos; teste defasagens de 1 e 2 anos.
- **Municípios pequenos e 2026 parcial** distorcem taxas; use a população mínima e evite incluir 2026.
- Os grupos podem ter populações e perfis diferentes. As taxas não são ajustadas por idade ou outros fatores.
- P-valores e intervalos são exploratórios e não ajustam a dependência espacial entre localidades.
""")
    c.mostra_sql("CORR", dose=dose_r)
