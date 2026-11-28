import json,re,subprocess,os,shutil
W=json.load(open('words.json'))
GUT=305
def col(w): return 0 if w[0]<GUT else 1
def line_words(ws,x0,y0,x1,c):
    return sorted([w for w in ws if abs(w[1]-y0)<2.5 and w[0]>=x1-0.1 and col(w)==c],key=lambda w:w[0])
def title_words(ws,i,skip=0):
    x0,y0,x1,y1,t=ws[i]; c=col(ws[i]); out=[]; prev=x1
    ln=line_words(ws,x0,y0,x1,c)
    for w in ln[skip:]:
        if w[0]-prev>16 and out: break
        out.append(w[4]); prev=w[2]
        if w[4].endswith('.'): break
    return out,y0,c,ws[i]
SMALL={'de','da','do','das','dos','e','a','o','as','os','em','no','na','ao','à','pelo','pela','por','para','com','um','uma','que','nos','nas','ou'}
def tc(s):
    ws=s.lower().split(); r=[]
    for i,w in enumerate(ws):
        if i>0 and w in SMALL: r.append(w)
        else: r.append(re.sub(r'^([^\wÀ-ú]*)(\w)',lambda m:m.group(1)+m.group(2).upper(),w))
    return ' '.join(r)
heads=[]  # (page, col, y0, num, label, title)
for pi,ws in enumerate(W,1):
    for i,(x0,y0,x1,y1,t) in enumerate(ws):
        if re.fullmatch(r'\d{1,3}',t) and 1<=int(t)<=400 and (abs(x0-85)<2 or abs(x0-319)<2):
            nxt=sorted([w for w in ws if abs(w[1]-y0)<2 and w[0]>x1 and w[0]-x1<25])
            if not(nxt and nxt[0][4].upper()==nxt[0][4] and re.match(r'[A-ZÀ-Ú\-]',nxt[0][4])): continue
            label=None; skip=0
            if nxt[0][4]=='-': label=f'{t}-{nxt[1][4]}'; skip=2
            tw,_,c,_=title_words(ws,i,skip)
            if tw and tw[-1].endswith(','):
                ys=sorted(set(round(w[1],1) for w in ws if col(w)==c and 8<w[1]-y0<18))
                if ys:
                    nl=sorted([w for w in ws if abs(w[1]-ys[0])<2.5 and col(w)==c],key=lambda w:w[0])
                    prev=nl[0][0]-1
                    for w in nl:
                        if w[0]-prev>16: break
                        tw.append(w[4]); prev=w[2]
                        if w[4].endswith('.'): break
            tit=' '.join(tw)
            tit=re.sub(r'\s+[A-G][#b]?-?\s+\d+/\d+$','',tit)
            tit=re.sub(r'\s+[A-G][#b]?-?$','',tit) if re.search(r'\s[A-G][#b]?-?$',tit) and not tit.endswith('.') and len(tit.split())>2 and False else tit
            tit=tit.strip(' .,!').replace('!.','!')
            tit=tit.replace(' !','!').replace(' .','')
            tit=tc(tit).replace('Glória Á','Glória à')
            heads.append(dict(page=pi,col=c,y=y0,num=int(t),label=label,title=tit,x=x0))
for pi,ws in enumerate(W,1):
    for i,(x0,y0,x1,y1,t) in enumerate(ws):
        m=re.fullmatch(r'(\d{1,3})-([A-Z])',t)
        if m and (abs(x0-85)<2 or abs(x0-319)<2):
            tw,_,c,_=title_words(ws,i,0)
            tit=' '.join(tw); tit=re.sub(r'\s+[A-G][#b]?-?\s+\d+/\d+$','',tit)
            tit=tit.strip(' .,!'); tit=tc(tit)
            heads.append(dict(page=pi,col=c,y=y0,num=int(m.group(1)),label=t,title=tit,x=x0))
print(len(heads))
# ordem de leitura: pagina, coluna, y
heads.sort(key=lambda h:(h['page'],h['col'],h['y']))
cols=[(p,c) for p in range(1,len(W)+1) for c in (0,1)]
segs={}  # idx hino -> lista de (page,col,ytop,ybot)
cur=None
for (p,c) in cols:
    ws=[w for w in W[p-1] if col(w)==c]
    if not ws: continue
    hs=[h for h in heads if h['page']==p and h['col']==c]
    ys=[h['y'] for h in hs]
    top_end=ys[0]-1 if ys else 1e9
    pre=[w for w in ws if w[1]<top_end]
    if pre and cur is not None:
        segs.setdefault(cur,[]).append((p,c,min(w[1] for w in pre),max(w[3] for w in pre)))
    for k,h in enumerate(hs):
        end=(ys[k+1]-1) if k+1<len(hs) else 1e9
        body=[w for w in ws if h['y']-1<=w[1]<end]
        idx=heads.index(h); cur=idx
        segs.setdefault(idx,[]).append((p,c,min(w[1] for w in body),max(w[3] for w in body)))
json.dump({'heads':heads,'segs':{str(k):v for k,v in segs.items()}},open('segs.json','w'),ensure_ascii=False)
multi=[(heads[i]['num'],len(v)) for i,v in segs.items() if len(v)>1]
print('hinos com continuacao:',len(multi),multi[:40])
