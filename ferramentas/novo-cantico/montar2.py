import cv2,numpy as np,json,collections,os,io,shutil,sys
from multiprocessing import Pool
from PIL import Image
P={int(k):v for k,v in json.load(open('/tmp/nc/final/paginas.json')).items()}
REF=json.load(open('/tmp/nc/titulos.json'))
TIT={r['rot']:r['titulo'] for r in REF}
TIT.update({'9':'Aleluia ao Deus Trino','21':'Deus de Abraão','56':'Ações de Graças e Súplica','61':'Ações de Graças','86':'Espírito do Eterno Deus','166':'Luz da Vida','307':'A Santa Igreja','374':'Saudando o Ano Novo','375':'O Ano Velho','400-A':'Ofertórios e Améns'})
NUM={r['rot']:r['num'] for r in REF}
ORD=[r['rot'] for r in REF]
HP=2000            # altura de cada página na imagem final
OUT='/tmp/nc/out_nc'; shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT)
# versões (músicas) de cada hino: cada página de título começa uma
sets=[]
for pg in sorted(P):
    v=P[pg]
    if v['role']=='T' or not sets or sets[-1]['hymn']!=v['hymn']:
        sets.append(dict(hymn=v['hymn'],pages=[pg]))
    else: sets[-1]['pages'].append(pg)
for s in sets:
    assert s['pages']==list(range(s['pages'][0],s['pages'][0]+len(s['pages']))),s
byh=collections.OrderedDict()
for s in sets: byh.setdefault(s['hymn'],[]).append(s)
def quant(a):
    """4 tons de cinza: branco, cinza claro (linhas fracas), cinza escuro, preto"""
    out=np.full(a.shape,3,np.uint8)
    out[a<228]=2; out[a<150]=1; out[a<62]=0
    return out
PAL=[0,0,0, 105,105,105, 188,188,188, 255,255,255]+[0]*(252*3)
def salvar(a,path):
    im=Image.fromarray(quant(a),mode='P'); im.putpalette(PAL)
    im.save(path,format='PNG',optimize=True,bits=2)
def fit(e,H):
    h,w=e.shape; s=H/h
    return cv2.resize(e,(max(1,int(round(w*s))),H),interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC),s
jobs=[]
for rot,ss in byh.items():
    k=0
    for s in ss:
        pgs=s['pages']
        for i in range(0,len(pgs),2):
            k+=1; par=pgs[i:i+2]
            tag=rot.lower().replace('-a','a')
            ver=max(P[pg].get('ver',0) for pg in par)       # folha refeita com foto nova ganha outro nome (o app guarda as imagens pelo nome)
            nome=f"nc-{int(NUM[rot]):03d}{'a' if rot.endswith('-A') else ''}-{k}{'' if ver==0 else '-v%d'%(ver+1)}.png"
            jobs.append(dict(rot=rot,nome=nome,par=par))
def work(j):
    ims=[cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0) for pg in j['par']]
    H=min(HP,max(i.shape[0] for i in ims))
    partes=[];info=[];x=0
    gap=int(0.035*H)
    for pg,im in zip(j['par'],ims):
        r,s=fit(im,H)
        info.append(dict(pg=pg,x0=x,s=s,w=r.shape[1]))
        partes.append(r); x+=r.shape[1]+gap
    if len(partes)==2:
        tela=np.full((H,partes[0].shape[1]+gap+partes[1].shape[1]),255,np.uint8)
        tela[:,:partes[0].shape[1]]=partes[0]; tela[:,partes[0].shape[1]+gap:]=partes[1]
    else: tela=partes[0]
    salvar(tela,f"{OUT}/{j['nome']}")
    return dict(nome=j['nome'],rot=j['rot'],w=int(tela.shape[1]),h=int(tela.shape[0]),pages=info,bytes=os.path.getsize(f"{OUT}/{j['nome']}"))
if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='extras':        # "python3 montar2.py extras": só refaz as folhas extras; as do livro ficam como estão
        res=json.load(open('/tmp/nc/final/folhas.json'))
    else:
        with Pool(2) as p: res=p.map(work,jobs,chunksize=8)
        json.dump(res,open('/tmp/nc/final/folhas.json','w'),ensure_ascii=False,indent=0)
    # folhas extras, fora do livro (versões da igreja montadas à parte; ver /tmp/nc/extras/extras.json):
    # a imagem tem o mesmo quadro de uma página do livro (pg_cifras), de onde vêm as cifras para a troca de tom
    extras=[]
    if os.path.exists('/tmp/nc/extras/extras.json'):
        for x in json.load(open('/tmp/nc/extras/extras.json')):
            im=cv2.imread(x['arquivo'],0); r,s=fit(im,min(HP,im.shape[0]))
            salvar(r,f"{OUT}/{x['nome']}")
            extras.append(dict(nome=x['nome'],rot=x['rot'],w=int(r.shape[1]),h=int(r.shape[0]),pages=[dict(pg=x['pg_cifras'],x0=0,s=s,w=int(r.shape[1]))],
                               bytes=os.path.getsize(f"{OUT}/{x['nome']}"),extra=True,rotulo=x.get('rotulo'),chave=x.get('chave')))
    json.dump(extras,open('/tmp/nc/final/folhas_extras.json','w'),ensure_ascii=False,indent=0)
    tot=sum(r['bytes'] for r in res)
    print(len(res),'folhas;',round(tot/1e6,1),'MB; media',round(tot/len(res)/1024),'KB')
    # entradas do catálogo
    itens=[]
    for rot in ORD:
        if rot not in byh: continue
        fl=[r for r in res if r['rot']==rot]
        d=dict(num=NUM[rot],titulo=TIT[rot],paginas=[f"/midias/nc/{r['nome']}" for r in fl])
        # as extras entram depois das folhas do livro, com nome próprio e tom guardado à parte
        # "chave": o nome com que a folha foi publicada pela 1ª vez — o tom e as anotações guardados no aparelho ficam presos a ele,
        # então a folha pode ganhar arquivo novo (-v2, -v3...) sem o músico perder o que já fez
        d['paginas']+=[dict(img=f"/midias/nc/{x['nome']}",nome=x.get('rotulo') or 'outra versão',tomProprio=True,**({'chave':x['chave']} if x.get('chave') else {})) for x in extras if x['rot']==rot]
        if rot.endswith('-A'): d['rotulo']=rot
        itens.append(d)
    json.dump(itens,open('/tmp/nc/final/fonte_nc.json','w'),ensure_ascii=False,indent=1)
    print(len(itens),'hinos; folhas por hino:',collections.Counter(len(i['paginas']) for i in itens),'| extras:',[x['nome'] for x in extras])
    print('sem foto:',[r for r in ORD if r not in byh])
