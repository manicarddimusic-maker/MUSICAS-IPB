"""Desentorta uma página fotografada usando as pautas como régua:
 y_foto = a(x)*v + b(x)   (cada coluna da foto é uma reta em v: página curva vista de cima)
depois acerta a largura (pontas das pautas) e o espaçamento das linhas (igual em todas as páginas)."""
import sys
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from tracar import tons_da_foto,tracar,paginas,linha_fina

class Modelo:
    """y_foto = v + soma_k psi_k(x) * (c0_k + c1_k*t + c2_k*t^2 + ...),  t=(v-vm)/V0,  psi_k(x)=phi_k(x)-phi_k(xref)
    (na coluna de referência xref, y = v)"""
    V0=1000.0
    def __init__(s,nos,C,xref,vm): s.nos=nos; s.C=C; s.xref=xref; s.vm=vm     # C: [grau+1, K]
    def _psi(s,x):
        x=np.asarray(x,np.float64); sh=x.shape; x=x.ravel()
        h=s.nos[1]-s.nos[0]
        xc=np.clip(x,s.nos[0],s.nos[-1])
        f=np.maximum(0,1-np.abs(xc[:,None]-s.nos[None,:])/h)
        fr=np.maximum(0,1-np.abs(s.xref-s.nos)/h)
        return f-fr[None,:],sh
    def coef(s,x):
        """coeficientes do polinômio em t para cada x -> [grau+1, ...x.shape]"""
        P,sh=s._psi(x)
        return (P@s.C.T).T.reshape((s.C.shape[0],)+sh)
    def y(s,x,v):
        c=s.coef(x); t=(np.asarray(v,np.float64)-s.vm)/s.V0
        out=np.asarray(v,np.float64)+0*c[0]
        for j in range(c.shape[0]): out=out+c[j]*t**j
        return out
    def dy_dv(s,x,v):
        c=s.coef(x); t=(np.asarray(v,np.float64)-s.vm)/s.V0
        out=1.0+0*c[0]
        for j in range(1,c.shape[0]): out=out+j*c[j]*t**(j-1)/s.V0
        return out

def ajustar(cs,x0,x1,d,K=18,grau=2,lam=0.08,its=10):
    """ajusta o modelo e o v de cada pauta -> (Modelo, v[], resíduo rms, resíduos por pauta)"""
    nos=np.linspace(x0-6*d,x1+6*d,K)
    xref=0.5*(x0+x1)
    X=np.concatenate([c['X'] for c in cs]); Y=np.concatenate([c['Y'] for c in cs])
    S=np.concatenate([np.full(len(c['X']),i) for i,c in enumerate(cs)])
    v=np.array([float(np.interp(xref,c['X'],c['Y'])) if c['xa']<=xref<=c['xb'] else float(np.median(c['Y'])) for c in cs])
    vm=float(v.mean())
    g=min(grau,max(1,len(cs)-1)) if len(cs)>=2 else 0
    M=Modelo(nos,np.zeros((g+1,K)),xref,vm)
    Psi,_=M._psi(X)
    D2=np.zeros((K-2,K))
    for k in range(K-2): D2[k,k]=1; D2[k,k+1]=-2; D2[k,k+2]=1
    w=np.ones(len(X)); n=len(X)
    for it in range(its):
        t=(v[S]-vm)/M.V0
        A=np.hstack([Psi*(t**j)[:,None] for j in range(g+1)])
        sw=np.sqrt(w)[:,None]
        regs=[]; 
        for j in range(g+1):
            Z=np.zeros((K-2,K*(g+1))); Z[:,j*K:(j+1)*K]=np.sqrt(lam*n/K)*D2; regs.append(Z)
            if j>=2:
                Z2=np.zeros((K,K*(g+1))); Z2[:,j*K:(j+1)*K]=np.sqrt(0.002*n/K)*np.eye(K); regs.append(Z2)
        Rg=np.vstack(regs)
        R=np.vstack([A*sw,Rg,1e-4*np.eye(K*(g+1))])
        r=np.concatenate([(Y-v[S])*sw[:,0],np.zeros(Rg.shape[0]+K*(g+1))])
        th=np.linalg.lstsq(R,r,rcond=None)[0]
        M.C=th.reshape(g+1,K)
        for _ in range(3):      # Newton no v de cada pauta
            f=M.y(X,v[S]); fv=M.dy_dv(X,v[S])
            for i in range(len(cs)):
                m=S==i
                v[i]+=float((w[m]*fv[m]*(Y[m]-f[m])).sum()/max(1e-9,(w[m]*fv[m]**2).sum()))
        res=Y-M.y(X,v[S])
        w=1.0/np.maximum(1.0,np.abs(res)/1.0)
    rms=float(np.sqrt(np.mean(res**2)))
    por=[float(np.sqrt(np.mean(res[S==i]**2))) for i in range(len(cs))]
    return M,v,rms,por

