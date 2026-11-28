"""Fotos de partitura da aba Hinos em que as cifras impressas foram riscadas e reescritas à mão noutro tom.
O tom da folha passa a ser o da caneta: as cifras guardadas são as impressas já levadas para esse tom (K semitons),
a tinta da caneta perto das linhas de cifras vira "borracha" (some quando o tom muda) e os riscos sem cifra conhecida ficam marcados."""
import sys,json,glob,os,re,subprocess
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from multiprocessing import Pool
import mao
R='/home/claude/musicas-ipb/public'
GIRO={90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}
K={'h003_6458_v2':-3,'h004_6488':-3,'h016_6366':-1,'h027_6437':-3,'h027_9942c626':-3,'h028_6446':-3,'h028_73e79a49':-3,'h032_bf50fecd':-2,
   'h042_6378':-1,'h042_6408':-1,'h064_6451':-1,'h064_d0d20ca2':-1,'h088_6352':-1,'h088_6483':-3,'h088b_82c9f21b':-1,'h104_6487':-3,
   'h107_6367':-3,'h107_6456':-1,'h110_6435':-1,'h110_a21c6fce':-1,'h120_1d7a266d':-1,'h120_6425':-1,'h133_6351':-1,'h133_9c1ed220':-1,
   'h135_6403':-3,'h137_6395':-3,'h159_6396':-1,'h172_2858fca2':-1,'h172_6438':-1,'h286_6370':-1,'h288_6442':-1,'h288_9d0be71a':-1,
   'h297_3e1f37e4':-3,'h297_6452':-3,'h298_nova':-1,'h299_6427':-1,'h332_6379':-1,'h333_6364':-1,'h340_6439':-1,'h340_b1047d39':-1,
   'h352_6383':-1,'h352_6477':-1,'h367_6426':-3,'h367_6432':-1,'h382_6422':-1}
K.update({'h239_6428':-5,'h311_6476':-3,'h349_6412':-1,'h079_6392':-2})
FONTE_FIXA={'h079_6392':['exata:/midias/cifras/u-79-1.jpg']}
SEM_BORRACHA={'h298_nova'}                       # partitura refeita noutro tom, sem caneta
FORA={'h239_6428','h311_6476','h349_6412','h003_6458','h298_nova'}       # cifras impressas tapadas com corretivo: tratar à mão
def k_de(nome):
    for p,v in K.items():
        if nome.startswith(p): return v
    return None
def aplainar(g):
    k=max(31,int(min(g.shape)*0.05))|1
    fundo=cv2.GaussianBlur(cv2.morphologyEx(g,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))),(0,0),k/3)
    return np.clip(g.astype(np.float32)/np.maximum(fundo.astype(np.float32),1)*255,0,255).astype(np.uint8)
def linhas_de(pares):
    rows=[]
    for p in sorted(pares,key=lambda p:(p[5],p[4])):
        for rw in rows:
            v=min(rw,key=lambda o:abs(o[4]-p[4]))
            if abs(v[5]-p[5])<0.9*p[7]+0.1*abs(v[4]-p[4]): rw.append(p); break
        else: rows.append([p])
    return [sorted(rw,key=lambda o:o[4]) for rw in sorted(rows,key=lambda rw:min(o[5] for o in rw))]
def papel(cor,x0,y0,x1,y1):
    a=cor[max(0,y0-4):y1+4,max(0,x0-4):x1+4].reshape(-1,3)
    if len(a)==0: return 'ffffff'
    sm=a.sum(axis=1); cl=a[sm>=np.percentile(sm,70)]
    return '%02x%02x%02x'%tuple(int(v) for v in np.median(cl,axis=0)[::-1])
