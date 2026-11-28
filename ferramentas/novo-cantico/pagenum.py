import json,re,collections,numpy as np
D=json.load(open('ident3.json'))
REF=json.load(open('titulos.json'))
PMAX=660
def emis(d):
    e=np.zeros(PMAX+1)
    for v,x,conf in d['foot']:
        s=str(v)
        for p in range(1,PMAX+1):
            t=str(p)
            if t==s: sc=1.0
            elif len(s)==len(t) and sum(a!=b for a,b in zip(s,t))==1: sc=0.35
            elif len(s)==len(t)-1 and any(t[:k]+t[k+1:]==s for k in range(len(t))): sc=0.3
            else: sc=0
            e[p]=max(e[p],sc)
    # paridade: esquerda = par, direita = ímpar
    if d['tag']=='L': e[1::2]-=0.8
    if d['tag']=='R': e[0::2]-=0.8
    if d['tag']=='S':
        lado=None
        big=[n for n in d['nums'] if n[4]>=40 and n[0]>=10]
        if d['role']=='T' and big:
            lado='L' if big[0][2]<900 else 'R'        # número do hino à esquerda = página par
        elif d['foot']:
            f=max(d['foot'],key=lambda x:x[2]); lado='L' if f[1]<900 else 'R'
        if lado=='L': e[1::2]-=0.6
        if lado=='R': e[0::2]-=0.6
    return e
res={}
for src in ('dabc','e'):
    P=[d for c in src for d in D if d['f']==c]
    n=len(P); E=[emis(d) for d in P]
    idx=np.arange(PMAX+1)
    diff=idx[None,:]-idx[:,None]      # diff[i,j]=j-i  (de i para j)
    T=np.full(diff.shape,-3.0)
    T[diff==1]=0; T[diff==0]=-0.7; T[diff==2]=-0.3; T[diff==3]=-0.45
    for k in range(4,12): T[diff==k]=-0.5-0.05*k
    for k in range(1,8): T[diff==-k]=-1.3-0.05*k
    dp=E[0].copy(); bk=[]
    for t in range(1,n):
        Tt=T
        a,b_=P[t-1],P[t]
        ha=a['hymn'] if a['role']=='T' else a.get('hymn_c'); hb=b_['hymn'] if b_['role']=='T' else b_.get('hymn_c')
        if b_['tag']=='R' and a['tag']=='L' and b_['i']==a['i']:
            Tt=np.where(diff==1,0,-50.0)
        elif b_['role']=='T' and ha!=hb:
            Tt=T.copy(); Tt[diff==0]=-50.0       # hino novo = página nova
            if ha is not None and hb>ha+1:
                need=hb-ha               # hinos que faltam no meio ocupam ao menos 1 página cada
                Tt[(diff>0)&(diff<need)]=-50.0
                Tt[diff==need]=-0.05; Tt[diff==need+1]=-0.15; Tt[diff==need+2]=-0.3
        elif b_['role']=='T' and a['role']=='T' and ha==hb:
            va,vb=a.get('version',0),b_.get('version',0)
            Tt=T.copy()
            if va and vb and va!=vb: Tt[diff==0]=-50.0     # 1ª e 2ª música: páginas diferentes
            elif va==vb: Tt[diff==0]=0.0; Tt[diff==1]=-0.5  # mesma página fotografada de novo
            else: Tt[diff==0]=-0.2; Tt[diff==1]=-0.2
        m=dp[:,None]+Tt
        b=m.argmax(axis=0); dp=m.max(axis=0)+E[t]; bk.append(b)
    j=int(dp.argmax()); path=[j]
    for b in reversed(bk): j=int(b[j]); path.append(j)
    path.reverse()
    for d,p in zip(P,path): d['pg']=p
json.dump(D,open('ident4.json','w'),ensure_ascii=False)
# conferências: página x hino monotônico; saltos
prev=None
for d in D:
    lab=REF[d['hymn']]['rot'] if d['role']=='T' else ''
    f=','.join(str(x[0]) for x in d['foot']) or '-'
    note=''
    if prev and (prev['f']==d['f'] or True):
        dl=d['pg']-prev['pg']
        if dl!=1: note=f'  <-- salto {dl:+d}'
    print(f"{d['name']} pg={d['pg']:3d} ocr={f:10s} {d['role']} {lab:6s} q={int(d['sharp'])}{note}")
    prev=d
