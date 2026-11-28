"""Cifras do PDF "Hinário Novo Cântico – Cifras" nas coordenadas da página original (duas colunas),
para casar com fotos da página impressa. Saída: /tmp/cif/pdfhc.json {paginas:{p:{w,h,f,c:[[x,base,w,fs,txt,num]]}}, tons:{num:tom}, pags:{num:[p]}}"""
import json,os,re,sys,collections
import pymupdf
sys.path.insert(0,'/tmp/cif')
from acordes import eh_acorde
d=json.load(open('/tmp/hc/segs.json')); heads=d['heads']; segs=d['segs']; W=json.load(open('/tmp/hc/words.json'))
S=400/72; XR={0:(71,291),1:(305,525)}; STANZA=13
doc=pymupdf.open('/tmp/hc/hnc.pdf')
_tok={}
def tokens(p):
    if p in _tok: return _tok[p]
    out=[]
    for b in doc[p-1].get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                if 'Bold' not in s['font']: continue
                cur=None
                for ch in s['chars']:
                    c=ch['c']
                    if c.isspace() or c=='\xa0':
                        if cur: out.append(cur); cur=None
                        continue
                    x0,y0,x1,y1=ch['bbox']
                    if cur is None: cur=dict(t=c,x0=x0,x1=x1,base=ch['origin'][1],size=s['size'],y0=y0,y1=y1)
                    else: cur['t']+=c; cur['x1']=x1
                if cur: out.append(cur)
    _tok[p]=out; return out
pag=collections.defaultdict(list); tons={}; pags=collections.defaultdict(list)
for k in sorted(segs,key=int):
    h=heads[int(k)]; num=h['num']; rot=f"{num}{'-A' if h['label'] else ''}"; tom=None
    for p,c,y0,y1 in segs[k]:
        if p not in pags[rot]: pags[rot].append(p)
        x0,x1=XR[c]
        toks=[t for t in tokens(p) if x0-1<=t['x0']<x1 and y0-1.5<=t['base']<=y1+1.5]
        junt=[]
        for t in sorted(toks,key=lambda t:t['x0']):
            if re.fullmatch(r'[oO0º°]',t['t']) and t['size']<9:
                dono=[q for q in toks if q is not t and eh_acorde(q['t']) and q['x1']-1.5<=t['x0']<=q['x1']+3 and 0<=q['base']-t['base']<7]
                if dono: dono[0]['t']+='º'; dono[0]['x1']=max(dono[0]['x1'],t['x1']); continue
            junt.append(t)
        linhas=collections.defaultdict(list)
        for t in junt: linhas[round(t['base'],0)].append(t)
        for base,ts in sorted(linhas.items()):
            ts.sort(key=lambda t:t['x0'])
            cab=bool(re.fullmatch(r'\d{1,3}(-[A-Z])?',ts[0]['t'])) and len(ts)>1 and ts[0]['x0']<x0+20
            chave=None
            for i,t in enumerate(ts):
                if re.fullmatch(r'\d{1,2}/\d{1,2}',t['t']) and i>0 and eh_acorde(ts[i-1]['t']) and len(ts[i-1]['t'])<=4: chave=ts[i-1]; break
            if chave is not None: ts=[chave]; tom=tom or chave['t']
            elif cab: ts=[]
            else:
                ok=[t for t in ts if eh_acorde(t['t'])]
                ts=[] if len(ok)<0.6*len(ts) else ok
            for t in ts:
                pag[p].append([round(t['x0']*S),round(t['base']*S),round((t['x1']-t['x0'])*S),round(t['size']*S,1),t['t'],rot])
    if tom: tons[rot]=tom
out=dict(paginas={str(p):dict(w=3308,h=4678,f='t',c=cs) for p,cs in pag.items()},tons=tons,pags=pags)
json.dump(out,open('/tmp/cif/pdfhc.json','w'),ensure_ascii=False)
print(len(pag),'páginas',sum(len(c) for c in pag.values()),'cifras',len(tons),'tons'); print(pags['161'],tons.get('161'),pag[pags['161'][0]][:6])
