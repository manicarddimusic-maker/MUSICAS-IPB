import sys,json,collections,re
sys.path.insert(0,'/tmp/cif')
from nccomum import *
from acordes import eh_acorde
from multiprocessing import Pool
def um(pg):
    try:
        b=base_da_pagina(pg); d=espaco_pauta(b); toks,lab,cap=candidatos(b,d)
        sel=[t for t in toks if t['cap']>=0.97*cap and t['sw']>=0.2*cap]
        r=lote([recorte(b,lab,t) for t in sel],7,f'c{pg}')
        return pg,[(a,c) for a,c in r]
    except Exception as ex:
        return pg,[('ERRO '+str(ex),0)]
if __name__=='__main__':
    boas=[pg for pg,v in sorted(PAG.items()) if v['cls']=='boa']
    am=boas[::9][:64]
    with Pool(2) as p: res=p.map(um,am)
    suf=collections.Counter(); raiz=collections.Counter(); baixo=collections.Counter(); tot=0
    for pg,r in res:
        for txt,conf in r:
            if txt.startswith('ERRO'): print(pg,txt); continue
            if conf<60 or not eh_acorde(txt): continue
            m=re.fullmatch(r'([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?',txt)
            if not m: continue
            tot+=1; raiz[m.group(1)]+=1; suf[m.group(2)]+=1; baixo[m.group(3) or '-']+=1
    print('páginas',len(am),'acordes lidos com confiança',tot)
    print('raízes',raiz.most_common()); print('baixos',baixo.most_common())
    print('sufixos',suf.most_common(120))
    json.dump(dict(suf=suf.most_common(),raiz=raiz.most_common(),baixo=baixo.most_common()),open('/tmp/cif/colheita.json','w'))
