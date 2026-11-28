"""Leva as cifras de uma folha conhecida (PDF, página do hinário, foto já lida) para outra foto da mesma folha.
Casa pontos das duas imagens (SIFT) e, para cada cifra, usa os pontos vizinhos para achar o lugar dela na foto
(funciona com página curva, foto torta, recorte diferente)."""
import sys,json,os
import cv2,numpy as np
from scipy.spatial import cKDTree
_sift=cv2.SIFT_create(nfeatures=9000,contrastThreshold=0.025)
def _feats(gray,max_dim=1800):
    s=min(1.0,max_dim/max(gray.shape))
    g=cv2.resize(gray,None,fx=s,fy=s,interpolation=cv2.INTER_AREA) if s<1 else gray
    kp,des=_sift.detectAndCompute(g,None)
    if des is None: return np.zeros((0,2),np.float32),None
    return np.float32([k.pt for k in kp])/s,des
_cache={}
def feats(chave,gray,max_dim=1800):
    if chave not in _cache: _cache[chave]=_feats(gray,max_dim)
    return _cache[chave]
def casar_pontos(fs,fd,ratio=0.74):
    ps,ds=fs; pd,dd=fd
    if ds is None or dd is None or len(ps)<8 or len(pd)<8: return np.zeros((0,2),np.float32),np.zeros((0,2),np.float32)
    # casamento exato (sempre dá o mesmo resultado; o aproximado variava de uma rodada para outra)
    mm=cv2.BFMatcher(cv2.NORM_L2).knnMatch(ds,dd,k=2)
    melhor={}
    for x in mm:
        if len(x)==2 and x[0].distance<ratio*x[1].distance:
            # cada ponto da foto casa com um só ponto da origem (o mais parecido): vários-para-um faz a
            # transformação "encolher" tudo para um ponto e parecer um casamento ótimo
            t=x[0].trainIdx
            if t not in melhor or x[0].distance<melhor[t].distance: melhor[t]=x[0]
    S=[ps[m.queryIdx] for m in melhor.values()]; D=[pd[m.trainIdx] for m in melhor.values()]
    return np.float32(S).reshape(-1,2),np.float32(D).reshape(-1,2)
