import json,glob,collections,sys
sys.path.insert(0,'/tmp/cif')
import numpy as np
from nccomum import PAG
rows=[]
for f in sorted(glob.glob('/tmp/cif/pag/p*.json')):
    r=json.load(open(f)); pg=r['pg']; c=r['c']
    ok=[x for x in c if x[4]!='?']; q=len(c)-len(ok)
    conf=[x[5] for x in ok]
    rows.append((pg,PAG[pg]['cls'],len(ok),q,float(np.median(conf)) if conf else 0,float(np.percentile(conf,20)) if conf else 0,r['lim'],r['hx'],r.get('nhx')))
print('páginas',len(rows))
for cls in ('boa','media','ruim'):
    R=[x for x in rows if x[1]==cls]
    if not R: continue
    print(cls,len(R),'| cifras lidas (mediana)',np.median([x[2] for x in R]),'| "?" por página',round(np.mean([x[3] for x in R]),1),'| confiança mediana',round(float(np.median([x[4] for x in R])),3),'| páginas sem nenhuma',sum(1 for x in R if x[2]==0))
if len(sys.argv)>1:
    for x in rows:
        if x[1]!='boa' or x[2]<6 or x[4]<0.9: print(x)
