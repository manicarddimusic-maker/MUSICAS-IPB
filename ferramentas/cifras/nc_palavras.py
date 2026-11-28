"""Páginas novas do hinário: confere a leitura cifra por cifra contra as PALAVRAS impressas na linha das cifras.
Conserta cifra lida pela metade ("Bb" de "Bb/D"), junta pedaços, aplica o que foi lido a olho e acha cifra que ficou sem ler.
Saída: /tmp/cif/nc_palavras.json {pg: lista c} (mesmo formato de nc_decidido) + lista de pendências para ler a olho."""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from acordes import eh_acorde
MANUAL="""Bb/F Esus D7/E Am/G C9/11 D11 Db9/11 Gb9/11 Gb9/11 Db Db9/11 Ab7/11 Ab7 Db5aum Ab7 Bb Bb F7/13 C5aum F9/11
F9/11 F5aum Dbdim C9/11 Gm7 G9/11 Bb9/11 Bb W:Bb7M/D Bb9/11 Bb9/11 Bb9/11 Bb/F Bb7/13 - Eb11/13 Bbsus4/9 Eb11/13 Em4/9 Bb9/11
Bb9/11 G/D Dm7 Gm7 Gm9/11 Ab9/11 Fm7 Ab6/11 Bbm5dim Bb9/11 Bb9/11 Bb9/11 Bb9/11 Gm9/11 C7/11 Dmsus4/9 Dsus4/9- Ab/Eb Bm5aum D/A
Bm5aum - - Bm5aum D/F# A7 D C6 F4/7+ Eb9/11+ W:Bb7/9m Bb7 Ab6 Bb7 Bb/D - Gm Bb9/11 Bb9/11 Bbdim
Eb9/11 Ab9/11 Ab9/11 Ab9/11 Ab9/11 Ab9/11 Asus4/9 A A B9/F# D/A A/E Cm7 Fm C9/11 C5aum/E A9m Esus4/9 A/B A/C#
Esus4/9 B B7 B7 E/B Bb/D Eb F7 F9/11 F9/11 C7 Adim Ab7M F7 Bb7 Eb/G Eb/Bb Eb Bbsus4/9 F9/11
F/C Gm Fsus4 F Eb E7 G#dim Am C5aum/E F#dim Ab/C Bm/F# Am7 D7/9 Adim Bb7 Ebdim Fm Ebdim Ab/Eb
Eb/Bb Adim Bb7 Eb/Bb""".split()
LINHAS_MAO={613:[1153]}     # linhas de cifras em que a leitura normal não leu nada: {pg: [linha de base]}
EXTRA={}      # (pg, x da palavra) -> texto lido a olho numa segunda rodada
if os.path.exists('/tmp/cif/nc_palavras_manual.json'):
    EXTRA={tuple(int(q) for q in k.split(',')):v for k,v in json.load(open('/tmp/cif/nc_palavras_manual.json')).items()}
def extra(pg,p):
    for k,v in EXTRA.items():
        if k[0]==pg and abs(k[1]-p['x'])<=4 and (len(k)<3 or abs(k[2]-p['base'])<=10): return v
    return None
def contem(inteiro,toks):
    """o texto inteiro contém, na ordem, os pedaços já lidos?"""
    pos=0
    for t in toks:
        if t['txt'] in ('?','~'): continue
        i=inteiro.find(t['txt'],pos)
        if i<0: return False
        pos=i+len(t['txt'])
    return True
import re
from acordes import ACORDE
def normal(t):
    """acertos de leitura comuns na palavra inteira"""
    t=t.strip().replace('|','/').replace('l','/').replace('I','/')
    t=re.sub(r'^[)\]1.,;:]+(?=[A-G])','',t)
    t=re.sub(r'^[38](?=b)','B',t)
    t=re.sub(r'(?<!d)i(?!m)','/',t)            # "BbiD" -> "Bb/D" (o i só vale em "dim")
    return t
def cortes(S,maxp):
    """todas as maneiras de partir S em até maxp cifras válidas"""
    n=len(S); memo={}
    def rec(i,k):
        if i==n: return [[]]
        if k==0: return []
        if (i,k) in memo: return memo[(i,k)]
        out=[]
        for j in range(i+1,n+1):
            if ACORDE.match(S[i:j]):
                for r in rec(j,k-1): out.append([S[i:j]]+r)
        memo[(i,k)]=out; return out
    return rec(0,maxp)