class Registro:
    """casamento entre a folha de origem e a foto: transformação geral (homografia) + campo suave de desvios
    (folha curva) + ajuste local com os pontos vizinhos que concordam com o conjunto"""
    def __init__(self,S,D):
        self.S=S; self.D=D; self.n=0; self.H=None; self.ang=0.0; self.esc=1.0; self.coef=None
        self.ok=np.zeros(len(S),bool)
        if len(S)>=10:
            cv2.setRNGSeed(20261127)
            H,mask=cv2.findHomography(S,D,cv2.RANSAC,6.0)
            if H is not None:
                self.H=H; self.inl=mask.ravel().astype(bool); self.n=int(self.inl.sum())
                # transformação degenerada (tudo cai quase no mesmo lugar, ou escala absurda): não vale
                if self.n>=4:
                    esp_s=float(np.linalg.norm(S[self.inl].std(axis=0))); esp_d=float(np.linalg.norm(D[self.inl].std(axis=0)))
                    if esp_d<0.08*esp_s or esp_d>12*esp_s: self.n=0; self.inl=np.zeros(len(S),bool)
                M=None
                if self.n>=3:
                    try: M,_=cv2.estimateAffinePartial2D(S[self.inl],D[self.inl])
                    except cv2.error: M=None
                if M is not None:
                    self.ang=float(np.degrees(np.arctan2(M[1,0],M[0,0]))); self.esc=float(np.hypot(M[0,0],M[1,0]))
                self.ok=self.inl.copy()
                if self.n>=14:
                    # desvios da homografia variam devagar pela folha; pontos que fogem disso são casamentos errados
                    # (trechos de música repetidos casam com o vizinho)
                    pred=cv2.perspectiveTransform(S.reshape(-1,1,2).astype(np.float32),H).reshape(-1,2); res=D-pred
                    self.c0=S[self.inl].mean(axis=0); self.s0=float(S[self.inl].std())+1.0
                    tol=max(6.0,0.008*float(np.hypot(*np.ptp(D[self.inl],axis=0))))
                    ok=self.inl.copy(); coef=None; grau=2
                    for it in range(5):
                        if ok.sum()<14: break
                        grau=3 if ok.sum()>=90 else 2
                        coef,_,_,_=np.linalg.lstsq(self._base(S[ok],grau),res[ok],rcond=None)
                        err=np.hypot(*(res-self._base(S,grau)@coef).T)
                        novo=err<tol
                        if (novo==ok).all(): break
                        ok=novo
                    if coef is not None and ok.sum()>=14: self.ok=ok; self.coef=coef; self.grau=grau
        idx=np.where(self.ok)[0]; self.idx=idx
        self.tree=cKDTree(S[idx]) if len(idx) else None
    def _base(self,P,grau):
        X=(np.asarray(P,np.float64)-self.c0)/self.s0; x,y=X[:,0],X[:,1]
        cols=[np.ones(len(X)),x,y,x*x,x*y,y*y]
        if grau>=3: cols+=[x*x*x,x*x*y,x*y*y,y*y*y]
        return np.stack(cols,axis=1)
    def geral(self,P):
        """leva pontos da origem para a foto pela transformação geral (homografia + campo suave)"""
        P=np.asarray(P,np.float32).reshape(-1,2)
        q=cv2.perspectiveTransform(P.reshape(-1,1,2),self.H).reshape(-1,2).astype(np.float64)
        if self.coef is not None: q=q+self._base(P,self.grau)@self.coef
        return q
    def local(self,x,y,raio):
        """transformação (2x3) válida perto do ponto (x,y) da origem"""
        if self.tree is None or self.H is None: return None,0
        alvo=self.geral([[x,y]])[0]
        for k in (1.0,1.6,2.6):
            ii=self.tree.query_ball_point([x,y],raio*k)
            if len(ii)<7: continue
            ii=self.idx[ii]
            cv2.setRNGSeed(20261127)
            try: M,inl=cv2.estimateAffinePartial2D(self.S[ii],self.D[ii],method=cv2.RANSAC,ransacReprojThreshold=3.5)
            except cv2.error: M=None
            if M is None: continue
            n=int(inl.sum()); e=float(np.hypot(M[0,0],M[1,0]))
            q=M[:,:2]@np.float64([x,y])+M[:,2]
            if n>=6 and 0.5*self.esc<=e<=2.0*self.esc and abs(((np.degrees(np.arctan2(M[1,0],M[0,0]))-self.ang+180)%360)-180)<12 \
               and np.hypot(*(q-alvo))<=max(10.0,0.05*raio):
                return M,n
        if self.n>=25:
            p=np.float32([[x,y],[x+10,y],[x,y+10]]); q=self.geral(p).astype(np.float32)
            return cv2.getAffineTransform(p,q).astype(np.float64),0
        return None,0
def girar_para_cima(gray,ang):
    """devolve (imagem girada, giro) para a folha ficar de pé; giro = graus no sentido horário aplicados"""
    a=ang%360
    if 45<=a<135: return cv2.rotate(gray,cv2.ROTATE_90_COUNTERCLOCKWISE),270
    if 135<=a<225: return cv2.rotate(gray,cv2.ROTATE_180),180
    if 225<=a<315: return cv2.rotate(gray,cv2.ROTATE_90_CLOCKWISE),90
    return gray,0
