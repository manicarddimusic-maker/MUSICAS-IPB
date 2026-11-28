import sys,json,os,glob,time,traceback
sys.path.insert(0,'/tmp/cif')
from multiprocessing import Pool
R='/home/claude/musicas-ipb/public'
def um(img):
    fn='/tmp/cif/foto_bruto/'+img.strip('/').replace('/','__')[:-4]+'.json'
    if os.path.exists(fn): return img,'ja'
    try:
        from foto import bruto
        r=bruto(R+img); r['img']=img; json.dump(r,open(fn,'w'),ensure_ascii=False); return img,len(r['toks'])
    except Exception as ex:
        open(fn[:-5]+'.erro','w').write(traceback.format_exc()); return img,'ERRO '+str(ex)[:60]
if __name__=='__main__':
    os.makedirs('/tmp/cif/foto_bruto',exist_ok=True)
    # espera a leitura do Novo Cântico terminar (usa os dois núcleos)
    C=json.load(open(R+'/data/catalogo.json'))
    U=json.load(open('/tmp/cif/user.json'))['folhas']
    imgs=[]; ORD=['caderninho','canticos','palavra','salmos','hinos']
    for s in sorted(C['secoes'],key=lambda s:ORD.index(s['id']) if s['id'] in ORD else 99):
        if s['id'] not in ORD: continue
        for it in s['itens']:
            for p in it['paginas']:
                if p['img'] not in U and p['img'] not in imgs: imgs.append(p['img'])
    print(len(imgs),'fotos',flush=True); t0=time.time()
    with Pool(2) as p:
        for i,(f,r) in enumerate(p.imap_unordered(um,imgs,chunksize=2)):
            if i%25==0 or (isinstance(r,str) and r.startswith('ERRO')): print(i,f,r,'%.0fs'%(time.time()-t0),flush=True)
    print('FIM %.0fs'%(time.time()-t0),flush=True)
