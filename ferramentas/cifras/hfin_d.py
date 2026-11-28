"""Etapa D: monta as cifras de cada foto riscada: cifra impressa (já no tom da caneta) no lugar do risco,
borrachas para os riscos e para as letras à mão, marcas "?" para o que não se sabe.
Depois aplica as correções feitas à mão (arquivo /tmp/cif/hfin/corr/<nome>.txt, coordenadas da imagem de conferência)."""
import sys,json,glob,os,re,subprocess
sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
import hfin_b,hfin_c,mao
from hfin_rot import carregar_rotulos,rotulo_de
from hinos_final import FORA,SEM_BORRACHA
R='/home/claude/musicas-ipb/public'
NOTA=re.compile(r'^[A-G][#b]?$')
LARG_CONF=1800          # largura (ou altura, a maior) da imagem de conferência
def ORD(fonte):
    return int(fonte.split(':')[1]) if fonte.startswith('nc') else (5000 if fonte.startswith('mao') else 0)
def larg_txt(t,cap):
    return cap*sum(0.33 if ch in '/()+' else 0.62 for ch in t)
def papel(cor,x0,y0,x1,y1):
    a=cor[max(0,int(y0)-4):int(y1)+4,max(0,int(x0)-4):int(x1)+4].reshape(-1,3)
    if len(a)==0: return 'ffffff'
    sm=a.sum(axis=1); cl=a[sm>=np.percentile(sm,70)]
    return '%02x%02x%02x'%tuple(int(v) for v in np.median(cl,axis=0)[::-1])
