"""Completa, com a página antiga, o pedaço de baixo que a foto nova cortou (última pauta, rodapé)."""
import sys,os,json
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nn')
import cv2,numpy as np
from registro import _feats,casar_pontos
from final import ALT,PAD_T,W_OUT,d
ANT='/tmp/nc/final_antes/' if os.path.isdir('/tmp/nc/final_antes') else '/tmp/nc/final/'
PAGS=json.load(open(ANT+'paginas.json')) if os.path.exists(ANT+'paginas.json') else json.load(open('/tmp/nc/final/paginas.json'))

def registrar(old,new,valido):
    """homografia página antiga -> quadro novo, só com pontos da parte que a foto nova cobre"""
    best=None
    for dim in (1500,1100):
        fo=_feats(old,dim); fn=_feats(new,dim)
        S,D=casar_pontos(fo,fn,ratio=0.8)
        if len(S)<12: continue
        ok=valido[np.clip(D[:,1].astype(int),0,new.shape[0]-1),np.clip(D[:,0].astype(int),0,new.shape[1]-1)]
        S,D=S[ok],D[ok]
        if len(S)<12: continue
        cv2.setRNGSeed(11)
        Hm,mk=cv2.findHomography(S,D,cv2.RANSAC,4.0)
        if Hm is None: continue
        n=int(mk.sum())
        if best is None or n>best[1]: best=(Hm,n,S[mk.ravel()>0],D[mk.ravel()>0])
        if n>=80: break
    return best

MUSICA=(554,572,576,488,376,176,276,462)      # a foto nova cortou a última pauta: só nessas a página antiga completa o pedaço de baixo
def limpar_rodape(img,falta,j,sempre=False):
    """rodapé (número da página e seção) cortado pela beira da foto, ou vindo borrado da página antiga: some inteiro"""
    H,W=img.shape; yz=j['yz']; x0=j['x0']; yF=int(yz+j['fim']*d)
    ca=int(x0-1.0*d); cb=int(x0+W_OUT+1.0*d)
    ink=(img[:,ca:cb]<150)
    tem=ink.sum(axis=1)>=6
    a0=max(0,int(yF-4.5*d)); runs=[]; y=a0
    while y<H:
        if tem[y]:
            s=y
            while y<H and tem[y]: y+=1
            runs.append([s,y-1])
        else: y+=1
    jn=[]
    for r in runs:
        if jn and r[0]-jn[-1][1]<0.3*d: jn[-1][1]=r[1]
        else: jn.append(r)
    cand=[r for r in jn if r[1]-r[0]+1<=3.9*d and yF-2.2*d<=r[1]<=yF+1.4*d and r[0]>a0+2]
    if not cand:
        # rodapé fora do lugar esperado ou em pedaços: se a foto não o cobre inteiro (ou só sobraram restos), sai
        ult=[r for r in jn if r[0]>a0+2 and r[1]>=yF-2.4*d]
        if ult:
            a=ult[0][0]; b=ult[-1][1]
            xs=np.where(ink[a:b+1].any(axis=0))[0]
            xa=max(0,ca+int(xs[0])-int(0.8*d)); xb=min(W,ca+int(xs[-1])+int(0.8*d))
            pouco=int(ink[a:b+1].sum())<260
            tudo=np.where((img[a:b+1,:]<150).any(axis=0))[0]
            if pouco or falta[max(0,a-2):min(H,b+3),xa:xb].any() or (len(tudo) and (tudo[0]<=3 or tudo[-1]>=W-4)):
                img=img.copy(); img[max(0,a-3):,:]=255; return img,'restos'
        return img,None
    a,b=cand[-1]
    xs=np.where(ink[a:b+1].any(axis=0))[0]
    xa=max(0,ca+int(xs[0])-int(2*d)); xb=min(W,ca+int(xs[-1])+int(2*d))
    xa=max(0,ca+int(xs[0])-int(0.8*d)); xb=min(W,ca+int(xs[-1])+int(0.8*d))
    cortado=bool(falta[max(0,a-2):min(H,b+3),xa:xb].any())
    if not j.get('corte_limpo',True) and b>=min(H,j.get('corte',H))-3: cortado=True      # rodapé mais baixo do que o quadro: sairia pela metade
    tudo=np.where((img[a:b+1,:]<150).any(axis=0))[0]
    if len(tudo) and (tudo[0]<=3 or tudo[-1]>=W-4): cortado=True      # encosta na beira do quadro (número da página cortado)
    if cortado or sempre:
        img=img.copy(); img[max(0,a-3):,:]=255
        return img,'tirado'
    return img,'inteiro'

