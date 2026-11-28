import json,cv2,numpy as np
from multiprocessing import Pool
R=json.load(open('/tmp/nc/ocr2.json'))
def axis(g):
    s=800/max(g.shape); g=cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_AREA).astype(np.float32)
    def rough(a):
        # a: imagem; mede "rugosidade" do perfil de linhas em 8 faixas verticais
        H,W=a.shape; tot=0
        for k in range(8):
            st=a[:,k*W//8:(k+1)*W//8].mean(axis=1)
            d=np.abs(np.diff(st)); tot+=float((d**2).mean())
        return tot/8
    return rough(g),rough(g.T)
def work(k):
    r=R[k]; g=cv2.imread(r['p'],0)
    hr,vr=axis(g)
    return dict(f=r['f'],i=r['i'],hr=hr,vr=vr,ocr_rot=r['rot'],ocr_score=r['score'],shape=g.shape)
if __name__=='__main__':
    with Pool(2) as p: res=p.map(work,range(len(R)),chunksize=8)
    json.dump(res,open('/tmp/nc/orient2.json','w'))
    bad=0
    for x in res:
        ax='h' if x['hr']>=x['vr'] else 'v'
        exp='h' if x['ocr_rot'] in (0,180) else 'v'
        if x['ocr_score']>=40 and ax!=exp: bad+=1; print('DIS',x['f'],x['i'],round(x['hr'],1),round(x['vr'],1),x['ocr_rot'],x['ocr_score'])
    print('disagree',bad,'of',sum(1 for x in res if x['ocr_score']>=40))
    import collections
    print(collections.Counter(('h' if x['hr']>=x['vr'] else 'v', x['ocr_rot']) for x in res if x['ocr_score']<40))
    rat=sorted(max(x['hr'],x['vr'])/max(1e-6,min(x['hr'],x['vr'])) for x in res); print('ratios',[round(r,2) for r in rat[:12]],rat[len(rat)//2])