def montar(nome,ROT):
    rr=hfin_b.analisar(nome,guardar_faixas=True)
    if not rr: return None
    o,faixas,up=rr
    C_=hfin_c.classificar(o)
    linhas=[]
    por_fonte={}
    for x in C_:
        for q in x['L']['cif']: por_fonte.setdefault(x['L']['fi'],[]).append(q.get('tinta',1.0)>0.035)
    falsas={fi for fi,v in por_fonte.items() if len(v)>=4 and sum(v)<0.35*len(v)}
    itens=[]; soltas=[]; livres=[]; letras_livres=[]
    sem_b=any(nome.startswith(p) for p in SEM_BORRACHA); capd_m=[]
    for x in C_:
        L=x['L']
        if L['fi'] in falsas: continue
        c=x['c']; f=L['f']; cap=L['cap']; fonte=L['fonte']; bf=L['base_foto']; esc=L['esc']; capd_m.append(cap*esc)
        lin=len(linhas); linhas.append(dict(L=L,c=c,faixa=faixas[(L['fi'],L['ri'])],livres=[],letras=[]))
        def pt(u):
            i=float(np.clip(u/8.0,0,len(bf)-1)); a=int(np.floor(i)); b=min(len(bf)-1,a+1); t=i-a
            return bf[a][0]+t*(bf[b][0]-bf[a][0]),bf[a][1]+t*(bf[b][1]-bf[a][1])
        def bsrc(u):
            bs_=L['base_src']; i=int(np.clip(u/8.0,0,len(bs_)-1)); return bs_[i]
        V=[]
        for q in L['cif']:
            t=q['txt']; lit=False; rot=None
            if '=' in t:
                # lugar completado à mão: "IMPRESSA=ESCRITA" (o que vale nesta folha é o que está escrito à mão)
                imp,mao_=t.split('=',1)
                if mao_=='x': rot='x'; t='?'
                else: t=mao_; lit=True
            V.append(dict(u0=q['x0'],u1=q['x1'],txt=t,lit=lit,riscos=[q['risco']] if q.get('risco') is not None else [],tipo='vaga',ids=[q['i']],xs=q['xs'],bs=q['bs'],ws=q['ws'],rot=rot))
        for ri in ([] if fonte.startswith('mao') else x['desconhecidos']):
            r=L['riscos'][ri]; V.append(dict(u0=r[0],u1=r[2],txt='?',lit=False,riscos=[ri],tipo='risco',ids=[],xs=L['xs0']+r[0]/f,bs=bsrc((r[0]+r[2])/2),ws=(r[2]-r[0])/f,rot=None))
        V.sort(key=lambda v:v['u0'])
        for v in V:
            if v['txt']=='?' and v['rot'] is None:
                r=rotulo_de(ROT,fonte,v['xs'],v['bs'],cap,v['ws'])
                if r: v['rot']=r['txt']
        vivos=[True]*len(V); so_borr=[]
        def junta(a,b):
            a['u0']=min(a['u0'],b['u0']); a['u1']=max(a['u1'],b['u1']); a['riscos']=list(dict.fromkeys(a['riscos']+b['riscos'])); a['ids']=a['ids']+b['ids']
        for n,v in enumerate(V):
            if not vivos[n] or v['rot'] is None: continue
            t=v['rot']
            if t=='-': vivos[n]=False; continue
            if t=='x': vivos[n]=False; so_borr+=v['riscos']; continue
            if t=='?': continue
            if t.startswith('<'):
                esq=[m for m in range(n-1,-1,-1) if vivos[m]]
                if esq and v['u0']-V[esq[0]]['u1']<2.5*c:
                    w=V[esq[0]]; w['txt']=t[1:]; w['lit']=False; junta(w,v); vivos[n]=False
                else: v['txt']=t[1:]; v['u0']=v['u1']-larg_txt(t[1:],c)
                continue
            if t.endswith('>'):
                v['txt']=t[:-1]
                dire=[m for m in range(n+1,len(V)) if vivos[m]]
                if dire and V[dire[0]]['u0']-v['u1']<2.5*c: junta(v,V[dire[0]]); vivos[dire[0]]=False
                else: v['u1']=v['u0']+larg_txt(v['txt'],c)
                continue
            if t.startswith('['): v['txt']=t[1:]; v['u0']=min(v['u0'],v['u1']-larg_txt(t[1:],c)); continue
            if t.endswith(']'): v['txt']=t[:-1]; v['u1']=max(v['u1'],v['u0']+larg_txt(t[:-1],c)); continue
            if t.startswith('='): v['txt']=t[1:]; v['lit']=True; continue
            v['txt']=t
        V2=[v for n,v in enumerate(V) if vivos[n]]
        j=0
        while j<len(V2)-1:       # barra perdida: "Eb" + "G" colados = "Eb/G"
            a,b=V2[j],V2[j+1]
            if a['txt']!='?' and b['txt']!='?' and not a['lit'] and not b['lit'] and b['u0']-a['u1']<0.45*c and NOTA.match(b['txt']) and '/' not in a['txt']:
                a['txt']=a['txt']+'/'+b['txt']; junta(a,b); del V2[j+1]; continue
            j+=1
        j=0
        while j<len(V2)-1:       # a mesma cifra duas vezes quase no mesmo lugar (vaga + risco deslocado)
            a,b=V2[j],V2[j+1]
            if a['txt']!='?' and a['txt']==b['txt'] and b['u0']-a['u1']<2.2*c and (a['tipo']=='risco' or b['tipo']=='risco'):
                fica,sai=(a,b) if a['tipo']=='risco' else (b,a)
                u0,u1=fica['u0'],fica['u1']; junta(fica,sai); fica['u0'],fica['u1']=u0,u1; V2.remove(sai); continue
            j+=1
        V3=[]
        for v in V2:             # vários acordes num rótulo só ("Dsus+D")
            ps=v['txt'].split('+')
            if len(ps)>1 and all(re.match(r'^[A-G]',p) for p in ps):
                tot=sum(len(p)+1 for p in ps); u=v['u0']
                for p in ps:
                    w=(v['u1']-v['u0'])*(len(p)+1)/tot; d=dict(v); d.update(txt=p,u0=u,u1=u+w-0.25*c); V3.append(d); u+=w
            else: V3.append(v)
        # letras à mão de cada vaga/risco
        letras_de_vaga={}; letras_de_risco={}
        for li,(tp,quem) in x['letras_de'].items():
            (letras_de_vaga if tp=='c' else letras_de_risco).setdefault(quem,[]).append(li)
        ao_lado={}
        for ri,ci in x['ao_lado']: ao_lado.setdefault(ci,[]).append(ri)
        usados_r=set(so_borr); usadas_l=set()
        for v in V3:
            x0,y0=pt(v['u0']); x1,y1=pt(v['u1']); base=(y0+y1)/2; capd=cap*esc
            bs=[]
            if not sem_b:
                for ri in v['riscos']: bs.append(L['riscos_foto'][ri])
                for i in v['ids']:
                    for ri in ao_lado.get(i,[]): bs.append(L['riscos_foto'][ri]); usados_r.add(ri)
                    for li in letras_de_vaga.get(i,[]): bs.append(L['letras_foto'][li]); usadas_l.add(li)
                for ri in v['riscos']:
                    for li in letras_de_risco.get(ri,[]): bs.append(L['letras_foto'][li]); usadas_l.add(li)
            usados_r.update(v['riscos'])
            itens.append(dict(x=x0,base=base,w=max(x1-x0,0.5*capd),cap=capd,txt=v['txt'],lit=v['lit'],borr=bs,lin=lin,u0=v['u0'],u1=v['u1'],anc=bool(v['riscos']),
                              ordem=(ORD(fonte),L['bs'],v['u0'])))
        if not sem_b:
            for ri in so_borr:
                soltas.append(L['riscos_foto'][ri])
                for li in letras_de_risco.get(ri,[]): soltas.append(L['letras_foto'][li]); usadas_l.add(li)
        capd=cap*esc
        for ri,r in enumerate(L['riscos']):
            if ri not in usados_r and r[4]>=0.2*c*c: livres.append(dict(b=L['riscos_foto'][ri],cap=capd,lin=lin,u0=r[0],u1=r[2],ordem=(ORD(fonte),L['bs'],r[0])))
        for li,l in enumerate(L['letras']):
            if li not in usadas_l: letras_livres.append(dict(b=L['letras_foto'][li],cap=capd,lin=lin,u0=l[0],u1=l[2]))
    return dict(o=o,itens=itens,soltas=soltas,livres=livres,letras_livres=letras_livres,up=up,falsas=len(falsas),capd=float(np.median(capd_m)) if capd_m else 22.0,linhas=linhas)
