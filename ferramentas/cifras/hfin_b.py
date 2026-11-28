"""Etapa B: na foto, separa a tinta da caneta (letras escritas à mão + riscos em cima das cifras impressas) da impressão,
trabalhando no desenho "endireitado" de cada linha de cifras (coordenadas da folha limpa de origem)."""
import sys,json,glob,os,re
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
import mao
R='/home/claude/musicas-ipb/public'
GIRO={90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}
def papel(cor,x0,y0,x1,y1):
    a=cor[max(0,int(y0)-4):int(y1)+4,max(0,int(x0)-4):int(x1)+4].reshape(-1,3)
    if len(a)==0: return 'ffffff'
    sm=a.sum(axis=1); cl=a[sm>=np.percentile(sm,70)]
    return '%02x%02x%02x'%tuple(int(v) for v in np.median(cl,axis=0)[::-1])
def linhas_fonte(P):
    """agrupa as cifras da folha de origem em linhas, tolerando página inclinada e linha curva"""
    n=len(P); pai=list(range(n))
    def acha(i):
        while pai[i]!=i: pai[i]=pai[pai[i]]; i=pai[i]
        return i
    # inclinação da página: mediana das inclinações entre cada cifra e a vizinha da direita
    incl=[]
    for i in range(n):
        best=None; cap=P[i][3]
        for j in range(n):
            dx=P[j][0]-P[i][0]
            if 1.5*cap<dx<12*cap and abs(P[j][1]-P[i][1])<0.25*dx+0.3*cap and (best is None or dx<best[0]): best=(dx,(P[j][1]-P[i][1])/dx)
        if best: incl.append(best[1])
    m=float(np.median(incl)) if len(incl)>=4 else 0.0
    def nivel(i): return P[i][1]-m*P[i][0]
    for i in range(n):
        for j in range(i+1,n):
            cap=max(P[i][3],P[j][3]); dx=abs((P[i][0]+P[i][2]/2)-(P[j][0]+P[j][2]/2))
            if abs(nivel(i)-nivel(j))<0.35*cap+0.04*min(dx,12*cap): pai[acha(i)]=acha(j)
    g={}
    for i in range(n): g.setdefault(acha(i),[]).append(i)
    rows=[sorted(r,key=lambda i:P[i][0]) for r in g.values()]
    rows.sort(key=lambda r:float(np.median([nivel(i) for i in r])))
    # duas "linhas" a menos de 1,3 cap uma da outra (comparando cifras vizinhas em x) são a mesma linha de cifras
    mudou=True
    while mudou:
        mudou=False
        for a_ in range(len(rows)):
            for b_ in range(a_+1,len(rows)):
                ok=False
                for i in rows[a_]:
                    j=min(rows[b_],key=lambda j:abs(P[j][0]-P[i][0])); cap=max(P[i][3],P[j][3]); dx=abs(P[j][0]-P[i][0])
                    if abs(nivel(i)-nivel(j))<1.3*cap+0.04*min(dx,12*cap): ok=True; break
                if ok:
                    rows[a_]=sorted(rows[a_]+rows[b_],key=lambda i:P[i][0]); del rows[b_]; mudou=True; break
            if mudou: break
    return rows
