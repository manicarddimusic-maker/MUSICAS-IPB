"""Lê todas as cifras de uma página do hinário (partitura): devolve posição, texto e confiança."""
import sys,json,os,time,re
sys.path.insert(0,'/tmp/cif')
import numpy as np,cv2
from nccomum import base_da_pagina,recorte,lote,PAG
from ncocr import espaco_pauta,candidatos,limiar_da_pagina
from ncpauta import linhas_finas
import ncglifo
from ncglifo import Vocab,casar,calibrar_hx,partir_na_barra,angulo_local
from acordes import eh_acorde,estimar_tom,primeiro
_V=None
def vocab():
    global _V
    if _V is None: _V=Vocab()
    return _V
MAIOR=[0,2,4,5,7,9,11]
def diatonicas(tom):
    """alturas (0..11) das notas do tom ('F', 'Dm'...)"""
    if not tom: return None
    p=primeiro(tom)
    if not p: return None
    pc=p[0]; menor=tom.endswith('m')
    if menor: pc=(pc+3)%12
    return {(pc+x)%12 for x in MAIOR}
def altura(nota):
    p=primeiro(nota); return p[0] if p else None
def partes(txt):
    m=re.fullmatch(r'([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?',txt)
    return (m.group(1),m.group(2),m.group(3)) if m else (None,None,None)
def tem_pauta_abaixo(m,t,d):
    """há pauta logo abaixo da palavra? (linhas finas horizontais)"""
    H,W=m.shape
    x0=max(0,int(t['x0']-4*d)); x1=min(W,int(t['x1']+4*d))
    y0=min(H-1,int(t['base']+0.25*d)); y1=min(H,int(t['base']+9.5*d))
    if y1-y0<3*d or x1-x0<4: return False
    p=m[y0:y1,x0:x1].mean(axis=1)
    on=p>=0.33; n=0; i=0
    while i<len(on):
        if on[i]:
            n+=1
            while i<len(on) and on[i]: i+=1
        else: i+=1
    return n>=3
