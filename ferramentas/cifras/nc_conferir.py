"""Tiras de conferência: cada linha de cifras de uma página, com a leitura final escrita embaixo de cada cifra."""
import sys,json
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
FONTE='/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf'
def tiras(pg,R,esc=1.6):
    im=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0); c=sorted(R[str(pg)],key=lambda x:(x[1],x[0]))
    capm=float(np.median([x[3] for x in c])) if c else 22
    rows=[]
    for x in c:
        if rows and x[1]-np.median([q[1] for q in rows[-1]])<0.6*capm: rows[-1].append(x)
        else: rows.append([x])
    out=[]
    for rw in rows:
        b=int(np.median([x[1] for x in rw])); y0=max(0,b-int(1.5*capm)); y1=min(im.shape[0],b+int(0.45*capm))
        s=cv2.resize(im[y0:y1,:],None,fx=esc,fy=esc,interpolation=cv2.INTER_CUBIC)
        H=s.shape[0]+int(30*esc/1.6)+6
        t=Image.new('RGB',(s.shape[1],H),(255,255,255)); t.paste(Image.fromarray(s).convert('RGB'),(0,0))
        dr=ImageDraw.Draw(t); f=ImageFont.truetype(FONTE,int(22*esc/1.6)+4)
        for x in sorted(rw):
            dr.text((int(x[0]*esc),s.shape[0]+1),x[4],fill=(0,60,220) if x[4]!='?' else (220,0,0),font=f)
            dr.line([(int(x[0]*esc),s.shape[0]),(int((x[0]+x[2])*esc),s.shape[0])],fill=(230,0,0),width=2)
        dr.text((2,2),f'p{pg}',fill=(200,0,0),font=ImageFont.truetype(FONTE,16))
        dr.line([(0,H-1),(s.shape[1],H-1)],fill=(150,150,150),width=1)
        out.append(np.array(t)[:,:,::-1])
    return out
if __name__=='__main__':
    R=json.load(open('/tmp/cif/nc_palavras.json'))
    nome=sys.argv[1]; pgs=[int(a) for a in sys.argv[2:]]
    T=[]
    for pg in pgs: T+=tiras(pg,R)
    por=14
    for n0 in range(0,len(T),por):
        cv2.imwrite(f'/tmp/nn/vis/{nome}{n0//por}.png',np.vstack(T[n0:n0+por]))
    print(len(T),'tiras em',(len(T)+por-1)//por,'imagens')
