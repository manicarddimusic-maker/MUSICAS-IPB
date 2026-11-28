import sys,json,os,glob,time,traceback
sys.path.insert(0,'/tmp/cif')
from multiprocessing import Pool
def um(f):
    fn='/tmp/cif/cad_bruto/'+os.path.basename(f)[:-4]+'.json'
    if os.path.exists(fn): return f,'ja'
    try:
        from cad import bruto
        r=bruto(f); json.dump(r,open(fn,'w'),ensure_ascii=False); return f,len(r['toks'])
    except Exception as ex:
        open(fn[:-5]+'.erro','w').write(traceback.format_exc()); return f,'ERRO '+str(ex)[:60]
if __name__=='__main__':
    os.makedirs('/tmp/cif/cad_bruto',exist_ok=True)
    fs=sorted(glob.glob('/home/claude/musicas-ipb/public/midias/caderninho3/*.jpg')); t0=time.time()
    with Pool(2) as p:
        for i,(f,r) in enumerate(p.imap_unordered(um,fs,chunksize=3)):
            if i%20==0 or (isinstance(r,str) and r.startswith('ERRO')): print(i,os.path.basename(f),r,'%.0fs'%(time.time()-t0),flush=True)
    print('FIM %.0fs'%(time.time()-t0))
