import json,sys,subprocess,re,os,cv2,numpy as np
from multiprocessing import Pool
from enh import enhance
R=json.load(open('/tmp/nc/ocr4.json'))
ROT={0:None,-90:cv2.ROTATE_90_CLOCKWISE,90:cv2.ROTATE_90_COUNTERCLOCKWISE,180:cv2.ROTATE_180}
def ocr(g,psm='6',lang='por',extra=()):
    fn=f'/tmp/nc/_s{os.getpid()}.png'; cv2.imwrite(fn,g)
    r=subprocess.run(['tesseract',fn,'-','-l',lang,'--psm',psm,*extra,'tsv'],capture_output=True,text=True).stdout
    rows=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        try: rows.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11]))
        except: pass
    return rows
def gutter(e):
    H,W=e.shape
    ink=(e<128).astype(np.float32)[int(H*0.1):int(H*0.9)]
    prof=ink.mean(axis=0); k=max(5,W//200)|1
    prof=cv2.blur(prof.reshape(1,-1),(k,1)).ravel()
    a,b=int(W*0.44),int(W*0.56)
    # menor tinta; em empate, mais perto do centro
    idx=np.arange(a,b); cost=prof[a:b]+0.02*np.abs(idx-W/2)/W
    return int(idx[np.argmin(cost)])
def sharp(e):
    # nitidez em escala normalizada (altura 1500)
    s=1500/e.shape[0]; g=cv2.resize(e,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    lap=cv2.Laplacian(g,cv2.CV_32F,ksize=3)
    return float(lap.var()), float((g<110).mean())
def work(k):
    r=R[k]; g=cv2.imread(r['p'],0); c=ROT[r['rot']]
    if c is not None: g=cv2.rotate(g,c)
    e=enhance(g)
    H,W=g.shape
    if W/H>1.05:
        gx=gutter(e); parts=[('L',0,gx),('R',gx,W)]
    else: parts=[('S',0,W)]
    out=[]
    for tag,x0,x1 in parts:
        pg=g[:,x0:x1]; pe=e[:,x0:x1]
        name=f"{r['f']}{r['i']:03d}{tag}"
        cv2.imwrite(f'/tmp/nc/pgs/{name}.png',pg)
        ph,pw=pe.shape
        sv,dark=sharp(pe)
        # faixa do topo (titulo/numero) e do rodape, ampliadas para altura de letra confortavel
        top=pe[0:int(ph*0.15)]; sc=1800/pw
        top=cv2.resize(top,None,fx=sc,fy=sc,interpolation=cv2.INTER_CUBIC)
        trows=ocr(top,'11')
        foot=pe[int(ph*0.925):]; foot=cv2.resize(foot,None,fx=sc,fy=sc,interpolation=cv2.INTER_CUBIC)
        frows=ocr(foot,'11')
        out.append(dict(name=name,f=r['f'],i=r['i'],tag=tag,w=pw,h=ph,sharp=sv,dark=dark,top=trows,foot=frows,sc=sc))
    return out
if __name__=='__main__':
    with Pool(2) as pool: res=pool.map(work,range(len(R)),chunksize=4)
    flat=[p for o in res for p in o]
    json.dump(flat,open('/tmp/nc/pages.json','w'))
    print('paginas',len(flat))
