import json,re,unicodedata,collections
from rapidfuzz import fuzz,process
P=json.load(open('pages.json'))
REF=json.load(open('titulos.json'))
def norm(s): return re.sub(r'[^a-z0-9 ]','',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode()).strip()
refn=[norm(r['titulo']) for r in REF]
def ident(p):
    W=1800; top=p['top']; Hs=p['h']*0.15*p['sc']
    # tokens grandes (titulo): altura >= 34 px nessa escala
    big=[t for t in top if t['h']>=38 and t['conf']>30]
    nums=[]
    for t in top:
        m=re.fullmatch(r'(\d{1,3})[\s\-]?([AB])?[.,]?',t['t'])
        if m and t['h']>=40 and (t['x']<0.2*W or t['x']+t['w']>0.8*W):
            nums.append((int(m.group(1)),m.group(2) or '',t['x'],t['conf'],t['h']))
    words=[t for t in sorted(big,key=lambda t:(round(t['y']/60),t['x'])) if not re.fullmatch(r'[\d\W]+',t['t'])]
    title=' '.join(t['t'] for t in words)
    cand=None
    if len(norm(title))>=4:
        m=process.extractOne(norm(title),refn,scorer=fuzz.token_set_ratio)
        m2=process.extractOne(norm(title),refn,scorer=fuzz.ratio)
        cand=(m[2],m[1],m2[2],m2[1])
    foot=[]
    for t in p['foot']:
        m=re.fullmatch(r'[\(\[]?(\d{1,3})[\)\]\.,]?',t['t'])
        if m and (t['x']<0.22*W or t['x']+t['w']>0.78*W): foot.append((int(m.group(1)),t['x'],t['conf']))
    return dict(nums=nums,title=title,cand=cand,foot=foot)
out=[]
for p in P:
    d=ident(p); d.update(name=p['name'],f=p['f'],i=p['i'],tag=p['tag'],w=p['w'],h=p['h'],sharp=p['sharp'],dark=p['dark'])
    out.append(d)
json.dump(out,open('ident1.json','w'),ensure_ascii=False)
for d in out:
    c=d['cand']; cs=f"{REF[c[0]]['rot']}:{REF[c[0]]['titulo'][:22]}({int(c[1])})/{REF[c[2]]['rot']}({int(c[3])})" if c else '-'
    print(d['name'],'N:',','.join(f"{n[0]}{n[1]}" for n in d['nums']) or '-','| T:',d['title'][:34],'| ref:',cs,'| pg:',','.join(str(f[0]) for f in d['foot']) or '-','| q:',int(d['sharp']))
