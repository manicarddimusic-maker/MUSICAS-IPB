"""Lugares de cifra de uma página do hinário: as lidas (com texto ou "?") + as "sobras" (palavras com cara de cifra
que a leitura automática deixou de fora, em linhas de cifras). Usado para conferência manual e para levar às fotos."""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import numpy as np
from nc_decidir import decidir
_L=None
def lido(pg):
    global _L
    if _L is None: _L=json.load(open('/tmp/cif/nc_decidido.json'))
    return _L.get(str(pg))
def bruto_usado(pg):
    """o arquivo bruto cuja decisão coincide com a guardada"""
    r=lido(pg); cand=[]
    for d in ('bruto','bruto2'):
        f=f'/tmp/cif/{d}/p{pg:03d}.json'
        if os.path.exists(f): cand.append(json.load(open(f)))
    if not cand: return None
    if r is None or len(cand)==1: return cand[0]
    def dist(b):
        x=decidir(b); return abs(len(x['c'])-len(r['c']))+sum(1 for a,c in zip(x['c'],r['c']) if a[:5]!=c[:5])
    return min(cand,key=dist)
def extras(pg):
    """lugares completados à mão (nc_linha.py): [(x, base, w, cap, y0, y1, rótulo)]"""
    fn=f'/tmp/cif/slots_extra/{pg}.txt'; out=[]
    if os.path.exists(fn):
        for ln in open(fn):
            p=ln.split()
            if len(p)>=7:
                # rótulo: "TXT" (cifra impressa), "TXT=LIT" (impressa + o que está escrito à mão por cima), "=LIT", "TXT=x" (riscada, sem nada escrito)
                out.append(dict(x=int(p[0]),base=int(p[1]),w=int(p[2]),cap=int(p[3]),y0=int(p[4]),y1=int(p[5]),txt=p[6],org='manual'))
    return out
def slots(pg,extra=True):
    out=_slots(pg)
    if not extra: return out
    ex=extras(pg)
    if not ex: return out
    capp=float(np.median([o['cap'] for o in out])) if out else 21.0
    for m in ex:
        # o lugar feito à mão substitui o que a leitura automática tinha no mesmo ponto
        out=[o for o in out if not (min(o['x']+o['w'],m['x']+m['w'])-max(o['x'],m['x'])>0 and abs(o['base']-m['base'])<0.8*capp)]
        if m['txt']!='-': out.append(dict(m))
    out.sort(key=lambda o:(round(o['base']/(2.5*capp)),o['x']))
    return out
def _slots(pg):
    r=lido(pg); b=bruto_usado(pg)
    out=[]
    if r:
        for c in r['c']: out.append(dict(x=c[0],base=c[1],w=c[2],cap=c[3],txt=c[4],org='lida',y0=c[6],y1=c[7]))
    if not b: return out
    capp=r['cap'] if r else b['cap']
    T=[t for t in b['toks'] if 0.8*capp<=t['cap']<=1.35*capp and (t['x1']-t['x0'])>=0.4*capp]
    def ocupado(t):
        return any(min(t['x1'],o['x']+o['w'])-max(t['x0'],o['x'])>-0.1*capp and abs(t['base']-o['base'])<0.8*capp for o in out)
    sob=[t for t in T if not ocupado(t)]
    # inclinação da página: pelas linhas lidas (base em função de x)
    incl=0.0
    lid=[o for o in out]
    if len(lid)>=6:
        # pares na mesma linha
        ds=[]
        for i,a in enumerate(lid):
            for bb in lid[i+1:]:
                dx=bb['x']-a['x']
                if abs(dx)>6*capp and abs(bb['base']-a['base'])<0.03*abs(dx)+0.5*capp: ds.append((bb['base']-a['base'])/dx)
        if len(ds)>=4: incl=float(np.median(ds))
    def nivel(t): return (t['base'] if 'x0' in t else t['base'])-incl*(t['x0'] if 'x0' in t else t['x'])
    linhas_lidas=sorted({round(o['base']-incl*o['x']) for o in lid})
    novos=[]
    # (a) sobra alinhada com uma linha lida (compara com a cifra lida mais próxima em x: a linha pode estar inclinada)
    from nc_decidir import em_linhas
    rows=em_linhas(r['c'],r['cap']) if r else []
    def desvio(t,rw):
        o=min(rw,key=lambda o:abs(o[0]-t['x0'])); return t['base']-o[1],abs(o[0]-t['x0'])
    resto=[]
    for t in sob:
        ok=False
        for rw in rows:
            dv,dx=desvio(t,rw)
            if abs(dv)<0.45*capp+0.03*dx: ok=True; break
        if ok: novos.append(t)
        else: resto.append(t)
    # (b) três ou mais sobras alinhadas entre si, pelo menos uma com pauta logo abaixo, com cara de cifra
    resto=[t for t in resto if t['c'] and t['c'][0][0]>=0.55]
    resto.sort(key=lambda t:t['base']-incl*t['x0'])
    i=0
    while i<len(resto):
        g=[resto[i]]; j=i+1
        while j<len(resto) and (resto[j]['base']-incl*resto[j]['x0'])-(g[0]['base']-incl*g[0]['x0'])<0.7*capp: g.append(resto[j]); j+=1
        # não pode estar dentro da faixa de uma linha de cifras já lida (seria crédito/título logo acima dela)
        colado=False
        for t in g:
            for rw in rows:
                dv,dx=desvio(t,rw)
                if -5.2*capp-0.03*dx<dv<1.6*capp+0.03*dx: colado=True
        if len(g)>=3 and not colado and any(t['pa'] for t in g) and sum(1 for t in g if t['c'][0][0]>=0.7)>=2: novos+=g
        i=j
    for t in novos:
        palp=t['c'][0] if t['c'] else None
        out.append(dict(x=t['x0'],base=t['base'],w=t['x1']-t['x0'],cap=t['cap'],txt='?',org='sobra',y0=t['y0'],y1=t['y1'],palpite=palp))
    out.sort(key=lambda o:(o['base']-incl*o['x'],o['x']))
    return out
if __name__=='__main__':
    for pg in [int(a) for a in sys.argv[1:]] or [49,25,48]:
        s=slots(pg); print(pg,'lidas',sum(1 for o in s if o['org']=='lida'),'("?"',sum(1 for o in s if o['org']=='lida' and o['txt']=='?'),') sobras',sum(1 for o in s if o['org']=='sobra'))
        for o in s:
            if o['org']=='sobra': print('   sobra',o['x'],o['base'],o['w'],o.get('palpite'))
