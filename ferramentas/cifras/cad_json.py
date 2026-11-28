"""Decide e monta as cifras do Caderninho a partir da leitura crua (cad_bruto/*.json)."""
import sys,json,glob,os,re
sys.path.insert(0,'/tmp/cif')
import numpy as np
from acordes import eh_acorde
R='/home/claude/musicas-ipb/public/data/cifras/'
def decidir(r):
    T=[t for t in r['toks'] if t['c']]
    def marg(t): return t['c'][0][0]-(t['c'][1][0] if len(t['c'])>1 else 0)
    saida=[]
    for ref in sorted({t['capref'] for t in T}):
        G=[t for t in T if t['capref']==ref]
        fortes=[t for t in G if t['c'][0][0]>=0.88 and marg(t)>=0.04]
        if len(fortes)<3: continue
        capp=float(np.median([t['cap'] for t in fortes])); swp=float(np.median([t['sw']/t['cap'] for t in fortes]))
        vistos={}
        for t in fortes: vistos[t['c'][0][1]]=vistos.get(t['c'][0][1],0)+1
        for t in G:
            v1,x1=t['c'][0]; tx,cf=t['t']
            tipo=abs(t['cap']/capp-1)<=0.12 and t['sw']/t['cap']>=0.82*swp
            if not tipo: continue
            conc=(tx==x1 and cf>=50)
            bonus=0.02 if x1 in vistos else 0.0
            if v1+bonus>=0.84 or (v1>=0.74 and conc):
                txt=x1; conf=round(min(1.0,v1+(0.04 if conc else 0)),3)
                # dúvida de raiz (E×B, C×G...) sem nada que confirme
                outra=max([v for v,x in t['c'][1:] if x[:2].rstrip('m7964/(')!=x1[:2].rstrip('m7964/(')],default=0)
                if not conc and v1-outra<0.02 and x1 not in vistos: txt='?'; conf=0.0
            elif v1>=0.55 or (cf>=85 and eh_acorde(tx)):
                txt='?'; conf=0.0
            else: continue
            saida.append([t['x0'],t['base'],t['x1']-t['x0'],t['cap'],txt,conf,t['y0'],t['y1'],t['bg']])
    return saida
def folha(r):
    c=decidir(r)
    if sum(1 for x in c if x[4]!='?')<2: return None
    cs=[]
    for x0,base,w,cap,txt,conf,y0,y1,bg in sorted(c,key=lambda x:(x[1],x[0])):
        fs=cap/0.716*0.97            # Arial negrito itálico -> Inter negrito (maiúsculas 0,727)
        e=[x0,base,w,round(fs,1),txt,bg]
        sobe=(base-y0)+0.06*fs; desce=(y1-base)+0.05*fs
        if sobe>0.86*fs or desce>(0.27 if re.search(r'[()/]',txt) else 0.1)*fs: e+=[0,round(max(sobe,0.82*fs)),round(max(desce,0.08*fs))]
        cs.append(e)
    return dict(w=r['w'],h=r['h'],f='a',c=cs)
if __name__=='__main__':
    F={}; tot=0; ileg=0; sem=[]
    for f in sorted(glob.glob('/tmp/cif/cad_bruto/*.json')):
        r=json.load(open(f)); d=folha(r)
        img='/midias/caderninho3/'+os.path.basename(r['img'])
        if d: F[img]=d; tot+=sum(1 for c in d['c'] if c[4]!='?'); ileg+=sum(1 for c in d['c'] if c[4]=='?')
        else: sem.append(os.path.basename(r['img']))
    json.dump(dict(v=1,folhas=F),open(R+'caderninho.json','w'),ensure_ascii=False,separators=(',',':'))
    print('caderninho: folhas com cifras',len(F),'| cifras',tot,'| ilegíveis',ileg,'| sem leitura',len(sem),sem[:12],os.path.getsize(R+'caderninho.json')//1024,'KB')
