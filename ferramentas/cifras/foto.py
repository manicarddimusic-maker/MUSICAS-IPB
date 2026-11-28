"""Leitura das cifras impressas em fotos de folhas (qualquer aba): escolhe a fonte mais parecida e compara palavra por palavra."""
import sys,json,os,re,time,subprocess
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nc')
import cv2,numpy as np
from ncglifo import Vocab,casar,calibrar_hx,partir_na_barra,angulo_local
from ncpauta import linhas_finas,espaco,faixas
from nccomum import recorte,lote
from acordes import eh_acorde
L='/usr/share/fonts/truetype/liberation/'
#        arquivo                          traço/altura  folga entre letras  família no app  peso normal?
FONTES={'nb':(L+'LiberationSansNarrow-Bold.ttf',0.20,0.21,'s',0),
        'bi':(L+'LiberationSans-BoldItalic.ttf',0.19,0.21,'a',0),
        'sb':(L+'LiberationSans-Bold.ttf',0.19,0.21,'a',0),
        'sr':(L+'LiberationSans-Regular.ttf',0.115,0.22,'a',1),
        'si':(L+'LiberationSans-Italic.ttf',0.115,0.22,'a',1),
        'tr':(L+'LiberationSerif-Regular.ttf',0.10,0.20,'t',1),
        'tb':(L+'LiberationSerif-Bold.ttf',0.17,0.20,'t',0),
        'mr':(L+'LiberationMono-Regular.ttf',0.09,0.36,'m',1),
        'mb':(L+'LiberationMono-Bold.ttf',0.15,0.36,'m',0),
        'dm':('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',0.105,0.36,'m',1),
        'db':('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',0.17,0.36,'m',0)}
_V={}
def vocab(k):
    if k not in _V: _V[k]=Vocab(fonte=FONTES[k][0])
    return _V[k]
