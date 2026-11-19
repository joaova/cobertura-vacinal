import platform
import sqlite3
from importlib import metadata

import pandas as pd
import streamlit as st

import common as c
from vacina_sarampo import config, consultas

c.exige_banco()

st.title("Dados e metodologia")
st.caption("Fontes, modelo relacional, tratamento (ETL), limitações e reprodutibilidade.")

aba = st.tabs(["🗂 Fontes e extração", "🧱 Modelo relacional", "🧹 ETL e qualidade", "⚠ Limitações", "🔁 Reprodutibilidade", "🧾 Consultas SQL"])

# ------------------------------------------------------------------ fontes
with aba[0]:
    st.markdown("""
Os arquivos foram obtidos nos portais oficiais e armazenados em `dados/`. **O ETL não baixa nada**: ele apenas lê
esses arquivos, registra o **hash SHA-256** e a data de modificação de cada um, e guarda a **data de extração**
quando a própria fonte a informa (planilhas do SEIDIGI: coluna *Data Extração*; TABNET: rodapé de cada arquivo).
""")
    resumo = c.dados("resumo_fontes").rename(columns={"fonte": "Fonte", "arquivos": "Arquivos", "linhas_lidas": "Linhas lidas",
                                                       "data_extracao": "Data de extração (informada pela fonte)"})
    c.mostrar_tabela(resumo, "resumo_fontes", "src_res")
    st.markdown("**Manifesto completo dos arquivos**")
    man = c.dados("manifesto_fontes")
    fonte = st.multiselect("Filtrar fonte", sorted(man.fonte.unique()), default=sorted(man.fonte.unique()), key="src_f")
    man = man[man.fonte.isin(fonte)].rename(columns={"fonte": "Fonte", "arquivo": "Arquivo", "conteudo": "Conteúdo",
                                                      "linhas_lidas": "Linhas lidas", "data_extracao": "Extração",
                                                      "modificado_em": "Modificado em", "sha256": "SHA-256"})
    c.mostrar_tabela(man, "manifesto_fontes", "src_man", altura=360)
    st.markdown("""
| Fonte | Conteúdo | Período |
|---|---|---|
| TABNET/DATASUS SI-PNI | Cobertura anual (%) da Tríplice Viral D1/D2 — UF e municípios do RS | 2015–2022 |
| SEIDIGI/DEMAS (MS) | Cobertura, doses e população-alvo mensais; doses mensais | 2023–2026 (até ago/out) |
| SINAN (TABNET) | Casos de sarampo por **ano de início do exantema** e por ano de notificação | 2015–2026 |
| IBGE (Base dos Dados) | População residente por UF e município | 1991–2025 |
""")

