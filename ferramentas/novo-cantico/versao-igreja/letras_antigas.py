"""Letra impressa na página do 111: linhas, palavras (sílabas) e hifens de cada sistema."""
import sys
sys.path.insert(0,'/tmp/ig'); sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from base import carregar,sistemas,componentes
BASES=None
def linhas(e,S,d,lim=150):
    """-> lista de 4 linhas; cada linha = dict(base, xh, toks=[dict(x0,x1,y0,y1,comps)], hifens=[...], comps=[todos])"""
    y0=int(S['sol4']+0.3*d); y1=int(S['fa0']-0.3*d)
    bw=(e[y0:y1]<lim)
    n,lab,st=componentes(bw)
    cx=[]
    for i in range(1,n):
        x,y,w,h,a=[int(v) for v in st[i]]
        if h>2.6*d or w>12*d: continue
        if y<=1 or y+h>=(y1-y0)-1: continue
        cx.append(dict(x0=x,y0=y+y0,x1=x+w,y1=y+y0+h,a=a,i=i))
    letras=[c for c in cx if 0.75*d<=c['y1']-c['y0']<=2.4*d]
    pes=np.array([c['y1'] for c in letras]); hist=np.bincount(pes,minlength=y1+2)
    sm=np.convolve(hist,np.ones(3),'same'); bases=[]
    for y in np.argsort(-sm):
        if sm[y]<4: break
        if all(abs(y-c)>1.2*d for c in bases): bases.append(int(y))
    bases=sorted(bases)[:4]
    out=[]
    for b in bases:
        xh=15.0
        meus=[c for c in cx if b-1.75*xh<=(c['y0']+c['y1'])/2<=b+0.55*xh and c['y1']<=b+0.75*xh and c['y0']>=b-2.1*xh]
        hif=[c for c in meus if c['y1']-c['y0']<=0.33*xh and c['x1']-c['x0']>=0.3*xh and b-0.75*xh<=(c['y0']+c['y1'])/2<=b-0.2*xh]
        ids={id(h) for h in hif}
        resto=sorted([c for c in meus if id(c) not in ids],key=lambda c:c['x0'])
        toks=[]
        for c in resto:
            if toks and c['x0']-toks[-1]['x1']<=9: 
                t=toks[-1]; t['x1']=max(t['x1'],c['x1']); t['y0']=min(t['y0'],c['y0']); t['y1']=max(t['y1'],c['y1']); t['comps'].append(c)
            else: toks.append(dict(x0=c['x0'],x1=c['x1'],y0=c['y0'],y1=c['y1'],comps=[c]))
        # hífen isolado que sobrou como "palavra" (traço) não conta
        out.append(dict(base=b,xh=xh,toks=toks,hifens=hif,comps=meus))
    return out,(y0,y1),lab
if __name__=='__main__':
    e,P,d=carregar(); vis=cv2.cvtColor(e,cv2.COLOR_GRAY2BGR)
    for k,S in enumerate(sistemas(e,P,d)):
        L,(y0,y1),lab=linhas(e,S,d)
        for r,l in enumerate(L):
            print('sistema',k,'linha',r,'base',l['base'],'palavras',len(l['toks']),'hifens',len(l['hifens']),'| x0..x1:',[(t['x0'],t['x1']) for t in l['toks']])
            for t in l['toks']: cv2.rectangle(vis,(t['x0']-1,t['y0']-1),(t['x1'],t['y1']),(0,0,255),1)
            for h in l['hifens']: cv2.rectangle(vis,(h['x0']-1,h['y0']-1),(h['x1'],h['y1']),(0,160,0),1)
    cv2.imwrite('/tmp/ig/vis/toks.png',vis[490:1260])
