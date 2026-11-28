"""Decide, a partir da leitura crua de uma página, quais palavras são cifras e o que está escrito nelas."""
import sys,json,re,difflib
sys.path.insert(0,'/tmp/cif')
import numpy as np
from acordes import eh_acorde,estimar_tom,primeiro
P=dict(A=0.80,B=0.70,C=0.74,D=0.75,D_m=0.015,E_tess=88,duv=0.012,p2=0.86,p2_m=0.03,cap_tol=0.20,sw_min=0.78,um_conf=0.90)
def partes(txt):
    m=re.fullmatch(r'([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?',txt)
    return (m.group(1),m.group(2),m.group(3)) if m else (None,None,None)
def altura(n):
    p=primeiro(n); return p[0] if p else None
GRAU={0:(0.03,'M'),5:(0.03,'M'),7:(0.03,'M'),2:(0.02,'m'),4:(0.02,'m'),9:(0.025,'m'),11:(0.004,'d')}
def decidir(r,par=P):
    T=[dict(t) for t in r['toks'] if t['c']]
    cap0=r['cap']
    # acordes com baixo lidos em duas metades: junta as combinações à lista de candidatos
    for t in T:
        s_=t.get('s')
        if not s_ or not s_['l'] or not s_['r']: continue
        if s_['r'][0][0]<0.80 or s_['l'][0][0]<0.70: continue
        comb={}
        for vl,xl in s_['l']:
            for vr,xr in s_['r']:
                if xl.split('/')[0][:2].rstrip('m7964susdi')==xr: pass
                v=0.5*min(vl,vr)+0.25*(vl+vr)
                comb[xl+'/'+xr]=max(comb.get(xl+'/'+xr,0),round(v+0.02,3))
        junt=dict((x,v) for v,x in t['c'])
        for x,v in comb.items(): junt[x]=max(junt.get(x,0),v)
        t['c']=sorted(([v,x] for x,v in junt.items()),reverse=True)[:6]
        t['partido']=1
    def marg(t): return t['c'][0][0]-(t['c'][1][0] if len(t['c'])>1 else 0)
    fortes=[t for t in T if t['p']==1 and t['c'][0][0]>=0.88 and marg(t)>=0.04 and len(t['c'][0][1])>=2]
    if len(fortes)<4: fortes=[t for t in T if t['p']==1 and t['c'][0][0]>=0.86]
    if len(fortes)<3: return dict(pg=r['pg'],w=r['w'],h=r['h'],cap=cap0,tom=None,c=[],n_fortes=len(fortes))
    capp=float(np.median([t['cap'] for t in fortes])); swp=float(np.median([t['sw']/t['cap'] for t in fortes]))
    def tipo_ok(t):
        tol=par['cap_tol'] if t['p']==1 else 0.22
        if abs(t['cap']/capp-1)>tol: return False
        if t['p']==1 and t['sw']/t['cap']<par['sw_min']*swp: return False
        return True
    T=[t for t in T if tipo_ok(t)]
    def certo(t):
        v=t['c'][0][0]
        if t['p']!=1: return None
        if v>=0.86 and marg(t)>=0.045: return t['c'][0][1]
        if v>=0.80 and t['t'][0]==t['c'][0][1] and t['t'][1]>=60: return t['c'][0][1]
        return None
    certos=[c for c in map(certo,T) if c]
    tom=estimar_tom(certos) if len(certos)>=3 else None
    tonica=None; dia=None
    if tom:
        tonica=primeiro(tom)[0]
        if tom.endswith('m'): tonica=(tonica+3)%12
        dia={(tonica+x)%12 for x in (0,2,4,5,7,9,11)}
    vistos={}
    for c in certos: vistos[c]=vistos.get(c,0)+1
    raizes={partes(c)[0] for c in certos}
    def nota(v,txt):
        rz,s,bx=partes(txt); b=0.0
        if tonica is not None and rz:
            g=GRAU.get((altura(rz)-tonica)%12)
            if g:
                b+=g[0]; q=primeiro(txt)[1]
                if q==g[1] or (g[1]=='d' and q in 'dm'): b+=0.012
            if bx and altura(bx) in dia: b+=0.01
        if txt in vistos: b+=0.025
        elif rz in raizes: b+=0.008
        return v+b
    for t in T:
        rk=sorted(((nota(v,x),v,x) for v,x in t['c']),reverse=True)
        n1,v1,x1=rk[0]; n2=rk[1][0] if len(rk)>1 else 0
        outra=max([n for n,v,x in rk[1:] if partes(x)[0]!=partes(x1)[0]],default=0)
        tx,cf=t['t']; conc=(tx==x1 and cf>=50)
        t['v1']=v1; t['txt']='?'; t['conf']=0.0
        if t['p']==2:
            if v1>=par['p2'] and n1-n2>=par['p2_m'] and n1-outra>=0.03: t['txt']=x1; t['conf']=round(v1-0.06,3)
            continue
        ok = v1>=par['A'] or (v1>=par['B'] and conc) or (v1>=par['C'] and x1 in vistos and n1-n2>=0.03) or (v1>=par['D'] and '/' in x1 and n1-n2>=par['D_m'])
        if ok:
            t['txt']=x1; t['conf']=round(min(1.0,v1+(0.05 if conc else 0)+min(0.05,n1-n2)),3)
            if not conc and n1-outra<par['duv'] and v1<0.9: t['txt']='?'; t['conf']=0.0
        elif cf>=par['E_tess'] and eh_acorde(tx) and 1<=len(tx)<=10 and (tx in vistos or any(x==tx for _,x in t['c'])):
            t['txt']=tx; t['conf']=0.6
    boas=[t for t in T if t['txt']!='?']
    # linhas de cifras
    pai=list(range(len(boas)))
    def acha(i):
        while pai[i]!=i: pai[i]=pai[pai[i]]; i=pai[i]
        return i
    for i,a in enumerate(boas):
        for j in range(i+1,len(boas)):
            c=boas[j]; dx=abs(a['x0']-c['x0'])
            if dx<9*capp and abs(a['base']-c['base'])<0.35*capp+0.09*dx: pai[acha(i)]=acha(j)
    grupos={}
    for i,t in enumerate(boas): grupos.setdefault(acha(i),[]).append(t)
    def texto_ao_lado(g):
        """quantas palavras que não são cifra estão na mesma linha de texto (letra da música, título)"""
        n=0
        for o in T:
            if o['txt']!='?' or o['p']!=1 or o['v1']>=0.65: continue
            for t in g:
                dx=abs(o['x0']-t['x0'])
                if dx<12*capp and abs(o['base']-t['base'])<0.25*capp+0.02*dx: n+=1; break
        return n
    linhas=[]; sozinhas=[]
    for g in grupos.values():
        n=len(g)
        if n>=3: linhas.append(g); continue
        viz=texto_ao_lado(g)
        if viz>=2: continue
        if n==2 and (any(t['pa'] for t in g) or min(t['conf'] for t in g)>=0.85): linhas.append(g)
        elif n==1: sozinhas.append((g[0],viz))
    saida=[t for g in linhas for t in g]; ids={id(t) for t in saida}
    # cifra sozinha: vale se estiver na continuação de uma linha de cifras (folha curva) ou se for bem segura
    for t,viz in sozinhas:
        perto=None
        if saida:
            o=min(saida,key=lambda o:abs(o['x0']-t['x0'])+5*abs(o['base']-t['base'])); dx=abs(o['x0']-t['x0'])
            if dx<17*capp and abs(o['base']-t['base'])<0.4*capp+0.11*dx: perto=o
        conc=(t['t'][0]==t['txt'] and t['t'][1]>=70)
        if perto is not None or (t['conf']>=par['um_conf'] and t['pa'] and viz==0 and (len(t['txt'])>=2 or (conc and abs(t['cap']/capp-1)<=0.1))):
            saida.append(t); ids.add(id(t))
    if saida:
        for t in T:
            if id(t) in ids or t['txt']!='?' or t['v1']<0.5 or t['x1']-t['x0']<0.45*capp: continue
            if any(min(t['x1'],o['x1'])-max(t['x0'],o['x0'])>-0.1*capp and min(t['y1'],o['y1'])-max(t['y0'],o['y0'])>0 for o in saida): continue
            viz=min(saida,key=lambda o:abs(o['x0']-t['x0'])+4*abs(o['base']-t['base'])); dx=abs(viz['x0']-t['x0'])
            if dx<14*capp and abs(viz['base']-t['base'])<0.3*capp+0.08*dx: saida.append(t); ids.add(id(t))
    saida.sort(key=lambda t:(t['base'],t['x0']))
    return dict(pg=r['pg'],w=r['w'],h=r['h'],cap=round(capp,1),tom=tom,n_fortes=len(fortes),
                c=[[t['x0'],t['base'],t['x1']-t['x0'],t['cap'],t['txt'],t['conf'],t['y0'],t['y1']] for t in saida])
