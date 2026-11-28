import cv2,numpy as np,json,collections
from multiprocessing import Pool
from enh2 import flatten
D=json.load(open('/tmp/nc/ident5.json'))
def staffm(name):
    g=cv2.imread(f'/tmp/nc/pgs/{name}.png',0)
    s=1500/g.shape[0]; g=cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    n=flatten(g)
    # linhas horizontais finas: resposta de um filtro "linha escura fina" (top-hat vertical)
    k=cv2.getStructuringElement(cv2.MORPH_RECT,(1,7))
    bh=cv2.morphologyEx(n.astype(np.uint8),cv2.MORPH_BLACKHAT,k)      # realça traços escuros finos na vertical
    lines=cv2.morphologyEx((bh>28).astype(np.uint8),cv2.MORPH_OPEN,np.ones((1,45),np.uint8))
    frac=float(lines.mean())
    # contraste médio das linhas encontradas
    return name,frac
if __name__=='__main__':
    names=[d['name'] for d in D]
    with Pool(2) as p: res=dict(p.map(staffm,names,chunksize=16))
    for d in D: d['staff']=res[d['name']]
    json.dump(D,open('/tmp/nc/ident6.json','w'),ensure_ascii=False)
    v=sorted(res.values()); print([round(v[int(len(v)*k/10)],4) for k in range(10)],v[-1])
    for n in ('a117S','a069S','c110S','b014S','a093L','b004L','a071S','a042L','b013L','a046S','a130L','b076L','a000S','a011S','c051L'):
        d=[x for x in D if x['name']==n][0]; print(n,int(d['sharp']),round(d['staff'],4))