def casar(partes,T):
    """liga cada pedaço lido (na ordem) a uma parte que o contenha -> lista do índice da parte de cada pedaço, ou None"""
    ids=[]; j=0; pos=0
    for t in T:
        tx=t['txt']
        if tx in ('?','~'):
            ids.append(None); continue
        while j<len(partes):
            k=partes[j].find(tx,pos)
            if k>=0: ids.append(j); pos=k+len(tx); break
            j+=1; pos=0
        else: return None
    # pedaços sem texto ficam com a parte do vizinho mais próximo que ainda não "fechou"
    for i,v in enumerate(ids):
        if v is None:
            ant=[ids[q] for q in range(i) if ids[q] is not None]; dep=[ids[q] for q in range(i+1,len(ids)) if ids[q] is not None]
            ids[i]=ant[-1] if ant else (dep[0] if dep else 0)
    if set(ids)!=set(range(len(partes))): return None       # toda parte precisa de ao menos um pedaço lido
    return ids
def caixas(p,T,partes,ids):
    """caixa de cada parte, pelos componentes de tinta da palavra"""
    vao=[]
    for j in range(len(partes)):
        ts=[t for t,i in zip(T,ids) if i==j]
        vao.append([min(t['x'] for t in ts),max(t['x']+t['w'] for t in ts)])
    comps=sorted(p['cs']); dono=[]
    for c in comps:
        xc=(c[0]+c[2])/2; d=None
        for j,(a,b) in enumerate(vao):
            if a-1<=xc<=b+1: d=j; break
        dono.append(d)
    for q,c in enumerate(comps):
        if dono[q] is not None: continue
        xc=(c[0]+c[2])/2
        esq=[j for j,(a,b) in enumerate(vao) if b<xc]; dire=[j for j,(a,b) in enumerate(vao) if a>xc]
        a=esq[-1] if esq else None; b=dire[0] if dire else None
        def sobra(j,lado):
            ts=[t['txt'] for t,i in zip(T,ids) if i==j and t['txt'] not in ('?','~')]
            if not ts: return True
            return (not partes[j].endswith(ts[-1])) if lado=='fim' else (not partes[j].startswith(ts[0]))
        if a is None: dono[q]=b
        elif b is None: dono[q]=a
        else:
            sa,sb=sobra(a,'fim'),sobra(b,'ini')
            if sa and not sb: dono[q]=a
            elif sb and not sa: dono[q]=b
            else: dono[q]=a if xc-vao[a][1]<=vao[b][0]-xc else b
    out=[]
    for j in range(len(partes)):
        cs=[c for c,dn in zip(comps,dono) if dn==j]
        if not cs: return None
        altos=[c for c in cs if c[3]-c[1]>=0.7*p['cap']]
        base=sorted(c[3] for c in altos)[len(altos)//2] if altos else p['base']
        out.append([min(c[0] for c in cs),base,max(c[2] for c in cs)-min(c[0] for c in cs),p['cap'],partes[j],0.97,min(c[1] for c in cs),max(c[3] for c in cs)])
    return out
from PIL import ImageFont as _IF
_FNT=_IF.truetype('/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf',100)
def larg_esperada(txt,cap): return _FNT.getlength(txt)*(cap/0.711)/100.0
ADIC={}       # cifras que nem a leitura nem as palavras acharam (letra grudada em haste): {pg: [[x0,x1,base,txt],...]}
if os.path.exists('/tmp/cif/nc_adic.json'): ADIC={int(k):v for k,v in json.load(open('/tmp/cif/nc_adic.json')).items()}
def absorver(pg,out,capm):
    """letra grudada na haste de uma nota fica fora da palavra: a caixa da cifra cresce até cobri-la"""
    import nc_cobertura
    n=0
    for _ in range(3):
        mudou=False
        for s_ in nc_cobertura.sobras(pg,out):
            viz=[]
            for e in out:
                if abs(e[1]-s_['base'])>0.6*capm or e[4]=='?': continue
                gd=s_['x']-(e[0]+e[2]); ge=e[0]-(s_['x']+s_['w'])
                g=gd if gd>=-4 else (ge if ge>=-4 else None)
                if g is None or g>0.35*capm: continue
                if e[2]<0.85*larg_esperada(e[4],e[3]): viz.append((g,e))
            if viz:
                e=min(viz,key=lambda v:v[0])[1]
                x0=min(e[0],s_['x']); x1=max(e[0]+e[2],s_['x']+s_['w'])
                if x1-x0<=1.25*larg_esperada(e[4],e[3])+0.3*capm:
                    e[0]=x0; e[2]=x1-x0; e[6]=min(e[6],s_['y0']); n+=1; mudou=True
        if not mudou: break
    return n
def _img(e,p):
    pad=int(0.5*p['cap'])+2
    g=e[max(0,p['y0']-pad):p['y1']+pad,max(0,p['x']-pad):p['x']+p['w']+pad]
    k=48/max(8,p['cap']); g=cv2.resize(g,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(g,12,12,12,12,cv2.BORDER_CONSTANT,value=255)
def pagina(pg,L,dv):
    import nc_pag,nc_linha
    from nccomum import lote
    r=L[str(pg)]
    toks=[dict(j=j,x=c[0],base=c[1],w=c[2],cap=c[3],txt=c[4],conf=c[5],y0=c[6],y1=c[7],man=False) for j,c in enumerate(r['c'])]
    for t in toks:
        lab=dv.get((pg,t['j']))
        if lab is None: continue
        if lab=='-': t['txt']=None
        elif lab.startswith('W:'): t['txt']='~'; t['inteiro']=lab[2:]
        else: t['txt']=lab; t['conf']=1.0; t['man']=True
    toks=[t for t in toks if t['txt'] is not None]
    e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0); H,W=e.shape
    capm=float(np.median([t['cap'] for t in toks])) if toks else float(r.get('cap') or 22.0)
    # --- linhas de cifras: pelos pedaços lidos (linha de base) ...
    grupos=[]
    for t in sorted(toks,key=lambda t:t['base']):
        if grupos and t['base']-float(np.median([q['base'] for q in grupos[-1]]))<0.6*capm: grupos[-1].append(t)
        else: grupos.append([t])
    linhas=[]            # (palavras, tokens da linha)
    for g in grupos:
        xs=np.array([t['x'] for t in g],float); bs=np.array([t['base'] for t in g],float)
        if len(g)>=3 and np.ptp(xs)>10*capm:
            co=np.polyfit(xs,bs,1); pts=[(0.0,float(np.polyval(co,0))),(float(W),float(np.polyval(co,W)))]
        else: pts=[(0.0,float(np.median(bs))),(float(W),float(np.median(bs)))]
        ps,_e,_c=nc_linha.palavras(pg,pts,cap=capm,lim=170)
        linhas.append(([p for p in ps if 0.72*capm<=p['cap']<=1.35*capm],g))
    # --- ... e as linhas em que nada foi lido (acima do 1º pentagrama de cada sistema)
    rows,_e,_cap=nc_pag.linhas(pg,lim=170)
    bases=[float(np.median([t['base'] for t in g])) for g in grupos]
    vazias=[]
    for rw in rows:
        ws=[p for p in rw if 0.8*capm<=p['cap']<=1.25*capm]
        if len(ws)<2: continue
        b=float(np.median([p['base'] for p in ws]))
        if any(abs(b-bb)<1.5*capm for bb in bases): continue
        vazias.append(ws)
    todas=[p for ps,g in linhas for p in ps]+[p for ws in vazias for p in ws]
    res=lote([_img(e,p) for p in todas],psm=7,tag='pal') if todas else []
    lido={id(p):(normal(t),c) for p,(t,c) in zip(todas,res)}
    usados=set(); out=[]; pend=[]; soltas=[]; novas_man=[]; est=dict(palavras=0,iguais=0,diverg=0,linhas_novas=0)
    def P(p,tipo,S,conf,lidos): pend.append(dict(pg=pg,x=p['x'],base=p['base'],w=p['w'],cap=p['cap'],y0=p['y0'],y1=p['y1'],ocr=S,conf=conf,tipo=tipo,lidos=lidos))
    def manual(p,T):
        ex=extra(pg,p)
        if ex is None: return False
        if ex=='=': return True
        for t in T: usados.add(id(t))
        if ex.startswith('<'): novas_man.append((p,ex[1:])); return True
        if ex=='-': return True
        pts=ex.split()
        if len(pts)==1: out.append([p['x'],p['base'],p['w'],p['cap'],ex,1.0,p['y0'],p['y1']]); return True
        cs=sorted(p['cs']); vaos=sorted(((cs[i+1][0]-max(c[2] for c in cs[:i+1]),i) for i in range(len(cs)-1)),reverse=True)[:len(pts)-1]
        cortes_=sorted(i for _,i in vaos); ini=0
        for q,tx in enumerate(pts):
            fim=cortes_[q]+1 if q<len(cortes_) else len(cs)
            g=cs[ini:fim]; ini=fim
            if g and tx!='-': out.append([min(c[0] for c in g),p['base'],max(c[2] for c in g)-min(c[0] for c in g),p['cap'],tx,1.0,min(c[1] for c in g),max(c[3] for c in g)])
        return True
    est['words']=[dict(pg=pg,x=p['x'],base=p['base'],S=lido[id(p)][0],conf=lido[id(p)][1],toks=' '.join(t['txt'] for t in sorted(g,key=lambda t:t['x']) if min(t['x']+t['w'],p['x']+p['w'])-max(t['x'],p['x'])>0)) for ps,g in linhas for p in ps]
    falsas=[]
    for ps,g in linhas:
        sem=[p for p in ps if not any(min(t['x']+t['w'],p['x']+p['w'])-max(t['x'],p['x'])>0 for t in g) and 0.8*capm<=p['cap']<=1.25*capm]
        nao=[p for p in sem if not ACORDE.match(lido[id(p)][0]) or lido[id(p)][1]<50]
        if len(nao)>=3 and len(g)<=2 and not any(t['man'] for t in g):
            falsas.append(g)
            for t in g: t['txt']='~'
    linhas=[(ps,g) for ps,g in linhas if g not in falsas]
    est['falsas']=sum(len(g) for g in falsas)
    naoconf=[]
    for ps,g in linhas:
        for p in ps:
            est['palavras']+=1
            T=sorted([t for t in g if min(t['x']+t['w'],p['x']+p['w'])-max(t['x'],p['x'])>0],key=lambda t:t['x'])
            if any(id(t) in usados for t in T): continue
            if manual(p,T): continue
            S,conf=lido[id(p)]
            if not T: soltas.append((p,S,conf)); continue
            inteiro=[t['inteiro'] for t in T if t.get('inteiro')]
            if inteiro:
                for t in T: usados.add(id(t))
                out.append([p['x'],p['base'],p['w'],p['cap'],inteiro[0],1.0,p['y0'],p['y1']]); continue
            resto=sum(c[2]-c[0] for c in p['cs'] if not any(t['x']-2<=(c[0]+c[2])/2<=t['x']+t['w']+2 for t in T))
            todos_lidos=all(t['txt'] not in ('?','~') for t in T)
            if len(T)==1 and todos_lidos and resto<0.4*capm:
                t=T[0]
                # segunda opinião: a palavra inteira lida de novo
                if S==t['txt']: est['iguais']+=1
                elif not t['man'] and ACORDE.match(S) and conf>=75: est['diverg']+=1; P(p,'divergente',S,conf,[t['txt']])
                elif not t['man']: naoconf.append(dict(pg=pg,x=p['x'],base=p['base'],w=p['w'],cap=p['cap'],y0=p['y0'],y1=p['y1'],ocr=S,conf=conf,lidos=[t['txt']]))
                x0=min(t['x'],p['x']); x1=max(t['x']+t['w'],p['x']+p['w'])
                t['x']=x0; t['w']=x1-x0; t['y0']=min(t['y0'],p['y0']); t['y1']=max(t['y1'],p['y1'])
                continue
            feito=False; melhor=None
            for partes in cortes(S,len(T)):
                ids=casar(partes,T)
                if ids is None: continue
                if melhor is None or len(partes)>len(melhor[0]): melhor=(partes,ids)
            if melhor:
                partes,ids=melhor
                if len(partes)==len(T) and all(pt==t['txt'] for pt,t in zip(partes,T)) and resto<0.4*capm: feito=True; est['iguais']+=1
                else:
                    cx=caixas(p,T,partes,ids)
                    if cx:
                        for t in T: usados.add(id(t))
                        out+=cx; feito=True
            if not feito:
                if todos_lidos and resto<0.4*capm:
                    # cifras coladas, todas lidas por inteiro: fica como está; se a releitura discordar, confere-se a olho
                    if conf>=75 and any(len(c)==len(T) for c in cortes(S,len(T))): est['diverg']+=1; P(p,'divergente',S,conf,[t['txt'] for t in T])
                    elif not all(t['man'] for t in T): naoconf.append(dict(pg=pg,x=p['x'],base=p['base'],w=p['w'],cap=p['cap'],y0=p['y0'],y1=p['y1'],ocr=S,conf=conf,lidos=[t['txt'] for t in T]))
                    continue
                P(p,'conserto',S,conf,[t['txt'] for t in T])
    for t in toks:
        if id(t) in usados or t['txt']=='~': continue
        out.append([t['x'],t['base'],t['w'],t['cap'],t['txt'],t['conf'],t['y0'],t['y1']])
    # palavras soltas na linha das cifras: pedaço de uma cifra vizinha (separado pela haste de uma nota) ou cifra que ficou sem ler
    def viz(p):
        mesma=[c for c in out if abs(c[1]-p['base'])<0.5*capm]
        esq=[c for c in mesma if c[0]+c[2]<=p['x']+3]; dire=[c for c in mesma if c[0]>=p['x']+p['w']-3]
        a=max(esq,key=lambda c:c[0]+c[2]) if esq else None; b=min(dire,key=lambda c:c[0]) if dire else None
        return a,(p['x']-(a[0]+a[2]) if a else 1e9),b,(b[0]-(p['x']+p['w']) if b else 1e9)
    def juntar(c,p,txt):
        x0=min(c[0],p['x']); x1=max(c[0]+c[2],p['x']+p['w'])
        c[0]=x0; c[2]=x1-x0; c[4]=txt; c[5]=max(c[5],0.97); c[6]=min(c[6],p['y0']); c[7]=max(c[7],p['y1'])
    for p,txt in novas_man:
        a,ga,b,gb=viz(p)
        if a is not None and ga<1.5*capm: juntar(a,p,txt)
        else: out.append([p['x'],p['base'],p['w'],p['cap'],txt,1.0,p['y0'],p['y1']])
    for p,S,conf in sorted(soltas,key=lambda q:q[0]['x']):
        if any(min(c[0]+c[2],p['x']+p['w'])-max(c[0],p['x'])>0 and abs(c[1]-p['base'])<0.5*capm for c in out): continue     # já coberta
        a,ga,b,gb=viz(p)
        if ga<0.6*capm:
            if a[4]!='?' and (a[4].endswith(S) or S==a[4]) and p['w']<1.2*capm: juntar(a,p,a[4])
            elif a[4]!='?' and ACORDE.match(a[4]+S) and conf>=40: juntar(a,p,a[4]+S)
            else: P(p,'pedaço',S,conf,[a[4]])
        elif gb<0.6*capm:
            if b[4]!='?' and ACORDE.match(S+b[4]) and conf>=40: juntar(b,p,S+b[4])
            else: P(p,'pedaço',S,conf,[b[4]])
        elif ACORDE.match(S) and conf>=55: out.append([p['x'],p['base'],p['w'],p['cap'],S,0.97,p['y0'],p['y1']])
        elif S and 0.8*capm<=p['cap']<=1.25*capm: P(p,'nova',S,conf,[])
    # linhas em que nada tinha sido lido: valem quando a maioria das palavras é cifra
    for ws in vazias:
        V=[p for p in ws if ACORDE.match(lido[id(p)][0]) and lido[id(p)][1]>=60]
        if len(V)<2 or len(V)<0.4*len(ws): continue
        b=float(np.median([p['base'] for p in V]))
        if float(np.max(np.abs(np.array([p['base'] for p in V])-b)))>0.5*capm: continue
        est['linhas_novas']+=1
        for p in ws:
            if abs(p['base']-b)>0.45*capm: continue
            if manual(p,[]): continue
            S,conf=lido[id(p)]
            if p in V: out.append([p['x'],p['base'],p['w'],p['cap'],S,0.9,p['y0'],p['y1']])
            P(p,'linha-nova',S,conf,[])            # linha inteira que a leitura normal pulou: tudo conferido a olho
    for b in LINHAS_MAO.get(pg,[]):
        ps,_e,_c=nc_linha.palavras(pg,[(0.0,float(b)),(float(W),float(b))],cap=capm,lim=170)
        ps=[p for p in ps if 0.72*capm<=p['cap']<=1.35*capm]
        rs=lote([_img(e,p) for p in ps],psm=7,tag='pal') if ps else []
        for p,(tx,cf) in zip(ps,rs):
            est['words'].append(dict(pg=pg,x=p['x'],base=p['base'],S=normal(tx),conf=cf,toks=''))
            if manual(p,[]): continue
            P(p,'linha-nova',normal(tx),cf,[])
    for x0,x1,b,txt in ADIC.get(pg,[]):
        # o que já houver nesse lugar sai (cifra lida pela metade, pedaço lido em separado)
        out[:]=[c for c in out if not (abs(c[1]-b)<0.6*capm and min(c[0]+c[2],x1)-max(c[0],x0)>0.5*c[2])]
        out.append([int(x0),int(b),int(x1-x0),int(round(capm)),txt,1.0,int(b-capm),int(b)])
    est['absorvidas']=absorver(pg,out,capm)
    out.sort(key=lambda c:(c[1],c[0]))
    est['naoconf']=naoconf
    return pg,out,pend,est
def _um(a): 
    try: return pagina(*a)
    except Exception as ex:
        import traceback; return a[0],None,traceback.format_exc()[-600:],None
if __name__=='__main__':
    from multiprocessing import Pool
    L=json.load(open('/tmp/cif/nc_decidido.json')); P=json.load(open('/tmp/nc/final/paginas.json'))
    D=json.load(open('/tmp/cif/nc_duvidas.json')); assert len(D)==len(MANUAL),(len(D),len(MANUAL))
    dv={(pg,j):lab for (pg,j,x0,base),lab in zip(D,MANUAL)}
    novas=sorted(int(k) for k,v in P.items() if v['src'].startswith('nf') and k in L)
    R={}; PEND=[]; antes=depois=0
    with Pool(2) as p:
        EST={}; NC=[]; WORDS=[]
        for pg,out,pend,est in p.imap_unordered(_um,[(pg,L,dv) for pg in novas],chunksize=3):
            if out is None: print(pg,'ERRO',pend); continue
            R[pg]=out; PEND+=pend
            NC+=est.pop('naoconf'); WORDS+=est.pop('words')
            for k,v in est.items(): EST[k]=EST.get(k,0)+v
        NC.sort(key=lambda d:(d['pg'],d['base'],d['x'])); json.dump(NC,open('/tmp/cif/nc_naoconf.json','w')); json.dump(WORDS,open('/tmp/cif/nc_words.json','w'))
        print('conferência:',EST,'| sem confirmação da 2ª leitura:',len(NC))
    for pg in novas:
        if pg not in R: continue
        a=L[str(pg)]['c']; antes+=sum(1 for c in a if c[4]!='?'); depois+=sum(1 for c in R[pg] if c[4]!='?')
    json.dump({str(k):v for k,v in R.items()},open('/tmp/cif/nc_palavras.json','w'))
    PEND.sort(key=lambda d:(d['pg'],d['base'],d['x'])); json.dump(PEND,open('/tmp/cif/nc_pend.json','w'))
    print('páginas',len(R),'cifras antes',antes,'depois',depois,'ainda "?":',sum(1 for v in R.values() for c in v if c[4]=='?'),'| pendências para ler a olho:',len(PEND),{t:sum(1 for d in PEND if d['tipo']==t) for t in ('nova','conserto','pedaço','divergente','linha-nova')})
