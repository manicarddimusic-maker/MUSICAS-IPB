"""Põe as páginas novas (fotos de 28/11) no lugar das antigas em /tmp/nc/final e atualiza o índice de páginas."""
import sys,os,json,glob,shutil
import cv2,numpy as np
ANT='/tmp/nc/final_antes/'; FIN='/tmp/nc/final/'
P=json.load(open(ANT+'paginas.json'))
COMP={r['pg']:r for r in json.load(open('/tmp/nn/completar.json'))}
MUSICA=(554,572,576,488,376,176,276,462)       # páginas em que a foto cortou a última pauta (completadas com a antiga)
n=0
for a in sorted(glob.glob('/tmp/nn/pagf/p???.png')):
    pg=int(os.path.basename(a)[1:4]); j=json.load(open(f'/tmp/nn/pag/p{pg:03d}.json'))
    im=cv2.imread(a,0); cv2.imwrite(f'{FIN}p{pg:03d}.png',im)
    ant=P.get(str(pg))
    d=dict(src='nf%02d_%d'%(j['i'],j['k']),role=j['papel'],hymn=j['rot'],version=ant['version'] if ant else 0,q=30000.0,staff=0.02,
           cls='media' if pg in MUSICA else 'boa',w=int(im.shape[1]),h=int(im.shape[0]),ang=0.0,lavada=False,vis=0.02,
           alts=([ant['src']]+ant.get('alts',[])) if ant else [],ver=1 if ant else 0,
           completada=bool(COMP.get(pg,{}).get('feito')),musica_cortada=pg in MUSICA,
           geo=dict(yz=j['yz'],x0=j['x0'],topo=j['topo'],fim=j['fim'],d=14.545454545,pautas=j['Yp']))
    if ant: assert ant['role']==j['papel'] and ant['hymn']==j['rot'],(pg,ant['role'],ant['hymn'],j['papel'],j['rot'])
    P[str(pg)]=d; n+=1
P=dict(sorted(P.items(),key=lambda kv:int(kv[0])))
json.dump(P,open(FIN+'paginas.json','w'),ensure_ascii=False,indent=0)
import collections
print(n,'páginas novas;',len(P),'páginas ao todo;',collections.Counter(v['cls'] for v in P.values()))
print('faltam no intervalo:',[i for i in range(1,625) if str(i) not in P])
