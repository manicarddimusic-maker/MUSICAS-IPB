"""Pautas de uma página de partitura (aceita folha curva): traça cada pauta por faixas verticais."""
import cv2,numpy as np
def linhas_finas(e):
    h,w=e.shape
    k=max(7,int(h*0.0042))|1
    bh=cv2.morphologyEx(e,cv2.MORPH_BLACKHAT,cv2.getStructuringElement(cv2.MORPH_RECT,(1,k)))
    L=max(25,int(w*0.03))
    return cv2.morphologyEx((bh>40).astype(np.uint8),cv2.MORPH_OPEN,np.ones((1,L),np.uint8))
def espaco(m):
    h,w=m.shape; ds=[]
    for fx in np.arange(0.12,0.9,0.06):
        x0=int(w*fx); p=m[:,x0:x0+int(w*0.06)].sum(axis=1).astype(np.float32)
        if p.max()<=0: continue
        p=p-p.mean(); ac=np.correlate(p,p,'full')[len(p)-1:]
        lo,hi=max(6,int(h*0.003)),int(h*0.012)
        if hi<=lo+2: continue
        d=lo+int(np.argmax(ac[lo:hi]))
        if ac[d]>0.25*ac[0]:
            # refina com parábola
            if lo<d<hi-1:
                a,b,c=ac[d-1],ac[d],ac[d+1]; den=a-2*b+c
                d=d+(0.5*(a-c)/den if den!=0 else 0)
            ds.append(float(d))
    return float(np.median(ds)) if len(ds)>=3 else None
def faixas(m,d):
    """faixas (y0,y1) onde há pauta, pelo perfil da página inteira"""
    h,w=m.shape
    prof=m.sum(axis=1).astype(np.float32)
    win=int(4.2*d)|1
    sm=cv2.blur(prof.reshape(-1,1),(1,win)).ravel()
    thr=0.3*np.percentile(sm,99.5)
    on=sm>thr; segs=[];y=0
    while y<h:
        if on[y]:
            y0=y
            while y<h and on[y]: y+=1
            segs.append((y0,y))
        else: y+=1
    out=[]
    for a,b in segs:
        if b-a<2.5*d: continue
        ya=max(0,a-int(2.5*d)); yb=min(h,b+int(2.5*d))
        pr=prof[ya:yb]; idx=np.where(pr>0.25*pr.max())[0]
        if len(idx)<3: continue
        out.append([ya+int(idx[0]),ya+int(idx[-1])])
    junt=[]
    for s in out:
        if junt and s[0]-junt[-1][1]<1.2*d: junt[-1][1]=max(junt[-1][1],s[1])
        else: junt.append(s)
    return [f for f in junt if f[1]-f[0]>=3.0*d]