Y0=4.4      # a linha de base das cifras fica a 4,4 "cap" do topo da faixa
Y1=0.8      # e a faixa desce 0,8 "cap" abaixo dela
def mapa_da_linha(P,idx,xs0,bw,f,cap,abaixo=None):
    """faixa endireitada da linha de cifras: u = x na folha de origem, v = distância à linha de base.
    Devolve os mapas (faixa -> foto) e (faixa -> folha de origem). Acompanha a linha de âncora em âncora
    (cada cifra já colocada), então segue a curva da folha, na foto e na origem."""
    o=sorted(idx,key=lambda i:P[i][0])
    xa=np.array([P[i][0]+P[i][2]/2 for i in o]); ba=np.array([P[i][1] for i in o],np.float64)
    xd=np.array([P[i][4]+P[i][6]/2 for i in o]); bd=np.array([P[i][5] for i in o],np.float64)
    esc=np.array([P[i][7]/P[i][3] for i in o])
    # âncoras quase na mesma coluna (cifras coladas): fica só uma
    keep=[0]
    for i in range(1,len(o)):
        if xa[i]-xa[keep[-1]]>=1.2*cap: keep.append(i)
    xa,ba,xd,bd,esc=xa[keep],ba[keep],xd[keep],bd[keep],esc[keep]
    xs=xs0+np.arange(bw)/f; n=len(xa)
    bh=int(round((Y0+(Y1 if abaixo is None else abaixo))*cap*f))
    if n==1:
        Bx=xd[0]+(xs-xa[0])*esc[0]; By=np.full(bw,bd[0]); Tx=np.ones(bw); Ty=np.zeros(bw); sc=np.full(bw,esc[0]); bs=np.full(bw,ba[0])
    else:
        j=np.clip(np.searchsorted(xa,xs)-1,0,n-2); t=(xs-xa[j])/np.maximum(1e-6,xa[j+1]-xa[j])
        Bx=xd[j]+t*(xd[j+1]-xd[j]); By=bd[j]+t*(bd[j+1]-bd[j]); bs=ba[j]+t*(ba[j+1]-ba[j])
        ja=np.clip(j-1,0,n-1); jb=np.clip(j+2,0,n-1)
        dx=xd[jb]-xd[ja]; dy=bd[jb]-bd[ja]
        # direção da linha na foto, já descontada a inclinação da linha na origem
        ang_o=np.arctan2(ba[jb]-ba[ja],np.maximum(1e-6,xa[jb]-xa[ja])); ang_d=np.arctan2(dy,dx)
        Tx=np.cos(ang_d-ang_o); Ty=np.sin(ang_d-ang_o)
        sc=np.interp(xs,xa,esc)
    dyv=(np.arange(bh)/f-Y0*cap).reshape(-1,1)
    mapx=(Bx.reshape(1,-1)+(-Ty.reshape(1,-1))*dyv*sc.reshape(1,-1)).astype(np.float32)
    mapy=(By.reshape(1,-1)+(Tx.reshape(1,-1))*dyv*sc.reshape(1,-1)).astype(np.float32)
    msx=np.repeat(xs.reshape(1,-1),bh,axis=0).astype(np.float32)
    msy=(bs.reshape(1,-1)+dyv).astype(np.float32)
    return mapx,mapy,msx,msy,float(np.median(esc)),bh
