import json,sys,subprocess,re,os,cv2,numpy as np
from multiprocessing import Pool
from enh import enhance
R=json.load(open('/tmp/nc/ocr2.json'))
CH=re.compile(r'^[A-G][#b]?(m|maj|min|dim|aug|sus|add|M|º|°|\+|[0-9]|\(|\)|/[A-G][#b]?|/[0-9])*$')
def tsv(g):
    h=1800; g=cv2.resize(g,(int(g.shape[1]*h/g.shape[0]),h),interpolation=cv2.INTER_AREA)
    fn=f'/tmp/nc/_t{os.getpid()}.png'; cv2.imwrite(fn,g)
    r=subprocess.run(['tesseract',fn,'-','-l','por','--psm','11','tsv'],capture_output=True,text=True).stdout
    rows=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        try: rows.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11]))
        except: pass
    return rows,(g.shape[1],g.shape[0])
def score(rows):
    s=0
    for r in rows:
        t=r['t']
        if r['conf']>70 and len(t)>2 and re.search(r'[A-Za-zÀ-ú]{3}',t): s+=1
        elif r['conf']>55 and CH.match(t) and len(t)>=2: s+=0.7
    return s
ROT={0:None,-90:cv2.ROTATE_90_CLOCKWISE,90:cv2.ROTATE_90_COUNTERCLOCKWISE,180:cv2.ROTATE_180}
def work(k):
    r=R[k]; g=enhance(cv2.imread(r['p'],0))
    best=None; allsc={}
    for a,code in ROT.items():
        gg=g if code is None else cv2.rotate(g,code)
        rows,sz=tsv(gg); s=score(rows); allsc[a]=s
        if best is None or s>best[0]: best=(s,a,rows,sz)
    out=dict(r); out.update(rot=best[1],rows=best[2],sz=best[3],score=best[0],allsc=allsc,enh=True)
    return out
if __name__=='__main__':
    idx=[k for k,r in enumerate(R) if r['score']<30]
    with Pool(2) as pool: res=pool.map(work,idx,chunksize=2)
    for k,o in zip(idx,res):
        print(o['f'],o['i'],'antes',R[k]['rot'],R[k]['score'],'agora',o['rot'],o['allsc'])
        R[k]=o
    json.dump(R,open('/tmp/nc/ocr3.json','w'))
