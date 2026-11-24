"""Exporte les sources françaises en rapport et présentation PDF, puis rend les pages."""
from pathlib import Path
import hashlib
import html
import json
import re
import subprocess
from datetime import datetime,timezone
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,KeepTogether
from pypdf import PdfReader

ROOT=Path('/project');OUT=ROOT/'output/pdf';TMP=ROOT/'tmp/pdfs';OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
for name,file in [('DejaVu','DejaVuSans.ttf'),('DejaVu-Bold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/dejavu/'+file))
styles=getSampleStyleSheet()
for name in styles.byName:styles[name].fontName='DejaVu'
styles['Normal'].fontSize=9;styles['Normal'].leading=13.5;styles['Normal'].spaceAfter=6
for name,size in [('Title',23),('Heading1',18),('Heading2',14),('Heading3',11)]:styles[name].fontName='DejaVu-Bold';styles[name].fontSize=size;styles[name].leading=size*1.3;styles[name].spaceBefore=12;styles[name].keepWithNext=1;styles[name].spaceAfter=9
styles.add(ParagraphStyle(name='Cell',fontName='DejaVu',fontSize=7.5,leading=11))
styles.add(ParagraphStyle(name='CaptionBC1',fontName='DejaVu',fontSize=8,leading=11,textColor=colors.HexColor('#475569')))

def inline(s):
    s=html.escape(s).replace('—','-').replace('–','-').replace('→',' vers ')
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:m[1] if re.match(r'[^)]*\.md(#|$)',m[2]) else m[1]+' ['+m[2]+']',s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    return s.replace('`','')

def footer(c,doc):
    c.saveState();c.setFont('DejaVu',8);c.setFillColor(colors.HexColor('#475569'));c.drawString(42,25,'Thomas Gassmann - RNCP40875 BC1 - 23 novembre 2026');c.drawRightString(A4[0]-42,25,str(doc.page));c.restoreState()

source=ROOT/'docs/rapport.md';lines=source.read_text().splitlines();story=[];i=0
while i<len(lines):
    line=lines[i];i+=1
    if not line.strip():continue
    if line.startswith('```'):
        block=[]
        while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
        i+=1
        story.append(Paragraph('Flux métier : PaySim, Kafka, Spark, HDFS, MongoDB, MLlib, Gephi et API. PostgreSQL conserve les décisions. Ollama produit les brouillons soumis à relecture. Diagramme Mermaid modifiable dans docs/rapport.md.',styles['Normal']))
    elif line.startswith('!['):
        m=re.match(r'!\[(.*?)\]\((.*?)\)',line)
        if m:
            path=source.parent/m[2];im=Image(str(path));im._restrictSize(A4[0]-84,330);story.extend([im,Paragraph(inline(m[1]),styles['CaptionBC1']),Spacer(1,10)])
    elif line.startswith('|'):
        rows=[line]
        while i<len(lines) and lines[i].startswith('|'):rows.append(lines[i]);i+=1
        rows=[r for r in rows if not re.match(r'^\|[\s:|\-]+\|$',r)]
        data=[[Paragraph(inline(v.strip()),styles['Cell']) for v in r.strip('|').split('|')] for r in rows]
        n=len(data[0]);table=Table(data,colWidths=[(A4[0]-84)/n]*n,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e8f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#cbd5e1')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([table,Spacer(1,12)])
    elif line.startswith('#'):
        level=len(line)-len(line.lstrip('#'));story.append(Paragraph(inline(line.lstrip('#').strip()),styles['Title' if level==1 else 'Heading'+str(min(level-1,3))]))
    else:
        para=[line]
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','![')):para.append(lines[i]);i+=1
        story.append(Paragraph(inline(' '.join(para)),styles['Normal']))
report=OUT/'rapport-technique-bc1.pdf'
SimpleDocTemplate(str(report),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=44,title='Rapport technique BC1 - Thomas Gassmann',author='Thomas Gassmann').build(story,onFirstPage=footer,onLaterPages=footer)

slides=json.loads((ROOT/'docs/presentation.json').read_text())
W,H=landscape(A4);deck=OUT/'soutenance-bc1.pdf';c=canvas.Canvas(str(deck),pagesize=(W,H));c.setTitle('BC1 - Détection de fraude et réseaux financiers');c.setAuthor('Thomas Gassmann')
for index,s in enumerate(slides,1):
    c.setFillColor(colors.HexColor('#0f172a'));c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(colors.HexColor('#67e8f9'));c.setFont('DejaVu',10);c.drawString(44,H-35,'RNCP40875 / BC1 / THOMAS GASSMANN')
    title=Paragraph(html.escape(s['title']),ParagraphStyle(name='SlideTitle',fontName='DejaVu-Bold',fontSize=25,leading=32,textColor=colors.white));_,height=title.wrap(W-88,100);title.drawOn(c,44,H-65-height);y=H-95-height
    if s.get('image'):
        path=ROOT/s['image'];c.drawImage(str(path),44,105,width=W-88,height=y-110,preserveAspectRatio=True,anchor='c')
    else:
        for text in s['paragraphs']:
            p=Paragraph(inline(text),ParagraphStyle(name='SlideBody',fontName='DejaVu',fontSize=17,leading=25,textColor=colors.HexColor('#f1f5f9')));_,h=p.wrap(W-88,H);y-=h
            if y<83:raise ValueError('Slide overflow '+str(index))
            p.drawOn(c,44,y);y-=20
    c.setFont('DejaVu',9);c.setFillColor(colors.HexColor('#94a3b8'));c.drawString(44,40,s['source']);c.drawRightString(W-44,40,f'{index} / {len(slides)}');c.showPage()
c.save()
manifest={'created_at':datetime.now(timezone.utc).isoformat(),'candidate':'Thomas Gassmann','solo':True,'deadline':'non communiquée','oral_rehearsal_performed':False,'outputs':[]}
for path in (report,deck):
    reader=PdfReader(path);assert all(p.extract_text().strip() for p in reader.pages)
    assert 'thomas gassmann' in ''.join(p.extract_text() for p in reader.pages).lower()
    prefix=TMP/path.stem;subprocess.run(['pdftoppm','-r','80','-png',str(path),str(prefix)],check=True,stdout=subprocess.DEVNULL)
    manifest['outputs'].append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':len(reader.pages),'text_extraction_checked':True,'rendered':True})
(ROOT/'docs/evidence/p9/pdf-export.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest))