def limpar_bordas(img):
    """manchas encostadas na beira do quadro (sombra da beira da folha, resto de corte) saem"""
    H,W=img.shape
    n,lab,st,_=cv2.connectedComponentsWithStats((img<130).astype(np.uint8),8)
    out=img
    for q in range(1,n):
        x,y,w,h,a=[int(v) for v in st[q]]
        if not (x<=2 or x+w>=W-2 or y+h>=H-2 or y<=2): continue
        if x+w<=60 or x>=W-60 or y>=H-40 or y+h<=40:
            if out is img: out=img.copy()
            out[lab==q]=255
    return out

def completar(pg,forcar=False,debug=True):
    base=f'/tmp/nn/pag/p{pg:03d}'
    new=cv2.imread(base+'.png',0); falta=cv2.imread(base+'_m.png',0)>0; j=json.load(open(base+'.json'))
    arq=f'{ANT}p{pg:03d}.png'
    H,W=new.shape; x0=j['x0']; yz=j['yz']
    ca=int(x0-1.0*d); cb=int(x0+W_OUT+1.0*d)
    y_topo=int(yz+j['topo']*d); y_fim=int(yz+j['fim']*d)
    ult=yz+j['Yp'][-1]+4*d                      # pé da última pauta que a foto mostra inteira
    # primeira linha (de baixo para cima) em que a foto cobre toda a largura do bloco
    lin_falta=falta[:,ca:cb].any(axis=1)
    ys=np.where(~lin_falta[:y_fim])[0]
    cobre=int(ys[-1]) if len(ys) else 0
    info=dict(pg=pg,cobre=(cobre-yz)/d,fim=j['fim'],feito=False)
    cls=PAGS.get(str(pg),{}).get('cls','?')
    musica=pg in MUSICA
    info.update(cls=cls,musica=musica)
    if not musica or not os.path.exists(arq):
        out,rod=limpar_rodape(new,falta,j); info['rodape']=rod
        return out,info
    old=cv2.imread(arq,0)
    valido=~cv2.dilate(falta.astype(np.uint8),np.ones((31,31),np.uint8)).astype(bool)
    r=registrar(old,new,valido)
    if r is None or r[1]<18: info['erro']='sem registro (%s pontos)'%(None if r is None else r[1]); return new,info
    Hm,n,S,D=r
    # ajuste fino com os pontos da metade de baixo (mais perto da emenda)
    baixo=D[:,1]>=max(y_topo,cobre-70*d)
    if baixo.sum()>=14:
        H2,mk=cv2.findHomography(S[baixo],D[baixo],cv2.RANSAC,3.0)
        if H2 is not None and mk.sum()>=12: Hm=H2; n=int(mk.sum())
    ow=cv2.warpPerspective(old,Hm,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=255)
    oc=cv2.warpPerspective(np.full(old.shape,255,np.uint8),Hm,(W,H),flags=cv2.INTER_NEAREST,borderValue=0)>0
    # deslocamento fino numa faixa logo acima da emenda
    a=max(0,cobre-int(16*d)); b=cobre-int(0.5*d)
    T=(255-new[a:b,ca:cb]).astype(np.float32); mrg=14
    I=(255-ow[max(0,a-mrg):b+mrg,ca-mrg:cb+mrg]).astype(np.float32)
    T=cv2.GaussianBlur(T,(0,0),1.5); I=cv2.GaussianBlur(I,(0,0),1.5)
    dx=dy=0; cc=0.0
    if T.std()>3 and I.std()>3 and I.shape[0]>T.shape[0] and I.shape[1]>T.shape[1]:
        res=cv2.matchTemplate(I,T,cv2.TM_CCOEFF_NORMED)
        _,cc,_,loc=cv2.minMaxLoc(res)
        dx=loc[0]-mrg; dy=loc[1]-(a-max(0,a-mrg))
        if cc<0.25 or abs(dx)>=mrg or abs(dy)>=mrg: dx=dy=0
    if dx or dy:
        A=np.float32([[1,0,-dx],[0,1,-dy]])
        ow=cv2.warpAffine(ow,A,(W,H),flags=cv2.INTER_CUBIC,borderValue=255)
        oc=cv2.warpAffine(oc.astype(np.uint8),A,(W,H),flags=cv2.INTER_NEAREST,borderValue=0)>0
    # emenda: de preferência numa linha em branco (nas duas imagens) acima do corte
    s=cobre-int(0.4*d)
    tn=(new[:,ca:cb]<150).sum(axis=1); to=(ow[:,ca:cb]<150).sum(axis=1)
    achou=None
    # (as barras verticais do sistema e as bordas das caixas de texto atravessam: tolera alguns pixels)
    if musica:
        # página antiga borrada: aproveita tudo o que a foto nova mostra; senão, emenda na linha com menos tinta
        # logo acima do corte (a pauta cortada vem inteira da página antiga)
        if cls!='ruim':
            ja=max(y_topo,s-int(6.5*d)); custo=cv2.blur((tn[ja:s+1]+0.5*to[ja:s+1]).astype(np.float32).reshape(-1,1),(1,5)).ravel()
            achou=ja+int(np.argmin(custo))
    else:
        for y in range(s,max(y_topo,s-int(15*d)),-1):
            if tn[y-1:y+2].max()<=18 and to[y-1:y+2].max()<=44: achou=y; break
    em_branco=achou is not None
    if achou is not None: s=achou
    if not em_branco and not musica:
        info['erro']='sem linha em branco para emendar'; return new,info
    out=new.copy()
    usa=oc[s:,:]
    velho=np.where(usa,ow[s:,:],255).astype(np.uint8)
    # manchas cheias (dedo, sombra) que vieram com a página antiga
    nn,lb,st,_=cv2.connectedComponentsWithStats((velho<110).astype(np.uint8),8)
    for q in range(1,nn):
        x,y,w,h,a=st[q]
        if w>3.0*d and h>3.0*d and a>0.45*w*h: velho[lb==q]=255
    velho[:, :max(0,int(x0-1.6*d))]=255; velho[:, int(x0+W_OUT+0.7*d):]=255
    out[s:,:]=np.where(usa,velho,out[s:,:])
    # limpeza igual à da página nova
    yf=int(round(yz+j['fim']*d+0.5*d))
    if yf<H: out[yf:,:]=255
    if j.get('lomb_dir'): out[:,int(x0+W_OUT+2.2*d):]=255
    else: out[:,:max(0,int(x0-2.2*d))]=255
    rod='antigo'
    if cls=='ruim' or pg==572: out,rod=limpar_rodape(out,falta,j,sempre=True)      # rodapé borrado da página antiga some
    info['rodape']=rod
    info.update(feito=True,pontos=n,dx=int(dx),dy=int(dy),cc=round(float(cc),2),emenda=(s-yz)/d,em_branco=em_branco)
    if debug:
        vis=cv2.cvtColor(out,cv2.COLOR_GRAY2BGR); cv2.line(vis,(0,s),(W,s),(0,0,255),2)
        cv2.imwrite(f'/tmp/nn/dbg/comp{pg:03d}.jpg',vis[max(0,s-int(40*d)):],[cv2.IMWRITE_JPEG_QUALITY,82])
    return out,info
if __name__=='__main__':
    import glob
    pgs=[int(a) for a in sys.argv[1:]] or [int(os.path.basename(a)[1:4]) for a in sorted(glob.glob('/tmp/nn/pag/p???.png'))]
    res=[]
    for pg in pgs:
        out,info=completar(pg)
        out=limpar_bordas(out)
        cv2.imwrite(f'/tmp/nn/pagf/p{pg:03d}.png',out); res.append(info)
        if info.get('feito') or info.get('erro') or info.get('musica'): print(info,flush=True)
    json.dump(res,open('/tmp/nn/completar.json','w'))
    print('completadas:',sum(1 for r in res if r['feito']),'de',len(res))
