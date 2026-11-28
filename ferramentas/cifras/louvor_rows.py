import sys; sys.path.insert(0,'/tmp/cif')
import fitz,collections,re
from pdftok import letras,juntar
from acordes import eh_acorde
P='/home/claude/musicas-ipb/public/midias/pdf/'
def palavra_maiuscula(t):
    u=t.strip('.,;:!?()–-')
    return len(u)>=2 and u.isalpha() and u==u.upper() and not eh_acorde(t)
def linhas(T):
    rows=[]
    for t in sorted(T,key=lambda t:(t['base'],t['x'])):
        if rows and abs(rows[-1][0]['base']-t['base'])<0.35*t['s']: rows[-1].append(t)
        else: rows.append([t])
    for r in rows: r.sort(key=lambda t:t['x'])
    return rows
def classificar(rows):
    """devolve lista (row, tipo) — tipo 'titulo' ou 'cifras'"""
    out=[]
    for i,r in enumerate(rows):
        pal=[t for t in r if palavra_maiuscula(t['txt']) and not t['txt'].endswith(':')]
        val=[t for t in r if eh_acorde(t['txt'])]
        acent=[t for t in r if re.fullmatch(r'[ÁÉÍÓÚÀÂÊÔÃÕÇ]+',t['txt'])]
        if len(pal)>=2 or (len(pal)+len(acent)>=1 and (i==0 or not val)) : out.append((r,'titulo'))
        else: out.append((r,'cifras'))
    return out
if __name__=='__main__':
    d=fitz.open(P+'cifras-pasta-de-louvor-2025.pdf')
    for pn in range(len(d)):
        T=[t for t in juntar(letras(d[pn],lambda s:'Bold' in s['font'] and s['size']>=13.5),folga=0.12)]
        for r,tp in classificar(linhas(T)):
            txt=' '.join(t['txt'] for t in r)
            inval=[t['txt'] for t in r if not eh_acorde(t['txt'])]
            if tp=='titulo': print(f'T p{pn+1} y{r[0]["base"]:.0f}: {txt}')
            elif inval: print(f'  c p{pn+1} y{r[0]["base"]:.0f}: {txt}   <<{inval}')
            elif any(re.fullmatch(r'\(?[A-G]{2,}\)?',t['txt']) for t in r): print(f'  ? p{pn+1} y{r[0]["base"]:.0f}: {txt}')