def corrigir(nome,m):
    """correções à mão, em coordenadas da imagem de conferência (a foto reduzida para LARG_CONF)"""
    fn=f'/tmp/cif/hfin/corr/{nome}.txt'
    if not os.path.exists(fn): return 0
    up=m['up']; H,W=up.shape[:2]; s=max(H,W)/LARG_CONF; n=0
    pen=None
    def caneta():
        nonlocal pen
        if pen is None:
            picos=[p for p in mao.picos_de_cor(up,70) if not (10<=p[0]<=40)]
            if picos:
                h_,s_,v_=mao._hsv(up); cz=cv2.cvtColor(up,cv2.COLOR_BGR2GRAY)
                dh=np.abs(h_-picos[0][0]); dh=np.minimum(dh,180-dh)
                pen=(((s_>=60)&(dh<=22)&(v_>40)&(v_<250))|((s_>=22)&(dh<=16)&(cz<185))).astype(np.uint8)
            else: pen=np.zeros((H,W),np.uint8)
        return pen
    def perto(lista,X,Y,raio):
        best=None
        for e in lista:
            cx=e['x']+e['w']/2; cy=e['base']-e['cap']/2; d=np.hypot(cx-X,(cy-Y)*1.5)
            if d<raio and (best is None or d<best[0]): best=(d,e)
        return best[1] if best else None
    for ln in open(fn):
        ln=ln.split(';')[0].strip()
        if not ln: continue
        p=ln.split(); op=p[0]
        if re.fullmatch(r'L\d+',op):
            li_=int(op[1:]); op2=p[1]; U=float(p[2]); Lr=m['linhas'][li_]; L=Lr['L']; c=Lr['c']; bf=L['base_foto']; capd=L['cap']*L['esc']
            def ptL(u):
                i=float(np.clip(u/8.0,0,len(bf)-1)); a_=int(np.floor(i)); b_=min(len(bf)-1,a_+1); t=i-a_
                return bf[a_][0]+t*(bf[b_][0]-bf[a_][0]),bf[a_][1]+t*(bf[b_][1]-bf[a_][1])
            da_linha=[e for e in m['itens'] if e.get('lin')==li_]
            alvo=min(da_linha,key=lambda e:abs((e['u0']+e['u1'])/2-U)) if da_linha else None
            if alvo is not None and abs((alvo['u0']+alvo['u1'])/2-U)>max(2.2*c,(alvo['u1']-alvo['u0'])/2+1.2*c): alvo=None
            if op2=='set':
                if alvo is None: print('   !! set sem alvo:',nome,ln); continue
                alvo['txt']=p[3]; alvo['lit']=True; n+=1
            elif op2=='del':
                if alvo is None: print('   !! del sem alvo:',nome,ln); continue
                if len(p)>3 and p[3]=='borr': m['soltas']+=alvo['borr']+[[alvo['x']-2,alvo['base']-1.15*alvo['cap'],alvo['x']+alvo['w']+2,alvo['base']+0.2*alvo['cap']]]
                m['itens'].remove(alvo); n+=1
            elif op2=='mv':
                if alvo is None: print('   !! mv sem alvo:',nome,ln); continue
                d=float(p[3]); alvo['u0']+=d; alvo['u1']+=d; x0,y0=ptL(alvo['u0']); x1,y1=ptL(alvo['u1']); alvo['x']=x0; alvo['base']=(y0+y1)/2; n+=1
            elif op2=='add':
                txt=p[3]; liv=[lv for lv in m['livres'] if lv['lin']==li_]
                best=min(liv,key=lambda lv:abs((lv['u0']+lv['u1'])/2-U)) if liv else None
                bs=[]
                if best is not None and abs((best['u0']+best['u1'])/2-U)<=max(1.8*c,(best['u1']-best['u0'])/2+0.8*c):
                    u0,u1=best['u0'],best['u1']; bs.append(best['b']); m['livres'].remove(best)
                else:
                    w=larg_txt(txt,c); u0=U-w/2; u1=U+w/2
                for ll in list(m['letras_livres']):
                    if ll['lin']==li_ and ll['u0']<u1+0.9*c and ll['u1']>u0-0.9*c: bs.append(ll['b']); m['letras_livres'].remove(ll)
                x0,y0=ptL(u0); x1,y1=ptL(u1)
                m['itens'].append(dict(x=x0,base=(y0+y1)/2,w=max(x1-x0,0.5*capd),cap=capd,txt=txt,lit=True,borr=bs,lin=li_,u0=u0,u1=u1,ordem=(ORD(L['fonte']),L['bs'],u0))); n+=1
            elif op2=='x':        # só apaga a tinta da caneta perto de U (risco livre e letras livres)
                for lv in list(m['livres']):
                    if lv['lin']==li_ and lv['u0']<U+1.2*c and lv['u1']>U-1.2*c: m['soltas'].append(lv['b']); m['livres'].remove(lv)
                for ll in list(m['letras_livres']):
                    if ll['lin']==li_ and ll['u0']<U+1.2*c and ll['u1']>U-1.2*c: m['soltas'].append(ll['b']); m['letras_livres'].remove(ll)
                n+=1
            continue
        if op in ('set','del','add','mv') and not re.fullmatch(r'L\d+',op):
            X=float(p[1])*s; Y=float(p[2])*s
        if op=='set':
            e=perto(m['itens'],X,Y,90*s/ (1800/LARG_CONF) *0.6)
            if e is None: print('   !! set sem alvo:',nome,ln); continue
            e['txt']=p[3]; e['lit']=True; n+=1
        elif op=='del':
            e=perto(m['itens'],X,Y,60*s)
            if e is None: print('   !! del sem alvo:',nome,ln); continue
            if len(p)>3 and p[3]=='borr': m['soltas']+=e['borr']+[[e['x']-2,e['base']-1.15*e['cap'],e['x']+e['w']+2,e['base']+0.2*e['cap']]]      # some a cifra, ficam as borrachas
            m['itens'].remove(e); n+=1
        elif op=='add':
            txt=p[3]; capd=m['capd']
            # risco livre mais próximo
            best=None
            for lv in m['livres']:
                b=lv['b']; d=np.hypot((b[0]+b[2])/2-X,((b[1]+b[3])/2-Y)*1.2)
                if d<55*s and (best is None or d<best[0]): best=(d,lv)
            bs=[]
            if best:
                lv=best[1]; b=lv['b']; capd=lv['cap']; x0=b[0]; base=b[3]-0.15*capd; w=max(b[2]-b[0],0.6*capd); bs.append(b); m['livres'].remove(lv); ordem=lv['ordem']
            else:
                w=larg_txt(txt,capd); x0=X-w/2; base=Y+0.5*capd; ordem=(9999,Y,X)
                # sem faixa lida ali: procura a tinta da caneta em volta (risco embaixo, letra em cima)
                pm=caneta()
                if pm.any():
                    ya=int(max(0,Y-4.6*capd)); yb=int(min(H,Y+1.3*capd)); xa=int(max(0,X-2.6*capd)); xb=int(min(W,X+2.6*capd))
                    reg=cv2.dilate(pm[ya:yb,xa:xb],np.ones((max(3,int(0.3*capd))|1,max(3,int(0.5*capd))|1),np.uint8))
                    nn,lab,st,cen=cv2.connectedComponentsWithStats(reg,8)
                    for i in range(1,nn):
                        bx,by,bw_,bh_,ar=[int(v) for v in st[i]]
                        if ar<0.25*capd*capd: continue
                        cxg=xa+bx+bw_/2
                        if abs(cxg-X)<=1.6*capd+bw_/2*0.3: bs.append([xa+bx,ya+by,xa+bx+bw_,ya+by+bh_])
            # letras livres logo acima
            for ll in list(m['letras_livres']):
                b=ll['b']
                if b[0]<x0+w+0.8*capd and b[2]>x0-0.8*capd and b[3]<=base+1.2*capd and (b[1]+b[3])/2<base and b[3]>=base-5*capd:
                    bs.append(b); m['letras_livres'].remove(ll)
            m['itens'].append(dict(x=x0,base=base,w=w,cap=capd,txt=txt,lit=True,borr=bs,ordem=ordem)); n+=1
        elif op=='mv':
            e=perto(m['itens'],X,Y,60*s)
            if e is None: print('   !! mv sem alvo:',nome,ln); continue
            e['x']+=float(p[3])*s
            if len(p)>4: e['base']+=float(p[4])*s
            n+=1
        elif op=='put':
            # cifra escrita à mão onde não havia cifra impressa: texto novo com a esquerda em X e a linha de base em Y
            X=float(p[1])*s; Y=float(p[2])*s; capd=m['capd']*(float(p[4]) if len(p)>4 else 1.0); txt=p[3]
            m['itens'].append(dict(x=X,base=Y,w=larg_txt(txt,capd),cap=capd,txt=txt,lit=True,borr=[],ordem=(9999,Y,X))); n+=1
        elif op=='delq':
            # tira as marcas "?" dentro de um retângulo (engano do detector)
            x0,y0,x1,y1=[float(v)*s for v in p[1:5]]
            antes=len(m['itens'])
            m['itens']=[e for e in m['itens'] if not (e['txt']=='?' and x0<=e['x']+e['w']/2<=x1 and y0<=e['base']-e['cap']/2<=y1)]
            if len(m['itens'])==antes: print('   !! delq sem alvo:',nome,ln)
            n+=1
        elif op=='no':
            # o que foi tomado por risco perto de X,Y não é nada (número, sujeira): esquece, sem marcar nem apagar
            X=float(p[1])*s; Y=float(p[2])*s
            m['livres']=[lv for lv in m['livres'] if np.hypot((lv['b'][0]+lv['b'][2])/2-X,(lv['b'][1]+lv['b'][3])/2-Y)>=45*s]
            m['letras_livres']=[ll for ll in m['letras_livres'] if np.hypot((ll['b'][0]+ll['b'][2])/2-X,(ll['b'][1]+ll['b'][3])/2-Y)>=45*s]
            n+=1
        elif op=='x':
            # tinta de caneta sem cifra (risco solto) perto de X,Y: só apagar quando o tom mudar
            X=float(p[1])*s; Y=float(p[2])*s; achou=False
            for lv in list(m['livres']):
                b=lv['b']
                if np.hypot((b[0]+b[2])/2-X,(b[1]+b[3])/2-Y)<45*s: m['soltas'].append(b); m['livres'].remove(lv); achou=True
            for ll in list(m['letras_livres']):
                b=ll['b']
                if np.hypot((b[0]+b[2])/2-X,(b[1]+b[3])/2-Y)<45*s: m['soltas'].append(b); m['letras_livres'].remove(ll); achou=True
            if not achou: print('   !! x sem alvo:',nome,ln)
            n+=1
        elif op=='era':
            x0,y0,x1,y1=[float(v)*s for v in p[1:5]]; m['soltas'].append([int(x0),int(y0),int(x1),int(y1)]); n+=1
        elif op=='noera':
            X=float(p[1])*s; Y=float(p[2])*s
            for e in m['itens']: e['borr']=[b for b in e['borr'] if not (b[0]<=X<=b[2] and b[1]<=Y<=b[3])]
            m['soltas']=[b for b in m['soltas'] if not (b[0]<=X<=b[2] and b[1]<=Y<=b[3])]; n+=1
    return n
