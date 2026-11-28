"""Auditoria das páginas do hinário: todo sistema (par de pautas) deveria ter uma linha de cifras em cima.
Lista os sistemas sem nenhuma cifra lida. Saída: /tmp/cif/nc_audit.json {pg: {sistemas:[{y, x0, x1, tem, n}], d}}"""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from multiprocessing import Pool
from ncpauta import pautas,sistemas,topo
def um(pg):
    try:
        L=json.load(open('/tmp/cif/nc_decidido.json')); r=L.get(str(pg))
        e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
        if e is None: return pg,None
        P,d=pautas(e)
        if d is None or not P: return pg,dict(d=None,sistemas=[])
        tops,lig=sistemas(e,P,d); W=e.shape[1]
        out=[]
        for t in tops:
            p=P[t]; ym=float(topo(p,W/2))
            n=0
            if r:
                for c in r['c']:
                    yt=float(topo(p,c[0]))
                    if yt-9*d<=c[1]<=yt-0.2*d: n+=1
            out.append(dict(y=round(ym),xa=p['xa'],xb=p['xb'],co=p['co'],n=n))
        return pg,dict(d=d,sistemas=out,lida=bool(r),nc=len(r['c']) if r else 0)
    except Exception as ex:
        return pg,dict(erro=str(ex)[:100])
if __name__=='__main__':
    pgs=sorted(int(f[1:4]) for f in os.listdir('/tmp/nc/final') if f.startswith('p') and f.endswith('.png') and f[1:4].isdigit())
    res={}
    with Pool(2) as p:
        for pg,r in p.imap_unordered(um,pgs,chunksize=8): res[pg]=r
    json.dump(res,open('/tmp/cif/nc_audit.json','w'))
    lidas=[pg for pg in res if res[pg] and res[pg].get('lida')]
    falt=[(pg,[s['y'] for s in res[pg]['sistemas'] if s['n']==0],len(res[pg]['sistemas'])) for pg in sorted(lidas) if any(s['n']==0 for s in res[pg]['sistemas'])]
    print('páginas:',len(pgs),'lidas:',len(lidas),'com sistema sem cifra:',len(falt),'sistemas sem cifra:',sum(len(f[1]) for f in falt))
    print(falt[:60])
