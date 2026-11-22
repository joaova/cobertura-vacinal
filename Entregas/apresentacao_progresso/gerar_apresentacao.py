"""Gera PPTX editável, PDF e roteiro a partir do artigo atualizado.

Usa somente biblioteca padrão, Pillow e Matplotlib. O PPTX contém formas e
textos nativos, gráficos em PNG e notas do apresentador; não exige python-pptx.
Os dados são lidos do material complementar do artigo, sem alterar o SQLite.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

os.environ.setdefault("MPLCONFIGDIR", "/tmp/projetobd-slides-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.patches import FancyBboxPatch, Rectangle, Ellipse, Polygon
from matplotlib.ticker import FuncFormatter
from PIL import Image, ImageFont

PASTA = Path(__file__).resolve().parent
ARTIGO = PASTA.parent / "artigo_atualizado"
W, H = 13.333333, 7.5
EMU = 914400
FONT = "Arial"
BG, WHITE, NAVY = "F5F7FB", "FFFFFF", "102A43"
INK, MUTED, BLUE = "17324D", "586B80", "17649B"
TEAL, ORANGE, RED, GREEN = "107D85", "D28327", "B84F57", "39834C"
PALE = "E8EFF6"
TOTAL = 19
FAMILIAS = ["Arial", "Liberation Sans", "DejaVu Sans"]
FONTE_NORMAL = findfont(FontProperties(family=FAMILIAS))
FONTE_NEGRITO = findfont(FontProperties(family=FAMILIAS, weight="bold"))
FONTE_PDF = FontProperties(fname=FONTE_NORMAL).get_name()
PREVIEWS = Path("/tmp/projetobd-slides-previews")

plt.rcParams.update({"font.family": FONTE_PDF, "font.size": 15,
                     "axes.titlesize": 18, "axes.labelsize": 15,
                     "xtick.labelsize": 13, "ytick.labelsize": 13,
                     "legend.fontsize": 14, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42})


def ler_csv(nome):
    with (ARTIGO / "dados" / nome).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def grafico_salvar(fig, nome):
    destino = PASTA / "figuras" / f"{nome}.png"
    fig.savefig(destino, dpi=200, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return destino


def graficos():
    serie = ler_csv("serie_brasil_rs_poa.csv")
    fig, ax = plt.subplots(figsize=(9.3, 4.6))
    for nome, cor, marcador in [("Brasil", BLUE, "o"), ("Rio Grande do Sul", GREEN, "s"),
                                 ("Porto Alegre", "97559C", "^")]:
        d = [r for r in serie if r["nome_localidade"] == nome]
        ax.plot([int(r["ano"]) for r in d], [float(r["cobertura_d2"]) for r in d],
                label="RS" if nome == "Rio Grande do Sul" else nome,
                color="#" + cor, linewidth=2.5, marker=marcador, markersize=6)
    ax.axhline(95, color="#64748b", linestyle="--", linewidth=1.5)
    ax.text(2015.15, 96.4, "Meta de 95%", fontsize=14, color="#586B80")
    ax.axvline(2022.5, color="#a5b0bd", linestyle=":", linewidth=1.5)
    ax.axvspan(2025.5, 2026.4, color="#e8edf3")
    ax.set(ylim=(40, 102), xlim=(2014.8, 2026.4), ylabel="Cobertura D2 (%)")
    ax.set_xticks([2015, 2017, 2019, 2021, 2023, 2025, 2026])
    ax.grid(axis="y", alpha=0.18)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    fig.subplots_adjust(left=0.1, right=0.99, top=0.96, bottom=0.2)
    cobertura = grafico_salvar(fig, "cobertura_d2")

    rank = list(reversed(ler_csv("exemplos_municipais_2019.csv")))
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.5), sharey=True)
    nomes = [r["nome_localidade"] for r in rank]
    for ax, campo, titulo, cor in zip(axes, ["casos_inicio_exantema", "incidencia_100k"],
                                     ["Casos", "Incidência /100 mil"], [RED, BLUE]):
        valores = [float(r[campo]) for r in rank]
        ax.barh(nomes, valores, color="#" + cor, height=0.64)
        ax.set_title(titulo, pad=16, fontweight="bold")
        ax.set_xlim(0, max(valores) * 1.25)
        ax.grid(axis="x", alpha=0.15)
        for y, v in enumerate(valores):
            label = f"{v:.2f}".replace(".", ",") if campo == "incidencia_100k" else str(int(v))
            ax.text(v + max(valores) * 0.025, y, label, va="center", fontsize=13)
    fig.subplots_adjust(left=0.22, right=0.99, top=0.86, bottom=0.1, wspace=0.23)
    incidencia = grafico_salvar(fig, "casos_incidencia")

    mensal = ler_csv("doses_mensais_poa.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3))
    for ax, dose in zip(axes, ("D1", "D2")):
        for ano, cor in [(2023, BLUE), (2024, ORANGE), (2025, GREEN), (2026, "97559C")]:
            d = [r for r in mensal if r["ano"] == str(ano) and r["dose"] == dose]
            ax.plot([int(r["mes"]) for r in d], [int(r["doses_aplicadas"]) for r in d],
                    color="#" + cor, linewidth=2, marker="o", markersize=4,
                    linestyle="--" if ano == 2026 else "-", label=str(ano))
        ax.set_title(dose, fontweight="bold")
        ax.set(xlim=(0.8, 12.2), ylim=(0, None))
        ax.set_xticks([1, 3, 5, 7, 9, 11], ["jan", "mar", "mai", "jul", "set", "nov"])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", ".")))
        ax.grid(axis="y", alpha=0.18)
    axes[0].set_ylabel("Aplicações registradas")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.subplots_adjust(left=0.08, right=0.99, top=0.9, bottom=0.2, wspace=0.25)
    doses = grafico_salvar(fig, "doses_mensais")
    return cobertura, incidencia, doses


class Slide:
    def __init__(self, titulo, secao, subtitulo="", fonte="Artigo atualizado · dados do projeto · recorte de 22/11/2026", dark=False):
        self.titulo, self.secao = titulo, secao
        self.bg = NAVY if dark else BG
        self.objetos = []
        self.notas = ""
        self.rect(0, 0, W, 0.085, TEAL)
        if not dark:
            self.text(secao.upper(), 0.58, 0.31, 12.1, 0.25, 11, TEAL, bold=True)
            self.text(titulo, 0.58, 0.72, 12.1, 0.98, 31, INK, bold=True)
            if subtitulo:
                self.text(subtitulo, 0.6, 1.63, 12.0, 0.3, 16, MUTED)
        self.rect(0.58, 6.91, 12.17, 0.012, "CCD7E2" if not dark else "436078")
        self.text(fonte, 0.6, 6.99, 11.75, 0.2, 9.3, "6E8192" if not dark else "B5C6D4")
        self.text("UFRGS · Projeto de Banco de Dados", 0.6, 7.27, 10.8, 0.16, 8.5, MUTED if not dark else "B5C6D4")

    def rect(self, x, y, w, h, fill, radius=False, border=None):
        self.objetos.append(dict(kind="shape", x=x, y=y, w=w, h=h, fill=fill,
                                 geom="roundRect" if radius else "rect", border=border))

    def shape(self, x, y, w, h, fill, geom):
        self.objetos.append(dict(kind="shape", x=x, y=y, w=w, h=h, fill=fill, geom=geom, border=None))

    def text(self, txt, x, y, w, h, size=22, color=INK, bold=False, align="left", link=None):
        # A quebra explícita usa métricas da fonte compatível com Arial no PDF.
        fonte = ImageFont.truetype(FONTE_NEGRITO if bold else FONTE_NORMAL, 1000)
        linhas = []
        for par in str(txt).split("\n"):
            atual = ""
            for palavra in par.split():
                tentativa = (atual + " " + palavra).strip()
                largura = fonte.getlength(tentativa) / 1000 * size / 72
                if atual and largura > w - 0.015:
                    linhas.append(atual)
                    atual = palavra
                else:
                    atual = tentativa
            linhas.append(atual)
        self.objetos.append(dict(kind="text", text="\n".join(linhas), x=x, y=y, w=w, h=h,
                                 size=size, color=color, bold=bold, align=align, link=link))

    def image(self, path, x, y, w, h):
        with Image.open(path) as im:
            ratio = im.width / im.height
        if w / h > ratio:
            nw = h * ratio
            x += (w - nw) / 2
            w = nw
        else:
            nh = w / ratio
            y += (h - nh) / 2
            h = nh
        self.objetos.append(dict(kind="image", path=str(path), x=x, y=y, w=w, h=h))

    def card(self, x, y, w, h, titulo, corpo, accent=BLUE, num=None):
        self.rect(x, y, w, h, WHITE, radius=True)
        self.rect(x + 0.18, y + 0.22, 0.07, 0.42, accent)
        self.text(titulo, x + 0.39, y + 0.23, w - 0.65, 0.65, 20, INK, bold=True)
        self.text(corpo, x + 0.38, y + 1.0, w - 0.72, h - 1.12, 18, MUTED)
        if num:
            self.text(num, x + w - 0.9, y + 0.23, 0.5, 0.4, 14, accent, bold=True, align="right")

    def metric(self, x, y, w, value, label, accent=BLUE, detail=None):
        self.rect(x, y, w, 1.58, WHITE, radius=True)
        self.text(value, x + 0.23, y + 0.17, w - 0.46, 0.7, 40, accent, bold=True)
        self.text(label, x + 0.24, y + 0.97, w - 0.48, 0.47, 17, INK)
        if detail:
            self.text(detail, x + 0.24, y + 1.32, w - 0.48, 0.2, 11, MUTED)


def montar_slides(paths):
    cobertura, incidencia, doses = paths
    slides = []

    s = Slide("Cobertura vacinal e sarampo", "Apresentação do progresso", dark=True)
    s.text("PROJETO DE BANCO DE DADOS · 2026/2", 0.7, 0.55, 11.9, 0.3, 13, "75D0CE", bold=True)
    s.text("Cobertura vacinal\ne sarampo", 0.72, 1.35, 9.7, 1.65, 52, WHITE, bold=True)
    s.text("Integração de dados públicos e uma plataforma\ninterativa para os municípios do Rio Grande do Sul", 0.75, 3.25, 11.6, 1, 24, "DCE8F1")
    s.rect(0.76, 4.72, 3.6, 0.48, TEAL, radius=True)
    s.text("O QUE FOI IMPLEMENTADO ATÉ AGORA", 0.89, 4.85, 3.3, 0.2, 11, WHITE, bold=True)
    s.text("Gabriel Eichelberger Fontaneli\nJoão Villanova do Amaral · Rafaele Castagnara Alves", 0.77, 5.65, 11.5, 0.7, 17, WHITE)
    s.notas = "Apresentar os autores e o objetivo. Esta apresentação relata o estágio documentado no artigo de 22/11/2026: aplicação implementada, com validação técnica e pendências metodológicas. Tempo sugerido: 20 segundos."
    slides.append(s)

    s = Slide("Vacinar protege pessoas; monitorar ajuda a agir.", "01 · Contexto", "Tríplice Viral: sarampo, caxumba e rubéola.", "Fontes: OMS, Measles / Immunization; Ministério da Saúde, Manual de vacinação (2024).")
    s.rect(0.6, 2.2, 3.7, 3.95, NAVY, radius=True)
    s.text("95%", 0.92, 2.63, 3.0, 1.2, 78, WHITE, bold=True)
    s.text("Meta de cobertura\nda Tríplice Viral", 0.96, 4.0, 2.9, 0.9, 24, WHITE)
    s.text("Duas doses,\nem cada território.", 0.97, 5.24, 2.9, 0.62, 17, "C3D6E4")
    s.card(4.6, 2.2, 7.95, 1.84, "Proteção individual e coletiva", "A vacinação reduz doenças e transmissão, beneficiando também pessoas suscetíveis.", TEAL)
    s.card(4.6, 4.28, 7.95, 1.87, "O desafio para a gestão", "Médias agregadas podem ocultar territórios abaixo da meta e grupos com menor proteção.", ORANGE)
    s.notas = "Explicar brevemente proteção coletiva ou imunidade de rebanho. A OMS recomenda pelo menos 95% com duas doses em cada distrito para sustentar a eliminação do sarampo. Cobertura administrativa não mede diretamente a imunidade de toda a população. Tempo: 45 segundos."
    slides.append(s)

    s = Slide("De 70 arquivos a uma consulta territorial.", "02 · Objetivo", "Unificar vacinação, sarampo e população para apoiar análises no PET-Saúde Digital.")
    for i, (titulo, corpo, cor) in enumerate([("Fontes", "CSV e XLSX\nde quatro origens", BLUE), ("ETL", "Limpeza de dados\nCódigos e anos", TEAL), ("SQLite", "Dados relacionados\npor localidade e ano", BLUE), ("Streamlit", "Filtros, gráficos\ne exportações", TEAL)]):
        x = 0.6 + i * 3.15
        s.rect(x, 2.5, 2.73, 1.78, WHITE, radius=True)
        s.text(titulo, x + 0.2, 2.76, 2.33, 0.4, 23, cor, bold=True)
        s.text(corpo, x + 0.2, 3.37, 2.33, 0.65, 18, MUTED)
        if i < 3:
            s.shape(x + 2.84, 3.17, 0.23, 0.3, "9AAFBE", "rightArrow")
    for x, value, label in [(0.6, "525", "territórios"), (4.8, "2015–2026", "série histórica"), (9.0, "6", "páginas oficiais")]:
        s.metric(x, 4.85, 3.75, value, label, TEAL)
    s.notas = "O foco é resolver a fragmentação dos arquivos. O produto liga país, UFs e municípios do RS, sem ampliar artificialmente o escopo. Não há dados individuais nem tentativa de estimar eficácia vacinal. Tempo: 40 segundos."
    slides.append(s)

    s = Slide("Quatro fontes, com recortes distintos.", "03 · Dados", "Brasil + 27 UFs + 497 municípios do RS. Detalhamento municipal apenas no RS.")
    for x, y, titulo, num, corpo, cor in [
        (0.6, 2.18, "TABNET / SI-PNI", "16", "Cobertura anual D1/D2\n2015–2022 · CSV", BLUE),
        (6.88, 2.18, "SEIDIGI / DEMAS", "32", "Cobertura, população-alvo e aplicações\n2023–2026 · XLSX", TEAL),
        (0.6, 4.33, "SINAN / TABNET", "20", "Casos por ano de início do exantema\ne cortes por ano de notificação", RED),
        (6.88, 4.33, "IBGE / Base dos Dados", "2", "População residente · 1991–2025\nRecorte integrado: 2015–2026", ORANGE),
    ]:
        s.card(x, y, 5.86, 1.94, titulo, corpo, cor, num)
    s.notas = "São 16 arquivos de cobertura antiga, 32 planilhas recentes, 20 arquivos de vigilância e dois populacionais. A aquisição foi por exportação dos portais. O ETL lê o acervo local; não faz coleta automatizada. As datas de corte de 2026 serão discutidas ao final. Tempo: 40 segundos."
    slides.append(s)

    s = Slide("O território conecta as observações.", "04 · Modelo relacional", "Quatro tabelas principais e três tabelas de apoio.")
    s.rect(4.58, 2.12, 4.18, 0.97, BLUE, radius=True)
    s.text("LOCALIDADE", 4.78, 2.38, 3.78, 0.4, 24, WHITE, bold=True, align="center")
    s.rect(6.66, 3.09, 0.022, 0.23, "9AAFBE")
    s.rect(2.455, 3.30, 8.41, 0.022, "9AAFBE")
    for x, titulo, corpo in [(0.63, "Vacinação anual", "Localidade + ano\nCobertura D1/D2 e métodos"), (4.84, "Vacinação mensal", "Localidade + ano + mês + dose\nAplicações e população-alvo"), (9.04, "Sarampo anual", "Localidade + ano de exantema\nCasos, população e incidência")]:
        s.rect(x + 1.814, 3.30, 0.022, 0.39, "9AAFBE")
        s.rect(x, 3.69, 3.65, 1.46, WHITE, radius=True)
        s.text("1:N", x + 2.02, 3.37, 0.7, 0.25, 14, MUTED)
        s.text(titulo, x + 0.22, 3.94, 3.21, 0.4, 22, INK, bold=True)
        s.text(corpo, x + 0.22, 4.51, 3.21, 0.55, 16, MUTED)
    s.rect(0.64, 5.52, 12.04, 0.79, PALE, radius=True)
    s.text("Apoio: ano de notificação · manifesto de arquivos · log de qualidade", 0.9, 5.72, 11.5, 0.38, 19, INK, align="center")
    s.text("61.588 registros no banco completo  ·  aproximadamente 4,3 MB", 0.87, 6.45, 11.5, 0.28, 16, MUTED, align="center")
    s.notas = "A localidade evita repetir nome, código e UF nos fatos. Há unicidade localidade–ano e localidade–ano–mês–dose. Indicadores derivados são materializados por conveniência, portanto o artigo evita afirmar terceira forma normal estrita para todo o esquema físico. Tempo: 40 segundos."
    slides.append(s)

    s = Slide("Integrar também exige preservar incertezas.", "05 · Tratamento e rastreabilidade", "O ETL torna os dados comparáveis sem inventar informações ausentes.")
    cards = [
        (0.6, 2.18, "Padronização", "CSV/XLSX, vírgulas decimais e\ncódigos IBGE de 6 e 7 dígitos.", BLUE),
        (6.88, 2.18, "Ausente ≠ zero", "Coberturas não informadas ficam nulas;\ncasos seguem a convenção do acervo.", ORANGE),
        (0.6, 4.33, "Origem verificável", "70 arquivos com hash SHA-256\ne 28 ocorrências no log de qualidade.", TEAL),
        (6.88, 4.33, "Atualização do banco", "Consultas e conexão renovadas\nquando o ETL recria o SQLite.", BLUE),
    ]
    for x, y, titulo, corpo, cor in cards:
        s.card(x, y, 5.86, 1.94, titulo, corpo, cor)
    s.notas = "Destacar a distinção entre cobertura ausente e ausência de casos conforme a fonte. Existem quatro registros municipais sem cobertura nos CSVs históricos. O cache foi corrigido para acompanhar a modificação e a substituição do arquivo SQLite. O manifesto permite identificar o acervo exato. Tempo: 45 segundos."
    slides.append(s)

    s = Slide("Seis páginas oficiais compartilham a mesma base.", "06 · Plataforma implementada", "Filtros de território, período, dose, população, casos e cobertura, conforme a página.")
    itens = [
        ("Visão geral", "Brasil, RS e Porto Alegre:\nindicadores e evolução."),
        ("Cobertura vacinal", "Séries históricas, UFs e\nmunicípios frente à meta."),
        ("Casos e incidência", "Casos e taxa por\n100 mil habitantes."),
        ("Cobertura × sarampo", "Cruzamentos, grupos por meta\ne exploração estatística."),
        ("Ficha do município", "Séries anuais, doses mensais\ne exportação da ficha."),
        ("Dados e metodologia", "Fontes, modelo, qualidade,\nversões e consultas."),
    ]
    for i, (titulo, corpo) in enumerate(itens):
        s.card(0.6 + (i % 3) * 4.2, 2.22 + (i // 3) * 2.1,
               3.78, 1.9, titulo, corpo, TEAL if i % 2 else BLUE)
    s.notas = "Apresentar a navegação oficial. O gráfico de doses mensais fica na ficha municipal; a antiga página independente foi retirada. Todas as tabelas permitem CSV/Excel; os gráficos têm PNG pelo Plotly e HTML interativo. A ficha tem Excel com abas anual e mensal. Tempo: 50 segundos."
    slides.append(s)

    s = Slide("Uma ficha organiza a consulta do município.", "07 · Exemplo de uso", "Porto Alegre · 2025 · método padrão: média mensal da cobertura.")
    for x, valor, label, cor in [(0.6, "91,35%", "Cobertura D1", BLUE), (3.79, "77,47%", "Cobertura D2", ORANGE),
                                (6.98, "1", "Caso por ano de exantema", RED), (10.17, "0,0720", "Incidência /100 mil", TEAL)]:
        s.metric(x, 2.35, 2.58, valor, label, cor)
    for i, (titulo, corpo) in enumerate([("1 · Selecionar", "Município e ano\nde referência."), ("2 · Comparar", "Evolução anual e\naplicações por mês."), ("3 · Compartilhar", "Exportar a ficha\nem Excel." )]):
        s.card(0.6 + i * 4.2, 4.42, 3.78, 1.78, titulo, corpo, BLUE)
    s.notas = "Esta lâmina organiza os indicadores do recorte, não é uma captura de tela. Em uma demonstração ao vivo: abrir Ficha do município, selecionar Porto Alegre e 2025, percorrer a série e o gráfico mensal, e exportar Excel. Incidência foi mostrada com quatro casas para evitar parecer zero. Tempo: 45 segundos ou 1 minuto com demonstração."
    slides.append(s)

    s = Slide("A segunda dose permanece abaixo da meta.", "08 · Resultado: cobertura", "Brasil, RS e Porto Alegre · série do banco de 2015 a 2026.")
    s.rect(0.6, 2.12, 9.15, 4.5, WHITE, radius=True)
    s.image(cobertura, 0.74, 2.22, 8.84, 4.2)
    s.rect(10.0, 2.2, 2.69, 2.0, NAVY, radius=True)
    s.text("11 anos", 10.24, 2.52, 2.25, 0.6, 35, WHITE, bold=True)
    s.text("D2 abaixo\nda meta\n2015–2025", 10.26, 3.24, 2.18, 0.87, 18, WHITE)
    s.text("2023: mudança de fonte\ne agregação mensal.\n\n2026: período parcial\nna faixa sombreada.", 10.12, 4.62, 2.42, 1.65, 17, MUTED)
    s.notas = "No método padrão, as três séries ficam abaixo da meta de D2 em todos os 11 anos completos de 2015 a 2025. Há recuperação após 2021, mas ainda com distância da meta. Não comparar o ponto de 2026 diretamente com os anos completos. A linha vertical marca a mudança de fonte em 2023. Tempo: 50 segundos."
    slides.append(s)

    s = Slide("Mais casos não significa maior incidência.", "09 · Resultado: casos e população", "Exemplos municipais de 2019; não é um ranking completo do RS.")
    s.rect(0.6, 2.12, 9.1, 4.5, WHITE, radius=True)
    s.image(incidencia, 0.7, 2.24, 8.9, 4.15)
    s.text("Carlos Gomes", 10.0, 2.46, 2.65, 0.4, 23, INK, bold=True)
    s.text("1 caso", 10.0, 3.1, 2.65, 0.65, 37, RED, bold=True)
    s.text("em 1.377 habitantes", 10.02, 3.85, 2.6, 0.5, 17, MUTED)
    s.text("72,62", 10.0, 4.6, 2.65, 0.7, 43, BLUE, bold=True)
    s.text("casos por 100 mil", 10.02, 5.37, 2.65, 0.4, 18, INK)
    s.notas = "Gravataí tem 35 casos, Porto Alegre 22 e Cachoeirinha 20. A taxa muda a leitura porque considera o tamanho populacional. Um único caso em Carlos Gomes gera a maior taxa entre os exemplos selecionados. Isso justifica considerar taxa e contagem e usar filtros de população. Tempo: 45 segundos."
    slides.append(s)

    s = Slide("As doses mensais ficam na ficha municipal.", "10 · Resultado: aplicações", "Porto Alegre · uma linha por ano e separação entre D1 e D2.")
    s.rect(0.6, 2.1, 12.1, 3.82, WHITE, radius=True)
    s.image(doses, 0.77, 2.15, 11.76, 3.69)
    s.rect(0.62, 6.08, 12.05, 0.55, PALE, radius=True)
    s.text("D1 em 2025: 19.761 aplicações em todas as idades ≠ 11.713 no numerador da cobertura infantil.",
           0.86, 6.22, 11.55, 0.28, 16.7, INK)
    s.notas = "A separação por ano atende à crítica do JEMS sobre comparações mensais. Em 2026 os dados terminam em outubro, que pode estar incompleto; meses posteriores são ausentes, não zeros. Contagem de aplicações e numerador da cobertura têm universos distintos. Picos não demonstram, sozinhos, campanhas ou aumento de procura. Tempo: 50 segundos."
    slides.append(s)

    s = Slide("O método pode mudar a classificação municipal.", "11 · Sensibilidade dos indicadores", "D2 · 497 municípios do RS · 2025 · mesma meta de 95%.")
    s.rect(0.6, 2.2, 8.45, 4.1, WHITE, radius=True)
    for y, total, label, cor in [(2.72, 260, "Média das coberturas mensais", BLUE),
                                 (4.48, 236, "Razão entre as somas", TEAL)]:
        s.text(label, 0.91, y, 7.9, 0.38, 21, INK, bold=True)
        s.rect(0.94, y + 0.61, 6.75, 0.6, PALE, radius=True)
        s.rect(0.94, y + 0.61, 6.75 * total / 497, 0.6, cor, radius=True)
        s.text(f"{total} na meta", 5.05, y + 0.7, 3.0, 0.37, 23, cor, bold=True)
    s.rect(9.4, 2.2, 3.27, 2.24, NAVY, radius=True)
    s.text("138", 9.68, 2.52, 2.7, 0.9, 62, WHITE, bold=True)
    s.text("municípios mudam\nde grupo: 27,8%", 9.7, 3.6, 2.68, 0.72, 21, WHITE)
    s.text("Há mudanças nos dois sentidos.\n\nA equivalência à cobertura\nanual oficial ainda precisa\nser validada.", 9.47, 4.79, 3.14, 1.6, 17, MUTED)
    s.notas = "A média mensal é o padrão para reproduzir o anteprojeto. A razão soma numeradores e populações-alvo. A diferença líquida entre os totais é 24 municípios, mas 138 mudam de grupo porque há movimentos nas duas direções. Existem 3.144 registros mensais com população-alvo zero no acervo. Nenhum método foi homologado como substituto da regra oficial. Tempo: 1 minuto."
    slides.append(s)

    s = Slide("A relação observada é exploratória.", "12 · Cobertura × sarampo", "D2 em 2019 · população mínima de 5.000 habitantes · 266 municípios elegíveis.")
    s.card(0.6, 2.18, 5.86, 2.18, "Abaixo de 95%", "156 municípios · 102 casos\nIncidência: 1,218 por 100 mil", RED)
    s.card(6.88, 2.18, 5.86, 2.18, "95% ou mais", "110 municípios · 2 casos\nIncidência: 0,087 por 100 mil", GREEN)
    s.rect(0.63, 4.65, 12.08, 1.48, NAVY, radius=True)
    s.text("31 de 3.976 pares município–ano tinham casos em 2018–2025.", 0.95, 4.93, 11.48, 0.48, 25, WHITE, bold=True)
    s.text("Eventos esparsos, empates e diferenças de população limitam a interpretação.", 0.96, 5.62, 11.4, 0.3, 18, "C4D5E2")
    s.text("Taxa do grupo = total de casos ÷ população total × 100 mil. Associação não demonstra causalidade.", 0.85, 6.42, 11.75, 0.3, 16, MUTED)
    s.notas = "Um caso municipal de 2019 fica fora do recorte por população. O coeficiente de Spearman nesse conjunto é aproximadamente −0,158. O painel oferece defasagem de zero a dois anos e detalhes estatísticos. As populações vacinais infantis não equivalem à população de todas as idades usada na incidência. Não concluir eficácia, proteção individual ou causa dos surtos. Tempo: 55 segundos."
    slides.append(s)

    s = Slide("A entrega foi verificada e revisada.", "13 · Validação e avaliações", "Consistência computacional não substitui validação epidemiológica ou avaliação de uso.")
    s.rect(0.6, 2.2, 3.6, 3.95, NAVY, radius=True)
    s.text("82", 0.98, 2.55, 2.9, 1.4, 84, WHITE, bold=True)
    s.text("testes\naprovados", 1.0, 4.0, 2.85, 0.8, 23, WHITE, bold=True)
    s.text("ETL · consultas · estatística\nInterface · filtros · cache", 1.0, 5.05, 2.86, 0.95, 16, "C4D5E2")
    s.text("O que foi incorporado após o JEMS", 4.62, 2.34, 7.85, 0.6, 26, INK, bold=True)
    for i, texto in enumerate(["Avisos de fonte e recursos de exportação", "Doses mensais separadas por ano", "Termos epidemiológicos corrigidos", "Versões, datas e limitações documentadas"]):
        y = 3.36 + i * 0.7
        s.shape(4.65, y + 0.05, 0.13, 0.13, TEAL, "ellipse")
        s.text(texto, 4.96, y, 7.56, 0.5, 22, INK)
    s.notas = "Na revisão de 22/11/2026, 82 testes passaram. Foram reproduzidas as 36 linhas históricas do anteprojeto. As avaliações levaram à inclusão de avisos, exportações, filtros e comparação por ano e à correção de exantema versus início de sintomas. Não houve ainda avaliação com preceptores. Tempo: 50 segundos."
    slides.append(s)

    s = Slide("2026 reúne três datas de corte diferentes.", "14 · Limites do acervo", "A população de 2025 foi reutilizada para a incidência de 2026.")
    for x, titulo, valor, corpo, cor in [(0.6, "Cobertura", "JAN–AGO", "Agregação de oito\nmeses disponíveis.", BLUE),
                                       (4.8, "Aplicações", "JAN–OUT", "Outubro pode estar\nincompleto.", TEAL),
                                       (9.0, "Casos", "SET/2026", "Data de atualização.\nCasos são anuais.", ORANGE)]:
        s.rect(x, 2.23, 3.75, 2.55, WHITE, radius=True)
        s.text(titulo, x + 0.26, 2.5, 3.2, 0.4, 22, INK, bold=True)
        s.text(valor, x + 0.26, 3.16, 3.2, 0.6, 34, cor, bold=True)
        s.text(corpo, x + 0.28, 4.02, 3.2, 0.6, 18, MUTED)
    s.rect(0.64, 5.1, 12.07, 1.26, "FFF0DA", radius=True)
    s.text("O banco e os balanços oficiais ainda divergem.", 0.92, 5.35, 11.5, 0.4, 23, INK, bold=True)
    s.text("Banco / oficial: 2023 = 4 / 0; 2025 = 42 / 38 casos. Diferenças ainda não reconciliadas.",
           0.94, 5.95, 11.35, 0.3, 17, MUTED)
    s.notas = "Evitar comparar 2026 com totais completos. A população replicada é a última do acervo, não uma afirmação de ausência de dados mais recentes em outros portais. Nas comparações do rodapé, o primeiro número é do banco e o segundo, do balanço oficial consultado no artigo. Esses totais não são tratados como equivalentes. O ranking acumulado também precisa de revisão do denominador apresentado. Tempo: 1 minuto."
    slides.append(s)

    s = Slide("Os próximos passos priorizam validação e uso.", "15 · Estágio do projeto", "Base e interface implementadas; ainda há decisões metodológicas e avaliação de campo.")
    s.card(0.6, 2.28, 3.78, 3.7, "Implementado", "ETL e banco relacional\n\nSeis páginas e exportações\n\nRastreabilidade e testes", TEAL)
    s.card(4.8, 2.28, 3.78, 3.7, "Prioridade técnica", "Validar cobertura anual\n\nReconciliar casos\n\nRever ranking acumulado", ORANGE)
    s.card(9.0, 2.28, 3.78, 3.7, "Avaliação e expansão", "Testar tarefas com preceptores\n\nPublicar a aplicação\n\nAmpliar bases disponíveis", BLUE)
    s.text("Sem resultados de usabilidade ou de impacto nas UBS até este estágio.", 0.87, 6.4, 11.8, 0.3, 17, MUTED, align="center")
    s.notas = "A sequência proposta é validar os indicadores e corrigir pendências, realizar uma avaliação com preceptores e preparar a publicação. As tarefas de uso podem ser localizar município abaixo da meta, comparar a série com o RS, interpretar meses e exportar a ficha. A expansão para outras UFs requer novos arquivos; doses históricas exigem populações-alvo compatíveis. Tempo: 45 segundos."
    slides.append(s)

    s = Slide("Dados integrados para apoiar análises locais.", "16 · Encerramento", dark=True)
    s.text("O QUE ENTREGAMOS ATÉ AQUI", 0.75, 0.66, 11.8, 0.4, 15, "75D0CE", bold=True)
    s.text("Dados integrados para\napoiar análises locais.", 0.76, 1.65, 11.75, 1.6, 45, WHITE, bold=True)
    for x, titulo, corpo in [(0.78, "Base rastreável", "Origem e tratamento\ndocumentados."),
                             (4.98, "Consulta reproduzível", "Filtros e resultados\nverificáveis."),
                             (9.18, "Ficha municipal", "Leitura e exportação\npara análise territorial.")]:
        s.text(titulo, x, 4.3, 3.35, 0.55, 22, "75D0CE", bold=True)
        s.text(corpo, x, 5.13, 3.35, 0.85, 20, WHITE)
    s.notas = "Encerrar enfatizando a contribuição de integração e apresentação. A plataforma não substitui os sistemas oficiais nem demonstra causalidade. Abrir para perguntas ou demonstração da aplicação. Tempo: 20 segundos."
    slides.append(s)

    with (ARTIGO / "fontes_verificadas.csv").open(encoding="utf-8", newline="") as f:
        fontes = {r["chave_bibtex"]: r for r in csv.DictReader(f)}
    refs = [
        [("omssarampo", "OMS · Sarampo e recomendação de 95%"), ("oms2026", "OMS · Measles, ficha técnica (2026)"),
         ("manual2024", "Ministério da Saúde · Manual de vacinação (2024)"), ("petsaude", "Ministério da Saúde · PET-Saúde Digital"),
         ("tabnet", "DATASUS · Informações de Saúde / TABNET"), ("paineis", "Ministério da Saúde · Painéis de Vacinação"),
         ("basedados", "Base dos Dados · População brasileira / IBGE")],
        [("nota90", "Ministério da Saúde · Nota Técnica nº 90/2025"), ("situacao", "Ministério da Saúde · Situação epidemiológica"),
         ("balanco2026", "Ministério da Saúde · Balanço de 17/11/2026"), ("sqlite", "SQLite · Appropriate Uses for SQLite"),
         ("streamlitcache", "Streamlit · Documentação de cache"), ("scipy", "SciPy · Documentação de Spearman")],
    ]
    for idx, pagina in enumerate(refs):
        s = Slide("Referências e material de apoio", f"Apoio · {idx+1}/2", "Títulos clicáveis no PowerPoint e no PDF. Fontes verificadas na revisão do artigo.",
                  "Referências completas: Entregas/artigo_atualizado/referencias.bib · consulta em 22/11/2026.")
        for i, (key, titulo) in enumerate(pagina):
            y = 2.15 + i * 0.61
            s.shape(0.65, y + 0.12, 0.1, 0.1, TEAL, "ellipse")
            s.text(titulo, 0.94, y, 11.73, 0.46, 20, BLUE, link=fontes[key]["url"])
        s.notas = "Referências de apoio. A lista completa, as datas de consulta e os endereços estão na pasta do artigo.\n\n" + "\n".join(t + ": " + fontes[k]["url"] for k, t in pagina)
        slides.append(s)
    assert len(slides) == TOTAL
    for i, s in enumerate(slides, 1):
        s.text(f"{i:02d} / {TOTAL}", 11.85, 7.24, 0.88, 0.22, 9, MUTED if s.bg != NAVY else "B5C6D4", align="right")
    return slides


NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
for prefix, ns in NS.items():
    ET.register_namespace(prefix, ns)


def el(parent, tag, **attrs):
    prefix, name = tag.split(":")
    return ET.SubElement(parent, f"{{{NS[prefix]}}}{name}", {k: str(v) for k, v in attrs.items()})


def xml(root):
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def root(tag):
    prefix, name = tag.split(":")
    return ET.Element(f"{{{NS[prefix]}}}{name}")


def xfrm(parent, obj):
    tr = el(parent, "a:xfrm")
    el(tr, "a:off", x=round(obj["x"] * EMU), y=round(obj["y"] * EMU))
    el(tr, "a:ext", cx=round(obj["w"] * EMU), cy=round(obj["h"] * EMU))


def fill(parent, color):
    el(el(parent, "a:solidFill"), "a:srgbClr", val=color)


def tree(parent):
    st = el(parent, "p:spTree")
    nv = el(st, "p:nvGrpSpPr")
    el(nv, "p:cNvPr", id=1, name="")
    el(nv, "p:cNvGrpSpPr")
    el(nv, "p:nvPr")
    tr = el(el(st, "p:grpSpPr"), "a:xfrm")
    for n, attrs in [("off", {"x": 0, "y": 0}), ("ext", {"cx": 0, "cy": 0}),
                     ("chOff", {"x": 0, "y": 0}), ("chExt", {"cx": 0, "cy": 0})]:
        el(tr, "a:" + n, **attrs)
    return st


def relationships(items):
    rt = ET.Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
    for rid, tipo, target, external in items:
        attrs = dict(Id=rid, Type=NS["r"] + "/" + tipo, Target=target)
        if external:
            attrs["TargetMode"] = "External"
        ET.SubElement(rt, "Relationship", attrs)
    return xml(rt)


def shape(st, obj, sid, hyperlink=None):
    sp = el(st, "p:sp")
    nv = el(sp, "p:nvSpPr")
    el(nv, "p:cNvPr", id=sid, name=(obj.get("text", obj.get("geom", "shape"))[:60]))
    el(nv, "p:cNvSpPr", **({"txBox": 1} if obj["kind"] == "text" else {}))
    el(nv, "p:nvPr")
    pr = el(sp, "p:spPr")
    xfrm(pr, obj)
    geom = el(pr, "a:prstGeom", prst=obj.get("geom", "rect"))
    av = el(geom, "a:avLst")
    if obj.get("geom") == "roundRect":
        el(av, "a:gd", name="adj", fmla="val 6500")
    if obj["kind"] == "shape":
        fill(pr, obj["fill"])
    else:
        el(pr, "a:noFill")
    ln = el(pr, "a:ln", w=0)
    el(ln, "a:noFill")
    if obj["kind"] != "text":
        return
    tx = el(sp, "p:txBody")
    bp = el(tx, "a:bodyPr", wrap="none", lIns=0, tIns=0, rIns=0, bIns=0, anchor="t")
    el(bp, "a:noAutofit")
    el(tx, "a:lstStyle")
    for linha in obj["text"].split("\n"):
        p = el(tx, "a:p")
        pp = el(p, "a:pPr", algn={"left": "l", "center": "ctr", "right": "r"}[obj["align"]])
        el(el(pp, "a:lnSpc"), "a:spcPct", val=110000)
        el(el(pp, "a:spcAft"), "a:spcPts", val=0)
        run = el(p, "a:r")
        rp = el(run, "a:rPr", lang="pt-BR", sz=round(obj["size"] * 100), b=1 if obj["bold"] else 0)
        fill(rp, obj["color"])
        for tipo in ("latin", "ea", "cs"):
            el(rp, "a:" + tipo, typeface=FONT)
        if hyperlink:
            hl = el(rp, "a:hlinkClick")
            hl.set(f"{{{NS['r']}}}id", hyperlink)
        el(run, "a:t").text = linha
        el(p, "a:endParaRPr", lang="pt-BR", sz=round(obj["size"] * 100))


def picture(st, obj, sid, rid):
    pic = el(st, "p:pic")
    nv = el(pic, "p:nvPicPr")
    el(nv, "p:cNvPr", id=sid, name=Path(obj["path"]).stem, descr="Gráfico derivado dos dados do artigo")
    el(el(nv, "p:cNvPicPr"), "a:picLocks", noChangeAspect=1)
    el(nv, "p:nvPr")
    bf = el(pic, "p:blipFill")
    blip = el(bf, "a:blip")
    blip.set(f"{{{NS['r']}}}embed", rid)
    el(el(bf, "a:stretch"), "a:fillRect")
    pr = el(pic, "p:spPr")
    xfrm(pr, obj)
    el(el(pr, "a:prstGeom", prst="rect"), "a:avLst")


def pptx(slides, destino):
    media = {p: f"image{i+1}.png" for i, p in enumerate(dict.fromkeys(o["path"] for s in slides for o in s.objetos if o["kind"] == "image"))}
    tipos = ET.Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
    for ext, tipo in [("rels", "application/vnd.openxmlformats-package.relationships+xml"), ("xml", "application/xml"), ("png", "image/png")]:
        ET.SubElement(tipos, "Default", Extension=ext, ContentType=tipo)
    overrides = {"/ppt/presentation.xml": "presentationml.presentation.main+xml",
                 "/ppt/slideMasters/slideMaster1.xml": "presentationml.slideMaster+xml",
                 "/ppt/slideLayouts/slideLayout1.xml": "presentationml.slideLayout+xml",
                 "/ppt/notesMasters/notesMaster1.xml": "presentationml.notesMaster+xml",
                 "/ppt/theme/theme1.xml": "theme+xml"}
    for i in range(1, len(slides) + 1):
        overrides[f"/ppt/slides/slide{i}.xml"] = "presentationml.slide+xml"
        overrides[f"/ppt/notesSlides/notesSlide{i}.xml"] = "presentationml.notesSlide+xml"
    for part, tipo in overrides.items():
        ET.SubElement(tipos, "Override", PartName=part, ContentType="application/vnd.openxmlformats-officedocument." + tipo)
    for part, tipo in [("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
                        ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml")]:
        ET.SubElement(tipos, "Override", PartName=part, ContentType=tipo)

    with ZipFile(destino, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", xml(tipos))
        r = ET.Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
        for rid, tipo, target in [("rId1", NS["r"] + "/officeDocument", "ppt/presentation.xml"),
                                  ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
                                  ("rId3", NS["r"] + "/extended-properties", "docProps/app.xml")]:
            ET.SubElement(r, "Relationship", Id=rid, Type=tipo, Target=target)
        z.writestr("_rels/.rels", xml(r))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        z.writestr("docProps/core.xml", f'''<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Cobertura vacinal e sarampo — progresso do projeto</dc:title><dc:creator>Gabriel Eichelberger Fontaneli; João Villanova do Amaral; Rafaele Castagnara Alves</dc:creator><dc:description>Apresentação baseada no artigo atualizado de 22/11/2026.</dc:description><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created></cp:coreProperties>''')
        z.writestr("docProps/app.xml", f'''<?xml version="1.0" encoding="UTF-8"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>ProjetoBD</Application><PresentationFormat>Widescreen</PresentationFormat><Slides>{len(slides)}</Slides><Notes>{len(slides)}</Notes></Properties>''')
        pr = root("p:presentation")
        el(el(pr, "p:sldMasterIdLst"), "p:sldMasterId", id=2147483648).set(f"{{{NS['r']}}}id", "rId1")
        el(el(pr, "p:notesMasterIdLst"), "p:notesMasterId").set(f"{{{NS['r']}}}id", f"rId{len(slides)+2}")
        ids = el(pr, "p:sldIdLst")
        for i in range(1, len(slides) + 1):
            el(ids, "p:sldId", id=255+i).set(f"{{{NS['r']}}}id", f"rId{i+1}")
        el(pr, "p:sldSz", cx=round(W*EMU), cy=round(H*EMU), type="screen16x9")
        el(pr, "p:notesSz", cx=6858000, cy=9144000)
        z.writestr("ppt/presentation.xml", xml(pr))
        rs = [("rId1", "slideMaster", "slideMasters/slideMaster1.xml", False)]
        rs += [(f"rId{i+1}", "slide", f"slides/slide{i}.xml", False) for i in range(1, len(slides)+1)]
        rs.append((f"rId{len(slides)+2}", "notesMaster", "notesMasters/notesMaster1.xml", False))
        z.writestr("ppt/_rels/presentation.xml.rels", relationships(rs))
        master = root("p:sldMaster")
        tree(el(master, "p:cSld"))
        el(master, "p:clrMap", bg1="lt1", tx1="dk1", bg2="lt2", tx2="dk2",
           **{f"accent{i}": f"accent{i}" for i in range(1, 7)}, hlink="hlink", folHlink="folHlink")
        el(el(master, "p:sldLayoutIdLst"), "p:sldLayoutId", id=2147483649).set(f"{{{NS['r']}}}id", "rId1")
        styles = el(master, "p:txStyles")
        for name in ("titleStyle", "bodyStyle", "otherStyle"):
            el(styles, "p:" + name)
        z.writestr("ppt/slideMasters/slideMaster1.xml", xml(master))
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", relationships([
            ("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml", False),
            ("rId2", "theme", "../theme/theme1.xml", False)]))
        layout = root("p:sldLayout")
        layout.set("type", "blank"); layout.set("preserve", "1")
        tree(el(layout, "p:cSld", name="Blank"))
        el(el(layout, "p:clrMapOvr"), "a:masterClrMapping")
        z.writestr("ppt/slideLayouts/slideLayout1.xml", xml(layout))
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", relationships([("rId1", "slideMaster", "../slideMasters/slideMaster1.xml", False)]))
        nm = root("p:notesMaster")
        tree(el(nm, "p:cSld"))
        el(nm, "p:clrMap", bg1="lt1", tx1="dk1", bg2="lt2", tx2="dk2",
           **{f"accent{i}": f"accent{i}" for i in range(1,7)}, hlink="hlink", folHlink="folHlink")
        z.writestr("ppt/notesMasters/notesMaster1.xml", xml(nm))
        z.writestr("ppt/notesMasters/_rels/notesMaster1.xml.rels", relationships([("rId1", "theme", "../theme/theme1.xml", False)]))
        theme = root("a:theme"); theme.set("name", "ProjetoBD")
        te = el(theme, "a:themeElements")
        cs = el(te, "a:clrScheme", name="ProjetoBD")
        for key, cor in [("dk1", INK), ("lt1", WHITE), ("dk2", NAVY), ("lt2", BG),
                         ("accent1", BLUE), ("accent2", TEAL), ("accent3", ORANGE),
                         ("accent4", RED), ("accent5", GREEN), ("accent6", "97559C"),
                         ("hlink", BLUE), ("folHlink", "97559C")]:
            el(el(cs, "a:" + key), "a:srgbClr", val=cor)
        fs = el(te, "a:fontScheme", name="Arial")
        for item in ("majorFont", "minorFont"):
            ff = el(fs, "a:" + item)
            for tipo in ("latin", "ea", "cs"):
                el(ff, "a:" + tipo, typeface=FONT)
        fm = el(te, "a:fmtScheme", name="Default")
        for tipo in ("fillStyleLst", "lnStyleLst", "effectStyleLst", "bgFillStyleLst"):
            lst = el(fm, "a:" + tipo)
            for _ in range(3):
                if tipo == "lnStyleLst":
                    item = el(lst, "a:ln", w=9525)
                    el(el(item, "a:solidFill"), "a:schemeClr", val="phClr")
                elif tipo == "effectStyleLst":
                    el(el(lst, "a:effectStyle"), "a:effectLst")
                else:
                    el(el(lst, "a:solidFill"), "a:schemeClr", val="phClr")
        z.writestr("ppt/theme/theme1.xml", xml(theme))
        for caminho, nome in media.items():
            z.write(caminho, "ppt/media/" + nome)
        for i, slide in enumerate(slides, 1):
            rt = root("p:sld")
            common = el(rt, "p:cSld")
            fill(el(el(common, "p:bg"), "p:bgPr"), slide.bg)
            st = tree(common)
            rs = [("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml", False),
                  ("rId2", "notesSlide", f"../notesSlides/notesSlide{i}.xml", False)]
            for sid, obj in enumerate(slide.objetos, 2):
                if obj["kind"] == "image":
                    rid = f"rId{len(rs)+1}"
                    rs.append((rid, "image", "../media/" + media[obj["path"]], False))
                    picture(st, obj, sid, rid)
                else:
                    rid = None
                    if obj.get("link"):
                        rid = f"rId{len(rs)+1}"
                        rs.append((rid, "hyperlink", obj["link"], True))
                    shape(st, obj, sid, rid)
            el(el(rt, "p:clrMapOvr"), "a:masterClrMapping")
            z.writestr(f"ppt/slides/slide{i}.xml", xml(rt))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", relationships(rs))
            nt = root("p:notes")
            ns = tree(el(nt, "p:cSld"))
            item = el(ns, "p:sp")
            nv = el(item, "p:nvSpPr")
            el(nv, "p:cNvPr", id=2, name="Notas do apresentador")
            el(nv, "p:cNvSpPr")
            el(el(nv, "p:nvPr"), "p:ph", type="body", idx=1)
            el(item, "p:spPr")
            tb = el(item, "p:txBody"); el(tb, "a:bodyPr"); el(tb, "a:lstStyle")
            for linha in slide.notas.split("\n"):
                p = el(tb, "a:p"); r = el(p, "a:r")
                el(r, "a:rPr", lang="pt-BR", sz=1400)
                el(r, "a:t").text = linha
            el(el(nt, "p:clrMapOvr"), "a:masterClrMapping")
            z.writestr(f"ppt/notesSlides/notesSlide{i}.xml", xml(nt))
            z.writestr(f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels", relationships([
                ("rId1", "notesMaster", "../notesMasters/notesMaster1.xml", False),
                ("rId2", "slide", f"../slides/slide{i}.xml", False)]))


def pdf(slides, destino):
    with PdfPages(destino, metadata={"Title": "Cobertura vacinal e sarampo — progresso do projeto",
                                    "Author": "Gabriel Eichelberger Fontaneli; João Villanova do Amaral; Rafaele Castagnara Alves"}) as documento:
        for num, slide in enumerate(slides, 1):
            fig = plt.figure(figsize=(W, H), facecolor="#" + slide.bg)
            ax = fig.add_axes((0, 0, 1, 1))
            ax.set(xlim=(0, W), ylim=(H, 0)); ax.axis("off")
            for obj in slide.objetos:
                x, y, w, h = (obj[k] for k in ("x", "y", "w", "h"))
                if obj["kind"] == "image":
                    with Image.open(obj["path"]) as im:
                        ax.imshow(im.convert("RGB"), extent=(x, x+w, y+h, y), aspect="auto", zorder=3)
                elif obj["kind"] == "shape":
                    attrs = dict(facecolor="#"+obj["fill"], edgecolor="none", zorder=2)
                    if obj["geom"] == "roundRect":
                        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08", **attrs))
                    elif obj["geom"] == "ellipse":
                        ax.add_patch(Ellipse((x+w/2,y+h/2),w,h,**attrs))
                    elif obj["geom"] == "rightArrow":
                        ax.add_patch(Polygon([(x,y+h*.3),(x+w*.55,y+h*.3),(x+w*.55,y),
                                              (x+w,y+h*.5),(x+w*.55,y+h),(x+w*.55,y+h*.7),(x,y+h*.7)],**attrs))
                    else:
                        ax.add_patch(Rectangle((x,y),w,h,**attrs))
                else:
                    align = obj["align"]
                    tx = x if align=="left" else x+w/2 if align=="center" else x+w
                    ax.text(tx, y, obj["text"], va="top", ha=align, fontsize=obj["size"],
                            color="#"+obj["color"], fontfamily=FONTE_PDF,
                            fontweight="bold" if obj["bold"] else "normal", linespacing=1.1,
                            zorder=4, url=obj.get("link"))
            documento.savefig(fig, facecolor=fig.get_facecolor())
            fig.savefig(PREVIEWS / f"slide_{num:02}.png", dpi=105, facecolor=fig.get_facecolor())
            plt.close(fig)


def validar(slides):
    avisos = []
    for i, s in enumerate(slides, 1):
        for obj in s.objetos:
            assert obj["x"] >= 0 and obj["y"] >= 0
            assert obj["x"]+obj["w"] <= W+0.01 and obj["y"]+obj["h"] <= H+0.01, (i,obj)
            if obj["kind"] == "text":
                altura = len(obj["text"].split("\n")) * obj["size"] * 1.1 / 72
                if altura > obj["h"] + 0.06:
                    avisos.append(dict(slide=i, texto=obj["text"], altura=round(altura,3), caixa=obj["h"]))
    return avisos


def main():
    (PASTA/"figuras").mkdir(exist_ok=True)
    PREVIEWS.mkdir(exist_ok=True)
    # Confere os números destacados na apresentação contra o recorte do artigo.
    serie = ler_csv("serie_brasil_rs_poa.csv")
    poa = next(r for r in serie if r["cod_ibge"] == "431490" and r["ano"] == "2025")
    assert (float(poa["cobertura_d1"]), float(poa["cobertura_d2"])) == (91.35, 77.47)
    assert int(poa["casos_inicio_exantema"]) == 1 and float(poa["incidencia_100k"]) == 0.072
    sens = next(r for r in ler_csv("sensibilidade_metodos.csv") if r["ano"] == "2025")
    assert [int(sens[k]) for k in ("meta_d2_media", "meta_d2_razao", "mudam_d2")] == [260, 236, 138]
    grupos = ler_csv("comparacao_grupos_2019.csv")
    assert sum(int(r["localidades"]) for r in grupos) == 266
    assert sum(int(r["casos"]) for r in grupos) == 104
    slides = montar_slides(graficos())
    avisos = validar(slides)
    if avisos:
        print(json.dumps(avisos, ensure_ascii=False, indent=2))
        raise RuntimeError("Ajustar caixas de texto antes de exportar.")
    pptx(slides, PASTA/"apresentacao_progresso.pptx")
    pdf(slides, PASTA/"apresentacao_progresso.pdf")
    roteiro = ["ROTEIRO DA APRESENTAÇÃO — 22/11/2026\n", "17 slides de conteúdo + 2 de referências. Duração sugerida: 12–15 minutos.\n"]
    for i,s in enumerate(slides,1):
        roteiro.append(f"\n{i:02}. {s.titulo}\n{s.notas}\n")
    (PASTA/"roteiro_apresentacao.txt").write_text("\n".join(roteiro),encoding="utf-8")
    (PASTA/"manifesto.json").write_text(json.dumps({"slides":len(slides), "conteudo":17, "referencias":2,
        "fonte":"../artigo_atualizado/artigo.pdf", "recorte":"2026-11-22", "formato":"16:9",
        "sha256_artigo":hashlib.sha256((ARTIGO/"artigo.pdf").read_bytes()).hexdigest(),
        "sha256_dados":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ARTIGO/"dados").glob("*.csv")},
        "texto_editavel":True, "notas_do_apresentador":True,
        "observacao":"Gráficos derivados dos CSVs do artigo. Não são capturas da interface.",
        "checagem_caixas_texto":"Sem excesso de altura ou elementos fora da área do slide."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Gerados PPTX, PDF e roteiro com {len(slides)} slides.")


if __name__ == "__main__":
    main()
