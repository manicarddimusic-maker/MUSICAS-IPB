import json,math,os,re,sys,collections
import pymupdf
sys.path.insert(0,'/tmp/cif')
from acordes import eh_acorde
os.chdir('/tmp/hc')
W=json.load(open('words.json')); d=json.load(open('segs.json')); heads=d['heads']; segs=d['segs']
S=400/72; XR={0:(71,291),1:(305,525)}; WC=220; GX=22; PADV=10; PADH=8; TARGET=0.85; STANZA=13
def blocks_of(strip):
    p,c,y0,y1=strip
    ws=sorted([w for w in W[p-1] if (w[0]<305)==(c==0) and y0-0.5<=w[1] and w[3]<=y1+0.5],key=lambda w:w[1])
    rows=[]
    for w in ws:
        if rows and abs(w[1]-rows[-1][0])<2.5: rows[-1][1]=max(rows[-1][1],w[3])
        else: rows.append([w[1],w[3]])
    out=[]; cur=[rows[0][0],rows[0][1]]
    for a,b in zip(rows,rows[1:]):
        if b[0]-a[1]>=STANZA: out.append(cur); cur=[b[0],b[1]]
        else: cur[1]=b[1]
    out.append(cur)
    return [dict(p=p,c=c,y0=a-1,y1=b+1,strip=(p,c,y0,y1)) for a,b in out]
def gap_before(prev,b):
    if prev is None: return 0
    if prev['strip']==b['strip']: return max(2,b['y0']-prev['y1'])
    return STANZA
def best_split(bl,n):
    N=len(bl)
    def hgt(i,j):
        t=0;prev=None
        for k in range(i,j):
            t+=gap_before(prev,bl[k]) if prev else 0
            t+=bl[k]['y1']-bl[k]['y0']; prev=bl[k]
        return t
    from functools import lru_cache
    @lru_cache(None)
    def f(i,k):
        if k==1: return (hgt(i,N),(N,))
        best=(1e9,None)
        for j in range(i+1,N-k+2):
            r=f(j,k-1); m=max(hgt(i,j),r[0])
            if m<best[0]: best=(m,(j,)+r[1])
        return best
    m,cuts=f(0,n); groups=[];i=0
    for j in cuts: groups.append(bl[i:j]); i=j
    return m,groups
doc=pymupdf.open('/tmp/hc/hnc.pdf')
_tok={}
def tokens(p):
    """palavras em negrito da página (as cifras e os títulos), com caixa e linha de base"""
    if p in _tok: return _tok[p]
    out=[]
    for b in doc[p-1].get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                if 'Bold' not in s['font']: continue
                cur=None
                for ch in s['chars']:
                    c=ch['c']
                    if c.isspace() or c=='\xa0':
                        if cur: out.append(cur); cur=None
                        continue
                    x0,y0,x1,y1=ch['bbox']
                    if cur is None: cur=dict(t=c,x0=x0,x1=x1,base=ch['origin'][1],size=s['size'],y0=y0,y1=y1)
                    else: cur['t']+=c; cur['x1']=x1
                if cur: out.append(cur)
    _tok[p]=out; return out
folhas={}; stats=collections.Counter()
for k in sorted(segs,key=int):
    h=heads[int(k)]; bl=[]
    for s in segs[k]: bl+=blocks_of(tuple(s))
    best=None
    for n in range(1,min(3,len(bl))+1):
        m,gr=best_split(bl,n)
        asp=(m+2*PADV)/(n*WC+(n-1)*GX+2*PADH)
        sc=abs(math.log(asp/TARGET))+(0.03*(n-1))
        if best is None or sc<best[0]: best=(sc,n,gr,m,asp)
    _,n,gr,m,asp=best
    Wpx=int((n*WC+(n-1)*GX+2*PADH)*S); Hpx=int((m+2*PADV)*S)
    nome=f"hc-{h['num']:03d}{'a' if h['label'] else ''}.jpg"
    cif=[]; tom=None
    for gi,g in enumerate(gr):
        x=int((PADH+gi*(WC+GX))*S); y=PADV; prev=None
        for b in g:
            y+=gap_before(prev,b) if prev else 0
            x0,x1=XR[b['c']]
            toks=[t for t in tokens(b['p']) if x0-1<=t['x0']<x1 and b['y0']<=t['base']<=b['y1']+0.5]
            # o "o" pequeno e elevado logo depois de um acorde é o sinal de diminuto (º)
            junt=[]
            for t in sorted(toks,key=lambda t:t['x0']):
                if re.fullmatch(r'[oO0º°]',t['t']) and t['size']<9:
                    dono=[c for c in toks if c is not t and eh_acorde(c['t']) and c['x1']-1.5<=t['x0']<=c['x1']+3 and 0<=c['base']-t['base']<7]
                    if dono:
                        dono[0]['t']+='º'; dono[0]['x1']=max(dono[0]['x1'],t['x1']); stats['dim']+=1; continue
                junt.append(t)
            toks=junt
            # agrupa por linha (mesma linha de base)
            linhas=collections.defaultdict(list)
            for t in toks: linhas[round(t['base'],0)].append(t)
            for base,ts in sorted(linhas.items()):
                ts.sort(key=lambda t:t['x0'])
                cabecalho=bool(re.fullmatch(r'\d{1,3}(-[A-Z])?',ts[0]['t'])) and len(ts)>1 and ts[0]['x0']<x0+20
                chave=None
                for i,t in enumerate(ts):
                    # o tom vem logo antes do compasso (ex.: "E-  4/4")
                    if re.fullmatch(r'\d{1,2}/\d{1,2}',t['t']) and i>0 and eh_acorde(ts[i-1]['t']) and len(ts[i-1]['t'])<=4: chave=ts[i-1]; break
                if chave is not None:
                    ts=[chave]; tom=tom or chave['t']
                elif cabecalho: ts=[]
                else:
                    ok=[t for t in ts if eh_acorde(t['t'])]
                    if len(ok)<0.6*len(ts): stats['linha_mista']+=1; ts=[]
                    else:
                        stats['nao_acorde_em_linha']+=len(ts)-len(ok); ts=ok
                for t in ts:
                    X=x+(t['x0']-x0)*S; B=int(y*S)+(t['base']-b['y0'])*S
                    cif.append([round(X),round(B),round((t['x1']-t['x0'])*S),round(t['size']*S,1),t['t']])
                    stats['cifras']+=1
            y+=b['y1']-b['y0']; prev=b
    f=dict(w=Wpx,h=Hpx,f='t',c=cif)
    if tom: f['k']=tom
    else: stats['sem_tom']+=1
    folhas['/midias/cifras3/'+nome]=f
json.dump(dict(v=1,folhas=folhas),open('/tmp/cif/hinoscifra_hc.json','w'),ensure_ascii=False,separators=(',',':'))
print(len(folhas),dict(stats),os.path.getsize('/tmp/cif/hinoscifra_hc.json')//1024,'KB')
f=folhas['/midias/cifras3/hc-021.jpg']; print(f['w'],f['h'],f.get('k'),f['c'][:12])
