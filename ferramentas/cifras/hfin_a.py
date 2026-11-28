"""Etapa A (demorada, guardada): leva as cifras da página limpa do hinário para a foto só pela geometria."""
import sys,json,glob,os,re
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from multiprocessing import Pool
R='/home/claude/musicas-ipb/public'
from hinos_final import K,FORA,k_de,FONTE_FIXA
def um(f):
    try:
        from registro import transferir
        from transf_hinos import fontes_do_hino
        r=json.load(open(f)); img=r['img']; nome=os.path.basename(img)[:-4]
        out='/tmp/cif/hfin/'+nome+'.json'
        if os.path.exists(out): return nome,'ja'
        num=int(re.match(r'h(\d+)',nome).group(1))
        fontes={c[0]:c for c in fontes_do_hino(num,str(num))}
        dst=cv2.imread(R+img); res=[]
        fixa=[v for p,v in FONTE_FIXA.items() if nome.startswith(p)]
        import nc_slots
        if fixa: chaves=fixa[0]
        else:
            # todas as páginas do hino no hinário (mesmo as que a leitura automática não deu conta): quem decide é a geometria
            validadas=[d[0] for d in r['de']]
            FOL=json.load(open('/tmp/nc/final/folhas.json'))
            pgs=[]
            for F in FOL:
                if re.fullmatch(r'%d(-A)?'%num,F['rot']): pgs+=[p['pg'] for p in F['pages']]
            chaves=validadas+[f'nc:{p}' for p in sorted(set(pgs)) if f'nc:{p}' not in validadas]
        for chave in chaves:
            if chave in fontes: _,caminho,folha=fontes[chave]
            else: caminho=f"/tmp/nc/final/p{int(chave[3:]):03d}.png"; folha=dict(f='s')
            sg=cv2.imread(caminho,0)
            if chave.startswith('nc:'):
                # todos os lugares de cifra da página (inclui o que a leitura automática deixou de fora)
                sl=nc_slots.slots(int(chave[3:]))
                if not sl: continue
                folha=dict(folha); folha['w']=sg.shape[1]; folha['h']=sg.shape[0]
                folha['c']=[[o['x'],o['base'],o['w'],round(o['cap']/0.711,1),o['txt'],o['org']] for o in sl]
            o,rel=transferir(sg,folha,dst,chave_src=chave,modo='geom',min_inl=18 if chave in [d[0] for d in r['de']] or fixa else 20)
            if not o: continue
            # duas páginas não ocupam o mesmo lugar da foto: se esta cai em cima de outra já aceita, é casamento falso
            xs_=[p[4] for p in rel['pares']]; ys_=[p[5] for p in rel['pares']]
            cx=(min(xs_),min(ys_),max(xs_),max(ys_)); falso=False
            for q in res:
                a_=q['caixa']; ix=max(0,min(cx[2],a_[2])-max(cx[0],a_[0])); iy=max(0,min(cx[3],a_[3])-max(cx[1],a_[1]))
                area=max(1,(cx[2]-cx[0])*(cx[3]-cx[1]))
                if ix*iy>0.3*area: falso=True
            if falso or (res and o.get('r',0)!=res[0]['r']): continue
            res.append(dict(chave=chave,caminho=caminho,r=o.get('r',0),w=o['w'],h=o['h'],c=o['c'],pares=rel['pares'],inl=rel['inl'],f=folha.get('f','s'),n=folha.get('n'),k=folha.get('k'),caixa=cx))
        json.dump(dict(img=img,k=k_de(nome),fontes=res),open(out,'w'))
        return nome,[(x['chave'],len(x['c'])) for x in res]
    except Exception as ex:
        import traceback; return os.path.basename(f),'ERRO '+traceback.format_exc()[-300:]
if __name__=='__main__':
    fs=[]
    for f in sorted(glob.glob('/tmp/cif/transf/*.json')):
        r=json.load(open(f))
        nome=os.path.basename(r['img'])[:-4]
        if k_de(nome) is None: continue
        if not r['folha'] and not any(nome.startswith(p) for p in FONTE_FIXA): print('sem fonte:',nome); continue
        fs.append(f)
    print(len(fs),'fotos')
    with Pool(2) as p:
        for nome,d in p.imap_unordered(um,fs): print(nome,d,flush=True)
