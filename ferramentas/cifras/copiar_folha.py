"""Fotos repetidas da MESMA folha: copia as cifras (e borrachas) já conferidas de uma foto para a outra,
pelo registro entre as duas fotos. Rodar DEPOIS de hfin_d.py.   uso: copiar_folha.py [conferir]"""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from registro import _feats,casar_pontos,Registro,girar_para_cima
R='/home/claude/musicas-ipb/public'
GIRO={90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}
COPIAS={   # destino: origem  (a origem é a foto conferida; as duas são fotos da mesma folha, com a mesma letra à mão)
 '/midias/h297_3e1f37e4.jpg':'/midias/h297_6452_6140ba36.jpg',
 '/midias/h027_9942c626.jpg':'/midias/h027_6437_e0f6084c.jpg',
 '/midias/h028_73e79a49.jpg':'/midias/h028_6446_1d462d48.jpg',
 '/midias/h042_6378_c76ab491.jpg':'/midias/h042_6408_637ef86e.jpg',
 '/midias/h064_6451_0330d1a4.jpg':'/midias/h064_d0d20ca2.jpg',
 '/midias/h088b_82c9f21b.jpg':'/midias/h088_6352_a38b397e.jpg',
 '/midias/h110_a21c6fce.jpg':'/midias/h110_6435_16f046d4.jpg',
 '/midias/h120_1d7a266d.jpg':'/midias/h120_6425_c6e51d32.jpg',
 '/midias/h133_9c1ed220.jpg':'/midias/h133_6351_9833328f.jpg',
 '/midias/h172_6438_14867793.jpg':'/midias/h172_2858fca2.jpg',
 '/midias/h288_6442_c930dc48.jpg':'/midias/h288_9d0be71a.jpg',
 '/midias/h340_b1047d39.jpg':'/midias/h340_6439_eb270fc3.jpg',
 '/midias/h352_6383_ad0dda8b.jpg':'/midias/h352_6477_0d9e1450.jpg',
}
def papel(cor,x0,y0,x1,y1):
    a=cor[max(0,int(y0)-4):int(y1)+4,max(0,int(x0)-4):int(x1)+4].reshape(-1,3)
    if len(a)==0: return 'ffffff'
    sm=a.sum(axis=1); cl=a[sm>=np.percentile(sm,70)]
    return '%02x%02x%02x'%tuple(int(v) for v in np.median(cl,axis=0)[::-1])
def copiar(src,dst,J):
    FA=J['folhas'][src]; A=cv2.imread(R+src); B=cv2.imread(R+dst)
    if FA.get('r'): A=cv2.rotate(A,GIRO[FA['r']])
    Ag=cv2.cvtColor(A,cv2.COLOR_BGR2GRAY); Bg=cv2.cvtColor(B,cv2.COLOR_BGR2GRAY)
    fa=_feats(Ag,2400); S,D=casar_pontos(fa,_feats(Bg,2400)); Rg=Registro(S,D)
    if Rg.n<40: return None,Rg.n
    Bg2,giro=girar_para_cima(Bg,Rg.ang); Bup=cv2.rotate(B,GIRO[giro]) if giro else B
    if giro: S,D=casar_pontos(fa,_feats(Bg2,2400)); Rg=Registro(S,D)
    H,W=Bup.shape[:2]; out=[]; fora=0
    for c in FA['c']:
        x,base,w,fs,txt=c[:5]
        if txt=='':
            h=c[7]; M,n=Rg.local(x+w/2,base-h/2,raio=160)
            if M is None: fora+=1; continue
            pts=np.float64([[x,base-h],[x+w,base-h],[x,base],[x+w,base]]); q=(M[:,:2]@pts.T).T+M[:,2]
            x0,y0=q.min(axis=0); x1,y1=q.max(axis=0)
            if x1<0 or y1<0 or x0>W or y0>H: fora+=1; continue
            x0=max(0,x0); y0=max(0,y0); x1=min(W,x1); y1=min(H,y1)
            out.append([int(x0),int(round(y1)),int(round(x1-x0)),10,'',papel(Bup,x0,y0,x1,y1),0,int(round(y1-y0)),0])
        else:
            M,n=Rg.local(x+w/2,base-0.35*fs,raio=max(160.0,9*fs))
            if M is None: fora+=1; continue
            e=float(np.hypot(M[0,0],M[1,0])); q=M[:,:2]@np.float64([x,base])+M[:,2]
            if q[0]<-0.2*w*e or q[1]<0 or q[0]+0.6*w*e>W or q[1]>H: fora+=1; continue
            sobe=(c[7] if len(c)>7 and c[7] else 0.82*fs)*e; desce=(c[8] if len(c)>8 and c[8] else 0.08*fs)*e
            bg=papel(Bup,q[0],q[1]-sobe,q[0]+w*e,q[1]+desce) if txt!='?' else 0
            out.append([int(round(q[0])),int(round(q[1])),int(round(w*e)),round(fs*e,1),txt,bg,0,int(round(sobe)),int(round(desce))])
    F=dict(w=B.shape[1],h=B.shape[0],f=FA.get('f','s'),c=out)
    for k in ('k','n','q'):
        if FA.get(k): F[k]=FA[k]
    if giro: F['r']=giro
    return F,dict(inl=Rg.n,copiadas=sum(1 for c in out if c[4]!=''),borr=sum(1 for c in out if c[4]==''),fora=fora,giro=giro)
if __name__=='__main__':
    fn=R+'/data/cifras/hinos.json'; J=json.load(open(fn))
    so=sys.argv[2:] if len(sys.argv)>2 else None
    for dst,src in COPIAS.items():
        if so and not any(p in dst for p in so): continue
        if src not in J['folhas'] or not os.path.exists(R+dst): print('falta',src,dst); continue
        F,rel=copiar(src,dst,J)
        print(os.path.basename(dst),'<-',os.path.basename(src),rel)
        if F is None: continue
        J['folhas'][dst]=F
        if len(sys.argv)>1:
            B=cv2.imread(R+dst)
            if F.get('r'): B=cv2.rotate(B,GIRO[F['r']])
            for c in F['c']:
                if c[4]=='': cv2.rectangle(B,(c[0],c[1]-c[7]),(c[0]+c[2],c[1]),(120,200,120),1)
            for c in F['c']:
                if c[4]=='': continue
                cor=(255,60,0) if c[4]!='?' else (0,0,255)
                cv2.putText(B,c[4],(c[0],int(c[1]+1.25*c[3])),cv2.FONT_HERSHEY_SIMPLEX,max(0.5,c[3]/38),cor,2,cv2.LINE_AA); cv2.line(B,(c[0],c[1]+3),(c[0]+c[2],c[1]+3),cor,2)
            s=1800/max(B.shape[:2]); cv2.imwrite('/tmp/cif/hfin/conf_'+os.path.basename(dst)[:-4]+'.jpg',cv2.resize(B,None,fx=s,fy=s,interpolation=cv2.INTER_AREA),[1,84])
    json.dump(J,open(fn,'w'),ensure_ascii=False,separators=(',',':'))
