import cv2,numpy as np
def enhance(g, strength=1.0):
    """g: uint8 cinza. Achata a iluminação e escurece traços fracos."""
    h,w=g.shape
    # fundo: fechamento morfológico numa versão reduzida
    s=600/max(h,w)
    small=cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    k=max(9,int(0.03*600)|1)
    bg=cv2.morphologyEx(small,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    bg=cv2.GaussianBlur(bg,(0,0),6)
    bg=cv2.resize(bg,(w,h),interpolation=cv2.INTER_LINEAR).astype(np.float32)
    n=np.clip(g.astype(np.float32)/np.maximum(bg,1)*255,0,255)
    # ponto preto: percentil escuro dos traços
    ink=n[n<235]
    lo=float(np.percentile(ink,2)) if ink.size>1000 else 60.
    lo=min(lo,150.)
    hi=240.
    v=np.clip((n-lo)/(hi-lo),0,1)
    gamma=1.0+0.9*strength
    v=v**gamma
    return (v*255+0.5).astype(np.uint8)
if __name__=='__main__':
    import json,sys
    B=json.load(open('/tmp/nc/big.json'))
    for f,i,box in (('a',11,(100,300,1100,1100)),('a',2,(100,300,1300,1100)),('c',108,(0,0,1500,1000))):
        g=cv2.imread(B[f][i],0)
        e=enhance(g)
        x0,y0,x1,y1=box
        both=np.vstack([g[y0:y1,x0:x1],e[y0:y1,x0:x1]])
        cv2.imwrite(f'/tmp/nc/enh_{f}{i}.jpg',both,[cv2.IMWRITE_JPEG_QUALITY,85])
        print(f,i,g.shape)
