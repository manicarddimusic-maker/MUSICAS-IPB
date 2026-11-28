"""Leitura das cifras por comparação com a própria fonte do hinário (Arial Narrow Bold):
cada palavra candidata é comparada com o desenho de todos os acordes possíveis; vence o mais parecido."""
import sys,re,json,os
sys.path.insert(0,'/tmp/cif')
import numpy as np,cv2
from PIL import Image,ImageDraw,ImageFont
FONTE='/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf'
CAP=32; TOPO=10; DESC=12; ALT=TOPO+CAP+DESC; BASE=TOPO+CAP
def _fonte():
    # tamanho em que a altura do "E" é exatamente CAP
    lo,hi=30.0,60.0
    for _ in range(20):
        m=(lo+hi)/2; f=ImageFont.truetype(FONTE,m); b=f.getbbox('E',anchor='ls')
        if -b[1]<CAP: lo=m
        else: hi=m
    return ImageFont.truetype(FONTE,(lo+hi)/2)
F=_fonte()
def desenhar(s):
    """desenho da palavra na fonte, em preto e branco (1 = tinta), recortado na largura da tinta"""
    w=int(F.getlength(s))+16
    im=Image.new('L',(w,ALT),0); ImageDraw.Draw(im).text((8,BASE),s,font=F,fill=255,anchor='ls')
    a=(np.array(im)>110).astype(np.uint8)
    cols=np.where(a.max(axis=0)>0)[0]
    return a[:,cols[0]:cols[-1]+1]
RAIZES=['C','C#','Db','D','D#','Eb','E','F','F#','Gb','G','G#','Ab','A','A#','Bb','B']
SUF_BASE=['','m','7','m7','7M','6','m6','9','m9','4','sus','sus4','sus9','sus2','sus4/9','7sus4','dim','º','m5dim','5dim','7/9','7(9)','m7/9','7M/9','6/9','7/4','add9','5+','7+','+','m7(b5)','11','13','7/13','9/11','m9/11','7/9/11','m6/9','2','5','7/11','m7/11','7(b9)','7(#9)','7/5+','m7M','7(13)','9/13','7/6','7(b13)','4/9','m4','m7/4','7dim','dim7','º7','7M(9)','(9)','m(9)','6(9)','m7(9)','7(11)','sus7','7/b9']
SIGMA=0.9
def fonte_com_cap(caminho):
    lo,hi=30.0,70.0
    for _ in range(22):
        m=(lo+hi)/2; f=ImageFont.truetype(caminho,m); bb=f.getbbox('E',anchor='ls')
        if -bb[1]<CAP: lo=m
        else: hi=m
    return ImageFont.truetype(caminho,(lo+hi)/2)
def desenhar_com(f,s):
    w=int(f.getlength(s))+40
    im=Image.new('L',(w,ALT),0); ImageDraw.Draw(im).text((16,BASE),s,font=f,fill=255,anchor='ls')
    a=(np.array(im)>110).astype(np.uint8)
    cols=np.where(a.max(axis=0)>0)[0]
    return a[:,cols[0]:cols[-1]+1]
class Vocab:
    def __init__(self,sufixos=None,fonte=None):
        suf=list(dict.fromkeys(SUF_BASE+list(sufixos or [])))
        self.f=fonte_com_cap(fonte) if fonte else F
        desenhar=lambda t:desenhar_com(self.f,t)
        self._des=desenhar
        self.txt=[];self.img=[];self.larg=[]
        vistos=set()
        for r in RAIZES:
            for s in suf:
                for b in [None]+RAIZES:
                    if b==r: continue
                    t=r+s+('/'+b if b else '')
                    if t in vistos: continue
                    vistos.add(t); a=desenhar(t)
                    self.txt.append(t); self.larg.append(a.shape[1])
                    # guarda já borrado (0..255): na hora de comparar só é preciso ajustar a largura
                    self.img.append(np.clip(cv2.GaussianBlur(a.astype(np.float32),(0,0),SIGMA)*255,0,255).astype(np.uint8))
        self.larg=np.array(self.larg,np.float32)
        self.pos={t:i for i,t in enumerate(self.txt)}
        tem_baixo=np.array([bool(re.search(r'/[A-G][#b]?$',t)) for t in self.txt])
        self.sem_baixo=~tem_baixo
        self.so_raiz=np.array([t in RAIZES for t in self.txt])
    def largura(self,txt):
        i=self.pos.get(txt)
        return float(self.larg[i]) if i is not None else float(self._des(txt).shape[1])
    def candidatos(self,W,hx,folga=0.075,filtro=None):
        L=self.larg*hx
        ok=np.abs(L-W)<=folga*W+3
        if filtro is not None: ok&=filtro
        return np.where(ok)[0]