class Fino:
    """correção fina por pauta: resíduo r_s(x) de cada pauta, interpolado em v entre pautas vizinhas"""
    def __init__(s,M,cs,v,x0,x1,d):
        s.xg=np.arange(int(x0-8*d),int(x1+8*d)+1,4.0)
        ordem=np.argsort(v); s.v=np.asarray(v)[ordem]; R=[]
        for i in ordem:
            c=cs[i]; res=c['Y']-M.y(c['X'],v[i])
            xn=(c['X']-c['xa'])/max(1.0,c['xb']-c['xa'])*2-1
            g=min(6,max(1,len(c['X'])//12))
            co=np.polyfit(xn,res,g)
            xq=np.clip((s.xg-c['xa'])/max(1.0,c['xb']-c['xa'])*2-1,-1,1)
            R.append(np.polyval(co,xq))
        s.R=np.array(R)                    # [pautas, xg]
    def __call__(s,x,v):
        x=np.asarray(x,np.float64); v=np.asarray(v,np.float64); sh=np.broadcast(x,v).shape
        x=np.broadcast_to(x,sh).ravel(); v=np.broadcast_to(v,sh).ravel()
        fx=np.clip((x-s.xg[0])/(s.xg[1]-s.xg[0]),0,len(s.xg)-1.001); i0=fx.astype(int); f=fx-i0
        if len(s.v)==1:
            r=s.R[0,i0]*(1-f)+s.R[0,i0+1]*f
            return r.reshape(sh)
        k=np.clip(np.searchsorted(s.v,v)-1,0,len(s.v)-2)
        t=np.clip((v-s.v[k])/np.maximum(1e-6,s.v[k+1]-s.v[k]),0,1)
        ra=s.R[k,i0]*(1-f)+s.R[k,i0+1]*f; rb=s.R[k+1,i0]*(1-f)+s.R[k+1,i0+1]*f
        return (ra*(1-t)+rb*t).reshape(sh)

def medir_pauta(bh,M,F,vs,c,d,x0,x1):
    """mede na foto, ao longo da pauta já modelada: as 5 linhas (espaço exato) e as pontas esquerda/direita"""
    H,W=bh.shape
    ts=np.arange(-2.5*d,6.5*d,0.25)
    xa=max(0,int(x0-10*d)); xb=min(W-1,int(x1+10*d)); xs=np.arange(xa,xb+1,1.0)
    Xg,Tg=np.meshgrid(xs,ts)
    # o modelo é suave: calcula numa grade grossa e interpola
    xc=xs[::8]; tc=ts[::4]
    Yc=M.y(xc[None,:],(vs+tc)[:,None])+F(xc[None,:],(vs+tc)[:,None])
    Yg=cv2.resize(Yc.astype(np.float32),(len(xs),len(ts)),interpolation=cv2.INTER_LINEAR)
    # (resize não alinha os cantos exatamente; refaz por interpolação separável)
    Yg=np.empty((len(ts),len(xs)),np.float32)
    tmp=np.array([np.interp(xs,xc,row) for row in Yc])
    for j in range(len(xs)): Yg[:,j]=np.interp(ts,tc,tmp[:,j])
    S=cv2.remap(bh,Xg.astype(np.float32),Yg,cv2.INTER_LINEAR,borderValue=0)
    ia=int(np.clip(c['xa']+2*d-xa,0,len(xs)-2)); ib=int(np.clip(c['xb']-2*d-xa,ia+1,len(xs)-1))
    Q=S[:,ia:ib].mean(axis=1)
    em=float(np.median(c['E'])); tk=[]
    for k in range(5):
        t0=k*d*em; m=(ts>=t0-0.33*d)&(ts<=t0+0.33*d)
        q=Q[m]; tt=ts[m]
        j=int(np.argmax(q)); m2=(tt>=tt[j]-0.2*d)&(tt<=tt[j]+0.2*d)
        wq=np.maximum(q[m2]-0.3*q[j],0)
        tk.append(float((wq*tt[m2]).sum()/wq.sum()) if wq.sum()>1e-9 else float(t0))
    co=np.polyfit(np.arange(5),tk,1); ds=float(co[0]); t0=float(co[1])
    erro=float(np.max(np.abs(np.polyval(co,np.arange(5))-tk)))
    def linha(t): return S[int(np.clip(round((t-ts[0])/0.25),0,len(ts)-1))]
    L=np.mean([np.maximum(np.maximum(linha(t0+k*ds),linha(t0+k*ds-0.5)),linha(t0+k*ds+0.5)) for k in range(5)],axis=0)-np.mean([linha(t0+(k+0.5)*ds) for k in range(4)],axis=0)
    L=cv2.blur(L.reshape(1,-1),(max(3,int(0.6*d)|1),1)).ravel()
    ref=float(np.median(L[ia:ib])); thr=0.3*ref
    gapmax=int(1.2*d)
    def anda(i,passo):
        ult=i; falta=0
        while 0<=i<len(L):
            if L[i]>thr: ult=i; falta=0
            else:
                falta+=1
                if falta>gapmax: break
            i+=passo
        return ult
    il=anda(ia,-1); ir=anda(ib,+1)
    return dict(ds=ds,t0=t0,erro=erro,xl=float(xs[il]),xr=float(xs[ir]),ref=ref,corta_e=il<=2,corta_d=ir>=len(L)-3)

def reta_robusta(x,y):
    """reta y(x) pela mediana das inclinações (Theil–Sen); com menos de 3 pontos, constante"""
    x=np.asarray(x,float); y=np.asarray(y,float)
    if len(x)>=3 and np.ptp(x)>1:
        sl=[(y[j]-y[i])/(x[j]-x[i]) for i in range(len(x)) for j in range(i+1,len(x)) if abs(x[j]-x[i])>0.2*np.ptp(x)]
        m=float(np.median(sl)) if sl else 0.0
    else: m=0.0
    b=float(np.median(y-m*x))
    return m,b

W_OUT=1440            # largura das pautas na página tratada (px)
R_LIVRO=99.0          # largura da pauta / espaço entre linhas (igual no livro todo)
D_OUT=W_OUT/R_LIVRO

class Pagina:
    """tudo o que se mediu de uma página na foto + o mapa (X,Y da página tratada) -> (x,y da foto)"""
    pass

def medir_pagina(bh,cs,x0,x1,d,W,regs=()):
    cs=[c for c in cs if c['xb']-c['xa']>=0.6*(x1-x0)]
    if not cs: return None
    # réguas (bordas de caixa de texto) desta página: atravessam quase toda a largura
    rg=[c for c in regs if min(c['xb'],x1+3*d)-max(c['xa'],x0-3*d)>=0.6*(x1-x0) and c['xa']>=x0-4*d and c['xb']<=x1+4*d and float(np.median(c['F']))>=0.6]
    for c in rg: c['regua']=True
    npa=len(cs)
    cs=cs+rg
    M,v,rms,por=ajustar(cs,x0,x1,d,grau=2)
    for _ in range(4):
        if len(cs)<4: break
        # régua (borda de caixa) só sai se estiver muito fora; pauta sai se destoar das outras
        nota=[p/(4.0 if c.get('regua') else 1.0) for p,c in zip(por,cs)]
        pior=int(np.argmax(nota)); lim=max(3.0,3.5*float(np.median(nota)))
        if nota[pior]<=lim: break
        cs=[c for k,c in enumerate(cs) if k!=pior]
        M,v,rms,por=ajustar(cs,x0,x1,d,grau=2)
    # "pauta" isolada lá em cima ou lá embaixo (longe demais das outras) não é pauta: é o crochê ou a borda
    while True:
        ip=[k for k,c in enumerate(cs) if not c.get('regua')]
        if len(ip)<4: break
        o=sorted(ip,key=lambda k:v[k])
        tira=None
        if (v[o[1]]-v[o[0]])>42*d: tira=o[0]
        elif (v[o[-1]]-v[o[-2]])>46*d: tira=o[-1]
        if tira is None: break
        cs=[c for k,c in enumerate(cs) if k!=tira]
        M,v,rms,por=ajustar(cs,x0,x1,d,grau=2)
    F=Fino(M,cs,v,x0,x1,d)
    nreg=sum(1 for c in cs if c.get('regua'))
    par=[(c,vs) for c,vs in zip(cs,v) if not c.get('regua')]
    reg_v=[float(vs) for c,vs in zip(cs,v) if c.get('regua')]
    cs=[p[0] for p in par]; v=np.array([p[1] for p in par])
    if not cs: return None
    med=[medir_pauta(bh,M,F,vs,c,d,x0,x1) for c,vs in zip(cs,v)]
    P=Pagina(); P.M=M; P.F=F; P.d=d; P.rms=rms; P.x0=x0; P.x1=x1; P.reg_v=reg_v
    P.v=np.array([vs+m['t0'] for vs,m in zip(v,med)])       # v da 1ª linha de cada pauta
    P.ds=np.array([m['ds'] for m in med]); P.xl=np.array([m['xl'] for m in med]); P.xr=np.array([m['xr'] for m in med])
    P.ok_e=np.array([not m['corta_e'] and m['erro']<0.35 for m in med]); P.ok_d=np.array([not m['corta_d'] and m['erro']<0.35 for m in med])
    P.erro=np.array([m['erro'] for m in med])
    o=np.argsort(P.v)
    for k in ('v','ds','xl','xr','ok_e','ok_d','erro'): setattr(P,k,getattr(P,k)[o])
    return P

def acertar_escalas(P,outra=None):
    """retas das pontas x_L(v), x_R(v) e do espaço d(v); página com poucas pautas herda a perspectiva da vizinha"""
    n=len(P.v); alcance=float(np.ptp(P.v)) if n>1 else 0.0
    bom=(P.erro<0.35)
    P.proprio = n>=4 and alcance>=45*P.d
    if P.proprio or outra is None or not getattr(outra,'proprio',False):
        ml,bl=reta_robusta(P.v[P.ok_e],P.xl[P.ok_e]) if P.ok_e.sum()>=1 else (0.0,float(np.median(P.xl)))
        mr,br=reta_robusta(P.v[P.ok_d],P.xr[P.ok_d]) if P.ok_d.sum()>=1 else (0.0,float(np.median(P.xr)))
        md,bd=reta_robusta(P.v[bom],P.ds[bom]) if bom.sum()>=1 else (0.0,float(np.median(P.ds)))
        if not P.proprio and n<3: ml=mr=md=0.0
    else:
        # inclinação das verticais como função de x (ponto de fuga da vizinha) e variação relativa do espaço
        O=outra
        xa=O.ml*O.vm+O.bl; xb=O.mr*O.vm+O.br
        beta=(O.mr-O.ml)/max(1.0,xb-xa); alfa=O.ml-beta*xa
        vm=float(np.mean(P.v))
        xl0=float(np.median(P.xl[P.ok_e]-0)) if P.ok_e.any() else float(np.median(P.xl))
        xr0=float(np.median(P.xr[P.ok_d]-0)) if P.ok_d.any() else float(np.median(P.xr))
        ml=alfa+beta*xl0; mr=alfa+beta*xr0
        bl=float(np.median((P.xl-ml*P.v)[P.ok_e])) if P.ok_e.any() else xl0-ml*vm
        br=float(np.median((P.xr-mr*P.v)[P.ok_d])) if P.ok_d.any() else xr0-mr*vm
        rel=O.md/max(1e-6,O.md*O.vm+O.bd)           # d'(v)/d na vizinha
        dm=float(np.median(P.ds[bom])) if bom.any() else float(np.median(P.ds))
        vmd=float(np.median(P.v[bom])) if bom.any() else vm
        md=rel*dm; bd=dm-md*vmd
    P.ml,P.bl,P.mr,P.br,P.md,P.bd=ml,bl,mr,br,md,bd
    P.vm=float(np.mean(P.v))
    # tabela Y(v): Y=0 na 1ª linha da 1ª pauta; dY/dv = D_OUT/d(v)
    vv=np.arange(P.v[0]-80*P.d*3,P.v[-1]+260*P.d,2.0)
    dd=np.clip(md*vv+bd,0.6*np.median(P.ds),1.6*np.median(P.ds))
    YY=np.concatenate([[0],np.cumsum(0.5*(D_OUT/dd[1:]+D_OUT/dd[:-1])*np.diff(vv))])
    YY-=np.interp(P.v[0],vv,YY)
    P.vv=vv; P.YY=YY
    P.Yp=np.interp(P.v,vv,YY)            # Y da 1ª linha de cada pauta na página tratada
    P.R=float(np.median(((mr-ml)*P.v+(br-bl))/np.maximum(1e-6,md*P.v+bd)))
    return P

def mapa(P,X0,X1,Y0,Y1,passo=8):
    """mapas (mx,my) da página tratada [Y0..Y1) x [X0..X1) para a foto"""
    Xc=np.arange(X0,X1+passo,passo,dtype=np.float64); Yc=np.arange(Y0,Y1+passo,passo,dtype=np.float64)
    v=np.interp(Yc,P.YY,P.vv)
    xl=P.ml*v+P.bl; xr=P.mr*v+P.br
    x=xl[:,None]+(Xc[None,:]/W_OUT)*(xr-xl)[:,None]
    vg=np.broadcast_to(v[:,None],x.shape)
    y=P.M.y(x,vg)+P.F(x,vg)
    Wd=int(X1-X0); Hd=int(Y1-Y0)
    # interpola a grade grossa (alinhando os cantos)
    gx=(np.arange(Wd,dtype=np.float32))/passo; gy=(np.arange(Hd,dtype=np.float32))/passo
    GX,GY=np.meshgrid(gx,gy)
    mx=cv2.remap(x.astype(np.float32),GX,GY,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    my=cv2.remap(y.astype(np.float32),GX,GY,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    return mx,my
if __name__=='__main__':
    import json
    idx=json.load(open('/tmp/nn/fotos.json'))
    for i in [int(a) for a in sys.argv[1:]]:
        bgr=cv2.imread(idx[i]['arq']); e,el,n,bg,B=tons_da_foto(bgr)
        ch,d=tracar(el)
        bh=linha_fina(el,d)
        Ps=[medir_pagina(bh,cs,x0,x1,d,bgr.shape[1]) for x0,x1,cs in paginas(ch,bgr.shape[1],d)]
        Ps=[p for p in Ps if p is not None]
        for k,P in enumerate(Ps): P.proprio=len(P.v)>=4 and np.ptp(P.v)>=45*P.d
        for k,P in enumerate(Ps):
            outra=[q for q in Ps if q is not P and q.proprio]
            if outra and not getattr(outra[0],'ml',None): acertar_escalas(outra[0])
            acertar_escalas(P,outra[0] if outra else None)
            print(i,'pág',k,'pautas',len(P.v),'rms %.2f'%P.rms,'próprio' if P.proprio else 'herdado','R %.1f'%P.R,'d(v) %.2f..%.2f'%(P.md*P.v[0]+P.bd,P.md*P.v[-1]+P.bd),'Yp',np.round(P.Yp).astype(int).tolist())
            Y0=-34*D_OUT; Y1=P.Yp[-1]+60*D_OUT; X0=-0.07*W_OUT; X1=1.07*W_OUT
            Y0=int(Y0); Y1=int(Y1); X0=int(X0); X1=int(X1)
            mx,my=mapa(P,X0,X1,Y0,Y1)
            r=cv2.remap(e,mx,my,cv2.INTER_LANCZOS4,borderValue=255)
            cv2.imwrite(f'/tmp/nn/dbg/ret{i:02d}_{k}.png',r)
            print('    ',r.shape)
