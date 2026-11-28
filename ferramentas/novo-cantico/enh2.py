import cv2,numpy as np
def flatten(g):
    """divide pela iluminação de fundo (tira sombras), papel ~ 255"""
    h,w=g.shape; s=700/max(h,w)
    small=cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    k=int(0.035*700)|1
    bg=cv2.morphologyEx(small,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    bg=cv2.GaussianBlur(bg,(0,0),7)
    bg=cv2.resize(bg,(w,h),interpolation=cv2.INTER_LINEAR).astype(np.float32)
    return np.clip(g.astype(np.float32)/np.maximum(bg,1)*255,0,255)
def enhance_final(g):
    """imagem final para leitura: papel branco, tinta preta, sem realçar o verso da folha"""
    n=flatten(g)
    ink=n[n<200]
    p=float(np.percentile(ink,3)) if ink.size>2000 else 60.
    if p<95:       # tinta forte
        lo=max(25.,p*0.8); hi=208.; gamma=1.15
    elif p<140:    # tinta média
        lo=p*0.8; hi=222.; gamma=1.35
    else:          # página apagada
        lo=p*0.85; hi=min(246.,p+0.8*(255-p)); gamma=1.7
    v=np.clip((n-lo)/(hi-lo),0,1)**gamma
    return (v*255+0.5).astype(np.uint8),p
if __name__=='__main__':
    import json
    B=json.load(open('/tmp/nc/big.json'))
    tiles=[]
    for src,box in (('/tmp/nc/pgs/a000S.png',(200,480,1200,1080)),('/tmp/nc/pgs/a002L.png',(100,480,1100,1080)),('/tmp/nc/pgs/c051L.png',(100,480,1100,1080)),('/tmp/nc/pgs/c074L.png',(100,480,1100,1080)),('/tmp/nc/pgs/b039L.png',(100,480,1100,1080))):
        g=cv2.imread(src,0); e,p=enhance_final(g); x0,y0,x1,y1=box
        print(src,g.shape,'p',round(p))
        tiles.append(np.hstack([g[y0:y1,x0:x1],e[y0:y1,x0:x1]]))
    cv2.imwrite('/tmp/nc/enh2_test.jpg',np.vstack(tiles),[cv2.IMWRITE_JPEG_QUALITY,80])
