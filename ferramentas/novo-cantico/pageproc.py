import cv2,numpy as np,json
from enh2 import flatten
def skew_angle(n):
    s=900/max(n.shape); small=cv2.resize(n,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    bw=(small<170).astype(np.float32)
    h,w=bw.shape; c=(w/2,h/2)
    def score(a):
        M=cv2.getRotationMatrix2D(c,a,1.0)
        r=cv2.warpAffine(bw,M,(w,h),flags=cv2.INTER_LINEAR,borderValue=0)
        p=r[:,int(w*0.12):int(w*0.88)].sum(axis=1)
        return float((np.diff(p)**2).sum())
    best=max(np.arange(-4,4.01,0.5),key=score)
    best=max(np.arange(best-0.5,best+0.51,0.1),key=score)
    return float(best)
def clean_borders(n):
    """apaga faixas pretas/sombras grudadas na borda (lombada, fundo da mesa)"""
    h,w=n.shape
    dark=(n<110).astype(np.uint8)
    k=max(3,int(min(h,w)*0.004))|1
    dark=cv2.morphologyEx(dark,cv2.MORPH_CLOSE,np.ones((k,k),np.uint8))
    num,lab,st,cen=cv2.connectedComponentsWithStats(dark,8)
    out=n.copy()
    for i in range(1,num):
        x,y,bw_,bh_,a=st[i]
        touch=(x<=2 or y<=2 or x+bw_>=w-2 or y+bh_>=h-2)
        if not touch: continue
        # componente grande encostado na borda: faixa/sombra
        if a>0.0006*h*w and (bw_>0.25*w or bh_>0.12*h or a>0.004*h*w):
            m=(lab[y:y+bh_,x:x+bw_]==i)
            m=cv2.dilate(m.astype(np.uint8),np.ones((9,9),np.uint8))>0
            out[y:y+bh_,x:x+bw_][m]=255
    return out
def content_box(n):
    h,w=n.shape
    ink=(n<150).astype(np.uint8)
    ink=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
    rows=ink.sum(axis=1); cols=ink.sum(axis=0)
    ys=np.where(rows>max(3,0.004*w))[0]; xs=np.where(cols>max(3,0.004*h))[0]
    if len(ys)<10 or len(xs)<10: return 0,0,w,h
    y0,y1,x0,x1=ys[0],ys[-1],xs[0],xs[-1]
    px=int(0.03*w); py=int(0.022*h)
    return max(0,x0-px),max(0,y0-py),min(w,x1+px),min(h,y1+py)
def curve(n,q):
    t=float(np.clip((q-6000)/(15000-6000),0,1))
    hi=246-t*(246-214); gamma=1.6-t*(1.6-1.15); lo=25.
    v=np.clip((n-lo)/(hi-lo),0,1)**gamma
    return (v*255+0.5).astype(np.uint8)
def curve2(n,hi=253.,lo=30.,g=4.):
    v=np.clip((n-lo)/(hi-lo),0,1)**g
    return (v*255+0.5).astype(np.uint8)
def tirar_manchas(n,frac=0.014):
    """clareia manchas largas e fracas (verso da folha, sujeira) sem mexer nos traços"""
    h,w=n.shape; s=1400/max(h,w)
    small=cv2.resize(n,None,fx=s,fy=s,interpolation=cv2.INTER_AREA).astype(np.uint8)
    k=max(9,int(1400*frac))|1
    bg=cv2.morphologyEx(small,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    bg=cv2.GaussianBlur(bg,(0,0),3)
    bg=cv2.resize(bg,(w,h),interpolation=cv2.INTER_LINEAR).astype(np.float32)
    # só normaliza onde o "fundo" é claro (mancha fraca); fundo escuro de verdade fica como está
    bg=np.where(bg>170,bg,255.)
    return np.clip(n/np.maximum(bg,1)*255,0,255)
def staff_visibility(e):
    """fração de pixels em linhas horizontais finas e longas (pautas) numa imagem já tratada"""
    s=1500/e.shape[0]; g=cv2.resize(e,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    bh=cv2.morphologyEx(g,cv2.MORPH_BLACKHAT,cv2.getStructuringElement(cv2.MORPH_RECT,(1,7)))
    lines=cv2.morphologyEx((bh>28).astype(np.uint8),cv2.MORPH_OPEN,np.ones((1,45),np.uint8))
    return float(lines.mean())
def process(name,q,staff=0.01,src=None,so_base=False):
    g=cv2.imread(src or f'/tmp/nc/pgs/{name}.png',0)
    sat=float((g>=254).mean())
    lavada=sat>0.5            # o app de escanear já deixou o papel branco puro
    n=g.astype(np.float32) if lavada else flatten(g)
    n=clean_borders(n)
    a=skew_angle(n)
    h,w=n.shape
    if abs(a)>=0.1:
        M=cv2.getRotationMatrix2D((w/2,h/2),a,1.0)
        n=cv2.warpAffine(n,M,(w,h),flags=cv2.INTER_CUBIC,borderValue=255)
    x0,y0,x1,y1=content_box(n)
    n=n[y0:y1,x0:x1]
    if lavada:
        # tom geral suave; só os traços finos e fracos (linhas da pauta, hastes) são reforçados,
        # para não escurecer manchas e o verso da folha
        n=tirar_manchas(n)
        base=curve2(n,253.,30.,2.2)
        if so_base: return base,dict(ang=a,box=(int(x0),int(y0),int(x1),int(y1)),lavada=lavada)
        k=max(7,int(n.shape[0]*0.0042))|1
        u=n.astype(np.uint8)
        bh=np.maximum(cv2.morphologyEx(u,cv2.MORPH_BLACKHAT,cv2.getStructuringElement(cv2.MORPH_RECT,(1,k))),
                      cv2.morphologyEx(u,cv2.MORPH_BLACKHAT,cv2.getStructuringElement(cv2.MORPH_RECT,(k,1))))
        finos=curve2(255.-bh.astype(np.float32),253.,30.,6.5 if staff<0.006 else 4.0)
        e=np.minimum(base,finos)
    else:
        e=curve(n,q)
    return e,dict(ang=a,box=(int(x0),int(y0),int(x1),int(y1)),lavada=lavada,vis=staff_visibility(e))
if __name__=='__main__':
    D=json.load(open('/tmp/nc/ident6.json')); by={d['name']:d for d in D}
    tiles=[]
    for nme in ('a000S','a131L','c051L','a002L','d004L','c011L','b089L','a076S'):
        e,info=process(nme,by[nme]['sharp'],by[nme]['staff']); print(nme,e.shape,info)
        H=760; t=cv2.resize(e,(int(e.shape[1]*H/e.shape[0]),H),interpolation=cv2.INTER_AREA)
        cv2.putText(t,nme,(4,18),cv2.FONT_HERSHEY_SIMPLEX,0.55,0,2); tiles.append(t); tiles.append(np.full((H,12),90,np.uint8))
    cv2.imwrite('/tmp/nc/proc_test.jpg',np.hstack(tiles),[cv2.IMWRITE_JPEG_QUALITY,78])
