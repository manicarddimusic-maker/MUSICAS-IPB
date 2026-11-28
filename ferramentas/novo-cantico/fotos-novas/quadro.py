"""Acha, na página já desentortada, onde começa e termina o conteúdo (título/cifras em cima, rodapé embaixo)."""
import sys,os,json,pickle
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from retif import W_OUT,D_OUT
from pagina import niveis
RET='/tmp/nn/ret2/'

def carregar(i,k):
    base=f'{RET}{i:02d}_{k}'
    P=pickle.load(open(base+'.pkl','rb'))
    n=np.load(base+'_n.npy').astype(np.float32)/200.0
    bg=np.load(base+'_bg.npy').astype(np.float32)
    m=cv2.imread(base+'_m.png',0)
    return P,n,bg,m

def tons(n,bg,m):
    e=niveis(n,bg,nitidez=0.0)
    e[m>0]=255
    return e

def linhas_de_tinta(e,P,x0f=-0.03,x1f=1.03,lim=110,minpx=3):
    """perfil por linha (dentro da faixa das pautas) -> vetor bool por linha da imagem: tem tinta"""
    xa=int(x0f*W_OUT)-P.X0; xb=int(x1f*W_OUT)-P.X0
    tin=(e[:,xa:xb]<lim)
    return tin.sum(axis=1)>=minpx

def grossa(e,lim=110,r=3):
    """tinta grossa (título, número do hino): sobra depois de erodir"""
    t=(e<lim).astype(np.uint8)
    return cv2.erode(t,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1)))

def medir(i,k):
    P,n,bg,m=carregar(i,k)
    e=tons(n,bg,m)
    H,W=e.shape
    yz=-P.Y0                       # linha da imagem onde Y=0 (1ª linha da 1ª pauta)
    d=D_OUT
    tem=linhas_de_tinta(e,P)
    valido=(m[:, int(0.2*W):int(0.8*W)]==0).mean(axis=1)>0.5       # linha com página de verdade (dentro da foto)
    # topo: sobe a partir da 1ª pauta enquanto houver conteúdo, tolerando vãos pequenos
    def subir(maxd,vao):
        y=yz; topo=yz; falta=0
        while y>max(0,yz-int(maxd*d)):
            y-=1
            if not valido[y]: break
            if tem[y]: topo=y; falta=0
            else:
                falta+=1
                if falta>vao*d: break
        return topo
    topo_c=subir(12,3.0)           # página de continuação: só as cifras/CORO acima da pauta
    # título: tinta grossa acima da pauta
    g=grossa(e)
    xa=int(-0.02*W_OUT)-P.X0; xb=int(1.02*W_OUT)-P.X0
    gl=g[:,xa:xb].sum(axis=1)>=6
    y0b=max(0,yz-int(36*d))
    ys=np.where(gl[y0b:yz-int(4*d)])[0]
    topo_t=None
    if len(ys):
        ys=ys+y0b
        blocos=[]; a=ys[0]; p=ys[0]
        for y in ys[1:]:
            if y-p>2: blocos.append((a,p)); a=y
            p=y
        blocos.append((a,p))
        blocos=[b for b in blocos if b[1]-b[0]>=1.2*d]
        if blocos: topo_t=int(blocos[0][0])
    # fim: última linha com tinta dentro da foto
    yv=np.where(valido)[0]
    y_fim_foto=int(yv[-1]) if len(yv) else H-1
    yt=np.where(tem[:y_fim_foto+1])[0]
    fim=int(yt[-1]) if len(yt) else yz
    return dict(i=i,k=k,pg=P.pg,rot=P.rot,npag=P.npag,alinha=getattr(P,'alinha',0.0)/d,
                topo_c=(topo_c-yz)/d,topo_t=None if topo_t is None else (topo_t-yz)/d,fim=(fim-yz)/d,
                fim_foto=(y_fim_foto-yz)/d,ult_pauta=float(P.Yp[-1]/d)+4,npautas=len(P.v))
if __name__=='__main__':
    from mapa import mapa as mapa_fotos
    out=[]
    for F in mapa_fotos():
        for k in range(len(F['pgs'])):
            if not os.path.exists(f"{RET}{F['i']:02d}_{k}.pkl"): print(F['i'],k,'SEM RESULTADO'); continue
            r=medir(F['i'],k); out.append(r)
            print('%2d_%d pg %3s (%s) topo_c %6.1f  topo_t %s  fim %6.1f  fim_foto %6.1f  últ.pauta %6.1f  alinha %5.1f'%(r['i'],k,r['pg'],r['rot'],r['topo_c'],'  -   ' if r['topo_t'] is None else '%6.1f'%r['topo_t'],r['fim'],r['fim_foto'],r['ult_pauta'],r['alinha']))
    json.dump(out,open('/tmp/nn/medidas.json','w'))
