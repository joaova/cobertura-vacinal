"""Contexto anual do sarampo, resumido de publicações do Ministério da Saúde.

Consulta das fontes: 22/11/2026. Os textos descrevem o cenário nacional e
eventos investigados; não atribuem a origem de cada registro do banco local.
"""
from dataclasses import dataclass


DATA_CONSULTA = "22/11/2026"
MS = "https://www.gov.br/saude/pt-br"
BOLETINS = f"{MS}/centrais-de-conteudo/publicacoes/boletins/epidemiologicos/edicoes"
SITUACAO = f"{MS}/assuntos/saude-de-a-a-z/s/sarampo/situacao-epidemiologica/situacao-epidemiologica-do-sarampo/"
SERIE_HISTORICA = f"{MS}/assuntos/saude-de-a-a-z/s/sarampo/situacao-epidemiologica/casos-confirmados-sarampo-1990-2026.pdf"
GENOMICA = f"{BOLETINS}/2022/boletim-epidemiologico-vol-53-no12.pdf/@@download/file"
CIT_2018 = (f"{MS}/acesso-a-informacao/gestao-do-sus/articulacao-interfederativa/cit/"
            "pautas-de-reunioes-e-resumos/2018/novembro/3-b-apresentacao_sarampo_reuniao_cit_novembro-002.pdf")
NOTA_114 = f"{MS}/composicao/svsa/pni/notas-tecnicas/2024/nota-tecnica-conjunta-no-114-2024-dpni-dedt-svsa-ms"
NOTA_368 = (f"{MS}/centrais-de-conteudo/publicacoes/notas-tecnicas/2025/"
            "nota-tecnica-conjunta-no-368-2025-cgvdi-dpni-svsa-ms.pdf")
BALANCO_2026 = (f"{MS}/assuntos/noticias/2026/novembro/"
                "brasil-mantem-eliminacao-do-sarampo-apos-avanco-da-doenca-em-paises-das-americas/")


@dataclass(frozen=True)
class Fonte:
    titulo: str
    url: str


@dataclass(frozen=True)
class ContextoAnual:
    titulo: str
    resumo: str
    fontes: tuple[Fonte, ...]
    total_confirmado_brasil: int
    recorte_total: str = "série histórica atualizada em 21/09/2026"
    fonte_total: str = SERIE_HISTORICA


