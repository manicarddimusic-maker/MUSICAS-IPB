"""Lê as cifras impressas (negrito, sem serifa) de uma página de partitura do hinário."""
import sys,os,re,subprocess,tempfile,json
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from ncpauta import linhas_finas,espaco
from acordes import eh_acorde
WL='ABCDEFGMabdgijmnsu#+-/()0123456789º°'
FONTE='/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf'
def espaco_pauta(e):
    d=espaco(linhas_finas(e))
    return d if d else 0.0058*e.shape[0]
def componentes(e,cap,lim=150):
    bw=(e<lim).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(bw,8)
    dt=cv2.distanceTransform(bw,cv2.DIST_L2,3)
    comps=[]
    for i in range(1,n):
        x,y,w,h,a=[int(v) for v in st[i]]
        if h<0.2*cap or h>1.8*cap or w>5.5*cap or a<0.025*cap*cap: continue
        if w>2.2*cap and h<0.5*cap: continue          # traço horizontal (linha, ligadura)
        vals=dt[y:y+h,x:x+w][lab[y:y+h,x:x+w]==i]
        comps.append(dict(x=x,y=y,w=w,h=h,a=a,sw=2*float(np.percentile(vals,90)),id=i))
    return comps,lab
def agrupar(comps,cap):
    """junta glifos vizinhos em palavras (da esquerda para a direita)"""
    comps=sorted(comps,key=lambda c:c['x']); toks=[]
    for c in comps:
        best=None
        for t in toks:
            gap=c['x']-t['x1']
            if gap>0.21*cap or c['x']<t['x0']-2: continue
            ov=min(t['y1'],c['y']+c['h'])-max(t['y0'],c['y'])
            if ov>0.4*min(c['h'],t['y1']-t['y0']) or (c['h']<0.45*cap and t['y0']-0.15*cap<=c['y'] and c['y']+c['h']<=t['y1']+0.15*cap):
                if best is None or gap<c['x']-best['x1']: best=t
        if best is None: toks.append(dict(x0=c['x'],x1=c['x']+c['w'],y0=c['y'],y1=c['y']+c['h'],cs=[c]))
        else:
            best['x1']=max(best['x1'],c['x']+c['w']); best['y0']=min(best['y0'],c['y']); best['y1']=max(best['y1'],c['y']+c['h']); best['cs'].append(c)
    return toks
def candidatos(e,d,lim=150):
    cap=1.7*d
    comps,lab=componentes(e,cap,lim)
    toks=agrupar(comps,cap)
    out=[]
    for t in toks:
        h=t['y1']-t['y0']; w=t['x1']-t['x0']
        altos=[c for c in t['cs'] if c['h']>=0.8*cap]
        if not altos or h>1.75*cap or w<0.3*cap or w>7.5*cap: continue
        prim=min(altos,key=lambda c:c['x'])
        if prim['x']>t['x0']+0.45*cap: continue            # tem de começar por letra alta (a raiz); tolera "(" antes
        if not (0.84*cap<=prim['h']<=1.3*cap): continue
        sw=float(np.median([c['sw'] for c in altos]))
        if sw<0.12*cap or sw>0.34*cap: continue
        # linha de base: pé das letras altas (parênteses e vírgulas descem mais)
        pes=sorted(c['y']+c['h'] for c in altos); base=pes[len(pes)//2] if len(pes)>2 else prim['y']+prim['h']
        if prim['y']+prim['h']<base-0.2*cap: base=prim['y']+prim['h']
        t.update(base=int(base),cap=int(prim['h']),sw=sw)
        out.append(t)
    return out,lab,cap
_pref={}
def prefixo(H):
    if H not in _pref:
        f=ImageFont.truetype(FONTE,int(round(H/0.716)))
        im=Image.new('L',(int(H*2.2),int(H*2.4)),255); dr=ImageDraw.Draw(im)
        dr.text((int(H*0.2),int(H*1.6)),'AA',font=f,fill=0,anchor='ls')
        _pref[H]=np.array(im)
    return _pref[H]
def montar_linhas(e,lab,toks,H=44,binar=False):
    """uma linha por cifra: [AA] espaço [cifra]; devolve imagem e a lista de (y0,y1,x_cifra) de cada linha"""
    alt=int(H*2.4); bl=int(H*1.6); pre=prefixo(H); xc=pre.shape[1]+int(H*1.4)
    linhas=[];W=0
    for t in toks:
        pad=int(0.25*t['cap'])+2
        x0,y0=max(0,t['x0']-pad),max(0,t['y0']-pad); x1,y1=min(e.shape[1],t['x1']+pad),min(e.shape[0],t['y1']+pad)
        ids=np.array([c['id'] for c in t['cs']])
        m=np.isin(lab[y0:y1,x0:x1],ids).astype(np.uint8)
        m=cv2.dilate(m,np.ones((5,5),np.uint8))
        g=np.where(m>0,e[y0:y1,x0:x1],255).astype(np.uint8)
        k=H/t['cap']
        g=cv2.resize(g,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
        if binar: g=cv2.threshold(cv2.GaussianBlur(g,(0,0),0.8),140,255,cv2.THRESH_BINARY)[1]
        by=int(round((t['base']-y0)*k))       # linha de base dentro do recorte
        lin=np.full((alt,xc+g.shape[1]+int(H)),255,np.uint8)
        lin[:,:pre.shape[1]]=pre
        ya=bl-by; ga=max(0,-ya); yb=min(alt,ya+g.shape[0])
        if yb>max(0,ya): lin[max(0,ya):yb,xc:xc+g.shape[1]]=g[ga:ga+yb-max(0,ya)]
        linhas.append(lin); W=max(W,lin.shape[1])
    return linhas,W,alt,xc
def tess(img,psm=6):
    fd,fn=tempfile.mkstemp(suffix='.png',dir='/tmp/cif/dbg'); os.close(fd); cv2.imwrite(fn,img)
    r=subprocess.run(['tesseract',fn,'-','-l','eng','--psm',str(psm),'-c','tessedit_char_whitelist='+WL,'tsv'],capture_output=True,text=True).stdout
    os.remove(fn); out=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        out.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11].strip()))
    return out
