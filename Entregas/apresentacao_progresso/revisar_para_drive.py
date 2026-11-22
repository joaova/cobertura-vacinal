"""Revisão da apresentação para conversão em Google Slides.

Reutiliza o mecanismo de formas e textos editáveis da apresentação original.
O conteúdo prioriza a introdução e o percurso pelas páginas oficiais do app.
"""
from pathlib import Path
import csv
import json
import hashlib

import gerar_apresentacao as b

P = Path(__file__).resolve().parent
REFS = {r['chave_bibtex']: r for r in csv.DictReader((b.ARTIGO/'fontes_verificadas.csv').open(encoding='utf-8'))}
MS_COLETIVA = 'https://www.gov.br/saude/pt-br/composicao/svsa/pni/faq/faq/vacinas/o-que-e-imunidade-coletiva'
OMS_VACINAS = 'https://www.who.int/news-room/feature-stories/detail/how-do-vaccines-work'
b.PREVIEWS = Path('/tmp/projetobd-slides-revisados')


def painel(s, x, y, w, h, titulo, corpo, cor=b.BLUE):
    s.rect(x, y, w, h, b.WHITE, radius=True)
    s.rect(x+.2, y+.24, .06, .34, cor)
    s.text(titulo, x+.4, y+.22, w-.65, .7, 20, b.INK, bold=True)
    s.text(corpo, x+.4, y+1.0, w-.75, h-1.13, 18, b.MUTED)


def faixa(s, texto, y=6.25, cor=b.PALE):
    s.rect(.6, y, 12.1, .43, cor, radius=True)
    s.text(texto, .8, y+.10, 11.7, .27, 14, b.INK)


def grafico_combinado():
    d = [r for r in b.ler_csv('serie_brasil_rs_poa.csv') if r['nome_localidade']=='Porto Alegre']
    anos = [int(r['ano']) for r in d]
    fig, ax = b.plt.subplots(figsize=(9.2, 4.5))
    ax2 = ax.twinx()
    ax2.bar(anos, [float(r['incidencia_100k']) for r in d], color='#D9B3B7', width=.65,
            label='Incidência /100 mil', zorder=1)
    ax.set_zorder(ax2.get_zorder()+1); ax.patch.set_visible(False)
    for dose, cor in [('d1', b.BLUE), ('d2', b.TEAL)]:
        ax.plot(anos, [float(r['cobertura_'+dose]) for r in d], marker='o', markersize=4,
                linewidth=2.4, color='#'+cor, label=dose.upper(), zorder=3)
    ax.axhline(95, color='#6E8192', linestyle='--', linewidth=1.2, label='Meta de 95%')
    ax.set(xlim=(2014.7,2026.4), ylim=(0,110), ylabel='Cobertura (%)')
    ax2.set(ylim=(0,max(float(r['incidencia_100k']) for r in d)*1.35), ylabel='Incidência /100 mil')
    ax.set_xticks([2015,2017,2019,2021,2023,2025,2026]); ax.grid(axis='y',alpha=.16)
    ax.axvspan(2025.5,2026.4,color='#e8edf3',alpha=.7)
    h,l=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels()
    fig.legend(h+h2,l+l2,loc='lower center',ncol=4,frameon=False,fontsize=12)
    fig.subplots_adjust(left=.09,right=.9,bottom=.2,top=.96)
    return b.grafico_salvar(fig,'cruzamento_poa_revisado')


