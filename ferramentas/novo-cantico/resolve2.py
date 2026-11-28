import json,re,collections
D=json.load(open('ident2.json'))
REF=json.load(open('titulos.json'))
rot2idx={r['rot']:k for k,r in enumerate(REF)}
by={d['name']:d for d in D}
def setT(name,rot,ver=None):
    d=by[name]; d['role']='T'; d['hymn']=rot2idx[rot]; d['hem']=9; d.pop('hymn_c',None)
    if ver is not None: d['version']=ver
def setC(name):
    d=by[name]; d['role']='C'; d.pop('hymn',None)
setT('a123S','139',1); setT('a131L','145'); setT('a133L','147'); setT('b019S','169'); setT('c011L','266'); setT('c083L','334')
setT('c108L','354-A'); setT('e001L','354-A'); setT('c126L','372'); setT('d004L','4'); setT('c158S','400-A'); setC('c159S')
setT('a076S','100',2)
# versões (1ª, 2ª, 3ª música)
for d in D:
    t=d['title'].lower()
    if d['role']=='T' and not d.get('version'):
        if re.search(r'terceira',t): d['version']=3
        elif re.search(r'segun|egund',t): d['version']=2
        elif re.search(r'prime|rimei',t): d['version']=1
# continuações herdam o hino da página de título anterior (na ordem do PDF)
for src in 'abcde':
    cur=None
    for d in [x for x in D if x['f']==src]:
        if d['role']=='T': cur=d['hymn']
        else: d['hymn_c']=cur
json.dump(D,open('ident3.json','w'),ensure_ascii=False)
seen=collections.OrderedDict()
for d in D:
    j=d['hymn'] if d['role']=='T' else d['hymn_c']
    seen.setdefault(REF[j]['rot'],[]).append(d['name'])
allrot=[r['rot'] for r in REF]
miss=[r for r in allrot if r not in seen]
print('hinos presentes',len(seen),'faltando',len(miss)); print(miss)
