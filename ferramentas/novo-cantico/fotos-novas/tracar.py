"""Acha e segue as pautas na própria foto (página curva, duas páginas, sombra, trechos fora de foco):
cada pauta vira uma cadeia de pontos (x, y da 1ª linha). Serve de régua para desentortar a página."""
import sys
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from pagina import normalizar,niveis
from ncpauta import linhas_finas,espaco

INCL=(-0.20,-0.14,-0.09,-0.045,0.0,0.045,0.09,0.14,0.20)

def tons_da_foto(bgr):
    """-> (e_firme, e_leve, n, bg, B): e_leve guarda as linhas fracas (fora de foco) para o traçado"""
    n,bg,B=normalizar(bgr)
    e=niveis(n,bg,nitidez=0.0)
    el=niveis(n,bg,hi=0.92,nitidez=0.0)
    return e,el,n,bg,B

def linha_fina(e,d):
    k=max(5,int(0.75*d)|1)
    bh=cv2.morphologyEx(e,cv2.MORPH_BLACKHAT,cv2.getStructuringElement(cv2.MORPH_RECT,(1,k)))
    return np.minimum(bh,100).astype(np.float32)/100.0

def pente(P,d):
    """resposta do pente de 5 linhas (posição = 1ª linha), a menor das 5 linhas e a escala usada"""
    n,H=P.shape
    ys=np.arange(H,dtype=np.float32)
    best=None
    for esc in (0.93,0.965,1.0,1.035,1.07):
        dd=d*esc
        soma=np.zeros_like(P); minimo=np.full_like(P,9.0); entre=np.zeros_like(P)
        for k in range(5):
            idx=ys+k*dd; i0=np.clip(np.floor(idx).astype(int),0,H-1); i1=np.clip(i0+1,0,H-1); f=idx-np.floor(idx)
            v=P[:,i0]*(1-f)+P[:,i1]*f
            v[:,idx>H-1]=0
            soma+=v; minimo=np.minimum(minimo,v)
        for k in range(4):
            idx=ys+(k+0.5)*dd; i0=np.clip(np.floor(idx).astype(int),0,H-1); i1=np.clip(i0+1,0,H-1); f=idx-np.floor(idx)
            entre+=P[:,i0]*(1-f)+P[:,i1]*f
        C=soma-0.8*entre
        if best is None: best=[C,minimo,np.full(P.shape,esc,np.float32),soma]
        else:
            m=C>best[0]
            best[0]=np.where(m,C,best[0]); best[1]=np.where(m,minimo,best[1]); best[2]=np.where(m,esc,best[2]); best[3]=np.where(m,soma,best[3])
    return best

