"""Página desentortada -> página final: tons limpos, linhas da pauta reforçadas, quadro igual em todas as páginas."""
import sys,os,json,pickle
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from retif import W_OUT,D_OUT
from pagina import niveis
from quadro import carregar
from estrutura import medir
from nitidez import ganho,reforcar_finos
from mapa import mapa as mapa_fotos
d=D_OUT
ALT=164.7          # do alto do título (ou das cifras) até o pé do rodapé, em espaços de pauta — igual no livro todo
PAD_T=3.2; PAD_B=2.6; PAD_X=0.055
LARG=int(round((1+2*PAD_X)*W_OUT)); ALTURA=int(round((ALT+PAD_T+PAD_B)*d))
TOPO_FIXO={}       # (foto,k) -> topo à mão (em espaços, relativo à 1ª pauta), para os casos em que a detecção erra
if os.path.exists('/tmp/nn/topo_fixo.json'): TOPO_FIXO={tuple(int(x) for x in k.split('_')):v for k,v in json.load(open('/tmp/nn/topo_fixo.json')).items()}

def limpar_pontos(e,semente=120,lim=232):
    """some com manchinhas claras soltas (verso da folha, granulado): fica só o que encosta em tinta de verdade"""
    fraco=(e<lim).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(fraco,8)
    forte=np.zeros(n,bool)
    ids,cnt=np.unique(lab[e<semente],return_counts=True)
    forte[ids[cnt>=3]]=True
    forte[0]=True
    out=e.copy(); out[~forte[lab]]=255
    return out

def reforcar_pautas(e,P,yz):
    """redesenha de leve as 5 linhas de cada pauta onde a foto ficou fraca (fora de foco)"""
    H,W=e.shape
    x0=-P.X0; x1=-P.X0+W_OUT
    f=e.astype(np.float32); info=[]
    for Y in P.Yp:
        ya=int(round(yz+Y-1.0*d)); yb=int(round(yz+Y+5.0*d))
        if ya<0 or yb>=H: continue
        prof=(255-f[ya:yb+1,x0+int(2*d):x1-int(2*d)]).mean(axis=1)
        linhas=[]
        for k in range(5):
            yc=yz+Y+k*d-ya
            a=int(round(yc-2.5)); b=int(round(yc+2.5))
            if a<0 or b>=len(prof): continue
            seg=prof[a:b+1]; w=np.maximum(seg-seg.min(),0)
            if w.sum()<=1e-6: continue
            linhas.append(ya+a+float((w*np.arange(len(seg))).sum()/w.sum()))
        if len(linhas)<5: continue
        rows=[int(round(l)) for l in linhas]
        lin=np.mean([255-f[r,:] for r in rows],axis=0)
        ent=np.mean([255-f[int(round((linhas[k]+linhas[k+1])/2)),:] for k in range(4)],axis=0)
        L=cv2.blur((lin-ent).reshape(1,-1),(int(0.8*d)|1,1)).ravel()
        ref=float(np.median(L[x0+int(3*d):x1-int(3*d)])); thr=0.3*ref
        xa=x0+int(3*d)
        while xa>1 and L[xa-1]>thr: xa-=1
        xb=x1-int(3*d)
        while xb<W-2 and L[xb+1]>thr: xb+=1
        xa=max(xa,x0-int(0.6*d)); xb=min(xb,x1+int(0.6*d))
        for l in linhas:
            for r in range(int(l)-2,int(l)+4):
                if 0<=r<H:
                    w=float(np.exp(-0.5*((r-l)/0.85)**2))
                    f[r,xa:xb+1]=np.minimum(f[r,xa:xb+1],255.0*(1-0.70*w))
        info.append(dict(linhas=[float(l) for l in linhas],xa=int(xa),xb=int(xb)))
    return np.clip(f,0,255).astype(np.uint8),info

def quadro(i,k,papel):
    """-> (topo, fim, como): linhas (em espaços, relativas à 1ª pauta) do alto do bloco de texto e do pé do rodapé"""
    r=medir(i,k,papel)
    if (i,k) in TOPO_FIXO: topo,como=TOPO_FIXO[(i,k)],'à mão'
    elif papel=='T' and r['titulo'] is not None: topo,como=r['titulo'],'título'
    else: topo,como=r['cifras'],('cifras' if papel=='C' else 'SEM TÍTULO')
    fim=topo+ALT
    if r['rodape'] is not None and abs(r['rodape']-fim)<=2.2:
        fim=r['rodape']; como+='+rodapé'
        if (i,k) not in TOPO_FIXO: topo=fim-ALT
    elif r['rodape'] is not None: como+=' (rodapé a %.1f do esperado)'%(r['rodape']-fim)
    return topo,fim,como,r

