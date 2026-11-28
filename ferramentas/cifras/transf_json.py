"""Junta as cifras trazidas por registro (fonte exata ou página do hinário) nos dados da aba Hinos – Partitura."""
import json,glob,os
R='/home/claude/musicas-ipb/public/data/cifras/'
fn=R+'hinos.json'; J=json.load(open(fn))
n_ex=n_nc=preench=0
import sys
sys.path.insert(0,'/tmp/cif')
from hinos_final import k_de,FORA
for f in sorted(glob.glob('/tmp/cif/transf/*.json')):
    r=json.load(open(f))
    if not r['folha']: continue
    nome_=os.path.basename(r['img'])[:-4]
    if k_de(nome_) is not None or any(nome_.startswith(p) for p in FORA): continue      # folhas riscadas: outra etapa
    nova=r['folha']; img=r['img']; exata=not r['de'][0][0].startswith('nc')
    velha=J['folhas'].get(img)
    if not exata and velha and velha.get('r')==nova.get('r'):
        # onde a página do hinário não foi lida ("?") e a leitura direta da foto leu, aproveita
        for c in nova['c']:
            if c[4]!='?': continue
            for o in velha['c']:
                if o[4]!='?' and abs((o[0]+o[2]/2)-(c[0]+c[2]/2))<0.5*max(o[2],c[2]) and abs(o[1]-c[1])<0.6*c[3]:
                    c[4]=o[4]; preench+=1; break
    J['folhas'][img]=nova
    if exata: n_ex+=1
    else: n_nc+=1
json.dump(J,open(fn,'w'),ensure_ascii=False,separators=(',',':'))
print('hinos: folhas com fonte exata',n_ex,'| vindas do hinário',n_nc,'| "?" preenchidos pela leitura direta',preench,'|',os.path.getsize(fn)//1024,'KB')