def encaixar(dst,x,base,w,cap):
    """ajusta a caixa da cifra à tinta que está de fato na foto; devolve (x,base,w,topo,fundo) ou None"""
    H,W=dst.shape
    x0=int(max(0,x-0.5*cap)); x1=int(min(W,x+w+0.5*cap)); y0=int(max(0,base-1.6*cap)); y1=int(min(H,base+0.6*cap))
    if x1-x0<4 or y1-y0<4: return None
    reg=dst[y0:y1,x0:x1]
    papel=float(np.percentile(reg,85)); lim=min(papel-38,0.72*papel)
    bw=(reg<lim).astype(np.uint8)
    n,lab,st,cen=cv2.connectedComponentsWithStats(bw,8)
    sel=[]
    for i in range(1,n):
        cx,cy=cen[i]; bx,by,bw_,bh,ar=st[i]
        if bh<0.3*cap or bh>1.5*cap or bw_>2.2*cap or ar<0.02*cap*cap: continue
        gx=x0+cx; gy=y0+cy
        if x-0.15*cap<=gx<=x+w+0.15*cap and base-1.25*cap<=gy<=base+0.3*cap: sel.append((x0+bx,y0+by,x0+bx+bw_,y0+by+bh))
    if not sel: return None
    ux0=min(s[0] for s in sel); ux1=max(s[2] for s in sel); uy0=min(s[1] for s in sel)
    altos=sorted(s[3] for s in sel if s[3]-s[1]>=0.6*cap)
    ub=altos[len(altos)//2] if altos else max(s[3] for s in sel)
    uy1=max(s[3] for s in sel)
    if not (0.55*w<=ux1-ux0<=1.5*w+0.4*cap): return None
    return ux0,ub,ux1-ux0,uy0,uy1
def refinar(src_gray,dst_gray,M,x,base,w,cap):
    """acerta o lugar da cifra comparando o desenho dela na origem com a foto; devolve (dx,dy,nota)"""
    e=float(np.hypot(M[0,0],M[1,0]))
    mg=0.3*cap
    sx0=int(max(0,x-mg)); sx1=int(min(src_gray.shape[1],x+w+mg)); sy0=int(max(0,base-cap-mg)); sy1=int(min(src_gray.shape[0],base+0.35*cap+mg))
    if sx1-sx0<4 or sy1-sy0<4: return 0,0,0.0
    pw=max(4,int(round((sx1-sx0)*e))); ph=max(4,int(round((sy1-sy0)*e)))
    # leva o pedaço da origem para a escala/rotação da foto
    A=M.copy(); canto=A[:,:2]@np.float32([sx0,sy0])+A[:,2]
    A[:,2]-=canto
    # caixa que contém o pedaço transformado
    cs=np.float32([[sx0,sy0],[sx1,sy0],[sx0,sy1],[sx1,sy1]]); q=(M[:,:2]@cs.T).T+M[:,2]
    qx0,qy0=q.min(axis=0); qx1,qy1=q.max(axis=0)
    A=M.copy(); A[:,2]-=np.float32([qx0,qy0])
    tw=int(np.ceil(qx1-qx0)); th=int(np.ceil(qy1-qy0))
    if tw<5 or th<5 or tw>900 or th>400: return 0,0,0.0
    molde=cv2.warpAffine(src_gray,A,(tw,th),flags=cv2.INTER_AREA if e<1 else cv2.INTER_LINEAR,borderValue=255)
    if molde.std()<6: return 0,0,0.0
    capd=cap*e; bx=int(1.3*capd)+4; by=int(2.3*capd)+4
    rx0=int(qx0)-bx; ry0=int(qy0)-by; rx1=int(qx0)+tw+bx; ry1=int(qy0)+th+by
    H,W=dst_gray.shape
    ax0=max(0,rx0); ay0=max(0,ry0); ax1=min(W,rx1); ay1=min(H,ry1)
    if ax1-ax0<tw+2 or ay1-ay0<th+2: return 0,0,0.0
    reg=dst_gray[ay0:ay1,ax0:ax1]
    r=cv2.matchTemplate(reg,molde,cv2.TM_CCOEFF_NORMED)
    # prefere perto do lugar previsto
    yy,xx=np.mgrid[0:r.shape[0],0:r.shape[1]]
    px=int(qx0)-ax0; py=int(qy0)-ay0
    dist=np.hypot((xx-px),(yy-py)*0.7)/max(1.0,capd)
    nota=r-0.035*dist
    j=int(np.argmax(nota)); iy,ix=divmod(j,r.shape[1])
    return float(ix-px),float(iy-py),float(r[iy,ix])
def cor_papel(cor,x,y0,w,y1):
    H,W=cor.shape[:2]
    a=cor[max(0,int(y0)-4):min(H,int(y1)+4),max(0,int(x)-4):min(W,int(x+w)+4)].reshape(-1,3)
    if len(a)==0: return 'ffffff'
    sm=a.sum(axis=1); claro=a[sm>=np.percentile(sm,65)]
    return '%02x%02x%02x'%tuple(int(v) for v in np.median(claro,axis=0)[::-1])
CAPF={'a':0.727,'s':0.711,'t':0.662,'m':0.72}
def transferir(src_gray,folha,dst_cor,chave_src=None,min_inl=18,debug=None,fd=None,modo='fino'):
    """folha: dict(w,h,f,c=[[x,base,w,fs,txt,...]]) nas coordenadas de src_gray. Devolve (folha da foto, relatório)"""
    dst_gray=cv2.cvtColor(dst_cor,cv2.COLOR_BGR2GRAY)
    fs_=feats(chave_src,src_gray) if chave_src else _feats(src_gray)
    S,D=casar_pontos(fs_,fd if fd is not None else _feats(dst_gray)); R=Registro(S,D)
    rel=dict(pontos=len(S),inl=R.n,ang=round(R.ang,1),esc=round(R.esc,3))
    if R.n<min_inl: return None,rel
    g2,giro=girar_para_cima(dst_gray,R.ang)
    c2=dst_cor if giro==0 else cv2.rotate(dst_cor,{90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}[giro])
    if giro:
        S,D=casar_pontos(fs_,_feats(g2)); R=Registro(S,D); rel.update(inl=R.n,ang=round(R.ang,1),giro=giro)
        if R.n<min_inl: return None,rel
    fam=folha.get('f','s'); kcap=CAPF[fam]
    cs=[]; achou=0; semlugar=0; postas=[]; pendentes=[]; pares=[]; notas=[]
    fila=[(c,None) for c in folha['c']]
    while fila:
        c,Mforc=fila.pop(0)
        x,base,w,fs,txt=c[:5]; cap=fs*kcap
        if Mforc is None:
            M,n=R.local(x+w/2,base-cap/2,raio=max(120.0,9*fs))
            if M is None: pendentes.append(c); continue
        else: M=Mforc; n=6
        p=np.float32([[x,base],[x+w,base],[x,base-cap]]); q=(M[:,:2]@p.T).T+M[:,2]
        e=float(np.hypot(M[0,0],M[1,0]))
        xd=float(q[0,0]); bd=float((q[0,1]+q[1,1])/2); wd=float(w*e); capd=float(cap*e)
        if not (-capd<=xd<=g2.shape[1] and 0<=bd<=g2.shape[0]+capd): semlugar+=1; continue
        if modo=='geom':
            # só geometria (a cifra impressa está riscada na foto: comparar o desenho dela enganaria)
            dx=dy=0.0; nota=1.0 if n>=6 else 0.45; topo=bd-capd*1.08; fundo=bd+0.12*capd
        else:
            dx,dy,nota=refinar(src_gray,g2,M,x,base,w,cap)
            if nota>=0.42: xd+=dx; bd+=dy
            aj=encaixar(g2,xd,bd,wd,capd) if nota>=0.30 else None
            if aj: xd,bd,wd,topo,fundo=aj; achou+=1
            elif nota>=0.5: topo=bd-capd*1.05; fundo=bd+0.1*capd
            else:
                if Mforc is None: pendentes.append(c)
                else: semlugar+=1
                continue
        if nota>=0.42:
            M2=M.copy(); M2[0,2]+=dx; M2[1,2]+=dy; postas.append((x+w/2,base,M2))
        # no fim da primeira passada: tenta as que ficaram sem lugar com a transformação da vizinha já colocada
        if not fila and pendentes and postas and Mforc is None:
            pass
        fsd=capd/kcap
        ent=[int(round(xd)),int(round(bd)),int(round(wd)),round(fsd,1),txt,cor_papel(c2,xd,topo,wd,fundo),0,int(round(max(bd-topo+3,0.82*fsd))),int(round(max(fundo-bd+3,0.08*fsd)))]
        cs.append(ent); pares.append([float(x),float(base),float(w),float(cap),ent[0],ent[1],ent[2],round(capd,1)]); notas.append(round(float(nota),3))
        if not fila and pendentes and postas:
            novos=[]
            for pc in pendentes:
                px,pb=pc[0]+pc[2]/2,pc[1]
                viz=min(postas,key=lambda o:abs(o[0]-px)+3*abs(o[1]-pb))
                novos.append((pc,viz[2]))
            pendentes=[]; fila=novos; postas=[]      # uma única rodada extra
    semlugar+=len(pendentes)
    rel.update(cifras=len(cs),encaixadas=achou,sem_lugar=semlugar,pares=pares,notas=notas)
    if not cs: return None,rel
    Hh,Ww=dst_gray.shape
    out=dict(w=Ww,h=Hh,f=fam,c=cs)
    if folha.get('n'): out['n']=1
    if folha.get('k'): out['k']=folha['k']
    if giro: out['r']=giro
    if debug:
        vis=c2.copy()
        for e in cs:
            cv2.rectangle(vis,(e[0],e[1]-e[7]),(e[0]+e[2],e[1]+e[8]),(0,150,0) if e[4]!='?' else (0,0,255),2)
            cv2.putText(vis,e[4],(e[0],e[1]-e[7]-4),cv2.FONT_HERSHEY_SIMPLEX,max(0.5,e[3]/45),(255,0,0),2)
        cv2.imwrite(debug,vis,[cv2.IMWRITE_JPEG_QUALITY,72])
    return out,rel
