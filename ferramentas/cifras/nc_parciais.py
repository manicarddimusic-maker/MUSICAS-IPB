"""Auditoria: cifras lidas só pela metade (ex.: "C/E" lida como "C"): a palavra impressa continua além do lugar lido.
Saída: /tmp/cif/nc_parciais.json {pg: [[x, base, w, cap, y0, y1, txt_lido, x_palavra, w_palavra]]}"""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from multiprocessing import Pool
def um(pg):
    try:
        import nc_slots,nc_pag,nc_linha
        sl=nc_slots.slots(pg,extra=False)
        if not sl: return pg,[]
        out=[]
        for pts in nc_pag.linhas(pg):
            ps,e,cap=nc_linha.palavras(pg,pts,lim=170)
            for p in ps:
                dentro=[o for o in sl if min(o['x']+o['w'],p['x']+p['w'])-max(o['x'],p['x'])>0 and abs(o['base']-p['base'])<0.8*cap]
                if not dentro or p['w']>9*cap: continue
                cob=sum(min(o['x']+o['w'],p['x']+p['w'])-max(o['x'],p['x']) for o in dentro)
                if p['w']-cob>=0.55*cap:
                    for o in dentro:
                        if o['txt']!='?': out.append([o['x'],o['base'],o['w'],o['cap'],o['y0'],o['y1'],o['txt'],p['x'],p['w'],p['y0'],p['y1'],p['base']])
        return pg,out
    except Exception as ex:
        import traceback; return pg,'ERRO '+traceback.format_exc()[-200:]
if __name__=='__main__':
    L=json.load(open('/tmp/cif/nc_decidido.json')); pgs=sorted(int(k) for k in L)
    res={}; tot=0; lidas=0
    with Pool(2) as p:
        for pg,r in p.imap_unordered(um,pgs,chunksize=6):
            if isinstance(r,str): print(pg,r); continue
            if r: res[pg]=r; tot+=len(r)
    for k in L: lidas+=sum(1 for c in L[k]['c'] if c[4]!='?')
    json.dump(res,open('/tmp/cif/nc_parciais.json','w'))
    print('páginas',len(pgs),'cifras lidas',lidas,'| lidas pela metade:',tot,'em',len(res),'páginas')
    import collections
    print(collections.Counter(x[6] for r in res.values() for x in r).most_common(25))
