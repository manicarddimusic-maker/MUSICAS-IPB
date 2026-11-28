"""Reconhecimento de texto de cifra (o mesmo critério para todas as fontes de dados)."""
import re
# raiz, sufixos permitidos, baixo; aceita vários acordes colados ("E-B", "GDG")
_UM=r'[A-G][#b]?(?:m(?!a)|maj|min|dim|aug|sus|add|M|º|°|ø|\+|-|[0-9]|\(|\)|,|[#b](?=[0-9])|(?<=[0-9])[#b]|/(?=[#b]?[0-9(]))*(?:/[A-G][#b]?)?'
ACORDE=re.compile(r'^(?:'+_UM+r')$')
ACORDES=re.compile(r'^\(?(?:(?:'+_UM+r')+|/[A-G][#b]?)\)?[.,;]?$')
def eh_acorde(t):
    t=t.replace('♯','#').replace('♭','b')
    return bool(ACORDES.match(t))
LETRAS='CDEFGAB'; SEMI=[0,2,4,5,7,9,11]
def primeiro(t):
    m=re.match(r'\(?([A-G])([#b]?)(.*)',t)
    if not m: return None
    pc=(SEMI[LETRAS.index(m.group(1))]+(1 if m.group(2)=='#' else -1 if m.group(2)=='b' else 0))%12
    resto=m.group(3)
    dim=bool(re.match(r'(º|°|dim|ø|m7\(b5\)|m7b5)',resto))
    menor=bool(re.match(r'(m(?!aj)|-)',resto)) and not dim
    return pc,('d' if dim else 'm' if menor else 'M'),m.group(1)+m.group(2)
def estimar_tom(acordes):
    """mesmo critério do aplicativo (src/tom.ts): devolve 'G', 'Em', 'Bb'..."""
    pares=[(a,primeiro(a)) for a in acordes]; pares=[(a,x) for a,x in pares if x]
    lidos=[x for a,x in pares]
    if not lidos: return None
    cad=[]
    for i in range(len(pares)-1):
        (ta,xa),(tb,xb)=pares[i],pares[i+1]
        if xa[1]=='M' and re.match(r'^\(?[A-G][#b]?7(?!M)',ta) and (xb[0]-xa[0])%12==5 and xb[1]!='d': cad.append((xb[0],xb[1]=='m'))
    MAIOR=[(0,'M'),(2,'m'),(4,'m'),(5,'M'),(7,'M'),(9,'m'),(11,'d')]
    MENOR=[(0,'m'),(2,'d'),(3,'M'),(5,'m'),(7,'m'),(7,'M'),(8,'M'),(10,'M'),(11,'d')]
    best=None
    for a in range(12):
        for menor in (False,True):
            graus=MENOR if menor else MAIOR; pts=0
            for pc,q,_ in lidos:
                d=(pc-a)%12
                if (d,q) in graus: pts+=1
                if d==0 and q==('m' if menor else 'M'): pts+=0.35
            ton=lambda x:(x[0]-a)%12==0 and x[1]==('m' if menor else 'M')
            if ton(lidos[-1]): pts+=max(2.5,len(lidos)*0.1)
            if ton(lidos[0]): pts+=max(1.0,len(lidos)*0.04)
            pts+=0.6*sum(1 for c in cad if c==(a,menor))
            if not menor: pts+=0.01
            if best is None or pts>best[0]: best=(pts,a,menor)
    _,a,menor=best
    nome=next((n for pc,q,n in lidos if pc==a),None)
    if nome is None:
        nome=(['C','C#','D','Eb','E','F','F#','G','G#','A','Bb','B'] if menor else ['C','Db','D','Eb','E','F','F#','G','Ab','A','Bb','B'])[a]
    return nome+('m' if menor else '')
