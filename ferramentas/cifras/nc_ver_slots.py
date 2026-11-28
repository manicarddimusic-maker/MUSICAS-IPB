"""Desenha os lugares de cifra conhecidos de uma página do hinário (para completar à mão o que falta)."""
import sys,cv2,json
sys.path.insert(0,'/tmp/cif')
import nc_slots
def ver(pg,out,y0=0,y1=None,larg=1800):
    e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png'); s=nc_slots.slots(pg)
    for o in s:
        cor=(0,160,0) if o['org']=='lida' and o['txt']!='?' else ((0,140,255) if o['org']=='lida' else (255,0,255))
        if o['org']=='manual': cor=(200,0,0)
        cv2.rectangle(e,(int(o['x']),int(o['base']-o['cap'])),(int(o['x']+o['w']),int(o['base'])),cor,2)
        cv2.putText(e,o['txt'],(int(o['x']),int(o['base']+1.25*o['cap'])),cv2.FONT_HERSHEY_SIMPLEX,0.6,(200,0,0),2)
    H,W=e.shape[:2]
    # régua
    for x in range(0,W,100): cv2.putText(e,str(x),(x,14),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,255),1); cv2.line(e,(x,16),(x,26),(0,0,255),1)
    for y in range(0,H,100): cv2.putText(e,str(y),(2,y+4),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,255),1); cv2.line(e,(0,y),(14,y),(0,0,255),1)
    e=e[y0:y1 or H]
    sc=larg/W
    cv2.imwrite(out,cv2.resize(e,None,fx=sc,fy=sc,interpolation=cv2.INTER_AREA if sc<1 else cv2.INTER_CUBIC),[1,85]); print(pg,(H,W),len(s),'escala',round(sc,3))
if __name__=='__main__':
    pg=int(sys.argv[1]); ver(pg,sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 0,int(sys.argv[4]) if len(sys.argv)>4 else None)