def criar():
    cobertura = P/'figuras/cobertura_d2.png'
    incidencia = P/'figuras/casos_incidencia.png'
    mensal = P/'figuras/doses_mensais.png'
    combinado = grafico_combinado()
    slides=[]

    s=b.Slide('Dashboard de cobertura vacinal e sarampo','Apresentação do dashboard',dark=True)
    s.text('PROJETO DE BANCO DE DADOS · 2026/2',.75,.65,11.8,.35,13,'75D0CE',bold=True)
    s.text('Dashboard de cobertura\nvacinal e sarampo',.75,1.55,11.8,1.75,42,b.WHITE,bold=True)
    s.text('Dados disponíveis e funcionamento das páginas',.78,3.55,11.5,.65,25,'DCE8F1')
    s.text('Brasil, unidades da federação e municípios do Rio Grande do Sul',.78,4.42,11.4,.6,19,'C3D6E4')
    s.text('Gabriel Eichelberger Fontaneli\nJoão Villanova do Amaral · Rafaele Castagnara Alves',.78,5.65,11.5,.75,18,b.WHITE)
    s.notas='Apresentar os autores e o objetivo: demonstrar a aplicação documentada no artigo atualizado. O percurso começa pelos conceitos de cobertura e proteção coletiva e segue pelas seis páginas oficiais. Duração sugerida para a apresentação: 12 a 15 minutos.'
    slides.append(s)

    s=b.Slide('Vacinação e acompanhamento da cobertura','Introdução','Tríplice Viral: proteção contra sarampo, caxumba e rubéola.',
              'Fontes: OMS, Measles / How do vaccines work?; Ministério da Saúde, Manual de vacinação (2024).')
    painel(s,.6,2.2,3.85,3.75,'Prevenção','A vacinação prepara a resposta do organismo e reduz a ocorrência de doenças e suas complicações.',b.TEAL)
    painel(s,4.7,2.2,3.85,3.75,'Continuidade','Acompanhar a primeira e a segunda dose ajuda a observar o cumprimento do esquema vacinal.',b.BLUE)
    painel(s,8.8,2.2,3.85,3.75,'Distribuição','A cobertura deve ser observada em cada território. Uma média nacional pode ocultar áreas abaixo da meta.',b.ORANGE)
    faixa(s,'O dashboard reúne cobertura vacinal, registros de sarampo e população para consulta conjunta.')
    s.notas='O sarampo é uma doença altamente contagiosa. A vacinação é uma medida de prevenção e exige continuidade do esquema. O painel serve ao acompanhamento territorial, sem medir diretamente a resposta imune de cada pessoa. Fontes: '+REFS['omssarampo']['url']+' ; '+OMS_VACINAS+' ; '+REFS['manual2024']['url']
    slides.append(s)

    s=b.Slide('Meta de cobertura vacinal','Introdução','Referência para a Tríplice Viral: pelo menos 95%, com acompanhamento de D1 e D2.',
              'Fontes: Ministério da Saúde, Manual de vacinação (2024); OMS, Measles: Immunization, Vaccines and Biologicals.')
    s.rect(.6,2.18,4.0,3.93,b.NAVY,radius=True)
    s.text('95%',.92,2.48,3.35,1.2,76,b.WHITE,bold=True)
    s.text('Meta para cada dose\ne cada território',.95,3.95,3.2,1.05,23,b.WHITE)
    s.text('Cobertura alta e homogênea\nreduz lacunas de proteção.',.96,5.33,3.12,.65,17,'C3D6E4')
    painel(s,4.9,2.18,7.75,1.88,'Como interpretar o percentual','O denominador é a população-alvo definida para a vacinação, e não a população total.',b.BLUE)
    painel(s,4.9,4.27,7.75,1.84,'Por que observar as duas doses','A meta de D1 não substitui a de D2. O esquema de duas doses é necessário para a proteção contra o sarampo.',b.TEAL)
    faixa(s,'A linha de 95% aparece nos gráficos de cobertura e orienta a classificação dos municípios.')
    s.notas='A OMS recomenda que os países alcancem pelo menos 95% com ambas as doses em cada distrito. O percentual administrativo usa os registros e a população-alvo da fonte; não representa a fração imune de toda a comunidade. A meta é uma referência de acompanhamento. Fonte: '+REFS['omssarampo']['url']+' ; '+REFS['manual2024']['url']
    slides.append(s)

    s=b.Slide('Como funciona a imunidade de rebanho','Introdução','Também chamada de imunidade coletiva: redução da circulação do agente infeccioso.',
              'Fontes: Ministério da Saúde, Imunidade coletiva; OMS, How do vaccines work? Diagrama conceitual, sem escala.')
    s.rect(.6,2.2,7.15,3.85,b.WHITE,radius=True)
    s.text('Mais pessoas suscetíveis',.85,2.45,6.6,.4,19,b.INK,bold=True)
    s.text('Há mais oportunidades de transmissão.',.85,2.97,6.6,.4,16,b.MUTED)
    for y, cores in [(3.58,[b.RED,b.ORANGE,b.ORANGE,b.ORANGE]),(5.1,[b.RED,b.TEAL,b.TEAL,b.ORANGE])]:
        for i,cor in enumerate(cores):
            x=1.08+i*1.7
            s.shape(x,y,.47,.47,cor,'ellipse')
            if i<3 and (y<4 or i==0):
                s.shape(x+.68,y+.14,.66,.18,'B7C7D3','rightArrow')
    s.rect(3.45,5.06,.045,.55,b.TEAL)
    s.text('Mais pessoas imunes',.85,4.28,6.6,.4,19,b.INK,bold=True)
    s.text('A chance de uma nova infecção diminui.',.85,4.76,6.6,.3,16,b.MUTED)
    for x,cor,txt in [(.9,b.RED,'Infectada'),(3.05,b.ORANGE,'Suscetível'),(5.35,b.TEAL,'Imune')]:
        s.shape(x,6.23,.17,.17,cor,'ellipse'); s.text(txt,x+.26,6.19,1.85,.35,14,b.MUTED)
    painel(s,8.05,2.2,4.6,3.85,'Proteção indireta','Com menos transmissão, pessoas que não podem receber a vacina têm menor chance de exposição.\n\nA proteção não é absoluta e depende da distribuição da imunidade.',b.TEAL)
    s.notas='As setas representam contatos possíveis, não infecções certas. Quando um número suficiente de pessoas está imune, cada pessoa infectada tende a gerar menos novas infecções e as cadeias de transmissão têm menor chance de se manter. O efeito também beneficia quem não pode receber determinada vacina, mas não garante proteção total. A concentração de suscetíveis pode permitir surtos mesmo quando a média agregada é alta. Não associar cada círculo a uma proporção real de cobertura. Fontes: '+MS_COLETIVA+' ; '+OMS_VACINAS
    slides.append(s)

    s=b.Slide('Objetivo e escopo do dashboard','Dados e organização','Consultar vacinação e sarampo por localidade e período, com acesso às tabelas utilizadas.')
    for i,(t,c,cor) in enumerate([('Fontes públicas','SI-PNI / TABNET\nPainéis do Ministério da Saúde\nSINAN e população do IBGE',b.BLUE),('Integração','Arquivos CSV e XLSX\nPadronização de códigos e anos\nArmazenamento em SQLite',b.TEAL),('Consulta','Filtros por território e ano\nGráficos e tabelas\nExportação de dados',b.BLUE)]):
        painel(s,.6+i*4.15,2.2,3.8,2.93,t,c,cor)
    s.text('Brasil + 27 UFs + 497 municípios do RS',.8,5.48,11.7,.5,25,b.INK,bold=True)
    s.text('Série anual: 2015–2026. Detalhamento mensal de doses: 2023–2026.',.8,6.17,11.7,.35,18,b.MUTED)
    s.notas='Explicar o percurso dos arquivos até o painel. O detalhamento municipal está restrito ao Rio Grande do Sul; o projeto não inclui todos os municípios brasileiros. A série de 2026 é parcial. As fontes e os procedimentos estão descritos na página Dados e metodologia e no artigo.'
    slides.append(s)

    s=b.Slide('Navegação e filtros','Funcionamento','As seis páginas oficiais se complementam durante a consulta.')
    paginas=[('01','Visão geral','Indicadores e evolução histórica'),('02','Cobertura vacinal','Doses, UFs e municípios na meta'),('03','Casos e incidência','Contagens e taxas de sarampo'),('04','Cobertura × sarampo','Consulta conjunta das variáveis'),('05','Ficha do município','Detalhe anual e doses mensais'),('06','Dados e metodologia','Fontes, definições e limitações')]
    for i,(n,t,c) in enumerate(paginas):
        x=.6+(i%3)*4.15; y=2.13+(i//3)*1.56
        s.rect(x,y,3.8,1.35,b.WHITE,radius=True)
        s.text(n,x+.18,y+.18,.4,.35,16,b.TEAL,bold=True)
        s.text(t,x+.75,y+.17,2.85,.64,19,b.INK,bold=True)
        s.text(c,x+.2,y+.92,3.42,.3,14,b.MUTED)
    s.rect(.6,5.52,12.1,1.12,b.PALE,radius=True)
    s.text('Cálculo anual da cobertura em 2023–2026',.83,5.69,11.6,.4,19,b.INK,bold=True)
    s.text('Escolha global: média mensal ou razão entre somas de doses e população-alvo.',.83,6.19,11.6,.3,16,b.MUTED)
    s.notas='Apontar o menu lateral e depois os filtros específicos de cada página. A opção global de cálculo afeta as coberturas de 2023 a 2026. A média mensal é o padrão atual do painel. O método alternativo é soma de doses dividida pela soma da população-alvo, vezes 100. Em 2015–2022 são usadas as coberturas anuais fornecidas pela fonte.'
    slides.append(s)

    s=b.Slide('Página Visão geral','Percurso pelo dashboard','Ponto de entrada para observar o ano selecionado e o contexto da série histórica.')
    painel(s,.6,2.15,4.0,2.0,'1. Selecionar o ano','Atualizar os indicadores de cobertura, casos e incidência.',b.BLUE)
    painel(s,.6,4.22,4.0,2.1,'2. Ler a evolução','O gráfico mantém a série completa, mesmo quando o ano dos indicadores muda.',b.TEAL)
    s.rect(4.9,2.15,7.75,4.17,b.WHITE,radius=True)
    s.text('O que aparece na página',5.17,2.42,7.2,.45,22,b.INK,bold=True)
    s.text('Cobertura D1 e D2 de Brasil, RS e Porto Alegre\n\nMunicípios do RS que alcançam a meta de D1\n\nCasos e incidência de sarampo\n\nSérie de cobertura com os casos do Brasil',5.18,3.18,7.08,2.8,21,b.MUTED)
    s.notas='Na demonstração, selecionar um ano e mostrar quais cartões mudam. Explicar que o gráfico histórico conserva todo o período para contextualizar esse recorte. Usar a página como visão inicial antes de abrir os filtros mais detalhados das demais páginas.'
    slides.append(s)

    s=b.Slide('Cobertura vacinal: série histórica','Percurso pelo dashboard','Comparar D1 e D2 ao longo do tempo para as localidades selecionadas.')
    painel(s,.6,2.15,3.65,3.93,'Filtros da consulta','Até oito localidades\n\nIntervalo de anos\n\nPrimeira e/ou segunda dose\n\nTabela e exportação',b.BLUE)
    s.rect(4.5,2.15,8.15,3.93,b.WHITE,radius=True)
    s.image(cobertura,4.62,2.3,7.92,3.61)
    faixa(s,'Exemplo de leitura: D2 de Brasil, RS e Porto Alegre. A linha tracejada indica a meta de 95%.')
    s.notas='Abrir a aba Série histórica e selecionar as localidades e doses desejadas. O gráfico apresentado foi gerado com os dados do artigo e ilustra a consulta, sem ser uma captura de tela. A mudança de fonte ocorre em 2023 e 2026 é parcial. Não usar a curva como conclusão isolada sobre proteção da população.'
    slides.append(s)

    s=b.Slide('Cobertura: comparação entre territórios','Percurso pelo dashboard','Outras duas abas ajudam a comparar doses e identificar municípios abaixo da meta.')
    painel(s,.6,2.2,5.85,3.85,'1ª × 2ª dose por UF','Escolher ano e regiões.\n\nComparar as barras de D1 e D2.\n\nOrdenar pela diferença entre doses, por cobertura ou pela UF.',b.BLUE)
    painel(s,6.75,2.2,5.9,3.85,'Municípios do RS na meta','Escolher D1 ou D2 e observar a evolução anual.\n\nFiltrar a tabela por ano, nome, situação de cobertura e faixa percentual.',b.TEAL)
    faixa(s,'A tabela mantém a categoria “sem dado” separada de “abaixo da meta”.')
    s.notas='Na aba por UF, demonstrar a comparação das duas doses no mesmo ano e a ordenação pela diferença entre elas. Na aba municipal, escolher D2 e filtrar os municípios abaixo de 95%. Mostrar que ausência de dado não equivale a cobertura zero. A classificação depende do método global escolhido.'
    slides.append(s)

    s=b.Slide('Página Casos e incidência','Percurso pelo dashboard','Ler contagens e taxas em conjunto, considerando o tamanho da população.')
    painel(s,.6,2.15,3.75,3.92,'Filtros disponíveis','Brasil, UFs ou municípios do RS\nAno ou intervalo\n\nMínimo de casos e população\nOrdenação e número de locais',b.RED)
    s.rect(4.6,2.15,8.05,3.92,b.WHITE,radius=True)
    s.image(incidencia,4.72,2.34,7.79,3.5)
    faixa(s,'Exemplo com seis municípios do RS em 2019. Incidência = casos ÷ população × 100 mil.')
    s.notas='As duas medidas respondem a perguntas diferentes: casos mostram o volume registrado; incidência relaciona casos à população. O gráfico ilustra seis municípios escolhidos no artigo, não o ranking completo da tela. Explicar o uso do filtro de população mínima ao comparar municípios pequenos. Para a demonstração, preferir um único ano; na opção acumulada, a taxa exibida é soma das taxas anuais.'
    slides.append(s)

    s=b.Slide('Cobertura × sarampo: evolução por localidade','Percurso pelo dashboard','Primeira aba: relacionar as séries no mesmo recorte temporal.')
    painel(s,.6,2.15,3.75,3.92,'Escolhas da tela','Até quatro localidades\n\nIntervalo de anos\n\nBarras de casos ou incidência\n\nLinhas D1 e D2',b.TEAL)
    s.rect(4.6,2.15,8.05,3.92,b.WHITE,radius=True)
    s.image(combinado,4.72,2.32,7.8,3.61)
    faixa(s,'Exemplo: Porto Alegre. As coberturas e a incidência usam eixos e unidades diferentes.')
    s.notas='O exemplo reproduz os dados usados na aplicação para Porto Alegre. Explicar cada eixo antes de interpretar coincidências entre as curvas e as barras. Para cada localidade escolhida, a tela apresenta um gráfico. A sobreposição temporal permite exploração; não demonstra causalidade nem eficácia individual da vacina.'
    slides.append(s)

    s=b.Slide('Comparação por situação de cobertura','Percurso pelo dashboard','Segunda aba de Cobertura × sarampo: análise exploratória entre localidades.')
    for i,(titulo,corpo) in enumerate([('Definir o recorte','UFs ou municípios do RS\nDose e ano\nPopulação mínima, se municipal'),('Separar os grupos','Abaixo de 95%\nPelo menos 95%\nDefasagem opcional de 0 a 2 anos'),('Consultar as medidas','População, casos e incidência\nTabela por grupo\nDispersão e Spearman nos detalhes')]):
        painel(s,.6+i*4.15,2.2,3.8,3.85,titulo,corpo,b.TEAL if i==1 else b.BLUE)
    faixa(s,'A incidência do grupo é calculada a partir dos totais de casos e população incluídos.')
    s.notas='Mostrar primeiro a definição do recorte e o tamanho dos grupos. A defasagem permite usar a cobertura de até dois anos antes dos casos. O filtro municipal de população mínima altera quais localidades entram na comparação. A correlação de Spearman e a dispersão ficam nos detalhes: são descritivas e não controlam fatores de confusão. Não apresentar associação ecológica como efeito causal.'
    slides.append(s)

    s=b.Slide('Página Ficha do município','Percurso pelo dashboard','Reunir os indicadores anuais e a evolução histórica de um município do RS.')
    s.rect(.6,2.13,12.05,.55,b.PALE,radius=True)
    s.text('Exemplo de seleção: Porto Alegre · ano 2025 · método padrão',.84,2.29,11.5,.3,17,b.INK)
    for x,v,t,cor in [(.6,'91,35%','Cobertura D1',b.BLUE),(3.68,'77,47%','Cobertura D2',b.TEAL),(6.76,'1','Caso de sarampo',b.RED),(9.84,'0,072','Incidência /100 mil',b.BLUE)]:
        s.metric(x,2.95,2.82,v,t,cor)
    painel(s,.6,4.87,5.85,1.78,'Resumo do ano','Os cartões e avisos mostram a situação da cobertura em relação à meta.',b.BLUE)
    painel(s,6.75,4.87,5.9,1.78,'Contexto do município','O gráfico e a tabela anual permitem acompanhar D1, D2 e os casos.',b.TEAL)
    s.notas='Escolher um município e o ano. Os valores ilustram uma seleção real do banco do artigo, não são indicadores novos. Primeiro mostrar os cartões do ano; depois a série anual e a tabela. A ficha reúne os diferentes recortes municipais sem exigir uma troca de página para as doses mensais.'
    slides.append(s)

    s=b.Slide('Doses mensais dentro da ficha do município','Percurso pelo dashboard','Comparar a distribuição das aplicações ao longo dos meses e entre os anos.')
    s.rect(.6,2.13,8.25,4.0,b.WHITE,radius=True)
    s.image(mensal,.73,2.28,7.98,3.66)
    painel(s,9.1,2.13,3.55,4.0,'Como ler','Um painel por dose\n\nUma linha por ano\n\nAplicações registradas, incluindo todas as idades',b.TEAL)
    faixa(s,'Exemplo: Porto Alegre, 2023–2026. Meses ainda não disponíveis não devem ser lidos como zero.')
    s.notas='O gráfico mensal permanece na Ficha do município; não há página independente de doses mensais. As aplicações registradas incluem todas as idades, por isso não são o mesmo numerador da cobertura da população-alvo. Para 2026, a série de aplicações tem corte diferente da série de cobertura. O Excel da ficha contém abas anual e mensal.'
    slides.append(s)

    s=b.Slide('Página Dados e metodologia','Percurso pelo dashboard','Consultar a origem das informações e as regras usadas na integração.')
    itens=[('Fontes e extração','Origem dos arquivos e datas de corte'),('Modelo relacional','Tabelas, chaves e dicionário de dados'),('ETL e qualidade','Padronização e registros do processamento'),('Limitações','Restrições de cobertura e comparabilidade'),('Reprodutibilidade','Arquivos, versões e procedimentos'),('Consultas SQL','Consultas de apoio à análise')]
    for i,(t,c) in enumerate(itens):
        x=.6+(i%2)*6.15; y=2.16+(i//2)*1.43
        s.rect(x,y,5.9,1.22,b.WHITE,radius=True)
        s.text(t,x+.23,y+.18,5.4,.39,20,b.INK,bold=True)
        s.text(c,x+.23,y+.78,5.4,.3,16,b.MUTED)
    s.notas='Usar esta página para esclarecer o significado de um indicador ou uma mudança de fonte. Há seis abas, com documentação das fontes, modelo e procedimentos. A apresentação mostra a função das abas sem exibir código. O processamento lê os arquivos locais disponibilizados; não corresponde a uma coleta automática em tempo real.'
    slides.append(s)

    s=b.Slide('Exportação e sequência de consulta','Demonstração sugerida','Um percurso que pode ser repetido durante a apresentação do dashboard.')
    passos=[('1','Cobertura vacinal','Filtrar municípios abaixo da meta'),('2','Ficha do município','Abrir o município e escolher o ano'),('3','Histórico e doses mensais','Observar a série e a distribuição mensal'),('4','Exportação','Salvar a tabela ou o gráfico da consulta')]
    for i,(n,t,c) in enumerate(passos):
        y=2.12+i*1.0
        s.shape(.7,y+.12,.5,.5,b.TEAL,'ellipse'); s.text(n,.7,y+.2,.5,.3,16,b.WHITE,bold=True,align='center')
        s.text(t,1.5,y+.07,4.0,.4,21,b.INK,bold=True)
        s.text(c,5.65,y+.12,6.65,.4,18,b.MUTED)
    faixa(s,'Tabelas: CSV e Excel. Gráficos: PNG pela câmera do gráfico e HTML para interação.')
    s.notas='Demonstrar um percurso simples. Na tabela municipal de cobertura, selecionar uma dose e o grupo abaixo da meta; anotar um município para abrir na ficha. Observar a evolução anual e as aplicações mensais antes de exportar. As tabelas têm downloads CSV/Excel; os gráficos podem ser salvos como PNG pela ferramenta da câmera e como HTML interativo. A exportação integral da ficha reúne duas abas no Excel.'
    slides.append(s)

    s=b.Slide('Cuidados na interpretação das consultas','Leitura dos dados','O recorte selecionado e as definições da fonte acompanham os indicadores.')
    painel(s,.6,2.17,5.85,2.0,'2026 é um ano parcial','Cobertura: janeiro a agosto. Aplicações: janeiro a outubro. Casos: atualização de setembro.',b.ORANGE)
    painel(s,6.75,2.17,5.9,2.0,'População e incidência','O denominador residente é usado na incidência. Para 2026, repete-se a população de 2025.',b.BLUE)
    painel(s,.6,4.4,5.85,2.0,'Métodos e mudanças de fonte','O cálculo anual em 2023–2026 pode alterar o percentual e a classificação em relação à meta.',b.TEAL)
    painel(s,6.75,4.4,5.9,2.0,'Alcance da análise','São dados agregados. As comparações servem à exploração e não estimam proteção individual.',b.BLUE)
    s.notas='Evitar comparar um ano parcial diretamente com anos completos. Na cobertura, a população-alvo difere da população residente usada na incidência. A série muda de fonte em 2023. Os dois métodos anuais são alternativas analíticas do projeto, sem equivalência metodológica integral comprovada com o painel oficial. As diferenças entre registros de vigilância e balanços oficiais também estão descritas no artigo.'
    slides.append(s)

    s=b.Slide('Referências: vacinação e proteção coletiva','Referências','Links para as fontes utilizadas na introdução.', 'Fontes institucionais verificadas em 22/11/2026. Links nos títulos abaixo.')
    fontes=[('OMS · Measles: Immunization, Vaccines and Biologicals',REFS['omssarampo']['url'],'Duas doses e cobertura de pelo menos 95% em cada território.'),('Ministério da Saúde · Manual de vacinação (2024)',REFS['manual2024']['url'],'Meta de cobertura e acompanhamento do Programa Nacional de Imunizações.'),('Ministério da Saúde · O que é imunidade coletiva?',MS_COLETIVA,'Definição e proteção indireta de pessoas que não podem ser vacinadas.'),('OMS · How do vaccines work?',OMS_VACINAS,'Resposta imune, esquema de doses e limites da proteção coletiva.')]
    for i,(titulo,url,desc) in enumerate(fontes):
        y=2.12+i*1.08
        s.text(titulo,.8,y,11.7,.43,20,b.BLUE,bold=True,link=url)
        s.text(desc,.8,y+.56,11.7,.35,16,b.MUTED)
    s.notas='As referências estão vinculadas aos respectivos títulos. A explicação da introdução é uma síntese dessas fontes, sem reproduzir figuras institucionais.'
    slides.append(s)

    s=b.Slide('Referências: dados e documentação','Referências','Fontes dos dados integrados e do contexto do projeto.', 'Fontes institucionais verificadas em 22/11/2026. Links nos títulos abaixo.')
    for i,(key,desc) in enumerate([('tabnet','DATASUS · Informações de Saúde (TABNET)'),('paineis','Ministério da Saúde · Painéis de Vacinação'),('basedados','Base dos Dados · População Brasileira, fonte IBGE'),('nota90','Ministério da Saúde · Nota Técnica nº 90/2025'),('petsaude','Ministério da Saúde · PET-Saúde Digital')]):
        y=2.14+i*.76
        s.text(desc,.8,y,11.7,.49,20,b.BLUE,bold=True,link=REFS[key]['url'])
    s.text('Documentação do projeto: artigo atualizado e página Dados e metodologia do dashboard.',.8,6.17,11.6,.5,17,b.MUTED)
    s.notas='As fontes de vacinação e vigilância são integradas pelo código IBGE da localidade e pelo ano. O artigo e a página de metodologia descrevem o recorte e as escolhas de cálculo. Os números mostrados nos exemplos foram extraídos do material complementar do artigo.'
    slides.append(s)

    for i,s in enumerate(slides,1):
        s.text(f'{i:02d} / {len(slides)}',11.85,7.24,.88,.22,9,'B5C6D4' if s.bg==b.NAVY else b.MUTED,align='right')
    return slides


def main():
    b.PREVIEWS.mkdir(parents=True,exist_ok=True)
    slides=criar()
    avisos=b.validar(slides)
    if avisos:
        print(json.dumps(avisos,ensure_ascii=False,indent=2))
        raise RuntimeError('Revisar dimensionamento dos textos.')
    b.pptx(slides,P/'apresentacao_dashboard_revisada.pptx')
    b.pdf(slides,P/'apresentacao_dashboard_revisada.pdf')
    (P/'roteiro_dashboard_revisado.txt').write_text('\n\n'.join(f'{i:02d}. {s.titulo}\n{s.notas}' for i,s in enumerate(slides,1))+'\n',encoding='utf-8')
    manifesto={'titulo':'ProjetoBD — Apresentação do dashboard','data':'2026-11-22','slides':len(slides),
               'conteudo':[s.titulo for s in slides], 'arquivos':{},
               'observacao':'Textos, formas e diagramas nativos editáveis; gráficos inseridos como imagens. Originais preservados.',
               'novas_fontes':[{'titulo':'Ministério da Saúde: Imunidade coletiva','url':MS_COLETIVA,'verificado_em':'2026-11-22'},
                              {'titulo':'OMS: How do vaccines work?','url':OMS_VACINAS,'verificado_em':'2026-11-22'}]}
    for nome in ['apresentacao_dashboard_revisada.pptx','apresentacao_dashboard_revisada.pdf','roteiro_dashboard_revisado.txt']:
        manifesto['arquivos'][nome]=hashlib.sha256((P/nome).read_bytes()).hexdigest()
    (P/'manifesto_revisado.json').write_text(json.dumps(manifesto,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(slides)} slides gerados; prévias em {b.PREVIEWS}')


if __name__=='__main__':
    main()