def acertar_pela_pauta(P,idx,xs0,bw,f,cap,cinza,sg):
    """a pauta impressa logo abaixo da linha de cifras está igual na folha limpa e na foto (a caneta não mexe nela):
    compara as duas, trecho por trecho, e corrige a altura de cada cifra na foto. Devolve quantas cifras mexeu."""
    AB=4.8
    mapx,mapy,msx,msy,e,bh=mapa_da_linha(P,idx,xs0,bw,f,cap,abaixo=AB)
    H,W=cinza.shape
    fg=cv2.remap(cinza,mapx,mapy,cv2.INTER_LINEAR,borderValue=255); src=cv2.remap(sg,msx,msy,cv2.INTER_LINEAR,borderValue=255)
    c=cap*f; vb=int(Y0*c); lo=vb+int(0.3*c)
    A=255.0-src[lo:].astype(np.float32); B=255.0-fg[lo:].astype(np.float32)
    larg=int(9*c); passo=int(3*c); maxd=int(2.4*c)
    us=[];dvs=[]
    for u0 in range(0,max(1,bw-larg//2),passo):
        a=A[:,u0:u0+larg].mean(axis=1); b=B[:,u0:u0+larg].mean(axis=1)
        dentro=((mapx[lo:,u0:u0+larg]>=0)&(mapx[lo:,u0:u0+larg]<W-1)&(mapy[lo:,u0:u0+larg]>=0)&(mapy[lo:,u0:u0+larg]<H-1)).mean()
        if dentro<0.8 or a.std()<3 or b.std()<3: continue
        a=(a-a.mean())/a.std(); b=(b-b.mean())/b.std()
        best=None
        for dv in range(-maxd,maxd+1):
            if dv>=0: x=a[:len(a)-dv]; y=b[dv:]
            else: x=a[-dv:]; y=b[:len(b)+dv]
            if len(x)<0.55*len(a): continue
            sc=float((x*y).mean())-0.03*abs(dv)/c
            if best is None or sc>best[0]: best=(sc,dv)
        if best and best[0]>0.4: us.append(u0+larg/2); dvs.append(best[1])
    if len(us)<2: return 0,None
    us=np.array(us,float); dvs=np.array(dvs,float)
    # tira saltos isolados (engano de uma linha da pauta): mediana de 3 vizinhos
    if len(dvs)>=3:
        md=dvs.copy()
        for i in range(len(dvs)): md[i]=np.median(dvs[max(0,i-1):i+2])
        dvs=md
    n=0
    for i in idx:
        u=(P[i][0]+P[i][2]/2-xs0)*f; dv=float(np.interp(u,us,dvs))
        if abs(dv)<0.12*c: continue
        ui=int(np.clip(u,0,bw-1)); v0=int(np.clip(vb,0,bh-1)); v1=int(np.clip(vb+dv,0,bh-1))
        P[i][4]+=float(mapx[v1,ui]-mapx[v0,ui]); P[i][5]+=float(mapy[v1,ui]-mapy[v0,ui]); n+=1
    return n,(us,dvs)
def acertar_pelos_riscos(P,idx,xs0,bw,f,cap,cinza):
    """altura da linha de cifras na foto: a linha impressa (riscada ou não) é uma fileira de manchas compactas nos lugares
    das cifras, com papel branco logo abaixo (antes da pauta). Procura, para cima e para baixo, a altura em que os lugares
    das cifras ficam mais cheios de tinta e o vão de baixo mais vazio, e leva a linha inteira para lá."""
    AB=4.4
    mapx,mapy,msx,msy,e,bh=mapa_da_linha(P,idx,xs0,bw,f,cap,abaixo=AB)
    H,W=cinza.shape
    fg=cv2.remap(cinza,mapx,mapy,cv2.INTER_LINEAR,borderValue=255)
    tinta=(fg<150).astype(np.float32); c=cap*f; vb=int(Y0*c)
    S=np.zeros(bh,np.float32); n=0
    for i in idx:
        a0=int(max(0,(P[i][0]-xs0)*f-0.1*c)); a1=int(min(bw,(P[i][0]+P[i][2]-xs0)*f+0.1*c))
        if a1-a0<3: continue
        S+=tinta[:,a0:a1].mean(axis=1); n+=1
    if n<2: return 0,0.0
    S/=n
    cs=np.concatenate([[0],np.cumsum(S)])
    def media(v0,v1):
        v0=int(np.clip(v0,0,bh)); v1=int(np.clip(v1,0,bh))
        return float((cs[v1]-cs[v0])/max(1,v1-v0))
    def nota(dv): return media(vb+dv-1.05*c,vb+dv+0.1*c)-media(vb+dv+0.22*c,vb+dv+0.8*c)
    lim=int(4.0*c); melhor=max(range(-lim,lim+1),key=lambda dv:nota(dv)-0.012*abs(dv)/c)
    n0=nota(0); n1=nota(melhor)
    if abs(melhor)<0.15*c or n1-n0<0.10 or n1<0.18: return 0,n0
    for i in idx:
        u=int(np.clip((P[i][0]+P[i][2]/2-xs0)*f,0,bw-1)); v0=int(np.clip(vb,0,bh-1)); v1=int(np.clip(vb+melhor,0,bh-1))
        P[i][4]+=float(mapx[v1,u]-mapx[v0,u]); P[i][5]+=float(mapy[v1,u]-mapy[v0,u])
    return melhor,n1
def acertar_por_trechos(P,idx,xs0,bw,f,cap,cinza,so=None):
    """folha dobrada/curva: um pedaço da linha de cifras pode estar numa altura diferente do resto.
    Para cada cifra, olha as vizinhas (2 de cada lado) e procura a altura em que os lugares ficam cheios de tinta
    com papel limpo embaixo; só mexe quando a evidência é forte. Devolve quantas cifras mexeu."""
    if len(idx)<4: return 0
    AB=4.4
    mapx,mapy,msx,msy,e,bh=mapa_da_linha(P,idx,xs0,bw,f,cap,abaixo=AB)
    fg=cv2.remap(cinza,mapx,mapy,cv2.INTER_LINEAR,borderValue=255)
    tinta=(fg<150).astype(np.float32); c=cap*f; vb=int(Y0*c)
    o=sorted(idx,key=lambda i:P[i][0]); perfis=[]
    for i in o:
        a0=int(max(0,(P[i][0]-xs0)*f-0.1*c)); a1=int(min(bw,(P[i][0]+P[i][2]-xs0)*f+0.1*c))
        perfis.append(tinta[:,a0:a1].mean(axis=1) if a1-a0>=3 else np.zeros(bh,np.float32))
    lim=int(2.6*c); dvs=[]
    for k in range(len(o)):
        S=np.mean(perfis[max(0,k-2):k+3],axis=0); cs=np.concatenate([[0],np.cumsum(S)])
        def media(v0,v1):
            v0=int(np.clip(v0,0,bh)); v1=int(np.clip(v1,0,bh)); return float((cs[v1]-cs[v0])/max(1,v1-v0))
        def nota(dv): return media(vb+dv-1.05*c,vb+dv+0.1*c)-media(vb+dv+0.22*c,vb+dv+0.8*c)
        m=max(range(-lim,lim+1),key=lambda dv:nota(dv)-0.02*abs(dv)/c); n0=nota(0); n1=nota(m)
        dvs.append(m if (abs(m)>=0.3*c and n1-n0>=0.16 and n1>=0.3) else 0)
    # só vale o que os vizinhos confirmam (mediana de 3)
    sm=[int(np.median(dvs[max(0,k-1):k+2])) for k in range(len(dvs))]
    n=0
    for k,i in enumerate(o):
        dv=sm[k]
        if dv==0 or (so is not None and i not in so): continue
        u=int(np.clip((P[i][0]+P[i][2]/2-xs0)*f,0,bw-1)); v0=int(np.clip(vb,0,bh-1)); v1=int(np.clip(vb+dv,0,bh-1))
        P[i][4]+=float(mapx[v1,u]-mapx[v0,u]); P[i][5]+=float(mapy[v1,u]-mapy[v0,u]); n+=1
    TRECHOS.append([round(d/c,2) for d in sm])
    return n
TRECHOS=[]
def _tokens(m,c,kx,ky,minpx,minh,dy=0):
    j=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_RECT,(max(3,int(kx*c))|1,max(3,int(ky*c))|1)))
    n,lab,st,_=cv2.connectedComponentsWithStats(j,8); out=[]
    for i in range(1,n):
        bx,by,bw_,bh_,ar=[int(v) for v in st[i]]
        mm=m[by:by+bh_,bx:bx+bw_]*(lab[by:by+bh_,bx:bx+bw_]==i).astype(np.uint8)
        px=int(mm.sum())
        if px<minpx*c*c: continue
        ys,xs=np.nonzero(mm); h=int(ys.max()-ys.min()+1); w=int(xs.max()-xs.min()+1)
        if h<minh*c and px<0.3*c*c: continue
        if h<0.5*c and w>3.5*c: continue              # traço comprido e fino: resto de linha de pauta/ligadura
        out.append([bx+int(xs.min()),dy+by+int(ys.min()),bx+int(xs.max())+1,dy+by+int(ys.max())+1,px])
    return out
