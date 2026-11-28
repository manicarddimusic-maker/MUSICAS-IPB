"""Fotos de partitura em que as cifras impressas foram riscadas e reescritas à mão (noutro tom).
Compara a foto com a página limpa do hinário: a tinta que só existe na foto, perto das linhas de cifras,
é a letra da caneta (e os riscos). Guarda essas caixas (para apagar na troca de tom) e monta tiras de conferência."""
import sys,json,glob,os,re
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from multiprocessing import Pool
R='/home/claude/musicas-ipb/public'
GIRO={90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}
def aplainar(g):
    k=max(31,int(min(g.shape)*0.05))|1
    fundo=cv2.GaussianBlur(cv2.morphologyEx(g,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k))),(0,0),k/3)
    return np.clip(g.astype(np.float32)/np.maximum(fundo.astype(np.float32),1)*255,0,255).astype(np.uint8)
def linhas_de(pares):
    rows=[]
    for p in sorted(pares,key=lambda p:(p[5],p[4])):
        for rw in rows:
            v=min(rw,key=lambda o:abs(o[4]-p[4]))
            if abs(v[5]-p[5])<0.9*p[7]+0.1*abs(v[4]-p[4]): rw.append(p); break
        else: rows.append([p])
    return [sorted(rw,key=lambda o:o[4]) for rw in sorted(rows,key=lambda rw:min(o[5] for o in rw))]
def um(f):
    try:
        from registro import transferir
        from transf_hinos import fontes_do_hino
        r=json.load(open(f)); img=r['img']; nome=os.path.basename(img)[:-4]
        num=int(re.match(r'h(\d+)',nome).group(1))
        fontes={c[0]:c for c in fontes_do_hino(num,str(num))}
        dst=cv2.imread(R+img)
        g=r['folha'].get('r',0); up=cv2.rotate(dst,GIRO[g]) if g else dst
        cinza=aplainar(cv2.cvtColor(up,cv2.COLOR_BGR2GRAY)); H,W=cinza.shape
        tinta=(cinza<150).astype(np.uint8)
        out=dict(img=img,r=g,w=W,h=H,linhas=[],borrachas=[])
        for chave,_ in r['de']:
            _,caminho,folha=fontes[chave]; sg=cv2.imread(caminho,0)
            o,rel=transferir(sg,folha,dst,chave_src=chave)
            if not o: continue
            txt={(c[0],c[1]):c[4] for c in o['c']}
            for rw in linhas_de(rel['pares']):
                cap=float(np.median([p[7] for p in rw]))
                y0=int(max(0,min(p[5] for p in rw)-3.7*cap)); y1=int(min(H,max(p[5] for p in rw)+0.45*cap))
                x0=int(max(0,rw[0][4]-2.5*cap)); x1=int(min(W,rw[-1][4]+rw[-1][6]+4*cap))
                L=dict(y0=y0,y1=y1,x0=x0,x1=x1,cap=round(cap,1),txt=[txt.get((p[4],p[5]),'') for p in rw],chave=chave,n_extra=0)
                out['linhas'].append(L)
                if len(rw)<2: continue
                # transformação origem -> foto para esta linha (pelos cantos das cifras)
                S=[];D=[]
                for xs,bs,ws,cs_,xd,bd,wd,cd in rw:
                    S+=[[xs,bs],[xs+ws,bs],[xs,bs-cs_]]; D+=[[xd,bd],[xd+wd,bd],[xd,bd-cd]]
                M,_i=cv2.estimateAffine2D(np.float32(S),np.float32(D),method=cv2.LMEDS)
                if M is None: continue
                M2=M.copy(); M2[0,2]-=x0; M2[1,2]-=y0
                src_w=cv2.warpAffine(sg,M2,(x1-x0,y1-y0),flags=cv2.INTER_AREA,borderValue=255)
                kk=max(3,int(0.42*cap))|1
                tinta_src=cv2.dilate((src_w<150).astype(np.uint8),np.ones((kk,kk),np.uint8))
                extra=tinta[y0:y1,x0:x1]&(1-tinta_src)
                extra=cv2.morphologyEx(extra,cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
                junto=cv2.dilate(extra,cv2.getStructuringElement(cv2.MORPH_RECT,(max(3,int(0.5*cap))|1,max(3,int(0.3*cap))|1)))
                n,lab,st,_c=cv2.connectedComponentsWithStats(junto,8)
                for i in range(1,n):
                    bx,by,bw,bh,ar=[int(v) for v in st[i]]
                    px=int(extra[by:by+bh,bx:bx+bw].sum())
                    if px<0.12*cap*cap or bh<0.35*cap: continue
                    out['borrachas'].append([x0+bx,y0+by,x0+bx+bw,y0+by+bh]); L['n_extra']+=1
        # tira de conferência: a linha com mais cifras entre as primeiras
        boas=[L for L in out['linhas'][:3] if len(L['txt'])>=4] or out['linhas'][:1]
        if boas:
            L=max(boas,key=lambda L:len(L['txt'])) if False else boas[0]
            c=up[L['y0']:L['y1'],L['x0']:L['x1']]; larg=1500
            s=min(2.4,larg/c.shape[1]); c=cv2.resize(c,None,fx=s,fy=s,interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
            t=np.full((c.shape[0]+24,larg,3),255,np.uint8); t[:c.shape[0],:c.shape[1]]=c
            cv2.putText(t,f"{nome[:20]} | impresso: "+' '.join(L['txt'])[:125],(4,t.shape[0]-7),cv2.FONT_HERSHEY_SIMPLEX,0.55,(0,0,200),1)
            cv2.imwrite(f'/tmp/cif/hmao/{nome}.png',t)
        json.dump(out,open(f'/tmp/cif/hmao/{nome}.json','w'))
        return nome,len(out['linhas']),len(out['borrachas'])
    except Exception as ex:
        import traceback; return os.path.basename(f),'ERRO',traceback.format_exc()[-300:]
if __name__=='__main__':
    fs=[f for f in sorted(glob.glob('/tmp/cif/transf/*.json')) if (lambda r:r['folha'] and r['de'][0][0].startswith('nc'))(json.load(open(f)))]
    print(len(fs),'fotos de partitura',flush=True)
    for f in glob.glob('/tmp/cif/hmao/*'): os.remove(f)
    with Pool(2) as p:
        for x in p.imap_unordered(um,fs,chunksize=2): print(x,flush=True)
