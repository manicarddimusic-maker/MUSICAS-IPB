"""Conferência: tinta na faixa das cifras que nenhuma cifra lida cobre (cifra que faltou, letra fora da caixa)."""
import sys,json
import cv2,numpy as np
def sobras(pg,c):
    im=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0); H,W=im.shape
    if not c: return []
    capm=float(np.median([x[3] for x in c]))
    rows=[]
    for x in sorted(c,key=lambda x:x[1]):
        if rows and x[1]-np.median([q[1] for q in rows[-1]])<0.6*capm: rows[-1].append(x)
        else: rows.append([x])
    out=[]
    for rw in rows:
        b=int(np.median([x[1] for x in rw])); y0=max(0,int(b-1.2*capm)); y1=min(H,int(b+0.15*capm))
        ink=(im[y0:y1]<140).astype(np.uint8)
        for x in rw: ink[:,max(0,int(x[0])-3):int(x[0]+x[2])+4]=0
        n,lab,st,_=cv2.connectedComponentsWithStats(ink,8)
        for j in range(1,n):
            x,y,w,h,a=[int(v) for v in st[j]]
            if w<0.35*capm or h<0.6*capm or a<0.12*capm*capm: continue
            if w>8*capm: continue
            out.append(dict(pg=pg,x=x,y0=y0+y,w=w,h=h,base=b,cap=capm))
    return out
if __name__=='__main__':
    R=json.load(open(sys.argv[1] if len(sys.argv)>1 else '/tmp/cif/nc_palavras.json'))
    S=[]
    for k in sorted(R,key=int): S+=sobras(int(k),R[k])
    json.dump(S,open('/tmp/cif/nc_sobras.json','w'))
    print(len(S),'sobras em',len(set(s['pg'] for s in S)),'páginas')
    TW,TH=392,104; cols=5; tiles=[]; cache={}
    for q,d in enumerate(S):
        pg=d['pg']
        if pg not in cache: cache[pg]=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
        im=cache[pg]; pad=int(2.6*d['cap'])
        xa=max(0,d['x']-pad); xb=min(im.shape[1],d['x']+d['w']+pad); ya=max(0,int(d['base']-1.7*d['cap'])); yb=min(im.shape[0],int(d['base']+0.6*d['cap']))
        g=im[ya:yb,xa:xb]; s=min((TW-8)/g.shape[1],(TH-30)/g.shape[0],3.0)
        g=cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_CUBIC)
        t=np.full((TH,TW),255,np.uint8); t[24:24+g.shape[0],4:4+g.shape[1]]=g; t=cv2.cvtColor(t,cv2.COLOR_GRAY2BGR)
        xl=4+int((d['x']-xa)*s); xr=4+int((d['x']+d['w']-xa)*s); cv2.line(t,(xl,TH-3),(xr,TH-3),(0,0,255),3)
        cv2.putText(t,f"{q} p{pg} x{d['x']} b{d['base']}",(4,16),cv2.FONT_HERSHEY_SIMPLEX,0.5,(200,0,0),1); cv2.rectangle(t,(0,0),(TW-1,TH-1),(170,170,170),1); tiles.append(t)
    while len(tiles)%cols: tiles.append(np.full((TH,TW,3),255,np.uint8))
    por=70
    for n0 in range(0,len(tiles),por):
        cv2.imwrite(f'/tmp/nn/vis/sobras{n0//por}.png',np.vstack([np.hstack(tiles[k:k+cols]) for k in range(n0,min(len(tiles),n0+por),cols)]))
