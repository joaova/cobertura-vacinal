"""Compila o pitch no tema Inf e produz PPTX com texto nativo editável.

O PDF Beamer é a versão visual de referência. Para o PPTX, extrai as caixas de
texto, mantém a geometria das figuras em fundos sem texto e usa Arial como
alternativa portátil à Latin Modern do LaTeX. Nunca rasteriza o texto narrativo.
"""
from pathlib import Path
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parent))
import gerar_apresentacao as b
from PIL import ImageFont

P=Path(__file__).resolve().parent
OUT=P/'pitch'
BUILD=Path('/tmp/projetobd-pitch/build')
BUILD.mkdir(parents=True,exist_ok=True)
SVG='http://www.w3.org/2000/svg'
XLINK='http://www.w3.org/1999/xlink'
TIMES=[20,45,30,35,30,35,35,30,40,0]
TITLES=['Cobertura vacinal e incidência de sarampo no RS','Motivação e contexto',
        'Objetivo do projeto','Etapas de tratamento e integração',
        'Tecnologias utilizadas','Implementação do dashboard',
        'Cobertura da segunda dose em 2025','Validação e avaliação do dashboard',
        'Perspectivas futuras','Fontes e referências']

def run(args):
    result=subprocess.run(args,cwd=OUT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(result.stdout[-4000:])
    return result.stdout

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def strip_text(svg_path,page):
    tree=ET.parse(svg_path)
    root=tree.getroot()
    # Os números de seção são decoração do tema e ultrapassam o limite superior.
    # Permanecem como formas no fundo para reproduzir seu recorte original.
    for parent in root.iter():
        for child in list(parent):
            if child.tag=='{'+SVG+'}use' and child.get('{'+XLINK+'}href','').startswith('#glyph'):
                href=child.get('{'+XLINK+'}href','')
                keep=2<=page<=9 and href.startswith('#glyph-0-')
                if not keep:
                    parent.remove(child)
    tree.write(svg_path,encoding='utf-8',xml_declaration=True)

def text_value(node):
    return ''.join(node.itertext()).replace('\u2212','−')

def plain_tex(s):
    s=re.sub(r'\\(?:textbf|destaque)\{([^{}]*)\}',r'\1',s)
    return s.replace(r'\%', '%').replace(r'\_', '_').replace('~',' ')

def main():
    serie=b.ler_csv('serie_brasil_rs_poa.csv')
    assert [float(next(r for r in serie if r['nome_localidade']==n and r['ano']=='2025')['cobertura_d2'])
            for n in ['Brasil','Rio Grande do Sul','Porto Alegre']]==[78.72,84.62,77.47]
    for _ in range(2):
        run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape',
             '-output-directory='+str(BUILD),'apresentacao_pitch.tex'])
    pdf=BUILD/'apresentacao_pitch.pdf'
    shutil.copyfile(pdf,OUT/pdf.name)
    run(['pdftohtml','-xml','-hidden','-nodrm','-i','-noroundcoord','-zoom','1',str(pdf),str(BUILD/'texto.xml')])
    pages=ET.parse(BUILD/'texto.xml').getroot().findall('page')
    assert len(pages)==10
    src=(OUT/'apresentacao_pitch.tex').read_text()
    notes=['Tempo: 20 segundos. Apresentamos os resultados parciais do projeto sobre cobertura da vacina tríplice viral e incidência de sarampo no Rio Grande do Sul, desenvolvido no contexto do PET-Saúde Digital. O trabalho integra dados públicos em um dashboard de consulta territorial e temporal.']
    notes.extend(plain_tex(s) for s in re.findall(r'\\note\{(.*?)\}\s*\\end\{frame\}',src,re.S))
    assert len(notes)==10
    assets=OUT/'fundos'
    assets.mkdir(exist_ok=True)
    fonts={}
    slides=[]
    export=[]
    for idx,page in enumerate(pages,1):
        svg_path=BUILD/f'fundo_{idx:02}.svg'
        run(['pdftocairo','-f',str(idx),'-l',str(idx),'-svg',str(pdf),str(svg_path)])
        strip_text(svg_path,idx)
        png=assets/f'fundo_{idx:02}.png'
        run(['rsvg-convert','-w','1920','-h','1080','-o',str(png),str(svg_path)])
        for font in page.findall('fontspec'):fonts[font.get('id')]=font.attrib
        pw,ph=float(page.get('width')),float(page.get('height'))
        sx,sy=b.W/pw,b.H/ph
        s=b.Slide.__new__(b.Slide)
        s.titulo,s.secao,s.bg,s.notas=TITLES[idx-1],'Pitch','FFFFFF',notes[idx-1]
        s.objetos=[dict(kind='image',path=str(png),x=0.,y=0.,w=b.W,h=b.H)]
        for text in page.findall('text'):
            value=text_value(text)
            top=float(text.get('top'))
            if top<0:continue
            f=fonts[text.get('font')]
            x=float(text.get('left'))*sx
            y=top*sy
            w=float(text.get('width'))*sx
            h=float(text.get('height'))*sy
            color=f['color'].lstrip('#').upper()
            if value.strip()=='•':
                # Símbolo decorativo da lista, sem caractere de bullet digitado.
                r=.045
                s.objetos.append(dict(kind='shape',x=x+w/2-r,y=y+h*.55-r,w=r*2,h=r*2,
                                      fill=color,geom='ellipse',border=None))
                continue
            size=float(f['size'])*sx*72
            bold=text.find('b') is not None
            font=ImageFont.truetype(b.FONTE_NEGRITO if bold else b.FONTE_NORMAL,1000)
            measured=font.getlength(value)/1000*size/72
            # Uma linha por caixa; mantém o corpo legível no fallback Arial.
            size*=min(1.,w/max(measured,1e-6))
            obj=dict(kind='text',text=value,x=x,y=y,w=min(w+.055,b.W-x),h=max(h+.05,size*1.2/72),
                     size=round(size,3),color=color,bold=bold,align='left')
            link=text.find('.//a')
            if link is not None:obj['link']=link.get('href')
            s.objetos.append(obj)
        slides.append(s)
        export.append(dict(titulo=s.titulo,tempo_s=TIMES[idx-1],notas=s.notas,objetos=s.objetos))
    b.pptx(slides,OUT/'apresentacao_pitch.pptx')
    # Prévias da versão editável; o PDF principal continua sendo o Beamer original.
    b.PREVIEWS=BUILD/'pptx-previas'
    b.PREVIEWS.mkdir(exist_ok=True)
    b.pdf(slides,BUILD/'pptx-previas.pdf')
    (OUT/'elementos_pitch.json').write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n')
    script=['PITCH DOS RESULTADOS PARCIAIS — 23/11/2026',
            '9 slides para 5 minutos + 1 slide de referências para apoio.',
            'Recorte documental e computacional dos dados: 22/11/2026.\n']
    elapsed=0
    for i,(title,note,secs) in enumerate(zip(TITLES,notes,TIMES),1):
        end=elapsed+secs
        script.append(f'{i:02}. {title}\n{elapsed//60}:{elapsed%60:02}–{end//60}:{end%60:02} ({secs}s)\n{note}\n')
        elapsed=end
    assert elapsed==300
    (OUT/'roteiro_pitch.txt').write_text('\n'.join(script),encoding='utf-8')
    sources=[P/'template_slides.txt',OUT/'beamerthemeInf.sty',OUT/'inf-logo-dark.pdf',OUT/'inf-logo-white.pdf',
             OUT/'apresentacao_pitch.tex',b.ARTIGO/'dados/serie_brasil_rs_poa.csv']
    manifest=dict(slides=10,slides_pitch=9,slides_apoio=1,duracao_s=300,formato='16:9',
        recorte_dados='2026-11-22',data_apresentacao='2026-11-23',tema='Inf original fornecido pelo usuário',
        arquivo_tema_preservado=sha(OUT/'beamerthemeInf.sty')==sha(P/'Template_slides_inf_ufrgs/beamerthemeInf.sty'),
        requisitos=['motivação','objetivo','metodologia','tecnologias utilizadas','resultados parciais'],
        texto_editavel=True,notas_pptx=10,pdf_principal='PDF Beamer com o tema e os logotipos originais',
        pptx='Texto nativo com fallback Arial; figuras e decoração em fundos sem texto narrativo.',
        sha256_fontes={str(f.relative_to(P.parent)):sha(f) for f in sources},
        sha256_entregas={n:sha(OUT/n) for n in ['apresentacao_pitch.pdf','apresentacao_pitch.pptx','apresentacao_pitch.tex']})
    (OUT/'manifesto_pitch.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Pitch gerado: PDF Beamer, PPTX editável e roteiro, com 10 slides.')
if __name__=='__main__':main()