def ler_pagina(pg,debug=False):
    V=vocab()
    b=base_da_pagina(pg); e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
    if e is None or e.shape!=b.shape: e=b
    d=espaco_pauta(e); lim=limiar_da_pagina(b,d)
    toks,lab,cap=candidatos(b,d,lim)
    sel=[t for t in toks if t['cap']>=0.86*cap and t['cap']<=1.3*cap and t['sw']>=0.14*t['cap']]
    if not sel: return dict(pg=pg,w=b.shape[1],h=b.shape[0],d=d,cap=cap,lim=lim,hx=None,c=[])
    tes=lote([recorte(b,lab,t) for t in sel],7,f'p{pg}')
    hx,nhx=calibrar_hx(V,sel,tes)
    mfin=linhas_finas(e)
    for t,(tx,cf) in zip(sel,tes):
        r=casar(V,b,lab,t,lim,hx)
        t['cands']=r[:6]; t['tess']=(tx,cf); t['pauta']=tem_pauta_abaixo(mfin,t,d)
    # ---- 1ª passada: o que é certo
    def certo(t):
        r=t['cands']
        if not r: return None
        s1=r[0][0]; s2=r[1][0] if len(r)>1 else 0
        if s1>=0.86 and s1-s2>=0.045: return r[0][1]
        if s1>=0.80 and t['tess'][0]==r[0][1] and t['tess'][1]>=60: return r[0][1]
        return None
    certos=[c for c in (certo(t) for t in sel) if c]
    tom=estimar_tom(certos) if len(certos)>=3 else None
    dia=diatonicas(tom)
    vistos={}
    for c in certos: vistos[c]=vistos.get(c,0)+1
    raizes_vistas={partes(c)[0] for c in certos}
    # ---- 2ª passada: decide cada palavra, desempate pelo contexto (tom da música e acordes já vistos)
    tonica=None
    if tom:
        tonica=primeiro(tom)[0]
        if tom.endswith('m'): tonica=(tonica+3)%12     # trabalha com o relativo maior
    GRAU={0:(0.03,'M'),5:(0.03,'M'),7:(0.03,'M'),2:(0.02,'m'),4:(0.02,'m'),9:(0.025,'m'),11:(0.004,'d')}
    def nota(v,txt):
        r,s,bx=partes(txt); bonus=0.0
        if tonica is not None and r:
            g=GRAU.get((altura(r)-tonica)%12)
            if g:
                bonus+=g[0]
                q=primeiro(txt)[1]
                if q==g[1] or (g[1]=='d' and q in 'dm'): bonus+=0.012
            if bx and altura(bx) in dia: bonus+=0.01
        if txt in vistos: bonus+=0.025
        elif r in raizes_vistas: bonus+=0.008
        return v+bonus
    for t in sel:
        r=t['cands']; tx,cf=t['tess']
        t['txt']=None; t['conf']=0.0
        if not r:
            if cf>=90 and eh_acorde(tx) and len(tx)<=10: t['txt']=tx; t['conf']=0.5
            continue
        rk=sorted(((nota(v,x),v,x) for v,x in r),reverse=True)
        n1,v1,x1=rk[0]; n2=rk[1][0] if len(rk)>1 else 0
        concorda=(tx==x1 and cf>=50)
        if v1>=0.80 or (v1>=0.72 and concorda) or (v1>=0.74 and x1 in vistos and n1-n2>=0.03):
            t['txt']=x1; t['conf']=round(min(1.0,v1+(0.05 if concorda else 0)+min(0.05,n1-n2)),3)
            # raiz em dúvida (F×E, C×G, B×D...) sem nada que desempate: melhor marcar do que errar
            if not concorda and n1-n2<0.012 and len(rk)>1 and partes(rk[1][2])[0]!=partes(x1)[0] and v1<0.9: t['txt']='?'
        elif cf>=88 and eh_acorde(tx) and 1<=len(tx)<=10 and (tx in V.pos or tx in vistos):
            t['txt']=tx; t['conf']=0.6
        else:
            t['txt']='?'
    # ---- linhas de cifras: palavras aceitas, alinhadas, com pauta logo abaixo
    boas=[t for t in sel if t['txt'] and t['txt']!='?']
    pai={id(t):id(t) for t in boas}; por={id(t):t for t in boas}
    def acha(i):
        while pai[i]!=i: pai[i]=pai[pai[i]]; i=pai[i]
        return i
    for i,a in enumerate(boas):
        for c in boas[i+1:]:
            dx=abs(a['x0']-c['x0'])
            if dx<9*cap and abs(a['base']-c['base'])<0.35*cap+0.09*dx: pai[acha(id(a))]=acha(id(c))
    grupos={}
    for t in boas: grupos.setdefault(acha(id(t)),[]).append(t)
    linhas=[g for g in grupos.values() if len(g)>=3 or (len(g)==2 and (any(t['pauta'] for t in g) or min(t['conf'] for t in g)>=0.85)) or (len(g)==1 and g[0]['conf']>=0.88 and g[0]['pauta'])]
    saida=[]
    usados=set()
    # a letra das cifras tem sempre o mesmo tamanho na página: tira linhas de letra maior/menor (título, rodapé)
    if linhas:
        capp=float(np.median([t['cap'] for g in linhas for t in g if t['conf']>=0.85] or [t['cap'] for g in linhas for t in g]))
        linhas=[g for g in linhas if abs(np.median([t['cap'] for t in g])/capp-1)<=0.11]
    for g in linhas:
        g.sort(key=lambda t:t['x0'])
        capm=float(np.median([t['cap'] for t in g]))
        for t in g: usados.add(id(t)); saida.append(t)
        # palavras não lidas que estão na mesma linha: marca como "?"
        for t in sel:
            if id(t) in usados or t['txt']!='?' : continue
            viz=min(g,key=lambda o:abs(o['x0']-t['x0'])); dx=abs(viz['x0']-t['x0'])
            if dx<10*cap and abs(viz['base']-t['base'])<0.3*cap+0.08*dx and 0.85*capm<=t['cap']<=1.2*capm:
                usados.add(id(t)); saida.append(t)
    # ---- cifras fracas (foto fora de foco em parte da folha): procura de novo com um limiar mais escuro
    if saida:
        lim2=min(190,int(lim*1.9)+10)
        toks2,lab2,_=candidatos(b,d,lim2)
        capp2=float(np.median([t['cap'] for t in saida]))
        for t in toks2:
            if not (0.85*capp2<=t['cap']<=1.3*capp2) or t['x1']-t['x0']<0.45*cap or t['sw']<0.14*t['cap']: continue
            if any(min(t['x1'],o['x1'])-max(t['x0'],o['x0'])>-0.2*cap and abs(o['base']-t['base'])<0.9*cap for o in saida): continue
            viz=min(saida,key=lambda o:abs(o['x0']-t['x0'])); dx=abs(viz['x0']-t['x0'])
            if not (dx<12*cap and abs(viz['base']-t['base'])<0.45*cap+0.09*dx): continue
            r=casar(V,b,lab2,t,lim2,hx)
            if not r or r[0][0]<0.55: continue
            rk=sorted(((nota(v,x),v,x) for v,x in r[:6]),reverse=True)
            n1,v1,x1=rk[0]; n2=rk[1][0] if len(rk)>1 else 0
            t['cands']=r[:6]; t['tess']=('',0); t['pauta']=False
            if v1>=0.86 and n1-n2>=0.03: t['txt']=x1; t['conf']=round(v1-0.06,3)
            else: t['txt']='?'; t['conf']=0.0
            t['fraca']=True
            saida.append(t)
    if debug: print('   sel',len(sel),'com pauta',sum(1 for t in sel if t['pauta']),'lidas',sum(1 for t in sel if t['txt'] and t['txt']!='?'),'boas',len(boas),'linhas',len(linhas))
    saida.sort(key=lambda t:(t['base'],t['x0']))
    out=dict(pg=pg,w=int(b.shape[1]),h=int(b.shape[0]),d=round(d,2),cap=round(cap,1),lim=lim,hx=round(hx,3),nhx=nhx,tom=tom,
             c=[[int(t['x0']),int(t['base']),int(t['x1']-t['x0']),int(t['cap']),t['txt'],float(t['conf']),int(t['y0']),int(t['y1']),(t['cands'][0][1] if t.get('cands') else ''),t['tess'][0],int(bool(t.get('fraca')))] for t in saida])
    if debug:
        vis=cv2.cvtColor(e,cv2.COLOR_GRAY2BGR)
        for t in sel:
            if id(t) in usados: continue
            cv2.rectangle(vis,(t['x0'],t['y0']),(t['x1'],t['y1']),(200,200,0),1)
        for t in saida:
            cor=(0,0,255) if t['txt']=='?' else (0,150,0)
            cv2.rectangle(vis,(t['x0']-2,t['y0']-2),(t['x1']+2,t['y1']+2),cor,2)
            cv2.putText(vis,t['txt']+(' %.2f'%t['conf'] if t['txt']!='?' else ''),(t['x0'],t['y0']-8),cv2.FONT_HERSHEY_SIMPLEX,0.62,(255,0,0) if t['txt']!='?' else (0,0,255),2)
        cv2.imwrite(f'/tmp/cif/dbg/lido{pg:03d}.jpg',vis,[cv2.IMWRITE_JPEG_QUALITY,70])
    return out
