import sys,json,os,subprocess,time
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nc')
import cv2,numpy as np
from pageproc import process
from ncocr import *
P={int(k):v for k,v in json.load(open('/tmp/nc/final/paginas.json')).items()}
D={d['name']:d for d in json.load(open('/tmp/nc/ident6.json'))}
pg=int(sys.argv[1]); src=P[pg]['src']
b,info=process(src,D[src]['sharp'],D[src]['staff'],so_base=True)
b=np.clip(b,0,255).astype(np.uint8)
e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
print(b.shape,e.shape)
cv2.imwrite(f'/tmp/cif/dbg/base{pg}.png',b)
d=espaco_pauta(e); cap=1.7*d
toks,lab,cap=candidatos(b,d)
print('candidatos na base:',len(toks))
import collections
for t in sorted(toks,key=lambda t:(round(t['base']/(2.2*cap)),t['x0']))[:60]:
    print(t['x0'],t['base'],'cap',t['cap'],'sw %.2f'%(t['sw']/cap),'n',len(t['cs']),'w',t['x1']-t['x0'])
