"""Cifras das folhas digitais enviadas pelo usuário (imagens u-*): acha a página do PDF de origem e usa o texto exato."""
import sys,json,re,os,glob
sys.path.insert(0,'/tmp/cif')
import fitz,cv2,numpy as np
from pdftok import juntar,limpar
from acordes import eh_acorde
from louvor2 import ROT,MARCA,palavra_maiuscula
R='/home/claude/musicas-ipb/'
C=json.load(open(R+'public/data/catalogo.json'))
usadas={}
for s in C['secoes']:
    for it in s['itens']:
        for p in it['paginas']:
            if '/u-' in p['img']: usadas.setdefault(p['img'],set()).add(s['id'])
print(len(usadas),'imagens u-*')
def cifras_da_pagina(page):
    """linhas do PDF em que praticamente tudo é acorde"""
    out=[]
    for b in page.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            if abs(l['dir'][0]-1)>1e-3: continue
            cs=[]
            for s in l['spans']:
                if s['size']<6: continue
                for c in s['chars']:
                    if c['c'].strip(): cs.append(dict(x0=c['bbox'][0],x1=c['bbox'][2],y=c['origin'][1],s=s['size'],c=c['c'],t=c['bbox'][1],b=c['bbox'][3],neg='Bold' in s['font'],fonte=s['font'],cor=s['color']))
            if not cs: continue
            mono='Courier' in cs[0]['fonte'] or 'Mono' in cs[0]['fonte']
            r=sorted(juntar(cs,folga=0.3 if mono else 0.12),key=lambda t:t['x'])
            val=[t for t in r if limpar(t)]
            rot=[t for t in r if not limpar(t) and ROT.match(t['txt'])]
            resto=len(r)-len(val)-len(rot)
            if not val: continue
            pal=[t for t in r if palavra_maiuscula(t['txt']) and not ROT.match(t['txt'])]
            ok = resto==0 or (len(val)>=4 and resto<=1) or (len(val)>=8 and resto<=3)
            if ok and pal and len(pal)>=len(val): ok=False          # título em maiúsculas
            # uma palavra só ("A", "E", "Em") em linha de letra normal preta: provavelmente é letra da música
            if ok and len(r)==1 and not r[0]['chars'][0]['neg'] and r[0]['chars'][0]['cor'] in (0,0x212121) and r[0]['txt'] in ('A','E','Em','Am','Da','De'): ok=False
            peg=[]
            if ok: peg=[limpar(t) for t in r if limpar(t)]
            else:
                k=next((i for i,t in enumerate(r) if MARCA.match(t['txt']) or re.match(r'^(Tom|TOM|Intro|INTRO|Introdução)\\s*:?$',t['txt'])),None)
                if k is not None:
                    for t in r[k+1:]:
                        u=limpar(t)
                        if u: peg.append(u)
                        elif t['txt'] in '()[]=:': continue
                        else: break
            for u in peg:
                u['fonte']=u['chars'][0]['fonte']; u['neg']=u['chars'][0]['neg']; out.append(u)
    return out
orb=cv2.ORB_create(nfeatures=4000,scaleFactor=1.2,nlevels=8)
def feats(g): return orb.detectAndCompute(g,None)
DPI=110
paginas=[]   # (arquivo, nº, kp, des, escala px/pt)
for f in sorted(glob.glob('/tmp/zipin/x/*.pdf')):
    if 'HNC Cifras' in f: continue
    try: d=fitz.open(f)
    except Exception: continue
    for pn in range(len(d)):
        pm=d[pn].get_pixmap(matrix=fitz.Matrix(DPI/72,DPI/72),colorspace=fitz.csGRAY)
        g=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width)
        kp,des=feats(g)
        if des is not None: paginas.append((f,pn,kp,des,g))
