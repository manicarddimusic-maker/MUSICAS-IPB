import sys; sys.path.insert(0,'/tmp/cif')
import fitz,re,collections
from pdftok import letras,juntar,limpar
from acordes import eh_acorde
from louvor_rows import linhas,classificar,palavra_maiuscula
ROT=re.compile(r'^(\[.*\]?|.*\]|\(?\d+[xX]\)?|[=()\[\]/–—-]+|Intro:?|INT:?|Final:?|Fim|AMÉM|Passagem|Terminar|voltar=?|\(?2ª|VEZ[:)]?|\(Frase:)$')
MARCA=re.compile(r'^(INT\.?:?|Intro:?|VOLTAR:?|=|Final:?|FINAL:?|PASSAGEM:?|Passagem:?|Interlúdio:?)$')
def cifras_da_pagina(page):
    """devolve os tokens de cifra (já limpos) da página da pasta de louvor — decide linha por linha do PDF"""
    out=[];vistos=[]
    for b in page.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            if abs(l['dir'][0]-1)>1e-3: continue
            cs=[]
            for s in l['spans']:
                if s['size']<10.5: continue
                for c in s['chars']:
                    if c['c'].strip(): cs.append(dict(x0=c['bbox'][0],x1=c['bbox'][2],y=c['origin'][1],s=s['size'],c=c['c'],t=c['bbox'][1],b=c['bbox'][3],neg='Bold' in s['font']))
            if not cs: continue
            r=sorted(juntar(cs,folga=0.12),key=lambda t:t['x'])
            for t in r: t['neg']=all(c['neg'] for c in t['chars'])
            reg=[t for t in r if not t['neg']]
            val=[t for t in r if eh_acorde(t['txt']) or limpar(t)]
            rot=[t for t in r if not (eh_acorde(t['txt']) or limpar(t)) and ROT.match(t['txt'])]
            resto=len(r)-len(val)-len(rot)
            if not val: continue
            pal=[t for t in r if palavra_maiuscula(t['txt']) and not t['txt'].endswith(':') and not ROT.match(t['txt'])]
            acent=[t for t in r if re.fullmatch(r'[ÁÉÍÓÚÀÂÊÔÃÕÇ]+',t['txt'])]
            if not reg:
                # linha toda em negrito: título ou cifras (regra das palavras em maiúsculas)
                if (len(pal)>=2 and len(pal)>len(val)) or (len(pal)+len(acent)>=1 and len(val)<=len(pal)+len(acent)): continue
                ok=True
            else:
                # linha com letra normal: só é de cifras se praticamente tudo for acorde
                ok = resto==0 or (len(val)>=4 and resto<=1) or (len(val)>=8 and resto<=3)
            if ok:
                for t in r:
                    u=limpar(t)
                    if u: out.append(u)
                vistos.append((bool(reg),' '.join(t['txt'] for t in r)))
            else:
                # linha de letra com um trecho de cifras depois de um marcador ("INT:", "PARA VOLTAR =")
                k=next((i for i,t in enumerate(r) if MARCA.match(t['txt'])),None)
                peg=[]
                if k is not None:
                    for t in r[k+1:]:
                        u=limpar(t)
                        if u: peg.append(u)
                        elif t['txt'] in '()[]=': continue
                        else: break
                if peg:
                    out+=peg; vistos.append((True,' '.join(t['txt'] for t in peg)))
                elif len(val)>=2: vistos.append(('NAO',' '.join(t['txt'] for t in r)))
    return out,vistos
if __name__=='__main__':
    d=fitz.open('/home/claude/musicas-ipb/public/midias/pdf/cifras-pasta-de-louvor-2025.pdf')
    tot=0; reg=collections.Counter(); 
    for pn in range(len(d)):
        out,v=cifras_da_pagina(d[pn]); tot+=len(out)
        for r,t in v:
            if r=='NAO': print('  recusada p',pn+1,t)
            elif r: reg[(pn+1,t)]+=1
    print('cifras',tot)
    um=collections.Counter(t for (p,t),n in reg.items() for _ in range(n) if len(t.split())==1)
    print('linhas normais de 1 token:',um.most_common(40))
    print('linhas normais com mais tokens (amostra):')
    for (p,t),n in list(reg.items()):
        pass
