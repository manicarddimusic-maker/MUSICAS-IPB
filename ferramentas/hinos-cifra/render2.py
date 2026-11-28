import json,math,os,shutil
from PIL import Image
W=json.load(open('words.json')); d=json.load(open('segs.json')); heads=d['heads']; segs=d['segs']
S=400/72; XR={0:(71,291),1:(305,525)}; WC=220; GX=22; PADV=10; PADH=8; TARGET=0.85; STANZA=13
pages={}
def pg(p):
    if p not in pages: pages[p]=Image.open(f'pg/p-{p:03d}.png').convert('L')
    return pages[p]
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
    # DP: parte a sequencia em n grupos consecutivos minimizando a altura maxima
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
meta=[]
os.makedirs('out2',exist_ok=True)
for f in os.listdir('out2'): os.remove('out2/'+f)
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
    im=Image.new('L',(Wpx,Hpx),255)
    for gi,g in enumerate(gr):
        x=int((PADH+gi*(WC+GX))*S); y=PADV; prev=None
        for b in g:
            y+=gap_before(prev,b) if prev else 0
            x0,x1=XR[b['c']]
            crop=pg(b['p']).crop((int(x0*S),int(b['y0']*S),int(x1*S),int(b['y1']*S)))
            im.paste(crop,(x,int(y*S))); y+=b['y1']-b['y0']; prev=b
    nome=f"hc-{h['num']:03d}{'a' if h['label'] else ''}.jpg"
    im.save('out2/'+nome,quality=86,optimize=True)
    meta.append(dict(num=h['num'],label=h['label'],titulo=h['title'],file=nome,cols=n,aspect=round(asp,2)))
json.dump(meta,open('meta2.json','w'),ensure_ascii=False,indent=1)
import collections
print(len(meta),collections.Counter(m['cols'] for m in meta)); print(sorted(round(m['aspect'],2) for m in meta)[::40])
