import cv2,numpy as np,json,itertools,sys
from enh import enhance
_cache={}
orb=cv2.ORB_create(3000)
def feat(name):
    if name not in _cache:
        g=cv2.imread(f'/tmp/nc/pgs/{name}.png',0); e=enhance(g)
        s=1100/e.shape[0]; e=cv2.resize(e,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
        e=cv2.GaussianBlur(e,(0,0),1.2)
        mask=np.zeros(e.shape,np.uint8); mask[int(e.shape[0]*0.2):int(e.shape[0]*0.93)]=255
        _cache[name]=orb.detectAndCompute(e,mask)
    return _cache[name]
bf=cv2.BFMatcher(cv2.NORM_HAMMING)
def same(a,b):
    ka,da=feat(a); kb,db=feat(b)
    if da is None or db is None or len(ka)<20 or len(kb)<20: return 0
    m=bf.knnMatch(da,db,k=2)
    good=[x for x,y in (p for p in m if len(p)==2) if x.distance<0.78*y.distance]
    if len(good)<12: return len(good)*0
    src=np.float32([ka[g.queryIdx].pt for g in good]); dst=np.float32([kb[g.trainIdx].pt for g in good])
    H,mask=cv2.findHomography(src,dst,cv2.RANSAC,8.0)
    if H is None: return 0
    # homografia plausível (sem inversão/escala absurda)
    det=np.linalg.det(H[:2,:2])
    if not (0.4<det<2.5): return 0
    return int(mask.sum())
if __name__=='__main__':
    D=json.load(open('/tmp/nc/ident4.json'))
    by={d['name']:d for d in D}
    tests=[('a011S','a012S'),('a018S','a019L'),('a063S','a064L'),('a042L','a043S'),('a043S','a044S'),('d017R','d018S'),('d018S','d019S'),('a077S','a080S'),('a000S','a001S'),('a003S','a004S'),('c153R','c154S'),('b099S','b100S'),('a025S','a026S'),('c108L','e001L'),('b113L','e000S')]
    for a,b in tests: print(a,b,same(a,b))