if __name__=='__main__':
    ROT=carregar_rotulos()
    ns=[os.path.basename(f)[:-5] for f in sorted(glob.glob('/tmp/cif/hfin/h*.json'))]
    ns=[n for n in ns if not any(n.startswith(p) for p in FORA)]
    args=[a for a in sys.argv[1:]]
    if args: ns=[n for n in ns if any(n.startswith(a) for a in args)]
    res={}
    for n in ns:
        m=montar(n,ROT)
        if not m: continue
        m['ncorr']=corrigir(n,m)
        # tinta de caneta que sobrou na linha das cifras impressas, sem cifra conhecida:
        #  - com letra escrita à mão logo acima: é uma cifra que não sabemos -> marca "?" (a letra à mão continua à vista)
        #  - sem nada escrito acima: resto de risco -> some junto com os outros quando o tom muda
        sobra=[]
        for lv in m['livres']:
            b=lv['b']; cap=lv['cap']
            tem=[ll for ll in m['letras_livres'] if ll['lin']==lv['lin'] and ll['u0']<lv['u1']+0.8*cap and ll['u1']>lv['u0']-0.8*cap]
            if tem:
                m['itens'].append(dict(x=b[0],base=b[3],w=max(b[2]-b[0],0.5*cap),cap=cap,txt='?',lit=False,borr=[],lin=lv['lin'],u0=lv['u0'],u1=lv['u1'],ordem=lv['ordem']))
                sobra.append(lv)
            # (sem letra em cima: fica como está na foto — apagar sozinho arriscava tapar nota da partitura)
        m['livres']=sobra
        # marca "?" em cima de uma cifra conhecida (lugar repetido): fica só a cifra
        sab=[e for e in m['itens'] if e['txt']!='?']
        def repetida(q):
            for e in sab:
                ov=min(q['x']+q['w'],e['x']+e['w'])-max(q['x'],e['x'])
                if ov>0.3*min(q['w'],e['w']) and abs(q['base']-e['base'])<1.2*max(q['cap'],e['cap']): return True
            return False
        m['itens']=[e for e in m['itens'] if e['txt']!='?' or not repetida(e)]
        if any(n.startswith(p) for p in SEM_BORRACHA): m['itens']=[e for e in m['itens'] if e['txt']!='?']; m['livres']=[]; m['letras_livres']=[]     # folha sem caneta: não há o que marcar
        res[n]=m
    nomes=sorted(res)
    # tom impresso (pela ordem de leitura das cifras ainda no tom impresso) e cifras no tom da caneta
    ent=[dict(k=0,acordes=[e['txt'] for e in sorted(res[n]['itens'],key=lambda e:e['ordem']) if not e['lit'] and e['txt']!='?']) for n in nomes]
    toms=json.loads(subprocess.run(['node','--experimental-strip-types','/tmp/cif/transpor.mts'],input=json.dumps(ent),capture_output=True,text=True).stdout)
    # fotos do mesmo hino: o mesmo tom impresso (o mais votado)
    por_hino={}
    for n,t in zip(nomes,toms): por_hino.setdefault(re.match(r'h(\d+)',n).group(1),[]).append(t['tom'])
    import collections
    tom_h={h:collections.Counter([t for t in ts if t]).most_common(1)[0][0] if any(ts) else None for h,ts in por_hino.items()}
    ent=[dict(k=res[n]['o']['k'],acordes=[e['txt'] for e in res[n]['itens'] if not e['lit'] and e['txt']!='?'],tom=tom_h[re.match(r'h(\d+)',n).group(1)]) for n in nomes]
    out=json.loads(subprocess.run(['node','--experimental-strip-types','/tmp/cif/transpor.mts'],input=json.dumps(ent),capture_output=True,text=True).stdout)
    fn=R+'/data/cifras/hinos.json'; J=json.load(open(fn))
    tot=dict(cifras=0,marcas=0,borr=0)
    for n,o_ in zip(nomes,out):
        m=res[n]; up=m['up']; H,W=up.shape[:2]; it=iter(o_['acordes']); cs=[]; fim=[]
        def caixa(b): return [max(0,int(b[0])-2),max(0,int(b[1])-2),min(W,int(b[2])+2),min(H,int(b[3])+2)]
        nb=0
        for e in m['itens']:
            if e['txt']=='?':
                fs=e['cap']/0.711
                fim.append([int(round(e['x'])),int(round(e['base'])),int(round(e['w'])),round(fs,1),'?',0,0,int(round(1.1*e['cap'])),int(round(0.15*e['cap']))]); continue
            txt=e['txt'] if e['lit'] else next(it)
            for b in e['borr']:
                b=caixa(b); cs.append([b[0],b[3],b[2]-b[0],10,'',papel(up,*b),0,b[3]-b[1],0]); nb+=1
            fs=e['cap']/0.711; y0=e['base']-1.12*e['cap']; y1=e['base']+0.16*e['cap']
            fim.append([int(round(e['x'])),int(round(e['base'])),int(round(e['w'])),round(fs*1.15,1),txt,papel(up,e['x'],y0,e['x']+e['w'],y1),0,int(round(1.12*e['cap']+2)),int(round(0.16*e['cap']+2))])
        for b in m['soltas']:
            b=caixa(b); cs.append([b[0],b[3],b[2]-b[0],10,'',papel(up,*b),0,b[3]-b[1],0]); nb+=1
        cs+=fim
        nc=sum(1 for c_ in fim if c_[4]!='?'); nq=len(fim)-nc
        folha=dict(w=H if m['o']['r'] in (90,270) else W,h=W if m['o']['r'] in (90,270) else H,f='s',c=cs)
        if o_['tomNovo']: folha['k']=o_['tomNovo']
        if m['o']['r']: folha['r']=m['o']['r']
        if nc and nq>0.25*nc: folha['q']=1
        J['folhas'][m['o']['img']]=folha
        tot['cifras']+=nc; tot['marcas']+=nq; tot['borr']+=nb
        anc=[e.get('anc',True) for e in m['itens'] if e['txt']!='?' and 'anc' in e]
        m['ancoradas']=sum(anc)/max(1,len(anc))
        print(f"{n[:24]:24s} k{m['o']['k']:>3} {o_['tom']}->{o_['tomNovo']} cifras {nc:3d} '?' {nq:2d} borrachas {nb:3d} riscos livres {len(m['livres']):2d} letras livres {len(m['letras_livres']):2d} corr {m['ncorr']} ancoradas {100*m['ancoradas']:.0f}% ({len(anc)-sum(anc)} soltas)")
        if os.environ.get('CONF'):
            # tiras
            txt_de={id(e):t for e,t in zip([e for e in m['itens'] if e['txt']!='?'],[c_[4] for c_ in fim if c_[4]!='?'])}
            blocos=[]
            for li_,Lr in enumerate(m['linhas']):
                L=Lr['L']; c=Lr['c']; cor_f,src=Lr['faixa']; bw=L['bw']
                vr=max(0,L['v_row']-int(0.45*c)); limpa=cv2.cvtColor(src[vr:],cv2.COLOR_GRAY2BGR)
                raia=np.full((36,bw,3),255,np.uint8)
                for u in range(0,bw,100):
                    cv2.line(raia,(u,0),(u,4 if u%200 else 8),(120,120,120),1)
                    if u%200==0: cv2.putText(raia,str(u),(u+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.33,(120,120,120),1)
                for e in m['itens']:
                    if e.get('lin')!=li_: continue
                    t=txt_de.get(id(e),'?'); corr=(200,60,0) if t!='?' else (0,0,255)
                    cv2.putText(raia,t,(int(e['u0']),30),cv2.FONT_HERSHEY_SIMPLEX,0.55,corr,2,cv2.LINE_AA)
                    cv2.line(raia,(int(e['u0']),15),(int(e['u1']),15),corr,2)
                for lv in m['livres']:
                    if lv['lin']==li_: cv2.rectangle(raia,(int(lv['u0']),16),(int(lv['u1']),34),(0,0,255),2)
                for ll in m['letras_livres']:
                    if ll['lin']==li_: cv2.line(raia,(int(ll['u0']),34),(int(ll['u1']),34),(0,150,255),3)
                cab=np.full((16,bw,3),235,np.uint8); cv2.putText(cab,f"L{li_}  {L['fonte']}",(4,12),cv2.FONT_HERSHEY_SIMPLEX,0.42,(150,0,0),1)
                blocos.append(np.vstack([cab,cor_f,raia,limpa]))
            larg=max(b.shape[1] for b in blocos) if blocos else 0
            blocos=[cv2.copyMakeBorder(b,0,6,0,larg-b.shape[1],cv2.BORDER_CONSTANT,value=(255,255,255)) for b in blocos]
            parte=[];alt=0;k_=0
            for b in blocos+[None]:
                if b is None or (alt+b.shape[0]>1500 and parte):
                    cv2.imwrite(f'/tmp/cif/hfin/tiras_{n}_{k_}.jpg',np.vstack(parte),[cv2.IMWRITE_JPEG_QUALITY,84]); k_+=1; parte=[]; alt=0
                if b is not None: parte.append(b); alt+=b.shape[0]
            vis=up.copy()
            for c_ in cs:
                if c_[4]=='': cv2.rectangle(vis,(c_[0],c_[1]-c_[7]),(c_[0]+c_[2],c_[1]),(120,200,120),1)
            for lv in m['livres']: b=lv['b']; cv2.rectangle(vis,(b[0]-2,b[1]-2),(b[2]+2,b[3]+2),(0,0,255),3)
            for ll in m['letras_livres']: b=ll['b']; cv2.rectangle(vis,(b[0]-2,b[1]-2),(b[2]+2,b[3]+2),(0,150,255),2)
            for c_ in fim:
                cor=(255,60,0) if c_[4]!='?' else (0,0,255)
                cv2.putText(vis,c_[4],(c_[0],int(c_[1]+1.25*c_[3])),cv2.FONT_HERSHEY_SIMPLEX,max(0.5,c_[3]/38),cor,2,cv2.LINE_AA)
                cv2.line(vis,(c_[0],c_[1]+3),(c_[0]+c_[2],c_[1]+3),cor,2)
            sc=LARG_CONF/max(H,W)
            cv2.imwrite(f'/tmp/cif/hfin/conf_{n}.jpg',cv2.resize(vis,None,fx=sc,fy=sc,interpolation=cv2.INTER_AREA),[cv2.IMWRITE_JPEG_QUALITY,84])
    json.dump(J,open(fn,'w'),ensure_ascii=False,separators=(',',':'))
    print(tot,os.path.getsize(fn)//1024,'KB')
