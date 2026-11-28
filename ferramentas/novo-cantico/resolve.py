import json,re,unicodedata,collections,math
from rapidfuzz import fuzz
D=json.load(open('ident1.json'))
REF=json.load(open('titulos.json'))
def norm(s): return re.sub(r'[^a-z0-9 ]','',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode()).strip()
refn=[norm(r['titulo']) for r in REF]
STOP={'coro','primeira','segunda','musica','irregular'}
def clean_title(t):
    # só palavras em minúsculas/Capitalizadas (o nome da melodia vem em MAIÚSCULAS)
    ws=[w for w in t.split() if not (w.upper()==w and len(w)>2) and not re.search(r'\d',w)]
    ws=[w for w in ws if norm(w) not in STOP]
    return norm(' '.join(ws))
def tsim(t,j):
    if len(t)<3: return 0
    a=fuzz.token_sort_ratio(t,refn[j])/100
    # o título do hino aparece inteiro no que foi lido (sobram palavras da melodia etc.)
    rt=set(refn[j].split()); ot=set(t.split())
    if len(refn[j])>=5 and rt<=ot: a=max(a,0.93)
    return a
def numscore(nums,j):
    r=REF[j]; best=0
    target=str(r['num']); suf='A' if r['rot'].endswith('-A') else ''
    for n,s,x,conf,h in nums:
        o=str(n)
        if o==target: sc=1.0
        elif len(o)==len(target) and sum(a!=b for a,b in zip(o,target))==1: sc=0.45
        elif len(o)==len(target)-1 and (target.endswith(o) or target.startswith(o) or any(target[:k]+target[k+1:]==o for k in range(len(target)))): sc=0.4
        else: sc=0
        if sc and s!=suf: sc*=0.6 if suf else 0.85
        best=max(best,sc)
    return best
# emissões
for d in D:
    t=clean_title(d['title'])
    em=[]
    for j in range(len(REF)):
        ts=tsim(t,j); ns=numscore(d['nums'],j)
        em.append(0.9*ts*ts+0.8*ns)
    d['em']=em; d['ct']=t
    d['best']=max(em)
    d['bt']=max(tsim(t,j) for j in range(len(REF)))
    d['n2']=any(n[0]>=10 and n[4]>=40 for n in d['nums'])
    d['version']=2 if re.search(r'egund',d['title']) else (1 if re.search(r'rimei',d['title']) else 0)
out={}
for src in 'abcde':
    pages=[d for d in D if d['f']==src]
    # candidatas a página de título
    T=[d for d in pages if (d['bt']>=0.72 and len(d['ct'])>=6) or (d['n2'] and d['tag']!='R') or (d['n2'] and d['bt']>=0.5)]
    n=len(T); J=len(REF)
    INF=-1e9
    dp=[[INF]*J for _ in range(n)]; bk=[[0]*J for _ in range(n)]
    for j in range(J): dp[0][j]=T[0]['em'][j]
    for t in range(1,n):
        # transição: mesmo hino ou seguinte = 0; pular k hinos = -0.25*k (máx 3); voltar = -1.5
        prev=dp[t-1]
        # melhor anterior para cada j
        for j in range(J):
            best=INF;bi=0
            for dj,pen in ((0,0),(1,0),(2,-0.25),(3,-0.5),(4,-0.75),(5,-1.0),(6,-1.2),(7,-1.3),(8,-1.4)):
                i=j-dj
                if i>=0 and prev[i]+pen>best: best=prev[i]+pen;bi=i
            # voltar (reescaneou um anterior) ou pular muito
            gi=max(range(J),key=lambda i:prev[i]); 
            if prev[gi]-0.8>best: best=prev[gi]-0.8;bi=gi
            dp[t][j]=best+T[t]['em'][j]; bk[t][j]=bi
    j=max(range(J),key=lambda j:dp[n-1][j]); path=[j]
    for t in range(n-1,0,-1): j=bk[t][j]; path.append(j)
    path.reverse()
    for d,j in zip(T,path):
        if d['em'][j]<0.6 and d['tag']=='R': continue
        d['hymn']=j; d['hem']=d['em'][j]
    cur=None
    for d in pages:
        if 'hymn' in d: cur=d['hymn']; d['role']='T'
        else: d['role']='C'; d['hymn_c']=cur
for d in D:
    d.pop('em',None)
json.dump(D,open('ident2.json','w'),ensure_ascii=False)
for d in D:
    if d['role']=='T':
        r=REF[d['hymn']]; flag='' if d['hem']>=1.2 else ('  ?' if d['hem']>=0.7 else '  ???')
        print(f"{d['name']} T {r['rot']:>6} {r['titulo'][:26]:26} em={d['hem']:.2f} v{d['version']} N:{','.join(str(n[0])+n[1] for n in d['nums']) or '-'} [{d['ct'][:30]}] pg:{','.join(str(f[0]) for f in d['foot']) or '-'} q:{int(d['sharp'])}{flag}")
    else:
        r=REF[d['hymn_c']] if d.get('hymn_c') is not None else None
        print(f"{d['name']} c {(r['rot'] if r else '?'):>6} {'':26} best={d['best']:.2f} N:{','.join(str(n[0])+n[1] for n in d['nums']) or '-'} [{d['ct'][:30]}] pg:{','.join(str(f[0]) for f in d['foot']) or '-'} q:{int(d['sharp'])}")