def casar_riscos(cif,riscos,c):
    """liga as vagas (lugares de cifra impressa) aos riscos da caneta que as cobrem.
    1º por sobreposição; depois, o que sobrou, na ordem da linha, tolerando desvio (registro imperfeito).
    Devolve (vaga->risco, risco->[vagas], desvio de cada vaga casada sem sobreposição)"""
    v2r={}; r2v={}
    for qi,q in enumerate(cif):
        best=None
        for ri,r in enumerate(riscos):
            ov=min(r[2],q['x1'])-max(r[0],q['x0'])
            if ov>0.3*min(r[2]-r[0],q['x1']-q['x0']) and (best is None or ov>best[0]): best=(ov,ri)
        if best: v2r[qi]=best[1]; r2v.setdefault(best[1],[]).append(qi)
    desvio={}
    # trechos entre pares já ligados: casa pela ordem
    livres_v=[qi for qi in range(len(cif)) if qi not in v2r]; livres_r=[ri for ri in range(len(riscos)) if ri not in r2v and riscos[ri][4]>=0.25*c*c]
    if livres_v and livres_r:
        cx_v={qi:(cif[qi]['x0']+cif[qi]['x1'])/2 for qi in range(len(cif))}; cx_r={ri:(riscos[ri][0]+riscos[ri][2])/2 for ri in range(len(riscos))}
        lv=sorted(livres_v,key=lambda qi:cx_v[qi]); lr=sorted(livres_r,key=lambda ri:cx_r[ri])
        n,m=len(lv),len(lr); INF=1e9; PULA=1.7; LIM=3.3
        D=[[0.0]*(m+1) for _ in range(n+1)]; T=[[0]*(m+1) for _ in range(n+1)]
        for a in range(1,n+1): D[a][0]=a*PULA; T[a][0]=1
        for b in range(1,m+1): D[0][b]=b*PULA; T[0][b]=2
        def custo(qi,ri):
            d=abs(cx_v[qi]-cx_r[ri])/c
            if d>LIM: return INF
            # não pode atravessar um par já ligado
            lo,hi=sorted((cx_v[qi],cx_r[ri]))
            for qj,rj in v2r.items():
                if lo<cx_v[qj]<hi or lo<cx_r[rj]<hi: return INF
            return d
        for a in range(1,n+1):
            for b in range(1,m+1):
                o=[(D[a-1][b-1]+custo(lv[a-1],lr[b-1]),0),(D[a-1][b]+PULA,1),(D[a][b-1]+PULA,2)]
                D[a][b],T[a][b]=min(o)
        a,b=n,m
        while a>0 or b>0:
            t=T[a][b]
            if t==0 and a>0 and b>0:
                qi,ri=lv[a-1],lr[b-1]; v2r[qi]=ri; r2v.setdefault(ri,[]).append(qi); desvio[qi]=cx_r[ri]-cx_v[qi]; a-=1; b-=1
            elif t==1: a-=1
            else: b-=1
    return v2r,r2v,desvio
