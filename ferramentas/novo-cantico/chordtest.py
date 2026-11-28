import json,subprocess,re,os,cv2,numpy as np,sys
from enh import enhance
B=json.load(open('/tmp/nc/big.json'))
CH=re.compile(r'^[A-G][#b]?(m|maj|min|dim|aug|sus|add|M|º|°|\+|[0-9]|\(|\)|/[A-G][#b]?|/[0-9]|[#b](?=\d))*$')
def ocr(g,psm,lang,extra=()):
    fn='/tmp/nc/_c.png'; cv2.imwrite(fn,g)
    r=subprocess.run(['tesseract',fn,'-','-l',lang,'--psm',psm,*extra,'tsv'],capture_output=True,text=True).stdout
    rows=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        rows.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11]))
    return rows
g=cv2.imread(B['a'][0],0)
for name,img in (('raw',g),('enh',enhance(g))):
    for lang in ('eng','por'):
        rows=ocr(img,'11',lang)
        ch=[r for r in rows if CH.match(r['t'])]
        ch.sort(key=lambda r:(round(r['y']/60),r['x']))
        print(name,lang,len(rows),'chords:',len(ch))
        print('   ',' '.join(f"{r['t']}@{r['y']}" for r in ch))
