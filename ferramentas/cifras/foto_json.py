"""Decide e monta as cifras lidas nas fotos (Caderninho, Cânticos, Hinos–Partitura, Salmos, Palavra)."""
import sys,json,glob,os,re
sys.path.insert(0,'/tmp/cif')
import numpy as np
from acordes import eh_acorde
from foto import FONTES
import nc_decidir
R='/home/claude/musicas-ipb/public/data/cifras/'
CAPF={'a':0.727,'s':0.711,'t':0.662,'m':0.72}
def juntar_partes(T):
    for t in T:
        s_=t.get('s')
        if not s_ or not s_['l'] or not s_['r'] or s_['r'][0][0]<0.78 or s_['l'][0][0]<0.68: continue
        junt=dict((x,v) for v,x in t['c'])
        for vl,xl in s_['l']:
            for vr,xr in s_['r']:
                v=round(0.5*min(vl,vr)+0.25*(vl+vr)+0.02,3); k=xl+'/'+xr; junt[k]=max(junt.get(k,0),v)
        t['c']=sorted(([v,x] for x,v in junt.items()),reverse=True)[:6]
def decidir(r):
    if not r.get('fonte') or not r['toks']: return []
    T=[dict(t) for t in r['toks'] if t['c']]
    juntar_partes(T)
    if r.get('partitura'):
        for t in T: t['pa']=1; t['p']=1
        d=nc_decidir.decidir(dict(pg=0,w=r['w'],h=r['h'],cap=r['cap'],toks=T))
        bgs={(t['x0'],t['base']):t['bg'] for t in T}
        return [c[:8]+[bgs.get((c[0],c[1]),'ffffff')] for c in d['c']]
    normal=FONTES[r['fonte']][4]; thr=0.76 if normal else 0.80
    # palavras de letra (não cifra) na mesma linha: as vizinhas que parecem cifra não contam
    c0=r['cap']
    for t in T:
        parecidas=sum(1 for o in T if o is not t and o['c'][0][0]>=0.7 and abs(o['base']-t['base'])<0.3*c0 and abs(o['x0']-t['x0'])<14*c0)
        t['viz']=max(0,t['viz']-parecidas)
    def marg(t): return t['c'][0][0]-(t['c'][1][0] if len(t['c'])>1 else 0)
    fortes=[t for t in T if t['c'][0][0]>=thr+0.06 and marg(t)>=0.04 and t['viz']<=3]
    if len(fortes)<3: fortes=[t for t in T if t['t'][0]==t['c'][0][1] and t['t'][1]>=75 and t['c'][0][0]>=0.7 and t['viz']<=3]
    if len(fortes)<2: return []
    capp=float(np.median([t['cap'] for t in fortes])); swp=float(np.median([t['sw']/t['cap'] for t in fortes]))
    vistos={}
    for t in fortes: vistos[t['c'][0][1]]=vistos.get(t['c'][0][1],0)+1
    out=[]
    for t in T:
        if abs(t['cap']/capp-1)>0.16 or t['sw']/t['cap']<0.7*swp or t['sw']/t['cap']>1.5*swp: continue
        tx,cf=t['t']; rk=[]
        for v,x in t['c']:
            b=0.0
            if x==tx: b+=0.06 if cf>=70 else (0.03 if cf>=40 else 0.0)
            if x in vistos: b+=0.02
            rk.append((v+b,v,x))
        rk.sort(reverse=True); n1,v1,x1=rk[0]; n2=rk[1][0] if len(rk)>1 else 0
        conc=(x1==tx and cf>=40)
        if t['viz']>=4 and not (conc and re.search(r'[0-9#/]',x1) and v1>=thr): continue
        txt=None
        if v1>=thr and (n1-n2>=0.015 or conc or x1 in vistos): txt=x1; conf=min(1.0,v1+(0.05 if conc else 0))
        elif v1>=thr-0.08 and conc: txt=x1; conf=v1
        elif cf>=90 and eh_acorde(tx) and len(tx)<=8 and any(x==tx for _,_,x in rk): txt=tx; conf=0.6
        elif v1>=0.6 and t['viz']<=2 and t['x1']-t['x0']<=4.5*capp: txt='?'; conf=0.0
        if txt is None: continue
        out.append([t['x0'],t['base'],t['x1']-t['x0'],t['cap'],txt,round(conf,3),t['y0'],t['y1'],t['bg']])
    # "?" só vale ao lado de cifras lidas, na mesma linha (senão é palavra da letra)
    boas=[x for x in out if x[4]!='?']
    def na_linha(q): return any(abs(o[0]-q[0])<20*capp and abs(o[1]-q[1])<0.45*capp+0.06*abs(o[0]-q[0]) for o in boas)
    return [x for x in out if x[4]!='?' or na_linha(x)]
def folha(r):
    c=decidir(r)
    if sum(1 for x in c if x[4]!='?')<2: return None
    fam=FONTES[r['fonte']][3]; normal=FONTES[r['fonte']][4]
    cs=[]
    for x0,base,w,cap,txt,conf,y0,y1,bg in sorted(c,key=lambda x:(x[1],x[0])):
        fs=cap/CAPF[fam]
        e=[x0,base,w,round(fs,1),txt,bg]
        sobe=(base-y0)+0.06*fs; desce=(y1-base)+0.05*fs
        if sobe>0.86*fs or desce>(0.27 if re.search(r'[()/]',txt) else 0.1)*fs: e+=[0,round(max(sobe,0.82*fs)),round(max(desce,0.08*fs))]
        cs.append(e)
    W,H=r['w'],r['h']; g=r.get('giro',0)
    d=dict(w=(H if g in (90,270) else W),h=(W if g in (90,270) else H),f=fam,c=cs)
    if normal: d['n']=1
    if g: d['r']=g
    return d
if __name__=='__main__':
    C=json.load(open('/home/claude/musicas-ipb/public/data/catalogo.json'))
    sec_de={}
    for s in C['secoes']:
        for it in s['itens']:
            for p in it['paginas']: sec_de.setdefault(p['img'],set()).add(s['id'])
    por={}; rel={}
    for f in sorted(glob.glob('/tmp/cif/foto_bruto/*.json')):
        r=json.load(open(f)); d=folha(r)
        for sec in sec_de.get(r['img'],[]):
            st=rel.setdefault(sec,dict(fotos=0,com=0,cifras=0,ileg=0)); st['fotos']+=1
            if d: por.setdefault(sec,{})[r['img']]=d; st['com']+=1; st['cifras']+=sum(1 for c in d['c'] if c[4]!='?'); st['ileg']+=sum(1 for c in d['c'] if c[4]=='?')
    for sec,fs in por.items():
        fn=R+sec+'.json'
        J=json.load(open(fn)) if os.path.exists(fn) else dict(v=1,folhas={})
        J['folhas'].update(fs)
        json.dump(J,open(fn,'w'),ensure_ascii=False,separators=(',',':'))
    for sec,st in rel.items(): print(sec,st)
    json.dump(rel,open('/tmp/cif/foto_rel.json','w'))
