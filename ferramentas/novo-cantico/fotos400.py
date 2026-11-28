import cv2,numpy as np
from enh import enhance
def proc(path,out):
    im=cv2.imread(path); hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    paper=((hsv[...,2]>135)&(hsv[...,1]<70)).astype(np.uint8)
    paper=cv2.morphologyEx(paper,cv2.MORPH_CLOSE,np.ones((41,41),np.uint8))
    paper=cv2.morphologyEx(paper,cv2.MORPH_OPEN,np.ones((61,61),np.uint8))
    n,lab,st,cen=cv2.connectedComponentsWithStats(paper,8)
    k=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); mask=(lab==k).astype(np.uint8)
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    # fora do papel vira branco (com borda suave)
    m=cv2.erode(mask,np.ones((15,15),np.uint8))
    g2=g.copy(); g2[m==0]=255
    # fundo local estimado só dentro do papel
    e=enhance(np.where(m>0,g,np.uint8(np.median(g[m>0]))).astype(np.uint8))
    e[m==0]=255
    # inclinação pelas linhas da pauta
    bw=(e<120).astype(np.uint8)*255
    lines=cv2.HoughLinesP(bw,1,np.pi/1800,threshold=300,minLineLength=e.shape[1]//3,maxLineGap=12)
    angs=[]
    if lines is not None:
        for x1,y1,x2,y2 in lines.reshape(-1,4):
            a=np.degrees(np.arctan2(y2-y1,x2-x1))
            if abs(a)<8: angs.append(a)
    ang=float(np.median(angs)) if angs else 0.0
    h,w=e.shape
    M=cv2.getRotationMatrix2D((w/2,h/2),ang,1.0)
    e=cv2.warpAffine(e,M,(w,h),flags=cv2.INTER_CUBIC,borderValue=255)
    ink=(e<140)
    ys=np.where(ink.sum(axis=1)>3)[0]; xs=np.where(ink.sum(axis=0)>3)[0]
    y0,y1,x0,x1=ys[0],ys[-1],xs[0],xs[-1]
    pad=int(0.035*w)
    y0=max(0,y0-pad); y1=min(h,y1+pad); x0=max(0,x0-pad); x1=min(w,x1+pad)
    e=e[y0:y1,x0:x1]
    cv2.imwrite(out,e); print(out,e.shape,'ang',round(ang,2),len(angs))
proc('/mnt/user-data/uploads/251bf961-image.jpg','/tmp/nc/f400a.png')
proc('/mnt/user-data/uploads/752b9970-image.jpg','/tmp/nc/f400b.png')
a=cv2.imread('/tmp/nc/f400a.png',0); b=cv2.imread('/tmp/nc/f400b.png',0)
H=900
t=[cv2.resize(x,(int(x.shape[1]*H/x.shape[0]),H)) for x in (a,b)]
cv2.imwrite('/tmp/nc/f400_prev.jpg',np.hstack([t[0],np.full((H,20),128,np.uint8),t[1]]),[cv2.IMWRITE_JPEG_QUALITY,80])
