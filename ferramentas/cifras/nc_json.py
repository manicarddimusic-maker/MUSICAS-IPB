"""Monta os dados de cifras do Hinário Novo Cântico (folhas da aba e páginas do PDF único)."""
import json,glob,os,sys
sys.path.insert(0,'/tmp/cif')
import numpy as np
from nccomum import PAG
R='/home/claude/musicas-ipb/public/data/cifras/'
FOL=json.load(open('/tmp/nc/final/folhas.json'))
PMAP={int(k):v for k,v in json.load(open('/tmp/nc/final/pdf_map.json')).items()}
from nc_decidir import decidir,em_linhas
from acordes import estimar_tom
LID={}
def valor(r):
    ok=[x for x in r['c'] if x[4]!='?']
    return len(ok)-0.5*(len(r['c'])-len(ok)) if len(ok)>=3 and np.median([x[5] for x in ok])>=0.86 else -1
troca=0
for f in glob.glob('/tmp/cif/bruto/p*.json'):
    r=decidir(json.load(open(f))); pg=r['pg']
    f2=f.replace('/bruto/','/bruto2/')
    if os.path.exists(f2):
        r2=decidir(json.load(open(f2)))
        if valor(r2)>valor(r): r=r2; troca+=1
    LID[pg]=r
print('páginas em que a 2ª leitura ficou melhor:',troca)
json.dump(LID,open('/tmp/cif/nc_decidido.json','w'))
def confiavel(r):
    """a leitura desta página merece confiança? devolve (usa, duvidosa)"""
    c=r['c']; ok=[x for x in c if x[4]!='?']
    if len(ok)<3: return False,True
    conf=[x[5] for x in ok]; med=float(np.median(conf)); frac_q=(len(c)-len(ok))/len(c)
    if med<0.86 or frac_q>0.5: return False,True
    duvidosa = PAG[r['pg']]['cls']!='boa' or med<0.92 or frac_q>0.3
    return True,duvidosa
def cifra(x,s,dx,dy,k=1.0):
    """(x0,base,w,cap,txt,...) em pixels da página -> entrada na folha (escala s, deslocamento dx,dy) ; k converte no fim (pontos do PDF)"""
    x0,base,w,cap,txt=x[:5]; y0,y1=x[6],x[7]
    fs=cap*s/0.711
    X=(dx+s*x0)*k; B=(dy+s*base)*k; W=s*w*k; FS=fs*k
    out=[round(X,1) if k!=1 else round(X),round(B,1) if k!=1 else round(B),round(W,1) if k!=1 else round(W),round(FS,1),txt]
    sobe=(base-y0)*s*k+0.05*FS; desce=(y1-base)*s*k+0.04*FS
    tem=any(ch in txt for ch in '()/')
    if sobe>0.86*FS or desce>(0.27 if tem else 0.1)*FS:
        out+=[0,0,round(max(sobe,0.82*FS),1),round(max(desce,0.08*FS),1)]
    return out
folhas={}; rel=dict(folhas=0,com=0,duvidosas=0,cifras=0,ileg=0,pag_sem=[])
for F in FOL:
    cs=[]; duv=False; alguma=False; ordem=[]
    for p in F['pages']:
        r=LID.get(p['pg'])
        if not r: duv=True; continue
        usa,d=confiavel(r)
        if not usa:
            duv=True; rel['pag_sem'].append(p['pg']); continue
        alguma=True; duv=duv or d
        for rw in em_linhas(r['c'],r['cap']):
            for x in rw:
                cs.append(cifra(x,p['s'],p['x0'],0)); ordem.append(x[4])
    rel['folhas']+=1
    if not cs: continue
    d=dict(w=F['w'],h=F['h'],f='s',c=cs)
    tom=estimar_tom([x for x in ordem if x!='?'])
    if tom: d['k']=tom
    if duv: d['q']=1; rel['duvidosas']+=1
    folhas['/midias/nc/'+F['nome']]=d; rel['com']+=1; rel['cifras']+=sum(1 for c in cs if c[4]!='?'); rel['ileg']+=sum(1 for c in cs if c[4]=='?')
json.dump(dict(v=1,folhas=folhas),open(R+'novocantico.json','w'),ensure_ascii=False,separators=(',',':'))
print('aba: folhas',rel['folhas'],'com cifras',rel['com'],'duvidosas',rel['duvidosas'],'cifras',rel['cifras'],'ilegíveis',rel['ileg'],os.path.getsize(R+'novocantico.json')//1024,'KB')
print('páginas sem leitura confiável:',len(set(rel['pag_sem'])))
# PDF único: página i do PDF = i-ésima página do livro que temos
pgs=sorted(PAG); K=432/1100
fp={}
for i,pg in enumerate(pgs):
    r=LID.get(pg)
    if not r: continue
    usa,d=confiavel(r)
    if not usa: continue
    m=PMAP[pg]
    lin=[x for rw in em_linhas(r['c'],r['cap']) for x in rw]
    cs=[cifra(x,m['s'],m['x0'],m['y0'],K) for x in lin]
    if not cs: continue
    D=dict(w=432,h=648,f='s',c=cs)
    tom=estimar_tom([x[4] for x in lin if x[4]!='?'])
    if tom: D['k']=tom
    if d: D['q']=1
    fp[str(i+1)]=D
json.dump(dict(v=1,folhas=fp),open(R+'pdf-hinario-novo-cantico.json','w'),ensure_ascii=False,separators=(',',':'))
print('pdf: páginas com cifras',len(fp),os.path.getsize(R+'pdf-hinario-novo-cantico.json')//1024,'KB')
json.dump(dict(pag_sem=sorted(set(rel['pag_sem']))),open('/tmp/cif/nc_rel.json','w'))