def aplainar(g):
    k=max(31,int(min(g.shape)*0.05))|1
    fundo=cv2.morphologyEx(g,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    fundo=cv2.GaussianBlur(fundo,(0,0),k/3)
    n=np.clip(g.astype(np.float32)/np.maximum(fundo.astype(np.float32),1)*255,0,255).astype(np.uint8)
    # estica o contraste: o tom mais escuro do texto vira preto
    lo=float(np.percentile(n,0.6)); 
    if lo<200: n=np.clip((n.astype(np.float32)-lo)/(250-lo)*255,0,255).astype(np.uint8)
    return n
def componentes(e,cap,lim):
    bw=(e<lim).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(bw,8)
    dt=cv2.distanceTransform(bw,cv2.DIST_L2,3)
    comps=[]
    for i in range(1,n):
        x,y,w,h,a=[int(v) for v in st[i]]
        if h<0.2*cap or h>1.8*cap or w>5.5*cap or a<0.02*cap*cap: continue
        if w>2.2*cap and h<0.5*cap: continue
        vals=dt[y:y+h,x:x+w][lab[y:y+h,x:x+w]==i]
        comps.append(dict(x=x,y=y,w=w,h=h,a=a,sw=2*float(np.percentile(vals,90)),id=i))
    return comps,lab
def agrupar(comps,cap,folga):
    comps=sorted(comps,key=lambda c:c['x']); toks=[]
    for c in comps:
        best=None
        for t in toks:
            gap=c['x']-t['x1']
            if gap>folga*cap or c['x']<t['x0']-2: continue
            ov=min(t['y1'],c['y']+c['h'])-max(t['y0'],c['y'])
            if ov>0.4*min(c['h'],t['y1']-t['y0']) or (c['h']<0.45*cap and t['y0']-0.15*cap<=c['y'] and c['y']+c['h']<=t['y1']+0.15*cap):
                if best is None or gap<c['x']-best['x1']: best=t
        if best is None: toks.append(dict(x0=c['x'],x1=c['x']+c['w'],y0=c['y'],y1=c['y']+c['h'],cs=[c]))
        else:
            best['x1']=max(best['x1'],c['x']+c['w']); best['y0']=min(best['y0'],c['y']); best['y1']=max(best['y1'],c['y']+c['h']); best['cs'].append(c)
    return toks
def candidatos(e,cap,lim,alvo,folga):
    comps,lab=componentes(e,cap,lim)
    todos=agrupar(comps,cap,folga); out=[]
    for t in todos:
        h=t['y1']-t['y0']; w=t['x1']-t['x0']
        altos=[c for c in t['cs'] if c['h']>=0.8*cap]
        t['pal']=(w>=0.3*cap and h>=0.4*cap)
        if not altos or h>1.75*cap or w<0.25*cap or w>7.5*cap: continue
        prim=min(altos,key=lambda c:c['x'])
        if prim['x']>t['x0']+0.45*cap or not (0.84*cap<=prim['h']<=1.3*cap): continue
        sw=float(np.median([c['sw'] for c in altos]))
        if sw<0.5*alvo*cap or sw>2.1*alvo*cap: continue
        pes=sorted(c['y']+c['h'] for c in altos); base=pes[len(pes)//2] if len(pes)>2 else prim['y']+prim['h']
        if prim['y']+prim['h']<base-0.2*cap: base=prim['y']+prim['h']
        t.update(base=int(base),cap=int(prim['h']),sw=sw); out.append(t)
    return out,lab,[t for t in todos if t['pal']]
def limiar(e,cap,alvo,folga):
    melhor=None
    for lim in (60,85,110,135,160,185):
        toks,lab,_=candidatos(e,cap,lim,alvo,folga)
        fortes=[t for t in toks if t['cap']>=0.95*cap]
        if len(fortes)<5: continue
        r=sorted(t['sw']/t['cap'] for t in fortes); q=r[int(len(r)*0.7)]
        if melhor is None or abs(q-alvo)<abs(melhor[1]-alvo): melhor=(lim,q)
    return melhor[0] if melhor else 130
ALT_TEXTO=[]
def palavras_tess(b):
    """palavras que o tesseract lê como acorde: dão a altura das cifras e servem para escolher a fonte"""
    s=min(1.0,2400/max(b.shape)); small=cv2.resize(b,None,fx=s,fy=s,interpolation=cv2.INTER_AREA) if s<1 else b
    fn='/tmp/cif/dbg/foto_%d.png'%os.getpid(); cv2.imwrite(fn,small)
    r=subprocess.run(['tesseract',fn,'-','-l','por','--psm','6','tsv'],capture_output=True,text=True).stdout; os.remove(fn)
    out=[]; ALT_TEXTO.clear()
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        t=c[11].strip()
        if float(c[10])>=60 and len(t)>=3 and t[0].isupper() and not re.search(r'[gjpqyç,;()]',t): ALT_TEXTO.append(int(c[9])/s)
        if float(c[10])>=55 and len(t)>=2 and eh_acorde(t) and re.search(r'[0-9#mb/]',t) and not re.fullmatch(r'[A-G][a-z]',t.replace('m','')+'x' if False else 'zz'):
            out.append((int(c[6])/s,int(c[7])/s,int(c[8])/s,int(c[9])/s,t))
    return out
ORDEM_FIXA=None
GIROS={90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}
def bruto(caminho):
    """lê a foto como está; se não achar cifras, tenta deitada (90°, 270°) e de cabeça para baixo"""
    cor0=cv2.imread(caminho)
    melhor=None
    for giro in (0,90,270):
        cor=cor0 if giro==0 else cv2.rotate(cor0,GIROS[giro])
        r=bruto_img(cor,caminho); r['giro']=giro
        n=sum(1 for t in r['toks'] if t['c'][0][0]>=0.8)
        if melhor is None or n>melhor[0]: melhor=(n,r)
        if n>=4 or (giro==0 and r.get('partitura')): break
    return melhor[1]
def bruto_img(cor,caminho,escala=1):
    """escala=2: foto com letra pequena é ampliada antes de ler"""
    if escala==1:
        g0=cv2.cvtColor(cor,cv2.COLOR_BGR2GRAY); pt0=palavras_tess(aplainar(g0))
        if (len(pt0)<3 or float(np.median([p[3] for p in pt0]))<27) and max(g0.shape)<=3200:
            r=bruto_img(cv2.resize(cor,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC),caminho,2)
            for t in r['toks']:
                for k in ('x0','x1','y0','y1','base','cap'): t[k]=int(round(t[k]/2))
                t['sw']=round(t['sw']/2,2)
            r['w']//=2; r['h']//=2
            if r.get('cap'): r['cap']=round(r['cap']/2,1)
            r['ampliada']=1
            if r['toks'] or len(pt0)<3: return r
    g=cv2.cvtColor(cor,cv2.COLOR_BGR2GRAY)
    b=aplainar(g)
    out=dict(img=caminho,w=int(g.shape[1]),h=int(g.shape[0]),fonte=None,cap=None,toks=[])
    mf=linhas_finas(b); d=espaco(mf)
    if d is not None and len(faixas(mf,d))<3: d=None       # sem pautas de verdade: é folha de letra e cifra
    pt=palavras_tess(b)
    partitura = d is not None and len(pt)<8
    sem_tess=False
    if partitura: cap=1.7*d; ordem=['nb']
    else:
        sem_tess=len(pt)<3
        if sem_tess:
            if len(ALT_TEXTO)<6: return out
            cap=0.9*float(np.median(ALT_TEXTO))      # sem cifras lidas pelo tesseract: usa a altura da letra da música
        else:
            hs=sorted(p[3] for p in pt); cap=float(np.median(hs))
        ordem=ORDEM_FIXA or ['tr','mr','dm','sb','bi','sr','mb','tb','nb']
    out['cap']=round(cap,1); out['partitura']=int(partitura)
    # escolhe a fonte: a que melhor reproduz as palavras que o tesseract já leu como acorde
    melhor=None; _cls={}
    for k in ordem:
        arq,alvo,folga,_,_=FONTES[k]
        ch=(0.105 if alvo<0.13 else 0.185,folga)
        if ch not in _cls:
            lim=limiar(b,cap,ch[0],folga); _cls[ch]=(lim,)+tuple(candidatos(b,cap,lim,ch[0],folga))
        lim,toks,lab,todos=_cls[ch]
        if len(ordem)==1: melhor=(1.0,k,lim,toks,lab,todos,0.85 if k=='nb' else 1.0); break
        V=vocab(k)
        if not partitura and sem_tess:
            # escolhe a fonte pelas palavras que mais se parecem com algum acorde
            am2=sorted([t for t in toks if 0.82*cap<=t['cap']<=1.3*cap and 0.5*cap<=t['x1']-t['x0']<=5*cap and len(t['cs'])<=8],key=lambda t:-(t['x1']-t['x0']))[:40]
            notas=[]
            for t in am2:
                r=casar(V,b,lab,t,lim,1.0,n_fino=2); notas.append(r[0][0] if r else 0.0)
            notas.sort(reverse=True)
            if len(notas)<5: continue
            m=float(np.mean(notas[:8]))
            if melhor is None or m>melhor[0]: melhor=(m,k,lim,toks,lab,todos,1.0)
            continue
        am=[]
        for (x,y,w,h,txt) in pt[:40]:
            cand=[t for t in toks if abs(t['x0']-x)<0.6*cap and abs((t['y0']+t['y1'])/2-(y+h/2))<0.6*cap]
            if cand: am.append((cand[0],txt))
        if len(am)<3: continue
        rs=[(t['x1']-t['x0'])*32/t['cap']/V.largura(txt) for t,txt in am]; rs=[r for r in rs if 0.6<r<1.3]
        hx=float(np.median(rs)) if len(rs)>=3 else 1.0
        notas=[]; bw=(b<lim).astype(np.uint8); cache={}
        for t,txt in am[:14]:
            r=casar(V,b,lab,t,lim,hx,n_fino=4,ang=angulo_local(bw,(t['x0']+t['x1'])/2,t['base'],cap,cache))
            notas.append(next((v for v,x in r if x==txt),0.0) if r else 0.0)
        m=float(np.mean(sorted(notas,reverse=True)[:max(3,len(notas)*2//3)]))
        if melhor is None or m>melhor[0]: melhor=(m,k,lim,toks,lab,todos,hx)
    if melhor is None: return out
    m,k,lim,toks,lab,todos,hx=melhor
    V=vocab(k); arq,alvo,folga,fam,normal=FONTES[k]
    sel=[t for t in toks if 0.82*cap<=t['cap']<=1.3*cap]
    out.update(fonte=k,nota_fonte=round(m,3),lim=lim,hx=round(hx,3))
    if not sel: return out
    tes=lote([recorte(b,lab,t) for t in sel],7,'foto')
    if partitura:
        hx,_=calibrar_hx(V,sel,tes,b=b,lab=lab,lim=lim); out['hx']=round(hx,3)
    bw=(b<lim).astype(np.uint8); cache={}
    for t,(tx,cf) in zip(sel,tes):
        a_=angulo_local(bw,(t['x0']+t['x1'])/2,t['base'],cap,cache)
        r=casar(V,b,lab,t,lim,hx,ang=a_)
        if not r: continue
        y0,y1=max(0,t['y0']-4),min(g.shape[0],t['y1']+4); x0,x1=max(0,t['x0']-4),min(g.shape[1],t['x1']+4)
        reg=cor[y0:y1,x0:x1].reshape(-1,3); sm=reg.sum(axis=1); claro=reg[sm>=np.percentile(sm,65)]
        bg=[int(v) for v in np.median(claro,axis=0)[::-1]] if len(claro) else [255,255,255]
        # quantas outras palavras há na mesma linha de texto (letra da música tem muitas)
        viz=sum(1 for o in todos if o is not t and abs((o['y1'])-t['base'])<0.3*cap and abs(o['x0']-t['x0'])<14*cap)
        e=dict(x0=int(t['x0']),x1=int(t['x1']),y0=int(t['y0']),y1=int(t['y1']),base=int(t['base']),cap=int(t['cap']),sw=round(float(t['sw']),2),n=len(t['cs']),
               c=[[round(float(v),3),x] for v,x in r[:5]],t=[tx,round(float(cf))],viz=viz,bg='%02x%02x%02x'%tuple(bg))
        p2=partir_na_barra(t,lab)
        if p2:
            re_=casar(V,b,lab,p2[0],lim,hx,n_fino=6,filtro=V.sem_baixo,ang=a_); rd=casar(V,b,lab,p2[1],lim,hx,n_fino=5,filtro=V.so_raiz,ang=a_)
            if re_ and rd: e['s']=dict(l=[[round(float(v),3),x] for v,x in re_[:3]],r=[[round(float(v),3),x] for v,x in rd[:3]])
        out['toks'].append(e)
    return out
if __name__=='__main__':
    for a in sys.argv[1:]:
        t0=time.time(); r=bruto(a); print(os.path.basename(a),'fonte',r.get('fonte'),r.get('nota_fonte'),'cap',r.get('cap'),'hx',r.get('hx'),'partitura',r.get('partitura'),len(r['toks']),'%.1fs'%(time.time()-t0))
        json.dump(r,open('/tmp/cif/foto_teste_'+os.path.basename(a)[:-4]+'.json','w'))
        bons=[t for t in r['toks'] if t['c'][0][0]>=0.7]
        for t in sorted(bons,key=lambda t:(round(t['base']/(2.2*r['cap'])),t['x0']))[:45]:
            print('  ',t['x0'],t['base'],'cap',t['cap'],t['c'][0],t['c'][1] if len(t['c'])>1 else '',t['t'],'viz',t['viz'])