CONTEXTOS = {
    2015: ContextoAnual(
        titulo="Continuidade dos surtos de 2013–2015, sobretudo no Ceará",
        resumo=(
            "O Ministério da Saúde descreveu os surtos de 2013–2015 como introduções do vírus do exterior "
            "que encontraram pessoas suscetíveis, com a maior parte dos casos do período em Pernambuco "
            "e no Ceará. Na distribuição específica de 2015, o Ceará concentrou 211 dos 214 casos confirmados "
            "do país. A explicação documentada envolve a entrada do vírus e pessoas sem proteção suficiente; "
            "a cobertura estadual anual, isoladamente, não permite identificar esses grupos."
        ),
        fontes=(
            Fonte("Ministério da Saúde, balanço dos surtos de 2013–2015 (dezembro/2015)",
                  f"{MS}/assuntos/noticias/2015/dezembro/brasil-recebe-certificado-de-eliminacao-da-rubeola-em-territorio-nacional"),
            Fonte("Situação epidemiológica apresentada à CIT, 29/11/2018, p. 2", f"{CIT_2018}#page=2"),
        ),
        total_confirmado_brasil=214,
    ),
    2016: ContextoAnual(
        titulo="Ano sem casos confirmados e certificação de eliminação",
        resumo=(
            "O Ministério da Saúde informa ausência de casos confirmados no Brasil em 2016, após os "
            "últimos casos de 2015. O país recebeu a certificação de eliminação naquele ano. "
            "Assim, essa fonte não descreve um surto nacional em 2016 para explicar."
        ),
        fontes=(Fonte("Boletim Epidemiológico, vol. 53, nº 3, janeiro/2022, p. 1",
                      f"{BOLETINS}/2022/boletim-epidemiologico-vol-53-no03.pdf/@@download/file#page=1"),),
        total_confirmado_brasil=0,
    ),
    2017: ContextoAnual(
        titulo="Ano sem casos confirmados no Brasil",
        resumo=(
            "O Ministério da Saúde também informa ausência de casos confirmados no Brasil em 2017. "
            "Esse ano faz parte do período sem confirmação entre os casos de 2015 e a reintrodução "
            "do vírus em 2018. Portanto, os registros locais do painel não devem ser interpretados "
            "automaticamente como evidência de um surto confirmado naquele ano."
        ),
        fontes=(Fonte("Situação epidemiológica apresentada à CIT, 29/11/2018, p. 2", f"{CIT_2018}#page=2"),),
        total_confirmado_brasil=0,
    ),
    2018: ContextoAnual(
        titulo="Reintrodução do vírus e surtos em Roraima e no Amazonas",
        resumo=(
            "A investigação epidemiológica e genômica do Ministério da Saúde relacionou a introdução "
            "do vírus em Roraima e no Amazonas à circulação na Venezuela. O vírus identificado apresentava "
            "a mesma linhagem encontrada naquele país. O Ministério também apontou baixas coberturas "
            "vacinais em vários municípios como parte do contexto que permitiu a reintrodução."
        ),
        fontes=(
            Fonte("Boletim de vigilância laboratorial 2018–2021, vol. 53, nº 12, p. 20", f"{GENOMICA}#page=20"),
            Fonte("Nota Técnica Conjunta nº 114/2024, seção 3", NOTA_114),
        ),
        total_confirmado_brasil=9329,
    ),
    2019: ContextoAnual(
        titulo="Nova introdução em São Paulo e disseminação pelo país",
        resumo=(
            "Segundo a investigação genômica do Ministério da Saúde, um surto iniciado em São Paulo "
            "em março de 2019 teve como fonte de infecção um viajante procedente de Israel. A linhagem "
            "viral desse evento se disseminou por quase todos os estados brasileiros. Houve também "
            "um surto em um navio de cruzeiro, com outra linhagem, que ficou restrito aos envolvidos "
            "e a poucos contatos; o boletim distingue essas cadeias de transmissão."
        ),
        fontes=(Fonte("Boletim de vigilância laboratorial 2018–2021, vol. 53, nº 12, p. 20", f"{GENOMICA}#page=20"),),
        total_confirmado_brasil=21704,
    ),
    2020: ContextoAnual(
        titulo="Circulação persistente e necessidade de alcançar pessoas suscetíveis",
        resumo=(
            "O boletim de julho de 2020 registrou circulação do vírus em diversos estados, com "
            "concentração de casos no Pará, Rio de Janeiro e São Paulo. O Ministério justificou a "
            "prorrogação da vacinação de adultos pelas baixas coberturas e pelo grande contingente "
            "de pessoas suscetíveis, recomendando manter a vacinação mesmo durante a pandemia de "
            "covid-19. Esse cenário envolve falhas de proteção acumuladas, além da cobertura do próprio ano."
        ),
        fontes=(Fonte("Boletim Epidemiológico, vol. 51, nº 30, julho/2020, pp. 1–3 e 8–9",
                      f"{BOLETINS}/2020/boletim-epidemiologico-vol-51-no30"),),
        total_confirmado_brasil=8035,
    ),
    2021: ContextoAnual(
        titulo="Concentração de casos no Amapá e no Pará",
        resumo=(
            "O balanço das semanas epidemiológicas 1–52 de 2021 destacou o Amapá como o estado "
            "com mais casos, seguido pelo Pará. Crianças menores de um ano apresentavam a maior "
            "incidência. O documento orienta vacinação e resposta rápida aos casos para interromper "
            "a circulação. Ele descreve a distribuição do surto, mas não identifica uma única causa "
            "para todos os casos nem permite atribuí-los à cobertura estadual do mesmo ano."
        ),
        fontes=(Fonte("Boletim Epidemiológico, vol. 53, nº 3, janeiro/2022, pp. 1–3 e recomendações",
                      f"{BOLETINS}/2022/boletim-epidemiologico-vol-53-no03.pdf/@@download/file"),),
        total_confirmado_brasil=670,
    ),
    2022: ContextoAnual(
        titulo="Redução dos casos e interrupção da transmissão endêmica",
        resumo=(
            "A série histórica do Ministério da Saúde registra casos no Amapá, Pará, Rio de Janeiro "
            "e São Paulo. A Nota Técnica nº 114/2024 situa o último caso endêmico em junho de 2022. "
            "O ano marca a redução da circulação e sua interrupção, após os surtos anteriores; "
            "o total anual não permite determinar a origem de cada caso exibido na tabela."
        ),
        fontes=(
            Fonte("Série histórica de casos confirmados, atualização de 21/09/2026", SERIE_HISTORICA),
            Fonte("Nota Técnica Conjunta nº 114/2024, seção 3.3", NOTA_114),
        ),
        total_confirmado_brasil=41,
    ),
    2023: ContextoAnual(
        titulo="Nenhum caso confirmado segundo o Ministério da Saúde",
        resumo=(
            "O Ministério da Saúde informa que não houve casos confirmados no Brasil em 2023. "
            "Seu balanço associa a manutenção da eliminação ao fortalecimento da vigilância e à "
            "retomada da vacinação. Portanto, não há surto confirmado naquele ano a explicar nessa "
            "fonte; os registros do banco do projeto precisam ser distinguidos do balanço oficial."
        ),
        fontes=(Fonte("Ministério da Saúde, balanço da eliminação do sarampo, 17/11/2026",
                      BALANCO_2026),),
        total_confirmado_brasil=0,
    ),
    2024: ContextoAnual(
        titulo="Casos esporádicos, principalmente importados",
        resumo=(
            "O Ministério da Saúde registra cinco casos confirmados em 2024: quatro importados "
            "(Rio Grande do Sul, Minas Gerais e São Paulo) e um no Rio de Janeiro com fonte de "
            "infecção desconhecida. A Nota Técnica nº 6/2024 detalha o caso de Rio Grande: uma "
            "criança de três anos, sem histórico de vacinação, procedente do Paquistão. "
            "A entrada de casos do exterior é o principal contexto documentado para esse ano."
        ),
        fontes=(
            Fonte("Ministério da Saúde, situação epidemiológica, seção 2024", SITUACAO),
            Fonte("Nota Técnica Conjunta nº 6/2024, seção 3",
                  f"{MS}/centrais-de-conteudo/publicacoes/notas-tecnicas/2024/nota-tecnica-conjunta-no-6-2024-cgvdi-dpni-svsa-ms"),
        ),
        total_confirmado_brasil=5,
    ),
    2025: ContextoAnual(
        titulo="Importações e transmissão em comunidades com baixa vacinação",
        resumo=(
            "Em Campos Lindos (TO), o surto começou em julho após quatro brasileiros retornarem "
            "infectados da Bolívia. A investigação descreve baixa adesão à vacinação e rápida "
            "transmissão entre familiares e contatos da comunidade. Houve também um caso no Maranhão "
            "vinculado a essa cadeia. No Mato Grosso, a nota descreve outra introdução em uma "
            "família não vacinada que também havia viajado à Bolívia. O balanço do Ministério "
            "registra 25 casos confirmados no Tocantins. A cobertura estadual de D1 pode ocultar "
            "grupos locais suscetíveis e não representa o esquema completo de todas as idades."
        ),
        fontes=(
            Fonte("Nota Técnica Conjunta nº 368/2025, seções 3.2–3.4", NOTA_368),
            Fonte("Ministério da Saúde, situação epidemiológica, seção 2025", SITUACAO),
        ),
        total_confirmado_brasil=38,
    ),
    2026: ContextoAnual(
        titulo="Ano parcial: surtos e importações em contexto de circulação nas Américas",
        resumo=(
            "Em 17/11/2026, o Ministério da Saúde informava 70 casos no Brasil, associados à "
            "importação do vírus, com concentração em São Paulo e municípios do Amazonas e do Acre. "
            "O balanço anterior, até 19/10, relacionava os surtos no Amazonas e no Acre à circulação "
            "no Peru. A resposta incluiu investigação, monitoramento de contatos e vacinação de "
            "bloqueio. São dados parciais de eventos distintos; não indicam uma origem comum "
            "para todos os registros do ano."
        ),
        fontes=(
            Fonte("Ministério da Saúde, balanço de 17/11/2026", BALANCO_2026),
            Fonte("Ministério da Saúde, situação epidemiológica, balanço até 19/10/2026", SITUACAO),
        ),
        total_confirmado_brasil=70,
        recorte_total="balanço parcial publicado em 17/11/2026",
        fonte_total=BALANCO_2026,
    ),
}
