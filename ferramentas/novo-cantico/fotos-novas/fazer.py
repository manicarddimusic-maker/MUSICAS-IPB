"""Foto do hinário -> páginas desentortadas (uma ou duas por foto), em tons limpos, com as medidas guardadas."""
import sys,os,json,pickle
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from tracar import tons_da_foto,tracar,paginas,linha_fina,reguas
from retif import medir_pagina,acertar_escalas,mapa,W_OUT,D_OUT
from pagina import niveis
from mapa import mapa as mapa_fotos

ACIMA=38        # quanto se olha acima da 1ª pauta (em espaços de pauta)
ABAIXO=206      # e abaixo dela
MX=0.075        # margem lateral (fração da largura da pauta)

def mascaras(bgr,bg,B,d,caixa=None):
    """o que na foto não é página: crochê claro e amarelado, fio dourado e preto (mesa, capa) — só vale o que
    encosta na borda da foto (nunca um pedaço no meio da página) -> uint8 (255 = não é página)"""
    H,W=bgr.shape[:2]
    lab=cv2.cvtColor(bgr,cv2.COLOR_BGR2Lab).astype(np.float32)
    L=lab[...,0]*100/255; b=lab[...,2]-128
    k=int(1.6*d)|1
    Lb=cv2.blur(L,(k,k)); bb=cv2.blur(b,(k,k))
    cl=b[::4,::4][L[::4,::4]>70]
    bref=float(np.percentile(cl,35)) if cl.size>500 else 3.0
    cro=(((Lb>75)&(bb>bref+5.5))|((Lb>40)&(bb>bref+13.0))).astype(np.uint8)
    cro=cv2.morphologyEx(cro,cv2.MORPH_OPEN,np.ones((k,k),np.uint8))
    cro=cv2.dilate(cro,np.ones((int(2.5*d)|1,int(2.5*d)|1),np.uint8))
    esc=((bg-B)<14).astype(np.uint8)
    esc=cv2.morphologyEx(esc,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    esc=cv2.dilate(esc,np.ones((int(0.8*d)|1,int(0.8*d)|1),np.uint8))
    m=(cro|esc)
    n,lb,st,_=cv2.connectedComponentsWithStats(m,8)
    fica=np.zeros(n,bool)
    for j in range(1,n):
        x,y,w,h,a=st[j]
        if x<=1 or y<=1 or x+w>=W-1 or y+h>=H-1: fica[j]=True
    return (fica[lb]*255).astype(np.uint8),bref

def casco(P,H,W,d):
    """região da foto ocupada pelas pautas de uma página (com uma folga) -> máscara 255 dentro"""
    vs=np.linspace(P.v[0]-1.5*d,P.v[-1]+5.5*d,40)
    esq=[];dire=[]
    for v in vs:
        xl=P.ml*v+P.bl-1.5*d; xr=P.mr*v+P.br+1.5*d
        esq.append((xl,float(P.M.y(xl,v)+P.F(xl,v)))); dire.append((xr,float(P.M.y(xr,v)+P.F(xr,v))))
    pol=np.int32(np.r_[np.array(esq),np.array(dire)[::-1]])
    m=np.zeros((H,W),np.uint8); cv2.fillPoly(m,[pol],255)
    return m

def alinhar(PL,PR,H):
    """diferença de Y entre as duas páginas de uma foto (mesma altura física na lombada) -> YR - YL"""
    difs=[]
    for vL in np.linspace(PL.v[0],PL.v[-1]+4*PL.d,12):
        xg=0.5*((PL.mr*vL+PL.br)+(PR.ml*vL+PR.bl))
        y=float(PL.M.y(xg,vL)+PL.F(xg,vL))
        # v da página direita que passa por (xg, y)
        vR=y
        for _ in range(8):
            f=float(PR.M.y(xg,vR)+PR.F(xg,vR)); vR+=(y-f)
        difs.append(float(np.interp(vR,PR.vv,PR.YY))-float(np.interp(vL,PL.vv,PL.YY)))
    return float(np.median(difs)),float(np.ptp(difs))

def tratar_foto(i,salvar=True):
    F=mapa_fotos()[i]
    bgr=cv2.imread(F['arq']); H,W=bgr.shape[:2]
    e,el,n,bg,B=tons_da_foto(bgr)
    from ncpauta import linhas_finas,espaco
    d=espaco(linhas_finas(e))
    if d is None: d=espaco(linhas_finas(el))
    if d is None: return []
    msk,bref=mascaras(bgr,bg,B,d)
    ch,d=tracar(el,d=d,debug=f'/tmp/nn/dbg/tr{i:02d}.jpg',fundo_dbg=e,nao_pagina=msk)
    if ch:
        # espaço medido nas próprias cadeias; se for bem diferente do palpite, traça de novo
        dm=d*float(np.median(np.concatenate([c['E'] for c in ch])))
        if abs(dm/d-1)>0.03:
            ch,d=tracar(el,d=dm,debug=f'/tmp/nn/dbg/tr{i:02d}.jpg',fundo_dbg=e,nao_pagina=msk)
    bh=linha_fina(el,d)
    rg=reguas(bh,d,ch,nao_pagina=msk)
    Ps=[medir_pagina(bh,cs,x0,x1,d,W,regs=rg) for x0,x1,cs in paginas(ch,W,d)]
    Ps=[p for p in Ps if p is not None]
    # numa foto deitada ficam as duas maiores; numa em pé, a maior
    Ps.sort(key=lambda p:-(p.x1-p.x0)); Ps=Ps[:2 if F['deitada'] else 1]; Ps.sort(key=lambda p:p.x0)
    for P in Ps: P.proprio=len(P.v)>=4 and np.ptp(P.v)>=45*P.d
    for P in sorted(Ps,key=lambda p:-int(p.proprio)):
        outra=[q for q in Ps if q is not P and q.proprio and hasattr(q,'ml')]
        acertar_escalas(P,outra[0] if outra else None)
    out=[]
    for P in Ps: msk[casco(P,H,W,d)>0]=0          # dentro das pautas nunca é "fora da página"
    for k,P in enumerate(Ps):
        pg=F['pgs'][k] if k<len(F['pgs']) else None
        X0=int(-MX*W_OUT); X1=int((1+MX)*W_OUT); Y0=int(-ACIMA*D_OUT); Y1=int(ABAIXO*D_OUT)
        mx,my=mapa(P,X0,X1,Y0,Y1)
        nr=cv2.remap(n.astype(np.float32),mx,my,cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_CONSTANT,borderValue=1.0)
        bgr_=cv2.remap(bg.astype(np.float32),mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        mr=cv2.remap(msk,mx,my,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=255)
        fora=((mx<1)|(my<1)|(mx>W-2)|(my>H-2))
        P.pg=pg; P.foto=i; P.X0=X0; P.Y0=Y0; P.rot=F['rot']; P.k=k; P.npag=len(Ps)
        P.escala=float(np.median((P.mr-P.ml)*P.v+(P.br-P.bl)))/W_OUT        # px da foto por px da página
        out.append(dict(P=P,n=nr,bg=bgr_,mask=mr,fora=fora))
    if len(Ps)==2:
        dif,var=alinhar(Ps[0],Ps[1],H)
        Ps[0].alinha=0.0; Ps[1].alinha=dif; Ps[0].alinha_var=Ps[1].alinha_var=var
    if salvar:
        for o in out:
            P=o['P']
            base=f'/tmp/nn/ret2/{i:02d}_{P.k}'
            np.save(base+'_n.npy',(np.clip(o['n'],0,1.3)*200).astype(np.uint8))
            np.save(base+'_bg.npy',np.clip(o['bg'],0,255).astype(np.uint8))
            cv2.imwrite(base+'_m.png',np.where(o['fora'],128,o['mask']).astype(np.uint8))
            pickle.dump(P,open(base+'.pkl','wb'))
    return out
if __name__=='__main__':
    from multiprocessing import Pool
    ids=[int(a) for a in sys.argv[1:]] or list(range(67))
    def um(i):
        try:
            out=tratar_foto(i)
            return i,[(o['P'].pg,len(o['P'].v),len(o['P'].reg_v),round(o['P'].rms,2),round(o['P'].R,1),'próprio' if o['P'].proprio else 'herdado',round(o['P'].escala,2),round(getattr(o['P'],'alinha',0)/D_OUT,1),round(getattr(o['P'],'alinha_var',0)/D_OUT,2)) for o in out],None
        except Exception as ex:
            import traceback; return i,[],traceback.format_exc()
    with Pool(2) as p:
        for i,r,err in p.imap_unordered(um,ids):
            print(i,r,flush=True)
            if err: print(err,flush=True)
