"""Cifras escritas à mão (ou impressas em cor): acha cada uma na foto e monta uma folha numerada para leitura.
modos: cor (caneta colorida), escuro (caneta preta/lápis por cima de letra impressa), tudo (folha toda manuscrita)"""
import sys,json,os,subprocess
import cv2,numpy as np
def _hsv(cor):
    hsv=cv2.cvtColor(cor,cv2.COLOR_BGR2HSV); return hsv[...,0].astype(np.int32),hsv[...,1].astype(np.int32),hsv[...,2].astype(np.int32)
def _finos(m,lim=7):
    dt=cv2.distanceTransform(m,cv2.DIST_L2,3)
    grosso=cv2.dilate((dt>lim).astype(np.uint8),np.ones((25,25),np.uint8))
    return (m&(1-grosso)).astype(np.uint8)
def picos_de_cor(cor,smin=85):
    h,s,v=_hsv(cor); m=_finos(((s>smin)&(v>60)&(v<245)).astype(np.uint8))
    hh=h[m>0]
    if len(hh)<150: return []
    hist=np.bincount(hh.ravel(),minlength=180).astype(np.float32); hist=np.convolve(np.r_[hist[-8:],hist,hist[:8]],np.ones(17),'same')[8:-8]
    picos=[]; hc=hist.copy()
    for _ in range(3):
        p=int(np.argmax(hc))
        if hc[p]<0.12*hist.max() or hc[p]<150: break
        picos.append((p,int(hc[p])))
        for d in range(-22,23): hc[(p+d)%180]=0
    return picos
def tinta_colorida(cor,matiz=None,smin=85,larga=False):
    """máscara da tinta colorida de traço fino; matiz: None = cor dominante, número = essa cor, 'todas' = qualquer cor"""
    h,s,v=_hsv(cor)
    if matiz is None:
        p=picos_de_cor(cor,smin); matiz=p[0][0] if p else 'todas'
    if larga: base=(s>max(40,smin-37))&(v>45)&(v<250)
    else: base=(s>smin)&(v>60)&(v<245)
    if matiz!='todas':
        dh=np.abs(h-int(matiz)); dh=np.minimum(dh,180-dh); base&=(dh<=(24 if larga else 15))
    return _finos(base.astype(np.uint8),lim=9 if larga else 7)
def tinta_larga(cor,matiz=None,smin=85): return tinta_colorida(cor,matiz,smin,larga=True)
def aplainar(g):
    k=max(31,int(min(g.shape)*0.05))|1
    fundo=cv2.GaussianBlur(cv2.morphologyEx(g,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))),(0,0),k/3)
    return np.clip(g.astype(np.float32)/np.maximum(fundo.astype(np.float32),1)*255,0,255).astype(np.uint8)
def palavras_impressas(g):
    """caixas das palavras impressas (lidas com confiança pelo tesseract)"""
    s=min(1.0,2400/max(g.shape)); small=cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_AREA) if s<1 else g
    fn='/tmp/cif/dbg/mao_%d.png'%os.getpid(); cv2.imwrite(fn,small)
    r=subprocess.run(['tesseract',fn,'-','-l','por','--psm','6','tsv'],capture_output=True,text=True).stdout; os.remove(fn)
    out=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        t=c[11].strip()
        if float(c[10])>=60 and sum(ch.isalpha() for ch in t)>=3 and any(ch.islower() for ch in t):
            out.append((int(int(c[6])/s),int(int(c[7])/s),int((int(c[6])+int(c[8]))/s),int((int(c[7])+int(c[9]))/s)))
    return out
def tinta_escura(cor,modo='escuro'):
    g=aplainar(cv2.cvtColor(cor,cv2.COLOR_BGR2GRAY))
    m=(g<150).astype(np.uint8)
    m=_finos(m,lim=max(6,int(g.shape[1]*0.004)))
    if modo=='escuro':
        for x0,y0,x1,y1 in palavras_impressas(g):
            m[max(0,y0-3):y1+3,max(0,x0-3):x1+3]=0
    return m