def em_linhas(c,cap):
    """agrupa as cifras em linhas (para conferir)"""
    c=sorted(c,key=lambda x:x[0]); rows=[]
    for x in sorted(c,key=lambda x:(x[1],x[0])):
        for rw in rows:
            v=min(rw,key=lambda o:abs(o[0]-x[0]))
            if abs(v[1]-x[1])<0.6*cap+0.12*abs(v[0]-x[0]): rw.append(x); break
        else: rows.append([x])
    rows.sort(key=lambda rw:min(o[1] for o in rw))
    return [sorted(rw,key=lambda o:o[0]) for rw in rows]
def avaliar(res,verdade):
    """compara com a leitura feita a olho: devolve (certas, erradas, marcadas '?', faltando, sobrando)"""
    rows=em_linhas(res['c'],res['cap']); lidas=[[x[4] for x in rw] for rw in rows]
    ok=err=qm=falta=sobra=0; det=[]
    usados=set()
    for vr in verdade:
        # linha lida mais parecida
        best=None
        for i,lr in enumerate(lidas):
            if i in usados: continue
            s=difflib.SequenceMatcher(None,vr,lr,autojunk=False).ratio()
            if best is None or s>best[0]: best=(s,i)
        if best is None or best[0]<0.2: falta+=len(vr); det.append(('FALTA LINHA',vr)); continue
        usados.add(best[1]); lr=lidas[best[1]]
        for op,a0,a1,b0,b1 in difflib.SequenceMatcher(None,vr,lr,autojunk=False).get_opcodes():
            if op=='equal': ok+=a1-a0
            elif op=='delete': falta+=a1-a0; det.append(('faltou',vr[a0:a1]))
            elif op=='insert':
                for x in lr[b0:b1]:
                    if x!='?': sobra+=1; det.append(('sobrou',x))
            else:
                va,lb=vr[a0:a1],lr[b0:b1]
                for k in range(max(len(va),len(lb))):
                    if k<len(va) and k<len(lb):
                        if lb[k]=='?': qm+=1
                        else: err+=1; det.append(('ERRO',va[k],'lido',lb[k]))
                    elif k<len(va): falta+=1; det.append(('faltou',va[k]))
                    elif lb[k]!='?': sobra+=1; det.append(('sobrou',lb[k]))
    for i,lr in enumerate(lidas):
        if i not in usados:
            n=sum(1 for x in lr if x!='?'); sobra+=n
            if n: det.append(('LINHA A MAIS',lr))
    return dict(ok=ok,err=err,q=qm,falta=falta,sobra=sobra),det
