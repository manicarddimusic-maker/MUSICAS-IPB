import json,cv2,numpy as np,sys
from multiprocessing import Pool
B=json.load(open('/tmp/nc/big.json'))
R=json.load(open('/tmp/nc/ocr2.json'))
t0=cv2.imread(B['a'][0],0)[603:747,226:294]
def prep(g,maxdim=1500):
    s=maxdim/max(g.shape); return cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_AREA),s
def staffdir(g):
    bw=(g<140).astype(np.uint8)
    L=int(0.15*min(g.shape))
    h=cv2.morphologyEx(bw,cv2.MORPH_OPEN,np.ones((1,L),np.uint8)).sum()
    v=cv2.morphologyEx(bw,cv2.MORPH_OPEN,np.ones((L,1),np.uint8)).sum()
    return h,v
def clef(g,s):
    best=0
    for k in (0.6,0.7,0.8,0.9,1.0,1.12):
        t=cv2.resize(t0,None,fx=s*k,fy=s*k,interpolation=cv2.INTER_AREA)
        if t.shape[0]<12: continue
        m=cv2.matchTemplate(g,t,cv2.TM_CCOEFF_NORMED)
        # media dos 3 maiores picos separados
        vals=[]
        mm=m.copy()
        for _ in range(3):
            _,mx,_,loc=cv2.minMaxLoc(mm); vals.append(mx)
            x,y=loc; cv2.rectangle(mm,(max(0,x-t.shape[1]),max(0,y-t.shape[0])),(x+t.shape[1],y+t.shape[0]),-1,-1)
        best=max(best,float(np.mean(vals)))
    return best
def rot(g,ang):
    if ang==0: return g
    if ang==-90: return cv2.rotate(g,cv2.ROTATE_90_CLOCKWISE)
    if ang==90: return cv2.rotate(g,cv2.ROTATE_90_COUNTERCLOCKWISE)
    return cv2.rotate(g,cv2.ROTATE_180)
def work(k):
    r=R[k]; g=cv2.imread(r['p'],0); g,s=prep(g)
    h,v=staffdir(g)
    cands=(0,180) if h>=v else (-90,90)
    sc={a:clef(rot(g,a),s) for a in cands}
    return dict(f=r['f'],i=r['i'],h=int(h),v=int(v),clef=sc,ocr_rot=r['rot'],ocr_score=r['score'])
if __name__=='__main__':
    with Pool(2) as p: res=p.map(work,range(len(R)),chunksize=8)
    json.dump(res,open('/tmp/nc/orient.json','w'))
    dis=0;low=0
    for x in res:
        best=max(x['clef'],key=lambda a:x['clef'][a]); x['best']=best
        vals=sorted(x['clef'].values()); margin=vals[-1]-vals[0]
        if x['ocr_score']>=40 and best!=x['ocr_rot']: dis+=1; print('DISAGREE',x)
        if margin<0.08: low+=1; print('lowmargin',x)
    print('disagree',dis,'lowmargin',low)