def pautas(e,nst=22):
    """-> (lista de pautas, d). pauta = dict(xa,xb,co=polinômio do y da 1ª linha em função de x)"""
    h,w=e.shape; m=linhas_finas(e); d=espaco(m)
    if d is None: return [],None
    F=faixas(m,d)
    xs=np.linspace(0,w,nst+1).astype(int)
    perfis=[]
    for s in range(nst):
        p=m[:,xs[s]:xs[s+1]].sum(axis=1).astype(np.float32)
        p=np.maximum(p,np.maximum(np.roll(p,1),np.roll(p,-1)))
        perfis.append(p)
    out=[]
    for ya,yb in F:
        lo=max(0,int(ya-1.5*d)); hi=min(h-int(4*d)-2,int(yb-4*d+1.5*d))
        if hi<=lo: hi=lo+1
        pts=[]
        for s in range(nst):
            p=perfis[s]; larg=xs[s+1]-xs[s]
            ys=np.arange(lo,hi+1)
            sc=np.zeros(len(ys),np.float32); n=np.zeros(len(ys),np.float32)
            for k in range(5):
                v=p[np.clip(ys+int(round(k*d)),0,h-1)]
                sc+=np.minimum(v,larg); n+=(v>=0.22*larg)
            # desconta o que houver no meio das linhas (texto)
            for k in range(4):
                v=p[np.clip(ys+int(round((k+0.5)*d)),0,h-1)]; sc-=0.5*np.minimum(v,larg)
            i=int(np.argmax(sc))
            if n[i]>=3 and sc[i]>=0.9*larg: pts.append((s,(xs[s]+xs[s+1])/2,float(ys[i])))
        if len(pts)<4:
            # pauta fraca: usa a faixa como reta
            if yb-ya<=5.2*d: out.append(dict(xa=0,xb=w,co=[0.0,0.0,float((ya+yb)/2-2*d)],n=0))
            continue
        X=np.array([a[1] for a in pts]); Y=np.array([a[2] for a in pts],np.float64)
        grau=2 if len(pts)>=8 else 1
        co=np.polyfit(X,Y,grau)
        for _ in range(2):
            r=np.abs(np.polyval(co,X)-Y); bom=r<=max(2.5,0.3*d)
            if bom.sum()>=max(4,0.5*len(pts)): co=np.polyfit(X[bom],Y[bom],grau)
        co=[0.0]*(3-len(co))+[float(v) for v in co]
        out.append(dict(xa=int(xs[pts[0][0]]),xb=int(xs[pts[-1][0]+1]),co=co,n=len(pts)))
    out.sort(key=lambda p:np.polyval(p['co'],w/2))
    return out,d
def topo(p,x): return np.polyval(p['co'],x)
def base(p,x,d): return np.polyval(p['co'],x)+4*d
def sistemas(e,P,d):
    """índices das pautas que abrem um sistema (a de cima de cada grupo ligado pela barra vertical)"""
    h,w=e.shape; bw=(e<140).astype(np.uint8)
    lig=[]
    for i in range(len(P)-1):
        a,b=P[i],P[i+1]; ok=False
        for lado in ('esq','dir'):
            xr=(max(0,min(a['xa'],b['xa'])-int(3*d)),min(a['xa'],b['xa'])+int(5*d)) if lado=='esq' else (max(a['xb'],b['xb'])-int(5*d),min(w,max(a['xb'],b['xb'])+int(3*d)))
            xm=(xr[0]+xr[1])/2
            y0=int(base(a,xm,d)+0.6*d); y1=int(topo(b,xm)-0.6*d)
            if y1-y0<d: continue
            faixa=bw[y0:y1,xr[0]:xr[1]]
            if faixa.size==0: continue
            # fecha buracos pequenos e mede a maior coluna quase cheia (tolerando inclinação: janela de 3 px)
            col=cv2.dilate(faixa,np.ones((1,5),np.uint8)).mean(axis=0)
            if col.max()>=0.9: ok=True
        lig.append(ok)
    tops=[0] if P else []
    for i,l in enumerate(lig):
        if not l: tops.append(i+1)
    return tops,lig
if __name__=='__main__':
    import sys
    for pg in (60,62,144,300,464,76,114,2,623):
        e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
        P,d=pautas(e)
        if d is None: print(pg,'sem pautas'); continue
        tops,lig=sistemas(e,P,d)
        print(pg,e.shape,'d=%.1f'%d,'pautas',len(P),'tops',tops,[int(topo(p,e.shape[1]/2)) for p in P])
        vis=cv2.cvtColor(e,cv2.COLOR_GRAY2BGR)
        for i,p in enumerate(P):
            xs=np.arange(p['xa'],p['xb'],8)
            for x in xs:
                cv2.circle(vis,(int(x),int(topo(p,x))),2,(0,0,255) if i in tops else (255,120,0),-1)
                cv2.circle(vis,(int(x),int(base(p,x,d))),2,(0,160,0),-1)
        cv2.imwrite(f'/tmp/cif/dbg/pauta{pg}.jpg',cv2.resize(vis,None,fx=0.5,fy=0.5,interpolation=cv2.INTER_AREA),[cv2.IMWRITE_JPEG_QUALITY,75])
