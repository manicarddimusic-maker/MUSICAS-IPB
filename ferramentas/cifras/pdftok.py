"""Cifras tiradas do texto de um PDF (posição exata de cada acorde)."""
import fitz,re,sys
sys.path.insert(0,'/tmp/cif')
from acordes import eh_acorde
def letras(page,sel):
    out=[]
    for b in page.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            if abs(l['dir'][0]-1)>1e-3 or abs(l['dir'][1])>1e-3: continue
            for s in l['spans']:
                if not sel(s): continue
                for c in s['chars']:
                    if not c['c'].strip(): continue
                    out.append(dict(x0=c['bbox'][0],x1=c['bbox'][2],y=c['origin'][1],s=s['size'],c=c['c'],t=c['bbox'][1],b=c['bbox'][3]))
    return out
def juntar(chars,folga=0.16,dy_max=0.82,dy_abs=0.0):
    """junta letras vizinhas em palavras; aceita expoentes/índices (deslocados na vertical)"""
    chars=sorted(chars,key=lambda c:(c['x0'],c['y']))
    n=len(chars); pai=list(range(n))
    def acha(i):
        while pai[i]!=i: pai[i]=pai[pai[i]]; i=pai[i]
        return i
    for i in range(n):
        a=chars[i]
        for j in range(i+1,n):
            b=chars[j]
            S=max(a['s'],b['s'])
            if b['x0']-a['x1']>folga*S: 
                if b['x0']-a['x0']>3*S: break
                continue
            if abs(a["y"]-b["y"])>max(dy_max*S,dy_abs): continue
            # vizinhos (b começa perto do fim de a) ou empilhados (expoente sobre índice)
            if b['x0']>=a['x0']-0.01 and b['x0']-a['x1']<=folga*S:
                if abs(a['y']-b['y'])<0.01 or b['x0']-a['x1']>-0.9*min(a['x1']-a['x0'],b['x1']-b['x0'])-0.01 or True:
                    pai[acha(i)]=acha(j)
    grupos={}
    for i in range(n): grupos.setdefault(acha(i),[]).append(chars[i])
    toks=[]
    for g in grupos.values():
        g.sort(key=lambda c:(c['x0'],c['y']))
        # linha de base: a da primeira letra de tamanho cheio
        smax=max(c['s'] for c in g)
        cheias=[c for c in g if c['s']>=smax-0.3 and not (c['c']=='o' and any(abs(c['y']-o['y'])>1 and o['s']>=smax-0.3 and o['c']!='o' for o in g))]
        base=cheias[0]['y'] if cheias else g[0]['y']
        # se quase todas as letras cheias estão noutra linha de base, usa a mais comum
        ys=[round(c['y'],1) for c in cheias if c['c']!='o']
        if ys: base=max(set(ys),key=ys.count)
        txt='';ant=None
        for c in g:
            ch=c['c']
            dy=c['y']-base
            if ch=='o' and dy<-1.5: ch='º'
            if ant is not None and dy>1.5 and (ant['y']-base)<-1.5 and c['x0']<ant['x1']-0.2: txt+='/'
            txt+=ch; ant=c
        x0=min(c['x0'] for c in g); x1=max(c['x1'] for c in g)
        sobe=base-min(c['y']-0.70*c['s'] for c in g)   # altura das maiúsculas ≈ 0,66–0,70 do corpo
        desce=max(c['y']+(0.24*c['s'] if c['c'] in '()gjpqy,;' else 0.03*c['s']) for c in g)-base
        toks.append(dict(x=x0,w=x1-x0,base=base,s=smax,txt=txt,sobe=sobe,desce=desce,chars=g))
    toks.sort(key=lambda t:(round(t['base']),t['x']))
    return toks

SOBRAS='[](){}.,;:|*…'
def limpar(t):
    """tira pontuação grudada no começo/fim até sobrar um acorde; devolve o token ajustado ou None"""
    if eh_acorde(t['txt']): return t
    g=t['chars']
    if len(g)!=len(t['txt']): return None      # tem "/" ou "º" inserido: não mexe
    for a in range(0,4):
        for b in range(0,5):
            if a+b==0 or a+b>=len(g): continue
            if any(c['c'] not in SOBRAS for c in g[:a]+g[len(g)-b:]): continue
            sub=g[a:len(g)-b]; txt=t['txt'][a:len(g)-b]
            if eh_acorde(txt) and not txt.startswith('(') and not txt.endswith(')'):
                x0=min(c['x0'] for c in sub); x1=max(c['x1'] for c in sub)
                return dict(t,x=x0,w=x1-x0,txt=txt,chars=sub)
    return None