def tokens(cor,modo='cor',matiz=None,smin=85,junta=3.4):
    H,W=cor.shape[:2]
    m=tinta_colorida(cor,matiz,smin) if modo=='cor' else tinta_escura(cor,modo)
    k=max(3,int(W*0.004))|1
    junto=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_RECT,(int(k*junta)|1,k)))
    n,lab,st,_=cv2.connectedComponentsWithStats(junto,8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=[int(v) for v in st[i]]
        tinta=int(m[y:y+h,x:x+w].sum())
        if h<W*0.011 or h>W*0.09 or w<W*0.007 or w>W*0.34 or tinta<W*0.03 or w>8*h: continue
        out.append(dict(x0=x,y0=y,x1=x+w,y1=y+h,tinta=tinta))
    # ordem de leitura: por linhas
    out.sort(key=lambda t:(t['y0']+t['y1'])/2)
    linhas=[]
    for t in out:
        cy=(t['y0']+t['y1'])/2
        if linhas and abs(cy-linhas[-1]['cy'])<0.6*max(t['y1']-t['y0'],linhas[-1]['h']):
            L=linhas[-1]; L['ts'].append(t); L['cy']=(L['cy']*(len(L['ts'])-1)+cy)/len(L['ts']); L['h']=max(L['h'],t['y1']-t['y0'])
        else: linhas.append(dict(cy=cy,h=t['y1']-t['y0'],ts=[t]))
    out=[t for L in linhas for t in sorted(L['ts'],key=lambda t:t['x0'])]
    return out,m
def folha_numerada(cor,toks,alt=44,cols=11):
    cel_w=166; cel_h=alt+14; rows=max(1,(len(toks)+cols-1)//cols)
    tela=np.full((rows*cel_h+4,cols*cel_w,3),255,np.uint8)
    for i,t in enumerate(toks):
        pad=6; c=cor[max(0,t['y0']-pad):t['y1']+pad,max(0,t['x0']-pad):t['x1']+pad]
        s=min(alt/c.shape[0],(cel_w-40)/c.shape[1]); c=cv2.resize(c,None,fx=s,fy=s,interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
        r,cc=divmod(i,cols); y=r*cel_h+7; x=cc*cel_w+36
        tela[y:y+c.shape[0],x:x+c.shape[1]]=c
        cv2.putText(tela,str(i+1),(cc*cel_w+2,r*cel_h+34),cv2.FONT_HERSHEY_SIMPLEX,0.5,(160,0,0),1)
        cv2.rectangle(tela,(cc*cel_w,r*cel_h),(cc*cel_w+cel_w-1,r*cel_h+cel_h-1),(210,210,210),1)
    return tela
def cor_do_papel(cor,t):
    y0,y1=max(0,t['y0']-6),min(cor.shape[0],t['y1']+6); x0,x1=max(0,t['x0']-6),min(cor.shape[1],t['x1']+6)
    reg=cor[y0:y1,x0:x1].reshape(-1,3); sm=reg.sum(axis=1); claro=reg[sm>=np.percentile(sm,65)]
    return '%02x%02x%02x'%tuple(int(v) for v in np.median(claro,axis=0)[::-1])
def preparar(f,modo='cor',matiz=None,smin=85,junta=3.4,nome=None):
    cor=cv2.imread(f); toks,m=tokens(cor,modo,matiz,smin,junta)
    for t in toks: t['bg']=cor_do_papel(cor,t)
    nome=nome or os.path.basename(f)[:-4]; os.makedirs('/tmp/cif/mao',exist_ok=True)
    json.dump(dict(img=f,w=cor.shape[1],h=cor.shape[0],modo=modo,matiz=matiz,smin=smin,toks=toks),open(f'/tmp/cif/mao/{nome}.json','w'))
    tela=folha_numerada(cor,toks); cv2.imwrite(f'/tmp/cif/mao/{nome}.jpg',tela,[cv2.IMWRITE_JPEG_QUALITY,70])
    return nome,cor.shape[:2],len(toks),tela.shape[:2]
if __name__=='__main__':
    # uso: mao.py <imagem> [modo] [matiz|todas] [smin] [junta]
    f=sys.argv[1]; modo=sys.argv[2] if len(sys.argv)>2 else 'cor'
    mz=sys.argv[3] if len(sys.argv)>3 else None
    mz=None if mz in (None,'auto') else (mz if mz=='todas' else int(mz))
    smin=int(sys.argv[4]) if len(sys.argv)>4 else 85; junta=float(sys.argv[5]) if len(sys.argv)>5 else 3.4
    if modo=='cor': print('   cores (matiz, força):',picos_de_cor(cv2.imread(f),smin))
    print(*preparar(f,modo,mz,smin,junta))
