import sys,json,os,subprocess,time,shutil
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from ncocr import *
pg=int(sys.argv[1])
b=cv2.imread(f'/tmp/cif/dbg/base{pg}.png',0); e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
d=espaco_pauta(e); toks,lab,cap=candidatos(b,d)
sel=[t for t in toks if t['cap']>=1.0*cap and t['sw']>=0.215*cap]
sel.sort(key=lambda t:(round(t['base']/(4*cap)),t['x0']))
print(len(sel),'tokens')
def recorte(img,t,H,pad_rel=0.5,mask=True,binar=False):
    pad=int(pad_rel*t['cap'])+2
    x0,y0=max(0,t['x0']-pad),max(0,t['y0']-pad); x1,y1=min(img.shape[1],t['x1']+pad),min(img.shape[0],t['y1']+pad)
    g=img[y0:y1,x0:x1].copy()
    if mask:
        ids=np.array([c['id'] for c in t['cs']]); m=np.isin(lab[y0:y1,x0:x1],ids).astype(np.uint8)
        m=cv2.dilate(m,np.ones((7,7),np.uint8)); g=np.where(m>0,g,255).astype(np.uint8)
    k=H/t['cap']; g=cv2.resize(g,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
    if binar: g=cv2.threshold(cv2.GaussianBlur(g,(0,0),1.0),150,255,cv2.THRESH_BINARY)[1]
    return cv2.copyMakeBorder(g,12,12,12,12,cv2.BORDER_CONSTANT,value=255)
def lote(imgs,psm,wl=True,oem=None):
    dd='/tmp/cif/dbg/lote'; shutil.rmtree(dd,ignore_errors=True); os.makedirs(dd)
    for i,g in enumerate(imgs): cv2.imwrite(f'{dd}/{i:04d}.png',g)
    open(dd+'/l.txt','w').write('\n'.join(f'{dd}/{i:04d}.png' for i in range(len(imgs))))
    cmd=['tesseract',dd+'/l.txt','-','-l','eng','--psm',str(psm)]
    if oem is not None: cmd+=['--oem',str(oem)]
    if wl: cmd+=['-c','tessedit_char_whitelist='+WL]
    cmd+=['tsv']
    t0=time.time(); r=subprocess.run(cmd,capture_output=True,text=True).stdout; dt=time.time()-t0
    out=[('',0.0)]*len(imgs)
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        i=int(c[1])-1; a=out[i]; out[i]=(a[0]+c[11].strip(),min(a[1] or 100,float(c[10])))
    return out,dt
res={}
for nome,img,H,binar,psm in (('base48',b,48,False,8),('base48p7',b,48,False,7),('enh48',e,48,False,8),('bin56',b,56,True,8),('base36',b,36,False,8),('base48p13',b,48,False,13)):
    res[nome],dt=lote([recorte(img,t,H,binar=binar) for t in sel],psm); print(nome,'%.1fs'%dt)
ks=list(res)
print('     x  base | '+' | '.join(f'{k:14s}' for k in ks))
for i,t in enumerate(sel):
    print(f"{t['x0']:5d} {t['base']:5d} | "+' | '.join(f"{res[k][i][0][:10]:10s}{res[k][i][1]:4.0f}" for k in ks))