def normalizar(b,lab,t,lim,cap=None,dy=0.0):
    """recorta a palavra em preto e branco, com a altura das maiúsculas = CAP e a linha de base em BASE"""
    cap=cap or t['cap']; k=CAP/cap
    y0=int(round(t['base']+dy-(TOPO+CAP)/k)); y1=int(round(t['base']+dy+DESC/k)); x0,x1=t['x0'],t['x1']
    H,W=b.shape; ya,yb=max(0,y0),min(H,y1)
    g=np.zeros((y1-y0,x1-x0),np.float32)
    ids=np.array([c['id'] for c in t['cs']])
    m=np.isin(lab[ya:yb,x0:x1],ids)
    g[ya-y0:yb-y0,:]=m.astype(np.float32)
    g=cv2.resize(g,(max(2,int(round((x1-x0)*k))),ALT),interpolation=cv2.INTER_AREA if k<1 else cv2.INTER_LINEAR)
    return cv2.GaussianBlur(g,(0,0),SIGMA)
def angulo_local(bw,x,y,cap,cache=None):
    """inclinação (graus) do texto/pauta em volta de um ponto: a que deixa as linhas mais "em pé" no perfil"""
    chave=(int(x//(5*cap)),int(y//(4*cap)))
    if cache is not None and chave in cache: return cache[chave]
    H,W=bw.shape
    x0=max(0,int(x-7*cap)); x1=min(W,int(x+7*cap)); y0=max(0,int(y-2.5*cap)); y1=min(H,int(y+6.5*cap))
    j=bw[y0:y1,x0:x1].astype(np.float32)
    if j.size==0 or j.sum()<20: 
        if cache is not None: cache[chave]=0.0
        return 0.0
    h,w=j.shape
    def nota(a):
        M=np.float32([[1,0,0],[-np.tan(np.radians(a)),1,np.tan(np.radians(a))*w/2]])
        s=cv2.warpAffine(j,M,(w,h),flags=cv2.INTER_LINEAR)
        p=s.sum(axis=1); return float((p*p).sum())
    best=max(((nota(a),a) for a in (-9,-7.5,-6,-4.5,-3,-1.5,0,1.5,3,4.5,6,7.5,9)))
    a0=best[1]; best=max(((nota(a),a) for a in (a0-0.75,a0,a0+0.75)))
    # só vale se for bem melhor que "sem inclinação"
    ang=best[1] if best[0]>1.04*nota(0.0) else 0.0
    if cache is not None: cache[chave]=ang
    return ang
def preparar(lab,t,ang=0.0):
    """máscara da palavra (já desentortada), com a linha de base e a altura das maiúsculas"""
    m_=4
    x0,y0=max(0,t['x0']-m_),max(0,t['y0']-m_); x1,y1=min(lab.shape[1],t['x1']+m_),min(lab.shape[0],t['y1']+m_)
    ids=np.array([c['id'] for c in t['cs']])
    m=np.isin(lab[y0:y1,x0:x1],ids).astype(np.uint8)
    if abs(ang)<0.6:
        return dict(m=m[:,t['x0']-x0:t['x1']-x0].astype(np.float32),base=t['base']-y0,cap=t['cap'])
    h,w=m.shape; pad=int(0.12*w)+6
    m=cv2.copyMakeBorder(m,pad,pad,pad,pad,cv2.BORDER_CONSTANT,value=0)
    h,w=m.shape
    M=cv2.getRotationMatrix2D((w/2,h/2),ang,1.0)       # ângulo positivo = texto descendo para a direita -> gira ao contrário
    r=cv2.warpAffine(m.astype(np.float32),M,(w,h),flags=cv2.INTER_LINEAR)
    bin_=(r>0.5).astype(np.uint8)
    cols=np.where(bin_.max(axis=0)>0)[0]; rows=np.where(bin_.max(axis=1)>0)[0]
    if len(cols)<2 or len(rows)<2: return dict(m=m.astype(np.float32),base=t['base']-y0+pad,cap=t['cap'])
    n,lb,st,_=cv2.connectedComponentsWithStats(bin_,8)
    altos=[(st[i][0],st[i][1],st[i][3]) for i in range(1,n) if st[i][3]>=0.8*t['cap']]
    if altos:
        xa,ya,ha=min(altos); base=ya+ha; cap=ha
        pes=sorted(a[1]+a[2] for a in altos)
        if len(pes)>2: base=pes[len(pes)//2]
        if ya+ha<base-0.2*t['cap']: base=ya+ha
    else: base=rows[-1]+1; cap=t['cap']
    return dict(m=r[:,cols[0]:cols[-1]+1],base=int(base),cap=int(cap))
def normalizar_m(P,cap=None,dy=0.0):
    m=P['m']; cap0=cap or P['cap']; k=CAP/cap0
    y0=int(round(P['base']+dy-(TOPO+CAP)/k)); y1=int(round(P['base']+dy+DESC/k))
    g=np.zeros((max(2,y1-y0),m.shape[1]),np.float32); ya=max(0,y0); yb=min(m.shape[0],y1)
    if yb>ya: g[ya-y0:yb-y0,:]=m[ya:yb,:]
    g=cv2.resize(g,(max(2,int(round(m.shape[1]*k))),ALT),interpolation=cv2.INTER_AREA if k<1 else cv2.INTER_LINEAR)
    return cv2.GaussianBlur(g,(0,0),SIGMA)
def _ncc_lote(T,M):
    t=T-T.mean(); m=M-M.mean(axis=(1,2),keepdims=True)
    num=(m*t).sum(axis=(1,2)); den=np.sqrt((m*m).sum(axis=(1,2))*(t*t).sum())+1e-6
    return num/den
def _moldes(V,ids,W):
    return np.stack([cv2.resize(V.img[i],(W,ALT),interpolation=cv2.INTER_LINEAR) for i in ids]).astype(np.float32)
def eh_barra(c,lab,cap):
    """o glifo é uma barra "/"? (traço fino, reto e inclinado)"""
    h,w=c['h'],c['w']
    if not (0.9*cap<=h<=1.55*cap and 0.14*cap<=w<=0.6*cap): return False
    m=(lab[c['y']:c['y']+h,c['x']:c['x']+w]==c['id'])
    if m.mean()>0.62: return False
    ys,xs=np.nonzero(m)
    if len(ys)<8: return False
    a,b0=np.polyfit(ys,xs,1)
    res=xs-(a*ys+b0)
    return -0.8<a<-0.1 and res.std()<0.11*cap and np.abs(res).max()<0.24*cap
def partir_na_barra(t,lab):
    """se a palavra tem uma barra no meio, devolve (parte da esquerda, parte da direita)"""
    cs=sorted(t['cs'],key=lambda c:c['x'])
    for k in range(len(cs)-2,0,-1):
        if eh_barra(cs[k],lab,t['cap']):
            E,D=cs[:k],cs[k+1:]
            if not E or not D: return None
            def sub(g):
                return dict(x0=min(c['x'] for c in g),x1=max(c['x']+c['w'] for c in g),y0=min(c['y'] for c in g),y1=max(c['y']+c['h'] for c in g),base=t['base'],cap=t['cap'],cs=g)
            return sub(E),sub(D)
    return None
def casar(V,b,lab,t,lim,hx,n_fino=10,filtro=None,ang=0.0):
    """devolve [(nota, texto)] dos acordes mais parecidos com a palavra (melhor primeiro)"""
    P=preparar(lab,t,ang)
    T=normalizar_m(P); W=T.shape[1]
    idx=V.candidatos(W,hx,filtro=filtro)
    if len(idx)==0: return []
    s=_ncc_lote(T,_moldes(V,idx,W))
    top=idx[np.argsort(-s)[:n_fino]]
    melhor={}
    for esc in (0.94,1.0,1.06):
        for dy in (-1.5,0.0,1.5):
            T2=normalizar_m(P,cap=P['cap']*esc,dy=dy*P['cap']/CAP)
            W2=T2.shape[1]
            s2=_ncc_lote(T2,_moldes(V,top,W2))
            for i,v in zip(top,s2):
                rz=V.larg[i]*hx/W2; v=float(v)-0.5*max(0.0,abs(np.log(rz))-0.03)
                if v>melhor.get(i,-1): melhor[i]=v
    return sorted(((v,V.txt[i]) for i,v in melhor.items()),reverse=True)
def calibrar_hx(V,toks,leituras,padrao=0.84,b=None,lab=None,lim=None):
    """quanto a letra do livro é mais estreita que a fonte: mede nas palavras que o tesseract leu com certeza;
    se forem poucas, experimenta alguns valores e fica com o que dá as melhores comparações"""
    from acordes import eh_acorde
    rs=[]
    for t,(tx,cf) in zip(toks,leituras):
        if cf>=70 and len(tx)>=2 and eh_acorde(tx):
            rs.append((t['x1']-t['x0'])*CAP/t['cap']/V.largura(tx))
    rs=[r for r in rs if 0.6<r<1.15]
    if len(rs)>=4: return float(np.median(rs)),len(rs)
    if b is None: return padrao,len(rs)
    am=sorted([t for t in toks if len(t['cs'])>=3],key=lambda t:-(t['x1']-t['x0']))[:14]
    if len(am)<4: return padrao,len(rs)
    melhor=(0,padrao)
    for hx in (0.78,0.82,0.86,0.90,0.94):
        notas=[]
        for t in am:
            r=casar(V,b,lab,t,lim,hx,n_fino=3)
            notas.append(r[0][0] if r else 0.0)
        notas.sort(reverse=True); m=float(np.mean(notas[:max(4,len(notas)//2)]))
        if m>melhor[0]: melhor=(m,hx)
    return melhor[1],-1
if __name__=='__main__':
    import time
    from nccomum import *
    from ncocr import limiar_da_pagina
    pg=int(sys.argv[1]) if len(sys.argv)>1 else 144
    t0=time.time(); V=Vocab(); print('vocabulário',len(V.txt),'em %.1fs'%(time.time()-t0))
    b=base_da_pagina(pg); d=espaco_pauta(b); lim=limiar_da_pagina(b,d)
    toks,lab,cap=candidatos(b,d,lim)
    sel=[t for t in toks if t['cap']>=0.9*cap and t['sw']>=0.15*t['cap']]
    sel.sort(key=lambda t:(round(t['base']/(4*cap)),t['x0']))
    t0=time.time()
    tes=lote([recorte(b,lab,t) for t in sel],7,'g')
    hx,n=calibrar_hx(V,sel,tes); print('limiar',lim,'cap %.1f'%cap,'candidatos',len(sel),'hx %.3f (%d)'%(hx,n))
    for t,(tx,cf) in zip(sel,tes):
        r=casar(V,b,lab,t,lim,hx)
        a=r[0] if r else (0,''); c=r[1] if len(r)>1 else (0,'')
        print(f"{t['x0']:5d} {t['base']:5d} cap{t['cap']:3d} sw{t['sw']/t['cap']:.2f} | {a[1]:10s} {a[0]:.3f} | {c[1]:10s} {c[0]:.3f} | tess {tx:10s} {cf:3.0f}")
    print('%.1fs'%(time.time()-t0))