def picos(bh,d,cmin=0.45,mmin=0.05):
    """picos do pente em faixas estreitas, testando várias inclinações -> (cols, lista por faixa de (y, força, inclinação, escala))"""
    H,W=bh.shape
    sw=int(round(2.0*d)); passo=max(4,int(round(0.8*d)))
    cols=np.arange(sw//2,W-sw//2,passo)
    r=max(2,int(round(0.45*d)))
    todos=[[] for _ in cols]
    for s in INCL:
        pad=int(abs(s)*W/2)+2
        A=np.float32([[1,0,0],[-s,1,s*W/2+pad]])
        sh=cv2.warpAffine(bh,A,(W,H+2*pad),flags=cv2.INTER_LINEAR,borderValue=0)
        sm=cv2.blur(sh,(sw,1)); sm=cv2.GaussianBlur(sm,(1,5),0.9)
        P=np.minimum(np.ascontiguousarray(sm[:,cols].T),0.6)
        C,M,E,SO=pente(P,d)
        C=np.where((M>=mmin)&(M>=0.4*SO/5.0),C,-9.0).astype(np.float32)
        Cm=cv2.dilate(C,np.ones((1,2*r+1),np.uint8))
        ok=(C>=Cm-1e-6)&(C>=cmin)
        jj,yy=np.where(ok)
        for j,y in zip(jj,yy):
            if 1<=y<C.shape[1]-1:
                a,b,c=C[j,y-1],C[j,y],C[j,y+1]; den=a-2*b+c
                off=0.5*(a-c)/den if (den<0 and a>-5 and c>-5) else 0.0
                yr=y+float(np.clip(off,-0.5,0.5))-pad+s*(cols[j]-W/2)
                if 0<=yr<H: todos[j].append((yr,float(b),s,float(E[j,y])))
    # junta os picos de inclinações diferentes que são a mesma pauta
    out=[]
    for lst in todos:
        lst.sort(key=lambda p:-p[1]); fica=[]
        for p in lst:
            if all(abs(p[0]-q[0])>0.5*d for q in fica): fica.append(p)
        fica.sort(); out.append(fica)
    return cols,out

def ligar(cols,pk,d,gap=5,tol=0.42,forte=1.0):
    """liga os picos de faixas vizinhas em cadeias (uma por pauta); só pico forte começa cadeia"""
    ativas=[]; fechadas=[]
    for j,lst in enumerate(pk):
        usados=set()
        for ch in sorted(ativas,key=lambda c:-len(c['pts'])):
            xj=cols[j]; xl,yl=ch['pts'][-1][0],ch['pts'][-1][1]
            yp=yl+ch['inc']*(xj-xl)
            melhor=None
            for i,p in enumerate(lst):
                if i in usados: continue
                dy=abs(p[0]-yp)
                if dy<=tol*d and (melhor is None or dy<melhor[0]): melhor=(dy,i)
            if melhor is not None:
                i=melhor[1]; usados.add(i); p=lst[i]
                ch['pts'].append((float(xj),p[0],p[1],p[3])); ch['falhas']=0
                q=ch['pts'][-8:]
                if len(q)>=3:
                    X=np.array([t[0] for t in q]); Y=np.array([t[1] for t in q])
                    ch['inc']=float(np.polyfit(X,Y,1)[0])
                else: ch['inc']=p[2]
            else: ch['falhas']+=1
        for i,p in enumerate(lst):
            if i not in usados and p[1]>=forte: ativas.append(dict(pts=[(float(cols[j]),p[0],p[1],p[3])],inc=p[2],falhas=0))
        ainda=[]
        for ch in ativas:
            (fechadas if ch['falhas']>gap else ainda).append(ch)
        ativas=ainda
    return fechadas+ativas

def _cadeia(pts):
    X=np.array([p[0] for p in pts]); Y=np.array([p[1] for p in pts]); F=np.array([p[2] for p in pts]); E=np.array([p[3] for p in pts])
    return dict(X=X,Y=Y,F=F,E=E,xa=float(X[0]),xb=float(X[-1]))

def tracar(el,d=None,debug=None,fundo_dbg=None,nao_pagina=None):
    """-> (cadeias, d). cadeia = dict(X, Y (1ª linha), F (força), E (escala do espaço), xa, xb)"""
    H,W=el.shape
    if d is None:
        d=espaco(linhas_finas(el))
        if d is None: return [],None
    bh=linha_fina(el,d)
    cols,pk=picos(bh,d)
    # da esquerda p/ direita e da direita p/ esquerda (para pegar o começo fraco das pautas)
    ch=ligar(cols,pk,d)
    ch2=ligar(cols[::-1],pk[::-1],d)
    cad=[]
    for c in ch: cad.append(_cadeia(c['pts']))
    for c in ch2: cad.append(_cadeia(c['pts'][::-1]))
    cad=[c for c in cad if len(c['X'])>=12 and c['xb']-c['xa']>=12*d and (c['F']>=1.0).sum()>=8]
    if nao_pagina is not None:
        bons=[]
        for c in cad:
            xi=np.clip(c['X'].astype(int),0,W-1); yi=np.clip((c['Y']+2*d).astype(int),0,H-1)
            if (nao_pagina[yi,xi]>0).mean()<0.2: bons.append(c)
        cad=bons
    # mesma pauta achada duas vezes -> une os pontos (fica com o mais forte em cada coluna)
    cad.sort(key=lambda c:-len(c['X']))
    grupos=[]
    for c in cad:
        posto=False
        for g in grupos:
            x0=max(c['xa'],g['xa']); x1=min(c['xb'],g['xb'])
            if x1-x0<3*d: continue
            xs=np.linspace(x0,x1,9)
            dy=np.abs(np.interp(xs,c['X'],c['Y'])-np.interp(xs,g['X'],g['Y']))
            if np.median(dy)<0.35*d:
                m={}
                for cc in (g,c):
                    for x,y,f,e in zip(cc['X'],cc['Y'],cc['F'],cc['E']):
                        if x not in m or f>m[x][1]: m[x]=(y,f,e)
                xs_=sorted(m)
                g.update(_cadeia([(x,)+m[x] for x in xs_])); posto=True; break
            if np.median(dy)<3.2*d: posto=True; break     # deslocada de uma linha: é a mesma pauta, descarta
        if not posto: grupos.append(c)
    # junta pedaços separados por um trecho ilegível (nunca através da lombada)
    juntou=True
    while juntou:
        juntou=False
        grupos.sort(key=lambda c:c['xa'])
        for i in range(len(grupos)):
            for j in range(len(grupos)):
                if i==j: continue
                a,b=grupos[i],grupos[j]
                gapx=b['xa']-a['xb']
                if not (0<gapx<=7.0*d): continue
                ia=np.polyfit(a['X'][-8:],a['Y'][-8:],1); ib=np.polyfit(b['X'][:8],b['Y'][:8],1)
                xm=(a['xb']+b['xa'])/2
                if abs(np.polyval(ia,xm)-np.polyval(ib,xm))<=0.4*d:
                    grupos[i]=dict(X=np.r_[a['X'],b['X']],Y=np.r_[a['Y'],b['Y']],F=np.r_[a['F'],b['F']],E=np.r_[a['E'],b['E']],xa=a['xa'],xb=b['xb'])
                    del grupos[j]; juntou=True; break
            if juntou: break
    grupos.sort(key=lambda c:(np.median(c['Y'])))
    if debug:
        vis=cv2.cvtColor(fundo_dbg if fundo_dbg is not None else el,cv2.COLOR_GRAY2BGR)
        for k,c in enumerate(grupos):
            cor=[(0,0,255),(0,160,0),(255,80,0),(200,0,200)][k%4]
            for x,y,e in zip(c['X'],c['Y'],c['E']):
                cv2.circle(vis,(int(x),int(round(y))),3,cor,-1); cv2.circle(vis,(int(x),int(round(y+4*d*e))),3,cor,-1)
        s=1600/max(vis.shape[:2])
        cv2.imwrite(debug,cv2.resize(vis,None,fx=s,fy=s,interpolation=cv2.INTER_AREA),[cv2.IMWRITE_JPEG_QUALITY,80])
    return grupos,d

def reguas(bh,d,cad,nao_pagina=None,pmin=0.33):
    """linhas horizontais compridas fora das pautas (bordas das caixas de texto) -> cadeias (X, Y) de 1 linha"""
    H,W=bh.shape
    # faixas das pautas já achadas não contam
    veda=np.zeros((H,W),np.uint8)
    for c in cad:
        xs=np.arange(max(0,int(c['xa']-6*d)),min(W,int(c['xb']+6*d)),4)
        ys=np.interp(xs,c['X'],c['Y'])
        # fora do trecho medido, continua com a inclinação das pontas
        ia=np.polyfit(c['X'][:10],c['Y'][:10],1); ib=np.polyfit(c['X'][-10:],c['Y'][-10:],1)
        ys=np.where(xs<c['xa'],np.polyval(ia,xs),np.where(xs>c['xb'],np.polyval(ib,xs),ys))
        topo=np.c_[xs,ys-1.6*d]; base=np.c_[xs,ys+5.6*d][::-1]
        cv2.fillPoly(veda,[np.int32(np.r_[topo,base])],255)
    if nao_pagina is not None: veda=np.maximum(veda,nao_pagina)
    sw=int(round(3.0*d)); passo=max(4,int(round(0.8*d)))
    cols=np.arange(sw//2,W-sw//2,passo)
    r=max(2,int(round(0.6*d)))
    todos=[[] for _ in cols]
    for s in INCL:
        pad=int(abs(s)*W/2)+2
        A=np.float32([[1,0,0],[-s,1,s*W/2+pad]])
        sh=cv2.warpAffine(bh,A,(W,H+2*pad),flags=cv2.INTER_LINEAR,borderValue=0)
        sm=cv2.blur(sh,(sw,1)); sm=cv2.GaussianBlur(sm,(1,5),0.9)
        P=np.ascontiguousarray(sm[:,cols].T)
        Pm=cv2.dilate(P,np.ones((1,2*r+1),np.uint8))
        jj,yy=np.where((P>=Pm-1e-6)&(P>=pmin))
        for j,y in zip(jj,yy):
            if 1<=y<P.shape[1]-1:
                a,b,c=P[j,y-1],P[j,y],P[j,y+1]; den=a-2*b+c
                off=0.5*(a-c)/den if den<0 else 0.0
                yr=y+float(np.clip(off,-0.5,0.5))-pad+s*(cols[j]-W/2)
                if 0<=yr<H and veda[int(yr),int(cols[j])]==0: todos[j].append((yr,float(b),s,1.0))
    pk=[]
    for lst in todos:
        lst.sort(key=lambda p:-p[1]); fica=[]
        for p in lst:
            if all(abs(p[0]-q[0])>0.5*d for q in fica): fica.append(p)
        fica.sort(); pk.append(fica)
    ch=ligar(cols,pk,d,gap=4,tol=0.3,forte=pmin)
    out=[]
    for c in ch:
        if len(c['pts'])<20: continue
        k=_cadeia(c['pts'])
        out.append(k)
    return out

def paginas(cad,W,d):
    """separa as cadeias por página (esquerda/direita) pela cobertura em x -> lista de (x0, x1, cadeias)"""
    cov=np.zeros(W,np.int32)
    for c in cad: cov[int(c['xa']):int(c['xb'])+1]+=1
    lim=max(2,int(0.3*cov.max())) if len(cad)>=4 else 1
    on=cov>=lim; segs=[]; x=0
    while x<W:
        if on[x]:
            x0=x
            while x<W and on[x]: x+=1
            segs.append([x0,x])
        else: x+=1
    # buracos pequenos dentro da mesma página
    j=[]
    for s in segs:
        if j and s[0]-j[-1][1]<5*d: j[-1][1]=s[1]
        else: j.append(s)
    out=[]
    for x0,x1 in j:
        if x1-x0<30*d: continue
        cs=[c for c in cad if min(c['xb'],x1)-max(c['xa'],x0)>=0.5*(c['xb']-c['xa']) and c['xb']-c['xa']>=0.25*(x1-x0)]
        if len(cs)>=1: out.append((x0,x1,cs))
    return out

if __name__=='__main__':
    import json,time
    idx=json.load(open('/tmp/nn/fotos.json'))
    for i in [int(a) for a in sys.argv[1:]]:
        t=time.time()
        bgr=cv2.imread(idx[i]['arq'])
        e,el,n,bg,B=tons_da_foto(bgr)
        ch,d=tracar(el,debug=f'/tmp/nn/dbg/tr{i:02d}.jpg',fundo_dbg=e)
        pg=paginas(ch,bgr.shape[1],d)
        print(i,bgr.shape,'d=%.2f'%d if d else 'sem d','cadeias',len(ch),'| páginas:',[(x0,x1,len(cs)) for x0,x1,cs in pg],'%.1fs'%(time.time()-t))
        for x0,x1,cs in pg: print('    ',[(int(c['xa']),int(c['xb']),int(np.median(c['Y'])),len(c['X']),round(float(np.median(c['F'])),2)) for c in cs])