if __name__=='__main__':
    for a in sys.argv[1:]:
        t0=time.time(); r=ler_pagina(int(a),debug=True)
        txts=[c[4] for c in r['c']]
        print(a,'tom',r['tom'],'lim',r['lim'],'hx',r['hx'],'cifras',len(txts),'ilegíveis',txts.count('?'),'%.1fs'%(time.time()-t0))
        linhas={}
        for c in r['c']: linhas.setdefault(round(c[1]/ (3*r['cap'])),[]).append(c)
        for k in sorted(linhas): print('   ',' '.join(c[4] for c in sorted(linhas[k])))

def limiar_por_comparacao(b,d,V,hx=0.86):
    """limiar de preto em que as palavras ficam mais parecidas com a fonte (mais seguro que medir o traço em foto sem foco)"""
    melhor=None
    for lim in (45,60,80,105,135,165):
        toks,lab,cap=candidatos(b,d,lim)
        sel=[t for t in toks if 0.86*cap<=t['cap']<=1.3*cap and t['sw']>=0.13*t['cap'] and 0.9*cap<=t['x1']-t['x0']<=6*cap and len(t['cs'])<=9]
        if len(sel)<5: continue
        sel=sorted(sel,key=lambda t:-(t['x1']-t['x0']))[:14]
        notas=[]
        for t in sel:
            r=casar(V,b,lab,t,lim,hx,n_fino=2)
            notas.append(r[0][0] if r else 0.0)
        notas.sort(reverse=True); m=float(np.mean(notas[:8]))
        if melhor is None or m>melhor[0]: melhor=(m,lim)
    return melhor[1] if melhor else 80
