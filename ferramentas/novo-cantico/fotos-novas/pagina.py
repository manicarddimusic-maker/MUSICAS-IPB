"""Tratamento de uma página nova já trazida para o enquadramento da antiga:
achatamento da luz (sombra do celular), preto/branco limpos, sem o verso da folha."""
import cv2,numpy as np
def fundo(g,k):
    """papel por trás da tinta: fechamento morfológico (acompanha a borda dura da sombra)"""
    gb=cv2.GaussianBlur(g,(0,0),1.2)
    el=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))
    bg=cv2.morphologyEx(gb,cv2.MORPH_CLOSE,el)
    return cv2.GaussianBlur(bg,(0,0),2.0)
def normalizar(bgr,dentro=None):
    g=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY).astype(np.float32)
    h,w=g.shape
    k=int(0.02*h)|1
    bg=fundo(g,k)
    m=np.ones(g.shape,bool) if dentro is None else dentro>0
    # nível de preto da foto (a tinta nunca chega a zero): percentil bem baixo dentro da página
    B=float(np.percentile(g[m][::7],0.4))-2.0
    B=float(np.clip(B,0,40))
    n=(g-B)/np.maximum(bg-B,6.0)
    return np.clip(n,0,1.3),bg,B
if __name__=='__main__':
    import sys
    for pg in (295,288,289,256):
        a=cv2.imread(f'/tmp/nn/bruta/p{pg}.png'); d=cv2.imread(f'/tmp/nn/bruta/p{pg}_m.png',0)
        n,bg,B=normalizar(a,d)
        print(pg,a.shape,'B',round(B,1),'bg min/med',int(bg[d>0].min()),int(np.median(bg[d>0])))
        cv2.imwrite(f'/tmp/nn/vis/n{pg}.png',np.clip(n*255,0,255).astype(np.uint8))
    n=cv2.imread('/tmp/nn/vis/n295.png',0); H,W=n.shape
    # recortes 1:1 — área clara (em cima) e área na sombra (em baixo, à esquerda)
    c1=n[int(.17*H):int(.17*H)+520,int(.08*W):int(.08*W)+1100]; c2=n[int(.74*H):int(.74*H)+520,int(.08*W):int(.08*W)+1100]
    cv2.imwrite('/tmp/nn/vis/n295_crop.png',np.vstack([c1,np.full((10,1100),0,np.uint8),c2]))

def niveis(n,bg,lo=0.12,hi=0.80,nitidez=0.7,gama=1.0):
    """tons finais (0..255): papel branco, tinta preta; o verso da folha e o granulado da sombra somem"""
    med=float(np.median(bg[bg>30])) if (bg>30).any() else 200.
    ganho=np.clip(med/np.maximum(bg,8.0),1.0,6.0)
    # alisa o granulado sem mexer nas bordas da tinta
    nf=cv2.bilateralFilter(n.astype(np.float32),5,0.10,1.6)
    # onde a foto estava muito escura o granulado é maior: o branco começa um pouco antes
    h_=hi-0.07*np.clip((ganho-1.5)/2.5,0,1)
    v=np.clip((nf-lo)/(h_-lo),0,1)
    if nitidez>0:
        b=cv2.GaussianBlur(v,(0,0),1.4)
        v=np.clip(v+nitidez*(v-b),0,1)
    if gama!=1.0: v=v**gama
    return (v*255+0.5).astype(np.uint8)
def quant(a):
    out=np.full(a.shape,3,np.uint8); out[a<228]=2; out[a<150]=1; out[a<62]=0
    return np.array([0,105,188,255],np.uint8)[out]
def como_na_folha(e,HP=2000):
    h,w=e.shape; s=HP/h
    r=cv2.resize(e,(int(round(w*s)),HP),interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
    return quant(r)
