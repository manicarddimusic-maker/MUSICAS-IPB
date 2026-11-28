"""Para cada foto da aba Hinos – Partitura: procura a mesma folha entre as fontes já lidas
(HNC Cifras, PDFs digitais do usuário, páginas do Hinário Novo Cântico) e traz as cifras."""
import sys,json,os,re,time,traceback
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from multiprocessing import Pool
R='/home/claude/musicas-ipb/public'
def fontes_do_hino(num,rot):
    """lista de (chave, caminho da imagem, folha) candidatas para o hino"""
    HC=json.load(open(R+'/data/cifras/hinoscifra.json'))['folhas']
    out=[]
    for img,f in HC.items():
        m=re.search(r'/u-(\d+)(-a)?-\d\.jpg$',img)
        if m and int(m.group(1))==num: out.append(('exata:'+img,R+img,f))
    # página original (duas colunas) do PDF "Novo Cântico – Cifras": casa com foto da página impressa
    PH=json.load(open('/tmp/cif/pdfhc.json'))
    for rot_ in (str(num),f'{num}-A'):
        for p in PH['pags'].get(rot_,[]):
            if any(o[0]==f'pdf:{p}' for o in out): continue
            f=dict(PH['paginas'][str(p)])
            if PH['tons'].get(str(num)): f['k']=PH['tons'][str(num)]
            out.append((f'pdf:{p}',f'/tmp/hc/pg/p-{p:03d}.png',f))
    FOL=json.load(open('/tmp/nc/final/folhas.json')); L=json.load(open('/tmp/cif/nc_decidido.json'))
    for F in FOL:
        if re.fullmatch(r'%d(-A)?'%num,F['rot']):
            for p in F['pages']:
                r=L.get(str(p['pg']))
                if not r: continue
                ok=[c for c in r['c'] if c[4]!='?']
                if len(ok)<3: continue
                folha=dict(w=r['w'],h=r['h'],f='s',c=[[c[0],c[1],c[2],round(c[3]/0.711,1),c[4]] for c in r['c']])
                out.append((f"nc:{p['pg']}",f"/tmp/nc/final/p{p['pg']:03d}.png",folha))
    return out
def um(arg):
    num,rot,img=arg
    fn='/tmp/cif/transf/'+img.strip('/').replace('/','__')[:-4]+'.json'
    if os.path.exists(fn): return img,'ja'
    try:
        from registro import transferir,_feats,casar_pontos,Registro,feats
        dst=cv2.imread(R+img); dg=cv2.cvtColor(dst,cv2.COLOR_BGR2GRAY); fd=_feats(dg)
        cand=[]
        for chave,caminho,folha in fontes_do_hino(num,rot):
            sg=cv2.imread(caminho,0)
            if sg is None: continue
            S,D=casar_pontos(feats(chave,sg),fd); n=Registro(S,D).n
            cand.append((n,chave,caminho,folha))
        cand.sort(key=lambda c:-c[0])
        res=dict(img=img,cands=[(c[0],c[1]) for c in cand],folha=None,de=[])
        cs=[]; base=None; tipo=None
        for n,chave,caminho,folha in cand:
            if n<18: break
            t=chave.split(':')[0]
            if tipo and (t!=tipo or t=='exata'): continue        # várias páginas só do hinário (foto de página dupla)
            out,rel=transferir(cv2.imread(caminho,0),folha,dst,chave_src=chave,fd=fd)
            res.setdefault('tent',[]).append((chave,rel))
            if not out or len(out['c'])<max(3,(0.2 if t=='pdf' else 0.5)*len(folha['c'])): continue
            if t!='nc' and (float(np.median(rel['notas']))<0.62 or float((np.array(rel['notas'])>=0.5).mean())<0.9): continue
            if base is None: base=out; tipo=t
            elif out.get('r')!=base.get('r'): continue
            # não repete cifra no mesmo lugar (duas fontes da mesma página)
            novos=[c for c in out['c'] if not any(abs(c[0]-o[0])<0.6*o[3] and abs(c[1]-o[1])<0.6*o[3] for o in cs)]
            cs+=novos; res['de'].append((chave,rel))
        if base and cs:
            base['c']=sorted(cs,key=lambda c:(c[1],c[0])); res['folha']=base
        json.dump(res,open(fn,'w'),ensure_ascii=False)
        return img,(len(cs),[c[:2] for c in res['cands'][:3]])
    except Exception as ex:
        open(fn[:-5]+'.erro','w').write(traceback.format_exc()); return img,'ERRO '+str(ex)[:70]
if __name__=='__main__':
    os.makedirs('/tmp/cif/transf',exist_ok=True)
    C=json.load(open(R+'/data/catalogo.json'))
    H=[s for s in C['secoes'] if s['id']=='hinos'][0]
    args=[]
    for it in H['itens']:
        for p in it['paginas']:
            if '/u-' in p['img']: continue
            args.append((it['num'],str(it.get('rotulo') or it['num']),p['img']))
    print(len(args),'fotos',flush=True); t0=time.time()
    with Pool(2) as p:
        for i,(img,r) in enumerate(p.imap_unordered(um,args,chunksize=2)):
            print(i,os.path.basename(img),r,'%.0fs'%(time.time()-t0),flush=True)
    print('FIM %.0fs'%(time.time()-t0),flush=True)
