"""Acha as pautas (pentagramas) de uma página de partitura já endireitada."""
import cv2,numpy as np
def linhas_finas(e):
    h,w=e.shape
    k=max(7,int(h*0.0042))|1
    bh=cv2.morphologyEx(e,cv2.MORPH_BLACKHAT,cv2.getStructuringElement(cv2.MORPH_RECT,(1,k)))
    L=max(25,int(w*0.03))
    return cv2.morphologyEx((bh>40).astype(np.uint8),cv2.MORPH_OPEN,np.ones((1,L),np.uint8))
def pautas(e):
    """devolve (lista de (y_topo, y_base) das pautas, distância entre linhas)"""
    h,w=e.shape
    m=linhas_finas(e)
    # distância entre as linhas: autocorrelação do perfil numa faixa central estreita (pouca curvatura)
    ds=[]
    for fx in (0.3,0.45,0.6,0.75):
        x0=int(w*fx); p=m[:,x0:x0+int(w*0.08)].sum(axis=1).astype(np.float32)
        if p.max()<=0: continue
        p=p-p.mean(); ac=np.correlate(p,p,'full')[len(p)-1:]
        lo,hi=max(6,int(h*0.003)),int(h*0.012)
        if hi<=lo+2: continue
        d=lo+int(np.argmax(ac[lo:hi])); 
        if ac[d]>0.25*ac[0]: ds.append(d)
    if not ds: return [],None
    d=float(np.median(ds))
    prof=m.sum(axis=1).astype(np.float32)
    win=int(4.2*d)|1
    sm=cv2.blur(prof.reshape(-1,1),(1,win)).ravel()
    thr=0.3*np.percentile(sm,99.5)
    on=sm>thr
    segs=[];y=0
    while y<h:
        if on[y]:
            y0=y
            while y<h and on[y]: y+=1
            segs.append((y0,y))
        else: y+=1
    out=[]
    for a,b in segs:
        if b-a<2.5*d: continue
        # limites reais: primeira e última linha fina dentro do trecho alargado
        ya=max(0,a-int(2.5*d)); yb=min(h,b+int(2.5*d))
        pr=prof[ya:yb]; idx=np.where(pr>0.25*pr.max())[0]
        if len(idx)<3: continue
        out.append((ya+int(idx[0]),ya+int(idx[-1])))
    # junta trechos que são a mesma pauta
    junt=[]
    for s in out:
        if junt and s[0]-junt[-1][1]<1.2*d: junt[-1]=(junt[-1][0],max(junt[-1][1],s[1]))
        else: junt.append(s)
    return junt,d
if __name__=='__main__':
    import sys
    for pg in (60,62,144,300,464,76):
        e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
        st,d=pautas(e); print(pg,e.shape,'d',d,'pautas',len(st),[(a,b,b-a) for a,b in st])
