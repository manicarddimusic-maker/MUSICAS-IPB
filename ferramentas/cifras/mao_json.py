"""Monta as cifras escritas à mão (lidas uma a uma) nas folhas das abas."""
import sys,json,glob,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
import mao
from mao import tinta_colorida,tinta_larga
R='/home/claude/musicas-ipb/public'
C=json.load(open(R+'/data/catalogo.json'))
sec_de={}
for s in C['secoes']:
    for it in s['itens']:
        for p in it['paginas']: sec_de.setdefault(p['img'],set()).add(s['id'])
por={}; tot=0; ileg=0
for f in sorted(glob.glob('/tmp/cif/mao/*.json')):
    J=json.load(open(f))
    if not any('txt' in t for t in J['toks']): continue
    img=J['img'].replace(R,''); cor=cv2.imread(J['img'])
    m=tinta_larga(cor,J.get('matiz'),J.get('smin',85)) if J.get('modo','cor')=='cor' else mao.tinta_escura(cor,'tudo')
    cs=[]
    alts=[]
    for t in J['toks']:
        if t.get('txt','-') in ('-','?'): continue
        ys,xs=np.nonzero(m[t['y0']:t['y1'],t['x0']:t['x1']])
        if len(ys)>5: alts.append(int(ys.max()-ys.min()+1))
    alt_ref=float(np.median(alts)) if alts else 40.0
    fs_folha=round(max(16.0,0.80*alt_ref/0.727),1)
    for t in J['toks']:
        txt=t.get('txt','-')
        if txt=='-': continue
        sub=m[t['y0']:t['y1'],t['x0']:t['x1']]
        ys,xs=np.nonzero(sub)
        if len(xs)<5:
            ys,xs=np.nonzero(np.ones_like(sub))
        bx0,bx1=t['x0']+int(xs.min()),t['x0']+int(xs.max())+1; by0,by1=t['y0']+int(ys.min()),t['y0']+int(ys.max())+1
        if by1-by0>1.45*alt_ref: by1=int(by0+1.3*alt_ref)      # a cifra fica em cima; embaixo já é a letra da música
        partes=txt.split(); caixas=[(bx0,bx1)]
        if len(partes)>1:
            col=sub[:,xs.min():xs.max()+1].sum(axis=0)>0
            vazios=[];i=0
            while i<len(col):
                if not col[i]:
                    j=i
                    while j<len(col) and not col[j]: j+=1
                    vazios.append((j-i,i,j)); i=j
                else: i+=1
            vazios.sort(reverse=True)
            if len(vazios)>=len(partes)-1:
                cortes=sorted(v[1:] for v in vazios[:len(partes)-1]); a=0; caixas=[]
                for (i,j) in cortes: caixas.append((bx0+a,bx0+i)); a=j
                caixas.append((bx0+a,bx1))
            else: partes=[txt]
        for (xa,xb),p in zip(caixas,partes):
            bh=by1-by0
            cs.append([int(xa),int(by1),int(xb-xa),fs_folha,p,t['bg'],0,int(max(bh,0.8*alt_ref)+5),6])
            if p=='?': ileg+=1
            else: tot+=1
    if sum(1 for c in cs if c[4]!='?')<2: continue
    d=dict(w=J['w'],h=J['h'],f='a',c=cs)
    for sec in sec_de.get(img,[]): por.setdefault(sec,{})[img]=d
for sec,fs in por.items():
    fn=R+'/data/cifras/'+sec+'.json'
    Jc=json.load(open(fn)) if os.path.exists(fn) else dict(v=1,folhas={})
    Jc['folhas'].update(fs); json.dump(Jc,open(fn,'w'),ensure_ascii=False,separators=(',',':'))
    print(sec,'+',len(fs),'folhas com cifra à mão')
print('cifras à mão:',tot,'| marcadas como ilegíveis:',ileg)
