import json,cv2,numpy as np,sys,re
from enh import enhance
from chordocr import *
B=json.load(open('/tmp/nc/big.json'))
f,i=sys.argv[1],int(sys.argv[2])
g=cv2.imread(B[f][i],0); e=enhance(g)
cap,rows,s=estimate_cap(e); print('cap',cap)
comps,lab=components(e,cap)
bold=[c for c in comps if c['sw']>=0.165*cap and 0.7*cap<=c['h']<=1.5*cap]
toks=group_tokens([c for c in comps if c['sw']>=0.15*cap],cap)
# palavra candidata: tem ao menos um glifo "negrito alto" e altura ~cap
cands=[t for t in toks if any(c in bold for c in t['cs']) and 0.8*cap<=t['y1']-t['y0']<=1.6*cap]
print(len(toks),'tokens',len(cands),'cands')
res=[]
for t in cands:
    pad=int(0.35*cap)
    x0,y0,x1,y1=max(0,t['x0']-pad),max(0,t['y0']-pad),min(e.shape[1],t['x1']+pad),min(e.shape[0],t['y1']+pad)
    crop=e[y0:y1,x0:x1]
    sc=60/ (t['y1']-t['y0'])
    crop=cv2.resize(crop,None,fx=sc,fy=sc,interpolation=cv2.INTER_CUBIC)
    crop=cv2.copyMakeBorder(crop,20,20,20,20,cv2.BORDER_CONSTANT,value=255)
    outs=[]
    for psm,lang,wl in ((8,'eng',WL),(7,'eng',WL),(8,'eng',None)):
        w=tess_words(crop,psm,lang,wl)
        outs.append((''.join(x['t'] for x in w), min([x['conf'] for x in w],default=0)))
    t['ocr']=outs
    res.append(t)
res.sort(key=lambda t:(round(t['y0']/ (2.5*cap)),t['x0']))
for t in res:
    ok=[bool(CH.match(o[0])) for o in t['ocr']]
    print(t['x0'],t['y0'],t['x1']-t['x0'],t['y1']-t['y0'],t['ocr'],'OK' if any(ok) else '--')
