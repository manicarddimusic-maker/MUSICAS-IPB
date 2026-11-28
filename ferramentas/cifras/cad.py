"""Cifras do Caderninho (fotos de um livreto impresso: cifras em negrito itálico sobre a letra)."""
import sys,json,os,re,time
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nc')
import cv2,numpy as np
from ncocr import candidatos,limiar_da_pagina,tess
from nccomum import recorte,lote
from ncglifo import Vocab,casar,calibrar_hx
from acordes import eh_acorde
ITAL='/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf'
_V=None
def vocab():
    global _V
    if _V is None: _V=Vocab(fonte=ITAL)
    return _V
def aplainar(g):
    """tira a variação de luz da foto: papel vira branco"""
    k=max(31,int(min(g.shape)*0.06))|1
    fundo=cv2.morphologyEx(g,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    fundo=cv2.GaussianBlur(fundo,(0,0),k/3)
    n=np.clip(g.astype(np.float32)/np.maximum(fundo.astype(np.float32),1)*255,0,255)
    return n.astype(np.uint8),fundo
def alturas_das_cifras(b):
    """altura das maiúsculas das cifras, pelas palavras que o tesseract lê como acorde"""
    s=min(1.0,2200/max(b.shape)); small=cv2.resize(b,None,fx=s,fy=s,interpolation=cv2.INTER_AREA) if s<1 else b
    fd='/tmp/cif/dbg/cad_%d.png'%os.getpid(); cv2.imwrite(fd,small)
    import subprocess
    r=subprocess.run(['tesseract',fd,'-','-l','por','--psm','6','tsv'],capture_output=True,text=True).stdout; os.remove(fd)
    hs=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        t=c[11].strip()
        if float(c[10])>=60 and len(t)>=2 and eh_acorde(t) and re.search(r'[0-9#mb/]',t): hs.append(int(c[9])/s)
    return hs
def bruto(caminho):
    V=vocab()
    cor=cv2.imread(caminho); g=cv2.cvtColor(cor,cv2.COLOR_BGR2GRAY)
    b,fundo=aplainar(g)
    hs=alturas_das_cifras(b)
    out=dict(img=caminho,w=int(g.shape[1]),h=int(g.shape[0]),caps=[],toks=[])
    if len(hs)<3: return out
    hs=sorted(hs); grupos=[[hs[0]]]
    for h in hs[1:]:
        if h<=grupos[-1][0]*1.22: grupos[-1].append(h)
        else: grupos.append([h])
    caps=[float(np.median(x)) for x in grupos if len(x)>=3] or [float(np.median(hs))]
    vistos=[]
    for cap in caps[:2]:
        d=cap/1.7; lim=limiar_da_pagina(b,d,alvo=0.19)
        toks,lab,_=candidatos(b,d,lim)
        sel=[t for t in toks if 0.82*cap<=t['cap']<=1.25*cap and t['sw']>=0.12*t['cap']]
        sel=[t for t in sel if not any(abs(t['x0']-o[0])<3 and abs(t['base']-o[1])<3 for o in vistos)]
        if not sel: continue
        tes=lote([recorte(b,lab,t) for t in sel],7,'cad')
        hx,nhx=calibrar_hx(V,sel,tes,padrao=1.0)
        out['caps'].append(dict(cap=round(cap,1),lim=lim,hx=round(hx,3),nhx=nhx))
        for t,(tx,cf) in zip(sel,tes):
            r=casar(V,b,lab,t,lim,hx)
            # cor do papel em volta da palavra
            y0,y1=max(0,t['y0']-4),min(g.shape[0],t['y1']+4); x0,x1=max(0,t['x0']-4),min(g.shape[1],t['x1']+4)
            reg=cor[y0:y1,x0:x1].reshape(-1,3); claro=reg[reg.sum(axis=1)>=np.percentile(reg.sum(axis=1),60)]
            bg=[int(v) for v in np.median(claro,axis=0)[::-1]] if len(claro) else [255,255,255]
            out['toks'].append(dict(x0=int(t['x0']),x1=int(t['x1']),y0=int(t['y0']),y1=int(t['y1']),base=int(t['base']),cap=int(t['cap']),sw=round(float(t['sw']),2),n=len(t['cs']),
                c=[[round(float(v),3),x] for v,x in r[:5]],t=[tx,round(float(cf))],pa=0,p=1,bg='%02x%02x%02x'%tuple(bg),capref=round(cap,1)))
            vistos.append((t['x0'],t['base']))
    return out
if __name__=='__main__':
    t0=time.time(); r=bruto(sys.argv[1]); print(r['caps'],len(r['toks']),'%.1fs'%(time.time()-t0))
    for t in sorted(r['toks'],key=lambda t:(round(t['base']/ (2.5*t['capref'])),t['x0']))[:70]:
        print(t['x0'],t['base'],'cap',t['cap'],'sw %.2f'%(t['sw']/t['cap']),t['c'][:2],t['t'],t['bg'])
    json.dump(r,open('/tmp/cif/cad_teste.json','w'))
