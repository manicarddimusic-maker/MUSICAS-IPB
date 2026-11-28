"""Palavras de uma linha de cifras de uma página do hinário, achadas pela tinta (para completar à mão o que a leitura não leu).
uso: nc_linha.py <pg> "x1,b1 x2,b2 [x3,b3...]"   (pontos por onde passa a linha de base das cifras)
Mostra as palavras numeradas; depois: nc_linha.py <pg> "<pontos>" "rot1 rot2 ..." grava em /tmp/cif/slots_extra/<pg>.txt
rótulos: texto da cifra impressa; "=X" literal (tom da caneta); "-" não é cifra; "." já está certa (não mexe); "x" só borracha"""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
import nc_slots
def palavras(pg,pts,cap=None,x0=None,x1=None,lim=150):
    e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0); H,W=e.shape
    r=nc_slots.lido(pg); cap=cap or (r['cap'] if r else 21.0)
    pts=sorted(pts); xs=np.array([p[0] for p in pts],float); bs=np.array([p[1] for p in pts],float)
    def base(x):
        # linha de base por trechos retos entre os pontos dados (segue a curva da folha); fora deles, continua reta
        if x<=xs[0]: return float(bs[0]+(bs[1]-bs[0])/(xs[1]-xs[0])*(x-xs[0]))
        if x>=xs[-1]: return float(bs[-1]+(bs[-1]-bs[-2])/(xs[-1]-xs[-2])*(x-xs[-1]))
        return float(np.interp(x,xs,bs))
    bw=(e<lim).astype(np.uint8)
    n,lab,st,cen=cv2.connectedComponentsWithStats(bw,8)
    comps=[]
    for i in range(1,n):
        x,y,w,h,a=[int(v) for v in st[i]]
        b=base(x+w/2)
        if (x0 is not None and x+w<x0) or (x1 is not None and x>x1): continue
        if y+h<b-1.45*cap or y>b+0.45*cap: continue          # fora da faixa
        if y+h>b+0.5*cap or y<b-1.6*cap: continue             # atravessa a faixa (haste de nota, barra)
        if h<0.18*cap and w<0.18*cap: continue                 # pontinho
        if w>6*cap: continue
        comps.append((x,y,x+w,y+h,a))
    comps.sort()
    ws=[]
    for c in comps:
        if ws and c[0]-ws[-1][2]<0.42*cap: ws[-1]=[min(ws[-1][0],c[0]),min(ws[-1][1],c[1]),max(ws[-1][2],c[2]),max(ws[-1][3],c[3]),ws[-1][4]+[c]]
        else: ws.append([c[0],c[1],c[2],c[3],[c]])
    out=[]
    for w in ws:
        altos=[c for c in w[4] if c[3]-c[1]>=0.7*cap]
        if not altos: continue
        if w[3]-w[1]>1.75*cap: continue
        pes=sorted(c[3] for c in altos); b=pes[len(pes)//2]
        out.append(dict(x=w[0],base=b,w=w[2]-w[0],y0=w[1],y1=w[3],cap=int(round(np.median([c[3]-c[1] for c in altos]))),cs=[list(c[:4]) for c in w[4]]))
    return out,e,cap
def partir(p,n):
    """parte uma palavra em n pedaços nos (n-1) maiores vãos entre as letras"""
    cs=sorted(p['cs']); vaos=sorted(((cs[i+1][0]-max(c[2] for c in cs[:i+1]),i) for i in range(len(cs)-1)),reverse=True)[:n-1]
    cortes=sorted(i for _,i in vaos); out=[]; ini=0
    for c in cortes+[len(cs)-1]:
        g=cs[ini:c+1]; ini=c+1
        if not g: continue
        altos=[q for q in g if q[3]-q[1]>=0.7*p['cap']] or g
        pes=sorted(q[3] for q in altos)
        out.append(dict(x=min(q[0] for q in g),base=pes[len(pes)//2],w=max(q[2] for q in g)-min(q[0] for q in g),y0=min(q[1] for q in g),y1=max(q[3] for q in g),cap=p['cap']))
    return out
def existente(sl,p,cap):
    for o in sl:
        if min(o['x']+o['w'],p['x']+p['w'])-max(o['x'],p['x'])>0 and abs(o['base']-p['base'])<0.8*cap: return o
    return None
if __name__=='__main__':
    pg=int(sys.argv[1]); pts=[tuple(float(v) for v in t.split(',')) for t in sys.argv[2].split()]
    LIM=int(os.environ.get('LIM','150'))
    ps,e,cap=palavras(pg,pts,lim=LIM)
    sl=[o for o in nc_slots.slots(pg,extra=False)]
    if len(sys.argv)>3:
        labs=sys.argv[3].split(); assert len(labs)==len(ps),f'{len(labs)} rótulos para {len(ps)} palavras'
        fn=f'/tmp/cif/slots_extra/{pg}.txt'; linhas=[]
        for p,l in zip(ps,labs):
            if l=='.': continue
            linhas.append(f"{p['x']} {p['base']} {p['w']} {p['cap']} {p['y0']} {p['y1']} {l}")
        open(fn,'a').write('\n'.join(linhas)+'\n'); print('gravado',len(linhas),'em',fn)
    else:
        vis=cv2.cvtColor(e,cv2.COLOR_GRAY2BGR)
        ya=int(min(p['y0'] for p in ps))-40; yb=int(max(p['y1'] for p in ps))+50
        for i,p in enumerate(ps):
            o=existente(sl,p,cap); cor=(0,160,0) if o and o['txt']!='?' else ((0,140,255) if o else (0,0,255))
            cv2.rectangle(vis,(p['x'],p['y0']),(p['x']+p['w'],p['y1']),cor,1)
            cv2.putText(vis,str(i+1)+((':'+o['txt']) if o else ''),(p['x'],p['y1']+22),cv2.FONT_HERSHEY_SIMPLEX,0.55,cor,1)
        rec=vis[max(0,ya):yb]; sc=min(2.0,1900/rec.shape[1])
        cv2.imwrite(f'/tmp/cif/dbg/linha_{pg}.jpg',cv2.resize(rec,None,fx=sc,fy=sc,interpolation=cv2.INTER_CUBIC),[1,88])
        print(len(ps),'palavras:',' '.join(f"{i+1}@{p['x']}" for i,p in enumerate(ps)))
