"""Estrutura vertical de cada página desentortada: topo do título (ou das cifras) e rodapé."""
import sys,os,json
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from retif import W_OUT,D_OUT
from quadro import carregar,tons
from mapa import mapa as mapa_fotos
d=D_OUT

def faixas(ink,val,y0,y1,minpx=3):
    """faixas de linhas com tinta + medidas dos componentes de cada uma"""
    tem=ink.sum(axis=1)>=minpx
    out=[];y=max(0,y0); y1=min(len(tem),y1)
    while y<y1:
        if tem[y]:
            a=y
            while y<y1 and tem[y]: y+=1
            nn,lab,st,_=cv2.connectedComponentsWithStats(ink[a:y].astype(np.uint8),8)
            cs=[(int(st[j,3]),int(st[j,2]),int(st[j,4]),int(st[j,0])) for j in range(1,nn) if st[j,4]>=12]
            out.append(dict(a=a,b=y-1,hs=np.array([c[0] for c in cs]),ws=np.array([c[1] for c in cs]),xs=np.array([c[3] for c in cs]),val=float(val[a:y].min())))
        else: y+=1
    return out

def medir(i,k,papel):
    P,n,bg,m=carregar(i,k); yz=-P.Y0
    e=tons(n,bg,m); H,W=e.shape
    xa=int(-0.035*W_OUT)-P.X0; xb=int(1.035*W_OUT)-P.X0
    ink=(e[:,xa:xb]<110)
    val=(m[:,xa:xb]==0).mean(axis=1)
    r=dict(i=i,k=k,pg=P.pg,rot=P.rot,papel=papel,n=len(P.v),Yp=[float(y/d) for y in P.Yp])
    # --- título: faixa mais alta com 3+ letras grandes
    F=faixas(ink,val,yz-int(37.5*d),yz-int(10*d))
    tit=[f for f in F if ((f['hs']>=3.2*d)&(f['hs']<=7.5*d)).sum()>=3 and f['val']>=0.9]
    # o título é a faixa de letras grandes mais perto da pauta; título de duas linhas sobe mais uma faixa
    if tit:
        j=len(tit)-1
        while j>0 and tit[j]['a']-tit[j-1]['b']<=2.2*d: j-=1
        tit=tit[j:]
    r['titulo']=None if not tit else (tit[0]['a']-yz)/d
    r['titulo_fim']=None if not tit else (tit[-1]['b']-yz)/d
    # --- primeira tinta acima da 1ª pauta (cifras, CORO), tolerando vãos de até 5,6 espaços
    F2=faixas((e[:,xa:xb]<170),val,yz-int(13.5*d),yz+2)      # letra fina (CORO...) também conta
    topo=yz; 
    for f in F2[::-1]:
        longe=f['b']<yz-2*d
        if f['val']<0.9 or (longe and len(f['hs']) and (f['hs'].max()>3.2*d or f['ws'].max()>9*d)): break
        if topo-f['b']>4.6*d: break
        topo=f['a']
    r['cifras']=(topo-yz)/d
    # --- rodapé: a faixa de texto mais baixa (letras pequenas, uma linha só)
    yb=int(yz+P.Yp[-1]+4*d+1.5*d)
    F3=faixas(ink,val,yb,H)
    rod=None
    for j in range(len(F3)-1,-1,-1):
        f=F3[j]; alt=f['b']-f['a']+1
        peq=((f['hs']>=0.6*d)&(f['hs']<=2.1*d)).sum()
        if 0.8*d<=alt<=2.5*d and peq>=5 and f['val']>=0.9 and (len(f['hs'])==0 or f['hs'].max()<=2.5*d):
            acima=f['a']-(F3[j-1]['b'] if j>0 else yb)
            larg=(f['xs'].max()+f['ws'][np.argmax(f['xs'])]-f['xs'].min())/d
            if acima>=1.0*d and larg>=6: rod=f; break
    r['rodape']=None if rod is None else (rod['b']-yz)/d
    r['rodape_topo']=None if rod is None else (rod['a']-yz)/d
    # até onde a foto cobre
    v=np.where(val>0.5)[0]
    r['cobre']=(int(v[-1])-yz)/d if len(v) else 0.0
    r['cobre_topo']=(int(v[0])-yz)/d if len(v) else 0.0
    return r
if __name__=='__main__':
    out=[]
    for F_ in mapa_fotos():
        for k,pg in enumerate(F_['pgs']):
            r=medir(F_['i'],k,'T' if k==0 else 'C'); out.append(r)
    json.dump(out,open('/tmp/nn/estrutura.json','w'))
    T=[r for r in out if r['papel']=='T']; C=[r for r in out if r['papel']=='C']
    print('T sem título:',[(r['i'],r['pg'],r['rot']) for r in T if r['titulo'] is None])
    a=[r['rodape']-r['titulo'] for r in T if r['titulo'] is not None and r['rodape'] is not None]
    print('T: rodapé-título n=%d'%len(a),np.round(sorted(a),1).tolist())
    b=[r['rodape']-r['cifras'] for r in C if r['rodape'] is not None]
    print('C: rodapé-cifras n=%d'%len(b),np.round(sorted(b),1).tolist())
    print('T: título:',np.round(sorted(r['titulo'] for r in T if r['titulo'] is not None),1).tolist())
    print('C: cifras:',np.round(sorted(r['cifras'] for r in C),1).tolist())
    print('vão máx. entre pautas vizinhas >42:',[(r['i'],r['pg'],np.round(np.diff(r['Yp']),0).tolist()) for r in out if len(r['Yp'])>1 and max(np.diff(r['Yp']))>42])