def um(f):
    try:
        from registro import transferir
        from transf_hinos import fontes_do_hino
        r=json.load(open(f)); img=r['img']; nome=os.path.basename(img)[:-4]
        k=k_de(nome)
        if k is None: return nome,None
        num=int(re.match(r'h(\d+)',nome).group(1))
        fontes={c[0]:c for c in fontes_do_hino(num,str(num))}
        dst=cv2.imread(R+img); g=r['folha'].get('r',0); up=cv2.rotate(dst,GIRO[g]) if g else dst
        cinza=aplainar(cv2.cvtColor(up,cv2.COLOR_BGR2GRAY)); H,W=cinza.shape
        tinta=(cinza<150).astype(np.uint8)
        picos=[p for p in mao.picos_de_cor(up,70) if not (12<=p[0]<=38)]
        mcor=mao.tinta_colorida(up,picos[0][0],70,larga=True) if picos else None
        velha={(c[0],c[1]):c[4] for c in r['folha']['c']}
        cifras=[]; borr=[]; marcas=[]; usa_cor=0; usa_dif=0
        for chave,_ in r['de']:
            _,caminho,folha=fontes[chave]; sg=cv2.imread(caminho,0)
            o,rel=transferir(sg,folha,dst,chave_src=chave)
            if not o: continue
            ents={(c[0],c[1]):c for c in o['c']}
            for c in o['c']:
                if c[4]=='?' and velha.get((c[0],c[1]),'?')!='?': c[4]=velha[(c[0],c[1])]
            cifras+=o['c']
            if nome in SEM_BORRACHA or any(nome.startswith(p) for p in SEM_BORRACHA): continue
            P=rel['pares']
            if not P: continue
            capg=float(np.median([p[7] for p in P]))
            X0=int(max(0,min(p[4] for p in P)-3.5*capg)); X1=int(min(W,max(p[4]+p[6] for p in P)+5*capg))
            Mant=None
            for rw in linhas_de(P):
                cap=float(np.median([p[7] for p in rw]))
                topo=min(p[5] for p in rw)-cap; fundo=max(p[5] for p in rw)+0.25*cap
                y0=int(max(0,topo-2.7*cap)); y1=int(min(H,fundo+0.35*cap))
                if y1-y0<4 or X1-X0<4: continue
                faixa_cor=mcor[y0:y1,X0:X1] if mcor is not None else None
                if faixa_cor is not None and faixa_cor.sum()>1.2*cap*cap*max(1,len(rw))*0.5:
                    extra=faixa_cor.copy(); usa_cor+=1
                else:
                    M=None
                    if len(rw)>=2:
                        S=[];D=[]
                        for xs,bs,ws,cs_,xd,bd,wd,cd in rw: S+=[[xs,bs],[xs+ws,bs],[xs,bs-cs_]]; D+=[[xd,bd],[xd+wd,bd],[xd,bd-cd]]
                        M,_i=cv2.estimateAffine2D(np.float32(S),np.float32(D),method=cv2.LMEDS)
                    if M is None: M=Mant
                    if M is None: continue
                    Mant=M
                    M2=M.copy(); M2[0,2]-=X0; M2[1,2]-=y0
                    src_w=cv2.warpAffine(sg,M2,(X1-X0,y1-y0),flags=cv2.INTER_AREA,borderValue=255)
                    kk=max(3,int(0.45*cap))|1
                    tinta_src=cv2.dilate((src_w<150).astype(np.uint8),np.ones((kk,kk),np.uint8))
                    extra=tinta[y0:y1,X0:X1]&(1-tinta_src)
                    extra=cv2.morphologyEx(extra,cv2.MORPH_OPEN,np.ones((2,2),np.uint8)); usa_dif+=1
                junto=cv2.dilate(extra,cv2.getStructuringElement(cv2.MORPH_RECT,(max(3,int(0.55*cap))|1,max(3,int(0.3*cap))|1)))
                n,lab,st,_c=cv2.connectedComponentsWithStats(junto,8)
                caixas=[]
                for i in range(1,n):
                    bx,by,bw,bh,ar=[int(v) for v in st[i]]
                    px=int(extra[by:by+bh,bx:bx+bw].sum())
                    if px<0.15*cap*cap or bh<0.35*cap: continue
                    ys,xs=np.nonzero(extra[by:by+bh,bx:bx+bw])
                    caixas.append([X0+bx+int(xs.min()),y0+by+int(ys.min()),X0+bx+int(xs.max())+1,y0+by+int(ys.max())+1])
                chs=[ents[(p[4],p[5])] for p in rw if (p[4],p[5]) in ents]
                base_l=float(np.median([p[5] for p in rw]))
                prot=[]; cand=[]
                for (ax,ay,bx_,by_) in caixas:
                    h=by_-ay; dentro=max(0,min(by_,fundo+0.1*cap)-max(ay,topo-0.1*cap))
                    sobre=any(min(bx_,c[0]+c[2])-max(ax,c[0])>0.3*min(bx_-ax,c[2]) and ay<c[1]+0.3*cap and by_>c[1]-1.3*cap for c in chs)
                    if sobre: borr.append([ax,ay,bx_,by_])
                    elif dentro>=0.6*h and h<=1.9*cap and bx_-ax<=7*cap:
                        marcas.append([ax,int(round(max(by_,base_l))) if abs(by_-base_l)<0.5*cap else by_,bx_-ax,round(cap/0.711,1),'?',papel(up,ax,ay,bx_,by_),0,int(by_-ay+3),3])
                        prot.append((ax-1.1*cap,bx_+1.1*cap))
                    else: cand.append([ax,ay,bx_,by_])
                for b in cand:
                    if any(b[2]>p0 and b[0]<p1 for p0,p1 in prot): continue
                    borr.append(b)
        return nome,dict(img=img,r=g,w=W,h=H,k=k,cifras=cifras,borr=borr,marcas=marcas,cor=usa_cor,dif=usa_dif,matiz=picos[0][0] if picos else None)
    except Exception as ex:
        import traceback; return os.path.basename(f),dict(erro=traceback.format_exc()[-400:])
