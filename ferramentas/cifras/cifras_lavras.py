"""Cifras (posição exata) das folhas da aba Lavras, tiradas do texto dos PDFs originais."""
import sys,json,re,subprocess,html,os
sys.path.insert(0,'/tmp/cif')
import fitz,numpy as np
from PIL import Image
from pdftok import letras,juntar,limpar
from acordes import eh_acorde
from louvor2 import cifras_da_pagina
R='/home/claude/musicas-ipb/'; P=R+'public/midias/pdf/'
C=json.load(open(R+'public/data/catalogo.json'))
usadas=set()
for s in C['secoes']:
    if s['id']!='lavras': continue
    for it in s['itens']:
        for p in it['paginas']: usadas.add(p['img'])
def tam(img):
    with Image.open(R+'public'+img) as im: return im.size
def r1(v): return round(float(v),1)
def cifra(t,sc,dx=0.0,dy=0.0,kf=1.0,sobe=None,desce=None):
    """token (pontos do PDF) -> [x, base, w, fs, txt, 0, 0, sobe, desce] em pixels da imagem"""
    fs=t['s']*sc*kf
    out=[round(t['x']*sc-dx),round(t['base']*sc-dy),round(t['w']*sc),r1(fs),t['txt']]
    # só informa a altura do retângulo quando passa do padrão (expoentes e índices)
    so=t['sobe']*sc; de=t['desce']*sc
    if so>0.84*fs or de>0.27*fs: out+=[0,0,round(max(so,0.82*fs)),round(max(de,0.08*fs))]
    return out
FOLHAS={}
rel=dict(vu=0,vu_fora=0,louvor=0,cc=0)
# ---------- Cânticos Antigos – Volume Único ----------
VU=fitz.open(P+'canticos-antigos-cifrados-volume-unico.pdf')
_tok={}
def tokens_vu(pp):
    if pp not in _tok:
        T=[]
        for t in juntar(letras(VU[pp-1],lambda s:s['color']==0x800000),dy_abs=6.6):
            if re.search(r'.\(\*\)$',t['txt']) and len(t['chars'])==len(t['txt']):
                g=t['chars'][:-3]; t=dict(t,txt=t['txt'][:-3],chars=g,x=min(c['x0'] for c in g),w=max(c['x1'] for c in g)-min(c['x0'] for c in g))
            t=limpar(t)
            if t: T.append(t)
        _tok[pp]=T
    return _tok[pp]
# páginas inteiras
for img in sorted(usadas):
    m=re.match(r'/midias/lavras2/antigos-(\d+)\.jpg',img)
    if not m: continue
    pp=int(m.group(1)); w,h=tam(img); sc=w/VU[pp-1].rect.width
    c=[cifra(t,sc) for t in tokens_vu(pp)]
    FOLHAS[img]=dict(w=w,h=h,f='t',n=1,c=c); rel['vu']+=len(c)
