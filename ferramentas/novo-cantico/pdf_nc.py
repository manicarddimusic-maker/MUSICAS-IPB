import cv2,numpy as np,json,io,img2pdf,os
from multiprocessing import Pool
from PIL import Image
P={int(k):v for k,v in json.load(open('/tmp/nc/final/paginas.json')).items()}
PW,PH=1100,1650
PAL=[0,0,0, 105,105,105, 188,188,188, 255,255,255]+[0]*(252*3)
def quant(a):
    out=np.full(a.shape,3,np.uint8); out[a<228]=2; out[a<150]=1; out[a<62]=0; return out
def work(pg):
    e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0); h,w=e.shape
    s=min(PW*0.97/w,PH*0.97/h)
    r=cv2.resize(e,(int(w*s),int(h*s)),interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
    tela=np.full((PH,PW),255,np.uint8)
    y0=(PH-r.shape[0])//2; x0=(PW-r.shape[1])//2
    tela[y0:y0+r.shape[0],x0:x0+r.shape[1]]=r
    im=Image.fromarray(quant(tela),mode='P'); im.putpalette(PAL)
    bio=io.BytesIO(); im.save(bio,format='PNG',optimize=True,bits=2)
    return pg,bio.getvalue(),dict(x0=x0,y0=y0,s=s)
if __name__=='__main__':
    pgs=sorted(P)
    with Pool(2) as p: res=p.map(work,pgs,chunksize=8)
    layout=img2pdf.get_layout_fun((img2pdf.in_to_pt(6),img2pdf.in_to_pt(9)))
    pdf=img2pdf.convert([r[1] for r in res],layout_fun=layout,title='Novo Cântico – Hinário Presbiteriano',author='')
    open('/tmp/nc/final/hinario-novo-cantico-v2.pdf','wb').write(pdf)
    json.dump({r[0]:r[2] for r in res},open('/tmp/nc/final/pdf_map.json','w'))
    print(len(res),'paginas;',round(len(pdf)/1e6,1),'MB')
