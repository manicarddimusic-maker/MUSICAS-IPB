import sys,json,os,time,traceback
sys.path.insert(0,'/tmp/cif')
from multiprocessing import Pool
def um(pg):
    fn=f'/tmp/cif/bruto/p{pg:03d}.json'
    if os.path.exists(fn): return pg,'ja'
    try:
        from ncpagina import bruto_pagina
        r=bruto_pagina(pg); json.dump(r,open(fn,'w'),ensure_ascii=False)
        return pg,len(r['toks'])
    except Exception as ex:
        open(f'/tmp/cif/bruto/erro{pg:03d}.txt','w').write(traceback.format_exc())
        return pg,'ERRO '+str(ex)[:80]
if __name__=='__main__':
    from nccomum import PAG
    os.makedirs('/tmp/cif/bruto',exist_ok=True)
    pgs=sorted(PAG); t0=time.time()
    with Pool(2) as p:
        for i,(pg,r) in enumerate(p.imap_unordered(um,pgs,chunksize=4)):
            if i%20==0 or (isinstance(r,str) and r.startswith('ERRO')): print(i,pg,r,'%.0fs'%(time.time()-t0),flush=True)
    print('FIM %.0fs'%(time.time()-t0))