# ------------------------------------------------------------------ modelo
with aba[1]:
    st.markdown("Modelo em **3FN** (SQLite). Colunas marcadas com `[EXT]` em `schema.sql` são extensões em relação ao artigo.")
    dot = """
digraph ER {
  rankdir=LR; nodesep=0.5; ranksep=1.1;
  node [shape=plaintext, fontname="Helvetica", fontsize=16];
  edge [fontname="Helvetica", fontsize=14, arrowhead=crow, color="#444444"];
  LOCALIDADE [label=<<table border="1" cellborder="0" cellspacing="0" cellpadding="6" bgcolor="#eef5ff">
    <tr><td bgcolor="#1f77b4"><font color="white"><b>LOCALIDADE</b></font></td></tr>
    <tr><td align="left"><b>id_localidade</b> (PK)</td></tr><tr><td align="left">cod_ibge (UNIQUE)</td></tr>
    <tr><td align="left">nome_localidade</td></tr><tr><td align="left">tipo_localidade (PAIS/UF/MUNICIPIO)</td></tr>
    <tr><td align="left">sigla_uf</td></tr><tr><td align="left">regiao</td></tr></table>>];
  VACINACAO_ANUAL [label=<<table border="1" cellborder="0" cellspacing="0" cellpadding="6" bgcolor="#fff5eb">
    <tr><td bgcolor="#ff7f0e"><font color="white"><b>VACINACAO_ANUAL</b> (2015–2026)</font></td></tr>
    <tr><td align="left"><b>id_vac_anual</b> (PK)</td></tr><tr><td align="left">id_localidade (FK) / ano</td></tr>
    <tr><td align="left">cobertura_d1 / d2 · cobertura_d1_pond / d2_pond</td></tr><tr><td align="left">doses_d1 / doses_d2</td></tr>
    <tr><td align="left">populacao_alvo_d1 / d2</td></tr><tr><td align="left">atingiu_meta_d1 / d2</td></tr>
    <tr><td align="left">meses_cobertos · periodo_parcial · fonte</td></tr></table>>];
  VACINACAO_MENSAL [label=<<table border="1" cellborder="0" cellspacing="0" cellpadding="6" bgcolor="#fff5eb">
    <tr><td bgcolor="#ff7f0e"><font color="white"><b>VACINACAO_MENSAL</b> (2023–2026)</font></td></tr>
    <tr><td align="left"><b>id_vac_mensal</b> (PK)</td></tr><tr><td align="left">id_localidade (FK) / ano / mes</td></tr>
    <tr><td align="left">dose (D1/D2) · doses_aplicadas</td></tr><tr><td align="left">cobertura_mensal · doses_pop_alvo · pop_alvo</td></tr></table>>];
  NOTIFICACAO_SARAMPO [label=<<table border="1" cellborder="0" cellspacing="0" cellpadding="6" bgcolor="#fdeeee">
    <tr><td bgcolor="#d62728"><font color="white"><b>NOTIFICACAO_SARAMPO</b> (2015–2026)</font></td></tr>
    <tr><td align="left"><b>id_notificacao</b> (PK)</td></tr><tr><td align="left">id_localidade (FK) / ano (início do exantema)</td></tr>
    <tr><td align="left">casos_inicio_exantema</td></tr><tr><td align="left">populacao_ibge · incidencia_100k</td></tr>
    <tr><td align="left">populacao_estimada · periodo_parcial</td></tr></table>>];
  NOTIFICACAO_ANO_NOTIF [label=<<table border="1" cellborder="0" cellspacing="0" cellpadding="6" bgcolor="#f5f5f5">
    <tr><td bgcolor="#7f7f7f"><font color="white"><b>NOTIFICACAO_ANO_NOTIF</b> [EXT]</font></td></tr>
    <tr><td align="left">id_localidade (FK) / ano_notificacao (PK)</td></tr><tr><td align="left">casos_notificados</td></tr></table>>];
  LOCALIDADE -> VACINACAO_ANUAL [label=" possui (1:N)"];
  LOCALIDADE -> VACINACAO_MENSAL [label=" registra (1:N)"];
  LOCALIDADE -> NOTIFICACAO_SARAMPO [label=" tem (1:N)"];
  LOCALIDADE -> NOTIFICACAO_ANO_NOTIF [label=" tem (1:N)"];
}
"""
    st.graphviz_chart(dot, width="stretch")
    st.markdown("**Registros por tabela**")
    c.mostrar_tabela(c.dados("contagens_tabelas").rename(columns={"tabela": "Tabela", "registros": "Registros"}), "contagens", "mod_cnt")
    st.markdown("**Dicionário de dados** (lido do próprio banco via `PRAGMA table_info`)")
    con = c.get_con()
    linhas = []
    for t in ("LOCALIDADE", "VACINACAO_ANUAL", "VACINACAO_MENSAL", "NOTIFICACAO_SARAMPO", "NOTIFICACAO_ANO_NOTIF",
              "FONTE_ARQUIVO", "LOG_QUALIDADE"):
        for _, nome, tipo, notnull, dflt, pk in con.execute(f"PRAGMA table_info({t})"):
            linhas.append((t, nome, tipo, "PK" if pk else ("NOT NULL" if notnull else "NULL"), dflt))
    dic = pd.DataFrame(linhas, columns=["Tabela", "Atributo", "Tipo", "Restrição", "Padrão"])
    c.mostrar_tabela(dic, "dicionario_dados", "mod_dic", altura=360)

