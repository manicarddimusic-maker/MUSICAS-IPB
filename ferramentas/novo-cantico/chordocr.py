"""Localiza e lê as cifras impressas acima da pauta (negrito, sem serifa) numa página de partitura."""
import subprocess,re,os,cv2,numpy as np,json,tempfile
from enh import enhance
CH=re.compile(r'^[A-G][#b]?(m(?!a)|maj|min|dim|aug|sus|add|M|º|°|\+|-|[0-9]|\(|\)|/[A-G][#b]?|/[0-9]|[#b](?=\d))*$')
WL='ABCDEFGMabdgijmnsu#+-/()0123456789º°'
def tess_words(img,psm,lang='eng',wl=None):
    fd,fn=tempfile.mkstemp(suffix='.png',dir='/tmp/nc'); os.close(fd); cv2.imwrite(fn,img)
    cmd=['tesseract',fn,'-','-l',lang,'--psm',str(psm)]
    if wl: cmd+=['-c','tessedit_char_whitelist='+wl]
    cmd+=['tsv']
    r=subprocess.run(cmd,capture_output=True,text=True).stdout; os.remove(fn)
    rows=[]
    for ln in r.splitlines()[1:]:
        c=ln.split('\t')
        if len(c)<12 or not c[11].strip(): continue
        rows.append(dict(x=int(c[6]),y=int(c[7]),w=int(c[8]),h=int(c[9]),conf=float(c[10]),t=c[11]))
    return rows
def estimate_cap(e):
    """altura das maiúsculas das cifras, pela leitura geral da página"""
    s=1800/e.shape[0]; small=cv2.resize(e,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    rows=tess_words(small,11,'eng')
    hs=[r['h']/s for r in rows if CH.match(r['t']) and len(r['t'])>=2 and r['conf']>80 and re.search(r'[A-G]',r['t'])]
    return (float(np.median(hs)) if len(hs)>=3 else None), rows, s
def components(e,cap):
    bw=(e<150).astype(np.uint8)
    n,lab,st,cen=cv2.connectedComponentsWithStats(bw,8)
    dt=cv2.distanceTransform(bw,cv2.DIST_L2,3)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if h<0.3*cap or h>1.7*cap or w>2.2*cap or a<0.03*cap*cap: continue
        m=dt[y:y+h,x:x+w][lab[y:y+h,x:x+w]==i]
        sw=2*float(np.percentile(m,90))   # espessura do traço
        out.append(dict(x=int(x),y=int(y),w=int(w),h=int(h),a=int(a),sw=sw,id=i))
    return out,lab
def group_tokens(comps,cap):
    """junta os glifos vizinhos (mesma linha, colados) em palavras"""
    comps=sorted(comps,key=lambda c:c['x'])
    toks=[]
    for c in comps:
        best=None
        for t in toks:
            if c['x']-t['x1']>0.42*cap: continue
            if c['x']<t['x0']-2: continue
            # sobreposição vertical com a palavra
            ov=min(t['y1'],c['y']+c['h'])-max(t['y0'],c['y'])
            if ov>0.35*min(c['h'],t['y1']-t['y0']): best=t
        if best is None:
            toks.append(dict(x0=c['x'],x1=c['x']+c['w'],y0=c['y'],y1=c['y']+c['h'],cs=[c]))
        else:
            best['x1']=max(best['x1'],c['x']+c['w']); best['y0']=min(best['y0'],c['y']); best['y1']=max(best['y1'],c['y']+c['h']); best['cs'].append(c)
    return toks
if __name__=='__main__':
    import sys
    B=json.load(open('/tmp/nc/big.json'))
    g=cv2.imread(B['a'][0],0); e=enhance(g)
    cap,rows,s=estimate_cap(e); print('cap',cap)
    comps,lab=components(e,cap)
    bold=[c for c in comps if c['sw']>=0.15*cap and c['h']>=0.75*cap and c['h']<=1.45*cap]
    print(len(comps),'comps',len(bold),'bold-caps')
    import collections
    print(collections.Counter(round(c['sw']/cap,2) for c in comps).most_common(12))
    vis=cv2.cvtColor(e,cv2.COLOR_GRAY2BGR)
    for c in comps:
        col=(0,0,255) if c in bold else (200,160,0)
        cv2.rectangle(vis,(c['x'],c['y']),(c['x']+c['w'],c['y']+c['h']),col,1)
    cv2.imwrite('/tmp/nc/cc_a0.jpg',vis[480:1400],[cv2.IMWRITE_JPEG_QUALITY,80])
