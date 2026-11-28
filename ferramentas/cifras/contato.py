import sys,json,cv2,numpy as np,os
R='/home/claude/musicas-ipb/public'
F=json.load(open('/tmp/cif/faltam.json'))
def folha(imgs,saida,H=760,por_linha=5,W=560):
    ts=[]
    for rot,im in imgs:
        a=cv2.imread(R+im)
        if a is None: continue
        s=min(H/a.shape[0],W/a.shape[1]); t=cv2.resize(a,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
        tela=np.full((H+26,W,3),70,np.uint8); tela[26:26+t.shape[0],:t.shape[1]]=t
        cv2.putText(tela,rot[:44],(4,18),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1); ts.append(tela)
    while len(ts)%por_linha: ts.append(np.full((H+26,W,3),70,np.uint8))
    rows=[np.hstack(ts[k:k+por_linha]) for k in range(0,len(ts),por_linha)]
    cv2.imwrite(saida,np.vstack(rows),[cv2.IMWRITE_JPEG_QUALITY,72])
if __name__=='__main__':
    sec=sys.argv[1]; a,b=int(sys.argv[2]),int(sys.argv[3])
    imgs=[(f"{it['rot']} {it['titulo'][:20]} {os.path.basename(im)[:14]}",im) for it in F[sec] for im in it['imgs']]
    print(sec,len(imgs),'imagens; mostrando',a,b)
    folha(imgs[a:b],f'/tmp/cif/dbg/contato_{sec}_{a}.jpg',por_linha=int(sys.argv[4]) if len(sys.argv)>4 else 5)
