"""Completar à mão as cifras de uma página do hinário, linha por linha (cada linha = faixa logo acima de um sistema de pautas,
acompanhando a curva da pauta).
  nc_pag.py <pg>                      -> mostra as linhas com as palavras numeradas: /tmp/cif/dbg/pag_<pg>.jpg
  nc_pag.py <pg> <linha> "r1 r2 ..."  -> grava os rótulos das palavras dessa linha
rótulos: "." deixa como está; "TXT" cifra impressa; "TXT=LIT" impressa + escrita à mão; "-" não é cifra; "A|B" palavra com 2 cifras coladas"""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
import nc_slots,nc_linha
from ncpauta import pautas,sistemas,topo
_cache={}
def linhas(pg,lim=170):
    """-> (lista de linhas; cada linha = lista de palavras), imagem, cap"""
    if (pg,lim) in _cache: return _cache[(pg,lim)]
    e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0); H,W=e.shape
    P,d=pautas(e)
    if d is None or not P: _cache[(pg,lim)]=([],e,21.0); return _cache[(pg,lim)]
    tops,lig=sistemas(e,P,d); cap=1.7*d
    r=nc_slots.lido(pg)
    if r and r.get('cap'): cap=float(r['cap'])
    bw=(e<lim).astype(np.uint8)
    n,lab,st,cen=cv2.connectedComponentsWithStats(bw,8)
    comps=[(int(st[i][0]),int(st[i][1]),int(st[i][0]+st[i][2]),int(st[i][1]+st[i][3]),int(st[i][4])) for i in range(1,n)]
    rows=[]
    for ti,t in enumerate(tops):
        p=P[t]
        # limite de cima: a pauta de baixo do sistema anterior (ou o topo da página)
        sel=[]
        for c in comps:
            x0,y0,x1,y1,a=c; w=x1-x0; h=y1-y0; xc=(x0+x1)/2
            yt=float(topo(p,xc))
            if y1>yt-0.15*d or y1<yt-7.5*d: continue           # tem de estar logo acima da pauta
            if h>1.75*cap or w>6*cap: continue
            if h<0.18*cap and w<0.18*cap: continue
            sel.append((x0,y0,x1,y1,yt))
        sel.sort()
        # palavras: junta o que está perto na horizontal e na mesma altura
        ws=[]
        for c in sel:
            if ws and c[0]-ws[-1]['x1']<0.42*cap and min(c[3],ws[-1]['y1'])-max(c[1],ws[-1]['y0'])>-0.3*cap:
                w=ws[-1]; w['x1']=max(w['x1'],c[2]); w['y0']=min(w['y0'],c[1]); w['y1']=max(w['y1'],c[3]); w['cs'].append(list(c[:4]))
            else: ws.append(dict(x0=c[0],y0=c[1],x1=c[2],y1=c[3],cs=[list(c[:4])],yt=c[4]))
        out=[]
        for w in ws:
            altos=[c for c in w['cs'] if 0.72*cap<=c[3]-c[1]<=1.45*cap and c[2]-c[0]>=0.28*cap]
            if not altos: continue
            if w['y1']-w['y0']>1.75*cap: continue
            pes=sorted(c[3] for c in altos); b=pes[len(pes)//2]
            out.append(dict(x=w['x0'],base=b,w=w['x1']-w['x0'],y0=w['y0'],y1=w['y1'],cap=int(round(np.median([c[3]-c[1] for c in altos]))),cs=w['cs'],yt=w['yt']))
        # a linha de cifras: as palavras que ficam na altura mais comum acima da pauta (tira créditos, números, andamento)
        if out:
            alt=np.array([o['yt']-o['base'] for o in out]); med=float(np.median(alt))
            out=[o for o,a_ in zip(out,alt) if abs(a_-med)<2.6*cap]
        rows.append(out)
    # linhas marcadas à mão (pontos da linha de base), para o que os sistemas de pauta não acharam
    fn=f'/tmp/cif/slots_extra/{pg}.linhas'
    if os.path.exists(fn):
        for ln in open(fn):
            if not ln.strip(): continue
            pts=[tuple(float(v) for v in t.split(',')) for t in ln.split()]
            ps,_e,_c=nc_linha.palavras(pg,pts,cap=cap,lim=lim)
            rows.append(ps)
    rows=[r for r in rows if r]
    rows.sort(key=lambda r:float(np.median([p['base'] for p in r])))
    _cache[(pg,lim)]=(rows,e,cap); return _cache[(pg,lim)]
def mostrar(pg,lim=170,so=None):
    rows,e,cap=linhas(pg,lim); sl=nc_slots.slots(pg)
    tiras=[]
    for li,ps in enumerate(rows):
        if not ps or (so is not None and li not in so): continue
        vis=cv2.cvtColor(e,cv2.COLOR_GRAY2BGR)
        ya=int(min(p['y0'] for p in ps))-24; yb=int(max(p['y1'] for p in ps))+40
        for i,p in enumerate(ps):
            o=nc_linha.existente(sl,p,cap)
            cor=(0,150,0) if o and o['txt']!='?' else ((0,140,255) if o else (0,0,255))
            cv2.rectangle(vis,(p['x'],p['y0']),(p['x']+p['w'],p['y1']),cor,1)
            cv2.putText(vis,str(i+1)+((':'+o['txt']) if o and o['txt']!='?' else ''),(p['x'],p['y1']+19),cv2.FONT_HERSHEY_SIMPLEX,0.5,cor,1)
        rec=vis[max(0,ya):yb].copy()
        cv2.putText(rec,f'L{li}',(4,16),cv2.FONT_HERSHEY_SIMPLEX,0.55,(150,0,0),2)
        tiras.append(rec); print(f'L{li}',len(ps),'palavras')
    if tiras:
        W=max(t.shape[1] for t in tiras); sc=min(1.6,1850/W)
        im=np.vstack([cv2.copyMakeBorder(t,0,4,0,W-t.shape[1],cv2.BORDER_CONSTANT,value=(255,255,255)) for t in tiras])
        cv2.imwrite(f'/tmp/cif/dbg/pag_{pg}.jpg',cv2.resize(im,None,fx=sc,fy=sc,interpolation=cv2.INTER_CUBIC),[1,88])
def gravar(pg,li,labs,lim=170):
    rows,e,cap=linhas(pg,lim); ps=rows[li]
    assert len(labs)==len(ps),f'{len(labs)} rótulos para {len(ps)} palavras'
    n=0; ents=[]
    for p,l in zip(ps,labs):
        if l=='.': continue
        if l=='~':
            # continuação da palavra anterior (o detector partiu a cifra em duas): aumenta a caixa dela
            assert ents,'"~" sem palavra antes'
            q=ents[-1]; x1=max(q[0]+q[2],p['x']+p['w']); q[0]=min(q[0],p['x']); q[2]=x1-q[0]; q[4]=min(q[4],p['y0']); q[5]=max(q[5],p['y1'])
            ents.append([p['x'],p['base'],p['w'],p['cap'],p['y0'],p['y1'],'-']); ents[-1],ents[-2]=ents[-2],ents[-1]
            continue
        if '|' in l:
            ls=l.split('|'); qs=nc_linha.partir(p,len(ls))
            assert len(qs)==len(ls),f'não deu para partir em {len(ls)}'
            ents.append([p['x'],p['base'],p['w'],p['cap'],p['y0'],p['y1'],'-'])
            for q,t in zip(qs,ls): ents.append([q['x'],q['base'],q['w'],q['cap'],q['y0'],q['y1'],t]); n+=1
            continue
        ents.append([p['x'],p['base'],p['w'],p['cap'],p['y0'],p['y1'],l]); n+=1
    with open(f'/tmp/cif/slots_extra/{pg}.txt','a') as f:
        for q in ents: f.write(' '.join(str(v) for v in q)+'\n')
    print('pág',pg,'linha',li,':',n,'gravados')
if __name__=='__main__':
    pg=int(sys.argv[1]); LIM=int(os.environ.get('LIM','170'))
    if len(sys.argv)>2 and sys.argv[2].startswith('+'):
        open(f'/tmp/cif/slots_extra/{pg}.linhas','a').write(sys.argv[2][1:]+'\n'); print('linha acrescentada'); sys.exit()
    if len(sys.argv)>3: gravar(pg,int(sys.argv[2]),sys.argv[3].split(),LIM)
    else: mostrar(pg,LIM)