# recortes (mesma conta de /tmp/vu/render.py)
pdfvu=P+'canticos-antigos-cifrados-volume-unico.pdf'
_w={}
def words(pp):
    if pp not in _w:
        o=subprocess.run(['pdftotext','-f',str(pp),'-l',str(pp),'-bbox',pdfvu,'-'],capture_output=True,text=True).stdout
        _w[pp]=[(float(a),float(b),float(c),float(d),html.unescape(t)) for a,b,c,d,t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',o)]
    return _w[pp]
_pg={}
def pagina(pp):
    if pp not in _pg:
        o=subprocess.run(['pdftotext','-f',str(pp),'-l',str(pp),'-bbox-layout',pdfvu,'-'],capture_output=True,text=True).stdout
        _pg[pp]=(float(re.search(r'<page width="([\d.]+)"',o).group(1)),float(re.search(r'height="([\d.]+)"',o).group(1)))
    return _pg[pp]
def gutter(pp,W):
    ws=[w for w in words(pp) if 30<w[1]<780]
    best=None
    for x in np.arange(240,360,0.5):
        n=sum(1 for w in ws if w[0]<x<w[2]); key=(n,abs(x-W/2))
        if best is None or key<best[0]: best=(key,x)
    return best[1]
ent=json.load(open('/tmp/vu/indice_final.json')); segs=json.load(open('/tmp/vu/segs.json')); names=json.load(open('/tmp/vu/names.json'))
SC=2490/597.6
conf=[]
for i,e in enumerate(ent):
    img='/midias/lavras3/'+names[str(i)]
    if img not in usadas: continue
    pp,c,y0,y1=segs[str(i)][0]; W,H=pagina(pp); sc=2490/W
    sp=gutter(pp,W)
    cb=[w for w in words(pp) if w[1]<780 and not re.fullmatch(r'\d+',w[4].strip()) and (((w[0]+w[2])/2<sp)==(c==0)) and w[1]>=y0-2 and w[3]<=y1+20]
    x0=max(0,min(b[0] for b in cb)-16); x1=min(W,max(b[2] for b in cb)+16)
    if c==0: x1=min(x1,sp+1)
    else: x0=max(x0,sp-1)
    ya=max(0,y0); yb=min(H,y1)
    px0,py0=int(x0*sc),int(ya*sc); cw,ch=int(x1*sc)-px0,int(yb*sc)-py0
    w,h=tam(img)
    if abs(cw-w)>1 or abs(ch-h)>1: conf.append((img,(cw,ch),(w,h)))
    cs=[]
    for t in tokens_vu(pp):
        cx=(t['x']+t['w']/2)*sc-px0; cy=t['base']*sc-py0
        if -2<=cx<=w+2 and 4<=cy<=h+4: cs.append(cifra(t,sc,px0,py0))
        elif ya-1<=t['base']<=yb+1 and ((t['x']+t['w']/2<sp)==(c==0)): rel['vu_fora']+=1
    FOLHAS[img]=dict(w=w,h=h,f='t',n=1,c=cs); rel['vu']+=len(cs)
print('recortes com tamanho diferente do esperado:',len(conf),conf[:5])
# ---------- Pasta de Louvor ----------
LV=fitz.open(P+'cifras-pasta-de-louvor-2025.pdf')
for img in sorted(usadas):
    m=re.match(r'/midias/lavras2/louvor-(\d+)\.jpg',img)
    if not m: continue
    pp=int(m.group(1)); w,h=tam(img); sc=w/LV[pp-1].rect.width
    cs=[cifra(t,sc,kf=0.93) for t in cifras_da_pagina(LV[pp-1])[0]]
    FOLHAS[img]=dict(w=w,h=h,f='s',c=cs); rel['louvor']+=len(cs)
# ---------- Cifra Club ----------
for pref,arq in (('jesuscentro','jesus-e-o-centro-part-julia-vitoria.pdf'),('elevem','ele-vem-pra-te-salvar-adhemar-de-campos.pdf')):
    D=fitz.open(P+arq); tom=None
    for pn in range(len(D)):
        img=f'/midias/lavras2/{pref}-{pn+1}.jpg'
        if img not in usadas: continue
        w,h=tam(img); sc=w/D[pn].rect.width
        T=juntar(letras(D[pn],lambda s:s['color']==0xee6600 and 'Mono' in s['font']),folga=0.3)
        cs=[cifra(t,sc) for t in map(limpar,T) if t]
        if pn==0:
            K=juntar(letras(D[pn],lambda s:s['color']==0xee6600 and s['font']=='Roboto-Bold'),folga=0.12)
            K.sort(key=lambda t:(round(t['base']),t['x']))
            txt=' '.join(t['txt'] for t in K)
            m=re.search(r'forma de ([A-G][#b]?m?)\)',txt)
            if m: tom=m.group(1)
            elif K and eh_acorde(K[0]['txt']): tom=K[0]['txt']
            print('   rótulo de tom:',txt[:60])
        FOLHAS[img]=dict(w=w,h=h,f='m',c=cs); rel['cc']+=len(cs)
        if tom: FOLHAS[img]['k']=tom
    print(pref,'tom escrito:',tom)
# ---------- os mesmos dados para o leitor de PDF (em pontos da página) ----------
def cifra_pt(t,kf=1.0):
    fs=t['s']*kf
    out=[round(t['x'],1),round(t['base'],1),round(t['w'],1),round(fs,2),t['txt']]
    if t['sobe']>0.84*fs or t['desce']>0.27*fs: out+=[0,0,round(max(t['sobe'],0.82*fs),1),round(max(t['desce'],0.08*fs),1)]
    return out
def gravar_pdf(nome,folhas):
    fn=R+f'public/data/cifras/pdf-{nome}.json'
    json.dump(dict(v=1,folhas=folhas),open(fn,'w'),ensure_ascii=False,separators=(',',':'))
    print('  pdf',nome,len(folhas),'páginas com cifras,',sum(len(f['c']) for f in folhas.values()),'cifras,',os.path.getsize(fn)//1024,'KB')
F={}
for pn in range(len(VU)):
    c=[cifra_pt(t) for t in tokens_vu(pn+1)]
    if c: F[str(pn+1)]=dict(w=round(VU[pn].rect.width,1),h=round(VU[pn].rect.height,1),f='t',n=1,c=c)
gravar_pdf('canticos-antigos-cifrados-volume-unico',F)
F={}
for pn in range(len(LV)):
    c=[cifra_pt(t,0.93) for t in cifras_da_pagina(LV[pn])[0]]
    if c: F[str(pn+1)]=dict(w=round(LV[pn].rect.width,1),h=round(LV[pn].rect.height,1),f='s',c=c)
gravar_pdf('cifras-pasta-de-louvor-2025',F)
for arq,tomk in (('jesus-e-o-centro-part-julia-vitoria.pdf','D'),('ele-vem-pra-te-salvar-adhemar-de-campos.pdf','D')):
    D=fitz.open(P+arq); F={}
    for pn in range(len(D)):
        T=juntar(letras(D[pn],lambda s:s['color']==0xee6600 and 'Mono' in s['font']),folga=0.3)
        c=[cifra_pt(t) for t in map(limpar,T) if t]
        if c: F[str(pn+1)]=dict(w=round(D[pn].rect.width,1),h=round(D[pn].rect.height,1),f='m',k=tomk,c=c)
    gravar_pdf(arq[:-4],F)
falt=[u for u in sorted(usadas) if u not in FOLHAS]
vaz=[u for u,f in FOLHAS.items() if not f['c']]
print(rel,'| folhas',len(FOLHAS),'| sem dados',len(falt),falt[:5],'| sem nenhuma cifra',len(vaz),vaz[:12])
json.dump(dict(v=1,folhas=FOLHAS),open(R+'public/data/cifras/lavras.json','w'),ensure_ascii=False,separators=(',',':'))
print(os.path.getsize(R+'public/data/cifras/lavras.json')//1024,'KB')
