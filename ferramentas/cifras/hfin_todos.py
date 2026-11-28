import sys,glob,os,json
sys.path.insert(0,'/tmp/cif')
from multiprocessing import Pool
from hinos_final import FORA
def um(n):
    import hfin_b
    try:
        o=hfin_b.analisar(n,debug=True)
        return n,[(L['fonte'],len(L['cif']),len(L['riscos']),len(L['letras'])) for L in o['linhas']]
    except Exception as ex:
        import traceback; return n,'ERRO '+traceback.format_exc()[-300:]
if __name__=='__main__':
    ns=[os.path.basename(f)[:-5] for f in sorted(glob.glob('/tmp/cif/hfin/h*.json')) if not f.endswith('.b.json')]
    ns=[n for n in ns if not any(n.startswith(p) for p in FORA)]
    with Pool(2) as p:
        for n,r in p.imap_unordered(um,ns):
            if isinstance(r,str): print(n,r)
            else: print(n,'linhas',len(r),'cifras',sum(x[1] for x in r),'riscos',sum(x[2] for x in r),'letras',sum(x[3] for x in r),flush=True)
