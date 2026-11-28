"""Etapa C: junta cifras conhecidas, riscos e letras à mão; lista o que ainda não se sabe (para leitura manual)."""
import sys,json,glob,os,re
sys.path.insert(0,'/tmp/cif')
import numpy as np
def classificar(o):
    """o: saída de hfin_b.analisar. Por linha: riscos sem vaga (cifra impressa que a leitura não achou, ou rabisco),
    letras à mão e a quem pertencem."""
    res=[]
    for L in o['linhas']:
        c=L['cap']*L['f']; cif=L['cif']; base=L['base_rel']
        usados={int(k) for k in L['r2v']}
        desconhecidos=[]; ao_lado=[]
        for ri,r in enumerate(L['riscos']):
            if ri in usados: continue
            h=r[3]-r[1]; cy=(r[1]+r[3])/2
            perto=[q for q in cif if r[0]-q['x1']<1.3*c and q['x0']-r[2]<1.3*c]
            if perto and not L['fonte'].startswith('nc'): ao_lado.append((ri,min(perto,key=lambda q:abs((q['x0']+q['x1'])/2-(r[0]+r[2])/2))['i']))
            elif r[4]>=0.3*c*c and h>=0.45*c and base-1.25*c<=cy<=base+0.4*c: desconhecidos.append(ri)
        letras_de={}
        for li,l in enumerate(L['letras']):
            cx=(l[0]+l[2])/2
            alvos=[('c',q['i'],(q['x0']+q['x1'])/2,q['x0'],q['x1']) for q in cif]+[('d',ri,(L['riscos'][ri][0]+L['riscos'][ri][2])/2,L['riscos'][ri][0],L['riscos'][ri][2]) for ri in desconhecidos]
            # a letra fica em cima do risco da cifra: usa o lugar do risco quando houver
            for qi,q in enumerate(cif):
                if q.get('risco') is not None:
                    r=L['riscos'][q['risco']]; alvos.append(('c',q['i'],(r[0]+r[2])/2,r[0],r[2]))
            if not alvos: continue
            a=min(alvos,key=lambda a:abs(a[2]-cx)); d=max(0,l[0]-a[4],a[3]-l[2])
            if d<=3.5*c: letras_de[li]=(a[0],a[1])
        res.append(dict(L=L,c=c,base=base,desconhecidos=desconhecidos,ao_lado=ao_lado,letras_de=letras_de))
    return res
if __name__=='__main__':
    import hfin_b
    from hinos_final import FORA
    ns=[os.path.basename(f)[:-5] for f in sorted(glob.glob('/tmp/cif/hfin/h*.json'))]
    ns=[n for n in ns if not any(n.startswith(p) for p in FORA)]
    for n in ns:
        o=hfin_b.analisar(n)
        R_=classificar(o)
        nc=sum(len(x['L']['cif']) for x in R_); q=sum(1 for x in R_ for c_ in x['L']['cif'] if c_['txt']=='?')
        risc=sum(1 for x in R_ for c_ in x['L']['cif'] if c_.get('risco') is not None)
        desc=sum(len(x['desconhecidos']) for x in R_); lado=sum(len(x['ao_lado']) for x in R_)
        let=sum(len(x['L']['letras']) for x in R_); let_ok=sum(len(x['letras_de']) for x in R_)
        print(f"{n[:22]:22s} k {o['k']:>3} cifras {nc:3d} ('?' {q:2d}) riscadas {risc:3d} ({100*risc//max(1,nc)}%) | riscos sem cifra {desc:2d} ao lado {lado:2d} | letras {let:3d} ligadas {let_ok:3d}",flush=True)
