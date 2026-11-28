"""Funções comuns: imagem-base de uma página do hinário, candidatos a cifra, tesseract em lote."""
import sys,json,os,subprocess,shutil,re
sys.path.insert(0,'/tmp/cif'); sys.path.insert(0,'/tmp/nc')
import cv2,numpy as np
from ncocr import espaco_pauta,candidatos,WL
PAG={int(k):v for k,v in json.load(open('/tmp/nc/final/paginas.json')).items()}
IDENT={d['name']:d for d in json.load(open('/tmp/nc/ident6.json'))}
def base_da_pagina(pg):
    """imagem da página na mesma geometria de final/pNNN.png, sem o reforço dos traços finos"""
    fn=f'/tmp/cif/base/p{pg:03d}.png'
    if os.path.exists(fn): return cv2.imread(fn,0)
    from pageproc import process
    src=PAG[pg]['src']
    if src.startswith('n'):       # fotos novas (400-A): usa a própria página final
        b=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
    else:
        b,_=process(src,IDENT[src]['sharp'],IDENT[src]['staff'],so_base=True)
        b=np.clip(b,0,255).astype(np.uint8)
        e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
        if e is not None and e.shape!=b.shape: b=e        # página tratada de outro jeito (foto cinza): usa a final
    os.makedirs('/tmp/cif/base',exist_ok=True); cv2.imwrite(fn,b)
    return b
def recorte(img,lab,t,H=48,pad_rel=0.5):
    pad=int(pad_rel*t['cap'])+2
    x0,y0=max(0,t['x0']-pad),max(0,t['y0']-pad); x1,y1=min(img.shape[1],t['x1']+pad),min(img.shape[0],t['y1']+pad)
    ids=np.array([c['id'] for c in t['cs']]); m=np.isin(lab[y0:y1,x0:x1],ids).astype(np.uint8)
    m=cv2.dilate(m,np.ones((7,7),np.uint8)); g=np.where(m>0,img[y0:y1,x0:x1],255).astype(np.uint8)
    k=H/t['cap']; g=cv2.resize(g,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(g,12,12,12,12,cv2.BORDER_CONSTANT,value=255)
def lote(imgs,psm=7,tag='x'):
    dd=f'/tmp/cif/lote_{tag}_{os.getpid()}'; shutil.rmtree(dd,ignore_errors=True); os.makedirs(dd)
    for i,g in enumerate(imgs): cv2.imwrite(f'{dd}/{i:04d}.png',g)
    open(dd+'/l.txt','w').write('\n'.join(f'{dd}/{i:04d}.png' for i in range(len(imgs))))
    r=subprocess.run(['tesseract',dd+'/l.txt','-','-l','eng','--psm',str(psm),'-c','tessedit_char_whitelist='+WL,'tsv'],capture_output=True,text=True).stdout
    out=[('',0.0)]*len(imgs)
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        i=int(c[1])-1; a=out[i]; out[i]=(a[0]+c[11].strip(),min(a[1] or 100,float(c[10])))
    shutil.rmtree(dd,ignore_errors=True)
    return out
