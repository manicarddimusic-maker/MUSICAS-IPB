"""Recortes ampliados só dos pontos duvidosos de cada folha (marcas "?" e tinta de caneta que sobrou sem cifra),
com as coordenadas da imagem de conferência escritas, para corrigir rápido."""
import sys,json,glob,os,re
import cv2,numpy as np
R='/home/claude/musicas-ipb/public'
J=json.load(open(R+'/data/cifras/hinos.json'))['folhas']
def um(nome):
    conf=cv2.imread(f'/tmp/cif/hfin/conf_{nome}.jpg')
    if conf is None: return None
    # pontos: vermelho forte (marcas "?" e riscos livres) na imagem de conferência
    b,g,r=[conf[...,i].astype(int) for i in range(3)]
    m=((r>200)&(g<60)&(b<60)).astype(np.uint8)
    m=cv2.dilate(m,np.ones((25,45),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
    recs=[]
    for i in range(1,n):
        x,y,w,h,a=[int(v) for v in st[i]]
        if a<300: continue
        x0=max(0,x-130); y0=max(0,y-95); x1=min(conf.shape[1],x+w+130); y1=min(conf.shape[0],y+h+60)
        c=cv2.resize(conf[y0:y1,x0:x1],None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
        cv2.putText(c,f'{x0},{y0}',(3,14),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,0),3); cv2.putText(c,f'{x0},{y0}',(3,14),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,255,255),1)
        # régua de x a cada 50
        for xx in range((x0//50+1)*50,x1,50):
            px=(xx-x0)*2; cv2.line(c,(px,c.shape[0]-8),(px,c.shape[0]),(0,0,0),1); cv2.putText(c,str(xx),(px+2,c.shape[0]-2),cv2.FONT_HERSHEY_SIMPLEX,0.33,(0,0,0),1)
        for yy in range((y0//50+1)*50,y1,50):
            py=(yy-y0)*2; cv2.line(c,(0,py),(8,py),(0,0,0),1); cv2.putText(c,str(yy),(10,py+4),cv2.FONT_HERSHEY_SIMPLEX,0.33,(0,0,0),1)
        recs.append(c)
    if not recs: return 0
    # monta em colunas
    W=1850; linhas=[]; cur=[]; larg=0
    for c in recs:
        if larg+c.shape[1]>W and cur: linhas.append(cur); cur=[]; larg=0
        cur.append(c); larg+=c.shape[1]+6
    if cur: linhas.append(cur)
    tiras=[]
    for ln in linhas:
        h=max(c.shape[0] for c in ln)
        t=np.hstack([cv2.copyMakeBorder(c,0,h-c.shape[0],0,6,cv2.BORDER_CONSTANT,value=(255,255,255)) for c in ln])
        tiras.append(cv2.copyMakeBorder(t,0,6,0,max(0,W-t.shape[1]),cv2.BORDER_CONSTANT,value=(255,255,255))[:, :W])
    im=np.vstack(tiras); cv2.imwrite(f'/tmp/cif/hfin/prob_{nome}.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,86])
    return len(recs),im.shape[:2]
if __name__=='__main__':
    ns=sorted(os.path.basename(f)[5:-4] for f in glob.glob('/tmp/cif/hfin/conf_*.jpg'))
    if len(sys.argv)>1: ns=[n for n in ns if any(n.startswith(a) for a in sys.argv[1:])]
    for n in ns: print(n[:22],um(n))
