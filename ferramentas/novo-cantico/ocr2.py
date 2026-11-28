import json,sys,subprocess,re,os
from multiprocessing import Pool
from PIL import Image
R=json.load(open('/tmp/nc/ocr.json'))
def tsv(im):
    h=1800; im=im.convert('L'); im=im.resize((int(im.width*h/im.height),h))
    fn=f'/tmp/nc/_t{os.getpid()}.png'; im.save(fn)
    r=subprocess.run(['tesseract',fn,'-','-l','por','--psm','11','tsv'],capture_output=True,text=True).stdout
    rows=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        try: rows.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11]))
        except: pass
    return rows,im.size
def score(rows): return sum(1 for r in rows if r['conf']>70 and len(r['t'])>2)
def work(k):
    r=R[k]; im=Image.open(r['p'])
    out=dict(r); out['score']=score(r['rows'])
    if im.width>im.height:
        rows,sz=tsv(im); s=score(rows)
        if s>out['score']: out.update(rot=0,rows=rows,sz=sz,score=s)
    elif out['score']<40:
        for ang in (-90,90,180):
            if ang==180 and r['rot']==180: continue
            rows,sz=tsv(im.rotate(ang,expand=True)); s=score(rows)
            if s>out['score']: out.update(rot=ang,rows=rows,sz=sz,score=s)
    return out
if __name__=='__main__':
    with Pool(2) as pool: res=pool.map(work,range(len(R)),chunksize=4)
    json.dump(res,open('/tmp/nc/ocr2.json','w'))
    import collections
    print('ok',len(res),collections.Counter(r['rot'] for r in res))
