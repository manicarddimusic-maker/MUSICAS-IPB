import json,os
R='/home/claude/musicas-ipb/public/'
C=json.load(open(R+'data/catalogo.json'))
tot=dict(it=0,ok=0)
for s in C['secoes']:
    fn=R+f'data/cifras/{s["id"]}.json'
    J=json.load(open(fn))['folhas'] if os.path.exists(fn) else {}
    n=len(s['itens']); ok=0; todas=0; sem=[]
    for it in s['itens']:
        tem=[p['img'] in J and any(c[4]!='?' for c in J[p['img']]['c']) for p in it['paginas']]
        if any(tem): ok+=1
        else: sem.append(it.get('rotulo') or it.get('num') or it['titulo'][:18])
        if all(tem): todas+=1
    tot['it']+=n; tot['ok']+=ok
    print(f"{s['id']:12s} {s['titulo'][:28]:28s} músicas {n:4d} | com troca de tom {ok:4d} ({100*ok//max(1,n)}%) | todas as folhas {todas:4d} | sem: {str(sem[:14])[:150]}")
print('TOTAL',tot,round(100*tot['ok']/tot['it'],1),'%')