def ler(e,lab,toks,H=44,binar=False,bloco=36):
    """devolve [(texto, confiança)] para cada token"""
    res=[('',0.0)]*len(toks)
    linhas,W,alt,xc=montar_linhas(e,lab,toks,H,binar)
    for a in range(0,len(toks),bloco):
        parte=linhas[a:a+bloco]
        tela=np.full((alt*len(parte)+20,W+40),255,np.uint8)
        for i,l in enumerate(parte): tela[10+i*alt:10+(i+1)*alt,20:20+l.shape[1]]=l
        ws=tess(tela)
        por={}
        for w in ws:
            i=int((w['y']+w['h']/2-10)//alt)
            if 0<=i<len(parte): por.setdefault(i,[]).append(w)
        for i,lst in por.items():
            lst.sort(key=lambda w:w['x'])
            cif=[w for w in lst if w['x']+w['w']/2>20+xc-0.5*H]
            pre=[w for w in lst if w not in cif]
            txt=''.join(w['t'] for w in cif); conf=min([w['conf'] for w in cif],default=0.0)
            # se o tesseract colou o prefixo na cifra
            if not cif and pre:
                j=''.join(w['t'] for w in pre)
                if j.startswith('AA') and len(j)>2: txt=j[2:]; conf=min(w['conf'] for w in pre)*0.8
            res[a+i]=(txt,conf)
    return res
if __name__=='__main__':
    pg=int(sys.argv[1])
    e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
    d=espaco_pauta(e); toks,lab,cap=candidatos(e,d)
    print('d=%.1f cap=%.1f candidatos=%d'%(d,cap,len(toks)))
    r1=ler(e,lab,toks,44,False); r2=ler(e,lab,toks,56,True)
    toks_=sorted(range(len(toks)),key=lambda i:(round(toks[i]['base']/(2.2*cap)),toks[i]['x0']))
    for i in toks_:
        t=toks[i]; a,b=r1[i],r2[i]
        print(f"{t['x0']:5d} {t['base']:5d} cap{t['cap']:3d} sw{t['sw']/cap:.2f}  {a[0]:12s} {a[1]:5.0f} | {b[0]:12s} {b[1]:5.0f}  {'ok' if eh_acorde(a[0]) else '--'}{'ok' if eh_acorde(b[0]) else '--'}")

def limiar_da_pagina(b,d,alvo=0.20):
    """escolhe o limiar de preto em que as cifras ficam com a espessura de traço da fonte (≈0,2 da altura)"""
    melhor=None
    for lim in (45,60,80,105,135,165):
        toks,lab,cap=candidatos(b,d,lim)
        fortes=[t for t in toks if t['cap']>=0.95*cap and len(t['cs'])>=2]
        if len(fortes)<6: continue
        # as cifras são as palavras de traço mais grosso: usa o quartil de cima
        r=sorted(t['sw']/t['cap'] for t in fortes); q=r[int(len(r)*0.8)]
        if melhor is None or abs(q-alvo)<abs(melhor[1]-alvo): melhor=(lim,q)
    return melhor[0] if melhor else 150
