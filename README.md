# Cobertura vacinal da Tríplice Viral × sarampo — versão inicial

Plataforma interativa (Python + SQLite + Streamlit/Plotly) que unifica bases públicas de **imunização**
(TABNET/SI-PNI 2015–2022 e SEIDIGI/DEMAS 2023–2026), **vigilância** (SINAN, casos de sarampo por ano de início do
exantema) e **população** (IBGE) para acompanhar a cobertura da 1ª e 2ª doses, as doses aplicadas e a incidência de
sarampo no **Brasil, nas 27 UFs e nos 497 municípios do RS** (com destaque para Porto Alegre).
Implementa o que foi definido no artigo anteprojeto (`Entregas/artigo_anteprojeto.pdf`) e incorpora as sugestões
das cinco avaliações recebidas (ver [Avaliações → o que foi feito](#avaliações--o-que-foi-feito)).

## Como executar

O [artigo atualizado em formato SBC](Entregas/artigo_atualizado/artigo.pdf) descreve a implementação atual,
os resultados e as limitações metodológicas. O [fonte LaTeX](Entregas/artigo_atualizado/artigo.tex),
as referências verificadas e os dados das figuras estão na mesma pasta.

Os [slides de apresentação do progresso](Entregas/apresentacao_progresso/apresentacao_progresso.pdf)
também estão disponíveis em [PowerPoint editável](Entregas/apresentacao_progresso/apresentacao_progresso.pptx),
com [roteiro de fala](Entregas/apresentacao_progresso/roteiro_apresentacao.txt) para cerca de 12–15 minutos.

A [apresentação revisada do dashboard no Google Slides](https://docs.google.com/presentation/d/12mHlmvi2--IQCYzjJJPI0kV1SruTafBgSL8rPvp1Fls/edit)
está na pasta ProjetoBD do Drive, com 21 slides. Essa versão amplia a introdução sobre vacinação,
explica as tecnologias e o fluxo dos dados e apresenta as páginas, os filtros e as exportações do aplicativo. As cópias em
[PDF](Entregas/apresentacao_progresso/apresentacao_dashboard_revisada.pdf) e
[PPTX](Entregas/apresentacao_progresso/apresentacao_dashboard_revisada.pptx), com
[roteiro revisado](Entregas/apresentacao_progresso/roteiro_dashboard_revisado.txt), estão no repositório.

Requer **Python 3.11+** (testado com 3.12).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python -m vacina_sarampo.etl      # ETL: lê dados/ e gera db/projeto_sarampo_vacina.db (~15 s)
streamlit run app/main.py         # interface em http://localhost:8501
pytest                            # testes (ETL, consultas SQL, interface)
```

O banco `db/projeto_sarampo_vacina.db` é gerado a partir de `dados/` e não é versionado.

## Estrutura

```
dados/                      arquivos brutos (70 arquivos de 4 fontes) — não alterados
Entregas/                   artigo anteprojeto, avaliações e templates
vacina_sarampo/
  config.py                 caminhos, constantes (meta 95%, UFs, regiões)
  schema.sql                esquema relacional em 3FN (+ visão VW_CRUZAMENTO)
  etl/extratores.py         leitura/limpeza de cada tipo de arquivo (CSV latin1, XLSX com cabeçalho mesclado, matrizes TABNET)
  etl/carga.py              transformação, cálculo da cobertura/incidência e carga no SQLite
  consultas.py              consultas SQL CB1–CB4, CA1–CA2 e extensões
  estatistica.py            correlação de Spearman (análise exploratória)
app/
  main.py                   navegação e configuração global
  common.py                 acesso a dados com cache, exportação, avisos metodológicos
  paginas/                  Visão geral · Cobertura · Casos e incidência · Cobertura × sarampo ·
                            Ficha do município (UBS) · Dados e metodologia
tests/                      pytest (valores de referência = Tabelas 1 e 4 do artigo)
```

## O que a interface oferece

| Página | Conteúdo | Origem no artigo |
|---|---|---|
| Visão geral | Indicadores do ano escolhido, evolução D1/D2 × casos, leitura rápida | Tabela 4 |
| Cobertura vacinal | Série histórica de qualquer localidade (CB1), D1 × D2 por UF no ano selecionado (CB2), municípios do RS dentro/fora da meta + tabela filtrável (CB4) | CB1, CB2, CB4 |
| Casos e incidência | Ranking de municípios/UFs por incidência ou casos, ano específico ou acumulado, filtros de população mínima e nº de casos (CB3) | CB3 |
| Cobertura × sarampo | Gráfico de eixo duplo por localidade (CA1), incidência por situação de cobertura, localidades com casos e contexto anual com fontes do Ministério da Saúde | CA1 |
| Ficha do município | Resumo para as UBS: cobertura, casos, incidência, séries anuais e gráfico de doses mensais por ano; download em Excel | PET-Saúde Digital / CA2 |
| Dados e metodologia | Manifesto das fontes (hash, data de extração), diagrama ER, dicionário, log de qualidade, limitações, versões, SQL | Seções 2–4 |

Todas as tabelas têm botões **CSV/Excel** e todos os gráficos têm **PNG** (ícone da câmera) e **HTML interativo**.

A página independente de doses mensais foi removida; o gráfico mensal permanece na ficha do município.
O cache acompanha caminho, identificação do arquivo, modificação em nanossegundos e tamanho do banco.
Após uma atualização ou reconstrução pelo ETL, consultas, catálogo de localidades e conexão SQLite são renovados.

Na relação exploratória, a lista de localidades com casos inclui também aquelas excluídas da comparação por
população mínima ou falta de cobertura, com indicação na tabela. O contexto de cada ano (2015–2026) resume
publicações do Ministério da Saúde consultadas em 22/11/2026, com links e datas dos balanços. Os totais oficiais
e os do banco são apresentados separadamente quando divergem; essas diferenças ainda não foram reconciliadas.

## Modelo de dados

Quatro tabelas do artigo — `LOCALIDADE`, `VACINACAO_ANUAL`, `VACINACAO_MENSAL`, `NOTIFICACAO_SARAMPO` — mais
`NOTIFICACAO_ANO_NOTIF` (casos por ano de notificação), `FONTE_ARQUIVO` (manifesto) e `LOG_QUALIDADE`. Resultado da carga:
**525** localidades · **6.300** registros anuais de vacinação e de notificação · **48.208** registros mensais · **70** arquivos.
Estes números e a **Tabela 4 inteira do artigo** (Brasil, RS e Porto Alegre, 2015–2026) são reproduzidos exatamente e
verificados por testes automatizados.

Desvios/extensões em relação ao artigo (marcados `[EXT]` em `schema.sql`):

- `populacao_alvo` desdobrada em `populacao_alvo_d1/d2` (os denominadores de D1 e D2 diferem nas planilhas do SEIDIGI).
- `cobertura_d1_pond/d2_pond`: método alternativo de cobertura anual 2023–2026 (veja abaixo).
- Colunas de sinalização: `periodo_parcial`, `meses_cobertos`, `populacao_estimada`, `fonte`.
- `VACINACAO_MENSAL` ganhou `cobertura_mensal`, `doses_pop_alvo`, `pop_alvo`; `LOCALIDADE` ganhou `regiao`.

### Decisões de tratamento dos dados

- **Cobertura 2023–2026.** O painel entrega apenas valores mensais (e usa a sentinela `1e-06` nos 3.144 registros mensais em que `pop_alvo = 0`). O padrão do projeto (que reproduz a Tabela 4 do artigo) é a
  **média simples das coberturas mensais**. Como a média de razões dá o mesmo peso a meses de populações-alvo diferentes (e pode
  distorcer municípios pequenos), a interface permite alternar (barra lateral) para **Σ doses ÷ Σ população-alvo**. Em 2015–2022 os dois coincidem.
- **Municípios ausentes no TABNET:** 4 CSVs anuais do RS omitem 1 município cada (2015, 2016, 2021, 2022); a cobertura é mantida como `NULL` (não inventada como 0), registrada em `LOG_QUALIDADE` e destacada na consulta CB4 (*Sem dado na fonte*).
- **Total do RS** aparece tanto nos arquivos de UF quanto nos de município; é carregado uma vez (e o ETL registra que as cópias não divergem).
- **Brasil (casos)** = 27 UFs + casos com UF de residência ignorada/exterior (reproduz 21.797 casos em 2019).
- **Municípios sem linha** nos arquivos de casos/doses recebem **0**; `-` vira 0; vírgula de milhar é removida.
- **Código IBGE:** 7 → 6 dígitos nos municípios (população); Brasil = soma das UFs.
- A linha de população sem UF (2025, 5.877 hab.) e 535 linhas municipais sem população são descartadas e registradas em `LOG_QUALIDADE`.

## Avaliações → o que foi feito

| Sugestão recebida | Tratamento na versão inicial |
|---|---|
| (1) Sinalizar particularidades das fontes na interface | Caixas “⚠ Particularidades das fontes” em todas as páginas (2026 parcial, população de 2026 = 2025, sem doses absolutas em 2015–2022, Censo 2022, municípios pequenos) e marcações no gráfico (faixa cinza de 2026 parcial) e nas tabelas |
| (1) Exportar tabelas/gráficos para os preceptores | CSV/Excel em todas as tabelas, PNG/HTML nos gráficos e ficha do município em Excel |
| (2) Estimar doses 2015–2022 | **Não implementado**: exigiria supor a população-alvo de anos sem esse dado. Fica como evolução (ver abaixo) |
| (2) Expandir detalhe municipal a outras UFs | Os dados atuais só trazem municípios do RS; o ETL já usa `UF_MUNICIPAL` em `config.py`, mas precisa de novos arquivos |
| (2) Análise estatística entre cobertura e incidência | Aba “Relação exploratória”: comparação anual abaixo de 95% × 95% ou mais, incidência calculada por total de casos ÷ população total, tabela dos grupos, defasagem de 0–2 anos e detalhes com dispersão, Spearman, p-valor e IC aproximado |
| (3) Versões das bibliotecas | `requirements.txt` (fixado), `requirements-lock.txt` e tabela de versões na página *Dados e metodologia* |
| (3) Como/quando os dados foram obtidos | Tabela `FONTE_ARQUIVO`: arquivo, linhas, SHA-256, data de modificação e data de extração informada pela fonte (SEIDIGI: 23/10/2026; TABNET: set/2026) |
| (3) “Exantema” ≠ “sintomas” | Terminologia “ano de início do exantema” em toda a interface e aviso explicativo |
| (3) Limitação da população 2025 → 2026 e dados incompletos de 2026 | Avisos, coluna `populacao_estimada`/`periodo_parcial` e marcação visual |
| (3) “Correlação” no título | A interface usa “cruzamento” e “relação”; a análise estatística é rotulada como exploratória e ecológica |
| (3) Figura 1 pequena | O diagrama ER está em tela cheia na aba *Modelo relacional* |
| (4) Doses mensais separadas por ano | Gráfico na *Ficha do município*: uma linha por ano, separado por dose |
| (5) Vários filtros | Filtros de localidades, período, dose, região, população mínima, nº de casos, busca por nome, faixa de cobertura, situação frente à meta e escopo |

## Limitações conhecidas / próximos passos

- Só o RS tem detalhamento municipal; doses absolutas só existem a partir de 2023.
- 2026 é parcial (cobertura até ago/2026, doses até out/2026, casos até set/2026). A população de 2026 replica 2025.
- A análise cobertura × incidência é descritiva/ecológica, sem ajuste de dependência entre anos; surtos concentrados (SP/2019) pesam muito.
- Evoluções: estimativa (rotulada) de doses 2015–2022, mapa coroplético do RS (requer malha municipal), hospedagem (Streamlit Community Cloud) e
  coleta automatizada dos dados.