def analisar(nome,debug=False,guardar_faixas=False):
    J=json.load(open(f'/tmp/cif/hfin/{nome}.json'))
    if not J['fontes']: return None
    g=J['fontes'][0]['r']; dst=cv2.imread(R+J['img']); up=cv2.rotate(dst,GIRO[g]) if g else dst
    cinza=mao.aplainar(cv2.cvtColor(up,cv2.COLOR_BGR2GRAY)); H,W=cinza.shape
    h_,s_,v_=mao._hsv(up)
    picos=[p for p in mao.picos_de_cor(up,70) if not (10<=p[0]<=40)]
    matiz=picos[0][0] if picos else None
    if matiz is not None:
        dh=np.abs(h_-matiz); dh=np.minimum(dh,180-dh)
        pen=(((s_>=60)&(dh<=22)&(v_>40)&(v_<250))|((s_>=20)&(dh<=16)&(cinza<185))).astype(np.uint8)*255
    else: pen=None
    out=dict(nome=nome,img=J['img'],r=g,w=W,h=H,k=J['k'],matiz=matiz,linhas=[])
    vis=up.copy() if debug else None
    faixas={}
    for fi,F in enumerate(J['fontes']):
        P=[list(p) for p in F['pares']]; C=F['c']
        if not P: continue
        sg=cv2.imread(F['caminho'],0)
        rows=linhas_fonte(P)
        capm=float(np.median([p[3] for p in P]))
        XS0=min(p[0] for p in P)-3.5*capm; XS1=max(p[0]+p[2] for p in P)+3.2*capm
        for ri,idx in enumerate(rows):
            cap=float(np.median([P[i][3] for i in idx])); bs=float(np.median([P[i][1] for i in idx]))
            e=float(np.median([P[i][7]/P[i][3] for i in idx])); f=float(min(2.0,max(1.0,e)))
            xs0=max(0.0,XS0); xs1=min(float(sg.shape[1]),XS1)
            bw=int((xs1-xs0)*f)
            if bw<20: continue
            c=cap*f; v_row=int((Y0-1.2)*cap*f)
            def passada():
                mapx,mapy,msx,msy,e_,bh=mapa_da_linha(P,idx,xs0,bw,f,cap)
                fg=cv2.remap(cinza,mapx,mapy,cv2.INTER_LINEAR,borderValue=255)
                src=cv2.remap(sg,msx,msy,cv2.INTER_LINEAR,borderValue=255)
                imp=(src<165).astype(np.uint8)
                kA=max(3,int(0.42*c))|1; kR=max(3,int(0.2*c))|1
                imp_d=cv2.dilate(imp,np.ones((kA,kA),np.uint8)); imp_d[v_row:]=cv2.dilate(imp,np.ones((kR,kR),np.uint8))[v_row:]
                tinta=(fg<150).astype(np.uint8)
                extra=tinta&(1-imp_d)
                extra=cv2.morphologyEx(extra,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
                if pen is not None:
                    fp=cv2.remap(pen,mapx,mapy,cv2.INTER_LINEAR,borderValue=0)
                    cor_m=(fp>100).astype(np.uint8)
                    # acima da linha das cifras, "tinta de cor" bem em cima de impressão é nota/pauta da linha de cima
                    # numa foto azulada (sombra), não caneta
                    k2=max(3,int(0.2*c))|1
                    cor_m[:v_row]&=(1-cv2.dilate(imp,np.ones((k2,k2),np.uint8)))[:v_row]
                    extra|=cor_m
                dentro=((mapx>=0)&(mapx<W-1)&(mapy>=0)&(mapy<H-1)).astype(np.uint8)
                extra[dentro==0]=0
                n,lab,st,_=cv2.connectedComponentsWithStats(extra,8)
                ruim=np.where(st[:,4]<max(6,0.02*c*c))[0]; ruim=ruim[ruim>0]
                if len(ruim): extra[np.isin(lab,ruim)]=0
                riscos=_tokens(extra[v_row:].copy(),c,0.5,0.3,0.14,0.3,dy=v_row)
                letras=_tokens(extra[:v_row].copy(),c,0.75,0.4,0.10,0.4)
                letras=[b for b in letras if not (b[1]<=1 and b[3]>=v_row-1)]
                cif=[]
                for i in idx:
                    xs,b,ws,cs_=P[i][:4]
                    cif.append(dict(i=i,x0=(xs-xs0)*f,x1=(xs+ws-xs0)*f,base=Y0*cap*f,txt=C[i][4],xs=xs,bs=b,ws=ws,cap=cs_))
                cif.sort(key=lambda q:q['x0'])
                vb_=int(Y0*cap*f)
                for q in cif:
                    a0=int(max(0,q['x0']-0.2*c)); a1=int(min(bw,q['x1']+0.2*c)); ya_=max(0,vb_-int(1.1*c)); yb_=vb_+int(0.2*c)
                    reg=tinta[ya_:yb_,a0:a1]
                    q['tinta']=float(reg.mean()) if reg.size else 0.0
                    # caneta preta por cima de letra preta: não dá para separar pela cor nem pelo desenho, mas a mancha
                    # fica bem mais cheia de tinta do que a letra impressa sozinha -> conta como risco no lugar da cifra
                    if reg.size and not any(min(r[2],q['x1'])-max(r[0],q['x0'])>0.3*min(r[2]-r[0],q['x1']-q['x0']) for r in riscos):
                        a_s=float(imp[ya_:yb_,a0:a1].mean())
                        if q['tinta']>=0.5 and q['tinta']>=1.35*a_s+0.06:
                            ys_,xs_=np.nonzero(reg)
                            riscos.append([a0+int(xs_.min()),ya_+int(ys_.min()),a0+int(xs_.max())+1,ya_+int(ys_.max())+1,int(reg.sum())])
                riscos.sort()
                return mapx,mapy,msx,msy,e_,bh,src,riscos,letras,cif,dentro
            nv,_nt=acertar_pelos_riscos(P,idx,xs0,bw,f,cap,cinza)
            mapx,mapy,msx,msy,e,bh,src,riscos,letras,cif,dentro=passada()
            v2r,r2v,desvio=casar_riscos(cif,riscos,c)
            # folha dobrada: cifras sem risco embaixo podem estar na altura errada; tenta acertar só essas,
            # e fica com o acerto só se mais cifras passarem a cair em cima de risco
            nt=0
            if len(v2r)<len(cif):
                guarda={i:list(P[i]) for i in idx}
                soltas={cif[qi]['i'] for qi in range(len(cif)) if qi not in v2r}
                if acertar_por_trechos(P,idx,xs0,bw,f,cap,cinza,so=soltas):
                    r2=passada(); v2,r2v2,d2=casar_riscos(r2[9],r2[7],c)
                    if len(v2)>len(v2r):
                        mapx,mapy,msx,msy,e,bh,src,riscos,letras,cif,dentro=r2; nt=len(v2)-len(v2r); v2r,r2v,desvio=v2,r2v2,d2
                    else:
                        for i in idx: P[i]=guarda[i]
            # registro escorregou neste trecho? acerta as âncoras pelos riscos (o risco está em cima da cifra impressa) e refaz;
            # repete: depois de acertar uma cifra, as vizinhas (fim de linha, folha curva) passam a casar também
            mexe={}; tot_mexe=0
            for _vez in range(3):
                mexe={qi:d for qi,d in desvio.items() if abs(d)>0.5*c}
                if not mexe: break
                tot_mexe+=len(mexe)
                vb=min(bh-1,int(Y0*cap*f))
                for qi,d in mexe.items():
                    q=cif[qi]; u0=int(np.clip((q['x0']+q['x1'])/2,0,bw-1)); u1=int(np.clip((q['x0']+q['x1'])/2+d,0,bw-1))
                    i=q['i']; P[i][4]+=float(mapx[vb,u1]-mapx[vb,u0]); P[i][5]+=float(mapy[vb,u1]-mapy[vb,u0])
                mapx,mapy,msx,msy,e,bh,src,riscos,letras,cif,dentro=passada()
                v2r,r2v,desvio=casar_riscos(cif,riscos,c)
            mexe=dict.fromkeys(range(tot_mexe))
            for qi,q in enumerate(cif): q['risco']=v2r.get(qi)
            def caixa_foto(b):
                u0=int(np.clip(b[0],0,bw-1)); u1=int(np.clip(b[2]-1,0,bw-1)); v0=int(np.clip(b[1],0,bh-1)); v1=int(np.clip(b[3]-1,0,bh-1))
                xs_=[mapx[v0,u0],mapx[v0,u1],mapx[v1,u0],mapx[v1,u1]]; ys_=[mapy[v0,u0],mapy[v0,u1],mapy[v1,u0],mapy[v1,u1]]
                return [int(np.floor(min(xs_))),int(np.floor(min(ys_))),int(np.ceil(max(xs_)))+1,int(np.ceil(max(ys_)))+1]
            vb=min(bh-1,int(Y0*cap*f))
            L=dict(fonte=F['chave'],fi=fi,ri=ri,bs=bs,cap=cap,f=f,xs0=xs0,bw=bw,bh=bh,v_row=v_row,cif=cif,riscos=riscos,letras=letras,capd=cap*e,dentro=float((dentro>0).mean()),
                   r2v={str(k):v for k,v in r2v.items()},mexidas=len(mexe),vert=nv,trechos=nt,
                   base_rel=Y0*cap*f,base_src=[float(v) for v in msy[vb,::8]],base_foto=[[float(mapx[vb,u]),float(mapy[vb,u])] for u in range(0,bw,8)],esc=e)
            L['riscos_foto']=[caixa_foto(b) for b in riscos]; L['letras_foto']=[caixa_foto(b) for b in letras]
            # lugar de cada vaga na foto (pela faixa, já com as âncoras acertadas)
            for q in cif:
                u0=int(np.clip(q['x0'],0,bw-1)); u1=int(np.clip(q['x1'],0,bw-1))
                q['foto']=[float(mapx[vb,u0]),float((mapy[vb,u0]+mapy[vb,u1])/2),float(np.hypot(mapx[vb,u1]-mapx[vb,u0],mapy[vb,u1]-mapy[vb,u0])),float(q['cap']*e)]
            out['linhas'].append(L)
            if guardar_faixas:
                faixas[(fi,ri)]=(cv2.remap(up,mapx,mapy,cv2.INTER_LINEAR,borderValue=(255,255,255)),src)
            if debug:
                for b in L['letras_foto']: cv2.rectangle(vis,(b[0],b[1]),(b[2],b[3]),(0,170,0),2)
                for bi,b in enumerate(L['riscos_foto']): cv2.rectangle(vis,(b[0],b[1]),(b[2],b[3]),(200,0,200) if str(bi) in L['r2v'] else (0,0,255),2)
                for q in cif:
                    xd,bd,wd,cd=q['foto']
                    cv2.rectangle(vis,(int(xd),int(bd-cd)),(int(xd+wd),int(bd)),(255,140,0) if q['txt']!='?' else (0,200,255),2)
                    cv2.putText(vis,q['txt'],(int(xd),int(bd+1.1*cd)),cv2.FONT_HERSHEY_SIMPLEX,max(0.45,cd/38),(200,80,0),2)
    fnl=f'/tmp/cif/hfin/linhas/{nome}.txt'
    if os.path.exists(fnl):
        sc=max(H,W)/1800.0
        capd=float(np.median([L['capd'] for L in out['linhas']])) if out['linhas'] else 0.012*W
        if pen is not None: tinta_m=(pen>0).astype(np.uint8)
        else: tinta_m=(cinza<120).astype(np.uint8)
        for mi,ln in enumerate(open(fnl)):
            p=ln.split(';')[0].split()
            if len(p)<4: continue
            x0,y0,x1,y1=[float(v)*sc for v in p[:4]]
            if len(p)>4: capd_=float(p[4])*sc
            else: capd_=capd
            comp=float(np.hypot(x1-x0,y1-y0)); bw=int(comp); c=capd_; bh=int(round((Y0+Y1)*c)); v_row=int((Y0-1.2)*c)
            tx,ty=(x1-x0)/comp,(y1-y0)/comp
            u=np.arange(bw).reshape(1,-1); dyv=(np.arange(bh)-Y0*c).reshape(-1,1)
            mapx=(x0+tx*u-ty*dyv).astype(np.float32); mapy=(y0+ty*u+tx*dyv).astype(np.float32)
            extra=(cv2.remap(tinta_m*255,mapx,mapy,cv2.INTER_LINEAR,borderValue=0)>100).astype(np.uint8)
            n,lab,st,_=cv2.connectedComponentsWithStats(extra,8)
            ruim=np.where(st[:,4]<max(6,0.02*c*c))[0]; ruim=ruim[ruim>0]
            if len(ruim): extra[np.isin(lab,ruim)]=0
            riscos=_tokens(extra[v_row:].copy(),c,0.5,0.3,0.14,0.3,dy=v_row)
            letras=_tokens(extra[:v_row].copy(),c,0.75,0.4,0.10,0.4)
            def caixa_foto(b):
                u0=int(np.clip(b[0],0,bw-1)); u1=int(np.clip(b[2]-1,0,bw-1)); v0=int(np.clip(b[1],0,bh-1)); v1=int(np.clip(b[3]-1,0,bh-1))
                xs_=[mapx[v0,u0],mapx[v0,u1],mapx[v1,u0],mapx[v1,u1]]; ys_=[mapy[v0,u0],mapy[v0,u1],mapy[v1,u0],mapy[v1,u1]]
                return [int(np.floor(min(xs_))),int(np.floor(min(ys_))),int(np.ceil(max(xs_)))+1,int(np.ceil(max(ys_)))+1]
            vb=min(bh-1,int(Y0*c))
            L=dict(fonte='mao:%d'%mi,fi=900+mi,ri=0,bs=float(y0),cap=c,f=1.0,xs0=0.0,bw=bw,bh=bh,v_row=v_row,cif=[],riscos=riscos,letras=letras,capd=c,dentro=1.0,r2v={},mexidas=0,
                   base_rel=Y0*c,base_src=[0.0]*(bw//8+1),base_foto=[[float(mapx[vb,uu]),float(mapy[vb,uu])] for uu in range(0,bw,8)],esc=1.0)
            L['riscos_foto']=[caixa_foto(b) for b in riscos]; L['letras_foto']=[caixa_foto(b) for b in letras]
            out['linhas'].append(L)
            if guardar_faixas: faixas[(900+mi,0)]=(cv2.remap(up,mapx,mapy,cv2.INTER_LINEAR,borderValue=(255,255,255)),np.full((bh,bw),255,np.uint8))
    if debug: cv2.imwrite(f'/tmp/cif/hfin/dbg_{nome}.jpg',vis,[cv2.IMWRITE_JPEG_QUALITY,80])
    return (out,faixas,up) if guardar_faixas else out
if __name__=='__main__':
    o=analisar(sys.argv[1],debug=True)
    for L in o['linhas']: print(L['fonte'],'cifras',len(L['cif']),'riscos',len(L['riscos']),'letras',len(L['letras']),'cap',round(L['cap'],1),'mexidas',L['mexidas'],'vert',L.get('vert'))
