"""Páginas antigas em que a leitura normal não achou nada: lê as palavras da linha das cifras, uma a uma."""
import sys,json,os
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from nc_palavras import normal,cortes,ACORDE
def pagina(pg):
    import nc_pag
    from nccomum import lote
    rows,e,cap=nc_pag.linhas(pg,lim=170)
    out=[];imgs=[];ws=[]
    for rw in rows:
        for p in rw:
            if not (0.75*cap<=p['cap']<=1.3*cap): continue
            pad=int(0.5*p['cap'])+2
            g=e[max(0,p['y0']-pad):p['y1']+pad,max(0,p['x']-pad):p['x']+p['w']+pad]
            k=48/max(8,p['cap']); g=cv2.resize(g,None,fx=k,fy=k,interpolation=cv2.INTER_CUBIC)
            imgs.append(cv2.copyMakeBorder(g,12,12,12,12,cv2.BORDER_CONSTANT,value=255)); ws.append(p)
    res=lote(imgs,psm=7,tag='pv') if imgs else []
    bons=ruins=0; lista=[]
    for p,(txt,conf) in zip(ws,res):
        S=normal(txt)
        if ACORDE.match(S) and conf>=60: out.append([p['x'],p['base'],p['w'],p['cap'],S,0.9,p['y0'],p['y1']]); bons+=1
        else:
            cs=[c for c in cortes(S,4) if len(c)>1] if conf>=60 else []
            if cs: bons+=1; lista.append((S,'várias'))      # várias cifras coladas numa palavra: fica para depois
            else: ruins+=1; lista.append((S,round(conf)))
    return dict(pg=pg,cap=cap,c=out,bons=bons,ruins=ruins,outros=lista,linhas=len(rows))
if __name__=='__main__':
    for pg in [int(a) for a in sys.argv[1:]]:
        r=pagina(pg); print(pg,'linhas',r['linhas'],'lidas',r['bons'],'não lidas',r['ruins'],[c[4] for c in r['c']][:40]); print('    não lidas:',r['outros'][:30])
