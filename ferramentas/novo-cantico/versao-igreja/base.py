"""Página do hino 111 (música): pautas, sistemas, linhas de letra e as palavras impressas de cada linha."""
import sys
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from ncpauta import pautas,topo,base as base_pauta
SRC='/tmp/nc/final/p173.png'
def carregar():
    e=cv2.imread(SRC,0)
    P,d=pautas(e)
    return e,P,d
def componentes(bw):
    n,lab,st,cen=cv2.connectedComponentsWithStats(bw.astype(np.uint8),8)
    return n,lab,st
def sistemas(e,P,d):
    """pares (pauta de cima, pauta de baixo) -> lista de dict(y_sol0,y_sol4,y_fa0,y_fa4,xa,xb)"""
    H,W=e.shape; out=[]
    ys=[float(topo(p,W/2)) for p in P]
    assert len(P)%2==0,len(P)
    for i in range(0,len(P),2):
        a,b=P[i],P[i+1]
        out.append(dict(sol0=ys[i],sol4=ys[i]+4*d,fa0=ys[i+1],fa4=ys[i+1]+4*d,xa=min(a['xa'],b['xa']),xb=max(a['xb'],b['xb'])))
    return out
def linhas_de_letra(e,S,d,lim=140):
    """4 linhas de letra entre as duas pautas de um sistema: (y_topo_x, base) de cada uma, pelos componentes pequenos"""
    y0=int(S['sol4']+0.3*d); y1=int(S['fa0']-0.3*d)
    bw=(e[y0:y1]<lim)
    n,lab,st=componentes(bw)
    caixas=[]
    for i in range(1,n):
        x,y,w,h,a=[int(v) for v in st[i]]
        if h>2.6*d or w>12*d: continue          # hastes, ligaduras grandes
        if y<=1 or y+h>=(y1-y0)-1: continue     # encosta na beira da faixa (haste, nota)
        caixas.append((x,y+y0,w,h,a,i))
    return caixas,(y0,y1),lab
if __name__=='__main__':
    e,P,d=carregar(); H,W=e.shape
    print('pág',e.shape,'d=%.3f'%d,'pautas',len(P),[round(float(topo(p,W/2)),1) for p in P],[(p['xa'],p['xb']) for p in P])
    for k,S in enumerate(sistemas(e,P,d)):
        cx,(y0,y1),lab=linhas_de_letra(e,S,d)
        # perfil vertical das caixas "altas o bastante" (letras)
        letras=[c for c in cx if c[3]>=0.75*d and c[3]<=2.4*d]
        pes=np.array([c[1]+c[3] for c in letras])
        hist=np.bincount(pes.astype(int),minlength=y1+2)
        # linhas de base: picos do histograma dos pés das letras
        sm=np.convolve(hist,np.ones(3),'same'); cand=[]
        for y in np.argsort(-sm):
            if sm[y]<4: break
            if all(abs(y-c)>1.2*d for c in cand): cand.append(int(y))
        cand=sorted(cand)
        print('sistema',k,'faixa da letra',y0,y1,'altura %.1f'%(y1-y0),'| bases',cand,'| n caixas',len(cx))
        for b in cand:
            alt=[c[3] for c in letras if abs(c[1]+c[3]-b)<=2]
            hs=np.bincount(np.array(alt),minlength=40)
            print('    base',b,'alturas (px:n):',{h:int(n) for h,n in enumerate(hs) if n})
