import cv2,numpy as np,json,subprocess,os,re,unicodedata,tempfile
from multiprocessing import Pool
P={int(k):v for k,v in json.load(open('/tmp/nc/final/paginas.json')).items()}
REF={r['rot']:r['titulo'] for r in json.load(open('/tmp/nc/titulos.json'))}
def norm(s): return re.sub(r'[^a-z0-9 ]','',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode()).strip()
first={}
for pg,v in sorted(P.items()):
    if v['role']=='T' and v['hymn'] not in first: first[v['hymn']]=pg
def work(item):
    rot,pg=item
    e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png',0); h,w=e.shape
    top=e[:int(h*0.085)]
    sc=1800/w; top=cv2.resize(top,None,fx=sc,fy=sc,interpolation=cv2.INTER_CUBIC)
    top=cv2.copyMakeBorder(top,20,20,20,20,cv2.BORDER_CONSTANT,value=255)
    fd,fn=tempfile.mkstemp(suffix='.png',dir='/tmp/nc'); os.close(fd); cv2.imwrite(fn,top)
    r=subprocess.run(['tesseract',fn,'-','-l','por','--psm','6','tsv'],capture_output=True,text=True).stdout; os.remove(fn)
    rows=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        rows.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11],line=(c[2],c[3],c[4])))
    if not rows: return rot,pg,'',0
    hmax=max(r['h'] for r in rows)
    big=[r for r in rows if r['h']>=0.62*hmax and r['h']>=38]
    # a linha com mais letras grandes
    import collections
    byl=collections.defaultdict(list)
    for r in big: byl[r['line']].append(r)
    if not byl: return rot,pg,'',0
    line=max(byl.values(),key=lambda l:sum(len(x['t']) for x in l))
    line=sorted(line,key=lambda r:r['x'])
    words=[r for r in line if not re.fullmatch(r'\d{1,3}[A-Za-z]?',r['t'])]
    txt=' '.join(r['t'] for r in words); conf=min([r['conf'] for r in words],default=0)
    return rot,pg,txt,conf
if __name__=='__main__':
    items=[(rot,pg) for rot,pg in first.items() if P[pg]['q']>=7000]
    with Pool(2) as p: res=p.map(work,items,chunksize=8)
    out=[]
    for rot,pg,txt,conf in res:
        a=norm(txt); b=norm(REF[rot])
        if a!=b: out.append((rot,pg,REF[rot],txt,round(conf)))
    json.dump(res,open('/tmp/nc/titulos_ocr.json','w'),ensure_ascii=False)
    print(len(res),'lidos;',len(out),'diferentes')
    for o in out: print(o)
