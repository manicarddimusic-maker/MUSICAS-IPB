"""Leitura manual dos lugares de cifra que ficaram sem texto: monta folhas de recortes numerados
(em cima: a foto com a letra à mão; embaixo: a página limpa do hinário), guarda/aplica os rótulos.
uso: hfin_rot.py montar            -> /tmp/cif/hfin/rot/itens.json + folha_NN.jpg
     hfin_rot.py rotular N "a b c" -> guarda os rótulos da folha N (na ordem dos números)"""
import sys,json,glob,os,re
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
D='/tmp/cif/hfin/rot'; os.makedirs(D,exist_ok=True)
def montar():
    import hfin_b,hfin_c
    from hinos_final import FORA
    ns=[os.path.basename(f)[:-5] for f in sorted(glob.glob('/tmp/cif/hfin/h*.json'))]
    ns=[n for n in ns if not any(n.startswith(p) for p in FORA)]
    itens={}       # (fonte, x, base) agrupado
    ROT=carregar_rotulos()
    def acha(fonte,xs,bs,cap):
        for k,v in itens.items():
            if v['fonte']==fonte and abs(v['xs']-xs)<1.3*cap and abs(v['bs']-bs)<0.8*cap: return v
        return None
    for n in ns:
        o,faixas,up=hfin_b.analisar(n,guardar_faixas=True)
        for x in hfin_c.classificar(o):
            L=x['L']; f=L['f']; cap=L['cap']
            alvos=[]
            for q in L['cif']:
                if q['txt']=='?': alvos.append((q['xs'],q['bs'],q['ws'],'vaga'))
            for ri in x['desconhecidos']:
                r=L['riscos'][ri]; alvos.append((L['xs0']+r[0]/f,L['base_src'][min(len(L['base_src'])-1,int((r[0]+r[2])/2)//8)],(r[2]-r[0])/f,'risco'))
            for xs,bs,ws,tipo in alvos:
                if rotulo_de(ROT,L['fonte'],xs,bs,cap,ws): continue
                it=acha(L['fonte'],xs,bs,cap)
                cor_f,src=faixas[(L['fi'],L['ri'])]
                u0=int((xs-L['xs0']-5.0*cap)*f); u1=int((xs+ws-L['xs0']+5.0*cap)*f)
                a0=max(0,u0); a1=min(L['bw'],u1)
                vr=max(0,L['v_row']-int(0.45*cap*f))
                rec_f=cor_f[:,a0:a1]; rec_s=src[vr:,a0:a1]
                marca=(int((xs-L['xs0'])*f)-a0,int((xs+ws-L['xs0'])*f)-a0)
                # as vagas da linha (lidas = verde, sem texto = laranja), para saber se o risco é de uma cifra já conhecida
                rec_s=cv2.cvtColor(rec_s,cv2.COLOR_GRAY2BGR)
                yb=int(L['base_rel'])-vr+int(0.32*cap*f) if 'base_rel' in L else rec_s.shape[0]-int(0.35*cap*f)
                for q in L['cif']:
                    qa=int(q['x0'])-a0; qb=int(q['x1'])-a0
                    if qb<0 or qa>rec_s.shape[1]: continue
                    cv2.line(rec_s,(max(0,qa),min(rec_s.shape[0]-2,yb)),(min(rec_s.shape[1]-1,qb),min(rec_s.shape[0]-2,yb)),(0,160,0) if q['txt']!='?' else (0,140,255),2)
                nitidez=float(cv2.Laplacian(cv2.cvtColor(rec_f,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var())
                if it is None:
                    it=dict(fonte=L['fonte'],xs=float(xs),bs=float(bs),ws=float(ws),cap=float(cap),tipo=tipo,fotos=[],k=o['k'])
                    itens[len(itens)]=it
                elif tipo=='vaga' and it['tipo']=='risco': it.update(xs=float(xs),ws=float(ws),tipo='vaga')
                it['fotos'].append(dict(nome=n,nit=nitidez,k=o['k']))
                if nitidez>=it.get('_nit',-1):
                    it['_nit']=nitidez; it['_rec']=(rec_f.copy(),rec_s.copy(),marca,f)
    # ordena por fonte, linha, x
    ordem=sorted(itens.values(),key=lambda v:(v['fonte'].startswith('nc'),int(v['fonte'].split(':')[1]) if v['fonte'].startswith('nc') else 0,v['fonte'],round(v['bs']/40),v['xs']))
    CW,CH=300,214; cols=6; por=30
    lista=[]
    for fi in range(0,len(ordem),por):
        bloco=ordem[fi:fi+por]; rows=(len(bloco)+cols-1)//cols
        tela=np.full((rows*CH,cols*CW,3),255,np.uint8)
        for i,it in enumerate(bloco):
            rec_f,rec_s,marca,f=it.pop('_rec'); it.pop('_nit',None)
            r,c=divmod(i,cols); x0=c*CW; y0=r*CH
            def poe(img,yy,alt):
                if img.ndim==2: img=cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
                s=min((CW-8)/img.shape[1],alt/img.shape[0]); im=cv2.resize(img,None,fx=s,fy=s,interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
                tela[yy:yy+im.shape[0],x0+4:x0+4+im.shape[1]]=im
                xa=x0+4+int(marca[0]*s); xb=x0+4+int(marca[1]*s)
                cv2.line(tela,(xa,yy+im.shape[0]+2),(max(xb,xa+6),yy+im.shape[0]+2),(0,0,230),3)
            poe(rec_f,y0+20,118); poe(rec_s,y0+20+118+8,58)
            num=fi+i+1
            cv2.putText(tela,f"{num}  {it['fonte'].replace('nc:','p')} k{it['k']} {it['tipo']}",(x0+4,y0+16),cv2.FONT_HERSHEY_SIMPLEX,0.5,(160,0,0),1)
            cv2.rectangle(tela,(x0,y0),(x0+CW-1,y0+CH-1),(200,200,200),1)
            it['num']=num; lista.append(it)
        cv2.imwrite(f'{D}/folha_{fi//por+1:02d}.jpg',tela,[cv2.IMWRITE_JPEG_QUALITY,82])
    json.dump(lista,open(f'{D}/itens.json','w'))
    print(len(lista),'itens em',(len(lista)+por-1)//por,'folhas;',sum(1 for i in lista if i['tipo']=='vaga'),'vagas,',sum(1 for i in lista if i['tipo']=='risco'),'riscos')
def carregar_rotulos():
    return json.load(open(f'{D}/rotulos.json')) if os.path.exists(f'{D}/rotulos.json') else []
def rotulo_de(R_,fonte,xs,bs,cap,ws=0):
    """rótulo já dado para este lugar (mesma fonte, mesma linha, x coincidindo)"""
    for r in R_:
        if r['fonte']==fonte and abs(r['bs']-bs)<0.8*cap and (abs(r['xs']-xs)<1.0*cap or min(r['xs']+r['ws'],xs+ws)-max(r['xs'],xs)>0.5*min(r['ws'],ws or 1e9)): return r
    return None
def rotular(n,txt):
    lista=json.load(open(f'{D}/itens.json')); por=30
    bloco=[i for i in lista if (i['num']-1)//por==n-1]
    labs=txt.split()
    assert len(labs)==len(bloco),f'{len(labs)} rótulos para {len(bloco)} itens'
    R_=carregar_rotulos()
    for it,l in zip(bloco,labs):
        v=rotulo_de(R_,it['fonte'],it['xs'],it['bs'],it['cap'],it['ws'])
        if v: v['txt']=l
        else: R_.append(dict(fonte=it['fonte'],xs=it['xs'],bs=it['bs'],ws=it['ws'],cap=it['cap'],tipo=it['tipo'],txt=l,k=it['k']))
    json.dump(R_,open(f'{D}/rotulos.json','w'))
    print('folha',n,'guardada;',len(R_),'rótulos no total')
if __name__=='__main__':
    if sys.argv[1]=='montar': montar()
    else: rotular(int(sys.argv[2]),sys.argv[3])