VERDADE={
 144:[['C7','F','F/A','F/C','C','F','Bb','Bb/A','Gm7','Bb6'],['F/C','C','F','C7','F','Am','F7','Bb7M/9','Bb6','D7/A'],['Gm','Gm5dim','Bbm6','Csus','C7','F','C','F','C7/G','F/A','Bb','Bdim'],['F/C','Dm','Dm7','G7/9','C','C/Bb','F/A','Bb','G7(9)/B','Csus9','C','F']],
 250:[['F','Fdim','F','Bb/F','Bb','Bb6','F/C'],['C','F/C','C','Bb/D','C7','F','Bb/F','F','Bb/F','F','F7/A'],['Bbsus4/9','Bb','D7/A','Bb6/9','Bb6','C','F/C','C7','F']],
}
if __name__=='__main__':
    import os
    tot=dict(ok=0,err=0,q=0,falta=0,sobra=0)
    for pg,vd in VERDADE.items():
        fn=f'/tmp/cif/bruto/p{pg:03d}.json'
        if not os.path.exists(fn): fn=f'/tmp/cif/bruto{pg}_teste.json'
        if not os.path.exists(fn): print(pg,'ainda não lida'); continue
        res=decidir(json.load(open(fn)))
        if pg==250:   # só as 3 primeiras linhas foram conferidas a olho
            rows=em_linhas(res['c'],res['cap'])[:3]; res=dict(res,c=[x for rw in rows for x in rw])
        a,det=avaliar(res,vd); print(pg,a,det)
        for k in tot: tot[k]+=a[k]
    print('TOTAL',tot)
