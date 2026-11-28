"""Mapa de nitidez de uma página desentortada, medido nas linhas das pautas (traço fino de contraste conhecido),
e reforço dos traços finos (letra, hastes, linhas) onde a foto saiu fora de foco."""
import sys
sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from retif import W_OUT,D_OUT
d=D_OUT

def contraste_das_linhas(n,P,yz):
    """-> (ys, xs, A): contraste das linhas de cada pauta (linha a linha da tabela = uma pauta), em blocos de 2 espaços"""
    dep=np.clip(1-n,0,1); H,W=dep.shape
    x0=-P.X0; x1=x0+W_OUT; bl=int(round(2*d))
    nb=(x1-x0)//bl
    ys=[];A=[]
    for Y in P.Yp:
        r0=int(round(yz+Y)); r4=int(round(yz+Y+4*d))
        if r0-3<0 or r4+3>=H: continue
        lin=np.mean([dep[int(round(yz+Y+k*d))-2:int(round(yz+Y+k*d))+3,x0:x1].max(axis=0) for k in range(5)],axis=0)
        gap=np.mean([dep[int(round(yz+Y+(k+0.5)*d))-1:int(round(yz+Y+(k+0.5)*d))+2,x0:x1].min(axis=0) for k in range(4)],axis=0)
        c=(lin-gap)[:nb*bl].reshape(nb,bl)
        A.append(np.median(c,axis=1)); ys.append(yz+Y+2*d)
    xs=x0+bl*(np.arange(nb)+0.5)
    return np.array(ys),xs,np.array(A)

def ganho(n,P,yz,ref=None,gmax=3.5):
    """ganho (>=1) por pixel para os traços finos"""
    ys,xs,A=contraste_das_linhas(n,P,yz)
    H,W=n.shape
    if len(ys)==0: return np.ones((H,W),np.float32),None
    A=cv2.GaussianBlur(A.astype(np.float32),(0,0),sigmaX=1.5,sigmaY=0.01) if A.shape[1]>3 else A.astype(np.float32)
    # interpola: em x (colunas) e em y (entre pautas)
    Ax=np.array([np.interp(np.arange(W),xs,a) for a in A])                  # [pautas, W]
    yy=np.arange(H,dtype=np.float32)
    if len(ys)==1: M=np.repeat(Ax,H,axis=0)
    else:
        k=np.clip(np.searchsorted(ys,yy)-1,0,len(ys)-2)
        t=np.clip((yy-ys[k])/np.maximum(1.0,ys[k+1]-ys[k]),0,1)[:,None]
        M=Ax[k]*(1-t)+Ax[k+1]*t
    r=ref if ref is not None else max(0.40,0.9*float(np.percentile(A,80)))
    g=np.clip(r/np.maximum(M,0.04),1.0,gmax).astype(np.float32)
    return g,dict(A=A,ref=r)

def reforcar_finos(n,g,k=9):
    """multiplica só a parte fina da tinta (o que some numa abertura de k px) pelo ganho local"""
    dep=np.clip(1-n,0,1).astype(np.float32)
    el=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))
    grosso=cv2.morphologyEx(dep,cv2.MORPH_OPEN,el)
    fino=dep-grosso
    dep2=np.minimum(1.0,grosso+g*fino)
    return 1-dep2
if __name__=='__main__':
    from quadro import carregar
    for (i,k) in ((57,0),(28,0),(61,1),(66,1),(1,1),(64,1),(61,0),(38,0)):
        P,n,bg,m=carregar(i,k); yz=-P.Y0
        ys,xs,A=contraste_das_linhas(n,P,yz)
        print('foto',i,k,'pg',P.pg,'A: p10 %.2f p50 %.2f p80 %.2f p95 %.2f | por terço (esq, meio, dir): %s'%(np.percentile(A,10),np.percentile(A,50),np.percentile(A,80),np.percentile(A,95),np.round([np.median(A[:,:A.shape[1]//3]),np.median(A[:,A.shape[1]//3:2*A.shape[1]//3]),np.median(A[:,2*A.shape[1]//3:])],2).tolist()))