# ------------------------------------------------------------------ ETL
with aba[2]:
    st.markdown("""
**Etapas do pipeline** (`python -m vacina_sarampo.etl`):
1. **Cobertura 2015–2022 (CSV latin1, `;`, vírgula decimal):** separa código e nome, lê a linha *Total* como Brasil (arquivos de UF) ou RS.
2. **Cobertura/doses 2023–2026 (XLSX com 3 linhas de cabeçalho mesclado):** reorganiza os trios *Cobertura / Doses / População* de cada mês; converte proporção em %.
3. **Doses mensais (XLSX):** converte `-` em 0, remove separador de milhar, completa com 0 os municípios ausentes e descarta a linha de UF ignorada.
4. **SINAN por ano de início do exantema:** localiza o cabeçalho, “derrete” a matriz de anos, descarta anos < 2015 e *Em branco/ign*, converte `-` em 0 e completa os municípios sem casos.
5. **População IBGE:** remove linhas sem UF/município/população; trunca o código municipal de 7 para 6 dígitos; Brasil = soma das UFs; 2026 replica 2025.
6. **Cobertura anual 2023–2026:** média das coberturas mensais (padrão) e razão das somas (alternativa); `atingiu_meta` = cobertura ≥ 95%.
7. **Incidência:** casos ÷ população × 100.000 (armazenada com 4 casas).
8. **Validação:** integridade referencial (`PRAGMA foreign_key_check`) e testes automatizados contra os valores publicados no artigo.
""")
    c.mostrar_tabela(c.dados("log_qualidade").rename(columns={"etapa": "Etapa", "descricao": "Ocorrência", "valor": "Valor"}),
                     "log_qualidade_etl", "etl_log", altura=300)
    st.markdown("**Casos por critério de data** — ano de início do exantema × ano de notificação (corte preliminar), Brasil")
    cmp_ = c.dados("comparacao_criterios_casos", cod=config.COD_BRASIL).rename(
        columns={"ano": "Ano", "casos_exantema": "Por início do exantema", "casos_ano_notificacao": "Por ano de notificação"})
    c.mostrar_tabela(cmp_, "criterios_data_brasil", "etl_cmp", altura=300)
    st.caption("As diferenças refletem o atraso de registro e a revisão dos dados; por isso o critério do exantema é o usado nas análises.")

# ------------------------------------------------------------------ limitações
with aba[3]:
    st.markdown("### Particularidades e limitações das fontes")
    for k in ("pop2026", "parcial", "doses", "exantema", "pop_censo", "pequenos", "metodo"):
        st.markdown(f"- {c.AVISOS[k]}")
    st.markdown("""
- **Escopo geográfico:** só o Rio Grande do Sul tem detalhamento municipal; as demais UFs estão agregadas.
- **Cobertura > 100%:** ocorre quando o numerador (doses) supera a população-alvo estimada; é mantida como informada pelas fontes.
- **Qualidade do SINAN:** os dados "não foram qualificados" (podem conter inconsistências e duplicidades) e estão sujeitos à revisão.
- **Total do Brasil:** soma das UFs + casos com UF de residência ignorada/exterior (a linha *Total* do arquivo UF equivale a esse critério).
- **Relação cobertura × incidência:** análise exploratória e ecológica; não indica causalidade.
""")

# ------------------------------------------------------------------ reprodutibilidade
with aba[4]:
    pacotes = ["pandas", "numpy", "openpyxl", "xlsxwriter", "plotly", "streamlit", "scipy", "pytest"]
    vers = []
    for p in pacotes:
        try:
            vers.append((p, metadata.version(p)))
        except metadata.PackageNotFoundError:
            vers.append((p, "não instalado"))
    vers = [("Python", platform.python_version()), ("SQLite (biblioteca)", sqlite3.sqlite_version)] + vers
    st.markdown("Versões **em uso nesta execução** (as mínimas/fixadas estão em `requirements.txt`):")
    c.mostrar_tabela(pd.DataFrame(vers, columns=["Componente", "Versão"]), "versoes_ambiente", "rep_v")
    st.code("""python -m venv .venv && .venv\\Scripts\\activate     # Windows
pip install -r requirements.txt
python -m vacina_sarampo.etl                         # gera db/projeto_sarampo_vacina.db
pytest                                               # valida o ETL e as consultas
streamlit run app/main.py                            # abre a interface""", language="bash")

# ------------------------------------------------------------------ SQL
with aba[5]:
    st.markdown("Consultas usadas pela interface (o método de cobertura escolhido na barra lateral é refletido no SQL).")
    nomes = {"CB1": "CB1 – Série histórica da cobertura", "CB2": "CB2 – D1 × D2 por UF", "CB3": "CB3 – Casos e incidência",
             "CB4": "CB4 – Municípios na meta", "CB4_TAB": "CB4 – Tabela de municípios", "CA1": "CA1 – Cruzamento cobertura × casos",
             "CA2": "CA2 – Doses mensais", "CORR": "Relação cobertura × incidência"}
    for k, rot in nomes.items():
        with st.expander(rot):
            st.code(consultas.sql_formatado(k, c.metodo_atual(), dose="D1"), language="sql")
