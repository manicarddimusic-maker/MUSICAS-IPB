import sys,json,glob,os,time
sys.path.insert(0,'/tmp/cif')
import cv2
import foto,foto_json
foto.ORDEM_FIXA=['si','bi']
R='/home/claude/musicas-ipb/public'
feitos=0
for f in sorted(glob.glob('/tmp/cif/foto_bruto/midias__caderninho3__*.json')):
    r=json.load(open(f))
    if foto_json.folha(r): continue
    cor=cv2.imread(R+r['img']); melhor=None
    for k in (1,):
        c2=cv2.resize(cor,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
        if max(c2.shape)>7000: continue
        n=foto.bruto_img(c2 if k!=1 else cor,r['img'],escala=2)
        for t in n['toks']:
            for q in ('x0','x1','y0','y1','base','cap'): t[q]=int(round(t[q]/k))
            t['sw']=round(t['sw']/k,2)
        n['w']=cor.shape[1]; n['h']=cor.shape[0]; n['img']=r['img']; n['giro']=0
        if n.get('cap'): n['cap']=round(n['cap']/k,1)
        d=foto_json.folha(n); q=len(d['c']) if d else 0
        if melhor is None or q>melhor[0]: melhor=(q,n)
        if q>=6: break
    if melhor and melhor[0]>0:
        json.dump(melhor[1],open(f,'w'),ensure_ascii=False); feitos+=1
    print(os.path.basename(r['img']),melhor[0] if melhor else 0,flush=True)
print('recuperadas',feitos)