if __name__=='__main__':
    fs=[f for f in sorted(glob.glob('/tmp/cif/transf/*.json')) if (lambda r:r['folha'] and r['de'][0][0].startswith('nc'))(json.load(open(f)))]
    res={}
    with Pool(2) as p:
        for nome,d in p.imap_unordered(um,fs,chunksize=2):
            if d is None: continue
            if 'erro' in d: print('ERRO',nome,d['erro']); continue
            res[nome]=d
    # tom novo e cifras já no tom da caneta (mesmo motor do aplicativo)
    nomes=sorted(res)
    # tom impresso de cada hino: pelas páginas do hinário, na ordem de leitura (o último acorde é a tônica)
    from nc_decidir import em_linhas
    FOL=json.load(open('/tmp/nc/final/folhas.json')); L=json.load(open('/tmp/cif/nc_decidido.json'))
    def acordes_do_hino(num):
        pgs=[]
        for F in FOL:
            if re.fullmatch(r'%d(-A)?'%num,F['rot']): pgs+=[p['pg'] for p in F['pages']]
        seq=[]
        for pg in sorted(set(pgs)):
            r_=L.get(str(pg))
            if r_: seq+=[x[4] for rw in em_linhas(r_['c'],r_['cap']) for x in rw if x[4]!='?']
        return seq
    nums=sorted({int(re.match(r'h(\d+)',n).group(1)) for n in nomes})
    toms=json.loads(subprocess.run(['node','--experimental-strip-types','/tmp/cif/transpor.mts'],input=json.dumps([dict(k=0,acordes=acordes_do_hino(n)) for n in nums]),capture_output=True,text=True).stdout)
    tom_hino={n:t['tom'] for n,t in zip(nums,toms)}
    print('tons impressos:',tom_hino)
    ent=[dict(k=res[n]['k'],acordes=[c[4] for c in res[n]['cifras']],tom=tom_hino.get(int(re.match(r'h(\d+)',n).group(1)))) for n in nomes]
    out=json.loads(subprocess.run(['node','--experimental-strip-types','/tmp/cif/transpor.mts'],input=json.dumps(ent),capture_output=True,text=True).stdout)
    fn=R+'/data/cifras/hinos.json'; J=json.load(open(fn))
    for n,o in zip(nomes,out):
        d=res[n]; cs=[]
        up=None
        for b in d['borr']:
            cs.append([b[0],b[3],b[2]-b[0],10,'',None,0,b[3]-b[1],0])
        for c,novo in zip(d['cifras'],o['acordes']):
            e=list(c); e[4]=novo; e[3]=round(e[3]*1.25,1); cs.append(e)
        cs+=d['marcas']
        d['tom']=o['tom']; d['tomNovo']=o['tomNovo']; d['final']=cs
        print(n,'k',d['k'],o['tom'],'->',o['tomNovo'],'| cifras',len(d['cifras']),'| borrachas',len(d['borr']),'| riscos sem cifra',len(d['marcas']),'| cor/dif',d['cor'],d['dif'])
    json.dump(res,open('/tmp/cif/hinos_final.json','w'))
    # cor do papel das borrachas e gravação
    for n in nomes:
        d=res[n]; up=cv2.imread(R+d['img'])
        if d['r']: up=cv2.rotate(up,GIRO[d['r']])
        for e in d['final']:
            if e[4]=='' : e[5]=papel(up,e[0],e[1]-e[7],e[0]+e[2],e[1])
        folha=dict(w=up.shape[1] if not d['r'] in (90,270) else up.shape[0],h=up.shape[0] if not d['r'] in (90,270) else up.shape[1],f='s',c=d['final'])
        if d['tomNovo']: folha['k']=d['tomNovo']
        if d['r']: folha['r']=d['r']
        J['folhas'][d['img']]=folha
    for img in list(J['folhas']):
        if any(os.path.basename(img).startswith(p) for p in FORA): del J['folhas'][img]
    json.dump(J,open(fn,'w'),ensure_ascii=False,separators=(',',':'))
    print(len(nomes),'folhas no tom da caneta;',os.path.getsize(fn)//1024,'KB')