def bruto_pagina(pg,lim_modo='traco'):
    """leitura crua: todas as palavras candidatas com os acordes mais parecidos (a decisão fica para depois)"""
    V=vocab()
    b=base_da_pagina(pg); e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0)
    if e is None or e.shape!=b.shape: e=b
    d=espaco_pauta(e); lim=limiar_por_comparacao(b,d,V) if lim_modo=='comp' else limiar_da_pagina(b,d)
    toks,lab,cap=candidatos(b,d,lim)
    sel=[t for t in toks if 0.84*cap<=t['cap']<=1.32*cap and t['sw']>=0.13*t['cap']]
    out=dict(pg=pg,w=int(b.shape[1]),h=int(b.shape[0]),d=round(d,2),cap=round(cap,1),lim=lim,hx=0.85,nhx=0,toks=[])
    if not sel: return out
    tes=lote([recorte(b,lab,t) for t in sel],7,f'p{pg}')
    hx,nhx=calibrar_hx(V,sel,tes,b=b,lab=lab,lim=lim); out['hx']=round(hx,3); out['nhx']=nhx
    mfin=linhas_finas(e)
    bw=(b<lim).astype(np.uint8); cache={}
    def ang_de(t): return angulo_local(bw,(t['x0']+t['x1'])/2,t['base'],cap,cache)
    def reg(t,r,tx,cf,p):
        out['toks'].append(dict(x0=int(t['x0']),x1=int(t['x1']),y0=int(t['y0']),y1=int(t['y1']),base=int(t['base']),cap=int(t['cap']),
            sw=round(float(t['sw']),2),n=len(t['cs']),c=[[round(float(v),3),x] for v,x in r[:5]],t=[tx,round(float(cf))],pa=int(tem_pauta_abaixo(mfin,t,d)),p=p))
    for t,(tx,cf) in zip(sel,tes):
        a_=ang_de(t)
        reg(t,casar(V,b,lab,t,lim,hx,ang=a_),tx,cf,1)
        out['toks'][-1]['a']=a_
        # acorde com baixo (F/C): lê cada lado da barra separado — a comparação fica bem mais segura
        pt=partir_na_barra(t,lab)
        if pt:
            re_=casar(V,b,lab,pt[0],lim,hx,n_fino=6,filtro=V.sem_baixo,ang=a_); rd=casar(V,b,lab,pt[1],lim,hx,n_fino=5,filtro=V.so_raiz,ang=a_)
            if re_ and rd: out['toks'][-1]['s']=dict(l=[[round(float(v),3),x] for v,x in re_[:3]],r=[[round(float(v),3),x] for v,x in rd[:3]])
    # 2ª passada, limiar mais escuro: cifras fracas (parte da folha fora de foco)
    lim2=min(190,int(lim*1.9)+10); out['lim2']=lim2
    toks2,lab2,_=candidatos(b,d,lim2)
    n2=0
    for t in toks2:
        if not (0.84*cap<=t['cap']<=1.4*cap) or t['x1']-t['x0']<0.45*cap or t['sw']<0.15*t['cap'] or t['sw']>0.34*t['cap']: continue
        if any(min(t['x1'],o['x1'])-max(t['x0'],o['x0'])>-0.15*cap and min(t['y1'],o['y1'])-max(t['y0'],o['y0'])>0 for o in sel): continue
        r=casar(V,b,lab2,t,lim2,hx,ang=ang_de(t))
        if not r or r[0][0]<0.5: continue
        reg(t,r,'',0,2); n2+=1
        if n2>=60: break
    return out
