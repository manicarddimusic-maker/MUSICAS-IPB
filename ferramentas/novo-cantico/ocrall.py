import json,sys,subprocess,re,os
from multiprocessing import Pool
from PIL import Image
B=json.load(open('/tmp/nc/big.json'))
jobs=[(f,i,p) for f in B for i,p in enumerate(B[f])]
def tsv(im):
    h=1800; im=im.convert('L'); im=im.resize((int(im.width*h/im.height),h))
    im.save(f'/tmp/nc/_t{os.getpid()}.png')
    r=subprocess.run(['tesseract',f'/tmp/nc/_t{os.getpid()}.png','-','-l','por','--psm','11','tsv'],capture_output=True,text=True).stdout
    rows=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        try: rows.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11]))
        except: pass
    return rows,im.size
def score(rows): return sum(1 for r in rows if r['conf']>70 and len(r['t'])>2)
def work(j):
    f,i,p=j
    im=Image.open(p); rot=0
    if im.width>im.height:
        best=None
        for ang in (-90,90):
            r=im.rotate(ang,expand=True)
            rows,sz=tsv(r)
            s=score(rows)
            if best is None or s>best[0]: best=(s,ang,rows,sz)
        _,rot,rows,sz=best
    else:
        rows,sz=tsv(im)
        s0=score(rows)
        if s0<25:
            r=im.rotate(180,expand=True); rows2,sz2=tsv(r)
            if score(rows2)>s0*1.5: rot=180; rows,sz=rows2,sz2
    return dict(f=f,i=i,p=p,rot=rot,sz=sz,rows=rows)
if __name__=='__main__':
    with Pool(2) as pool: res=pool.map(work,jobs,chunksize=4)
    json.dump(res,open('/tmp/nc/ocr.json','w'))
    print('ok',len(res))
