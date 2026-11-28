import cv2,numpy as np,json,collections,os
from multiprocessing import Pool
from pageproc import process
from enh2 import flatten
D=json.load(open('/tmp/nc/ident6.json'))
REF=json.load(open('/tmp/nc/titulos.json'))
rot2idx={r['rot']:k for k,r in enumerate(REF)}
# --- as duas fotos novas (400 A – Ofertórios e Améns)
def nova(path,box,name):
    im=cv2.imread(path,0); x0,y0,x1,y1=box
    cv2.imwrite(f'/tmp/nc/pgs/{name}.png',im[y0:y1,x0:x1])
nova('/mnt/user-data/uploads/251bf961-image.jpg',(70,60,1340,2016),'n623S')
nova('/mnt/user-data/uploads/752b9970-image.jpg',(105,80,1390,2016),'n624S')
def sharp(name):
    g=cv2.imread(f'/tmp/nc/pgs/{name}.png',0); n=flatten(g)
    s=1500/n.shape[0]; e=cv2.resize(n.astype(np.uint8),None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(e,cv2.CV_32F,ksize=3).var())
for name,pg,role,hy in (('n623S',623,'T',rot2idx['400-A']),('n624S',624,'C',rot2idx['400-A'])):
    g=cv2.imread(f'/tmp/nc/pgs/{name}.png',0)
    d=dict(name=name,f='n',i=pg,tag='S',w=g.shape[1],h=g.shape[0],sharp=30000.0,staff=0.02,role=role,pg=pg,nova=True)
    if role=='T': d['hymn']=hy
    else: d['hymn_c']=hy
    D.append(d)
def score(d):
    if d.get('nova'): return 1e9
    return min(d['sharp'],40000)*(0.5+0.5*min(1,d['staff']/0.004))*min(1,d['h']/2600)**0.5
g=collections.defaultdict(list)
for d in D: g[d['pg']].append(d)
sel={}
for pg,l in g.items():
    b=max(l,key=score); sel[pg]=b
def cls(d,vis):
    q=d['sharp']
    if d.get('nova'): return 'boa'
    if q<4500 or vis<0.001: return 'ruim'
    if q<9000 or vis<0.004: return 'media'
    return 'boa'
def work(pg):
    d=sel[pg]
    e,info=process(d['name'],d['sharp'],d['staff'])
    cv2.imwrite(f'/tmp/nc/final/p{pg:03d}.png',e)
    return pg,e.shape,info
if __name__=='__main__':
    with Pool(2) as p: res=p.map(work,sorted(sel),chunksize=8)
    out={}
    for pg,shape,info in res:
        d=sel[pg]
        out[pg]=dict(src=d['name'],role=d['role'],hymn=REF[d['hymn'] if d['role']=='T' else d['hymn_c']]['rot'],version=d.get('version',0),q=d['sharp'],staff=d['staff'],cls=cls(d,info['vis']),w=shape[1],h=shape[0],ang=info['ang'],lavada=info['lavada'],vis=info['vis'],alts=[x['name'] for x in g[pg] if x is not d])
    json.dump(out,open('/tmp/nc/final/paginas.json','w'),ensure_ascii=False,indent=0)
    c=collections.Counter(v['cls'] for v in out.values()); print(len(out),c)