print(len(paginas),'páginas de PDF')
bf=cv2.BFMatcher(cv2.NORM_HAMMING)
FOLHAS={}; rel=[]
for img in sorted(usadas):
    a=cv2.imread(R+'public'+img,0); H,W=a.shape
    k=min(1.0,1400/W); small=cv2.resize(a,None,fx=k,fy=k,interpolation=cv2.INTER_AREA) if k<1 else a
    kp,des=feats(small)
    achados=[]
    for f,pn,kp2,des2,g2 in paginas:
        mm=bf.knnMatch(des2,des,k=2)
        bons=[m for m,n in (x for x in mm if len(x)==2) if m.distance<0.75*n.distance]
        if len(bons)<14: continue
        src=np.float32([kp2[m.queryIdx].pt for m in bons]); dst=np.float32([kp[m.trainIdx].pt for m in bons])
        M,inl=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=2.5)
        if M is None: continue
        n=int(inl.sum()); esc=float(np.hypot(M[0,0],M[1,0])); rot=float(np.degrees(np.arctan2(M[1,0],M[0,0])))
        e_=esc*(DPI/72)/k
        if n>=12 and abs(rot)<0.6 and 1.2<=e_<=6.5:
            # confere de verdade: leva a página para cima da imagem e mede a semelhança da tinta
            w_=cv2.warpAffine(g2,M,(small.shape[1],small.shape[0]),flags=cv2.INTER_LINEAR,borderValue=255)
            A=255.0-cv2.GaussianBlur(small,(0,0),2.0).astype(np.float32); B=255.0-cv2.GaussianBlur(w_,(0,0),2.0).astype(np.float32)
            A-=A.mean(); B-=B.mean(); ncc=float((A*B).sum()/(np.sqrt((A*A).sum()*(B*B).sum())+1e-6))
            if ncc>=0.45: achados.append((ncc,f,pn,M,esc))
    if not achados: rel.append((img,'sem PDF de origem')); continue
    achados.sort(key=lambda x:-x[0]); melhor=achados[0][1]
    cs=[]; fontes=[]; negs=[]
    for n,f,pn,M,esc in achados:
        if f!=melhor: continue
        d=fitz.open(f)
        # página (pt) -> render (px a DPI) -> imagem reduzida -> imagem original
        e_=esc*(DPI/72)/k; tx=M[0,2]/k; ty=M[1,2]/k
        for t in cifras_da_pagina(d[pn]):
            x=t['x']*e_+tx; y=t['base']*e_+ty
            if -5<=x<=W and 0<=y<=H+5:
                mono='Courier' in t['fonte'] or 'Mono' in t['fonte']
                kf=0.86 if mono else (1.0 if 'Times' in t['fonte'] else 0.93)
                fs=t['s']*e_*kf
                c=[round(x),round(y),round(t['w']*e_),round(fs,1),t['txt']]
                so=t['sobe']*e_; de=t['desce']*e_
                if so>0.84*fs or de>0.27*fs: c+=[0,0,round(max(so,0.82*fs)),round(max(de,0.08*fs))]
                cs.append(c); fontes.append('m' if mono else 't' if 'Times' in t['fonte'] else 's'); negs.append(t['neg'])
    if not cs: rel.append((img,'PDF sem texto: '+os.path.basename(melhor)[:30])); continue
    fam=max(set(fontes),key=fontes.count)
    F=dict(w=W,h=H,f=fam,c=cs)
    if sum(negs)<0.5*len(negs): F['n']=1
    FOLHAS[img]=F; rel.append((img,f'{len(cs)} cifras  <- {os.path.basename(melhor)[:34]} (semelhança {achados[0][0]:.2f})'))
for r in rel: print('  ',r[0].split('/')[-1].ljust(44),r[1])
json.dump(dict(folhas=FOLHAS,secoes={k:sorted(v) for k,v in usadas.items()}),open('/tmp/cif/user.json','w'),ensure_ascii=False)
print(len(FOLHAS),'folhas com cifras')