def finalizar(i,k,papel):
    P,n,bg,m=carregar(i,k)
    yz=-P.Y0
    topo,fim,como,r=quadro(i,k,papel)
    # onde a foto saiu fora de foco (medido nas linhas das pautas), a letra e os traços finos ganham reforço
    g,ginfo=ganho(n,P,yz,ref=0.47)
    g=g**1.15
    if float(g.max())>1.05: n=reforcar_finos(n,g)
    e=niveis(n,bg,nitidez=0.7,gama=1.6)
    # perto da borda da foto a luz estimada não vale: some junto com o que está fora
    fora=cv2.dilate((m>0).astype(np.uint8),np.ones((int(1.0*d)|1,int(1.0*d)|1),np.uint8))>0
    e[fora]=255
    e,pautas=reforcar_pautas(e,P,yz)
    e[fora]=255
    e=limpar_pontos(e)
    H,W=e.shape
    x0=-P.X0; x1=-P.X0+W_OUT
    # lado da lombada: além da ponta das pautas só há a dobra do livro e a página vizinha
    lomb_dir=(P.npag==2 and k==0) or (P.npag==1 and P.pg%2==0)
    if lomb_dir: e[:,x1+int(2.2*d):]=255
    else: e[:,:max(0,x0-int(2.2*d))]=255
    yf=int(round(yz+fim*d+0.5*d)); corte_limpo=True
    # o rodapé pode estar um pouco mais baixo do que o esperado: o corte desce até o fim da linha de texto
    if 0<yf<H:
        tem=(e[:,max(0,x0-int(d)):x1+int(d)]<150).sum(axis=1)>=3
        y=yf; lim=min(H-1,int(yz+fim*d+2.3*d))
        while y<lim and tem[y]: y+=1
        if y<lim: yf=y+2
        else: corte_limpo=False
    if yf<H: e[yf:,:]=255
    ya=int(round(yz+(fim-ALT-PAD_T)*d)); yb=ya+ALTURA
    xa=x0-int(round(PAD_X*W_OUT)); xb=xa+LARG
    tela=np.full((ALTURA,LARG),255,np.uint8)
    sy0=max(0,ya); sy1=min(H,yb)
    tela[sy0-ya:sy1-ya,:]=e[sy0:sy1,xa:xb]
    # o que a foto não cobre dentro do quadro (para completar com a página antiga, se preciso)
    falta=np.ones((ALTURA,LARG),np.uint8)*255
    falta[sy0-ya:sy1-ya,:]=np.where(fora[sy0:sy1,xa:xb],255,0)
    info=dict(i=i,k=k,pg=P.pg,rot=P.rot,papel=papel,topo=topo,fim=fim,como=como,yz=yz-ya,x0=x0-xa,
              Yp=[float(y) for y in P.Yp],pautas=[dict(linhas=[l-ya for l in q['linhas']],xa=q['xa']-xa,xb=q['xb']-xa) for q in pautas],
              escala=P.escala,rms=P.rms,R=P.R,cobre=r['cobre'],rodape=r['rodape'],lomb_dir=bool(lomb_dir),
              ganho_med=float(np.median(g)),ganho_p95=float(np.percentile(g[::8,::8],95)),corte=int(yf-ya),corte_limpo=bool(corte_limpo))
    return tela,falta,info
if __name__=='__main__':
    from multiprocessing import Pool
    os.makedirs('/tmp/nn/pag',exist_ok=True)
    alvo=[int(a) for a in sys.argv[1:]]
    jobs=[(F['i'],k,pg) for F in mapa_fotos() if (not alvo or F['i'] in alvo) for k,pg in enumerate(F['pgs'])]
    def um(j):
        i,k,pg=j
        tela,falta,info=finalizar(i,k,'T' if k==0 else 'C')
        cv2.imwrite(f'/tmp/nn/pag/p{pg:03d}.png',tela); cv2.imwrite(f'/tmp/nn/pag/p{pg:03d}_m.png',falta)
        json.dump(info,open(f'/tmp/nn/pag/p{pg:03d}.json','w'))
        return 'foto %2d pg %3d (%s) %s topo %6.1f fim %6.1f  %-28s cobre até %6.1f  pautas %d'%(i,pg,info['rot'],info['papel'],info['topo'],info['fim'],info['como'],info['cobre'],len(info['pautas']))
    with Pool(2) as p:
        for s in p.imap(um,jobs): print(s,flush=True)
